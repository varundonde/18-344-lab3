#pragma once

#include <stdlib.h>
#include <stdint.h>
#include <utility>
#include "vm-util.h"
#include "pte-util.h"

class TLB;
class pageTableEntry;
class VM;
extern VM *vm;


class VM{

private:
  unsigned levels;
  unsigned pageTableIndexBits;
  size_t vmBumpPointer;
  unsigned long inactivePageList[VM_INACTIVESIZE];
  unsigned long activePageList[VM_ACTIVESIZE];

  TLB* _TLB;
  unsigned _tlb_hits;
  unsigned _accesses;
  unsigned _page_faults;

public:

  PTE root; 
  VM();
  void pageLoadMulti(unsigned long addr, uint32_t size, uint32_t instId);
  void pageStoreMulti(unsigned long addr, uint32_t size, uint32_t instId);
  void pageLoadSingle(unsigned long addr, uint32_t instId);
  void pageStoreSingle(unsigned long addr, uint32_t instId);
  unsigned long bumpAllocate();
  std::pair<unsigned long,unsigned long> replacePage();
  void addToReplacementList(unsigned long addr);

  unsigned getNumAcc() const { return _accesses; };
  unsigned getNumTlbHit() const { return _tlb_hits; };
  unsigned getNumPgFault() const { return _page_faults; };

  /*TODO: implement these*/
  unsigned long vmTranslate(unsigned long addr);
  void vmMap(unsigned long vaddr, size_t size);
  void vmPageFaultHandler(pageTableEntry*);
  void Load(unsigned long);
  void Store(unsigned long);

};
