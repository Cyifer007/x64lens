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
; Current scope:
;   Map supported exact suffix patterns into conservative semantic classes.
;   Sprint 10 adds ordered two-pop, exact register-transfer, bounded
;   positive stack-adjust, and narrowly scoped base-plus-zero qword memory
;   families. This is still not full instruction decoding; semantic
;   promotion describes exact suffix evidence.
;
; Safety model:
;   Candidate records and exact pattern IDs are produced only after parser,
;   executable-region, scanner, and pattern bounds checks. Direct target-byte
;   reads are limited to the validated ret-imm16 immediate and the fixed
;   five-byte stack-adjust suffix that is rechecked before promotion.

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
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_REG_TRANSFER_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_MEMORY_WRITE_COUNT
    CLEAR_SUMMARY_QWORD GADGET_SUMMARY_MEMORY_READ_COUNT
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
    cmp     eax, PATTERN_MULTI_POP_RET
    je      .class_multi_pop_arg
    cmp     eax, PATTERN_MOV_REG_REG_RET
    je      .class_reg_transfer
    cmp     eax, PATTERN_ADD_RSP_IMM8_RET
    je      .class_add_rsp_imm8
    cmp     eax, PATTERN_MOV_MEM_REG_RET
    je      .class_memory_write
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    je      .class_memory_read

    ; Conservative default: known exact patterns that are not yet mapped to a
    ; semantic primitive remain unknown_candidate for Sprint 4 metrics.
    MARK_UNKNOWN

.class_ret:
    CLASSIFY_NO_REG SEM_ALIGNMENT, STACK_DELTA_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_ALIGNMENT_COUNT

.class_ret_imm16:
    ; ret imm16 stack effect is pop return address plus immediate stack adjust.
    ; scanner.asm already verified the three-byte terminator is inside the
    ; executable file-backed region before this reads the little-endian imm16.
    mov     rbx, [r15 + GADGET_FILE_OFFSET]
    movzx   eax, word [r14 + rbx + 1]
    add     rax, STACK_DELTA_RET
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    mov     qword [r15 + GADGET_STACK_DELTA], rax
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_RET_IMM16
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

.class_multi_pop_arg:
    ; Pattern matching owns exact ordered-pop recognition. Recheck the compact
    ; structural record before semantic promotion so contradictory internal
    ; state fails closed instead of creating an unsupported primitive fact.
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     ebx, [r15 + GADGET_PATTERN_REG_ORDER]
    test    ebx, 0xffffff00
    jne     .bounds_error
    mov     ecx, ebx
    and     ecx, 0x0f           ; first pop in execution order
    shr     ebx, 4
    mov     edx, ebx
    and     edx, 0x0f           ; second pop in execution order
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     ecx, edx
    je      .bounds_error
    mov     r8d, ARG_CONTROL_REG_MASK
    bt      r8d, ecx
    jnc     .bounds_error
    bt      r8d, edx
    jnc     .bounds_error

    xor     eax, eax
    bts     rax, rcx
    bts     rax, rdx
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ARG_CONTROL
    mov     [r15 + GADGET_REGS_CONTROLLED], rax
    or      [r13 + GADGET_SUMMARY_REGS_CONTROLLED], rax
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_TWO_POP_RET
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_ARG_CONTROL_COUNT]
    jmp     .next_candidate

.class_reg_transfer:
    ; Exact-pattern metadata stores destination in the low nibble and source in
    ; the next nibble. Register transfer does not independently establish that
    ; the destination value is externally controlled, so controls remain empty.
    ; The overwritten destination is recorded as a clobber and the relation is
    ; rendered separately as source/destination evidence.
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     ebx, [r15 + GADGET_PATTERN_REG_ORDER]
    test    ebx, 0xffffff00
    jne     .bounds_error

    mov     ecx, ebx
    and     ecx, 0x0f           ; destination
    shr     ebx, 4
    mov     edx, ebx
    and     edx, 0x0f           ; source

    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     ecx, edx
    je      .bounds_error
    cmp     ecx, REG_RSP_BIT
    je      .bounds_error
    cmp     edx, REG_RSP_BIT
    je      .bounds_error

    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_REG_TRANSFER
    mov     qword [r15 + GADGET_REGS_CONTROLLED], 0
    xor     eax, eax
    bts     rax, rcx
    mov     [r15 + GADGET_REGS_CLOBBERED], rax
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_REGISTER_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_REG_TRANSFER_COUNT]
    jmp     .next_candidate

