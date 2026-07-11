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
;   x64lens_report_text_gadgets(path, gadget_summary, gadget_records, mapped_base, analysis_summary)
;
; Integrated-report seam:
;   report_context.asm exposes body-only wrappers. The wrappers set a narrow
;   process-local flag so these same reporters omit only their repeated banner.
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
extern print_hex8
extern print_u64_dec
extern report_body_only_flag

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
label_canary:          db "  Canary indicator: ", 0
label_stripped:        db "  Stripped indicator: ", 0
label_rwx:             db "  RWX load segment: ", 0
label_dynamic:         db "  Dynamic linking: ", 0
label_bind_now:        db "  Bind now: ", 0
label_dynamic_entries: db "  Dynamic entries: ", 0
label_dynamic_null:    db "  Dynamic terminator: ", 0
label_load_count:      db "  LOAD segments: ", 0
label_exec_count:      db "  Executable LOAD regions: ", 0
state_enabled:         db "enabled", 10, 0
state_disabled:        db "disabled", 10, 0
state_unknown:         db "unknown", 10, 0
state_present:         db "present", 10, 0
state_not_found:       db "not found", 10, 0
state_absent:          db "absent", 10, 0
state_stripped:        db "stripped", 10, 0
state_not_stripped:    db "not stripped", 10, 0
state_partial:         db "partial", 10, 0
state_full:            db "full", 10, 0
state_yes:             db "yes", 10, 0
state_no:              db "no", 10, 0
state_not_applicable:  db "not applicable", 10, 0

section_exec_regions:  db 10, "Executable regions:", 10, 0
no_exec_regions:       db "  none discovered from PT_LOAD + PF_X", 10, 0
region_prefix:         db "  - VA ", 0
region_file_offset:    db ", file offset ", 0
region_file_size:      db ", file size ", 0
region_mem_size:       db ", mem size ", 0
region_section:        db ", section: ", 0
region_perms:          db ", perms ", 0
perms_rwx:             db "RWX", 10, 0
perms_rw_:             db "RW-", 10, 0
perms_r_x:             db "R-X", 10, 0
perms_r__:             db "R--", 10, 0
perms__wx:             db "-WX", 10, 0
perms__w_:             db "-W-", 10, 0
perms___x:             db "--X", 10, 0
perms____:             db "---", 10, 0

section_analysis:      db 10, "Analysis:", 10, 0
label_report_type:     db "  Report type: ", 0
label_command:         db "  Command: ", 0
label_analysis_complete: db "  Complete: ", 0
label_candidate_truncated: db "  Candidate truncated: ", 0
label_candidate_dropped: db "  Candidate dropped count: ", 0
label_regions_scanned: db "  Regions scanned: ", 0
label_regions_total:   db "  Regions total: ", 0
report_type_analysis:  db "analysis", 10, 0
command_gadgets:       db "gadgets", 10, 0
command_analyze:       db "analyze", 10, 0
identity_unknown:      db "unknown", 10, 0

