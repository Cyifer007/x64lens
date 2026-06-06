; cli.asm
;
; Purpose:
;   CLI helper routines for command string comparison, usage output, and
;   temporary command stubs. This module should remain focused on user input
;   and should not contain ELF parsing, gadget scanning, or scoring logic.
;
; Current exported routines:
;   cstr_eq(a, b) -> 1 if equal, 0 otherwise
;   cli_print_help()
;   cli_command_info_stub(path)
;
; Sprint 1 next step:
;   Replace the info stub call path with a real `info` command implementation
;   once filemap.asm and elf64.asm are ready.

bits 64
default rel

%include "constants.inc"

extern print_cstr
extern print_nl

section .rodata
help_text:
    db "x64lens 0.1.0-dev", 10
    db "", 10
    db "Usage:", 10
    db "  x64lens help", 10
    db "  x64lens version", 10
    db "  x64lens info <file>", 10
    db "", 10
    db "Planned commands:", 10
    db "  x64lens mitigations <file>", 10
    db "  x64lens gadgets <file>", 10
    db "  x64lens analyze <file>", 10
    db "  x64lens bench <file>", 10, 0

info_stub_prefix:
    db "info: scaffold command received target: ", 0
info_stub_suffix:
    db 10, "Sprint 1 target: replace this stub with file mapping and ELF64 header validation.", 10, 0

section .text
global cstr_eq
global cli_print_help
global cli_command_info_stub

; cstr_eq(rdi=a, rsi=b) -> rax=1 if equal, else 0
;
; Inputs:
;   RDI = pointer to first null-terminated string
;   RSI = pointer to second null-terminated string
;
; Output:
;   RAX = 1 when strings match exactly, otherwise 0
;
; Clobbers:
;   RAX, RBX, RDI, RSI
cstr_eq:
    push    rbx
.loop:
    mov     al, [rdi]
    mov     bl, [rsi]
    cmp     al, bl
    jne     .not_equal
    test    al, al
    je      .equal
    inc     rdi
    inc     rsi
    jmp     .loop
.equal:
    mov     rax, 1
    pop     rbx
    ret
.not_equal:
    xor     rax, rax
    pop     rbx
    ret

; Print stable command help. Keep this synchronized with docs/cli-contract.md.
cli_print_help:
    lea     rdi, [help_text]
    call    print_cstr
    ret

; cli_command_info_stub(rdi=path_cstr)
;
; Temporary scaffold used before the real ELF64 info path exists. Keeping the
; stub explicit lets tests confirm that the command dispatch path works even
; before file parsing is implemented.
cli_command_info_stub:
    push    rdi
    lea     rdi, [info_stub_prefix]
    call    print_cstr
    pop     rdi
    call    print_cstr
    lea     rdi, [info_stub_suffix]
    call    print_cstr
    ret
