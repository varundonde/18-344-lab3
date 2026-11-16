#set document(
  title: "Lab 3: Virtual Memory",
  author: "Varun Donde and Kushal Garg",
)
#set page(paper: "us-letter", margin: (x: 0.7in, y: 0.65in))
#set text(font: "New Computer Modern", size: 10pt)

#align(center)[
  = Lab 3: Virtual Memory
  Varun Donde (vdonde) #h(1em) Kushal Garg (kushalg) #h(1em) 18-344, Fall 2026
]

= Introduction
In this lab, we aimed to isolate the effects of the TLB in virtual memory paging and address translation. We aimed to answer two questions, firstly: how effective is the TLB in making the address translation process more efficient, and secondly: what aspects of the TLB could you vary to lead to better performance. To answer these questions, we built three tools in C++: firstly, a page table following the Intel Core i7 processor, which uses a 4-level page table hierarchy to translate a 48-bit virtual address into a physical address. Secondly, the core virtual memory procedures to map virtual pages to physical frames, as well as a page fault handler. Finally, a TLB cache modeled after Skylake L1 data TLB. To evaluate our implementation, we created a series of traces to and measured the performance of our VM system with and without a TLB, as well as measured performance after varying design aspects of the TLB (eg. associativity, eviction policy). 

= Methodology

== Page Table Implementation

The page table's core operations are `getEntry` and `createEntry`. ```C getEntry(unsigned long addr, size_t level)``` retrieves the entry at the index calculated by the helper `getEntryIdFromAddr(addr, level)`, which selects the address bits for that page-table level. `getEntry` is used in address translation, when we traverse through the hierarchal page table to retrieve the associated physical frame for a virtual page. It's also used when traversing through the page table when we map out a frame for an address.  

Next, we implemented ```C createEntry(unsigned long addr, size_t level)```, which depending on the level of traversal, either creates a `new pageTable()` or `pageTableEntry(addr)` and stores it at an `addr` specified index within a page table. This function is used in our virtual memory implementation, when we map virtual pages to physical frames. 

== Virtual Memory Procedures

#align(center, image("figures/vm-procedure-flow.png", width: 100%))

Blue boxes are our implemened procedures, purple boxes are provided operations in the handout code, and green boxes are end conditions. `vmMap` creates paged-out leaf entries. On a page fault, the handler tries to `bumpAllocate`, and if no frame is free, `replacePage` evicts a page and the handler invalidates its TLB entry before reusing the frame. `vmTranslate` adds the new resident page to the replacement list.

== TLB

The TLB was implemented in a similar configuration to the caches from the previous lab. Each TLB was made of sets containing TLB entries. When the TLB is accessed, the address is shifted and masked in order to find the virtual page number, or VPN. The VPN corresponds to an entry in the TLB.

Each TLB entry contains the VPN's corresponding physical page number (PPN) along with the required information for each replacement policy:
#enum(
  enum.item(1)[Exact LRU: Uses ``` last_used``` to find and evict the least recently used victim],
  enum.item(2)[Bit-PLRU: Uses ``` used``` to denote recently used entries, this value resets when all entries are used. The first entry not recently used is evicted.],
  enum.item(3)[Round Robin: Uses ``` inserted``` to find and evict that entered the TLB first.],
  enum.item(4)[Random: A random entry is evicted.]
)

The TLB has three functions for its use: ``` lookup```, ``` update```, and ``` invalidate```.

``` lookup``` takes in an address and checks its VPN in the TLB. On a miss, it will return false; on a hit, it will return true alongside the PPN and update all of the replacement policy information.

``` update``` takes in an address and a PPN and creates a new entry in the TLB. It finds the victim based on the replacement policy, erases it, and adds the new entry into the TLB with the VPN, PPN, and replacement policy information.

``` invalidate``` takes in an address and erases its entry from the TLB. When a page is evicted from memory, the page translation in the TLB is now invalidated and must be erased.

== Traces

We created the following traces to test our VM system.

