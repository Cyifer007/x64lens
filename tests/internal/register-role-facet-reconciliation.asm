; register-role-facet-reconciliation.asm
;
; Purpose:
;   Executable C-free authority for the Sprint 13 Patch 080 private additive
;   exact-pop register-role side-car.
;
; It validates all 16 exact single-pop pattern masks, the RCX System V argument
; four versus R10 Linux syscall argument four distinction, the RSP exclusion
; from generic register control, and a non-pop zero-role control.  It does not
; validate public reporting or score policy.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_candidate_role_from_exact

global _start

section .rodata
success_msg: db "sprint13-role-facet-smoke: ok roles=16 generic_control=15 sysv_args=6 syscall_args=6 rcx_sysv_arg4=1 r10_syscall_arg4=1 nonpop_zero=1 public_fields_added=0 score_changes=0", 10
success_len: equ $ - success_msg

; pattern_id, register_id, expected_mask
cases:
    dd PATTERN_POP_RAX_RET, REG_RAX_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_RCX_RET, REG_RCX_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG4
    dd PATTERN_POP_RDX_RET, REG_RDX_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG3 | CANDIDATE_ROLE_SYSCALL_ARG3
    dd PATTERN_POP_RBX_RET, REG_RBX_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_RSP_RET, REG_RSP_BIT
    dq 0
    dd PATTERN_POP_RBP_RET, REG_RBP_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_RSI_RET, REG_RSI_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG2 | CANDIDATE_ROLE_SYSCALL_ARG2
    dd PATTERN_POP_RDI_RET, REG_RDI_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG1 | CANDIDATE_ROLE_SYSCALL_ARG1
    dd PATTERN_POP_R8_RET, REG_R8_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG5 | CANDIDATE_ROLE_SYSCALL_ARG5
    dd PATTERN_POP_R9_RET, REG_R9_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSV_ARG6 | CANDIDATE_ROLE_SYSCALL_ARG6
    dd PATTERN_POP_R10_RET, REG_R10_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL | CANDIDATE_ROLE_SYSCALL_ARG4
    dd PATTERN_POP_R11_RET, REG_R11_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_R12_RET, REG_R12_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_R13_RET, REG_R13_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_R14_RET, REG_R14_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
    dd PATTERN_POP_R15_RET, REG_R15_BIT
    dq CANDIDATE_ROLE_GENERIC_CONTROL
case_count: equ 16
case_size: equ 16

section .bss
align 16
summary:     resb GADGET_SUMMARY_RECORD_SIZE
gadget:      resb GADGET_RECORD_SIZE
role_record: resb CANDIDATE_ROLE_RECORD_SIZE

section .text
_start:
    mov     qword [summary + GADGET_SUMMARY_COUNT], 1
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 1
    xor     r12d, r12d
.loop:
    cmp     r12d, case_count
    jae     .nonpop

    ; Clear the current synthetic record and role slot.
    lea     rdi, [rel gadget]
    xor     eax, eax
    mov     ecx, GADGET_RECORD_SIZE / 8
    rep stosq
    mov     qword [role_record + CANDIDATE_ROLE_MASK], -1

    mov     eax, r12d
    imul    eax, case_size
    lea     r13, [rel cases]
    add     r13, rax
    mov     eax, [r13]
    mov     [gadget + GADGET_PATTERN_ID], eax
    mov     dword [gadget + GADGET_PATTERN_REG_COUNT], 1
    mov     eax, [r13 + 4]
    mov     [gadget + GADGET_PATTERN_REG_ORDER], eax

    lea     rdi, [rel summary]
    lea     rsi, [rel gadget]
    lea     rdx, [rel role_record]
    call    x64lens_candidate_role_from_exact
    test    eax, eax
    jnz     .fail
    mov     rax, [r13 + 8]
    cmp     [role_record + CANDIDATE_ROLE_MASK], rax
    jne     .fail
    mov     rdx, CANDIDATE_ROLE_MASK_ALLOWED
    not     rdx
    and     rdx, rax
    jnz     .fail
    inc     r12d
    jmp     .loop

.nonpop:
    lea     rdi, [rel gadget]
    xor     eax, eax
    mov     ecx, GADGET_RECORD_SIZE / 8
    rep stosq
    mov     dword [gadget + GADGET_PATTERN_ID], PATTERN_RET
    mov     qword [role_record + CANDIDATE_ROLE_MASK], -1
    lea     rdi, [rel summary]
    lea     rsi, [rel gadget]
    lea     rdx, [rel role_record]
    call    x64lens_candidate_role_from_exact
    test    eax, eax
    jnz     .fail
    cmp     qword [role_record + CANDIDATE_ROLE_MASK], 0
    jne     .fail

    mov     eax, 1
    mov     edi, 1
    lea     rsi, [rel success_msg]
    mov     edx, success_len
    syscall
    mov     eax, 60
    xor     edi, edi
    syscall

.fail:
    mov     eax, 60
    mov     edi, 1
    syscall
