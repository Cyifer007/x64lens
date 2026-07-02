; shdr.asm
;
; Purpose:
;   Bounded ELF64 section-header metadata helpers.
;
; Module scope:
;   Section headers are not runtime mapping authority. This module derives
;   analyst metadata indicators only after elf64.asm has validated the fixed
;   ELF identity and table extents. Program-header analysis remains the source
;   of executable-region truth.
;
; Current export:
;   x64lens_shdr_classify_stripped(base, file_size, summary)
;
; Contract:
;   Do not select executable ranges here. Do not print. Do not parse CLI
;   arguments. Keep section-derived facts evidence-qualified.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_bounds_table_extent_valid
extern x64lens_bounds_table_entry_offset

section .text
global x64lens_shdr_classify_stripped

; x64lens_shdr_classify_stripped(base=rdi, file_size=rsi, summary=rdx) -> rax=status
;
; Inputs:
;   RDI = mmap base for an already ELF64-validated target
;   RSI = target file size
;   RDX = writable phdr_summary record containing the metadata indicator slot
;
; Output:
;   RAX = stable x64lens status code
;
; Semantics:
;   - no section table: unknown
;   - validated section table without SHT_SYMTAB: stripped
;   - validated section table with SHT_SYMTAB: not stripped
;
; Safety:
;   Revalidates section-header table extent and each entry offset before
;   forming a pointer. This is duplicate validation by design because future
;   callers may reuse the helper independently from the current command flow.
x64lens_shdr_classify_stripped:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 16

    mov     r12, rdi            ; mapped base
    mov     r13, rsi            ; file size
    mov     r14, rdx            ; summary record

    mov     qword [r14 + PHDR_SUMMARY_STRIPPED_STATE], STRIPPED_STATE_UNKNOWN

    movzx   r15, word [r12 + E_SHNUM]
    test    r15, r15
    je      .ok                 ; extended/no section table: no bounded evidence

    cmp     word [r12 + E_SHENTSIZE], ELF64_SHDR_SIZE
    jne     .malformed
    mov     rsi, [r12 + E_SHOFF]
    test    rsi, rsi
    je      .malformed

    mov     rdi, r13
    mov     rdx, ELF64_SHDR_SIZE
    mov     rcx, r15
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .malformed

    ; A present, validated section table gives enough metadata evidence to
    ; classify absence of SHT_SYMTAB as stripped unless a later entry proves
    ; otherwise.
    mov     qword [r14 + PHDR_SUMMARY_STRIPPED_STATE], STRIPPED_STATE_STRIPPED

    xor     rbx, rbx
.loop:
    cmp     rbx, r15
    jae     .ok

    mov     rdi, r13
    mov     rsi, [r12 + E_SHOFF]
    mov     rdx, ELF64_SHDR_SIZE
    mov     rcx, r15
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed

    mov     rax, [rsp]
    lea     r10, [r12 + rax]
    cmp     dword [r10 + S_TYPE], SHT_SYMTAB
    je      .not_stripped

    inc     rbx
    jmp     .loop

.not_stripped:
    mov     qword [r14 + PHDR_SUMMARY_STRIPPED_STATE], STRIPPED_STATE_NOT_STRIPPED

.ok:
    xor     rax, rax
    jmp     .done

.malformed:
    mov     rax, EXIT_MALFORMED_ELF

.done:
    add     rsp, 16
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
