; candidate_effect.asm
;
; Purpose:
;   Materialize fixed-size architectural effect facts for every recognized exact
;   candidate after semantic classification and structured memory effects.
;
; Module scope:
;   Consume gadget_record[] plus memory_effect_record[] and populate the dense
;   candidate_effect_record[] side-car keyed by candidate index. This module
;   validates existing exact/semantic/effect relationships. It does not map or
;   parse files, scan bytes, assign exact patterns, choose semantic classes,
;   score candidates, or render reports.
;
; Public symbols:
;   x64lens_candidate_effect_from_exact
;
; Safety:
;   Count and capacity are checked before iteration. Compact register metadata,
;   semantic fields, side-effect masks, stack facts, and memory side-car records
;   are reconciled before an effect record is committed. Contradictory internal
;   state returns EXIT_BOUNDS.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .rodata
; Pattern IDs 3 through 18 map to the architectural register written by pop.
pop_pattern_reg_ids:
    db REG_RAX_BIT, REG_RCX_BIT, REG_RDX_BIT, REG_RBX_BIT
    db REG_RSP_BIT, REG_RBP_BIT, REG_RSI_BIT, REG_RDI_BIT
    db REG_R8_BIT, REG_R9_BIT, REG_R10_BIT, REG_R11_BIT
    db REG_R12_BIT, REG_R13_BIT, REG_R14_BIT, REG_R15_BIT

section .text
global x64lens_candidate_effect_from_exact

; Descriptor templates shared by exact return-ending families.
%define EFFECT_DESC_RET_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (1 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT))

%define EFFECT_DESC_POP_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define EFFECT_DESC_MULTI_POP_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (3 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define EFFECT_DESC_LEAVE_COMPLETE \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE | \
     CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RBP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (8 << CANDIDATE_EFFECT_READ_STRIDE_SHIFT))

%define EFFECT_DESC_POP_RSP_PARTIAL \
    (CANDIDATE_EFFECT_FLAG_PRESENT | \
     (CANDIDATE_EFFECT_STACK_BASE_DYNAMIC << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | \
     (2 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT))

%define EFFECT_DESC_SYSCALL_PARTIAL \
    (CANDIDATE_EFFECT_FLAG_PRESENT | CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN | \
     (CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP << CANDIDATE_EFFECT_STACK_BASE_SHIFT) | \
     CANDIDATE_EFFECT_CONTROL_RETURN | CANDIDATE_EFFECT_CONTROL_SYSCALL | \
     (1 << CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT) | \
     (ARCH_FLAG_SYSCALL_READ_MASK << CANDIDATE_EFFECT_FLAGS_READ_SHIFT))

; x64lens_candidate_effect_from_exact(gadget_summary=rdi,
;                                     gadget_records=rsi,
;                                     memory_records=rdx,
;                                     effect_records=rcx) -> rax=status
x64lens_candidate_effect_from_exact:
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
    test    rcx, rcx
    jz      .bounds_error

    mov     r12, rdi            ; summary
    mov     r13, rsi            ; gadget_record[]
    mov     r14, rdx            ; memory_effect_record[]
    mov     r15, rcx            ; candidate_effect_record[]

    mov     rax, [r12 + GADGET_SUMMARY_COUNT]
    cmp     rax, [r12 + GADGET_SUMMARY_CAPACITY]
    ja      .bounds_error
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds_error

    xor     rbp, rbp
    xor     r11d, r11d          ; represented exact records
.loop:
    cmp     rbp, [r12 + GADGET_SUMMARY_COUNT]
    jae     .reconcile

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     rbx, [r13 + rax]    ; current gadget_record

    mov     rax, rbp
    imul    rax, rax, CANDIDATE_EFFECT_RECORD_SIZE
    lea     r10, [r15 + rax]    ; current candidate_effect_record
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], 0
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], 0
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], 0

    mov     eax, [rbx + GADGET_PATTERN_ID]
    test    eax, eax
    jz      .unknown_pattern
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    ja      .bounds_error
    inc     r11d

    cmp     eax, PATTERN_RET
    je      .effect_ret
    cmp     eax, PATTERN_RET_IMM16
    je      .effect_ret_imm16
    cmp     eax, PATTERN_POP_RAX_RET
    jb      .bounds_error
    cmp     eax, PATTERN_POP_R15_RET
    jbe     .effect_single_pop
    cmp     eax, PATTERN_LEAVE_RET
    je      .effect_leave
    cmp     eax, PATTERN_SYSCALL_RET
    je      .effect_syscall
    cmp     eax, PATTERN_MULTI_POP_RET
    je      .effect_multi_pop
    cmp     eax, PATTERN_MOV_REG_REG_RET
    je      .effect_reg_transfer
    cmp     eax, PATTERN_ADD_RSP_IMM8_RET
    je      .effect_stack_adjust
    cmp     eax, PATTERN_MOV_MEM_REG_RET
    je      .effect_memory_write
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    je      .effect_memory_read
    jmp     .bounds_error

