; regions.asm
;
; Purpose:
;   Executable region model.
;
; Module scope:
;   Store executable byte ranges derived from PT_LOAD program headers with
;   PF_X set. Program headers remain authoritative for runtime mappings.
;   Section headers may later add human-readable labels, but they must not
;   override these loader-derived ranges.
;
; Current export:
;   x64lens_regions_store_from_phdr(region_buffer, index, phdr_ptr, phdr_index)
;
; Contract:
;   This module stores normalized facts. It does not validate ELF table
;   ranges, print reports, decode instructions, or decide mitigation policy.

bits 64
default rel

%include "elf64.inc"
%include "structs.inc"

section .text
global x64lens_regions_store_from_phdr

; x64lens_regions_store_from_phdr(region_buffer=rdi, index=rsi, phdr_ptr=rdx, phdr_index=rcx)
;
; Inputs:
;   RDI = base of executable_region[] buffer
;   RSI = destination region index
;   RDX = pointer to an already-validated ELF64 program header
;   RCX = original program-header table index
;
; Output:
;   RAX = 0
;
; Stored fields:
;   file offset, virtual address, file size, memory size, flags, and original
;   program-header index. The scanner later uses file offset + file size to walk bytes,
;   while reporting uses virtual address and flags for analyst readability.
;
; Clobbers:
;   RAX, RCX, RDI
x64lens_regions_store_from_phdr:
    mov     rax, rsi
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    add     rdi, rax

    mov     rax, [rdx + P_OFFSET]
    mov     [rdi + EXEC_REGION_FILE_OFFSET], rax

    mov     rax, [rdx + P_VADDR]
    mov     [rdi + EXEC_REGION_VADDR], rax

    mov     rax, [rdx + P_FILESZ]
    mov     [rdi + EXEC_REGION_FILESZ], rax

    mov     rax, [rdx + P_MEMSZ]
    mov     [rdi + EXEC_REGION_MEMSZ], rax

    mov     eax, [rdx + P_FLAGS]
    mov     [rdi + EXEC_REGION_FLAGS], eax
    mov     [rdi + EXEC_REGION_PHDR_INDEX], ecx
    mov     qword [rdi + EXEC_REGION_SECTION_NAME_PTR], 0
    mov     qword [rdi + EXEC_REGION_SECTION_NAME_LEN], 0
    mov     qword [rdi + EXEC_REGION_SECTION_INDEX], 0

    xor     rax, rax
    ret
