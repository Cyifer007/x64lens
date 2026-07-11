; version.asm
;
; Purpose:
;   Prints the tool version and output schema version. Version visibility is
;   required for reproducible benchmarks, enterprise automation, and paper
;   artifact tracking.

bits 64
default rel

%include "constants.inc"

extern print_cstr

section .rodata
version_text:
    db "x64lens ", X64LENS_VERSION, " schema ", X64LENS_SCHEMA, 10, 0

section .text
global version_print

; version_print()
;   Writes the version line to STDOUT.
version_print:
    lea     rdi, [version_text]
    jmp     print_cstr
