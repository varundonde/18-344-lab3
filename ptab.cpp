#include <assert.h>
#include <iostream>
#include <limits>
#include <stdlib.h>
#include <string.h>

#include "ptab.h"
#include "pte.h"
#include "pte-util.h"
#include "vm-util.h"

pageTable::pageTable(){

  /*Core i7 has 9 bits worth of entries per page table*/
  pageTableIndexBits = VM_PTABBITS;  

  /*Core i7 has 512 entries per page table*/
  pageTableSize = 1 << VM_PTABBITS; 

  /*Core i7 has 4 levels of PTs each with 512 entries*/
  levels = VM_PTABLEVS; 

  /*First level page table gets created and zeroed to start*/
  table = (PTE *)calloc( pageTableSize, sizeof( PTE ) );

}

PTE pageTable::createEntry(unsigned long addr, size_t level){

}

PTE pageTable::getEntryDirect(unsigned long index){
  return table[index];
}

PTE pageTable::getEntry(unsigned long addr, size_t level){
  long index = getEntryIdFromAddr(addr, level);
  // level 4 page table can just directly return the physical address of page
  if (level == 3) {
    return getEntryDirect(index);
  }
  return table[index];
}

/* Input:  unmodified address. 
   Return: level-specific bit field from address that is index into to that level's page table
*/
unsigned pageTable::getEntryIdFromAddr(unsigned long addr, size_t level) {
  // mask out the offset bits
  long non_offset_addr_bits = (addr & VM_PPNMASK) >> VM_PPOBITS;

  // shift right by the ([VM_PTABLEEVS - level] * VM_PTABITS (9))
  // levels in range [0, 3] --> we convert to [1, 4] to extract the right bits
  // [VPN 1, VPN 2, VPN 3, VPN 4] is layed out in this order, so we subtract levels 
  long vpn_bits = non_offset_addr_bits >> ((VM_PTABLEVS - (level + 1)) * VM_PTABBITS); 
  long index_bits = vpn_bits & VM_PTABMASK;
  assert (index_bits <= pageTableSize);
  return index_bits;
}
