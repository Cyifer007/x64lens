; report_json.asm
;
; Purpose:
;   JSON report emitter.
;
; Module scope:
;   Render versioned machine-readable output for benchmarks, CI/CD, dashboards, and future enterprise integrations.
;
; Next implementation step:
;   Sprint 5: emit schema-versioned JSON.
;
; Contract:
;   Keep this module focused. Do not mix CLI parsing, reporting, and
;   analysis policy into low-level parsing or scanning helpers.

bits 64
default rel

section .text
global x64lens_report_json_placeholder

; Placeholder symbol so the module assembles before its real routines exist.
; Remove this only when the first real exported routine is implemented.
x64lens_report_json_placeholder:
    ret
