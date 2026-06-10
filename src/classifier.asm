; classifier.asm
;
; Purpose:
;   Semantic primitive classifier for x64lens gadget candidates.
;
; Module scope:
;   Consume exact pattern IDs assigned by patterns.asm and populate semantic
;   primitive facts in gadget_record structures: semantic class, controlled
;   register bitmap, stack delta, and minimal side-effect flags. This module
;   does not scan bytes, parse ELF data, score gadgets, print reports, or claim
;   exploitability.
;
; Sprint 4 scope:
;   Map the Sprint 3 exact suffix patterns into conservative semantic classes.
;   This is still not full instruction decoding. A semantic label here means
;   the exact suffix pattern is meaningful enough for first-pass primitive
;   coverage, not that the entire raw candidate window was decoded.
;
; Safety model:
;   Candidate records and exact pattern IDs are produced only after parser,
;   executable-region, scanner, and pattern bounds checks. The only direct file
;   read performed here is the imm16 value for an already validated ret imm16
;   terminator.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_classifier_apply_exact

%macro CLEAR_SUMMARY_QWORD 1
    mov     qword [r13 + %1], 0
%endmacro

%macro MARK_UNKNOWN 0
    inc     qword [r13 + GADGET_SUMMARY_UNKNOWN_COUNT]
    jmp     .next_candidate
%endmacro

%macro CLASSIFY_NO_REG 4
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], %1
    mov     qword [r15 + GADGET_STACK_DELTA], %2
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], %3
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + %4]
    jmp     .next_candidate
%endmacro

%macro CLASSIFY_REG 5
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], %1
    mov     rax, (1 << %2)
    mov     qword [r15 + GADGET_REGS_CONTROLLED], rax
    or      qword [r13 + GADGET_SUMMARY_REGS_CONTROLLED], rax
    mov     qword [r15 + GADGET_STACK_DELTA], %3
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], %4
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + %5]
    jmp     .next_candidate
%endmacro

; x64lens_classifier_apply_exact(gadget_summary=rdi, gadget_records=rsi,
;                                mapped_base=rdx) -> rax=status
;
; Inputs:
;   RDI = writable gadget_summary record
;   RSI = writable gadget_record[] buffer
;   RDX = mapped target file base, used only for ret imm16 stack delta
;
; Output:
;   RAX = EXIT_OK
;
; Clobbers:
;   Caller-saved registers plus semantic fields in gadget_record[] and
;   semantic summary fields in gadget_summary.
x64lens_classifier_apply_exact:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     r13, rdi            ; gadget_summary pointer
    mov     r12, rsi            ; gadget_record[] pointer
    mov     r14, rdx            ; mapped file base

    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_SEMANTIC_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_UNKNOWN_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_ARG_CONTROL_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_SYSCALL_NUM_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_STACK_PIVOT_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_ALIGNMENT_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_REGS_CONTROLLED

    xor     rbp, rbp            ; candidate index
.candidate_loop:
    cmp     rbp, [r13 + GADGET_SUMMARY_COUNT]
    jae     .ok

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r15, [r12 + rax]    ; current gadget_record pointer

    ; Reset semantic fields so classifier output is deterministic even if this
    ; routine is called more than once over the same record array.
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_UNKNOWN_CANDIDATE
    mov     qword [r15 + GADGET_REGS_CONTROLLED], 0
    mov     qword [r15 + GADGET_REGS_CLOBBERED], 0
    mov     qword [r15 + GADGET_STACK_DELTA], 0
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], 0

    mov     eax, [r15 + GADGET_PATTERN_ID]

    cmp     eax, PATTERN_RET
    je      .class_ret
    cmp     eax, PATTERN_RET_IMM16
    je      .class_ret_imm16

    cmp     eax, PATTERN_POP_RDI_RET
    je      .class_pop_rdi_arg
    cmp     eax, PATTERN_POP_RSI_RET
    je      .class_pop_rsi_arg
    cmp     eax, PATTERN_POP_RDX_RET
    je      .class_pop_rdx_arg
    cmp     eax, PATTERN_POP_RCX_RET
    je      .class_pop_rcx_arg
    cmp     eax, PATTERN_POP_R8_RET
    je      .class_pop_r8_arg
    cmp     eax, PATTERN_POP_R9_RET
    je      .class_pop_r9_arg

    cmp     eax, PATTERN_POP_RAX_RET
    je      .class_pop_rax_syscall_num
    cmp     eax, PATTERN_SYSCALL_RET
    je      .class_syscall_trigger
    cmp     eax, PATTERN_LEAVE_RET
    je      .class_leave_pivot
    cmp     eax, PATTERN_POP_RSP_RET
    je      .class_pop_rsp_pivot

    ; Conservative default: known exact patterns that are not yet mapped to a
    ; semantic primitive remain unknown_candidate for Sprint 4 metrics.
    MARK_UNKNOWN

.class_ret:
    CLASSIFY_NO_REG SEM_ALIGNMENT, STACK_DELTA_RET, SIDE_EFFECT_NONE, GADGET_SUMMARY_ALIGNMENT_COUNT

.class_ret_imm16:
    ; ret imm16 stack effect is pop return address plus immediate stack adjust.
    ; scanner.asm already verified the three-byte terminator is inside the
    ; executable file-backed region before this reads the little-endian imm16.
    mov     rbx, [r15 + GADGET_FILE_OFFSET]
    movzx   eax, word [r14 + rbx + 1]
    add     rax, STACK_DELTA_RET
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    mov     qword [r15 + GADGET_STACK_DELTA], rax
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_RET_IMM16
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_ALIGNMENT_COUNT]
    jmp     .next_candidate

.class_pop_rdi_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_RDI_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT
.class_pop_rsi_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_RSI_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT
.class_pop_rdx_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_RDX_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT
.class_pop_rcx_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_RCX_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT
.class_pop_r8_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_R8_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT
.class_pop_r9_arg:
    CLASSIFY_REG SEM_ARG_CONTROL, REG_R9_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ARG_CONTROL_COUNT

.class_pop_rax_syscall_num:
    CLASSIFY_REG SEM_SYSCALL_NUM_CONTROL, REG_RAX_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_SYSCALL_NUM_COUNT

.class_syscall_trigger:
    CLASSIFY_NO_REG SEM_SYSCALL_TRIGGER, STACK_DELTA_RET, SIDE_EFFECT_SYSCALL, GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT

.class_leave_pivot:
    ; leave; ret derives the stack pointer from RBP and then returns through the
    ; pivoted stack. The exact delta is input-dependent, so stack_delta stays 0.
    CLASSIFY_REG SEM_STACK_PIVOT, REG_RSP_BIT, STACK_DELTA_UNKNOWN, SIDE_EFFECT_STACK_PIVOT, GADGET_SUMMARY_STACK_PIVOT_COUNT

.class_pop_rsp_pivot:
    ; pop rsp; ret overwrites RSP and makes the following ret target depend on
    ; the new stack. Treat the stack delta as unknown for Sprint 4.
    CLASSIFY_REG SEM_STACK_PIVOT, REG_RSP_BIT, STACK_DELTA_UNKNOWN, SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT, GADGET_SUMMARY_STACK_PIVOT_COUNT

.next_candidate:
    inc     rbp
    jmp     .candidate_loop

.ok:
    xor     rax, rax
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
