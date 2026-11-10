#include "tlb.h"
#include <cstdlib>

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
  
  //return PPN and true to acknowledge TLB hit
  PPN = hit->second.ppn;
  return true;
 
}

void TLB::update(unsigned long addr, unsigned long new_PPN){
  
  //find VPN and set
  unsigned long vpn = addr >> TLB_OFFSET_LEN;
  Set &set = sets[vpn & TLB_INDEX_MASK];
 
  //if set is full, evict based on the policy
  if (set.size() >= TLB_WAYS) {
    //set victim to first entry
    Set::iterator victim = set.begin();
    
    //random replacement (victim is random)
    if (TLB_POLICY == TLB_RANDOM) {
      std::advance(victim, rand() % set.size());
    
    //bit-PLRU replacement (victim is first not recently used)
    } else if (TLB_POLICY == TLB_BIT_PLRU) {
      for (Set::iterator it = set.begin(); it != set.end(); ++it) {
        if (!it->second.used) { victim = it; break; }
      }
 
    //exact-LRU replacement (victim is least recently used)
    } else if (TLB_POLICY == TLB_EXACT_LRU) {
      for (Set::iterator it = set.begin(); it != set.end(); ++it) {
        if (it->second.last_used < victim->second.last_used) victim = it;
      }
    //round robin replacement (FIFO, evict based on time entered TLB)
    } else if (TLB_POLICY == TLB_ROUND_ROBIN) {
      for (Set::iterator it = set.begin(); it != set.end(); ++it) {
        if (it->second.inserted < victim->second.inserted) victim = it;
      }
    }
    
    //erase victim
    set.erase(victim);
  }
 
  //update TLB with new entry, set all entry values
  Set::iterator e = set.insert(std::make_pair(vpn, Entry())).first;
  e->second.ppn = new_PPN;
  e->second.inserted = e->second.last_used = ++time;
  e->second.used = true;
  bool all_used = (set.size() == TLB_WAYS);
  for (Set::iterator it = set.begin(); it != set.end(); ++it) {
    if (!it->second.used) all_used = false;
  }
  if (all_used) {
    for (Set::iterator it = set.begin(); it != set.end(); ++it) {
      if (it != e) it->second.used = false;
    }
  }
}
