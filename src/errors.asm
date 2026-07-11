; errors.asm
;
; Purpose:
;   Error reporting helpers. Exit-code values live in include/errors.inc;
;   this module maps those stable codes to human-readable diagnostics.
;
; Design rule:
;   Error messages should be explicit enough for CLI users and test logs, but
;   they should not leak internal implementation details or imply exploitability.

bits 64
default rel

%include "errors.inc"

extern print_cstr_err

section .rodata
msg_general:      db "error: general failure", 10, 0
msg_usage:        db "error: invalid command usage", 10, 0
msg_file:         db "error: file open/stat/map failure", 10, 0
msg_not_elf:      db "error: target is not an ELF64 x86_64 little-endian binary", 10, 0
msg_malformed:    db "error: malformed or truncated ELF", 10, 0
msg_unsupported:  db "error: unsupported binary feature", 10, 0
msg_bounds:       db "error: internal bounds check failure", 10, 0

section .text
global x64lens_error_print_status

; x64lens_error_print_status(rdi=status)
;
; Inputs:
;   RDI = stable x64lens exit/error code
;
; Output:
;   Prints a matching diagnostic to STDERR.
;
; Notes:
;   The function does not exit. The caller owns cleanup and process exit.
x64lens_error_print_status:
    cmp     rdi, EXIT_USAGE
    je      .usage
    cmp     rdi, EXIT_FILE
    je      .file
    cmp     rdi, EXIT_NOT_ELF64_X64
    je      .not_elf
    cmp     rdi, EXIT_MALFORMED_ELF
    je      .malformed
    cmp     rdi, EXIT_UNSUPPORTED
    je      .unsupported
    cmp     rdi, EXIT_BOUNDS
    je      .bounds
    lea     rdi, [msg_general]
    jmp     .print
.usage:
    lea     rdi, [msg_usage]
    jmp     .print
.file:
    lea     rdi, [msg_file]
    jmp     .print
.not_elf:
    lea     rdi, [msg_not_elf]
    jmp     .print
.malformed:
    lea     rdi, [msg_malformed]
    jmp     .print
.unsupported:
    lea     rdi, [msg_unsupported]
    jmp     .print
.bounds:
    lea     rdi, [msg_bounds]
.print:
    jmp     print_cstr_err
