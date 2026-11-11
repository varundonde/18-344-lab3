#!/usr/bin/env python3
"""Run the shared lab traces against VM source variants and plot the results."""

import argparse
import csv
import json
import subprocess
from pathlib import Path

try:
    from enum import StrEnum
except ImportError:  # Python 3.6 on the lab machines
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self):
            return self.value

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ("pte.cpp", "vm-provided.cpp", "ptab.cpp", "tlb.cpp", "vm-student.cpp")
WAYS = (1, 2, 4)
POLICIES = {
    "random": "TLB_RANDOM",
    "bit_plru": "TLB_BIT_PLRU",
    "exact_lru": "TLB_EXACT_LRU",
    "round_robin": "TLB_ROUND_ROBIN",
}


class RunStatus(StrEnum):
    SUCCESS = "success"
    SUCCESS_WITH_PAGE_FAULTS = "success_with_page_faults"
    UNMAPPED_ACCESS = "unmapped_access"


class RunSummary:
    def __init__(self, variant, trace, group, exit_code, accesses=None,
                 tlb_hits=None, page_faults=None):
        self.variant = variant
        self.trace = trace
        self.group = group
        self.exit_code = exit_code
        self.accesses = accesses
        self.tlb_hits = tlb_hits
        self.page_faults = page_faults

        if accesses is None:
            self.status = RunStatus.UNMAPPED_ACCESS
            self.tlb_misses = None
            self.estimated_translation_references = None
            self.estimated_total_references = None
        else:
            self.status = (RunStatus.SUCCESS_WITH_PAGE_FAULTS if page_faults
                           else RunStatus.SUCCESS)
            self.tlb_misses = accesses - tlb_hits
            self.estimated_translation_references = 4 * self.tlb_misses
            self.estimated_total_references = accesses + self.estimated_translation_references


def expand_trace(path):
    """Expand repeat blocks into the simple commands understood by trace_driver.cpp."""
    blocks = [[]]
    counts = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        words = line.split()
        if words[0] == "repeat":
            blocks.append([])
            counts.append(int(words[1]))
        elif words[0] == "end":
            body = blocks.pop()
            count = counts.pop()
            blocks[-1].extend(body * count)
        elif words[0] == "map":
            blocks[-1].append(f"map {int(words[1], 0):#x} {int(words[2], 0)}")
        else:
            blocks[-1].append(f"{words[0]} {int(words[1], 0):#x}")
    return "\n".join(blocks[0]) + "\n"


def build_variant(policy, ways, binary):
    binary.parent.mkdir(parents=True, exist_ok=True)
    command = ["g++", "-std=c++11", "-O2", f"-DTLB_POLICY={policy}",
               f"-DTLB_WAYS={ways}", "-I", str(ROOT)]
    command += [str(ROOT / file) for file in SOURCE_FILES]
    command += ["-x", "c++", "-", "-o", str(binary)]
    subprocess.run(command, input=(ROOT / "trace_driver.cpp").read_text(),
                   universal_newlines=True, check=True)


def run_trace(variant, binary, name, metadata, output):
    trace_file = output / "expanded" / f"{name}.trace"
    result = subprocess.run([str(binary), str(trace_file)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True)
    log = output / variant / f"trace_{name}_{variant}.log"
    log.write_text(result.stderr + result.stdout)

    if metadata["expected"] == "fault":
        assert result.returncode and "Unmapped page" in result.stderr
        return RunSummary(variant, name, metadata["group"], result.returncode)

    assert result.returncode == 0, f"{variant}/{name}: see logs"
    stats_line = next(line for line in result.stdout.splitlines()
                      if line.startswith("TRACE_STATS "))
    counts = {}
    for field in stats_line.split()[1:]:
        key, value = field.split("=")
        counts[key] = int(value)
    summary = RunSummary(variant, name, metadata["group"], result.returncode,
                         counts["accesses"], counts["tlb_hits"], counts["page_faults"])
    print(f"{variant}/{name}: {summary.accesses} accesses, {summary.tlb_misses} walks, "
          f"{summary.page_faults} page faults")
    return summary


def save_results(summaries, output):
    variants = list(dict.fromkeys(summary.variant for summary in summaries))
    for variant in variants:
        records = [vars(summary) for summary in summaries if summary.variant == variant]
        csv_path = output / variant / f"results_{variant}.csv"
        if csv_path.exists():
            with csv_path.open(newline="") as file:
                previous = {row["trace"]: row for row in csv.DictReader(file)}
            previous.update({row["trace"]: row for row in records})
            records = list(previous.values())
        with csv_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)



