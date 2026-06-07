; report_text.asm
;
; Purpose:
;   Human-readable report emitter.
;
; Module scope:
;   Render stable text output for analysts, reviewers, and demos. Reporting
;   code formats facts discovered elsewhere; it should not perform file I/O,
;   ELF validation, gadget scanning, or scoring policy decisions.
;
; Sprint 1 export:
;   x64lens_report_text_elf64_info(path, mapped_base, file_size)

bits 64
default rel

%include "constants.inc"
%include "elf64.inc"

extern print_cstr
extern print_nl
extern print_hex64

section .rodata
header_tool:        db "x64lens ", X64LENS_VERSION, 10, 0
label_target:       db "Target: ", 0
section_format:     db 10, "Format:", 10, 0
label_type:         db "  Type: ELF64", 10, 0
label_endian:       db "  Endian: little", 10, 0
label_machine:      db "  Machine: x86_64", 10, 0
label_elf_type:     db "  ELF Type: ", 0
label_entry:        db "  Entry: ", 0
label_phoff:        db "  Program header offset: ", 0
label_phentsize:    db "  Program header entry size: ", 0
label_phnum:        db "  Program header count: ", 0
label_shoff:        db "  Section header offset: ", 0
label_shentsize:    db "  Section header entry size: ", 0
label_shnum:        db "  Section header count: ", 0
label_file_size:    db "  File size: ", 0
etype_exec:         db "ET_EXEC", 10, 0
etype_dyn:          db "ET_DYN", 10, 0
etype_rel:          db "ET_REL", 10, 0
etype_none:         db "ET_NONE", 10, 0
etype_unknown:      db "unknown", 10, 0

section .text
global x64lens_report_text_elf64_info

; x64lens_report_text_elf64_info(path=rdi, mapped_base=rsi, file_size=rdx)
;
; Inputs:
;   RDI = original target path C string from argv
;   RSI = mmap base address
;   RDX = file size in bytes
;
; Output:
;   Human-readable ELF64 metadata report on STDOUT.
x64lens_report_text_elf64_info:
    push    rbx
    push    r12
    push    r13

    mov     rbx, rdi            ; target path
    mov     r12, rsi            ; mapped base
    mov     r13, rdx            ; file size

    lea     rdi, [header_tool]
    call    print_cstr
    lea     rdi, [label_target]
    call    print_cstr
    mov     rdi, rbx
    call    print_cstr
    call    print_nl

    lea     rdi, [section_format]
    call    print_cstr
    lea     rdi, [label_type]
    call    print_cstr
    lea     rdi, [label_endian]
    call    print_cstr
    lea     rdi, [label_machine]
    call    print_cstr

    lea     rdi, [label_elf_type]
    call    print_cstr
    movzx   rdi, word [r12 + E_TYPE]
    call    .print_elf_type

    lea     rdi, [label_entry]
    call    print_cstr
    mov     rdi, [r12 + E_ENTRY]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_phoff]
    call    print_cstr
    mov     rdi, [r12 + E_PHOFF]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_phentsize]
    call    print_cstr
    movzx   rdi, word [r12 + E_PHENTSIZE]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_phnum]
    call    print_cstr
    movzx   rdi, word [r12 + E_PHNUM]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_shoff]
    call    print_cstr
    mov     rdi, [r12 + E_SHOFF]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_shentsize]
    call    print_cstr
    movzx   rdi, word [r12 + E_SHENTSIZE]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_shnum]
    call    print_cstr
    movzx   rdi, word [r12 + E_SHNUM]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_file_size]
    call    print_cstr
    mov     rdi, r13
    call    print_hex64
    call    print_nl

    pop     r13
    pop     r12
    pop     rbx
    ret

; Local helper: print ELF e_type as a stable label.
.print_elf_type:
    cmp     rdi, ET_EXEC
    je      .exec
    cmp     rdi, ET_DYN
    je      .dyn
    cmp     rdi, ET_REL
    je      .rel
    cmp     rdi, ET_NONE
    je      .none
    lea     rdi, [etype_unknown]
    jmp     print_cstr
.exec:
    lea     rdi, [etype_exec]
    jmp     print_cstr
.dyn:
    lea     rdi, [etype_dyn]
    jmp     print_cstr
.rel:
    lea     rdi, [etype_rel]
    jmp     print_cstr
.none:
    lea     rdi, [etype_none]
    jmp     print_cstr