.unknown_pattern:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_UNKNOWN_CANDIDATE
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], 0
    jne     .bounds_error
    jmp     .next

.effect_ret:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_RET_COMPLETE
    jmp     .next

.effect_ret_imm16:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jb      .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_RET_IMM16 | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_RET_COMPLETE
    jmp     .next

.effect_single_pop:
    mov     edx, eax
    sub     edx, PATTERN_POP_RAX_RET
    lea     r8, [rel pop_pattern_reg_ids]
    movzx   ecx, byte [r8 + rdx]
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error

    ; Every exact pop reads the entry stack and writes RSP plus its destination.
    mov     r8, (1 << REG_RSP_BIT)
    mov     r9, (1 << REG_RSP_BIT)
    bts     r9, rcx
    mov     [r10 + CANDIDATE_EFFECT_REGS_READ], r8
    mov     [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], r9

    cmp     ecx, REG_RSP_BIT
    je      .effect_pop_rsp
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_POP_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_POP_COMPLETE

    cmp     eax, PATTERN_POP_RAX_RET
    je      .verify_pop_rax
    cmp     eax, PATTERN_POP_RCX_RET
    je      .verify_pop_arg
    cmp     eax, PATTERN_POP_RDX_RET
    je      .verify_pop_arg
    cmp     eax, PATTERN_POP_RSI_RET
    je      .verify_pop_arg
    cmp     eax, PATTERN_POP_RDI_RET
    je      .verify_pop_arg
    cmp     eax, PATTERN_POP_R8_RET
    je      .verify_pop_arg
    cmp     eax, PATTERN_POP_R9_RET
    je      .verify_pop_arg

    ; Exact-only pops retain known effects but no semantic role or score.
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_UNKNOWN_CANDIDATE
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    jmp     .next

.verify_pop_rax:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_SYSCALL_NUM_CONTROL
    jne     .bounds_error
    jmp     .verify_pop_controlled

.verify_pop_arg:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_ARG_CONTROL
    jne     .bounds_error

.verify_pop_controlled:
    xor     r8, r8
    bts     r8, rcx
    cmp     [rbx + GADGET_REGS_CONTROLLED], r8
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    jmp     .next

.effect_pop_rsp:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_STACK_PIVOT
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_UNKNOWN
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_POP_RSP_PARTIAL
    jmp     .next

.effect_leave:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_STACK_PIVOT
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], (1 << REG_RBP_BIT)
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_UNKNOWN
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RBP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RBP_BIT) | (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_LEAVE_COMPLETE
    jmp     .next

.effect_syscall:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_SYSCALL_TRIGGER
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], (1 << REG_RCX_BIT) | (1 << REG_R11_BIT)
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_SYSCALL | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RAX_BIT) | (1 << REG_RDI_BIT) | (1 << REG_RSI_BIT) | (1 << REG_RDX_BIT) | (1 << REG_R10_BIT) | (1 << REG_R8_BIT) | (1 << REG_R9_BIT) | (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RAX_BIT) | (1 << REG_RCX_BIT) | (1 << REG_R11_BIT) | (1 << REG_RSP_BIT)
    mov     rax, EFFECT_DESC_SYSCALL_PARTIAL
    mov     [r10 + CANDIDATE_EFFECT_DESCRIPTOR], rax
    jmp     .next

