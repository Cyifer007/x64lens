; print.asm
;
; Purpose:
;   Minimal output helpers used by the no-libc assembly implementation.
;   These routines deliberately avoid libc and write directly through the
;   Linux x86_64 write(2) syscall.
;
; Safety note:
;   `print_cstr` and `print_cstr_err` assume the input pointer references a
;   trusted null-terminated string. Do not pass untrusted file data directly
;   to these routines unless a trusted length has been established and the
;   data has been copied or formatted safely.

bits 64
default rel

%include "constants.inc"

section .rodata
newline: db 10, 0

section .text
global print_cstr
global print_cstr_err
global print_nl

; print_cstr(rdi = null-terminated string)
;
; Inputs:
;   RDI = pointer to trusted null-terminated string
;
; Output:
;   writes bytes to STDOUT
;
; Clobbers:
;   RAX, RDI, RSI, RDX, RCX
print_cstr:
    push    rdi                ; save start pointer while we compute length
    xor     rdx, rdx           ; RDX becomes byte length for write(2)
.len_loop:
    cmp     byte [rdi + rdx], 0
    je      .write
    inc     rdx
    jmp     .len_loop
.write:
    pop     rsi                ; RSI = original buffer pointer
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    syscall
    ret

; print_cstr_err(rdi = null-terminated string)
;
; Same contract as print_cstr, except output goes to STDERR. This keeps
; command output and error output separable for tests and future automation.
print_cstr_err:
    push    rdi
    xor     rdx, rdx
.len_loop:
    cmp     byte [rdi + rdx], 0
    je      .write
    inc     rdx
    jmp     .len_loop
.write:
    pop     rsi
    mov     rax, SYS_WRITE
    mov     rdi, STDERR
    syscall
    ret

; print_nl()
;   Convenience wrapper for a single newline on STDOUT.
print_nl:
    lea     rdi, [newline]
    jmp     print_cstr
