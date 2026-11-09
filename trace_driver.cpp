#include "vm.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "usage: trace_driver EXPANDED_TRACE\n";
    return 2;
  }
  std::ifstream input(argv[1]);
  if (!input) {
    std::cerr << "cannot open trace: " << argv[1] << '\n';
    return 2;
  }
  vm = new VM();
  std::string line;
  unsigned line_number = 0;
  while (std::getline(input, line)) {
    ++line_number;
    std::istringstream fields(line);
    std::string op, extra;
    unsigned long address = 0;
    unsigned long size = 0;
    if (!(fields >> op >> std::hex >> address)) {
      std::cerr << "invalid expanded trace line " << line_number << '\n';
      return 2;
    }
    if (op == "map") {
      if (!(fields >> std::dec >> size) || size == 0 || (fields >> extra)) {
        std::cerr << "invalid map on line " << line_number << '\n';
        return 2;
      }
      vm->vmMap(address, size);
    } else if ((op == "load" || op == "store") && !(fields >> extra)) {
      if (op == "load") vm->pageLoadSingle(address, 0);
      else vm->pageStoreSingle(address, 0);
    } else {
      std::cerr << "invalid operation on line " << line_number << '\n';
      return 2;
    }
  }
  std::cout << "TRACE_STATS accesses=" << vm->getNumAcc()
            << " tlb_hits=" << vm->getNumTlbHit()
            << " page_faults=" << vm->getNumPgFault() << '\n';
}
