; analysis_summary.asm
;
; Purpose:
;   Construct fixed-size report-identity and analysis-completeness facts after
;   the shared gadget-analysis pipeline has completed successfully.
;
; Sprint role:
;   Sprint 9 Patch 040 foundation for schema 0.2.0. Candidate provenance and
;   decoder facts remain separate future side-car records keyed by candidate
;   index; this module does not classify, score, decode, or emit output.
;
; Export:
;   x64lens_analysis_summary_mark_complete(summary, command, max_depth,
;                                           phdr_summary, gadget_summary)
;
; Safety assumptions:
;   Callers pass repository-owned fixed-size records after scanner, pattern,
;   classifier, scoring, and annotation stages have returned success. Internal
;   count contradictions fail with EXIT_BOUNDS before either reporter runs.
;
; Current completeness contract:
;   Emitted reports are complete. Candidate-capacity exhaustion remains a
;   fail-closed EXIT_UNSUPPORTED path with empty stdout, so dropped-candidate
;   count is not guessed on that path.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_analysis_summary_mark_complete

; x64lens_analysis_summary_mark_complete(
;     summary=rdi,
;     command_id=rsi,
;     max_depth=rdx,
;     phdr_summary=rcx,
;     gadget_summary=r8) -> rax=status
;
; Clobbers: RAX, R9, R10
x64lens_analysis_summary_mark_complete:
    test    rdi, rdi
    jz      .bounds_failure
    test    rcx, rcx
    jz      .bounds_failure
    test    r8, r8
    jz      .bounds_failure

    cmp     rsi, REPORT_COMMAND_GADGETS
    je      .command_ok
    cmp     rsi, REPORT_COMMAND_ANALYZE
    jne     .bounds_failure
.command_ok:
    test    rdx, rdx
    jz      .bounds_failure
    cmp     rdx, GADGET_MAX_DEPTH_LIMIT
    ja      .bounds_failure

    cmp     rdx, [r8 + GADGET_SUMMARY_MAX_DEPTH]
    jne     .bounds_failure

    mov     r9, [r8 + GADGET_SUMMARY_CAPACITY]
    test    r9, r9
    jz      .bounds_failure
    mov     r10, [r8 + GADGET_SUMMARY_COUNT]
    cmp     r10, r9
    ja      .bounds_failure

    mov     rax, [rcx + PHDR_SUMMARY_EXEC_COUNT]
    cmp     rax, EXEC_REGION_MAX
    ja      .bounds_failure

    mov     qword [rdi + ANALYSIS_SUMMARY_REPORT_TYPE], REPORT_TYPE_ANALYSIS
    mov     [rdi + ANALYSIS_SUMMARY_COMMAND], rsi
    mov     [rdi + ANALYSIS_SUMMARY_MAX_DEPTH], rdx
    mov     [rdi + ANALYSIS_SUMMARY_CANDIDATE_CAPACITY], r9
    mov     [rdi + ANALYSIS_SUMMARY_CANDIDATE_COUNT], r10
    mov     qword [rdi + ANALYSIS_SUMMARY_CANDIDATE_TRUNCATED], 0
    mov     qword [rdi + ANALYSIS_SUMMARY_DROPPED_COUNT], 0
    mov     qword [rdi + ANALYSIS_SUMMARY_DROPPED_COUNT_KNOWN], 1

    mov     [rdi + ANALYSIS_SUMMARY_REGIONS_SCANNED], rax
    mov     [rdi + ANALYSIS_SUMMARY_REGIONS_TOTAL], rax
    mov     qword [rdi + ANALYSIS_SUMMARY_COMPLETE], 1

    xor     rax, rax
    ret

.bounds_failure:
    mov     rax, EXIT_BOUNDS
    ret