#{
  set text(size: 8.5pt)
  align(center, box(width: 108%, table(
    columns: (1.35fr, 2.4fr, 2.35fr),
    inset: (x: 4pt, y: 3pt),
    stroke: 0.4pt,
    align: left,
    table.header([Trace], [Workload], [Expected result]),
    [`hot_page`], [Repeated access within one page], [One compulsory fault, then TLB hits],
    [`cold_stream`], [First access to each of 12 pages], [12 faults and 12 walks, with no TLB hits],
    [`sequential_12`], [Reuse of a 12-page working set], [12 initial faults and walks, then TLB hits],
    [`same_set_4`], [Four pages mapping to one TLB set], [Four walks at 4 ways, conflict misses at fewer ways],
    [`same_set_5`], [Five pages competing in one TLB set], [Evictions and repeated walks at 4 ways],
    [`hot_pair_5`], [Two hot pages competing with three others], [Replacement-policy-dependent walks],
    [`two_sets_10`], [Five competing pages in each of two sets], [Evictions and repeated walks in both sets],
    [`stride64_4`], [Four pages spaced 64 VPNs apart], [Walks on every access at 1 and 2 ways, four initial walks at 4 and 8],
    [`stride64_5`], [Five pages spaced 64 VPNs apart], [Evictions below 8 ways, then five initial walks],
    [`stride64_hot_pair_5`], [Two hot pages and three competitors spaced 64 VPNs apart], [Policy-dependent walks at 2 and 4 ways],
    [`stride64_two_sets_10`], [Five competing pages in each of two sets], [Evictions in both sets below 8 ways],
    [`different_sets_4`], [Four pages mapping to separate TLB sets], [Four compulsory walks, then TLB hits],
    [`boundaries`], [Unaligned mappings across 4 KiB, 2 MiB, and 1 GiB boundaries], [Mapped accesses succeed with six page faults],
    [`unmapped_access`], [Load outside the mapped range], [Access violation and nonzero exit],
    [`page_pressure`], [15 pages with only 14 physical frames], [15 page faults and physical page replacement],
  )))
}

The `stride64` traces use the same access patterns as the corresponding non-stride traces, but place competing pages 64 VPNs apart so their set index stays the same regardless of the number of TLB sets. For example, VPNs 16 and 80 both map to set 16 with 64 sets (`VPN mod 64`), and both map to set 0 with 8 sets (`VPN mod 8`).

Together, these traces cover first loads / stores, page reuse, TLB set conflicts, replacement and eviction, page-table boundaries, physical-memory exhaustion, and invalid memory accesses. Their mix of loads and stores tests both normal translation and fault handling. The exact operations in each trace are included in our submission for your reference. 

== Testing

#block(breakable: false)[
We ran the original traces with no TLB and with our default TLB, modeled on the Skylake L1 data TLB for 4 KiB pages. It has 16 sets and four ways, for 64 entries, and uses exact LRU replacement. For the configuration sweep, we held the TLB at 64 entries and varied associativity across one, two, four, and eight ways. This gives 64, 32, 16, and 8 sets, respectively. We ran exact LRU, bit-PLRU, round robin, and random replacement on the fixed-capacity conflict traces.
]

= Results

#figure(
  image("figures/translation-reference-cost.svg", width: 90%),
) <fig-translation-cost>

#figure(
  image("figures/overall-reference-breakdown.svg", width: 90%),
) <fig-overall-summary>

#figure(
  image("figures/fixed64-walks-vs-associativity.svg", width: 90%),
) <fig-associativity>

#figure(
  image("figures/fixed64-policy-at-four-ways.svg", width: 90%),
) <fig-policy>

#figure(
  image("figures/fixed64-policy-across-ways.svg", width: 90%),
) <fig-policy-ways>

#pagebreak()

= Discussion

We preface our results with the fact that our data probably doesn't generalize to real world workloads, the use of arithmetic mean to get the speedup in the performance summary isn't representative of the frequency at which these traces occur in everyday use for different people, but is just what we observed while collecting data. The full per-trace data can be referred to in the appendix.

== Performance Summary

To answer our first question, we ran the VM system with and without a TLB. In our model, a TLB hit counts as one memory reference for the program's load or store. A TLB miss counts as five memory references, which are composed of: the program's reference + four references to walk the four-level page table. Figure 1 plots *total modeled references divided by the number of program accesses* (loads and stores). Trivially, we see that without a TLB, every access requires five references based on our model. On the other hand, TLB measurements vary per trace. For example, `hot_page` falls to 1.02 references per access and `sequential_12` falls to 1.5 because later accesses reuse cached translations. The `cold_stream` and `page_pressure` traces remain at five because each page is accessed only once so a cache doesn't help. We chose this subset to contrast reuse within one page, reuse across pages and TLB sets, and one-time streaming accesses.

