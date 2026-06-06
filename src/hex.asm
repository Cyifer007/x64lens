; hex.asm
;
; Purpose:
;   Future hexadecimal formatting helpers for addresses, offsets, sizes, and
;   raw gadget bytes. Keeping formatting separate from print.asm prevents
;   report emitters from duplicating conversion logic.
;
; Next implementation step:
;   Sprint 1 or Sprint 2 can add print_hex64 once ELF metadata output needs
;   stable address formatting.

bits 64
default rel

section .text
global x64lens_hex_placeholder

; Placeholder symbol so the module participates in the build graph.
x64lens_hex_placeholder:
    ret
