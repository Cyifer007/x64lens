; elf64.asm
;
; Purpose:
;   ELF64 identity, header-table, and extended-numbering validation.
;
; Module scope:
;   Validate ELF magic, class, endianness, machine type, fixed header fields,
;   ordinary program-header loader contracts, bounded section-table structure,
;   and the structural prerequisites for ELF extended numbering.
;
; Patch 062 boundary:
;   Ordinary program headers receive bounded p_align, congruence, virtual-end,
;   and executable-entrypoint validation through phdr.asm. Extended-numbering
;   encodings are detected and structurally validated, then return the stable
;   unsupported status before any reporter consumes sentinel values. Program
;   headers remain runtime mapping authority; section header zero is consulted
;   only because the ELF ABI stores extended counts there.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"

extern x64lens_bounds_has_size
extern x64lens_bounds_range_end_valid
extern x64lens_bounds_table_extent_valid
extern x64lens_phdr_validate_loader_contract

section .text
global x64lens_elf64_validate

; x64lens_elf64_validate(mapped_base=rdi, file_size=rsi) -> rax=status
;
; Success:
;   RAX = EXIT_OK
;
; Failure:
;   RAX = EXIT_NOT_ELF64_X64 for the wrong format/class/endian/architecture
;   RAX = EXIT_MALFORMED_ELF for unsafe or contradictory ELF structure
;   RAX = EXIT_UNSUPPORTED for structurally valid extended numbering
x64lens_elf64_validate:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 32             ; call alignment and bounded-table scratch

    mov     r15, rdi            ; mapped base
    mov     r14, rsi            ; file size

    ; Need at least four bytes before checking the ELF magic. A matching magic
    ; followed by a short header is malformed/truncated ELF rather than a
    ; generic non-ELF input.
    mov     rdi, r14
    mov     rsi, 4
    call    x64lens_bounds_has_size
    cmp     rax, 1
    jne     .malformed

    cmp     byte [r15 + EI_MAG0], ELFMAG0
    jne     .not_elf64_x64
    cmp     byte [r15 + EI_MAG1], ELFMAG1
    jne     .not_elf64_x64
    cmp     byte [r15 + EI_MAG2], ELFMAG2
    jne     .not_elf64_x64
    cmp     byte [r15 + EI_MAG3], ELFMAG3
    jne     .not_elf64_x64

    mov     rdi, r14
    mov     rsi, ELF64_EHDR_SIZE
    call    x64lens_bounds_has_size
    cmp     rax, 1
    jne     .malformed

    cmp     byte [r15 + EI_CLASS], ELFCLASS64
    jne     .not_elf64_x64
    cmp     byte [r15 + EI_DATA], ELFDATA2LSB
    jne     .not_elf64_x64
    cmp     byte [r15 + EI_VERSION], 1
    jne     .malformed
    cmp     word [r15 + E_MACHINE], EM_X86_64
    jne     .not_elf64_x64
    cmp     dword [r15 + E_VERSION_OFF], 1
    jne     .malformed
    cmp     word [r15 + E_EHSIZE], ELF64_EHDR_SIZE
    jne     .malformed

    ; Detect all ELF64 extended-numbering sentinels before ordinary table
    ; validation. Bit 0 = PN_XNUM, bit 1 = extended section count, bit 2 =
    ; extended section-name-table index.
    xor     ebx, ebx
    movzx   r13, word [r15 + E_PHNUM]
    cmp     r13, PN_XNUM
    jne     .extended_shnum
    or      ebx, 1
.extended_shnum:
    movzx   rax, word [r15 + E_SHNUM]
    test    rax, rax
    jnz     .extended_shstr
    cmp     qword [r15 + E_SHOFF], 0
    je      .extended_shstr
    or      ebx, 2
.extended_shstr:
    cmp     word [r15 + E_SHSTRNDX], SHN_XINDEX
    jne     .extended_dispatch
    or      ebx, 4
.extended_dispatch:
    test    ebx, ebx
    jnz     .validate_extended_numbering

    ; Reserved section-count and section-index values require the extended
    ; encodings above. Accepting them as ordinary values would reinterpret ABI
    ; sentinels as table counts or indexes.
    movzx   rax, word [r15 + E_SHNUM]
    cmp     rax, SHN_LORESERVE
    jae     .malformed
    movzx   rax, word [r15 + E_SHSTRNDX]
    cmp     rax, SHN_LORESERVE
    jae     .malformed

    ; Ordinary PHDR validation is centralized in phdr.asm so identity checks
    ; and command-level analysis share exactly one loader policy.
    mov     rdi, r15
    mov     rsi, r14
    mov     rdx, r13
    call    x64lens_phdr_validate_loader_contract
    test    rax, rax
    jne     .done

    ; Section headers remain metadata only. Validate the full fixed-stride
    ; table and the section-name-table index when an ordinary table exists.
    movzx   r12, word [r15 + E_SHNUM]
    test    r12, r12
    jnz     .ordinary_sections
    cmp     qword [r15 + E_SHOFF], 0
    jne     .malformed
    cmp     word [r15 + E_SHSTRNDX], SHN_UNDEF
    jne     .malformed
    jmp     .ok

