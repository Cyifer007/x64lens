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
; Current exports:
;   x64lens_shdr_classify_stripped(base, file_size, summary)
;   x64lens_shdr_annotate_exec_regions(base, file_size, regions, count)
;   x64lens_shdr_annotate_gadgets(base, file_size, gadgets, count)
;
; Contract:
;   Do not select executable ranges here. Do not print. Do not parse CLI
;   arguments. Keep section-derived facts evidence-qualified.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_bounds_range_end_valid
extern x64lens_bounds_add_u64_checked
extern x64lens_bounds_table_extent_valid
extern x64lens_bounds_table_entry_offset

; Stack-local section-label context. This deliberately avoids process-global
; helper state so future multi-target or library-style use cannot accidentally
; reuse stale section-name metadata across mapped files.
%define SHDR_CTX_BASE         0
%define SHDR_CTX_FILE_SIZE    8
%define SHDR_CTX_COUNT        16
%define SHDR_CTX_SHSTR_PTR    24
%define SHDR_CTX_SHSTR_SIZE   32
%define SHDR_CTX_HAS_NAMES    40
%define SHDR_CTX_SIZE         48

section .text
global x64lens_shdr_classify_stripped
global x64lens_shdr_annotate_exec_regions
global x64lens_shdr_annotate_gadgets

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


; x64lens_shdr_annotate_exec_regions(base=rdi, file_size=rsi, regions=rdx, count=rcx)
;   -> rax=status
;
; Section names are analyst annotations only. They never create, remove, resize,
; or reorder executable regions. If the section-name table is absent or unsafe,
; region records remain unlabeled and the loader-derived facts still report.
x64lens_shdr_annotate_exec_regions:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56             ; 48-byte context plus alignment padding

    mov     r12, rdx            ; executable_region[]
    mov     r13, rcx            ; region count

    lea     rdx, [rsp]
    call    shdr_label_setup
    test    rax, rax
    jne     .done
    cmp     qword [rsp + SHDR_CTX_HAS_NAMES], 0
    je      .ok

    xor     rbx, rbx
.region_loop:
    cmp     rbx, r13
    jae     .ok

    mov     rax, rbx
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     r14, [r12 + rax]

    mov     rdi, [r14 + EXEC_REGION_FILE_OFFSET]
    mov     rsi, [r14 + EXEC_REGION_VADDR]
    lea     rdx, [rsp]
    call    shdr_find_section_for_file_offset
    test    rax, rax
    jz      .next_region
    mov     [r14 + EXEC_REGION_SECTION_NAME_PTR], rax
    mov     [r14 + EXEC_REGION_SECTION_NAME_LEN], rdx
    mov     [r14 + EXEC_REGION_SECTION_INDEX], rcx

.next_region:
    inc     rbx
    jmp     .region_loop

.ok:
    xor     rax, rax
.done:
    add     rsp, 56
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; x64lens_shdr_annotate_gadgets(base=rdi, file_size=rsi, gadgets=rdx, count=rcx)
;   -> rax=status
;
; Adds optional section-name annotations to already discovered raw candidates.
; Candidate discovery, exact pattern matching, semantic classification, and
; scoring remain unchanged.
x64lens_shdr_annotate_gadgets:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56             ; 48-byte context plus alignment padding

    mov     r12, rdx            ; gadget_record[]
    mov     r13, rcx            ; gadget count

    lea     rdx, [rsp]
    call    shdr_label_setup
    test    rax, rax
    jne     .done
    cmp     qword [rsp + SHDR_CTX_HAS_NAMES], 0
    je      .ok

    xor     rbx, rbx
