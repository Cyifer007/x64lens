; arena.asm
;
; Purpose:
;   Minimal mmap-backed bump allocator for x64lens analysis records.
;
; Module scope:
;   Allocate one anonymous read/write memory region, hand out aligned slices
;   through a monotonic bump pointer, and release the full mapping during
;   command cleanup. The arena does not know about ELF, gadgets, mitigations,
;   or reporting semantics.
;
; Sprint 3 Phase C scope:
;   Replace the raw gadget candidate array's fixed .bss backing storage with
;   arena-backed storage while preserving the same candidate record contract.
;
; Safety model:
;   All allocation sizes and alignment adjustments are overflow-checked. A
;   failed allocation returns NULL instead of wrapping. The arena is private to
;   the current process and contains only x64lens analysis facts, never target
;   executable code.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"
%include "structs.inc"

extern x64_sys_mmap
extern x64_sys_munmap

section .text
global x64lens_arena_init
global x64lens_arena_alloc
global x64lens_arena_destroy

; x64lens_arena_init(arena_record=rdi, size=rsi) -> rax=status
;
; Inputs:
;   RDI = writable ARENA_RECORD_SIZE record
;   RSI = requested arena byte size
;
; Output:
;   RAX = EXIT_OK on success, EXIT_GENERAL on mmap or invalid-size failure
;
; Clobbers:
;   RAX, RDI, RSI, RDX, R10, R8, R9. Preserves RBX/R12.
x64lens_arena_init:
    push    rbx
    push    r12
    sub     rsp, 8              ; keep nested System V calls 16-byte aligned

    mov     rbx, rdi            ; arena record pointer
    mov     r12, rsi            ; requested size

    ; Initialize first so destroy is safe even after partial failure.
    mov     qword [rbx + ARENA_BASE], 0
    mov     qword [rbx + ARENA_SIZE], 0
    mov     qword [rbx + ARENA_USED], 0

    test    r12, r12
    jz      .fail

    ; mmap(NULL, size, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)
    xor     rdi, rdi
    mov     rsi, r12
    mov     rdx, PROT_READ | PROT_WRITE
    mov     r10, MAP_PRIVATE | MAP_ANONYMOUS
    mov     r8, -1
    xor     r9, r9
    call    x64_sys_mmap
    test    rax, rax
    js      .fail

    mov     [rbx + ARENA_BASE], rax
    mov     [rbx + ARENA_SIZE], r12
    mov     qword [rbx + ARENA_USED], 0
    xor     rax, rax
    jmp     .done

.fail:
    mov     rax, EXIT_GENERAL

.done:
    add     rsp, 8
    pop     r12
    pop     rbx
    ret


; x64lens_arena_alloc(arena_record=rdi, size=rsi, align=rdx) -> rax=ptr_or_0
;
; Inputs:
;   RDI = initialized arena record
;   RSI = requested allocation size
;   RDX = power-of-two alignment, or 0/1 for byte alignment
;
; Output:
;   RAX = aligned allocation pointer on success, 0 on failure
;
; Notes:
;   This is a simple bump allocator. Individual allocations cannot be freed.
;   Call x64lens_arena_destroy to release the whole backing mapping.
;
; Clobbers:
;   RAX, RBX, RCX, RDX, RSI. Preserves R12/R13.
x64lens_arena_alloc:
    push    rbx
    push    r12
    push    r13

    mov     rbx, rdi            ; arena record
    mov     r12, rsi            ; requested size
    mov     r13, rdx            ; requested alignment

    test    r12, r12
    jz      .fail

    ; Treat align 0 and align 1 as no alignment adjustment. Otherwise require
    ; a power of two so the mask math below is valid.
    cmp     r13, 1
    ja      .check_power_two
    mov     r13, 1
    jmp     .alignment_ready

.check_power_two:
    mov     rax, r13
    dec     rax
    test    rax, r13
    jnz     .fail

.alignment_ready:
    mov     rcx, [rbx + ARENA_USED]

    ; aligned = (used + align - 1) & ~(align - 1), with overflow detection.
    mov     rax, r13
    dec     rax                 ; alignment mask
    add     rcx, rax
    jc      .fail
    not     rax
    and     rcx, rax            ; RCX = aligned offset

    ; end = aligned + size. Reject wrap or capacity overflow.
    mov     rax, rcx
    add     rax, r12
    jc      .fail
    cmp     rax, [rbx + ARENA_SIZE]
    ja      .fail

    ; Convert aligned offset to a pointer before committing ARENA_USED. If
    ; base is invalid or pointer addition wraps, leave the arena unchanged.
    mov     rdx, [rbx + ARENA_BASE]
    test    rdx, rdx
    jz      .fail
    add     rdx, rcx
    jc      .fail

    mov     [rbx + ARENA_USED], rax
    mov     rax, rdx
    jmp     .done

.fail:
    xor     rax, rax

.done:
    pop     r13
    pop     r12
    pop     rbx
    ret


; x64lens_arena_destroy(arena_record=rdi)
;
; Inputs:
;   RDI = arena record, initialized or zeroed
;
; Output:
;   None. The record is reset to zero.
;
; Clobbers:
;   RAX, RDI, RSI. Preserves RBX.
x64lens_arena_destroy:
    push    rbx
    mov     rbx, rdi

    mov     rdi, [rbx + ARENA_BASE]
    test    rdi, rdi
    jz      .zero_record
    mov     rsi, [rbx + ARENA_SIZE]
    test    rsi, rsi
    jz      .zero_record
    call    x64_sys_munmap

.zero_record:
    mov     qword [rbx + ARENA_BASE], 0
    mov     qword [rbx + ARENA_SIZE], 0
    mov     qword [rbx + ARENA_USED], 0
    pop     rbx
    ret
