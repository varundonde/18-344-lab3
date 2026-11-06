#pragma once

#include "pte-util.h"

class pageTableEntry;
class pageTable{

private:
  size_t pageTableIndexBits; /*in bits*/
  size_t pageTableSize; /*in entries*/
  size_t pageTableOffsetBits; 

  /*Number of levels of page tables, i.e., 4levels */
  size_t levels;

  PTE *table;

  unsigned getEntryIdFromAddr(unsigned long,size_t);

public:
  pageTable();
  PTE getEntry(unsigned long,size_t);
  PTE getEntryDirect(unsigned long);
  PTE createEntry(unsigned long,size_t);

};