.effect_multi_pop:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_ARG_CONTROL
    jne     .bounds_error
    cmp     dword [rbx + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     eax, [rbx + GADGET_PATTERN_REG_ORDER]
    test    eax, 0xffffff00
    jne     .bounds_error
    mov     ecx, eax
    and     ecx, 0x0f
    shr     eax, 4
    and     eax, 0x0f
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     ecx, eax
    je      .bounds_error
    mov     r8d, ARG_CONTROL_REG_MASK
    bt      r8d, ecx
    jnc     .bounds_error
    bt      r8d, eax
    jnc     .bounds_error
    xor     r8, r8
    bts     r8, rcx
    bts     r8, rax
    cmp     [rbx + GADGET_REGS_CONTROLLED], r8
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_TWO_POP_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RSP_BIT)
    mov     r9, r8
    or      r9, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], r9
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_MULTI_POP_COMPLETE
    jmp     .next

.effect_reg_transfer:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_REG_TRANSFER
    jne     .bounds_error
    cmp     dword [rbx + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     eax, [rbx + GADGET_PATTERN_REG_ORDER]
    test    eax, 0xffffff00
    jne     .bounds_error
    mov     ecx, eax
    and     ecx, 0x0f           ; destination
    shr     eax, 4
    and     eax, 0x0f           ; source
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     ecx, eax
    je      .bounds_error
    cmp     ecx, REG_RSP_BIT
    je      .bounds_error
    cmp     eax, REG_RSP_BIT
    je      .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    xor     r8, r8
    bts     r8, rcx
    cmp     [rbx + GADGET_REGS_CLOBBERED], r8
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    xor     r8, r8
    bts     r8, rax
    or      r8, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_READ], r8
    xor     r8, r8
    bts     r8, rcx
    or      r8, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], r8
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_RET_COMPLETE
    jmp     .next

.effect_stack_adjust:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    mov     rax, [rbx + GADGET_STACK_DELTA]
    cmp     rax, 16
    jb      .bounds_error
    cmp     rax, 128
    ja      .bounds_error
    test    rax, 7
    jnz     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_FLAGS_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    sub     rax, STACK_DELTA_RET
    cmp     rax, CANDIDATE_EFFECT_FIRST_READ_MASK
    ja      .bounds_error
    mov     r8, EFFECT_DESC_RET_COMPLETE
    shl     rax, CANDIDATE_EFFECT_FIRST_READ_SHIFT
    or      r8, rax
    mov     rax, ARCH_FLAG_ARITHMETIC_WRITE_MASK
    shl     rax, CANDIDATE_EFFECT_FLAGS_WRITE_SHIFT
    or      r8, rax
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_READ], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_DESCRIPTOR], r8
    jmp     .next

.effect_memory_write:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_MEMORY_WRITE
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    sub     rsp, 8
    call    .load_memory_operands
    lea     rsp, [rsp + 8]      ; preserve returned carry flag
    jc      .bounds_error
    test    rax, MEMORY_EFFECT_FLAG_WRITE
    jz      .bounds_error
    xor     r8, r8
    bts     r8, rcx             ; base
    bts     r8, rdx             ; value source
    or      r8, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_READ], r8
    mov     qword [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], (1 << REG_RSP_BIT)
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_RET_COMPLETE
    jmp     .next