section_gadgets:       db 10, "Raw gadget candidates:", 10, 0
label_max_depth:       db "  Max depth: ", 0
label_capacity:        db "  Candidate capacity: ", 0
label_candidate_count: db "  Candidate count: ", 0
label_ret_count:       db "  ret count: ", 0
label_ret_imm_count:   db "  ret imm16 count: ", 0
label_pattern_count:   db "  Exact pattern count: ", 0
label_semantic_count:  db "  Semantic primitive count: ", 0
label_scored_count:    db "  Scored candidate count: ", 0
label_unknown_count:   db "  unknown_candidate count: ", 0
label_arg_count:       db "  arg_control count: ", 0
label_sysnum_count:    db "  syscall_num_control count: ", 0
label_systrig_count:   db "  syscall_trigger count: ", 0
label_pivot_count:     db "  stack_pivot count: ", 0
label_align_count:     db "  alignment count: ", 0
label_reg_coverage:    db "  Register coverage: ", 0
no_candidates:         db "  none discovered in executable regions", 10, 0
candidate_prefix:      db "  - VA ", 0
candidate_file_off:    db ", file offset ", 0
candidate_section:     db ", section: ", 0
section_escape_hex:    db 0x5c, "x", 0
section_escape_bslash: db 0x5c, 0x5c, 0
candidate_window:      db ", window start ", 0
candidate_len:         db ", len ", 0
candidate_term:        db ", terminator: ", 0
candidate_pattern:     db ", pattern: ", 0
candidate_semantic:    db ", semantic: ", 0
candidate_regs:        db ", regs: ", 0
candidate_stack_delta: db ", stack delta: ", 0
candidate_score:      db ", score: ", 0
candidate_bytes:       db ", bytes: ", 0
term_ret:              db "ret", 0
term_ret_imm16:        db "ret imm16", 0
term_unknown:          db "unknown", 0
pattern_unknown:       db "unknown", 0
pattern_ret:           db "ret", 0
pattern_ret_imm16:     db "ret imm16", 0
pattern_pop_rax_ret:   db "pop rax; ret", 0
pattern_pop_rcx_ret:   db "pop rcx; ret", 0
pattern_pop_rdx_ret:   db "pop rdx; ret", 0
pattern_pop_rbx_ret:   db "pop rbx; ret", 0
pattern_pop_rsp_ret:   db "pop rsp; ret", 0
pattern_pop_rbp_ret:   db "pop rbp; ret", 0
pattern_pop_rsi_ret:   db "pop rsi; ret", 0
pattern_pop_rdi_ret:   db "pop rdi; ret", 0
pattern_pop_r8_ret:    db "pop r8; ret", 0
pattern_pop_r9_ret:    db "pop r9; ret", 0
pattern_pop_r10_ret:   db "pop r10; ret", 0
pattern_pop_r11_ret:   db "pop r11; ret", 0
pattern_pop_r12_ret:   db "pop r12; ret", 0
pattern_pop_r13_ret:   db "pop r13; ret", 0
pattern_pop_r14_ret:   db "pop r14; ret", 0
pattern_pop_r15_ret:   db "pop r15; ret", 0
pattern_leave_ret:     db "leave; ret", 0
pattern_syscall_ret:   db "syscall; ret", 0
semantic_unknown:      db "unknown_candidate", 0
semantic_arg_control:  db "arg_control", 0
semantic_syscall_num:  db "syscall_num_control", 0
semantic_syscall_trig: db "syscall_trigger", 0
semantic_stack_pivot:  db "stack_pivot", 0
semantic_memory_write: db "memory_write", 0
semantic_memory_read:  db "memory_read", 0
semantic_reg_transfer: db "reg_transfer", 0
semantic_alignment:    db "alignment", 0
semantic_clobber:      db "clobber_heavy", 0
regs_none:             db "none", 0
reg_sep:               db "|", 0
reg_rax:               db "rax", 0
reg_rbx:               db "rbx", 0
reg_rcx:               db "rcx", 0
reg_rdx:               db "rdx", 0
reg_rsi:               db "rsi", 0
reg_rdi:               db "rdi", 0
reg_rbp:               db "rbp", 0
reg_rsp:               db "rsp", 0
reg_r8:                db "r8", 0
reg_r9:                db "r9", 0
reg_r10:               db "r10", 0
reg_r11:               db "r11", 0
reg_r12:               db "r12", 0
reg_r13:               db "r13", 0
reg_r14:               db "r14", 0
reg_r15:               db "r15", 0
space_str:             db " ", 0

section .bss
section_safe_byte: resb 1

section .text
global x64lens_report_text_elf64_info
global x64lens_report_text_mitigations
global x64lens_report_text_gadgets

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

    cmp     byte [rel report_body_only_flag], 0
    jne     .info_body_start

    lea     rdi, [header_tool]
    call    print_cstr
    lea     rdi, [label_target]
    call    print_cstr
    mov     rdi, rbx
    call    print_cstr
    call    print_nl

