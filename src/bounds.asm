; bounds.asm
;
; Purpose:
;   Bounds-check helpers for untrusted target-file parsing.
;
; Module scope:
;   Validate file offsets, sizes, pointer ranges, and overflow-sensitive
;   arithmetic before parser modules read target bytes.
;
; Contract:
;   Keep this module policy-light. It returns true/false facts. Parser modules
;   decide whether a failed check means malformed input, unsupported input, or
;   an internal bounds failure.

bits 64
default rel

section .text
global x64lens_bounds_has_size
global x64lens_bounds_range_valid

; x64lens_bounds_has_size(file_size=rdi, needed_size=rsi) -> rax=1/0
;
; Returns true when file_size >= needed_size.
x64lens_bounds_has_size:
    xor     rax, rax
    cmp     rdi, rsi
    jb      .done
    mov     rax, 1
.done:
    ret

; x64lens_bounds_range_valid(file_size=rdi, offset=rsi, length=rdx) -> rax=1/0
;
; Returns true when [offset, offset + length) fits inside file_size.
; The check avoids overflow by subtracting offset from file_size before
; comparing length.
x64lens_bounds_range_valid:
    xor     rax, rax
    cmp     rsi, rdi            ; offset > file_size is invalid
    ja      .done
    mov     rcx, rdi
    sub     rcx, rsi            ; rcx = remaining bytes from offset to EOF
    cmp     rdx, rcx
    ja      .done
    mov     rax, 1
.done:
    ret
