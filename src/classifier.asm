; classifier.asm
;
; Purpose:
;   Semantic primitive classifier.
;
; Module scope:
;   Map pattern matches to semantic classes such as arg_control, stack_pivot, syscall_trigger, and memory_write.
;
; Next implementation step:
;   Sprint 4: emit primitive classes and register bitmaps.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_classifier_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_classifier_placeholder:
    ret
