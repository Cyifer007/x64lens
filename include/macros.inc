; macros.inc
;
; Purpose:
;   Small NASM macros that are safe to reuse across modules. Keep this file
;   intentionally small. If a macro starts hiding important control flow,
;   move that behavior into a real function instead.

%ifndef X64LENS_MACROS_INC
%define X64LENS_MACROS_INC

; EXIT_WITH code
;   Directly exits the process through the Linux x86_64 exit syscall.
;   Use sparingly. Most modules should return status to the caller instead
;   so cleanup can happen in one place.
%macro EXIT_WITH 1
    mov rax, 60
    mov rdi, %1
    syscall
%endmacro

%endif
