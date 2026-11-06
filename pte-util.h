#pragma once
class pageTable;
class pageTableEntry;
typedef union pte_t{

  pageTable *pt;
  pageTableEntry *pte;

} PTE;