Figure 2 shows the counts behind this result. With the default TLB, `hot_page` makes 192 loads and stores but adds only four modeled page-table references. In contrast, `two_sets_10` makes 384 loads and stores and adds 784 page-table references because its translations keep competing within two sets. Together, figures 1 and 2 show that the TLB helps most when later accesses reuse translations. When page-table walks remain frequent, the translation work can exceed the program's own memory accesses. Across our ten successful original traces, the arithmetic mean reduction in page-table walks was 60.0%, and the arithmetic mean modeled speedup was 2.71$times$. 

== Design Space Exploration

To answer our second question, we varied TLB associativity while holding the TLB at 64 entries. As we increased the ways from one to eight, the number of sets fell from 64 to eight. We chose this comparison because more ways can reduce set conflicts without adding TLB entries, although they still need more tag comparison and replacement logic. Figure 3 shows that page-table walks decrease as more ways let competing pages fit in the same TLB set. In `stride64_4` every memory access at one and two way associativity leads to many page table walks, whereas at four and eight way associativity, only four page table walks are needed. The five-page traces exhibit this same general trend, and so we can say that Page-table walks decrease as associativity increases because each TLB set can hold more of the pages competing for it.

To isolate the effect of eviction policy, we held the TLB at 64 entries and four ways across our three conflict traces. Random produced the fewest walks on all three. For example, on `stride64_hot_pair_5`, random caused 116 walks, compared with 192 for exact LRU and 240 for round robin. Interestingly enough, random performed better than the well-known exact LRU and round robin policies on these traces. This is likely because our traces repeatedly access slightly more pages than a TLB set can hold, such as five pages competing for a four-way set. On these traces, giving up precise tracking of page-level locality seems less costly than it might be in a data or instruction cache, where reuse occurs at the finer granularity of cache lines. Random is also simple to implement in hardware, making it a useful policy to explore, and was something we were curious about when exploring aspects of the design space here.

= Conclusion

In conclusion, based on the speedup delivered on our set of traces, we see that the TLB is crucial for address translation during loads and stores. We would recommend the following configurations for these workloads:

- *Fewer page-table walks:* We'd recommend a 64-entry, 8-way TLB for workloads like our conflict traces, to ensure as many competing pages as possible fit in the same TLB set.
- *Simpler design:* We'd recommend a 64-entry, 4-way TLB with random replacement. Random produced the fewest walks across our three policy traces at four ways and does not need to track the full LRU order.

#pagebreak()

= Appendix

== Original Traces: No TLB vs Default TLB

`unmapped_access` is omitted because its expected access violation occurs before the driver prints counters.

#{
  set text(size: 8pt)
  let rows = csv("default_tlb_comparison.csv")
  table(
    columns: (1.6fr, 0.65fr, 0.6fr, 0.65fr, 0.8fr, 0.7fr, 0.75fr, 0.7fr, 0.65fr),
    inset: (x: 3pt, y: 3pt),
    stroke: 0.4pt,
    align: left,
    table.header([Trace], [Accesses], [Faults], [TLB hits], [No-TLB walks], [TLB walks], [No-TLB refs], [TLB refs], [Modeled speedup]),
    ..rows.flatten().map(cell => [#cell]),
  )
}

#pagebreak()

== Fixed-Capacity Sweep

#{
  set text(size: 7.5pt)
  let rows = csv("fixed_capacity_appendix.csv")
  table(
    columns: (1.8fr, 0.5fr, 0.5fr, 0.95fr, 0.75fr, 0.75fr, 0.8fr, 0.65fr),
    inset: (x: 3pt, y: 2pt),
    stroke: 0.4pt,
    align: left,
    table.header([Trace], [Sets], [Ways], [Policy], [Accesses], [TLB hits], [Page faults], [Walks]),
    ..rows.flatten().map(cell => [#cell]),
  )
}
