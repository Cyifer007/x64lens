; patterns.asm
;
; Purpose:
;   Opcode template matcher.
;
; Module scope:
;   Match candidate windows against known useful x86_64 byte templates without pretending to be a full decoder.
;
; Next implementation step:
;   Sprint 3/4: implement exact patterns such as pop rdi; ret and leave; ret.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_patterns_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_patterns_placeholder:
    ret
