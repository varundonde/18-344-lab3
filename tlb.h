#pragma once

#include <map>

/* Your TLB should be modeled after the
 * Intel Skylake DATA TLB L1 with the following
 * parameters
*/
#define TLB_SET             16
#define TLB_OFFSET_LEN      12
#define TLB_INDEX_LEN       4
#define TLB_INDEX_MASK      0xF

//If no associativity defined, default to 4-way
#ifndef TLB_WAYS
#define TLB_WAYS            4
#endif

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
  TLB() : time(0) {}                           //init with empty set @ time = 0
  bool lookup(unsigned long addr, unsigned long & PPN);   //lookup fn
  void update(unsigned long addr, unsigned long new_PPN); //update fn

};
