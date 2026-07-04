; mitigations.asm
;
; Purpose:
;   Command-level orchestration for `x64lens mitigations <file>`.
;
; Module scope:
;   Map a target file, validate ELF64 identity, analyze program headers, and
;   emit baseline mitigation and executable-region metadata. The low-level
;   program-header iteration lives in phdr.asm. Output formatting lives in
;   report_text.asm. This module owns command cleanup and error reporting.
;
; Sprint 2 scope:
;   Baseline NX stack, PIE, RWX PT_LOAD, PT_GNU_RELRO, PT_DYNAMIC, and
;   executable PT_LOAD + PF_X region discovery.
;
; Non-goal:
;   This command does not claim that a binary is exploitable. It reports
;   loader-level facts and mitigation indicators that constrain later analysis.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_file_map
extern x64lens_file_unmap
extern x64lens_elf64_validate
extern x64lens_phdr_analyze
extern x64lens_shdr_classify_stripped
extern x64lens_shdr_annotate_exec_regions
extern x64lens_report_text_mitigations
extern x64lens_error_print_status

section .bss
mit_mapped_file:  resb FILEMAP_RECORD_SIZE
mit_summary:      resb PHDR_SUMMARY_RECORD_SIZE
mit_regions:      resb EXEC_REGION_RECORD_SIZE * EXEC_REGION_MAX

section .text
global x64lens_command_mitigations

; x64lens_command_mitigations(path_cstr=rdi) -> rax=status
;
; Returns a stable x64lens exit code. The caller owns process exit.
; The command path mirrors info.asm so new analysis commands follow one
; predictable pattern: map, validate, analyze, report, cleanup.
x64lens_command_mitigations:
    push    rbx
    push    r12
    push    r13

    mov     r12, rdi            ; preserve target path for reporting

    ; Map target file read-only. The target is untrusted and never executed.
    mov     rdi, r12
    lea     rsi, [mit_mapped_file]
    call    x64lens_file_map
    test    rax, rax
    jne     .error

    ; Reuse Sprint 1 ELF64 validation before program-header analysis.
    mov     rdi, [mit_mapped_file + FILEMAP_ADDR]
    mov     rsi, [mit_mapped_file + FILEMAP_SIZE]
    call    x64lens_elf64_validate
    test    rax, rax
    jne     .error

    ; Populate PHDR summary and executable-region records.
    mov     rdi, [mit_mapped_file + FILEMAP_ADDR]
    mov     rsi, [mit_mapped_file + FILEMAP_SIZE]
    lea     rdx, [mit_summary]
    lea     rcx, [mit_regions]
    mov     r8, EXEC_REGION_MAX
    call    x64lens_phdr_analyze
    test    rax, rax
    jne     .error

    ; Section-derived metadata is an analyst indicator only. It must never
    ; change executable-region boundaries selected from PT_LOAD + PF_X.
    mov     rdi, [mit_mapped_file + FILEMAP_ADDR]
    mov     rsi, [mit_mapped_file + FILEMAP_SIZE]
    lea     rdx, [mit_summary]
    call    x64lens_shdr_classify_stripped
    test    rax, rax
    jne     .error

    ; Add optional section labels to executable-region records. These labels
    ; are annotations only and do not influence region selection.
    mov     rdi, [mit_mapped_file + FILEMAP_ADDR]
    mov     rsi, [mit_mapped_file + FILEMAP_SIZE]
    lea     rdx, [mit_regions]
    mov     rcx, [mit_summary + PHDR_SUMMARY_EXEC_COUNT]
    call    x64lens_shdr_annotate_exec_regions
    test    rax, rax
    jne     .error

    ; Emit human-readable Sprint 2 mitigation report.
    mov     rdi, r12
    mov     rsi, [mit_mapped_file + FILEMAP_ADDR]
    mov     rdx, [mit_mapped_file + FILEMAP_SIZE]
    lea     rcx, [mit_summary]
    lea     r8, [mit_regions]
    call    x64lens_report_text_mitigations

    lea     rdi, [mit_mapped_file]
    call    x64lens_file_unmap
    xor     rax, rax
    jmp     .done

.error:
    ; Preserve the failing status across cleanup and error reporting.
    mov     r13, rax
    lea     rdi, [mit_mapped_file]
    call    x64lens_file_unmap
    mov     rdi, r13
    call    x64lens_error_print_status
    mov     rax, r13

.done:
    pop     r13
    pop     r12
    pop     rbx
    ret