.class_add_rsp_imm8:
    ; patterns.asm accepts only 48 83 c4 imm8 c3 with a positive, nonzero,
    ; eight-byte-aligned immediate. Recheck the complete exact suffix and the
    ; empty compact-register metadata before promoting it into a known total
    ; stack delta. This keeps contradictory internal state fail-closed.
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 0
    jne     .bounds_error
    cmp     dword [r15 + GADGET_PATTERN_REG_ORDER], 0
    jne     .bounds_error
    cmp     qword [r15 + GADGET_BYTE_LEN], 5
    jb      .bounds_error
    mov     rbx, [r15 + GADGET_FILE_OFFSET]
    mov     rcx, [r15 + GADGET_BYTE_START]
    cmp     rbx, rcx
    jb      .bounds_error
    mov     rax, rbx
    sub     rax, rcx
    cmp     rax, 4
    jb      .bounds_error
    cmp     byte [r14 + rbx - 4], 0x48
    jne     .bounds_error
    cmp     byte [r14 + rbx - 3], 0x83
    jne     .bounds_error
    cmp     byte [r14 + rbx - 2], 0xc4
    jne     .bounds_error
    cmp     byte [r14 + rbx], 0xc3
    jne     .bounds_error
    movzx   eax, byte [r14 + rbx - 1]
    test    eax, eax
    jz      .bounds_error
    test    eax, 0x80
    jnz     .bounds_error
    test    eax, 0x07
    jnz     .bounds_error
    add     rax, STACK_DELTA_RET
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_ALIGNMENT
    mov     qword [r15 + GADGET_STACK_DELTA], rax
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_ADJUST | SIDE_EFFECT_FLAGS_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_ALIGNMENT_COUNT]
    jmp     .next_candidate

.class_memory_write:
    ; Pattern metadata stores base in the low nibble and the written value
    ; register in the next nibble. A store does not overwrite a GPR, so clobbers
    ; remain empty. Address/value controllability is intentionally not inferred.
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     ebx, [r15 + GADGET_PATTERN_REG_ORDER]
    test    ebx, 0xffffff00
    jne     .bounds_error
    mov     ecx, ebx
    and     ecx, 0x0f           ; base
    shr     ebx, 4
    mov     edx, ebx
    and     edx, 0x0f           ; value source
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RBP_BIT
    je      .bounds_error
    cmp     ecx, REG_R12_BIT
    je      .bounds_error
    cmp     ecx, REG_R13_BIT
    je      .bounds_error
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_MEMORY_WRITE
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_MEMORY_WRITE_COUNT]
    jmp     .next_candidate

.class_memory_read:
    ; The memory-loaded value register is overwritten and therefore clobbered.
    ; It is not marked controlled because current exact evidence does not prove
    ; control of the addressed memory contents.
    cmp     dword [r15 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     ebx, [r15 + GADGET_PATTERN_REG_ORDER]
    test    ebx, 0xffffff00
    jne     .bounds_error
    mov     ecx, ebx
    and     ecx, 0x0f           ; base
    shr     ebx, 4
    mov     edx, ebx
    and     edx, 0x0f           ; value destination
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_R15_BIT
    ja      .bounds_error
    cmp     edx, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RBP_BIT
    je      .bounds_error
    cmp     ecx, REG_R12_BIT
    je      .bounds_error
    cmp     ecx, REG_R13_BIT
    je      .bounds_error
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_MEMORY_READ
    xor     eax, eax
    bts     rax, rdx
    mov     [r15 + GADGET_REGS_CLOBBERED], rax
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_READ | SIDE_EFFECT_REGISTER_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_MEMORY_READ_COUNT]
    jmp     .next_candidate

.class_pop_rax_syscall_num:
    CLASSIFY_REG SEM_SYSCALL_NUM_CONTROL, REG_RAX_BIT, STACK_DELTA_POP_RET, SIDE_EFFECT_STACK_READ, GADGET_SUMMARY_SYSCALL_NUM_COUNT

.class_syscall_trigger:
    ; syscall writes RCX and R11 architecturally before the retained return.
    ; Record those writes as clobbers instead of implying that either value is
    ; controlled. The final ret consumes one stack value.
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_SYSCALL_TRIGGER
    mov     qword [r15 + GADGET_REGS_CLOBBERED], (1 << REG_RCX_BIT) | (1 << REG_R11_BIT)
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_SYSCALL | SIDE_EFFECT_REGISTER_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT]
    jmp     .next_candidate

.class_leave_pivot:
    ; leave; ret derives RSP from RBP, pops a replacement RBP, and then returns
    ; through the pivoted stack. RSP is the controlled pivot relation; RBP is
    ; an overwritten, non-controlled register and is therefore a clobber.
    mov     dword [r15 + GADGET_SEMANTIC_CLASS], SEM_STACK_PIVOT
    mov     qword [r15 + GADGET_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    or      qword [r13 + GADGET_SUMMARY_REGS_CONTROLLED], (1 << REG_RSP_BIT)
    mov     qword [r15 + GADGET_REGS_CLOBBERED], (1 << REG_RBP_BIT)
    mov     qword [r15 + GADGET_STACK_DELTA], STACK_DELTA_UNKNOWN
    mov     qword [r15 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT | SIDE_EFFECT_REGISTER_WRITE
    inc     qword [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    inc     qword [r13 + GADGET_SUMMARY_STACK_PIVOT_COUNT]
    jmp     .next_candidate

.class_pop_rsp_pivot:
    ; pop rsp; ret overwrites RSP and makes the following ret target depend on
    ; the new stack. Treat the stack delta as unknown for Sprint 4.
    CLASSIFY_REG SEM_STACK_PIVOT, REG_RSP_BIT, STACK_DELTA_UNKNOWN, SIDE_EFFECT_STACK_READ | SIDE_EFFECT_STACK_PIVOT, GADGET_SUMMARY_STACK_PIVOT_COUNT

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
