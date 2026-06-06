; regions.asm
;
; Purpose:
;   Executable region model.
;
; Module scope:
;   Represent executable byte ranges derived primarily from PT_LOAD segments with PF_X set.
;
; Next implementation step:
;   Sprint 2: build region records that scanner.asm can consume.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_regions_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_regions_placeholder:
    ret
