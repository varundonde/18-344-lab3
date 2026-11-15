#!/usr/bin/env python3
"""Run and plot a 64-entry TLB sweep with capacity held fixed.

Remote: python3 lab3/report/run_fixed_capacity.py --data-only
Local after syncing CSV: python3 lab3/report/run_fixed_capacity.py --plot-only
Outputs: lab3/results/fixed_capacity/summary.csv, three SVGs, and appendix rows.
The four traces here space VPNs by 64, so competing pages stay in the same
set as the set count changes from 64 to 8.
"""

import csv
import argparse
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "traces/fixed_capacity"
OUTPUT = ROOT / "results/fixed_capacity/summary.csv"
FIGURES = Path(__file__).resolve().parent / "figures"
APPENDIX_ROWS = Path(__file__).resolve().parent / "fixed_capacity_appendix.csv"
SOURCES = ("pte.cpp", "vm-provided.cpp", "ptab.cpp", "tlb.cpp",
           "vm-student.cpp", "trace_driver.cpp")
TOTAL_ENTRIES = 64
WAYS = (1, 2, 4, 8)
POLICIES = ("exact_lru", "bit_plru", "round_robin", "random")
POLICY_MACROS = {"exact_lru": "TLB_EXACT_LRU", "bit_plru": "TLB_BIT_PLRU",
                 "round_robin": "TLB_ROUND_ROBIN", "random": "TLB_RANDOM"}
TRACE_NAMES = ("stride64_4", "stride64_5", "stride64_hot_pair_5",
               "stride64_two_sets_10")
LABELS = {"stride64_4": "4 colliding pages",
          "stride64_5": "5 colliding pages",
          "stride64_hot_pair_5": "2 hot + 3 competing",
          "stride64_two_sets_10": "5 pages in each of 2 sets"}


def expand_trace(path):
    lines = []
    repeat_count = None
    repeat_body = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("repeat "):
            if repeat_count is not None:
                raise ValueError(f"Nested repeat in {path}")
            repeat_count = int(line.split()[1])
            repeat_body = []
        elif line == "end":
            if repeat_count is None:
                raise ValueError(f"Unmatched end in {path}")
            lines.extend(repeat_body * repeat_count)
            repeat_count = None
        elif repeat_count is None:
            lines.append(line)
        else:
            repeat_body.append(line)
    if repeat_count is not None:
        raise ValueError(f"Unclosed repeat in {path}")
    return "\n".join(lines) + "\n"


