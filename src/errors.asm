; errors.asm
;
; Purpose:
;   Error reporting helpers.
;
; Module scope:
;   Centralize stable human-readable error strings and make exit-code behavior auditable.
;
; Next implementation step:
;   Sprint 1: add user-facing messages for file, ELF, malformed, unsupported, and bounds failures.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_errors_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_errors_placeholder:
    ret
