# Toy corpus build contract
#
# Purpose:
#   Build small reproducible ELF64 binaries for parser, mitigation, and
#   gadget scanner validation. These binaries are generated artifacts and
#   should not be treated as source-of-truth documentation.

CC ?= gcc

.PHONY: all clean

all: minimal_nopie minimal_pie_canary minimal_execstack gadgets gadgets_sprint10 gadgets_sprint10_transfer gadgets_capacity_exact gadgets_capacity

minimal_nopie: minimal.c
	$(CC) -no-pie -fno-stack-protector -z noexecstack -o $@ $<

minimal_pie_canary: minimal.c
	$(CC) -fPIE -pie -fstack-protector-all -Wl,-z,relro,-z,now -z noexecstack -o $@ $<

minimal_execstack: minimal.c
	$(CC) -no-pie -fno-stack-protector -z execstack -o $@ $<

gadgets: gadgets.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

gadgets_sprint10: gadgets_sprint10.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

gadgets_sprint10_transfer: gadgets_sprint10_transfer.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

gadgets_capacity_exact: gadgets_capacity_exact.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

gadgets_capacity: gadgets_capacity.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

clean:
	rm -f minimal_nopie minimal_pie_canary minimal_execstack gadgets gadgets_sprint10 gadgets_sprint10_transfer gadgets_capacity_exact gadgets_capacity
