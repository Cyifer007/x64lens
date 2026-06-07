; hex.asm
;
; Purpose:
;   Hexadecimal formatting helpers for addresses, offsets, sizes, and future
;   raw gadget bytes. Keeping formatting separate from print.asm prevents
;   report emitters from duplicating conversion logic.
;
; Current Sprint 1 export:
;   print_hex64(value) prints a stable 0x-prefixed, 16-digit lowercase hex
;   value to STDOUT. Fixed-width output is intentionally verbose but makes
;   early parser demos and regression tests deterministic.
;   Sprint 3 adds print_hex8(value) for raw gadget byte windows.

bits 64
default rel

extern print_cstr

section .rodata
hexchars: db "0123456789abcdef"

section .bss
hexbuf: resb 19                 ; "0x" + 16 digits + NUL
hex8buf: resb 3                 ; two hex digits + NUL

section .text
global print_hex64
global print_hex8

; print_hex64(rdi=value)
;
; Inputs:
;   RDI = unsigned 64-bit value to render
;
; Output:
;   writes 0x0000000000000000-style text to STDOUT
;
; Clobbers:
;   RAX, RCX, RDX, RSI, RDI
print_hex64:
    push    rbx
    push    r12

    mov     rbx, rdi            ; RBX holds the shifting value
    lea     r12, [hexbuf]
    mov     byte [r12], '0'
    mov     byte [r12 + 1], 'x'

    lea     rsi, [r12 + 2]      ; output digit cursor
    mov     rcx, 16             ; one nibble per hex digit
    lea     rdx, [hexchars]
.digit_loop:
    mov     rax, rbx
    shr     rax, 60             ; isolate the current high nibble
    mov     al, [rdx + rax]
    mov     [rsi], al
    shl     rbx, 4
    inc     rsi
    loop    .digit_loop

    mov     byte [r12 + 18], 0
    mov     rdi, r12
    call    print_cstr

    pop     r12
    pop     rbx
    ret


; print_hex8(rdi=value)
;
; Inputs:
;   RDI = low byte to render
;
; Output:
;   writes exactly two lowercase hex digits to STDOUT, without 0x prefix
;
; Clobbers:
;   RAX, RBX, RDX, RSI, RDI
print_hex8:
    push    rbx
    push    r12

    mov     ebx, edi
    and     ebx, 0xff
    lea     r12, [hex8buf]
    lea     rdx, [hexchars]

    mov     eax, ebx
    shr     eax, 4
    and     eax, 0x0f
    mov     al, [rdx + rax]
    mov     [r12], al

    mov     eax, ebx
    and     eax, 0x0f
    mov     al, [rdx + rax]
    mov     [r12 + 1], al
    mov     byte [r12 + 2], 0

    mov     rdi, r12
    call    print_cstr

    pop     r12
    pop     rbx
    ret
