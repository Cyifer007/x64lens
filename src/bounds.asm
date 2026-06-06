; bounds.asm
;
; Purpose:
;   Bounds-check helpers.
;
; Module scope:
;   Validate file offsets, sizes, pointer ranges, and overflow-sensitive arithmetic before parser modules read target bytes.
;
; Next implementation step:
;   Sprint 1: implement file-size and offset+size validation routines.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_bounds_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_bounds_placeholder:
    ret