.info_body_start:
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
    sub     rsp, 8              ; keep nested System V calls 16-byte aligned

    mov     rbx, rdi            ; target path
    mov     r14, rcx            ; summary record
    mov     r15, r8             ; executable region buffer

    cmp     byte [rel report_body_only_flag], 0
    jne     .mitigations_body_start

    lea     rdi, [header_tool]
    call    print_cstr
    lea     rdi, [label_target]
    call    print_cstr
    mov     rdi, rbx
    call    print_cstr
    call    print_nl

.mitigations_body_start:
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
    cmp     qword [r14 + PHDR_SUMMARY_RELRO_SEEN], 0
    je      .relro_not_found
    cmp     qword [r14 + PHDR_SUMMARY_BIND_NOW], 0
    jne     .relro_full
    lea     rdi, [state_partial]
    call    print_cstr
    jmp     .after_relro
.relro_full:
    lea     rdi, [state_full]
    call    print_cstr
    jmp     .after_relro
.relro_not_found:
    lea     rdi, [state_not_found]
    call    print_cstr
.after_relro:

    lea     rdi, [label_canary]
    call    print_cstr
    mov     rax, [r14 + PHDR_SUMMARY_CANARY_STATE]
    cmp     rax, CANARY_STATE_PRESENT
    je      .canary_present
    cmp     rax, CANARY_STATE_ABSENT
    je      .canary_absent
    lea     rdi, [state_unknown]
    call    print_cstr
    jmp     .after_canary
.canary_present:
    lea     rdi, [state_present]
    call    print_cstr
    jmp     .after_canary
.canary_absent:
    lea     rdi, [state_absent]
    call    print_cstr
.after_canary:

    lea     rdi, [label_stripped]
    call    print_cstr
    mov     rax, [r14 + PHDR_SUMMARY_STRIPPED_STATE]
    cmp     rax, STRIPPED_STATE_STRIPPED
    je      .stripped_yes
    cmp     rax, STRIPPED_STATE_NOT_STRIPPED
    je      .stripped_no
    lea     rdi, [state_unknown]
    call    print_cstr
    jmp     .after_stripped
.stripped_yes:
    lea     rdi, [state_stripped]
    call    print_cstr
    jmp     .after_stripped
.stripped_no:
    lea     rdi, [state_not_stripped]
    call    print_cstr
