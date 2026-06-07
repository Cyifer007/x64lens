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
; Current exports:
;   x64lens_report_text_elf64_info(path, mapped_base, file_size)
;   x64lens_report_text_mitigations(path, mapped_base, file_size, summary, regions)
;
; Contract alignment:
;   Text output is allowed to evolve before 1.0.0, but changes must be tested
;   and documented. JSON output later must be emitted from internal records,
;   not by scraping these human-readable strings.

bits 64
default rel

%include "constants.inc"
%include "elf64.inc"
%include "structs.inc"

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

section_mitigations:    db 10, "Mitigations:", 10, 0
label_pie:             db "  PIE: ", 0
label_nx_stack:        db "  NX stack: ", 0
label_relro:           db "  RELRO: ", 0
label_rwx:             db "  RWX load segment: ", 0
label_dynamic:         db "  Dynamic linking: ", 0
label_load_count:      db "  LOAD segments: ", 0
label_exec_count:      db "  Executable LOAD regions: ", 0
state_enabled:         db "enabled", 10, 0
state_disabled:        db "disabled", 10, 0
state_unknown:         db "unknown", 10, 0
state_present:         db "present", 10, 0
state_not_found:       db "not found", 10, 0
state_yes:             db "yes", 10, 0
state_no:              db "no", 10, 0

section_exec_regions:  db 10, "Executable regions:", 10, 0
no_exec_regions:       db "  none discovered from PT_LOAD + PF_X", 10, 0
region_prefix:         db "  - VA ", 0
region_file_offset:    db ", file offset ", 0
region_file_size:      db ", file size ", 0
region_mem_size:       db ", mem size ", 0
region_perms:          db ", perms ", 0
perms_rwx:             db "RWX", 10, 0
perms_rw_:             db "RW-", 10, 0
perms_r_x:             db "R-X", 10, 0
perms_r__:             db "R--", 10, 0
perms__wx:             db "-WX", 10, 0
perms__w_:             db "-W-", 10, 0
perms___x:             db "--X", 10, 0
perms____:             db "---", 10, 0

section .text
global x64lens_report_text_elf64_info
global x64lens_report_text_mitigations

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
    call    report_text_print_elf_type

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

; x64lens_report_text_mitigations(path=rdi, mapped_base=rsi, file_size=rdx, summary=rcx, regions=r8)
;
; Inputs:
;   RDI = target path C string
;   RSI = mmap base address, currently unused but reserved for future labels
;   RDX = file size, currently unused but reserved for future consistency
;   RCX = phdr_summary record
;   R8  = executable_region[] buffer
;
; Output:
;   Human-readable mitigation and executable-region report on STDOUT.
x64lens_report_text_mitigations:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     rbx, rdi            ; target path
    mov     r14, rcx            ; summary record
    mov     r15, r8             ; executable region buffer

    lea     rdi, [header_tool]
    call    print_cstr
    lea     rdi, [label_target]
    call    print_cstr
    mov     rdi, rbx
    call    print_cstr
    call    print_nl

    lea     rdi, [section_mitigations]
    call    print_cstr

    lea     rdi, [label_pie]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_PIE]
    call    report_text_print_enabled_disabled

    lea     rdi, [label_nx_stack]
    call    print_cstr
    cmp     qword [r14 + PHDR_SUMMARY_GNU_STACK_SEEN], 0
    je      .nx_unknown
    cmp     qword [r14 + PHDR_SUMMARY_GNU_STACK_EXEC], 0
    jne     .nx_disabled
    lea     rdi, [state_enabled]
    call    print_cstr
    jmp     .after_nx
.nx_disabled:
    lea     rdi, [state_disabled]
    call    print_cstr
    jmp     .after_nx
.nx_unknown:
    lea     rdi, [state_unknown]
    call    print_cstr
