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

== TLB (TODO: Kushal)

The TLB was implemented in a similar configuration to the caches from the previous lab. Each TLB was made of sets containing TLB entries. When the TLB is accessed, the address is shifted and masked in order to find the virtual page number, or VPN. The VPN corresponds to an entry in the TLB.

Each TLB entry contains the VPN's corresponding physical page number (PPN) along with the required information for each replacement policy:
#enum(
  enum.item(1)[Exact LRU: Uses ```last_used``` to find and evict the least recently used victim],
  enum.item(2)[Bit-PLRU: Uses ```used``` to denote recently used entries, this value resets when all entries are used. The first entry not recently used is evicted.],
  enum.item(3)[Round Robin: Uses ```inserted ``` to find and evict that entered the TLB first.]
  enum.item(4)[Random: A random entry is evicted.]
)

The TLB has three functions for its use: ```lookup```, ```udpate```, and ```invalidate```.

```lookup``` takes in an address and checks its VPN in the TLB. On a miss, it will return false; on a hit, it will return true alongside the PPN and update all of the replacement policy information.

```update``` takes in an address and a PPN and creates a new entry in the TLB. It finds the victim based on the replacement policy, erases it, and adds the new entry into the TLB with the VPN, PPN, and replacement policy information.

```invalidate``` takes in an address and erases its entry from the TLB. When a page is evicted from memory, the page translation in the TLB is now invalidated and must be erased.

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
    [`different_sets_4`], [Four pages mapping to separate TLB sets], [Four compulsory walks, then TLB hits],
    [`boundaries`], [Unaligned mappings across 4 KiB, 2 MiB, and 1 GiB boundaries], [Mapped accesses succeed with six page faults],
    [`unmapped_access`], [Load outside the mapped range], [Access violation and nonzero exit],
    [`page_pressure`], [15 pages with only 14 physical frames], [15 page faults and physical page replacement],
  )))
}

Together, these traces cover first loads / stores, page reuse, TLB set conflicts, replacement and eviction, page-table boundaries, physical-memory exhaustion, and invalid memory accesses. Their mix of loads and stores tests both normal translation and fault handling. The exact operations in each trace are included in our submission for your reference. 

== Testing

We ran each trace with no TLB and with our default TLB, modeled on the Skylake L1 data TLB for 4 KiB pages. It has 16 sets and four ways, for 64 entries, and uses exact LRU replacement. We then kept the 16 sets fixed while varying associativity across one, two, and four ways and comparing exact LRU, bit-PLRU, round robin, and random eviction. The results below compare page-table walks and estimated memory-reference costs across these configurations.

= Results

#figure(
  image("figures/walks-vs-associativity.svg", width: 90%),
  caption: [Walk rate on three set-conflict traces as TLB associativity changes.],
) <fig-associativity>

#figure(
  image("figures/policy-at-four-ways.svg", width: 90%),
  caption: [Walk rate by replacement policy at four ways.],
) <fig-policy>

#figure(
  image("figures/policy-across-ways.svg", width: 90%),
  caption: [Walk rate by policy and associativity on the contention traces.],
) <fig-policy-ways>

#figure(
  image("figures/translation-reference-cost.svg", width: 90%),
  caption: [Estimated memory references per access with and without the TLB.],
) <fig-translation-cost>

#figure(
  image("figures/overall-reference-breakdown.svg", width: 90%),
  caption: [Program and translation references with the default TLB.],
) <fig-overall-summary>

= Discussion

= Conclusion
