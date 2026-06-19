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
;   x64lens mitigations <file>
;   x64lens gadgets [--format text|json] [--max-depth N] <file>
;   x64lens analyze [--format text|json] [--max-depth N] <file>
;
; Sprint 6 implementation target:
;   Keep command dispatch simple while routing `info`, `mitigations`,
;   `gadgets`, and integrated `analyze` reports through specialized command
;   orchestrators.
;
; Safety note:
;   This module should not parse target files directly. It should dispatch
;   to CLI/analysis modules and centralize process exit behavior.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"

extern cstr_eq
extern cli_parse_u64
extern cli_print_help
extern x64lens_command_info
extern x64lens_command_mitigations
extern x64lens_command_gadgets
extern x64lens_command_gadgets_json
extern x64lens_command_analyze
extern x64lens_command_analyze_json
extern version_print

section .rodata
cmd_help:       db "help", 0
cmd_version:    db "version", 0
cmd_info:       db "info", 0
cmd_mitigations: db "mitigations", 0
cmd_gadgets:     db "gadgets", 0
cmd_analyze:     db "analyze", 0
flag_max_depth:  db "--max-depth", 0
flag_format:     db "--format", 0
format_text:     db "text", 0
format_json:     db "json", 0

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

    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_mitigations]
    call    cstr_eq
    cmp     rax, 1
    je      .mitigations

    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_gadgets]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets

    mov     rdi, [r12 + 8]
    lea     rsi, [cmd_analyze]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze

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

.mitigations:
    ; `mitigations` requires a target file argument and routes through the
    ; Sprint 2 program-header analysis path. It reports loader-level
    ; mitigation indicators and executable PT_LOAD regions.
    cmp     rbx, 3
    jl      .show_help
    mov     rdi, [r12 + 16]
    call    x64lens_command_mitigations
    mov     rdi, rax
    jmp     .exit

.gadgets:
    ; `gadgets` requires a target file argument. Sprint 5 adds the narrow
    ; machine-readable form `--format json` while preserving the existing text
    ; output and `--max-depth N` behavior.
    cmp     rbx, 3
    je      .gadgets_default
    cmp     rbx, 5
    je      .gadgets_one_flag
    cmp     rbx, 7
    je      .gadgets_two_flags
    jmp     .show_help

.gadgets_default:
    ; Treat a bare known flag without its required value and target as usage
    ; error, not as an attempted filename.
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .show_help
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .show_help

    mov     rdi, [r12 + 16]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_gadgets
    mov     rdi, rax
    jmp     .exit

.gadgets_one_flag:
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_depth_text

    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_default_depth

    jmp     .show_help

.gadgets_depth_text:
    mov     rdi, [r12 + 24]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help

    mov     rsi, rax            ; parsed max depth
    mov     rdi, [r12 + 32]     ; target path
    call    x64lens_command_gadgets
    mov     rdi, rax
    jmp     .exit

.gadgets_format_default_depth:
    mov     rdi, [r12 + 24]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_default_depth_json

    mov     rdi, [r12 + 24]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_default_depth_text

    jmp     .show_help

.gadgets_format_default_depth_json:
    mov     rdi, [r12 + 32]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_gadgets_json
    mov     rdi, rax
    jmp     .exit

.gadgets_format_default_depth_text:
    mov     rdi, [r12 + 32]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_gadgets
    mov     rdi, rax
    jmp     .exit

.gadgets_two_flags:
    ; Supported orders:
    ;   gadgets --format json --max-depth N <file>
    ;   gadgets --max-depth N --format json <file>
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_then_depth

    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_depth_then_format

    jmp     .show_help

.gadgets_format_then_depth:
    mov     rdi, [r12 + 32]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    jne     .show_help

    mov     rdi, [r12 + 40]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help
    mov     r14, rax            ; parsed max depth

    mov     rdi, [r12 + 24]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_then_depth_json

    mov     rdi, [r12 + 24]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_format_then_depth_text

    jmp     .show_help

.gadgets_format_then_depth_json:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_gadgets_json
    mov     rdi, rax
    jmp     .exit

.gadgets_format_then_depth_text:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_gadgets
    mov     rdi, rax
    jmp     .exit

