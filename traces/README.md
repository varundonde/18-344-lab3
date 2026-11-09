# Lab 3 trace study

These traces are shared by every VM implementation. The trace driver is separate from `vm_test.cpp` and does not change any VM, page table, or TLB source file.

## Trace format

- `map ADDRESS SIZE` maps a byte range. `SIZE` is decimal or `0x` hex.
- `load ADDRESS` and `store ADDRESS` make one virtual memory access each.
- `repeat COUNT` ... `end` repeats enclosed operations. Blocks can nest.
- Addresses may be decimal or `0x` hex; `#` starts a comment.

The runner expands repeats before calling the C++ driver. It limits each expanded trace to 100,000 operations. The driver's `pageLoadSingle` and `pageStoreSingle` calls match the supplied test driver's access model; multi-byte access size is not modeled by the provided VM methods.

## Why these traces

| Trace | Behavior to inspect |
| --- | --- |
| `hot_page` | Spatial and temporal locality; one first-touch fault followed by many accesses to the same page. |
| `cold_stream` | Twelve distinct first touches; compulsory walks and faults. |
| `sequential_12` | Repeated twelve-page working set; capacity sensitivity without exhausting the fourteen physical pages. |
| `same_set_4` / `different_sets_4` | Conflict versus spread across low-four-bit VPN indices, useful for a 16-set design. |
| `boundaries` | Unaligned map plus crossings at 4 KiB, 2 MiB, and 1 GiB; exercises page table indexes. |
| `unmapped_access` | Expected access violation, recorded separately from successful-run metrics. |
| `page_pressure` | Fifteen first touches force replacement after fourteen available physical pages. |

The handout asks for TLB miss or page table walk frequency, total program accesses, page faults, and a quantitative estimate of translation work saved. The runner records all of these. It assumes four page table memory references per walk, matching the lab's four-level page table, and estimates `program accesses + 4 × misses` total memory references. This is an analytical estimate: it excludes TLB lookup cost, page fault service, and page replacement work. `page_pressure` is primarily a correctness and replacement probe; interpret its cost estimate with that limitation.

## Running later

Keep a source tree from before adding the TLB, then point each variant at a separate complete source tree. A Git worktree or a copy is suitable. Each tree needs `pte.cpp`, `vm-provided.cpp`, `ptab.cpp`, `tlb.cpp`, `vm-student.cpp`, and their headers. The runner builds a separate binary for each variant with its own copy of `trace_driver.cpp`; it never writes to a variant's source tree. `vm_test.cpp` is not linked.

First inspect the plan without building, running traces, or writing output:

```sh
python3 run_traces.py --variant no_tlb=/path/to/no_tlb_tree --variant tlb=/path/to/tlb_tree --baseline no_tlb --dry-run
```

When ready to collect data:

```sh
python3 run_traces.py --variant no_tlb=/path/to/no_tlb_tree --variant tlb=/path/to/tlb_tree --baseline no_tlb
```

For a TLB design-space study, add variants such as `--variant direct=/path/to/direct_tree` and `--variant four_way=/path/to/four_way_tree`. The script checks that the named no-TLB baseline reports zero TLB hits. You may also run a single variant or select traces with repeatable `--trace NAME` options. Requires Python 3, `g++`, and `matplotlib` for real runs; dry run does not import matplotlib.

Outputs under `trace-results/` include expanded input, raw stdout and stderr logs, `results.csv`, `results.json`, `comparison.png`, and, when a baseline is named, `baseline_comparison.json`. The CSV includes accesses, TLB hits, page table walks (`accesses − hits`), faults, and estimated reference counts. The plot shows walk frequency and estimated total references by trace and variant. The expected access violation appears as `expected_fault` without numerical metrics.
