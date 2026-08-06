; candidate_role.asm
;
; Purpose:
;   Materialize the Sprint 13 private additive register-role facet for exact
;   single-pop candidates.
;
; Module scope:
;   Consume existing gadget records and populate one dense 8-byte
;   candidate_role_record per candidate.  The role mask distinguishes generic
;   non-RSP register control, System V call-argument positions, and Linux
;   syscall-argument positions.  It does not change semantic classes, scores,
;   public output, schema fields, candidate counts, or ordering.
;
; Public symbols:
;   x64lens_candidate_role_from_exact
;
; Safety:
;   The candidate count and capacity are checked before iteration.  Exact-pop
;   structural metadata is reconciled with the pattern ID.  Contradictory
;   internal facts return EXIT_BOUNDS before report emission.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .rodata
; Pattern IDs 3 through 18 are ordered RAX, RCX, RDX, RBX, RSP, RBP, RSI,
; RDI, R8, R9, R10, R11, R12, R13, R14, R15.
pop_pattern_reg_ids:
    db REG_RAX_BIT, REG_RCX_BIT, REG_RDX_BIT, REG_RBX_BIT
    db REG_RSP_BIT, REG_RBP_BIT, REG_RSI_BIT, REG_RDI_BIT
    db REG_R8_BIT, REG_R9_BIT, REG_R10_BIT, REG_R11_BIT
    db REG_R12_BIT, REG_R13_BIT, REG_R14_BIT, REG_R15_BIT

pop_pattern_role_masks:
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG4
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG3 | CANDIDATE_ROLE_SYSCALL_ARG3
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq 0
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG2 | CANDIDATE_ROLE_SYSCALL_ARG2
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG1 | CANDIDATE_ROLE_SYSCALL_ARG1
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG5 | CANDIDATE_ROLE_SYSCALL_ARG5
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG6 | CANDIDATE_ROLE_SYSCALL_ARG6
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSCALL_ARG4
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dq CANDIDATE_ROLE_GENERIC_CONTROL

section .text
global x64lens_candidate_role_from_exact

; x64lens_candidate_role_from_exact(gadget_summary=rdi,
;                                    gadget_records=rsi,
;                                    role_records=rdx) -> rax=status
x64lens_candidate_role_from_exact:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    test    rdi, rdi
    jz      .bounds_error
    test    rsi, rsi
    jz      .bounds_error
    test    rdx, rdx
    jz      .bounds_error

    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     rax, [r12 + GADGET_SUMMARY_COUNT]
    cmp     rax, [r12 + GADGET_SUMMARY_CAPACITY]
    ja      .bounds_error
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds_error

    xor     r15d, r15d
.loop:
    cmp     r15, [r12 + GADGET_SUMMARY_COUNT]
    jae     .success

    mov     rax, r15
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     rbx, [r13 + rax]
    mov     qword [r14 + r15 * CANDIDATE_ROLE_RECORD_SIZE + CANDIDATE_ROLE_MASK], 0

    mov     eax, [rbx + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_POP_RAX_RET
    jb      .next
    cmp     eax, PATTERN_POP_R15_RET
    ja      .next

    mov     ecx, eax
    sub     ecx, PATTERN_POP_RAX_RET
    lea     r8, [rel pop_pattern_reg_ids]
    movzx   edx, byte [r8 + rcx]
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     dword [rbx + GADGET_PATTERN_REG_COUNT], 1
    jne     .bounds_error
    mov     eax, [rbx + GADGET_PATTERN_REG_ORDER]
    test    eax, 0xfffffff0
    jne     .bounds_error
    cmp     eax, edx
    jne     .bounds_error

    lea     r8, [rel pop_pattern_role_masks]
    mov     rax, [r8 + rcx * 8]
    mov     rdx, CANDIDATE_ROLE_MASK_ALLOWED
    not     rdx
    and     rdx, rax
    jnz     .bounds_error
    mov     [r14 + r15 * CANDIDATE_ROLE_RECORD_SIZE + CANDIDATE_ROLE_MASK], rax

.next:
    inc     r15
    jmp     .loop

.success:
    xor     eax, eax
    jmp     .done
.bounds_error:
    mov     eax, EXIT_BOUNDS
.done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
