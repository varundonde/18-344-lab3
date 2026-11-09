#!/usr/bin/env python3
"""Run the shared lab traces against VM source variants and plot the results."""

import argparse
import csv
import json
import subprocess
from enum import StrEnum
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ("pte.cpp", "vm-provided.cpp", "ptab.cpp", "tlb.cpp", "vm-student.cpp")


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


def build_variant(source, binary):
    binary.parent.mkdir(parents=True, exist_ok=True)
    command = ["g++", "-std=c++11", "-O2", "-I", str(source)]
    command += [str(source / file) for file in SOURCE_FILES]
    command += ["-x", "c++", "-", "-o", str(binary)]
    subprocess.run(command, input=(ROOT / "trace_driver.cpp").read_text(),
                   text=True, check=True)


def run_trace(variant, binary, name, metadata, output):
    trace_file = output / "expanded" / f"{name}.trace"
    result = subprocess.run([str(binary), str(trace_file)], capture_output=True, text=True)
    (output / "logs" / f"{variant}__{name}.stdout").write_text(result.stdout)
    (output / "logs" / f"{variant}__{name}.stderr").write_text(result.stderr)

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


def save_results(summaries, output, baseline):
    records = [vars(summary) for summary in summaries]
    (output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
    with (output / "results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    if baseline:
        base = {s.trace: s for s in summaries if s.variant == baseline and s.accesses is not None}
        savings = []
        for summary in summaries:
            if summary.variant == baseline or summary.accesses is None:
                continue
            original = base[summary.trace]
            savings.append({"trace": summary.trace, "variant": summary.variant,
                            "walks_avoided": original.tlb_misses - summary.tlb_misses,
                            "estimated_references_saved": original.estimated_total_references
                            - summary.estimated_total_references})
        (output / "baseline_comparison.json").write_text(json.dumps(savings, indent=2) + "\n")


def plot(summaries, output):
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
        axis.set_xticks(range(len(traces)), traces, rotation=25, ha="right")
        axis.legend()
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", action="append", required=True, metavar="NAME=SOURCE_DIR")
    parser.add_argument("--baseline", help="name of the no-TLB variant")
    parser.add_argument("--trace", action="append", help="trace name; repeatable")
    parser.add_argument("--output", type=Path, default=ROOT / "trace-results")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    variants = {}
    for item in args.variant:
        name, path = item.split("=", 1)
        variants[name] = Path(path).expanduser().resolve()
    manifest = json.loads((ROOT / "traces" / "manifest.json").read_text())
    names = args.trace or list(manifest)
    output = args.output.expanduser().resolve()

    if args.dry_run:
        for variant, source in variants.items():
            print(f"BUILD {variant} from {source}")
            for name in names:
                print(f"RUN {variant}/{name}: {manifest[name]['note']}")
        print(f"WRITE results and plots to {output}")
        return

    for variant, source in variants.items():
        build_variant(source, output / "build" / variant / "trace_driver")
    (output / "expanded").mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(parents=True, exist_ok=True)
    for name in names:
        (output / "expanded" / f"{name}.trace").write_text(
            expand_trace(ROOT / "traces" / f"{name}.trace"))
    summaries = [run_trace(variant, output / "build" / variant / "trace_driver",
                           name, manifest[name], output)
                 for variant in variants for name in names]
    save_results(summaries, output, args.baseline)
    plot(summaries, output)
    print(f"Saved results to {output}")


if __name__ == "__main__":
    main()
