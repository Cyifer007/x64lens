; scanner.asm
;
; Purpose:
;   Raw gadget candidate scanner.
;
; Module scope:
;   Walk executable regions, find terminators, and emit bounded byte windows for pattern matching.
;
; Next implementation step:
;   Sprint 3: implement ret/ret-imm scanning with --max-depth support.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_scanner_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_scanner_placeholder:
    ret
