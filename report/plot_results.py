#!/usr/bin/env python3
"""Regenerate Lab 3 SVG figures from the recorded trace CSVs.

Run from any directory: python3 lab3/report/plot_results.py
The estimate uses four page-table references per TLB miss, as in run_traces.py.
"""

import csv
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = Path(__file__).resolve().parent / "figures"
POLICIES = ("exact_lru", "bit_plru", "round_robin", "random")
COLORS = ("#2563a6", "#d27632", "#46926d", "#9b65a5")
NAMES = {"exact_lru": "Exact LRU", "bit_plru": "Bit PLRU",
         "round_robin": "Round robin", "random": "Random"}
TRACES = {
    "hot_page": "Hot page", "cold_stream": "Cold stream",
    "sequential_12": "Sequential 12", "same_set_4": "Same set, 4",
    "same_set_5": "Same set, 5", "hot_pair_5": "Hot pair, 5",
    "two_sets_10": "Two sets, 10", "different_sets_4": "Different sets, 4",
    "boundaries": "Boundaries", "page_pressure": "Page pressure",
}


def load(variant):
    path = RESULTS / variant / f"results_{variant}.csv"
    with path.open(newline="") as source:
        rows = {row["trace"]: row for row in csv.DictReader(source)}
    expected = set(TRACES)
    if not expected <= rows.keys():
        raise ValueError(f"{path}: missing {sorted(expected - rows.keys())}")
    for trace in expected:
        for key in ("accesses", "tlb_misses", "tlb_hits", "page_faults"):
            rows[trace][key] = int(rows[trace][key])
    return rows


DATA = {variant: load(variant) for variant in
        ["no_tlb"] + [f"{policy}_{ways}way" for policy in POLICIES
                      for ways in (1, 2, 4)]}


class SVG:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
                      f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                      '<rect width="100%" height="100%" fill="white"/>']

    def line(self, x1, y1, x2, y2, color="#d5dce4", width=1):
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
                          f'y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"/>')

    def rect(self, x, y, w, h, color):
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                          f'height="{max(0, h):.1f}" fill="{color}"/>')

    def circle(self, x, y, radius, color):
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}"/>')

    def text(self, x, y, value, size=13, color="#263544", anchor="start", weight="normal"):
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
                          f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
                          f'font-weight="{weight}">{escape(str(value))}</text>')

    def vertical_text(self, x, y, value, size=12):
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate(-90 {x:.1f} {y:.1f})" '
                          f'font-family="Helvetica,Arial,sans-serif" font-size="{size}" '
                          f'fill="#263544" text-anchor="middle">{escape(str(value))}</text>')

    def save(self, name):
        FIGURES.mkdir(parents=True, exist_ok=True)
        (FIGURES / name).write_text("\n".join(self.parts + ["</svg>\n"]))


def axes(svg, left, top, right, bottom, maximum, ticks, ylabel):
    for tick in ticks:
        y = bottom - (bottom - top) * tick / maximum
        svg.line(left, y, right, y)
        svg.text(left - 10, y + 4, tick, 11, anchor="end")
    svg.line(left, top, left, bottom, "#607080")
    svg.line(left, bottom, right, bottom, "#607080")
    svg.vertical_text(20, (top + bottom) / 2, ylabel)


def legend(svg, entries, x, y, gap=125):
    for i, (label, color) in enumerate(entries):
        svg.rect(x + i * gap, y - 11, 15, 10, color)
        svg.text(x + i * gap + 21, y - 2, label, 11)


def walk_rate(row):
    return 100 * row["tlb_misses"] / row["accesses"]


def references(row):
    return row["accesses"] + 4 * row["tlb_misses"]


