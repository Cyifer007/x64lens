/*
 * minimal.c
 *
 * Purpose:
 *   Small valid ELF64 test program for Sprint 1 parser validation. This is
 *   not a vulnerability sample. It simply provides a reproducible binary
 *   that x64lens can identify as ELF64 x86_64 after compilation.
 */

#include <stdio.h>

int main(void) {
    puts("x64lens minimal test binary");
    return 0;
}
