; print.asm
;
; Purpose:
;   Minimal output helpers used by the no-libc assembly implementation.
;   Sprint 1 only needs null-terminated string output and newlines. Later
;   sprints will add hexadecimal and decimal formatting in hex.asm.
;
; Safety note:
;   `print_cstr` assumes the input pointer references a valid null-terminated
;   string. Do not pass untrusted file data directly to this routine unless
;   a trusted length has been established and copied/formatted safely.

bits 64
default rel

%include "constants.inc"

section .rodata
newline: db 10, 0

section .text
global print_cstr
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

; print_nl()
;   Convenience wrapper for a single newline.
print_nl:
    lea     rdi, [newline]
    call    print_cstr
    ret