.effect_memory_read:
    cmp     dword [rbx + GADGET_SEMANTIC_CLASS], SEM_MEMORY_READ
    jne     .bounds_error
    cmp     qword [rbx + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [rbx + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [rbx + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    jne     .bounds_error
    sub     rsp, 8
    call    .load_memory_operands
    lea     rsp, [rsp + 8]      ; preserve returned carry flag
    jc      .bounds_error
    test    rax, MEMORY_EFFECT_FLAG_READ
    jz      .bounds_error
    xor     r8, r8
    bts     r8, rdx             ; value destination
    cmp     [rbx + GADGET_REGS_CLOBBERED], r8
    jne     .bounds_error
    xor     r8, r8
    bts     r8, rcx             ; base
    or      r8, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_READ], r8
    xor     r8, r8
    bts     r8, rdx
    or      r8, (1 << REG_RSP_BIT)
    mov     [r10 + CANDIDATE_EFFECT_REGS_WRITTEN], r8
    mov     qword [r10 + CANDIDATE_EFFECT_DESCRIPTOR], EFFECT_DESC_RET_COMPLETE
    jmp     .next

; Load and validate the structured memory side-car for the current candidate.
; Returns descriptor in RAX, base register ID in RCX, value register ID in RDX.
.load_memory_operands:
    push    rsi

    ; Resolve the side-car record at the same candidate index.
    mov     rax, rbp
    imul    rax, rax, MEMORY_EFFECT_RECORD_SIZE
    lea     rsi, [r14 + rax]
    cmp     qword [rsi + MEMORY_EFFECT_DISPLACEMENT], 0
    jne     .memory_operand_error
    mov     r8, [rsi + MEMORY_EFFECT_DESCRIPTOR]

    ; Reconstruct the canonical descriptor from the current candidate rather
    ; than accepting a permissive subset of a stale or wrong-index record.
    cmp     dword [rbx + GADGET_PATTERN_REG_COUNT], 2
    jne     .memory_operand_error
    mov     eax, [rbx + GADGET_PATTERN_REG_ORDER]
    test    eax, 0xffffff00
    jne     .memory_operand_error
    mov     ecx, eax
    and     ecx, 0x0f           ; base
    shr     eax, 4
    and     eax, 0x0f
    mov     edx, eax            ; value source/destination
    cmp     ecx, REG_R15_BIT
    ja      .memory_operand_error
    cmp     edx, REG_R15_BIT
    ja      .memory_operand_error
    cmp     ecx, REG_RSP_BIT
    je      .memory_operand_error
    cmp     ecx, REG_RBP_BIT
    je      .memory_operand_error
    cmp     ecx, REG_R12_BIT
    je      .memory_operand_error
    cmp     ecx, REG_R13_BIT
    je      .memory_operand_error
    cmp     edx, REG_RSP_BIT
    je      .memory_operand_error

    mov     eax, [rbx + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_MOV_MEM_REG_RET
    je      .memory_expected_write
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    je      .memory_expected_read
    jmp     .memory_operand_error

.memory_expected_write:
    mov     r9, MEMORY_EFFECT_FLAG_PRESENT | MEMORY_EFFECT_FLAG_WRITE | MEMORY_EFFECT_FLAG_DEREFERENCE | MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN
    jmp     .memory_expected_common
.memory_expected_read:
    mov     r9, MEMORY_EFFECT_FLAG_PRESENT | MEMORY_EFFECT_FLAG_READ | MEMORY_EFFECT_FLAG_DEREFERENCE | MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN

.memory_expected_common:
    mov     eax, ecx
    shl     rax, MEMORY_EFFECT_BASE_SHIFT
    or      r9, rax
    mov     eax, edx
    shl     rax, MEMORY_EFFECT_VALUE_SHIFT
    or      r9, rax
    mov     rax, MEMORY_EFFECT_SCALE_1
    shl     rax, MEMORY_EFFECT_SCALE_SHIFT
    or      r9, rax
    mov     rax, MEMORY_EFFECT_WIDTH_QWORD
    shl     rax, MEMORY_EFFECT_WIDTH_SHIFT
    or      r9, rax

    cmp     r8, r9
    jne     .memory_operand_error
    mov     rax, r8
    pop     rsi
    clc
    ret

.memory_operand_error:
    pop     rsi
    stc
    ret

.next:
    inc     rbp
    jmp     .loop

.reconcile:
    cmp     r11, [r12 + GADGET_SUMMARY_PATTERN_COUNT]
    jne     .bounds_error
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