.after_stripped:

    lea     rdi, [label_rwx]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_RWX_COUNT]
    call    report_text_print_yes_no_nonzero

    lea     rdi, [label_dynamic]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_DYNAMIC_SEEN]
    call    report_text_print_yes_no_nonzero

    lea     rdi, [label_bind_now]
    call    print_cstr
    cmp     qword [r14 + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .bind_now_na
    mov     rdi, [r14 + PHDR_SUMMARY_BIND_NOW]
    call    report_text_print_yes_no_nonzero
    jmp     .after_bind_now
.bind_now_na:
    lea     rdi, [state_not_applicable]
    call    print_cstr
.after_bind_now:

    lea     rdi, [label_dynamic_entries]
    call    print_cstr
    mov     rdi, [r14 + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_dynamic_null]
    call    print_cstr
    cmp     qword [r14 + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .dynamic_null_na
    mov     rdi, [r14 + PHDR_SUMMARY_DYNAMIC_NULL_SEEN]
    call    report_text_print_yes_no_nonzero
    jmp     .after_dynamic_null
.dynamic_null_na:
    lea     rdi, [state_not_applicable]
    call    print_cstr
.after_dynamic_null:

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

    cmp     qword [r12 + EXEC_REGION_SECTION_NAME_PTR], 0
    je      .region_section_done
    lea     rdi, [region_section]
    call    print_cstr
    mov     rdi, [r12 + EXEC_REGION_SECTION_NAME_PTR]
    mov     rsi, [r12 + EXEC_REGION_SECTION_NAME_LEN]
    call    report_text_print_section_name
.region_section_done:

    lea     rdi, [region_perms]
    call    print_cstr
    mov     edi, [r12 + EXEC_REGION_FLAGS]
    call    report_text_print_perms

    inc     rbp
    jmp     .regions_loop

.mit_done:
    add     rsp, 8
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


; x64lens_report_text_gadgets(path=rdi, gadget_summary=rsi, gadget_records=rdx, mapped_base=rcx, analysis_summary=r8)
;
; Inputs:
;   RDI = target path C string
;   RSI = gadget_summary record
;   RDX = gadget_record[] buffer
;   RCX = mapped target base used only for rendering raw window bytes
;   R8  = analysis_summary record with report identity and completeness facts
;
; Output:
;   Human-readable raw gadget candidate report on STDOUT.
;
; Scope:
;   This report renders raw scanner facts, exact pattern facts, first-pass
;   semantic classifier facts, and Sprint 5 scoring facts. It does not decode
;   full instruction streams or infer exploitability.
x64lens_report_text_gadgets:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    push    r8                  ; analysis_summary pointer

    mov     rbx, rdi            ; target path
    mov     r12, rsi            ; gadget_summary
    mov     r13, rdx            ; gadget_record[]
    mov     r14, rcx            ; mapped file base

    cmp     byte [rel report_body_only_flag], 0
    jne     .gadgets_body_start

    lea     rdi, [header_tool]
    call    print_cstr
    lea     rdi, [label_target]
    call    print_cstr
    mov     rdi, rbx
    call    print_cstr
    call    print_nl

.gadgets_body_start:
    ; Identity and completeness come from a command-owned record constructed
    ; only after the shared analysis pipeline succeeds.
    mov     r15, [rsp]

    lea     rdi, [section_analysis]
    call    print_cstr

    lea     rdi, [label_report_type]
    call    print_cstr
    cmp     qword [r15 + ANALYSIS_SUMMARY_REPORT_TYPE], REPORT_TYPE_ANALYSIS
    jne     .analysis_report_type_unknown
    lea     rdi, [report_type_analysis]
    call    print_cstr
    jmp     .analysis_report_type_done
.analysis_report_type_unknown:
    lea     rdi, [identity_unknown]
    call    print_cstr
.analysis_report_type_done:

    lea     rdi, [label_command]
    call    print_cstr
    cmp     qword [r15 + ANALYSIS_SUMMARY_COMMAND], REPORT_COMMAND_GADGETS
    je      .analysis_command_gadgets
    cmp     qword [r15 + ANALYSIS_SUMMARY_COMMAND], REPORT_COMMAND_ANALYZE
    je      .analysis_command_analyze
    lea     rdi, [identity_unknown]
    call    print_cstr
    jmp     .analysis_command_done
.analysis_command_gadgets:
    lea     rdi, [command_gadgets]
    call    print_cstr
    jmp     .analysis_command_done
.analysis_command_analyze:
    lea     rdi, [command_analyze]
    call    print_cstr
.analysis_command_done:

    lea     rdi, [label_analysis_complete]
    call    print_cstr
    cmp     qword [r15 + ANALYSIS_SUMMARY_COMPLETE], 0
    je      .analysis_complete_no
    lea     rdi, [state_yes]
    call    print_cstr
    jmp     .analysis_complete_done
.analysis_complete_no:
    lea     rdi, [state_no]
    call    print_cstr
.analysis_complete_done:

    lea     rdi, [label_candidate_truncated]
    call    print_cstr
    cmp     qword [r15 + ANALYSIS_SUMMARY_CANDIDATE_TRUNCATED], 0
    je      .analysis_truncated_no
    lea     rdi, [state_yes]
    call    print_cstr
    jmp     .analysis_truncated_done
.analysis_truncated_no:
    lea     rdi, [state_no]
    call    print_cstr
.analysis_truncated_done:

    lea     rdi, [label_candidate_dropped]
    call    print_cstr
    cmp     qword [r15 + ANALYSIS_SUMMARY_DROPPED_COUNT_KNOWN], 0
    je      .analysis_dropped_unknown
    mov     rdi, [r15 + ANALYSIS_SUMMARY_DROPPED_COUNT]
    call    print_hex64
    call    print_nl
    jmp     .analysis_dropped_done
.analysis_dropped_unknown:
    lea     rdi, [state_unknown]
    call    print_cstr
.analysis_dropped_done:

    lea     rdi, [label_regions_scanned]
    call    print_cstr
    mov     rdi, [r15 + ANALYSIS_SUMMARY_REGIONS_SCANNED]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_regions_total]
    call    print_cstr
    mov     rdi, [r15 + ANALYSIS_SUMMARY_REGIONS_TOTAL]
    call    print_hex64
    call    print_nl

    lea     rdi, [section_gadgets]
    call    print_cstr

    lea     rdi, [label_max_depth]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_MAX_DEPTH]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_capacity]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_CAPACITY]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_candidate_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_ret_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_RET_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_ret_imm_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_RET_IMM_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_pattern_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_PATTERN_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_semantic_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_SEMANTIC_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_scored_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_SCORED_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_unknown_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_UNKNOWN_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_arg_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_ARG_CONTROL_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_sysnum_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_SYSCALL_NUM_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_systrig_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_pivot_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_STACK_PIVOT_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_align_count]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_ALIGNMENT_COUNT]
    call    print_hex64
    call    print_nl

    lea     rdi, [label_reg_coverage]
    call    print_cstr
    mov     rdi, [r12 + GADGET_SUMMARY_REGS_CONTROLLED]
    call    report_text_print_regs_bitmap
    call    print_nl

    cmp     qword [r12 + GADGET_SUMMARY_COUNT], 0
    jne     .candidate_loop_setup
    lea     rdi, [no_candidates]
    call    print_cstr
    jmp     .gadgets_done