.after_nx:

    lea     rdi, [label_relro]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_RELRO_SEEN]
    call    report_text_print_present_not_found

    lea     rdi, [label_rwx]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_RWX_COUNT]
    call    report_text_print_yes_no_nonzero

    lea     rdi, [label_dynamic]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_DYNAMIC_SEEN]
    call    report_text_print_yes_no_nonzero

    lea     rdi, [label_phnum]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_PHNUM]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_load_count]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_LOAD_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_exec_count]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_EXEC_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [section_exec_regions]
    call    print_cstr
    cmp     qword [r14 + PHDR_SUMMARY_EXEC_COUNT], 0
    jne     .regions_loop_setup
    lea     rdi, [no_exec_regions]
    call    print_cstr
    jmp     .mit_done

.regions_loop_setup:
    xor     rbp, rbp
.regions_loop:
    cmp     rbp, [r14 + PHDR_SUMMARY_EXEC_COUNT]
    jae     .mit_done

    mov     rax, rbp
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     r12, [r15 + rax]

    lea     rdi, [region_prefix]
    call    print_cstr
    mov     rdi, [r12 + EXEC_REGION_VADDR]
    call    print_hex64

    lea     rdi, [region_file_offset]
    call    print_cstr
    mov     rdi, [r12 + EXEC_REGION_FILE_OFFSET]
    call    print_hex64

    lea     rdi, [region_file_size]
    call    print_cstr
    mov     rdi, [r12 + EXEC_REGION_FILESZ]
    call    print_hex64

    lea     rdi, [region_mem_size]
    call    print_cstr
    mov     rdi, [r12 + EXEC_REGION_MEMSZ]
    call    print_hex64

    lea     rdi, [region_perms]
    call    print_cstr
    mov     edi, [r12 + EXEC_REGION_FLAGS]
    call    report_text_print_perms

    inc     rbp
    jmp     .regions_loop

.mit_done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

 ; Local helper: print ELF e_type as a stable label.
report_text_print_elf_type:
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

 ; Print enabled/disabled based on zero/nonzero RDI.
report_text_print_enabled_disabled:
    test    rdi, rdi
    jz      .ped_disabled
    lea     rdi, [state_enabled]
    jmp     print_cstr
.ped_disabled:
    lea     rdi, [state_disabled]
    jmp     print_cstr

 ; Print present/not found based on zero/nonzero RDI.
report_text_print_present_not_found:
    test    rdi, rdi
    jz      .ppnf_not_found
    lea     rdi, [state_present]
    jmp     print_cstr
.ppnf_not_found:
    lea     rdi, [state_not_found]
    jmp     print_cstr

 ; Print yes/no based on zero/nonzero RDI.
report_text_print_yes_no_nonzero:
    test    rdi, rdi
    jz      .pynn_no
    lea     rdi, [state_yes]
    jmp     print_cstr
.pynn_no:
    lea     rdi, [state_no]
    jmp     print_cstr

 ; Print R/W/X permission triplet from ELF p_flags in EDI.
report_text_print_perms:
    mov     eax, edi
    and     eax, PF_R | PF_W | PF_X
    cmp     eax, PF_R | PF_W | PF_X
    je      .perms_rwx
    cmp     eax, PF_R | PF_W
    je      .perms_rw_
    cmp     eax, PF_R | PF_X
    je      .perms_r_x
    cmp     eax, PF_R
    je      .perms_r__
    cmp     eax, PF_W | PF_X
    je      .perms__wx
    cmp     eax, PF_W
    je      .perms__w_
    cmp     eax, PF_X
    je      .perms___x
    lea     rdi, [perms____]
    jmp     print_cstr
.perms_rwx:
    lea     rdi, [perms_rwx]
    jmp     print_cstr
.perms_rw_:
    lea     rdi, [perms_rw_]
    jmp     print_cstr
.perms_r_x:
    lea     rdi, [perms_r_x]
    jmp     print_cstr
.perms_r__:
    lea     rdi, [perms_r__]
    jmp     print_cstr
.perms__wx:
    lea     rdi, [perms__wx]
    jmp     print_cstr
.perms__w_:
    lea     rdi, [perms__w_]
    jmp     print_cstr
.perms___x:
    lea     rdi, [perms___x]
    jmp     print_cstr
