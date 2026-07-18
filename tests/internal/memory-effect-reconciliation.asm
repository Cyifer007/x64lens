; memory-effect-reconciliation.asm
;
; Purpose:
;   Test the candidate-effect materializer's fail-closed reconciliation of the
;   dense memory_effect_record side-car without debugger-only instrumentation.
;
; Scope:
;   Construct synthetic already-classified gadget records and memory side-car
;   records, call x64lens_candidate_effect_from_exact, and require exact
;   acceptance/rejection for valid, contradictory, reserved-bit, displacement,
;   base-mismatch, and wrong-index states.
;
; This test harness is not linked into the x64lens runtime binary.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_candidate_effect_from_exact
global _start

%define MEMORY_DESC_COMMON \
    (MEMORY_EFFECT_FLAG_PRESENT | MEMORY_EFFECT_FLAG_DEREFERENCE | \
     MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN | \
     (MEMORY_EFFECT_SCALE_1 << MEMORY_EFFECT_SCALE_SHIFT) | \
     (MEMORY_EFFECT_WIDTH_QWORD << MEMORY_EFFECT_WIDTH_SHIFT))

%define MEMORY_DESC_WRITE(base_id, value_id) \
    (MEMORY_DESC_COMMON | MEMORY_EFFECT_FLAG_WRITE | \
     ((base_id) << MEMORY_EFFECT_BASE_SHIFT) | \
     ((value_id) << MEMORY_EFFECT_VALUE_SHIFT))

%define MEMORY_DESC_READ(base_id, value_id) \
    (MEMORY_DESC_COMMON | MEMORY_EFFECT_FLAG_READ | \
     ((base_id) << MEMORY_EFFECT_BASE_SHIFT) | \
     ((value_id) << MEMORY_EFFECT_VALUE_SHIFT))

section .rodata
ok_message: db "memory-effect-reconciliation-smoke: ok cases=7 accepted=2 rejected=5", 10
ok_message_len: equ $ - ok_message

section .bss
align 16
summary:        resb GADGET_SUMMARY_SIZE
gadgets:        resb GADGET_RECORD_SIZE * 2
memory_records: resb MEMORY_EFFECT_RECORD_SIZE * 2
effect_records: resb CANDIDATE_EFFECT_RECORD_SIZE * 2

section .text