.candidate_loop_setup:
    xor     rbp, rbp
.candidate_loop:
    cmp     rbp, [r12 + GADGET_SUMMARY_COUNT]
    jae     .gadgets_done

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r15, [r13 + rax]

    lea     rdi, [candidate_prefix]
    call    print_cstr
    mov     rdi, [r15 + GADGET_VIRTUAL_ADDRESS]
    call    print_hex64

    lea     rdi, [candidate_file_off]
    call    print_cstr
    mov     rdi, [r15 + GADGET_FILE_OFFSET]
    call    print_hex64

    cmp     qword [r15 + GADGET_SECTION_NAME_PTR], 0
    je      .candidate_section_done
    lea     rdi, [candidate_section]
    call    print_cstr
    mov     rdi, [r15 + GADGET_SECTION_NAME_PTR]
    mov     rsi, [r15 + GADGET_SECTION_NAME_LEN]
    call    report_text_print_section_name
.candidate_section_done:

    lea     rdi, [candidate_window]
    call    print_cstr
    mov     rdi, [r15 + GADGET_BYTE_START]
    call    print_hex64

    lea     rdi, [candidate_len]
    call    print_cstr
    mov     rdi, [r15 + GADGET_BYTE_LEN]
    call    print_hex64

    lea     rdi, [candidate_term]
    call    print_cstr
    mov     edi, [r15 + GADGET_TERMINATOR_TYPE]
    call    report_text_print_terminator

    lea     rdi, [candidate_pattern]
    call    print_cstr
    mov     edi, [r15 + GADGET_PATTERN_ID]
    call    report_text_print_pattern

    lea     rdi, [candidate_semantic]
    call    print_cstr
    mov     edi, [r15 + GADGET_SEMANTIC_CLASS]
    call    report_text_print_semantic

    lea     rdi, [candidate_regs]
    call    print_cstr
    mov     rdi, [r15 + GADGET_REGS_CONTROLLED]
    call    report_text_print_regs_bitmap

    lea     rdi, [candidate_stack_delta]
    call    print_cstr
    mov     rdi, [r15 + GADGET_STACK_DELTA]
    call    print_hex64

    lea     rdi, [candidate_score]
    call    print_cstr
    mov     edi, [r15 + GADGET_SCORE]
    call    print_u64_dec

    lea     rdi, [candidate_bytes]
    call    print_cstr
    call    report_text_print_candidate_bytes
    call    print_nl

    inc     rbp
    jmp     .candidate_loop

