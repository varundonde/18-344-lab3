#include "tlb.h"
#include "vm-util.h"
#include <cstdlib>

TLB::TLB()
{
}

bool TLB::lookup(unsigned long addr, unsigned long &PPN){
 
  //find VPN and set
  unsigned long vpn = addr >> TLB_OFFSET_LEN;
  Set &set = sets[vpn & TLB_INDEX_MASK];
 
  //search for VPN, return false if miss
  Set::iterator hit = set.find(vpn);
  if (hit == set.end()) {
    return false;
  }
 
  //if hit, update replacement policy values
  hit->second.last_used = ++time;                               
  hit->second.used = true;
  bool all_used = (set.size() == TLB_WAYS);
  for (Set::iterator it = set.begin(); it != set.end(); ++it) {
    if (!it->second.used) all_used = false;
  }
  if (all_used) {
    for (Set::iterator it = set.begin(); it != set.end(); ++it) {
      if (it != hit) it->second.used = false;
    }
  }
  
  //return PPN and true to acknowledge tlb hit
  PPN = hit->second.ppn;
  return true;
 
}

void TLB::update(unsigned long addr, unsigned long new_PPN){
  
  /*TODO: Implement a TLB update here using the 
          virtual address and new PPN*/
  return;

}
