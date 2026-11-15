#pragma once

#include <map>

/* By default, model the 64-entry Skylake L1 data TLB for 4 KiB pages.
 * TLB_TOTAL_ENTRIES can be fixed while TLB_WAYS changes for a capacity-
 * controlled associativity sweep. Large-page translations are not modeled.
 */
#define TLB_OFFSET_LEN      12

//If no associativity defined, default to 4-way
#ifndef TLB_WAYS
#define TLB_WAYS            4
#endif

#ifndef TLB_TOTAL_ENTRIES
#define TLB_TOTAL_ENTRIES   (16 * TLB_WAYS)
#endif

#if TLB_WAYS < 1 || TLB_TOTAL_ENTRIES % TLB_WAYS != 0
#error "TLB_WAYS must divide TLB_TOTAL_ENTRIES"
#endif

#define TLB_SET             (TLB_TOTAL_ENTRIES / TLB_WAYS)
#if (TLB_SET & (TLB_SET - 1)) != 0
#error "The number of TLB sets must be a power of two"
#endif
#define TLB_INDEX_MASK      (TLB_SET - 1)

//replacement policies
#define TLB_RANDOM          0
#define TLB_BIT_PLRU        1
#define TLB_EXACT_LRU       2
#define TLB_ROUND_ROBIN     3
 
#ifndef TLB_POLICY
#define TLB_POLICY          TLB_EXACT_LRU
#endif

class TLB
{
private:
  struct Entry {                               //translated TLB entry
    unsigned long ppn;
    unsigned long last_used;                   //time of last hit/insert
    unsigned long inserted;                    //time entry was filled
    bool used;                                 //bit-PLRU most recently used bit
  };

  typedef std::map<unsigned long, Entry> Set;  //One set is a VPN and an entry
 
  Set sets[TLB_SET];                           //TLB
  unsigned long time;                          //time counter, increments on lookup/update

public:
  TLB() : time(0) {}                                      //init with empty set @ time = 0
  bool lookup(unsigned long addr, unsigned long & PPN);   //lookup fn
  void update(unsigned long addr, unsigned long new_PPN); //update fn
  void invalidate(unsigned long addr);

};
