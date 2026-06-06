# Toy corpus build contract
#
# Purpose:
#   Build small reproducible ELF64 binaries for parser, mitigation, and
#   gadget scanner validation. These binaries are generated artifacts and
#   should not be treated as source-of-truth documentation.

CC ?= gcc

.PHONY: all clean

all: minimal_nopie minimal_pie_canary gadgets

minimal_nopie: minimal.c
	$(CC) -no-pie -fno-stack-protector -z noexecstack -o $@ $<

minimal_pie_canary: minimal.c
	$(CC) -fPIE -pie -fstack-protector-all -Wl,-z,relro,-z,now -z noexecstack -o $@ $<

gadgets: gadgets.S
	$(CC) -nostdlib -static -no-pie -o $@ $<

clean:
	rm -f minimal_nopie minimal_pie_canary gadgets
