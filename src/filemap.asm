; filemap.asm
;
; Purpose:
;   File mapping helpers.
;
; Module scope:
;   Open a target path read-only, fstat it, mmap it, and provide a small mapped-file record to analysis modules.
;
; Next implementation step:
;   Sprint 1: implement openat/fstat/mmap/munmap/close orchestration.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_filemap_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_filemap_placeholder:
    ret
