; scoring.asm
;
; Purpose:
;   Gadget scoring engine.
;
; Module scope:
;   Consume semantic facts and the Patch 051 architectural-effect side-car,
;   validate every scored family, and populate GADGET_SCORE. This module does
;   not parse files, scan bytes, classify candidates, materialize effects, or
;   format output.
;
; Scoring policy:
;   Scores are bounded relative-utility hypotheses, not exploitability or risk.
;   Patch 051 calibrates ordered two-pop control and positive aligned stack
;   adjustment only after their semantic and architectural effects are explicit.
;   Register-transfer and memory families remain unscored until controllability
;   and dereference-risk facts support a defensible policy.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_scoring_apply

%define SCORE_DESC_RET_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (1 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT))

%define SCORE_DESC_POP_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define SCORE_DESC_MULTI_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (3 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define SCORE_DESC_LEAVE_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RBP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define SCORE_DESC_POP_RSP_PARTIAL \
    (CANDIDATE_EFFECT_FLAG_PRESENT | \
     (CANDIDATE_EFFECT_STACK_BASE_DYNAMIC << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT))

%define SCORE_DESC_SYSCALL_PARTIAL \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | CANDIDATE_EFFECT_CONTROL_SYSCALL | \
     (1 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (ARCH_FLAG_SYSCALL_READ_MASK << CANDIDATE_EFFECT_FLAGS_READ_SHIFT))

%macro SET_SCORE 1
    mov     dword [r15 + GADGET_SCORE], %1
    inc     qword [r13 + GADGET_SUMMARY_SCORED_COUNT]
    jmp     .next_candidate
%endmacro

%macro CHECK_EFFECT 3
    cmp     qword [r14 + CANDIDATE_EFFECT_REGS_READ], %1
    jne     .bounds_error
    cmp     qword [r14 + CANDIDATE_EFFECT_REGS_WRITTEN], %2
    jne     .bounds_error
    cmp     qword [r14 + CANDIDATE_EFFECT_DESCRIPTOR], %3
    jne     .bounds_error
%endmacro

; x64lens_scoring_apply(gadget_summary=rdi, gadget_records=rsi,
;                       candidate_effect_records=rdx) -> rax=status
x64lens_scoring_apply:
    push    rbp
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

    mov     r13, rdi            ; gadget_summary pointer
    mov     r12, rsi            ; gadget_record[] pointer
    mov     rbx, rdx            ; candidate_effect_record[] pointer

    mov     rax, [r13 + GADGET_SUMMARY_COUNT]
    cmp     rax, [r13 + GADGET_SUMMARY_CAPACITY]
    ja      .bounds_error
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds_error

    mov     qword [r13 + GADGET_SUMMARY_SCORED_COUNT], 0
    xor     rbp, rbp

.candidate_loop:
    cmp     rbp, [r13 + GADGET_SUMMARY_COUNT]
    jae     .ok

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r15, [r12 + rax]
    mov     rax, rbp
    imul    rax, rax, CANDIDATE_EFFECT_RECORD_SIZE
    lea     r14, [rbx + rax]

    ; Score zero means unscored, not low quality.
    mov     dword [r15 + GADGET_SCORE], 0

    mov     eax, [r15 + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_UNKNOWN_CANDIDATE
    je      .next_candidate

    mov     eax, [r15 + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_POP_RDI_RET
    je      .score_arg_rdi
    cmp     eax, PATTERN_POP_RSI_RET
    je      .score_arg_rsi
    cmp     eax, PATTERN_POP_RDX_RET
    je      .score_arg_rdx
    cmp     eax, PATTERN_POP_RCX_RET
    je      .score_arg_rcx
    cmp     eax, PATTERN_POP_R8_RET
    je      .score_arg_r8
    cmp     eax, PATTERN_POP_R9_RET
    je      .score_arg_r9
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
    cmp     eax, PATTERN_MULTI_POP_RET
    je      .score_multi_pop_arg_control
    cmp     eax, PATTERN_ADD_RSP_IMM8_RET
    je      .score_stack_adjust_alignment

    ; Transfer and memory families remain intentionally unscored.
    jmp     .next_candidate

.score_arg_rdi:
    mov     r8, (1 << REG_RDI_BIT)
    jmp     .score_arg_control
.score_arg_rsi:
    mov     r8, (1 << REG_RSI_BIT)
    jmp     .score_arg_control
.score_arg_rdx:
    mov     r8, (1 << REG_RDX_BIT)
    jmp     .score_arg_control
.score_arg_rcx:
    mov     r8, (1 << REG_RCX_BIT)
    jmp     .score_arg_control
.score_arg_r8:
    mov     r8, (1 << REG_R8_BIT)
    jmp     .score_arg_control
.score_arg_r9:
    mov     r8, (1 << REG_R9_BIT)

.score_arg_control:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ARG_CONTROL
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], r8
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_POP_RET
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     r9, r8
    or      r9, (1 << REG_RSP_BIT)
    CHECK_EFFECT (1 << REG_RSP_BIT), r9, SCORE_DESC_POP_COMPLETE
    SET_SCORE 90

.score_syscall_num:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_SYSCALL_NUM_CONTROL
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], (1 << REG_RAX_BIT)
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_POP_RET
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT (1 << REG_RSP_BIT), ((1 << REG_RSP_BIT) | (1 << REG_RAX_BIT)), SCORE_DESC_POP_COMPLETE
    SET_SCORE 85

.score_syscall_trigger:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_SYSCALL_TRIGGER
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], (1 << REG_RCX_BIT) | (1 << REG_R11_BIT)
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_SYSCALL | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT ((1 << REG_RAX_BIT) | (1 << REG_RDI_BIT) | (1 << REG_RSI_BIT) | (1 << REG_RDX_BIT) | (1 << REG_R10_BIT) | (1 << REG_R8_BIT) | (1 << REG_R9_BIT) | (1 << REG_RSP_BIT)), ((1 << REG_RAX_BIT) | (1 << REG_RCX_BIT) | (1 << REG_R11_BIT) | (1 << REG_RSP_BIT)), SCORE_DESC_SYSCALL_PARTIAL
    SET_SCORE 85

