#!/usr/bin/env python3
"""Build isolated VM variants, run shared traces, and plot handout metrics."""

import argparse
import csv
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACES = ROOT / "traces"
SOURCES = ("pte.cpp", "vm-provided.cpp", "ptab.cpp", "tlb.cpp", "vm-student.cpp")
HEADERS = ("vm.h", "ptab.h", "pte.h", "tlb.h", "pte-util.h", "vm-util.h")
STATS = re.compile(r"^TRACE_STATS accesses=(\d+) tlb_hits=(\d+) page_faults=(\d+)$", re.M)
UNMAPPED = re.compile(r"Unmapped page", re.I)
MAX_EXPANDED = 100_000


def parse_variant(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("use NAME=SOURCE_DIRECTORY")
    name, directory = value.split("=", 1)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
        raise argparse.ArgumentTypeError("variant name must use letters, digits, _ or -")
    path = Path(directory).expanduser().resolve()
    missing = [file for file in (*SOURCES, *HEADERS) if not (path / file).is_file()]
    if missing:
        raise argparse.ArgumentTypeError(f"{path}: missing {', '.join(missing)}")
    return name, path


def expand_trace(path):
    """Validate the small trace DSL and return map/load/store commands."""
    frames = [([], 1)]
    for number, original in enumerate(path.read_text().splitlines(), 1):
        line = original.split("#", 1)[0].strip()
        if not line:
            continue
        words = line.split()
        if words[0] == "repeat" and len(words) == 2:
            count = int(words[1], 0)
            if not 1 <= count <= MAX_EXPANDED:
                raise ValueError(f"{path}:{number}: invalid repeat count")
            frames.append(([], count))
        elif words == ["end"]:
            if len(frames) == 1:
                raise ValueError(f"{path}:{number}: unmatched end")
            body, count = frames.pop()
            if len(body) * count + len(frames[-1][0]) > MAX_EXPANDED:
                raise ValueError(f"{path}:{number}: trace too large")
            frames[-1][0].extend(body * count)
        elif words[0] in ("map", "load", "store"):
            expected = 3 if words[0] == "map" else 2
            if len(words) != expected:
                raise ValueError(f"{path}:{number}: expected {expected} fields")
            address = int(words[1], 0)
            if not 0 <= address < 1 << 48:
                raise ValueError(f"{path}:{number}: invalid 48-bit address")
            if words[0] == "map":
                size = int(words[2], 0)
                if size <= 0 or address + size > 1 << 48:
                    raise ValueError(f"{path}:{number}: invalid map size")
                command = f"map {address:#x} {size}"
            else:
                command = f"{words[0]} {address:#x}"
            frames[-1][0].append(command)
            if len(frames[-1][0]) > MAX_EXPANDED:
                raise ValueError(f"{path}:{number}: trace too large")
        else:
            raise ValueError(f"{path}:{number}: unknown command")
    if len(frames) != 1:
        raise ValueError(f"{path}: unclosed repeat block")
    return frames[0][0]


def build_variant(name, source, output, dry_run):
    binary = output / "build" / name / "trace_driver"
    driver_copy = binary.parent / "trace_driver.cpp"
    command = ["g++", "-std=c++11", "-O2", "-Wall", "-I", str(source),
               *(str(source / file) for file in SOURCES), str(driver_copy), "-o", str(binary)]
    if dry_run:
        print("BUILD", shlex.join(command))
    else:
        binary.parent.mkdir(parents=True, exist_ok=True)
        driver_copy.write_bytes((ROOT / "trace_driver.cpp").read_bytes())
        subprocess.run(command, check=True)
    return binary


def plot(rows, output, baseline):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ok = [row for row in rows if row["status"] == "ok"]
    if not ok:
        return
    trace_names = list(dict.fromkeys(row["trace"] for row in ok))
    variants = list(dict.fromkeys(row["variant"] for row in ok))
    fig, axes = plt.subplots(2, 1, figsize=(max(10, len(trace_names) * 1.6), 9),
                             constrained_layout=True)
    width = 0.8 / len(variants)
    positions = list(range(len(trace_names)))
    for index, variant in enumerate(variants):
        by_trace = {row["trace"]: row for row in ok if row["variant"] == variant}
        x = [pos - 0.4 + width * (index + 0.5) for pos in positions]
        axes[0].bar(x, [100 * by_trace[t]["tlb_misses"] / by_trace[t]["accesses"]
                         if t in by_trace and by_trace[t]["accesses"] else 0 for t in trace_names],
                    width, label=variant)
        axes[1].bar(x, [by_trace[t]["estimated_total_references"] if t in by_trace else 0
                         for t in trace_names], width, label=variant)
    axes[0].set_ylabel("Page table walks / accesses (%)")
    axes[0].set_title("TLB miss frequency (one walk per miss)")
    axes[1].set_ylabel("Estimated memory references")
    axes[1].set_title("Program accesses + 4 page table references per walk")
    for ax in axes:
        ax.set_xticks(positions, trace_names, rotation=25, ha="right")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)

    if baseline:
        base = {row["trace"]: row for row in ok if row["variant"] == baseline}
        comparison = []
        for row in ok:
            if row["variant"] == baseline or row["trace"] not in base:
                continue
            b = base[row["trace"]]
            comparison.append({"trace": row["trace"], "variant": row["variant"],
                               "walks_avoided": b["tlb_misses"] - row["tlb_misses"],
                               "estimated_references_saved": b["estimated_total_references"]
                               - row["estimated_total_references"]})
        (output / "baseline_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", type=parse_variant, action="append", required=True,
                        metavar="NAME=SOURCE_DIR", help="source tree for an implementation")
    parser.add_argument("--baseline", help="name of the no-TLB variant, for paired savings")
    parser.add_argument("--output", type=Path, default=ROOT / "trace-results")
    parser.add_argument("--dry-run", action="store_true", help="validate and show commands; write nothing")
    parser.add_argument("--trace", action="append", help="run only this trace name; repeatable")
    args = parser.parse_args()
    variants = dict(args.variant)
    if len(variants) != len(args.variant):
        parser.error("variant names must be unique")
    if len(set(variants.values())) != len(variants):
        parser.error("each variant needs a distinct source directory")
    if args.baseline and args.baseline not in variants:
        parser.error("--baseline must name a supplied variant")

    manifest = json.loads((TRACES / "manifest.json").read_text())
    selected = args.trace or list(manifest)
    for name in selected:
        if name not in manifest:
            parser.error(f"unknown trace {name}")
    traces = {name: expand_trace(TRACES / f"{name}.trace") for name in selected}
    output = args.output.expanduser().resolve()
    print(f"Output: {output}")
    for name, source in variants.items():
        print(f"Variant {name}: {source}")
    for name, commands in traces.items():
        print(f"Trace {name}: {len(commands)} operations; expected {manifest[name]['expected']}; "
              f"{manifest[name]['note']}")
    binaries = {name: build_variant(name, source, output, args.dry_run)
                for name, source in variants.items()}
    if args.dry_run:
        for variant, binary in binaries.items():
            for name in selected:
                print("RUN", shlex.join([str(binary), str(output / "expanded" / f"{name}.trace")]),
                      f"# {variant}")
        print("PLOT comparison.png; WRITE results.csv, results.json, raw logs")
        return 0

    (output / "expanded").mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(parents=True, exist_ok=True)
    for name, commands in traces.items():
        (output / "expanded" / f"{name}.trace").write_text("\n".join(commands) + "\n")

    rows = []
    for variant, binary in binaries.items():
        for name in selected:
            result = subprocess.run([str(binary), str(output / "expanded" / f"{name}.trace")],
                                    capture_output=True, text=True)
            (output / "logs" / f"{variant}__{name}.stdout").write_text(result.stdout)
            (output / "logs" / f"{variant}__{name}.stderr").write_text(result.stderr)
            expected = manifest[name]["expected"]
            match = STATS.search(result.stdout)
            if expected == "fault":
                if result.returncode == 0 or not UNMAPPED.search(result.stderr):
                    raise RuntimeError(f"{variant}/{name}: expected unmapped-access failure; see logs")
                rows.append({"variant": variant, "trace": name, "group": manifest[name]["group"],
                             "status": "expected_fault", "exit_code": result.returncode})
                continue
            if result.returncode or not match:
                raise RuntimeError(f"{variant}/{name}: execution failed or stats absent; see logs")
            accesses, hits, faults = map(int, match.groups())
            if hits > accesses:
                raise RuntimeError(f"{variant}/{name}: TLB hits exceed accesses")
            if variant == args.baseline and hits:
                raise RuntimeError(f"{variant}/{name}: baseline reported {hits} TLB hits; expected no TLB")
            misses = accesses - hits
            rows.append({"variant": variant, "trace": name, "group": manifest[name]["group"],
                         "status": "ok", "accesses": accesses, "tlb_hits": hits,
                         "tlb_misses": misses, "page_faults": faults,
                         "estimated_translation_references": 4 * misses,
                         "estimated_total_references": accesses + 4 * misses,
                         "exit_code": result.returncode})
            print(f"{variant}/{name}: accesses={accesses}, hits={hits}, walks={misses}, faults={faults}")
    (output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    fields = ("variant", "trace", "group", "status", "accesses", "tlb_hits", "tlb_misses",
              "page_faults", "estimated_translation_references", "estimated_total_references", "exit_code")
    with (output / "results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    plot(rows, output, args.baseline)
    print(f"Saved results and plots to {output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