.gadgets_done:
    add     rsp, 8              ; discard saved analysis_summary pointer
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; report_text_print_terminator(edi=terminator_type)
;
; Prints a short terminator label without a trailing newline so caller can
; continue the candidate line.
report_text_print_terminator:
    cmp     edi, GADGET_TERM_RET
    je      .term_ret
    cmp     edi, GADGET_TERM_RET_IMM16
    je      .term_ret_imm16
    lea     rdi, [term_unknown]
    jmp     print_cstr
.term_ret:
    lea     rdi, [term_ret]
    jmp     print_cstr
.term_ret_imm16:
    lea     rdi, [term_ret_imm16]
    jmp     print_cstr

; report_text_print_pattern(edi=pattern_id)
;
; Prints the exact byte-template pattern label without a trailing newline.
; Pattern IDs are assigned by patterns.asm and remain separate from semantic
; classes, which classifier.asm now populates as a downstream layer.
report_text_print_pattern:
    cmp     edi, PATTERN_RET
    je      .pattern_ret
    cmp     edi, PATTERN_RET_IMM16
    je      .pattern_ret_imm16
    cmp     edi, PATTERN_POP_RAX_RET
    je      .pattern_pop_rax_ret
    cmp     edi, PATTERN_POP_RCX_RET
    je      .pattern_pop_rcx_ret
    cmp     edi, PATTERN_POP_RDX_RET
    je      .pattern_pop_rdx_ret
    cmp     edi, PATTERN_POP_RBX_RET
    je      .pattern_pop_rbx_ret
    cmp     edi, PATTERN_POP_RSP_RET
    je      .pattern_pop_rsp_ret
    cmp     edi, PATTERN_POP_RBP_RET
    je      .pattern_pop_rbp_ret
    cmp     edi, PATTERN_POP_RSI_RET
    je      .pattern_pop_rsi_ret
    cmp     edi, PATTERN_POP_RDI_RET
    je      .pattern_pop_rdi_ret
    cmp     edi, PATTERN_POP_R8_RET
    je      .pattern_pop_r8_ret
    cmp     edi, PATTERN_POP_R9_RET
    je      .pattern_pop_r9_ret
    cmp     edi, PATTERN_POP_R10_RET
    je      .pattern_pop_r10_ret
    cmp     edi, PATTERN_POP_R11_RET
    je      .pattern_pop_r11_ret
    cmp     edi, PATTERN_POP_R12_RET
    je      .pattern_pop_r12_ret
    cmp     edi, PATTERN_POP_R13_RET
    je      .pattern_pop_r13_ret
    cmp     edi, PATTERN_POP_R14_RET
    je      .pattern_pop_r14_ret
    cmp     edi, PATTERN_POP_R15_RET
    je      .pattern_pop_r15_ret
    cmp     edi, PATTERN_LEAVE_RET
    je      .pattern_leave_ret
    cmp     edi, PATTERN_SYSCALL_RET
    je      .pattern_syscall_ret
    lea     rdi, [pattern_unknown]
    jmp     print_cstr
.pattern_ret:
    lea     rdi, [pattern_ret]
    jmp     print_cstr
.pattern_ret_imm16:
    lea     rdi, [pattern_ret_imm16]
    jmp     print_cstr
.pattern_pop_rax_ret:
    lea     rdi, [pattern_pop_rax_ret]
    jmp     print_cstr
.pattern_pop_rcx_ret:
    lea     rdi, [pattern_pop_rcx_ret]
    jmp     print_cstr
.pattern_pop_rdx_ret:
    lea     rdi, [pattern_pop_rdx_ret]
    jmp     print_cstr
.pattern_pop_rbx_ret:
    lea     rdi, [pattern_pop_rbx_ret]
    jmp     print_cstr
.pattern_pop_rsp_ret:
    lea     rdi, [pattern_pop_rsp_ret]
    jmp     print_cstr
.pattern_pop_rbp_ret:
    lea     rdi, [pattern_pop_rbp_ret]
    jmp     print_cstr
