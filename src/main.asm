; main.asm
;
; Purpose:
;   Process entrypoint for x64lens. Because the project intentionally avoids
;   libc in the core binary, execution begins at `_start` and reads `argc`
;   and `argv` directly from the Linux process stack.
;
; Current behavior:
;   x64lens version
;   x64lens help
;   x64lens info <file>
;
; Sprint 1 implementation target:
;   Keep command dispatch simple while routing `info <file>` through the real
;   file mapping and ELF64 validation path.
;
; Safety note:
;   This module should not parse target files directly. It should dispatch
;   to CLI/analysis modules and centralize process exit behavior.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"

extern cstr_eq
extern cli_print_help
extern x64lens_command_info
extern version_print

section .rodata
cmd_help:       db "help", 0
cmd_version:    db "version", 0
cmd_info:       db "info", 0

section .text
global _start

_start:
    ; Linux x86_64 process entry stack:
    ;   [rsp]      = argc
    ;   [rsp + 8]  = argv[0]
    ;   [rsp + 16] = argv[1]
    ;   [rsp + 24] = argv[2]
    ;
    ; We keep argc in RBX and the argv base in R12 because both are callee-
    ; saved registers under the System V AMD64 ABI. This makes the simple
    ; command-dispatch calls easier to reason about.
    mov     rbx, [rsp]
    lea     r12, [rsp + 8]

    ; With no command, show usage and return the stable usage error code.
    cmp     rbx, 2
    jl      .show_help

    ; Match argv[1] against known commands. This is intentionally explicit
    ; in Sprint 1. A table-driven dispatcher can be added later if command
    ; count grows enough to justify it.
    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_help]
    call    cstr_eq
    cmp     rax, 1
    je      .show_help_ok

    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_version]
    call    cstr_eq
    cmp     rax, 1
    je      .show_version

    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_info]
    call    cstr_eq
    cmp     rax, 1
    je      .info

    ; Unknown command. Show help and exit with usage error.
    jmp     .show_help

.show_help_ok:
    call    cli_print_help
    mov     rdi, EXIT_OK
    jmp     .exit

.show_help:
    call    cli_print_help
    mov     rdi, EXIT_USAGE
    jmp     .exit

.show_version:
    call    version_print
    mov     rdi, EXIT_OK
    jmp     .exit

.info:
    ; `info` requires a target file argument and now routes through the
    ; Sprint 1 file mapping and ELF64 validation path. The command returns a
    ; stable x64lens exit code in RAX, which becomes the process exit code.
    cmp     rbx, 3
    jl      .show_help
    mov     rdi, [r12 + 16]
    call    x64lens_command_info
    mov     rdi, rax
    jmp     .exit

.exit:
    ; Centralized process exit path. Future cleanup should happen before
    ; jumping here, not after this syscall.
    mov     rax, SYS_EXIT
    syscall
