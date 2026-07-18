; memory_effect.asm
;
; Purpose:
;   Materialize structured memory-access facts into a fixed-size candidate-index
;   side-car after exact matching and semantic classification.
;
; Module scope:
;   Consume completed gadget records and populate memory_effect_record[]. This
;   module reconciles facts already established upstream. It does not scan bytes,
;   parse ELF metadata, classify semantics, assign scores, or emit reports.
;
; Public symbols:
;   x64lens_memory_effect_from_exact
;
; Safety:
;   The caller allocates GADGET_RECORD_MAX dense records. Count/capacity and all
;   compact operand fields are revalidated before a side-car record is written.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_memory_effect_from_exact

; x64lens_memory_effect_from_exact(gadget_summary=rdi,
;                                  gadget_records=rsi,
;                                  memory_records=rdx) -> rax=status
x64lens_memory_effect_from_exact:
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

    mov     r13, rdi
    mov     r14, rsi
    mov     r15, rdx

    mov     rax, [r13 + GADGET_SUMMARY_COUNT]
    cmp     rax, [r13 + GADGET_SUMMARY_CAPACITY]
    ja      .bounds_error
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds_error

    xor     rbp, rbp
    xor     r10, r10            ; observed writes
    xor     r11, r11            ; observed reads
.loop:
    cmp     rbp, [r13 + GADGET_SUMMARY_COUNT]
    jae     .reconcile

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r12, [r14 + rax]

    mov     rax, rbp
    imul    rax, rax, MEMORY_EFFECT_RECORD_SIZE
    lea     rbx, [r15 + rax]
    mov     qword [rbx + MEMORY_EFFECT_DESCRIPTOR], 0
    mov     qword [rbx + MEMORY_EFFECT_DISPLACEMENT], 0

    mov     eax, [r12 + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_MOV_MEM_REG_RET
    je      .materialize_write
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    je      .materialize_read

    mov     eax, [r12 + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_MEMORY_WRITE
    je      .bounds_error
    cmp     eax, SEM_MEMORY_READ
    je      .bounds_error
    jmp     .next

.materialize_write:
    cmp     dword [r12 + GADGET_SEMANTIC_CLASS], SEM_MEMORY_WRITE
    jne     .bounds_error
    cmp     qword [r12 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r12 + GADGET_REGS_CLOBBERED], 0
    jne     .bounds_error
    cmp     qword [r12 + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [r12 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_MEMORY_WRITE
    jne     .bounds_error
    mov     r9, MEMORY_EFFECT_FLAG_PRESENT | MEMORY_EFFECT_FLAG_WRITE | MEMORY_EFFECT_FLAG_DEREFERENCE | MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN
    inc     r10
    jmp     .materialize_common

.materialize_read:
    cmp     dword [r12 + GADGET_SEMANTIC_CLASS], SEM_MEMORY_READ
    jne     .bounds_error
    cmp     qword [r12 + GADGET_REGS_CONTROLLED], 0
    jne     .bounds_error
    cmp     qword [r12 + GADGET_STACK_DELTA], STACK_DELTA_RET
    jne     .bounds_error
    cmp     qword [r12 + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_MEMORY_READ | SIDE_EFFECT_REGISTER_WRITE
    jne     .bounds_error
    mov     r9, MEMORY_EFFECT_FLAG_PRESENT | MEMORY_EFFECT_FLAG_READ | MEMORY_EFFECT_FLAG_DEREFERENCE | MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN
    inc     r11

.materialize_common:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     eax, [r12 + GADGET_PATTERN_REG_ORDER]
    test    eax, 0xffffff00
    jne     .bounds_error
    mov     ecx, eax
    and     ecx, 0x0f           ; base
    shr     eax, 4
    and     eax, 0x0f           ; value
    cmp     ecx, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RSP_BIT
    je      .bounds_error
    cmp     ecx, REG_RBP_BIT
    je      .bounds_error
    cmp     ecx, REG_R12_BIT
    je      .bounds_error
    cmp     ecx, REG_R13_BIT
    je      .bounds_error

    mov     r8, r9
    mov     edx, ecx
    shl     rdx, MEMORY_EFFECT_BASE_SHIFT
    or      r8, rdx
    mov     edx, eax
    shl     rdx, MEMORY_EFFECT_VALUE_SHIFT
    or      r8, rdx
    mov     rdx, MEMORY_EFFECT_SCALE_1
    shl     rdx, MEMORY_EFFECT_SCALE_SHIFT
    or      r8, rdx
    mov     rdx, MEMORY_EFFECT_WIDTH_QWORD
    shl     rdx, MEMORY_EFFECT_WIDTH_SHIFT
    or      r8, rdx
    mov     [rbx + MEMORY_EFFECT_DESCRIPTOR], r8
    mov     qword [rbx + MEMORY_EFFECT_DISPLACEMENT], 0

    cmp     dword [r12 + GADGET_PATTERN_ID], PATTERN_MOV_REG_MEM_RET
    jne     .next
    xor     rdx, rdx
    bts     rdx, rax
    cmp     qword [r12 + GADGET_REGS_CLOBBERED], rdx
    jne     .bounds_error

.next:
    inc     rbp
    jmp     .loop

.reconcile:
    cmp     r10, [r13 + GADGET_SUMMARY_MEMORY_WRITE_COUNT]
    jne     .bounds_error
    cmp     r11, [r13 + GADGET_SUMMARY_MEMORY_READ_COUNT]
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