def associativity():
    # All three traces have repeated set-conflict walks whose rate changes
    # with associativity. two_sets_10 is omitted because its line almost
    # exactly overlaps same_set_5 at every tested way count.
    traces = ("same_set_4", "same_set_5", "hot_pair_5")
    svg = SVG(830, 345)
    svg.text(415, 25, "Page-table walks vs. TLB associativity", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Exact LRU, 16 sets", 11, anchor="middle")
    left, top, right, bottom = 88, 65, 805, 265
    axes(svg, left, top, right, bottom, 100, (0, 25, 50, 75, 100),
         "Page-table walks per 100 accesses")
    xs = [left + (right - left) * (i + 0.5) / 3 for i in range(3)]
    for idx, trace in enumerate(traces):
        ys = [bottom - (bottom - top) * walk_rate(DATA[f"exact_lru_{ways}way"][trace]) / 100
              for ways in (1, 2, 4)]
        for i in range(2):
            svg.line(xs[i], ys[i], xs[i + 1], ys[i + 1], COLORS[idx], 3)
        for x, y in zip(xs, ys):
            svg.circle(x, y, 4.5, COLORS[idx])
    for x, way in zip(xs, (1, 2, 4)):
        svg.text(x, bottom + 22, str(way), 12, anchor="middle")
    svg.text((left + right) / 2, bottom + 42, "TLB associativity (ways)", 12,
             anchor="middle")
    legend(svg, [(TRACES[t], COLORS[i]) for i, t in enumerate(traces)], 145, 338, 205)
    svg.save("walks-vs-associativity.svg")


def policy():
    traces = ("same_set_5", "hot_pair_5", "two_sets_10")
    svg = SVG(830, 350)
    svg.text(415, 25, "Replacement policy under set contention", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "16 sets, 4 ways", 11, anchor="middle")
    left, top, right, bottom = 88, 65, 805, 260
    axes(svg, left, top, right, bottom, 100, (0, 25, 50, 75, 100),
         "Page-table walks per 100 accesses")
    group = (right - left) / len(traces)
    bar = 42
    for i, trace in enumerate(traces):
        center = left + group * (i + 0.5)
        for j, policy_name in enumerate(POLICIES):
            value = walk_rate(DATA[f"{policy_name}_4way"][trace])
            height = (bottom - top) * value / 100
            svg.rect(center + (j - 2) * bar + 5, bottom - height, bar - 8, height, COLORS[j])
        svg.text(center, bottom + 23, TRACES[trace], 12, anchor="middle")
    svg.text((left + right) / 2, bottom + 43, "Trace (category)", 12, anchor="middle")
    legend(svg, [(NAMES[p], COLORS[i]) for i, p in enumerate(POLICIES)], 80, 345, 180)
    svg.save("policy-at-four-ways.svg")


def policy_by_ways():
    traces = ("same_set_5", "hot_pair_5", "two_sets_10")
    svg = SVG(830, 400)
    svg.text(415, 25, "Replacement policy across associativities", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Numbers inside bars indicate TLB ways", 11, anchor="middle")
    left, top, right, bottom = 88, 65, 805, 300
    axes(svg, left, top, right, bottom, 100, (0, 25, 50, 75, 100),
         "Page-table walks per 100 accesses")
    group = (right - left) / len(traces)
    bar = 17
    for i, trace in enumerate(traces):
        center = left + group * (i + 0.5)
        for j, policy_name in enumerate(POLICIES):
            for k, ways in enumerate((1, 2, 4)):
                value = walk_rate(DATA[f"{policy_name}_{ways}way"][trace])
                height = (bottom - top) * value / 100
                x = center - 6 * bar + (j * 3 + k) * bar
                svg.rect(x, bottom - height, bar - 2, height, COLORS[j])
                if height > 12:
                    svg.text(x + 7.5, bottom - height + 13, str(ways), 9, "white", "middle", "bold")
        svg.text(center, bottom + 23, TRACES[trace], 12, anchor="middle")
    svg.text((left + right) / 2, bottom + 43, "Trace (category)", 12, anchor="middle")
    legend(svg, [(NAMES[p], COLORS[i]) for i, p in enumerate(POLICIES)], 80, 390, 180)
    svg.save("policy-across-ways.svg")


def translation_cost():
    traces = ("hot_page", "cold_stream", "sequential_12", "same_set_4",
              "different_sets_4", "page_pressure")
    svg = SVG(830, 350)
    svg.text(415, 25, "Translation cost with and without TLB", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Four page-table references per miss, exact LRU, 4 ways", 11,
             anchor="middle")
    left, top, right, bottom = 88, 65, 805, 260
    axes(svg, left, top, right, bottom, 5, (0, 1, 2, 3, 4, 5),
         "Memory references per access")
    group = (right - left) / len(traces)
    for i, trace in enumerate(traces):
        center = left + group * (i + 0.5)
        row = DATA["exact_lru_4way"][trace]
        baseline = DATA["no_tlb"][trace]
        for j, value in enumerate((references(baseline) / baseline["accesses"],
                                   references(row) / row["accesses"])):
            height = (bottom - top) * value / 5
            svg.rect(center - 34 + j * 34, bottom - height, 27, height, ("#a9b8c7", COLORS[0])[j])
        svg.text(center, bottom + 20, TRACES[trace], 10, anchor="middle")
    svg.text((left + right) / 2, bottom + 43, "Trace (category)", 12, anchor="middle")
    legend(svg, [("Without TLB", "#a9b8c7"), ("Exact LRU, 4 ways", COLORS[0])],
           240, 345, 230)
    svg.save("translation-reference-cost.svg")


def reference_breakdown():
    traces = ("hot_page", "cold_stream", "sequential_12", "same_set_4",
              "same_set_5", "hot_pair_5", "two_sets_10", "different_sets_4",
              "boundaries", "page_pressure")
    svg = SVG(830, 450)
    svg.text(415, 25, "Overall reference breakdown by trace", 18,
             anchor="middle", weight="bold")
    svg.text(415, 45, "Exact LRU, 16 sets, 4 ways", 11, anchor="middle")
    left, top, right = 180, 70, 790
    max_value = max(references(DATA["exact_lru_4way"][t]) for t in traces)
    scale = (right - left) / (max_value * 1.08)
    for tick in range(0, (max_value // 200 + 1) * 200, 200):
        x = left + tick * scale
        svg.line(x, top, x, 365)
        svg.text(x, 382, tick, 10, anchor="middle")
    for i, trace in enumerate(traces):
        row = DATA["exact_lru_4way"][trace]
        y = 74 + i * 29
        svg.text(left - 10, y + 13, TRACES[trace], 11, anchor="end")
        svg.rect(left, y, row["accesses"] * scale, 18, COLORS[0])
        svg.rect(left + row["accesses"] * scale, y, 4 * row["tlb_misses"] * scale, 18, COLORS[1])
        svg.text(left + references(row) * scale + 7, y + 13, references(row), 10)
    svg.vertical_text(20, 220, "Trace (category)", 12)
    svg.text((left + right) / 2, 407, "Estimated memory references (count)", 12,
             anchor="middle")
    legend(svg, [("Program accesses", COLORS[0]), ("Translation references", COLORS[1])],
           215, 443, 215)
    svg.save("overall-reference-breakdown.svg")


if __name__ == "__main__":
    associativity()
    policy()
    policy_by_ways()
    translation_cost()
    reference_breakdown()
    print(f"Wrote 5 figures to {FIGURES}")