.gadget_loop:
    cmp     rbx, r13
    jae     .ok

    mov     rax, rbx
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r14, [r12 + rax]

    mov     rdi, [r14 + GADGET_FILE_OFFSET]
    mov     rsi, [r14 + GADGET_VIRTUAL_ADDRESS]
    lea     rdx, [rsp]
    call    shdr_find_section_for_file_offset
    test    rax, rax
    jz      .next_gadget
    mov     [r14 + GADGET_SECTION_NAME_PTR], rax
    mov     [r14 + GADGET_SECTION_NAME_LEN], rdx
    mov     [r14 + GADGET_SECTION_INDEX], rcx

.next_gadget:
    inc     rbx
    jmp     .gadget_loop

.ok:
    xor     rax, rax
.done:
    add     rsp, 56
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; shdr_label_setup(base=rdi, file_size=rsi, context=rdx) -> rax=status
;
; Establishes a bounded section table and optional section-name string table.
; A malformed section table is fatal because other SHDR helpers depend on a
; valid stride and extent. Missing or unusable section names are nonfatal.
shdr_label_setup:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 24

    mov     r12, rdi            ; mapped base
    mov     r13, rsi            ; file size
    mov     r14, rdx            ; stack-local SHDR label context
    mov     [r14 + SHDR_CTX_BASE], rdi
    mov     [r14 + SHDR_CTX_FILE_SIZE], rsi
    mov     qword [r14 + SHDR_CTX_COUNT], 0
    mov     qword [r14 + SHDR_CTX_SHSTR_PTR], 0
    mov     qword [r14 + SHDR_CTX_SHSTR_SIZE], 0
    mov     qword [r14 + SHDR_CTX_HAS_NAMES], 0

    movzx   r15, word [r12 + E_SHNUM]
    test    r15, r15
    je      .ok

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
    mov     [r14 + SHDR_CTX_COUNT], r15

    movzx   rbx, word [r12 + E_SHSTRNDX]
    test    rbx, rbx
    je      .ok                 ; no section-name table selected
    cmp     rbx, r15
    jae     .ok                 ; extended/invalid index: labels unavailable

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
    lea     r15, [r12 + rax]    ; section-name string-table header
    cmp     dword [r15 + S_TYPE], SHT_STRTAB
    jne     .ok
    mov     rdx, [r15 + S_SIZE]
    test    rdx, rdx
    jz      .ok

    mov     rdi, r13
    mov     rsi, [r15 + S_OFFSET]
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .ok                 ; labels unavailable, but table iteration is safe

    mov     rax, [r15 + S_OFFSET]
    lea     rax, [r12 + rax]
    mov     [r14 + SHDR_CTX_SHSTR_PTR], rax
    mov     rax, [r15 + S_SIZE]
    mov     [r14 + SHDR_CTX_SHSTR_SIZE], rax
    mov     qword [r14 + SHDR_CTX_HAS_NAMES], 1

.ok:
    xor     rax, rax
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
.done:
    add     rsp, 24
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; shdr_find_section_for_file_offset(file_offset=rdi, virtual_address=rsi, context=rdx)
;   -> rax=section_name_ptr or 0, rdx=name_len, rcx=section_index
;
; Names are returned only after proving that the candidate section is a unique
; file-backed allocated executable section, its file-offset range contains the
; candidate, its SHF_ALLOC virtual-address range contains the candidate VA, and
; its name is non-empty and null-terminated inside the bounded section-name
; string table. Ambiguous overlapping executable sections intentionally return
; no label instead of implying false precision on hostile section tables.
shdr_find_section_for_file_offset:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56

    mov     rbp, rdx            ; stack-local SHDR label context
    mov     [rsp + 8], rdi      ; target file offset
    mov     [rsp + 48], rsi     ; target virtual address
    mov     qword [rsp + 16], 0 ; selected section-name pointer
    mov     qword [rsp + 24], 0 ; selected section-name length
    mov     qword [rsp + 32], 0 ; selected section index
    mov     qword [rsp + 40], 0 ; selected-match count, saturated at two

    cmp     qword [rbp + SHDR_CTX_HAS_NAMES], 0
    je      .not_found

    xor     rbx, rbx
