#include "vm.h"
#include "tlb.h"
#include "ptab.h"
#include "pte.h"
#include <assert.h>
#include <iostream>
#include <limits>
#include <stdlib.h>
#include <string.h>

VM::VM(){

  vmBumpPointer = VM_MINADDR;
  levels = VM_PTABLEVS;
  pageTableIndexBits = VM_PTABBITS;
  memset(inactivePageList,0x0,VM_INACTIVESIZE * sizeof(unsigned long));
  memset(activePageList,0x0,VM_ACTIVESIZE * sizeof(unsigned long));

  root.pt = new pageTable();
  _TLB = new TLB();

  _accesses = 0;
  _tlb_hits = 0;
  _page_faults = 0;
  std::cerr << "done allocating VM and TLB" << std::endl;

}


void VM::pageLoadMulti(unsigned long addr, uint32_t size, uint32_t instId){
  vm->Load(addr);
}

void VM::pageStoreMulti(unsigned long addr, uint32_t size, uint32_t instId){
  vm->Store(addr);
}

void VM::pageLoadSingle(unsigned long addr, uint32_t instId){
  vm->Load(addr);
}

void VM::pageStoreSingle(unsigned long addr, uint32_t instId){
  vm->Store(addr);
}

unsigned long VM::bumpAllocate(){

  unsigned long paddr = 0x0;
  if( vmBumpPointer < VM_PMEMSIZE ){

    paddr = vmBumpPointer;
    vmBumpPointer = vmBumpPointer + VM_PAGESIZE;

    if( vmBumpPointer >= VM_PMEMSIZE ){

      //std::cerr << "[VM: All Physical Memory Paged]" << std::endl;

    }

  }

  //std::cerr << "[VM: Physical Allocation" << std::hex << paddr << " BP=" << vmBumpPointer << "]" << std::endl;

  return paddr;

}

void VM::addToReplacementList(unsigned long addr){

  for(int i = 0; i < VM_INACTIVESIZE; i++){

    if(inactivePageList[i] == 0x0){

      inactivePageList[i] = addr;
      break;

    }

  }

}

std::pair<unsigned long,unsigned long> VM::replacePage(){

  int ind = rand() % VM_INACTIVESIZE;
  for(int i = 0; i < VM_INACTIVESIZE; i++){

    if( inactivePageList[ind] ){

      break;

    } 
    ind = (ind + 1) % VM_INACTIVESIZE;
  }

  unsigned long addr = inactivePageList[ind]; 
  inactivePageList[ind] = 0x0; 

  PTE pte = root;

  for(int i = 0; i < (int) levels; i++){

    pte = pte.pt->getEntry(addr,i);

  }

  unsigned long ret = pte.pte->ppn;
  pte.pte->ppn = VM_PAGEDOUT;

  return std::pair<unsigned long, unsigned long>(addr,ret);
  
}
