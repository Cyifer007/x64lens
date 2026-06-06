; report_text.asm
;
; Purpose:
;   Human-readable report emitter.
;
; Module scope:
;   Render stable text output for analysts, professors, and demos.
;
; Next implementation step:
;   Sprint 5: emit summary, mitigations, primitive coverage, and interpretation text.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_report_text_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_report_text_placeholder:
    ret
