; elf64.asm
;
; Purpose:
;   ELF64 validation and metadata parsing.
;
; Module scope:
;   Validate ELF magic, class, endianness, machine type, and basic header
;   ranges before deeper parsing. This module treats all target bytes as
;   untrusted and uses bounds helpers before reading offset-derived ranges.
;
; Current boundary:
;   This module validates fixed ELF64 header fields, header-table ranges, and
;   file-backed PT_LOAD ranges. Command-specific program-header semantics,
;   mitigation interpretation, region discovery, and gadget analysis remain in
;   their dedicated modules.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"

extern x64lens_bounds_has_size
extern x64lens_bounds_range_valid

section .text
global x64lens_elf64_validate

; x64lens_elf64_validate(mapped_base=rdi, file_size=rsi) -> rax=status
;
; Success:
;   RAX = EXIT_OK
;
; Failure:
;   RAX = EXIT_NOT_ELF64_X64 when the target is the wrong format/class/endian/arch
;   RAX = EXIT_MALFORMED_ELF when ELF-declared offsets or sizes are unsafe
x64lens_elf64_validate:
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 8              ; preserve 16-byte call-site alignment

    mov     rbx, rdi            ; mapped base
    mov     r12, rsi            ; file size

    ; Need at least four bytes before checking the ELF magic. Files that
    ; have enough bytes for a magic check but do not match are classified as
    ; non-ELF. Files that start with ELF magic but are too short for an ELF64
    ; header are malformed/truncated ELF.
    mov     rdi, r12
    mov     rsi, 4
    call    x64lens_bounds_has_size
    cmp     rax, 1
    jne     .malformed

    ; ELF magic check.
    cmp     byte [rbx + EI_MAG0], ELFMAG0
    jne     .not_elf64_x64
    cmp     byte [rbx + EI_MAG1], ELFMAG1
    jne     .not_elf64_x64
    cmp     byte [rbx + EI_MAG2], ELFMAG2
    jne     .not_elf64_x64
    cmp     byte [rbx + EI_MAG3], ELFMAG3
    jne     .not_elf64_x64

    ; Full ELF64 header-size check before reading the rest of e_ident and the
    ; fixed header fields.
    mov     rdi, r12
    mov     rsi, ELF64_EHDR_SIZE
    call    x64lens_bounds_has_size
    cmp     rax, 1
    jne     .malformed

    ; ELF identity checks.
    cmp     byte [rbx + EI_CLASS], ELFCLASS64
    jne     .not_elf64_x64
    cmp     byte [rbx + EI_DATA], ELFDATA2LSB
    jne     .not_elf64_x64
    cmp     byte [rbx + EI_VERSION], 1
    jne     .malformed

    ; Machine and ELF-header sanity checks.
    cmp     word [rbx + E_MACHINE], EM_X86_64
    jne     .not_elf64_x64
    cmp     dword [rbx + E_VERSION_OFF], 1
    jne     .malformed
    cmp     word [rbx + E_EHSIZE], ELF64_EHDR_SIZE
    jne     .malformed

    ; Validate program header table range when present.
    movzx   r13, word [rbx + E_PHNUM]
    test    r13, r13
    je      .check_sections
    cmp     word [rbx + E_PHENTSIZE], ELF64_PHDR_SIZE
    jne     .malformed
    mov     rsi, [rbx + E_PHOFF]
    test    rsi, rsi
    je      .malformed
    movzx   rdx, word [rbx + E_PHENTSIZE]
    imul    rdx, r13
    mov     rdi, r12
    call    x64lens_bounds_range_valid
    cmp     rax, 1
    jne     .malformed

    ; Validate every file-backed PT_LOAD range before any command reports ELF
    ; metadata. This keeps info, mitigations, and analyze aligned on malformed
    ; loader input. A later shared-arithmetic refactor can consolidate the
    ; repeated offset and table calculations without changing this policy.
    xor     r14, r14
.validate_program_headers:
    cmp     r14, r13
    jae     .check_sections

    mov     rax, r14
    imul    rax, rax, ELF64_PHDR_SIZE
    add     rax, [rbx + E_PHOFF]
    lea     r10, [rbx + rax]

    cmp     dword [r10 + P_TYPE], PT_LOAD
    jne     .next_program_header

    mov     rax, [r10 + P_FILESZ]
    cmp     rax, [r10 + P_MEMSZ]
    ja      .malformed

    mov     rdi, r12
    mov     rsi, [r10 + P_OFFSET]
    mov     rdx, [r10 + P_FILESZ]
    call    x64lens_bounds_range_valid
    cmp     rax, 1
    jne     .malformed

.next_program_header:
    inc     r14
    jmp     .validate_program_headers

.check_sections:
    ; Validate section header table range when present. Section headers are
    ; not authoritative for runtime mapping, but unsafe section offsets still
    ; indicate malformed input and must be rejected before future SHDR parsing.
    movzx   r13, word [rbx + E_SHNUM]
    test    r13, r13
    je      .ok
    ; ELF64 section-table entries have a fixed 64-byte layout. Accepting an
    ; arbitrary nonzero entry size would make future section iteration depend
    ; on an invalid stride, so reject it before any SHDR parser is enabled.
    cmp     word [rbx + E_SHENTSIZE], ELF64_SHDR_SIZE
    jne     .malformed
    mov     rsi, [rbx + E_SHOFF]
    test    rsi, rsi
    je      .malformed
    movzx   rdx, word [rbx + E_SHENTSIZE]
    imul    rdx, r13
    mov     rdi, r12
    call    x64lens_bounds_range_valid
    cmp     rax, 1
    jne     .malformed

.ok:
    xor     rax, rax
    jmp     .done
.not_elf64_x64:
    mov     rax, EXIT_NOT_ELF64_X64
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
.done:
    add     rsp, 8
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
