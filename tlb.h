#pragma once

/* Your TLB should be modeled after the
 * Intel Skylake DATA TLB L1 with the following
 * parameters
*/
#define TLB_SET             16
#define TLB_OFFSET_LEN      12
#define TLB_INDEX_LEN       4
#define TLB_INDEX_MASK      0xF

class TLB
{
private:

public:
  TLB();
  bool lookup(unsigned long addr, unsigned long & PPN);
  void update(unsigned long addr, unsigned long new_PPN);

};