.pattern_pop_rsi_ret:
    lea     rdi, [pattern_pop_rsi_ret]
    jmp     print_cstr
.pattern_pop_rdi_ret:
    lea     rdi, [pattern_pop_rdi_ret]
    jmp     print_cstr
.pattern_pop_r8_ret:
    lea     rdi, [pattern_pop_r8_ret]
    jmp     print_cstr
.pattern_pop_r9_ret:
    lea     rdi, [pattern_pop_r9_ret]
    jmp     print_cstr
.pattern_pop_r10_ret:
    lea     rdi, [pattern_pop_r10_ret]
    jmp     print_cstr
.pattern_pop_r11_ret:
    lea     rdi, [pattern_pop_r11_ret]
    jmp     print_cstr
.pattern_pop_r12_ret:
    lea     rdi, [pattern_pop_r12_ret]
    jmp     print_cstr
.pattern_pop_r13_ret:
    lea     rdi, [pattern_pop_r13_ret]
    jmp     print_cstr
.pattern_pop_r14_ret:
    lea     rdi, [pattern_pop_r14_ret]
    jmp     print_cstr
.pattern_pop_r15_ret:
    lea     rdi, [pattern_pop_r15_ret]
    jmp     print_cstr
.pattern_leave_ret:
    lea     rdi, [pattern_leave_ret]
    jmp     print_cstr
.pattern_syscall_ret:
    lea     rdi, [pattern_syscall_ret]
    jmp     print_cstr


; report_text_print_semantic(edi=semantic_class)
;
; Prints a semantic primitive label without a trailing newline.
report_text_print_semantic:
    cmp     edi, SEM_ARG_CONTROL
    je      .semantic_arg_control
    cmp     edi, SEM_SYSCALL_NUM_CONTROL
    je      .semantic_syscall_num
    cmp     edi, SEM_SYSCALL_TRIGGER
    je      .semantic_syscall_trig
    cmp     edi, SEM_STACK_PIVOT
    je      .semantic_stack_pivot
    cmp     edi, SEM_MEMORY_WRITE
    je      .semantic_memory_write
    cmp     edi, SEM_MEMORY_READ
    je      .semantic_memory_read
    cmp     edi, SEM_REG_TRANSFER
    je      .semantic_reg_transfer
    cmp     edi, SEM_ALIGNMENT
    je      .semantic_alignment
    cmp     edi, SEM_CLOBBER_HEAVY
    je      .semantic_clobber
    lea     rdi, [semantic_unknown]
    jmp     print_cstr
.semantic_arg_control:
    lea     rdi, [semantic_arg_control]
    jmp     print_cstr
.semantic_syscall_num:
    lea     rdi, [semantic_syscall_num]
    jmp     print_cstr
.semantic_syscall_trig:
    lea     rdi, [semantic_syscall_trig]
    jmp     print_cstr
.semantic_stack_pivot:
    lea     rdi, [semantic_stack_pivot]
    jmp     print_cstr
.semantic_memory_write:
    lea     rdi, [semantic_memory_write]
    jmp     print_cstr
.semantic_memory_read:
    lea     rdi, [semantic_memory_read]
    jmp     print_cstr
.semantic_reg_transfer:
    lea     rdi, [semantic_reg_transfer]
    jmp     print_cstr
.semantic_alignment:
    lea     rdi, [semantic_alignment]
    jmp     print_cstr
.semantic_clobber:
    lea     rdi, [semantic_clobber]
    jmp     print_cstr

%macro PRINT_REG_IF_SET 2
    mov     rax, rbx
    test    rax, (1 << %1)
    jz      %%skip
    test    r12, r12
    jz      %%no_sep
    lea     rdi, [reg_sep]
    call    print_cstr
%%no_sep:
    lea     rdi, [%2]
    call    print_cstr
    mov     r12, 1
%%skip:
%endmacro

