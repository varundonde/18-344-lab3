#include "vm.h"
#include "vm-util.h"
#include "pte-util.h"
#include "pte.h"
#include "ptab.h"
#include "tlb.h"

#include <assert.h>
#include <iostream>
#include <limits>
#include <stdlib.h>
#include <string.h>

VM *vm;

/*
 * Task:
 * Implement vmPageFault Handler.
 *
 * Arguments:
 * pageTableEntry *pte from pte.h
 *
 * Requires: 
 * bumpAllocate() from vm-provided.cpp
 *    [returns allocated physical address or 0x0 if must replace page]
 * replacePage() from vm-provided.cpp
 *    [returns physical address of page after replacement]
 *
 * Behavior:
 * Update physical page number in pte to one returned by allocation or
 * replacement
 */
void VM::vmPageFaultHandler(pageTableEntry *pte){

  /*TODO: Attempt to allocate a new physical page
          If all physical pages are occupied, replace
          a page.
          Update the PTE to store the new translation
  */
  _page_faults++; /*Don't forget to update the page fault counter*/
  assert(false && "vmPageFaultHandler not implemented");
}

/*
 * Task:
 * Implement vmMap
 *
 * Arguments: 
 * vaddr - virtual address to map
 * size - number of bytes in region to map
 *
 * Requires:
 * VM_PPOBITS - number of bits in the physical page offset 
 *
 * Behavior:
 * Updates the page table to include a mappings
 * for size bytes at address vaddr (which may require
 * mapping multiple pages)
 * 
 */
void VM::vmMap(unsigned long vaddr, size_t size){

  std::cerr << "[VM: Mapping Region " << std::hex << vaddr << " " << std::dec << size << "B]" << std::endl;

  /*TODO: Compute the number of pages in the region to be mapped
          Create an entry in the page table for each page to be mapped 
  */
  assert(false && "Abort: vmMap() unimplemented");
}

/*
 * Task:
 * Implement vmTranslate
 *
 * Arguments: 
 * vaddr - virtual address to translate 
 *
 * Requires:
 * VM_PPOMASK - physical page offset mask
 * VM_PPOBITS - number of bits in the physical page offset 
 * VM_PAGEDOUT - a page is paged out if its ppn == VM_PAGEDOUT
 * addToReplacementList() - add a replaced page to the replacement list
 *
 * Behavior:
 * Translate the virtual address addr to its corresponding
 * physical address (i.e., using the PPN and PPO), 
 * checking the TLB, if implemented,
 * then checking the page table and handling page faults.
 *
 *
 */
unsigned long VM::vmTranslate(unsigned long addr){
  // extract ppo from virtual address
  unsigned long ppo = addr & VM_PPOMASK;

  /* TODO: 
  * add TLB check for cached translation once we implement TLB
  * if hit : tlb_hits ++ 
   */ 
  
  // traverse from root to get entry for this address
  PTE pte = root;
  for(int level = 0; level < (int) levels; level++){
    pageTable *pt = pte.pt;
    // handle segfault case
    if (pt == NULL) {
      std::cerr << "Unmapped page at address 0x" << std::hex << addr << std::endl;
      std::exit(EXIT_FAILURE);
    }
    pte = pt->getEntry(addr, level);
  }

  // handle segfault case
  pageTableEntry *final_pte = pte.pte;
  if (final_pte == NULL) {
    std::cerr << "Unmapped page table entry at address 0x" << std::hex << addr << std::endl;
    std::exit(EXIT_FAILURE);
  }

  // handle page fault if paged out, add to replacement list
  if (final_pte->ppn == VM_PAGEDOUT) {
    vmPageFaultHandler(final_pte);
    addToReplacementList(addr);

  }
  // TODO: update TLB to cache new translation once we implement TLB

  // assemble and return physical address
  unsigned long phys_addr = (pte.pte->ppn | ppo); 

  _accesses++; /*Don't forget to update the access counter*/
  return phys_addr; 
}

void VM::Load(unsigned long addr){
  unsigned long translatedPaddr = vmTranslate(addr);
  std::cerr << "Load[0x" << std::hex << addr <<  "] => [" << translatedPaddr << "]" << std::endl;
}


void VM::Store(unsigned long addr){
  unsigned long translatedPaddr = vmTranslate(addr);
  std::cerr << "Store[0x" << std::hex << addr << "] => [" << translatedPaddr << "]" << std::endl;
}