.ordinary_sections:
    cmp     word [r15 + E_SHENTSIZE], ELF64_SHDR_SIZE
    jne     .malformed
    mov     rsi, [r15 + E_SHOFF]
    test    rsi, rsi
    jz      .malformed
    mov     rdi, r14
    mov     rdx, ELF64_SHDR_SIZE
    mov     rcx, r12
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .malformed

    ; Section-header entry zero is the reserved SHT_NULL record.  In an
    ; ordinary table none of its extended-numbering carrier fields is active,
    ; so the entire record must remain the canonical all-zero null entry.
    mov     rax, [r15 + E_SHOFF]
    lea     r13, [r15 + rax]
    cmp     dword [r13 + S_NAME], 0
    jne     .malformed
    cmp     dword [r13 + S_TYPE], SHT_NULL
    jne     .malformed
    cmp     qword [r13 + S_FLAGS], 0
    jne     .malformed
    cmp     qword [r13 + S_ADDR], 0
    jne     .malformed
    cmp     qword [r13 + S_OFFSET], 0
    jne     .malformed
    cmp     qword [r13 + S_SIZE], 0
    jne     .malformed
    cmp     dword [r13 + S_LINK], 0
    jne     .malformed
    cmp     dword [r13 + S_INFO], 0
    jne     .malformed
    cmp     qword [r13 + S_ADDRALIGN], 0
    jne     .malformed
    cmp     qword [r13 + S_ENTSIZE], 0
    jne     .malformed

    movzx   rax, word [r15 + E_SHSTRNDX]
    test    rax, rax
    jz      .ok
    cmp     rax, r12
    jae     .malformed
    jmp     .ok

.validate_extended_numbering:
    ; Every extended form depends on section header zero. Validate that entry
    ; first without trusting the eventual extended count.
    cmp     word [r15 + E_SHENTSIZE], ELF64_SHDR_SIZE
    jne     .malformed
    mov     r12, [r15 + E_SHOFF]
    test    r12, r12
    jz      .malformed
    mov     rdi, r14
    mov     rsi, r12
    mov     rdx, ELF64_SHDR_SIZE
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .malformed
    lea     r13, [r15 + r12]    ; bounded section-header entry zero
    cmp     dword [r13 + S_NAME], 0
    jne     .malformed
    cmp     dword [r13 + S_TYPE], SHT_NULL
    jne     .malformed
    cmp     qword [r13 + S_FLAGS], 0
    jne     .malformed
    cmp     qword [r13 + S_ADDR], 0
    jne     .malformed
    cmp     qword [r13 + S_OFFSET], 0
    jne     .malformed
    cmp     qword [r13 + S_ADDRALIGN], 0
    jne     .malformed
    cmp     qword [r13 + S_ENTSIZE], 0
    jne     .malformed

    ; Only the carrier selected by an active sentinel may be nonzero.  This
    ; prevents hidden contradictory counts/indexes from surviving underneath a
    ; different extended-numbering form.
    test    ebx, 2
    jnz     .extended_sh0_size_ready
    cmp     qword [r13 + S_SIZE], 0
    jne     .malformed
.extended_sh0_size_ready:
    test    ebx, 4
    jnz     .extended_sh0_link_ready
    cmp     dword [r13 + S_LINK], 0
    jne     .malformed
.extended_sh0_link_ready:
    test    ebx, 1
    jnz     .extended_sh0_info_ready
    cmp     dword [r13 + S_INFO], 0
    jne     .malformed
.extended_sh0_info_ready:

    ; Resolve the actual section count only for structural validation. A normal
    ; e_shnum remains authoritative when section-count extension is inactive.
    test    ebx, 2
    jz      .extended_normal_shnum
    mov     r12, [r13 + S_SIZE]
    cmp     r12, SHN_LORESERVE
    jb      .malformed
    jmp     .extended_shnum_ready
.extended_normal_shnum:
    movzx   r12, word [r15 + E_SHNUM]
    test    r12, r12
    jz      .malformed
    cmp     r12, SHN_LORESERVE
    jae     .malformed
.extended_shnum_ready:
    mov     rdi, r14
    mov     rsi, [r15 + E_SHOFF]
    mov     rdx, ELF64_SHDR_SIZE
    mov     rcx, r12
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .malformed

    ; PN_XNUM stores the real program-header count in sh_info. Validate its
    ; reserved-domain value and complete fixed-stride table before refusing the
    ; feature. This distinguishes safe unsupported input from malformed input.
    test    ebx, 1
    jz      .extended_shstr_check
    mov     eax, [r13 + S_INFO]
    cmp     rax, PN_XNUM
    jb      .malformed
    cmp     word [r15 + E_PHENTSIZE], ELF64_PHDR_SIZE
    jne     .malformed
    mov     rsi, [r15 + E_PHOFF]
    test    rsi, rsi
    jz      .malformed
    mov     rdi, r14
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, rax
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .malformed

.extended_shstr_check:
    ; When SHN_XINDEX is not active, validate the ordinary section-name-table
    ; index against the resolved section count. Reserved values still require
    ; the sentinel form even when another extended-numbering feature is active.
    test    ebx, 4
    jnz     .extended_shstr_value
    movzx   rax, word [r15 + E_SHSTRNDX]
    test    rax, rax
    jz      .unsupported
    cmp     rax, SHN_LORESERVE
    jae     .malformed
    cmp     rax, r12
    jae     .malformed
    jmp     .unsupported

.extended_shstr_value:
    ; SHN_XINDEX stores the actual section-name-table index in sh_link. It must
    ; name an entry inside the resolved section table and belong to the reserved
    ; index domain that requires the sentinel.
    mov     eax, [r13 + S_LINK]
    cmp     rax, SHN_LORESERVE
    jb      .malformed
    cmp     rax, r12
    jae     .malformed

.unsupported:
    mov     rax, EXIT_UNSUPPORTED
    jmp     .done
.ok:
    xor     rax, rax
    jmp     .done
.not_elf64_x64:
    mov     rax, EXIT_NOT_ELF64_X64
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
.done:
    add     rsp, 32
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