; report_text_print_regs_bitmap(rdi=register_bitmap)
;
; Prints a compact pipe-separated register list such as rdi|rsi. Prints none
; when the bitmap is zero. The bitmap order follows include/structs.inc.
report_text_print_regs_bitmap:
    push    rbx
    push    r12
    sub     rsp, 8              ; keep nested System V calls 16-byte aligned

    mov     rbx, rdi
    xor     r12, r12

    PRINT_REG_IF_SET REG_RAX_BIT, reg_rax
    PRINT_REG_IF_SET REG_RBX_BIT, reg_rbx
    PRINT_REG_IF_SET REG_RCX_BIT, reg_rcx
    PRINT_REG_IF_SET REG_RDX_BIT, reg_rdx
    PRINT_REG_IF_SET REG_RSI_BIT, reg_rsi
    PRINT_REG_IF_SET REG_RDI_BIT, reg_rdi
    PRINT_REG_IF_SET REG_RBP_BIT, reg_rbp
    PRINT_REG_IF_SET REG_RSP_BIT, reg_rsp
    PRINT_REG_IF_SET REG_R8_BIT, reg_r8
    PRINT_REG_IF_SET REG_R9_BIT, reg_r9
    PRINT_REG_IF_SET REG_R10_BIT, reg_r10
    PRINT_REG_IF_SET REG_R11_BIT, reg_r11
    PRINT_REG_IF_SET REG_R12_BIT, reg_r12
    PRINT_REG_IF_SET REG_R13_BIT, reg_r13
    PRINT_REG_IF_SET REG_R14_BIT, reg_r14
    PRINT_REG_IF_SET REG_R15_BIT, reg_r15

    test    r12, r12
    jne     .regs_done
    lea     rdi, [regs_none]
    call    print_cstr
.regs_done:
    add     rsp, 8
    pop     r12
    pop     rbx
    ret

; report_text_print_candidate_bytes()
;
; Inputs from surrounding x64lens_report_text_gadgets loop:
;   R14 = mapped file base
;   R15 = current gadget_record pointer
;
; Output:
;   Space-separated lowercase hex byte sequence.
;
; Clobbers:
;   RAX, RCX, RDX, RDI. Preserves RBX/R12-R15 because the caller loop uses them.
report_text_print_candidate_bytes:
    push    rbx
    push    r12
    push    r13

    mov     rbx, [r15 + GADGET_BYTE_START]
    mov     r12, [r15 + GADGET_BYTE_LEN]
    xor     r13, r13
.byte_loop:
    cmp     r13, r12
    jae     .bytes_done
    test    r13, r13
    je      .no_space
    lea     rdi, [space_str]
    call    print_cstr
.no_space:
    lea     rdx, [r14 + rbx]
    movzx   rdi, byte [rdx + r13]
    call    print_hex8
    inc     r13
    jmp     .byte_loop
.bytes_done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; Local helper: print a bounded section name in a single-line-safe text form.
; RDI = pointer, RSI = trusted bounded length proven by shdr.asm.
; Printable ASCII bytes are emitted directly except backslash, which is escaped.
; Control bytes, DEL, and high-bit bytes are emitted as \xNN so adversarial
; section names cannot split report lines or inject terminal controls.
report_text_print_section_name:
    push    rbx
    push    r12
    push    r13

    mov     r12, rdi
    mov     r13, rsi
.print_loop:
    test    r13, r13
    jz      .done

    movzx   ebx, byte [r12]
    cmp     bl, 0x5c
    je      .print_backslash
    cmp     bl, 0x20
    jb      .print_hex_escape
    cmp     bl, 0x7e
    ja      .print_hex_escape

    mov     [rel section_safe_byte], bl
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    lea     rsi, [rel section_safe_byte]
    mov     rdx, 1
    syscall
    jmp     .next

.print_backslash:
    lea     rdi, [section_escape_bslash]
    call    print_cstr
    jmp     .next

.print_hex_escape:
    lea     rdi, [section_escape_hex]
    call    print_cstr
    mov     rdi, rbx
    call    print_hex8

.next:
    inc     r12
    dec     r13
    jmp     .print_loop

.done:
    pop     r13
    pop     r12
    pop     rbx
    ret
