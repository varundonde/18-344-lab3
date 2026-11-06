#include <iostream>
#include "vm.h"


int main(int argc, char *argv[]){

  vm = new VM();
 
  void *p = (void*)0x0; 
  vm->vmMap((unsigned long)p,8192);
  
  std::cerr << "[TEST: OK; page fault]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+0,0xfeefee);
  
  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+0,0xfeefee);

  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+9,0xfeefee);
  
  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+4095,0xfeefee);
  
  std::cerr << "[TEST: OK; page fault]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+4096,0xfeefee);
  
  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+4096,0xfeefee);
  
  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+4097,0xfeefee);
  
  std::cerr << "[TEST: OK; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+5097,0xfeefee);

  /*std::cerr << "[TEST: SEGFAULT; ]" << std::endl;
  vm->pageStoreSingle((unsigned long)p+8193,0xfeefee);*/
  
  p = (void*)0x18000; 
  vm->vmMap((unsigned long)p,65536);
  for(int i = 0; i < 65536; i+=1024){
    vm->pageStoreSingle((unsigned long)p+i,0xfeefee);
  }

  unsigned accesses = vm->getNumAcc();
  unsigned TLB_hits = vm->getNumTlbHit();
  unsigned page_faults = vm->getNumPgFault();

  std::cerr << "[STATS:]" << std::endl;
  std::cerr << "number of virtual memory accesses: " << accesses << std::endl;
  std::cerr << "number of TLB hits: " << TLB_hits << std::endl;
  std::cerr << "number of page faults: " << page_faults << std::endl;

}
