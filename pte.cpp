#include "pte.h"

pageTableEntry::pageTableEntry(unsigned long phys){

  /*Set the PPN of this PTE to the physical address phys*/
  ppn = phys;

}
