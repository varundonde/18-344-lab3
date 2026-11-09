# Lab 3 traces

The same traces work with or without a TLB; the runner builds a separate driver for each implementation and does not edit VM code.

Without a TLB, every access walks the page table. With a TLB, only misses walk it, so repeated accesses should usually need fewer translation memory references.

| Trace | What to expect |
| --- | --- |
| `hot_page` | Without a TLB, all 192 accesses walk the page table; with one, only the first access should miss. |
| `cold_stream` | All 12 accesses touch new pages, so a TLB should give little or no benefit. |
| `sequential_12` | Repeated accesses to 12 pages should show fewer walks with a TLB if it can hold that working set. |
| `same_set_4` | Four pages compete for one TLB set, so a low-associativity TLB may miss often while no-TLB always walks. |
| `different_sets_4` | Four pages use different TLB sets, so a TLB should have only initial misses while no-TLB always walks. |
| `boundaries` | Both versions should handle the mapped 4 KiB, 2 MiB, and 1 GiB crossings; a TLB should save walks on repeats. |
| `unmapped_access` | Both versions should report an access violation for the unmapped page. |
| `page_pressure` | Both versions should encounter page replacement after 14 first-touch allocations; this trace mainly checks replacement behavior. |

The runner records accesses, TLB hits, page faults, and page table walks (`accesses − hits`). Each run gets a status of `success`, `success_with_page_faults`, or `unmapped_access`; page faults are normal events during a successful run. The plot estimates memory references as `program accesses + 4 × page table walks`, using the handout's four-level page table. This estimate does not include page fault or replacement work.

## Run later

Keep separate source directories for the no-TLB and TLB versions, then inspect the commands without running traces:

```sh
python3 run_traces.py --variant no_tlb=/path/to/no_tlb_tree --variant tlb=/path/to/tlb_tree --baseline no_tlb --dry-run
```

When ready to collect data, remove `--dry-run`. Add more `--variant NAME=SOURCE_DIR` arguments to compare TLB configurations. Results and plots go in `trace-results/`. The runner requires Python 3.11 or newer and `matplotlib`; real runs also require `g++`.

Trace files use `map ADDRESS SIZE`, `load ADDRESS`, `store ADDRESS`, and `repeat COUNT` ... `end`; `#` starts a comment.