.loop:
    cmp     rbx, [rbp + SHDR_CTX_COUNT]
    jae     .finish_search

    mov     rdi, [rbp + SHDR_CTX_FILE_SIZE]
    mov     r12, [rbp + SHDR_CTX_BASE]
    mov     rsi, [r12 + E_SHOFF]
    mov     rdx, ELF64_SHDR_SIZE
    mov     rcx, [rbp + SHDR_CTX_COUNT]
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .not_found

    mov     rax, [rsp]
    mov     r12, [rbp + SHDR_CTX_BASE]
    lea     r12, [r12 + rax]    ; current section header

    mov     eax, [r12 + S_TYPE]
    cmp     eax, SHT_NULL
    je      .next
    cmp     eax, SHT_NOBITS
    je      .next

    ; Labels are for executable-region/gadget addresses only. Requiring both
    ; SHF_ALLOC and SHF_EXECINSTR prevents a hostile metadata section such as
    ; .shstrtab from capturing runtime code offsets by appearing earlier.
    mov     rax, [r12 + S_FLAGS]
    mov     rdx, SHF_ALLOC | SHF_EXECINSTR
    and     rax, rdx
    cmp     rax, rdx
    jne     .next

    mov     r13, [r12 + S_SIZE]
    test    r13, r13
    jz      .next

    mov     rdi, [rbp + SHDR_CTX_FILE_SIZE]
    mov     rsi, [r12 + S_OFFSET]
    mov     rdx, r13
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .next

    mov     rax, [rsp + 8]      ; target file offset
    cmp     rax, [r12 + S_OFFSET]
    jb      .next
    cmp     rax, [rsp]          ; checked exclusive section-file end
    jae     .next

    ; A section label also has to agree with the runtime VA being annotated.
    ; Section headers remain annotations, but hostile metadata should not label
    ; loader-backed code only because its file offset happens to overlap.
    mov     rax, [rsp + 48]     ; target virtual address
    cmp     rax, [r12 + S_ADDR]
    jb      .next
    mov     rdi, [r12 + S_ADDR]
    mov     rsi, r13
    lea     rdx, [rsp]
    call    x64lens_bounds_add_u64_checked
    cmp     rax, 1
    jne     .next
    mov     rax, [rsp + 48]
    cmp     rax, [rsp]          ; checked exclusive section-VA end
    jae     .next

    mov     eax, [r12 + S_NAME]
    test    rax, rax
    jz      .next
    cmp     rax, [rbp + SHDR_CTX_SHSTR_SIZE]
    jae     .next

    mov     r13, [rbp + SHDR_CTX_SHSTR_SIZE]
    sub     r13, rax            ; bytes remaining in section-name string table
    mov     r14, [rbp + SHDR_CTX_SHSTR_PTR]
    add     r14, rax            ; candidate section-name pointer
    xor     r15, r15
.name_loop:
    cmp     r15, r13
    jae     .next
    cmp     byte [r14 + r15], 0
    je      .have_name
    inc     r15
    jmp     .name_loop

.have_name:
    test    r15, r15
    jz      .next
    cmp     qword [rsp + 40], 0
    jne     .ambiguous_match
    mov     [rsp + 16], r14
    mov     [rsp + 24], r15
    mov     [rsp + 32], rbx
    mov     qword [rsp + 40], 1
    jmp     .next

.ambiguous_match:
    mov     qword [rsp + 40], 2
    jmp     .next

.next:
    inc     rbx
    jmp     .loop

.finish_search:
    cmp     qword [rsp + 40], 1
    jne     .not_found
    mov     rax, [rsp + 16]
    mov     rdx, [rsp + 24]
    mov     rcx, [rsp + 32]
    jmp     .done

.not_found:
    xor     rax, rax
    xor     rdx, rdx
    xor     rcx, rcx
.done:
    add     rsp, 56
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
