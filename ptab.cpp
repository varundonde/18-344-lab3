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

  PTE pte;
  pte.pt = (pageTable *)0x0;
  return pte;

}

PTE pageTable::getEntryDirect(unsigned long index){

  return table[index];   

}

PTE pageTable::getEntry(unsigned long addr, size_t level){

  /*TODO: extract the bitfield from the address that corresponds to
          the page table index for this level's page table and return
          the entry in this level's table at that index.

          See also: getEntryIdFromAddr(addr, level)
  */
  PTE pte;
  pte.pt = (pageTable *)0x0; 
  return pte;

}

/* Input:  unmodified address.  
   Return: level-specific bit field from address that is index into 
           to that level's page table
*/
unsigned pageTable::getEntryIdFromAddr(unsigned long addr, size_t level){
 
  /*TODO: Use the level and the size of the page table to figure out which 
          bits from the address to extract and return.  This bit field from
          the address is the index into that level of page table

          A good chec to be sure that you've extracted the bits correctly
          is to have something like the following assertion in your code...
          assert( (addr & mask) <= pageTableSize );
  */

  return 0; 

}