.gadgets_depth_then_format:
    mov     rdi, [r12 + 32]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    jne     .show_help

    mov     rdi, [r12 + 24]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help
    mov     r14, rax            ; parsed max depth

    mov     rdi, [r12 + 40]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_depth_then_format_json

    mov     rdi, [r12 + 40]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .gadgets_depth_then_format_text

    jmp     .show_help

.gadgets_depth_then_format_json:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_gadgets_json
    mov     rdi, rax
    jmp     .exit

.gadgets_depth_then_format_text:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_gadgets
    mov     rdi, rax
    jmp     .exit

.analyze:
    ; `analyze` requires a target file argument. Sprint 6 exposes the
    ; integrated checkpoint report while preserving the existing text/JSON
    ; output and `--max-depth N` behavior.
    cmp     rbx, 3
    je      .analyze_default
    cmp     rbx, 5
    je      .analyze_one_flag
    cmp     rbx, 7
    je      .analyze_two_flags
    jmp     .show_help

.analyze_default:
    ; Treat a bare known flag without its required value and target as usage
    ; error, not as an attempted filename.
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .show_help
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .show_help

    mov     rdi, [r12 + 16]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_analyze
    mov     rdi, rax
    jmp     .exit

.analyze_one_flag:
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_depth_text

    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_default_depth

    jmp     .show_help

.analyze_depth_text:
    mov     rdi, [r12 + 24]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help

    mov     rsi, rax            ; parsed max depth
    mov     rdi, [r12 + 32]     ; target path
    call    x64lens_command_analyze
    mov     rdi, rax
    jmp     .exit

.analyze_format_default_depth:
    mov     rdi, [r12 + 24]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_default_depth_json

    mov     rdi, [r12 + 24]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_default_depth_text

    jmp     .show_help

.analyze_format_default_depth_json:
    mov     rdi, [r12 + 32]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_analyze_json
    mov     rdi, rax
    jmp     .exit

.analyze_format_default_depth_text:
    mov     rdi, [r12 + 32]
    mov     rsi, GADGET_DEFAULT_MAX_DEPTH
    call    x64lens_command_analyze
    mov     rdi, rax
    jmp     .exit

.analyze_two_flags:
    ; Supported orders:
    ;   analyze --format json --max-depth N <file>
    ;   analyze --max-depth N --format json <file>
    mov     rdi, [r12 + 16]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_then_depth

    mov     rdi, [r12 + 16]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_depth_then_format

    jmp     .show_help

.analyze_format_then_depth:
    mov     rdi, [r12 + 32]
    lea     rsi, [flag_max_depth]
    call    cstr_eq
    cmp     rax, 1
    jne     .show_help

    mov     rdi, [r12 + 40]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help
    mov     r14, rax            ; parsed max depth

    mov     rdi, [r12 + 24]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_then_depth_json

    mov     rdi, [r12 + 24]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_format_then_depth_text

    jmp     .show_help

.analyze_format_then_depth_json:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_analyze_json
    mov     rdi, rax
    jmp     .exit

.analyze_format_then_depth_text:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_analyze
    mov     rdi, rax
    jmp     .exit

.analyze_depth_then_format:
    mov     rdi, [r12 + 32]
    lea     rsi, [flag_format]
    call    cstr_eq
    cmp     rax, 1
    jne     .show_help

    mov     rdi, [r12 + 24]
    call    cli_parse_u64
    cmp     rdx, 1
    jne     .show_help
    test    rax, rax
    jz      .show_help
    cmp     rax, GADGET_MAX_DEPTH_LIMIT
    ja      .show_help
    mov     r14, rax            ; parsed max depth

    mov     rdi, [r12 + 40]
    lea     rsi, [format_json]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_depth_then_format_json

    mov     rdi, [r12 + 40]
    lea     rsi, [format_text]
    call    cstr_eq
    cmp     rax, 1
    je      .analyze_depth_then_format_text

    jmp     .show_help

.analyze_depth_then_format_json:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_analyze_json
    mov     rdi, rax
    jmp     .exit

.analyze_depth_then_format_text:
    mov     rdi, [r12 + 48]
    mov     rsi, r14
    call    x64lens_command_analyze
    mov     rdi, rax
    jmp     .exit

.exit:
    ; Centralized process exit path. Future cleanup should happen before
    ; jumping here, not after this syscall.
    mov     rax, SYS_EXIT
    syscall