def load_baseline(output, names):
    csv_path = output / "no_tlb" / "results_no_tlb.csv"
    with csv_path.open(newline="") as file:
        records = list(csv.DictReader(file))
    summaries = []
    for row in records:
        if row["trace"] not in names:
            continue
        if row["accesses"]:
            summaries.append(RunSummary("no_tlb", row["trace"], row["group"], 0,
                                        int(row["accesses"]), int(row["tlb_hits"]),
                                        int(row["page_faults"])))
    return summaries


def plot(summaries, output, ways):
    data = [s for s in summaries if s.accesses is not None]
    if not data:
        return
    traces = list(dict.fromkeys(s.trace for s in data))
    variants = list(dict.fromkeys(s.variant for s in data))
    width = 0.8 / len(variants)
    fig, axes = plt.subplots(2, 1, figsize=(max(10, len(traces) * 1.5), 9),
                             constrained_layout=True)
    for index, variant in enumerate(variants):
        runs = {s.trace: s for s in data if s.variant == variant}
        x = [i - 0.4 + width * (index + 0.5) for i in range(len(traces))]
        axes[0].bar(x, [100 * runs[t].tlb_misses / runs[t].accesses for t in traces],
                    width, label=variant)
        axes[1].bar(x, [runs[t].estimated_total_references for t in traces],
                    width, label=variant)
    axes[0].set_title("Page table walks per access")
    axes[0].set_ylabel("Percent")
    axes[1].set_title("Program accesses + 4 references per page table walk")
    axes[1].set_ylabel("Estimated memory references")
    for axis in axes:
        axis.set_xticks(range(len(traces)))
        axis.set_xticklabels(traces, rotation=25, ha="right")
        axis.legend()
    fig.savefig(output / f"comparison_{ways}way.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="append", help="trace name; repeatable")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "traces" / "manifest.json").read_text())
    names = args.trace or list(manifest)
    output = args.output.expanduser().resolve()

    if args.dry_run:
        print(f"READ {output / 'no_tlb' / 'results_no_tlb.csv'}")
        print(f"REUSE {output / 'no_tlb' / 'trace_driver'} for new baseline traces")
        print(f"TRACES {', '.join(names)}")
        for ways in WAYS:
            for policy_name, policy in POLICIES.items():
                variant = f"{policy_name}_{ways}way"
                print(f"BUILD and RUN {variant} with {policy}; WRITE {output / variant / ('results_' + variant + '.csv')}")
            print(f"WRITE {output / ('comparison_' + str(ways) + 'way.png')}")
        return

    for ways in WAYS:
        for policy_name, policy in POLICIES.items():
            variant = f"{policy_name}_{ways}way"
            build_variant(policy, ways, output / variant / "trace_driver")
    (output / "expanded").mkdir(parents=True, exist_ok=True)
    for name in names:
        (output / "expanded" / f"{name}.trace").write_text(
            expand_trace(ROOT / "traces" / f"{name}.trace"))
    recorded = {run.trace for run in load_baseline(output, names)}
    new_baseline_names = [name for name in names if name not in recorded
                          and manifest[name]["expected"] == "ok"]
    baseline_runs = [run_trace("no_tlb", output / "no_tlb" / "trace_driver",
                               name, manifest[name], output) for name in new_baseline_names]
    policy_runs = []
    for ways in WAYS:
        for policy_name in POLICIES:
            variant = f"{policy_name}_{ways}way"
            for name in names:
                policy_runs.append(run_trace(variant, output / variant / "trace_driver",
                                             name, manifest[name], output))
    save_results(baseline_runs + policy_runs, output)
    baseline = load_baseline(output, names)
    for ways in WAYS:
        runs = [run for run in policy_runs if run.variant.endswith(f"_{ways}way")]
        plot(baseline + runs, output, ways)
    print(f"Saved results to {output}")


if __name__ == "__main__":
    main()