def collect():
    rows = []
    with tempfile.TemporaryDirectory(prefix="lab3-fixed-tlb-") as temp:
        temp = Path(temp)
        for trace in TRACE_NAMES:
            (temp / f"{trace}.trace").write_text(expand_trace(TRACES / f"{trace}.trace"))
        for ways in WAYS:
            sets = TOTAL_ENTRIES // ways
            for policy in POLICIES:
                binary = temp / f"tlb_{policy}_{ways}way"
                command = ["g++", "-std=c++11", "-O0", f"-DTLB_TOTAL_ENTRIES={TOTAL_ENTRIES}",
                           f"-DTLB_WAYS={ways}", f"-DTLB_POLICY={POLICY_MACROS[policy]}",
                           "-I", str(ROOT), *[str(ROOT / source) for source in SOURCES],
                           "-o", str(binary)]
                build = subprocess.run(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True)
                if build.returncode:
                    raise RuntimeError(f"Build failed for {policy}/{ways}: {build.stderr[-2000:]}")
                for trace in TRACE_NAMES:
                    result = subprocess.run([str(binary), str(temp / f"{trace}.trace")],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            universal_newlines=True)
                    if result.returncode:
                        raise RuntimeError(f"{policy}/{ways}/{trace}: {result.stderr[-1000:]}")
                    stats_line = next((line for line in result.stdout.splitlines()
                                       if line.startswith("TRACE_STATS ")), None)
                    if stats_line is None:
                        raise RuntimeError(f"Missing stats: {policy}/{ways}/{trace}")
                    stats = dict(field.split("=", 1) for field in stats_line.split()[1:])
                    accesses = int(stats["accesses"])
                    hits = int(stats["tlb_hits"])
                    misses = accesses - hits
                    rows.append({"entries": TOTAL_ENTRIES, "sets": sets, "ways": ways,
                                 "policy": policy, "trace": trace, "accesses": accesses,
                                 "tlb_hits": hits, "page_faults": int(stats["page_faults"]),
                                 "tlb_misses": misses,
                                 "walks_per_100_accesses": 100 * misses / accesses})
            print(f"Finished {ways}-way, {sets}-set configurations", flush=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return {(row["policy"], row["ways"], row["trace"]): row for row in rows}


def rate(data, policy, ways, trace):
    return data[(policy, ways, trace)]["walks_per_100_accesses"]


def plot_associativity(data):
    from plot_results import SVG, axes, legend, COLORS

    traces = ("stride64_4", "stride64_5", "stride64_hot_pair_5")
    svg = SVG(830, 345)
    svg.text(415, 25, "Page-table walks vs. TLB associativity", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Measured with a 64-entry exact-LRU TLB at 1, 2, 4, and 8 ways",
             11, anchor="middle")
    left, top, right, bottom = 88, 65, 805, 265
    axes(svg, left, top, right, bottom, 100, (0, 25, 50, 75, 100),
         "Page-table walks per 100 accesses")
    xs = [left + (right - left) * (i + 0.5) / len(WAYS) for i in range(len(WAYS))]
    for j, trace in enumerate(traces):
        ys = [bottom - (bottom - top) * rate(data, "exact_lru", ways, trace) / 100
              for ways in WAYS]
        for i in range(len(WAYS) - 1):
            svg.line(xs[i], ys[i], xs[i + 1], ys[i + 1], COLORS[j], 3)
        for x, y in zip(xs, ys):
            svg.circle(x, y, 4.5, COLORS[j])
    for x, ways in zip(xs, WAYS):
        svg.text(x, bottom + 22, ways, 12, anchor="middle")
    svg.text(445, bottom + 42, "TLB associativity (ways)", 12, anchor="middle")
    legend(svg, [(LABELS[trace], COLORS[i]) for i, trace in enumerate(traces)],
           105, 338, 235)
    svg.save("fixed64-walks-vs-associativity.svg")


def plot_policy_four_way(data):
    from plot_results import SVG, axes, legend, COLORS, NAMES

    traces = ("stride64_5", "stride64_hot_pair_5", "stride64_two_sets_10")
    svg = SVG(830, 350)
    svg.text(415, 25, "Replacement policy under set contention", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Measured with a 64-entry, 16-set, 4-way TLB under four policies",
             11, anchor="middle")
    left, top, right, bottom = 88, 65, 805, 260
    axes(svg, left, top, right, bottom, 100, (0, 25, 50, 75, 100),
         "Page-table walks per 100 accesses")
    group = (right - left) / len(traces)
    for i, trace in enumerate(traces):
        center = left + group * (i + 0.5)
        for j, policy in enumerate(POLICIES):
            height = (bottom - top) * rate(data, policy, 4, trace) / 100
            svg.rect(center + (j - 2) * 42 + 5, bottom - height, 34, height, COLORS[j])
        svg.text(center, bottom + 22, LABELS[trace], 10, anchor="middle")
    svg.text(445, bottom + 43, "Trace (category)", 12, anchor="middle")
    legend(svg, [(NAMES[p], COLORS[i]) for i, p in enumerate(POLICIES)],
           80, 345, 180)
    svg.save("fixed64-policy-at-four-ways.svg")


def plot_policy_sweep(data):
    from plot_results import SVG, legend, COLORS, NAMES

    traces = ("stride64_5", "stride64_hot_pair_5", "stride64_two_sets_10")
    svg = SVG(830, 430)
    svg.text(415, 25, "Replacement policy across associativities", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Measured with 64-entry TLBs at 1, 2, 4, and 8 ways under four policies", 11,
             anchor="middle")
    top, bottom = 90, 325
    for panel, trace in enumerate(traces):
        left = 92 + panel * 245
        right = left + 205
        svg.text((left + right) / 2, 76, LABELS[trace], 10, anchor="middle", weight="bold")
        for tick in (0, 25, 50, 75, 100):
            y = bottom - (bottom - top) * tick / 100
            svg.line(left, y, right, y)
            if panel == 0:
                svg.text(left - 8, y + 4, tick, 10, anchor="end")
        svg.line(left, top, left, bottom, "#607080")
        svg.line(left, bottom, right, bottom, "#607080")
        xs = [left + 18 + i * (right - left - 36) / 3 for i in range(4)]
        for j, policy in enumerate(POLICIES):
            ys = [bottom - (bottom - top) * rate(data, policy, ways, trace) / 100
                  for ways in WAYS]
            for i in range(3):
                svg.line(xs[i], ys[i], xs[i + 1], ys[i + 1], COLORS[j], 2)
            for x, y in zip(xs, ys):
                svg.circle(x, y, 3.5, COLORS[j])
        for x, ways in zip(xs, WAYS):
            svg.text(x, bottom + 19, ways, 10, anchor="middle")
    svg.vertical_text(20, (top + bottom) / 2, "Page-table walks per 100 accesses")
    svg.text(445, 373, "TLB associativity (ways)", 12, anchor="middle")
    legend(svg, [(NAMES[p], COLORS[i]) for i, p in enumerate(POLICIES)],
           75, 421, 180)
    svg.save("fixed64-policy-across-ways.svg")


def load_collected():
    with OUTPUT.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != len(WAYS) * len(POLICIES) * len(TRACE_NAMES):
        raise ValueError(f"Expected 64 runs in {OUTPUT}, found {len(rows)}")
    for row in rows:
        row["ways"] = int(row["ways"])
        row["walks_per_100_accesses"] = float(row["walks_per_100_accesses"])
    return {(row["policy"], row["ways"], row["trace"]): row for row in rows}


def write_appendix_rows(data):
    with APPENDIX_ROWS.open("w", newline="") as output:
        writer = csv.writer(output)
        for trace in TRACE_NAMES:
            for ways in WAYS:
                for policy in POLICIES:
                    row = data[(policy, ways, trace)]
                    writer.writerow((trace, row["sets"], ways, NAMES_FOR_TABLE[policy],
                                     row["accesses"], row["tlb_hits"],
                                     row["page_faults"], row["tlb_misses"]))


NAMES_FOR_TABLE = {"exact_lru": "Exact LRU", "bit_plru": "Bit PLRU",
                   "round_robin": "Round robin", "random": "Random"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--data-only", action="store_true",
                      help="build and run on the remote machine, writing only the CSV")
    mode.add_argument("--plot-only", action="store_true",
                      help="read a synced CSV and regenerate the report figures locally")
    args = parser.parse_args()
    data = load_collected() if args.plot_only else collect()
    if not args.data_only:
        plot_associativity(data)
        plot_policy_four_way(data)
        plot_policy_sweep(data)
        write_appendix_rows(data)
        print(f"Wrote 3 report figures and appendix rows from {OUTPUT}")


if __name__ == "__main__":
    main()