_start:
    cld

    ; 1. Canonical write descriptor is accepted.
    call    init_one_write
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_WRITE(REG_RDI_BIT, REG_RAX_BIT)
    call    run_materializer
    test    eax, eax
    jne     fail

    ; 2. Canonical read descriptor is accepted.
    call    init_one_read
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_READ(REG_R8_BIT, REG_R9_BIT)
    call    run_materializer
    test    eax, eax
    jne     fail

    ; 3. READ and WRITE simultaneously is contradictory.
    call    init_one_write
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_WRITE(REG_RDI_BIT, REG_RAX_BIT) | MEMORY_EFFECT_FLAG_READ
    call    run_materializer
    cmp     eax, EXIT_BOUNDS
    jne     fail

    ; 4. Reserved descriptor bits fail closed.
    call    init_one_write
    mov     rax, MEMORY_DESC_WRITE(REG_RDI_BIT, REG_RAX_BIT)
    bts     rax, 63
    mov     [memory_records + MEMORY_EFFECT_DESCRIPTOR], rax
    call    run_materializer
    cmp     eax, EXIT_BOUNDS
    jne     fail

    ; 5. Base-register disagreement fails closed.
    call    init_one_write
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_WRITE(REG_RSI_BIT, REG_RAX_BIT)
    call    run_materializer
    cmp     eax, EXIT_BOUNDS
    jne     fail

    ; 6. A nonzero displacement is outside the current exact family.
    call    init_one_write
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_WRITE(REG_RDI_BIT, REG_RAX_BIT)
    mov     qword [memory_records + MEMORY_EFFECT_DISPLACEMENT], 8
    call    run_materializer
    cmp     eax, EXIT_BOUNDS
    jne     fail

    ; 7. Side-car records swapped across two candidate indexes fail closed.
    call    clear_state
    mov     qword [summary + GADGET_SUMMARY_COUNT], 2
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 2
    mov     qword [summary + GADGET_SUMMARY_PATTERN_COUNT], 2
    lea     rdi, [gadgets]
    call    init_write_gadget
    lea     rdi, [gadgets + GADGET_RECORD_SIZE]
    call    init_read_gadget
    mov     qword [memory_records + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_READ(REG_R8_BIT, REG_R9_BIT)
    mov     qword [memory_records + MEMORY_EFFECT_RECORD_SIZE + MEMORY_EFFECT_DESCRIPTOR], MEMORY_DESC_WRITE(REG_RDI_BIT, REG_RAX_BIT)
    call    run_materializer
    cmp     eax, EXIT_BOUNDS
    jne     fail

    mov     eax, 1                  ; write
    mov     edi, 1                  ; stdout
    lea     rsi, [ok_message]
    mov     edx, ok_message_len
    syscall
    xor     edi, edi
    mov     eax, 60                 ; exit
    syscall

fail:
    mov     edi, 1
    mov     eax, 60
    syscall

run_materializer:
    sub     rsp, 8
    lea     rdi, [summary]
    lea     rsi, [gadgets]
    lea     rdx, [memory_records]
    lea     rcx, [effect_records]
    call    x64lens_candidate_effect_from_exact
    add     rsp, 8
    ret

init_one_write:
    sub     rsp, 8
    call    clear_state
    mov     qword [summary + GADGET_SUMMARY_COUNT], 1
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 1
    mov     qword [summary + GADGET_SUMMARY_PATTERN_COUNT], 1
    lea     rdi, [gadgets]
    call    init_write_gadget
    add     rsp, 8
    ret

init_one_read:
    sub     rsp, 8
    call    clear_state
    mov     qword [summary + GADGET_SUMMARY_COUNT], 1
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 1
    mov     qword [summary + GADGET_SUMMARY_PATTERN_COUNT], 1
    lea     rdi, [gadgets]
    call    init_read_gadget
    add     rsp, 8
    ret

; RDI = gadget_record pointer.
init_write_gadget:
    mov     dword [rdi + GADGET_PATTERN_ID], PATTERN_MOV_MEM_REG_RET
    mov     dword [rdi + GADGET_SEMANTIC_CLASS], SEM_MEMORY_WRITE
    mov     qword [rdi + GADGET_REGS_CONTROLLED], 0
    mov     qword [rdi + GADGET_REGS_CLOBBERED], 0
    mov     qword [rdi + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [rdi + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    mov     dword [rdi + GADGET_PATTERN_REG_COUNT], 2
    mov     dword [rdi + GADGET_PATTERN_REG_ORDER], REG_RDI_BIT | (REG_RAX_BIT << 4)
    ret

; RDI = gadget_record pointer.
init_read_gadget:
    mov     dword [rdi + GADGET_PATTERN_ID], PATTERN_MOV_REG_MEM_RET
    mov     dword [rdi + GADGET_SEMANTIC_CLASS], SEM_MEMORY_READ
    mov     qword [rdi + GADGET_REGS_CONTROLLED], 0
    mov     qword [rdi + GADGET_REGS_CLOBBERED], (1 << REG_R9_BIT)
    mov     qword [rdi + GADGET_STACK_DELTA], STACK_DELTA_RET
    mov     qword [rdi + GADGET_SIDE_EFFECT_FLAGS], SIDE_EFFECT_STACK_READ | SIDE_EFFECT_MEMORY_READ | SIDE_EFFECT_REGISTER_WRITE | SIDE_EFFECT_CONTROL_TRANSFER
    mov     dword [rdi + GADGET_PATTERN_REG_COUNT], 2
    mov     dword [rdi + GADGET_PATTERN_REG_ORDER], REG_R8_BIT | (REG_R9_BIT << 4)
    ret

clear_state:
    lea     rdi, [summary]
    xor     eax, eax
    mov     ecx, (GADGET_SUMMARY_SIZE + (GADGET_RECORD_SIZE * 2) + (MEMORY_EFFECT_RECORD_SIZE * 2) + (CANDIDATE_EFFECT_RECORD_SIZE * 2)) / 8
    rep stosq
    ret
