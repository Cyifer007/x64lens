; scoring.asm
;
; Purpose:
;   Gadget scoring engine.
;
; Module scope:
;   Consume semantic primitive facts produced by classifier.asm and populate
;   the score field in each gadget_record. This module does not parse files,
;   scan bytes, assign semantic classes, or print reports.
;
; Sprint 5 scope:
;   Apply the first conservative exact-suffix score model. Scores are assigned
;   only when the classifier has justified a semantic class. Unknown candidates
;   remain unscored with score 0 and are not included in scored_candidate_count.
;
; Scoring policy:
;   The current scanner is exact-suffix based, not a full x86_64 decoder. The
;   first score table therefore includes a small uncertainty penalty compared
;   with the documented semantic base values. Future decoder-backed scoring can
;   reduce that penalty for fully decoded instruction sequences.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_scoring_apply

%macro SET_SCORE 1
    mov     dword [r15 + GADGET_SCORE], %1
    inc     qword [r13 + GADGET_SUMMARY_SCORED_COUNT]
    jmp     .next_candidate
%endmacro

; x64lens_scoring_apply(gadget_summary=rdi, gadget_records=rsi) -> rax=status
;
; Inputs:
;   RDI = writable gadget_summary record
;   RSI = writable gadget_record[] buffer
;
; Output:
;   RAX = EXIT_OK
;
; Clobbers:
;   Caller-saved registers plus GADGET_SCORE fields and
;   GADGET_SUMMARY_SCORED_COUNT.
x64lens_scoring_apply:
    push    rbp
    push    r12
    push    r13
    push    r15

    mov     r13, rdi            ; gadget_summary pointer
    mov     r12, rsi            ; gadget_record[] pointer

    mov     qword [r13 + GADGET_SUMMARY_SCORED_COUNT], 0
    xor     rbp, rbp            ; candidate index

.candidate_loop:
    cmp     rbp, [r13 + GADGET_SUMMARY_COUNT]
    jae     .ok

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r15, [r12 + rax]

    ; Deterministic default. A score of 0 means unscored, not low quality.
    mov     dword [r15 + GADGET_SCORE], 0

    mov     eax, [r15 + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_UNKNOWN_CANDIDATE
    je      .next_candidate

    ; Pattern-specific scores preserve useful distinctions within a semantic
    ; class, such as leave-ret versus pop-rsp-ret stack pivots.
    mov     eax, [r15 + GADGET_PATTERN_ID]

    cmp     eax, PATTERN_POP_RDI_RET
    je      .score_arg_control
    cmp     eax, PATTERN_POP_RSI_RET
    je      .score_arg_control
    cmp     eax, PATTERN_POP_RDX_RET
    je      .score_arg_control
    cmp     eax, PATTERN_POP_RCX_RET
    je      .score_arg_control
    cmp     eax, PATTERN_POP_R8_RET
    je      .score_arg_control
    cmp     eax, PATTERN_POP_R9_RET
    je      .score_arg_control

    cmp     eax, PATTERN_POP_RAX_RET
    je      .score_syscall_num
    cmp     eax, PATTERN_SYSCALL_RET
    je      .score_syscall_trigger
    cmp     eax, PATTERN_LEAVE_RET
    je      .score_leave_pivot
    cmp     eax, PATTERN_POP_RSP_RET
    je      .score_pop_rsp_pivot
    cmp     eax, PATTERN_RET
    je      .score_ret_alignment
    cmp     eax, PATTERN_RET_IMM16
    je      .score_ret_imm_alignment

    ; A classified future pattern without a score table entry remains unscored
    ; until the scoring model explicitly handles it.
    jmp     .next_candidate

.score_arg_control:
    SET_SCORE 90
.score_syscall_num:
    SET_SCORE 85
.score_syscall_trigger:
    SET_SCORE 85
.score_leave_pivot:
    SET_SCORE 75
.score_pop_rsp_pivot:
    SET_SCORE 70
.score_ret_alignment:
    SET_SCORE 45
.score_ret_imm_alignment:
    SET_SCORE 40

.next_candidate:
    inc     rbp
    jmp     .candidate_loop

.ok:
    xor     rax, rax
    pop     r15
    pop     r13
    pop     r12
    pop     rbp
    ret