.score_leave_pivot:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_STACK_PIVOT
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], (1 << REG_RBP_BIT)
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_UNKNOWN
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT (1 << REG_RBP_BIT), ((1 << REG_RBP_BIT) | (1 << REG_RSP_BIT)), SCORE_DESC_LEAVE_COMPLETE
    SET_SCORE 75

.score_pop_rsp_pivot:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_STACK_PIVOT
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_UNKNOWN
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT (1 << REG_RSP_BIT), (1 << REG_RSP_BIT), SCORE_DESC_POP_RSP_PARTIAL
    SET_SCORE 70

.score_ret_alignment:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT (1 << REG_RSP_BIT), (1 << REG_RSP_BIT), SCORE_DESC_RET_COMPLETE
    SET_SCORE 45

.score_ret_imm_alignment:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    jbe     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_RET_IMM16 | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    CHECK_EFFECT (1 << REG_RSP_BIT), (1 << REG_RSP_BIT), SCORE_DESC_RET_COMPLETE
    SET_SCORE 40

.score_multi_pop_arg_control:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ARG_CONTROL
    jne     .bounds_error
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     r8d, [r15 + GADGET_PATTERN_REG_ORDER]
    test    r8d, 0xffffff00
    jne     .bounds_error
    mov     ecx, r8d
    and     ecx, 0x0f
    shr     r8d, 4
    mov     edx, r8d
    and     edx, 0x0f
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     ecx, edx
    je      .bounds_error
    mov     r9d, ARG_CONTROL_REG_MASK
    bt      r9d, ecx
    jnc     .bounds_error
    bt      r9d, edx
    jnc     .bounds_error
    xor     r8, r8
    bts     r8, rcx
    bts     r8, rdx
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], r8
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_TWO_POP_RET
    jne     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     r9, r8
    or      r9, (1 << REG_RSP_BIT)
    CHECK_EFFECT (1 << REG_RSP_BIT), r9, SCORE_DESC_MULTI_COMPLETE
    SET_SCORE 95

.score_stack_adjust_alignment:
    cmp     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    mov     rax, [r15 + GADGET_STACK_DELTA]
    cmp     rax, 16
    jb      .bounds_error
    cmp     rax, 128
    ja      .bounds_error
    test    rax, 7
    jnz     .bounds_error
    cmp     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_FLAGS_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error

    ; Descriptor must match the exact complete return effect: one stack read
    ; at the adjusted offset, no invented stride/flag-read fields, and exactly
    ; the represented arithmetic flag writes.
    cmp     qword [r14 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RSP_BIT)
    jne     .bounds_error
    cmp     qword [r14 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RSP_BIT)
    jne     .bounds_error
    mov     r8, rax
    sub     r8, STACK_DELTA_RET
    shl     r8, CANDIDATE_EFFECT_FIRST_READ_SHIFT
    or      r8, SCORE_DESC_RET_COMPLETE
    mov     r9, ARCH_FLAG_ARITHMETIC_WRITE_MASK
    shl     r9, CANDIDATE_EFFECT_FLAGS_WRITE_SHIFT
    or      r8, r9
    cmp     [r14 + CANDIDATE_EFFECT_DESCRIPTOR], r8
    jne     .bounds_error
    SET_SCORE 35

.next_candidate:
    inc     rbp
    jmp     .candidate_loop

.ok:
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
    pop     rbp
    ret
