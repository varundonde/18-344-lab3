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
  /*TODO: *Extract the PPO from the virtual address
          *Check your TLB for a cached translation if you have a TLB 
          *Starting from the root page table address
          *Traverse the page table to get the Entry for this address 
          *If paged out, handle page fault, add addr to replacement list
          *Update TLB to cache new translation if you have a TLB 
          *Assemble and return physical address
  */
  /*if(...){_tlb_hits++;} Don't forget to update the TLB hit counter*/
  long physical_page_offset = addr & VM_PPOMASK;
  long vpn = addr & VM_PPNMASK;

  _accesses++; /*Don't forget to update the access counter*/
  assert(false && "Abort: vmTranslate not implemented");
  return 0; 
}

void VM::Load(unsigned long addr){
  unsigned long translatedPaddr = vmTranslate(addr);
  std::cerr << "Load[0x" << std::hex << addr <<  "] => [" << translatedPaddr << "]" << std::endl;
}


void VM::Store(unsigned long addr){
  unsigned long translatedPaddr = vmTranslate(addr);
  std::cerr << "Store[0x" << std::hex << addr << "] => [" << translatedPaddr << "]" << std::endl;
}
