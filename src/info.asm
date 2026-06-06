; info.asm
;
; Purpose:
;   Command-level orchestration for `x64lens info <file>`.
;
; Module scope:
;   This module wires together file mapping, ELF64 validation, text reporting,
;   error reporting, and cleanup. It should remain a coordinator. Format
;   parsing belongs in elf64.asm. Resource acquisition belongs in filemap.asm.
;   Output formatting belongs in report_text.asm.
;
; Contract alignment:
;   - Parser safety: validation happens before metadata reporting.
;   - Module boundaries: this module calls specialized modules instead of
;     owning their logic.
;   - Implementation completion: tests should verify valid ELF success and
;     invalid input rejection.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_file_map
extern x64lens_file_unmap
extern x64lens_elf64_validate
extern x64lens_report_text_elf64_info
extern x64lens_error_print_status

section .bss
info_mapped_file: resb FILEMAP_RECORD_SIZE

section .text
global x64lens_command_info

; x64lens_command_info(path_cstr=rdi) -> rax=status
;
; Returns a stable x64lens exit code. The caller owns process exit.
x64lens_command_info:
    push    rbx
    push    r12
    push    r13

    mov     r12, rdi            ; preserve target path for reporting

    ; Map the target file read-only.
    mov     rdi, r12
    lea     rsi, [info_mapped_file]
    call    x64lens_file_map
    test    rax, rax
    jne     .error

    ; Validate that the mapped target is ELF64 x86_64 little-endian before
    ; any report routine reads ELF fields.
    mov     rdi, [info_mapped_file + FILEMAP_ADDR]
    mov     rsi, [info_mapped_file + FILEMAP_SIZE]
    call    x64lens_elf64_validate
    test    rax, rax
    jne     .error

    ; Emit the Sprint 1 human-readable info report.
    mov     rdi, r12
    mov     rsi, [info_mapped_file + FILEMAP_ADDR]
    mov     rdx, [info_mapped_file + FILEMAP_SIZE]
    call    x64lens_report_text_elf64_info

    ; Cleanup after successful analysis.
    lea     rdi, [info_mapped_file]
    call    x64lens_file_unmap
    xor     rax, rax
    jmp     .done

.error:
    ; Preserve the status code across cleanup and error reporting.
    mov     r13, rax
    lea     rdi, [info_mapped_file]
    call    x64lens_file_unmap
    mov     rdi, r13
    call    x64lens_error_print_status
    mov     rax, r13

.done:
    pop     r13
    pop     r12
    pop     rbx
    ret
