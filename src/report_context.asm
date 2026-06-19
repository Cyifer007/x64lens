
; report_context.asm
;
; Purpose:
;   Provide body-only text reporter entry points for integrated commands.
;
; Module scope:
;   The focused `info`, `mitigations`, and `gadgets` commands retain their
;   complete version and target banners. Integrated commands can call the
;   wrappers below to reuse the same section renderers without duplicating
;   those banners.
;
; Safety and concurrency:
;   x64lens is currently single-threaded. The process-local flag is set only
;   for the duration of one reporter call and is cleared before returning.
;
; Exports:
;   report_body_only_flag
;   x64lens_report_text_elf64_info_body
;   x64lens_report_text_mitigations_body
;   x64lens_report_text_gadgets_body

bits 64
default rel

global report_body_only_flag
global x64lens_report_text_elf64_info_body
global x64lens_report_text_mitigations_body
global x64lens_report_text_gadgets_body

extern x64lens_report_text_elf64_info
extern x64lens_report_text_mitigations
extern x64lens_report_text_gadgets

section .bss
align 8
report_body_only_flag: resb 1

section .text

x64lens_report_text_elf64_info_body:
    mov     byte [rel report_body_only_flag], 1
    sub     rsp, 8
    call    x64lens_report_text_elf64_info
    add     rsp, 8
    mov     byte [rel report_body_only_flag], 0
    ret

x64lens_report_text_mitigations_body:
    mov     byte [rel report_body_only_flag], 1
    sub     rsp, 8
    call    x64lens_report_text_mitigations
    add     rsp, 8
    mov     byte [rel report_body_only_flag], 0
    ret

x64lens_report_text_gadgets_body:
    mov     byte [rel report_body_only_flag], 1
    sub     rsp, 8
    call    x64lens_report_text_gadgets
    add     rsp, 8
    mov     byte [rel report_body_only_flag], 0
    ret
