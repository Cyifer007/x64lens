; report_json.asm
;
; Purpose:
;   JSON report emitter.
;
; Module scope:
;   Render versioned machine-readable output for benchmarks, CI/CD, dashboards,
;   and future enterprise integrations. JSON is emitted from internal records,
;   not by scraping human-readable text output.
;
; Sprint 5 scope:
;   Emit initial `gadgets --format json` reports with schema/tool version,
;   target metadata, baseline mitigation facts, separated metric counts,
;   primitive coverage, scored gadget records, and explicit limitations.

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

section .rodata
j_open:                 db "{", 10, 0
j_close:                db "}", 10, 0
j_comma_nl:             db ",", 10, 0
j_nl:                   db 10, 0
j_q:                    db 0x22, 0
j_colon:                db ":", 0
j_true:                 db "true", 0
j_false:                db "false", 0
j_null:                 db "null", 0
j_empty_array:          db "[]", 0
j_array_open:           db "[", 0
j_array_close:          db "]", 0
j_comma:                db ",", 0
j_indent2:              db "  ", 0
j_indent4:              db "    ", 0
j_indent6:              db "      ", 0

field_schema:           db '  "schema_version":"', X64LENS_SCHEMA, '"', 0
field_tool:             db '  "tool":"', X64LENS_NAME, '"', 0
field_tool_version:     db '  "tool_version":"', X64LENS_VERSION, '"', 0
field_target_open:      db '  "target":{', 10, 0
field_target_path:      db '    "path":"', 0
field_target_format:    db '    "format":"ELF64",', 10, 0
field_target_arch:      db '    "arch":"x86_64",', 10, 0
field_target_size:      db '    "file_size":', 0
field_target_entry:     db '    "entry":"', 0
field_object_close:     db '  }', 0
field_mitigations_open: db '  "mitigations":{', 10, 0
field_nx_stack:         db '    "nx_stack":', 0
field_pie:              db '    "pie":', 0
field_relro:            db '    "relro":"', 0
field_rwx:              db '    "rwx_load_segment":', 0
field_dynamic:          db '    "dynamic_linking":', 0
field_bind_now:         db '    "bind_now":', 0
field_dyn_entry_count:  db '    "dynamic_entry_count":', 0
field_dyn_terminated:   db '    "dynamic_terminated":', 0
relro_partial:          db "partial", 0
relro_full:             db "full", 0
relro_none:             db "none", 0
field_counts_open:      db '  "counts":{', 10, 0
field_raw_count:        db '    "raw_candidate_count":', 0
field_ret_count:        db '    "ret_count":', 0
field_ret_imm_count:    db '    "ret_imm16_count":', 0
field_exact_count:      db '    "exact_pattern_count":', 0
field_sem_count:        db '    "semantic_candidate_count":', 0
field_unknown_count:    db '    "unknown_candidate_count":', 0
field_scored_count:     db '    "scored_candidate_count":', 0
field_coverage_open:    db '  "primitive_coverage":{', 10, 0
field_cov_arg:          db '    "arg_control":', 0
field_cov_sysnum:       db '    "syscall_num_control":', 0
field_cov_systrig:      db '    "syscall_trigger":', 0
field_cov_pivot:        db '    "stack_pivot":', 0
field_cov_align:        db '    "alignment":', 0
field_cov_registers:    db '    "registers":', 0
field_gadgets_open:     db '  "gadgets":[', 10, 0
field_limitations:      db '  "limitations":["Pattern-based scanner, not full x86_64 decoder","Pattern labels describe recognized suffixes, not necessarily complete decoded instruction windows","Exploitability requires an independent vulnerability and runtime context"]', 10, 0

f_va:                   db '      "va":"', 0
f_file_offset:          db '      "file_offset":"', 0
f_bytes:                db '      "bytes":"', 0
f_terminator:           db '      "terminator":"', 0
f_pattern:              db '      "pattern":"', 0
f_semantic:             db '      "semantic_class":"', 0
f_controls:             db '      "controls":', 0
f_stack_delta:          db '      "stack_delta":', 0
f_stack_known:          db '      "stack_delta_known":', 0
f_score:                db '      "score":', 0
candidate_open:         db '    {', 10, 0
candidate_close:        db '    }', 0

term_ret_s:             db "ret", 0
term_ret_imm16_s:       db "ret imm16", 0
term_unknown_s:         db "unknown", 0
pattern_unknown_s:      db "unknown", 0
pattern_ret_s:          db "ret", 0
pattern_ret_imm16_s:    db "ret imm16", 0
pattern_pop_rax_s:      db "pop rax; ret", 0
pattern_pop_rcx_s:      db "pop rcx; ret", 0
pattern_pop_rdx_s:      db "pop rdx; ret", 0
pattern_pop_rbx_s:      db "pop rbx; ret", 0
pattern_pop_rsp_s:      db "pop rsp; ret", 0
pattern_pop_rbp_s:      db "pop rbp; ret", 0
pattern_pop_rsi_s:      db "pop rsi; ret", 0
pattern_pop_rdi_s:      db "pop rdi; ret", 0
pattern_pop_r8_s:       db "pop r8; ret", 0
pattern_pop_r9_s:       db "pop r9; ret", 0
pattern_pop_r10_s:      db "pop r10; ret", 0
pattern_pop_r11_s:      db "pop r11; ret", 0
pattern_pop_r12_s:      db "pop r12; ret", 0
pattern_pop_r13_s:      db "pop r13; ret", 0
pattern_pop_r14_s:      db "pop r14; ret", 0
pattern_pop_r15_s:      db "pop r15; ret", 0
pattern_leave_s:        db "leave; ret", 0
pattern_syscall_s:      db "syscall; ret", 0
semantic_unknown_s:     db "unknown_candidate", 0
semantic_arg_s:         db "arg_control", 0
semantic_sysnum_s:      db "syscall_num_control", 0
semantic_systrig_s:     db "syscall_trigger", 0
semantic_pivot_s:       db "stack_pivot", 0
semantic_memwrite_s:    db "memory_write", 0
semantic_memread_s:     db "memory_read", 0
semantic_regxfer_s:     db "reg_transfer", 0
semantic_align_s:       db "alignment", 0
semantic_clobber_s:     db "clobber_heavy", 0
reg_rax_s:              db "rax", 0
reg_rbx_s:              db "rbx", 0
reg_rcx_s:              db "rcx", 0
reg_rdx_s:              db "rdx", 0
reg_rsi_s:              db "rsi", 0
reg_rdi_s:              db "rdi", 0
reg_rbp_s:              db "rbp", 0
reg_rsp_s:              db "rsp", 0
reg_r8_s:               db "r8", 0
reg_r9_s:               db "r9", 0
reg_r10_s:              db "r10", 0
reg_r11_s:              db "r11", 0
reg_r12_s:              db "r12", 0
reg_r13_s:              db "r13", 0
reg_r14_s:              db "r14", 0
reg_r15_s:              db "r15", 0

section .bss
json_path_ptr:          resq 1
json_base_ptr:          resq 1
json_file_size:         resq 1
json_phdr_summary:      resq 1
json_gadget_summary:    resq 1
json_gadget_records:    resq 1
json_current_record:    resq 1
json_char_buf:          resb 3

section .text
global x64lens_report_json_gadgets

%macro JSON_FIELD_COMMA_NL 0
    lea     rdi, [j_comma_nl]
    call    print_cstr
%endmacro

%macro JSON_REG_IF_SET 2
    mov     rax, rbx
    test    rax, (1 << %1)
    jz      %%skip
    test    r12, r12
    jz      %%no_comma
    lea     rdi, [j_comma]
    call    print_cstr
%%no_comma:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [%2]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    mov     r12, 1
%%skip:
%endmacro

; x64lens_report_json_gadgets(path=rdi, mapped_base=rsi, file_size=rdx,
;                             phdr_summary=rcx, gadget_summary=r8,
;                             gadget_records=r9)
;
; Output:
;   Versioned JSON report on STDOUT.
x64lens_report_json_gadgets:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     [json_path_ptr], rdi
    mov     [json_base_ptr], rsi
    mov     [json_file_size], rdx
    mov     [json_phdr_summary], rcx
    mov     [json_gadget_summary], r8
    mov     [json_gadget_records], r9

    lea     rdi, [j_open]
    call    print_cstr

    lea     rdi, [field_schema]
    call    print_cstr
    JSON_FIELD_COMMA_NL
    lea     rdi, [field_tool]
    call    print_cstr
    JSON_FIELD_COMMA_NL
    lea     rdi, [field_tool_version]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    call    json_print_target
    JSON_FIELD_COMMA_NL
    call    json_print_mitigations
    JSON_FIELD_COMMA_NL
    call    json_print_counts
    JSON_FIELD_COMMA_NL
    call    json_print_coverage
    JSON_FIELD_COMMA_NL
    call    json_print_gadget_array
    JSON_FIELD_COMMA_NL
    lea     rdi, [field_limitations]
    call    print_cstr

    lea     rdi, [j_close]
    call    print_cstr

    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

json_print_target:
    lea     rdi, [field_target_open]
    call    print_cstr

    lea     rdi, [field_target_path]
    call    print_cstr
    mov     rdi, [json_path_ptr]
    call    json_print_escaped_cstr
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_target_format]
    call    print_cstr
    lea     rdi, [field_target_arch]
    call    print_cstr

    lea     rdi, [field_target_size]
    call    print_cstr
    mov     rdi, [json_file_size]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_target_entry]
    call    print_cstr
    mov     rax, [json_base_ptr]
    mov     rdi, [rax + E_ENTRY]
    call    print_hex64
    lea     rdi, [j_q]
    call    print_cstr
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    ret

json_print_mitigations:
    lea     rdi, [field_mitigations_open]
    call    print_cstr
    mov     rbx, [json_phdr_summary]

    lea     rdi, [field_nx_stack]
    call    print_cstr
    cmp     qword [rbx + PHDR_SUMMARY_GNU_STACK_SEEN], 0
    je      .nx_unknown
    cmp     qword [rbx + PHDR_SUMMARY_GNU_STACK_EXEC], 0
    je      .nx_true
    lea     rdi, [j_false]
    call    print_cstr
    jmp     .nx_done
.nx_true:
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .nx_done
.nx_unknown:
    lea     rdi, [j_null]
    call    print_cstr
.nx_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_pie]
    call    print_cstr
    mov     rdi, [rbx + PHDR_SUMMARY_PIE]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_relro]
    call    print_cstr
    cmp     qword [rbx + PHDR_SUMMARY_RELRO_SEEN], 0
    je      .relro_none
    cmp     qword [rbx + PHDR_SUMMARY_BIND_NOW], 0
    jne     .relro_full
    lea     rdi, [relro_partial]
    call    print_cstr
    jmp     .relro_done
.relro_full:
    lea     rdi, [relro_full]
    call    print_cstr
    jmp     .relro_done
.relro_none:
    lea     rdi, [relro_none]
    call    print_cstr
.relro_done:
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_rwx]
    call    print_cstr
    mov     rdi, [rbx + PHDR_SUMMARY_RWX_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_dynamic]
    call    print_cstr
    mov     rdi, [rbx + PHDR_SUMMARY_DYNAMIC_SEEN]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_bind_now]
    call    print_cstr
    cmp     qword [rbx + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .bind_now_null
    mov     rdi, [rbx + PHDR_SUMMARY_BIND_NOW]
    call    json_print_bool_nonzero
    jmp     .bind_now_done
.bind_now_null:
    lea     rdi, [j_null]
    call    print_cstr
.bind_now_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_dyn_entry_count]
    call    print_cstr
    mov     rdi, [rbx + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_dyn_terminated]
    call    print_cstr
    cmp     qword [rbx + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .dynamic_terminated_null
    mov     rdi, [rbx + PHDR_SUMMARY_DYNAMIC_NULL_SEEN]
    call    json_print_bool_nonzero
    jmp     .dynamic_terminated_done
.dynamic_terminated_null:
    lea     rdi, [j_null]
    call    print_cstr
.dynamic_terminated_done:
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    ret

json_print_counts:
    lea     rdi, [field_counts_open]
    call    print_cstr
    mov     rbx, [json_gadget_summary]

    lea     rdi, [field_raw_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_ret_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_RET_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_ret_imm_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_RET_IMM_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_exact_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_PATTERN_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_sem_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_SEMANTIC_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_unknown_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_UNKNOWN_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_scored_count]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_SCORED_COUNT]
    call    print_u64_dec
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    ret

json_print_coverage:
    lea     rdi, [field_coverage_open]
    call    print_cstr
    mov     rbx, [json_gadget_summary]

    lea     rdi, [field_cov_arg]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_ARG_CONTROL_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_sysnum]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_SYSCALL_NUM_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_systrig]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_pivot]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_STACK_PIVOT_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_align]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_ALIGNMENT_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_registers]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_REGS_CONTROLLED]
    call    json_print_regs_array
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    ret

json_print_gadget_array:
    lea     rdi, [field_gadgets_open]
    call    print_cstr

    mov     rbx, [json_gadget_summary]
    cmp     qword [rbx + GADGET_SUMMARY_COUNT], 0
    je      .empty_done

    xor     rbp, rbp
.loop:
    mov     rbx, [json_gadget_summary]
    cmp     rbp, [rbx + GADGET_SUMMARY_COUNT]
    jae     .done

    test    rbp, rbp
    jz      .no_leading_comma
    JSON_FIELD_COMMA_NL
.no_leading_comma:
    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    mov     rdx, [json_gadget_records]
    add     rdx, rax
    mov     [json_current_record], rdx

    call    json_print_one_gadget

    inc     rbp
    jmp     .loop

.empty_done:
.done:
    call    print_nl
    lea     rdi, [j_indent2]
    call    print_cstr
    lea     rdi, [j_array_close]
    call    print_cstr
    ret

json_print_one_gadget:
    lea     rdi, [candidate_open]
    call    print_cstr

    lea     rdi, [f_va]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_VIRTUAL_ADDRESS]
    call    print_hex64
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_file_offset]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_FILE_OFFSET]
    call    print_hex64
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_bytes]
    call    print_cstr
    call    json_print_candidate_bytes
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_terminator]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     edi, [rbx + GADGET_TERMINATOR_TYPE]
    call    json_print_terminator
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_pattern]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     edi, [rbx + GADGET_PATTERN_ID]
    call    json_print_pattern
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_semantic]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     edi, [rbx + GADGET_SEMANTIC_CLASS]
    call    json_print_semantic
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_controls]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_REGS_CONTROLLED]
    call    json_print_regs_array
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_stack_delta]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     eax, [rbx + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_UNKNOWN_CANDIDATE
    je      .stack_unknown
    cmp     eax, SEM_STACK_PIVOT
    je      .stack_unknown
    mov     rdi, [rbx + GADGET_STACK_DELTA]
    call    print_u64_dec
    jmp     .stack_done
.stack_unknown:
    lea     rdi, [j_null]
    call    print_cstr
.stack_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_stack_known]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     eax, [rbx + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_UNKNOWN_CANDIDATE
    je      .known_false
    cmp     eax, SEM_STACK_PIVOT
    je      .known_false
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .known_done
.known_false:
    lea     rdi, [j_false]
    call    print_cstr
.known_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_score]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     edi, [rbx + GADGET_SCORE]
    test    edi, edi
    jz      .score_null
    call    print_u64_dec
    jmp     .score_done
.score_null:
    lea     rdi, [j_null]
    call    print_cstr
.score_done:
    call    print_nl

    lea     rdi, [candidate_close]
    call    print_cstr
    ret

json_print_bool_nonzero:
    test    rdi, rdi
    jz      .false
    lea     rdi, [j_true]
    jmp     print_cstr
.false:
    lea     rdi, [j_false]
    jmp     print_cstr

json_print_escaped_cstr:
    push    rbx
    mov     rbx, rdi
.loop:
    mov     al, [rbx]
    test    al, al
    je      .done
    cmp     al, 0x22
    je      .escape_quote
    cmp     al, 0x5c
    je      .escape_backslash
    cmp     al, 10
    je      .escape_newline
    cmp     al, 13
    je      .escape_cr
    cmp     al, 9
    je      .escape_tab
    cmp     al, 0x20
    jb      .control_char
    mov     [json_char_buf], al
    mov     byte [json_char_buf + 1], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.escape_quote:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 0x22
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.escape_backslash:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 0x5c
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.escape_newline:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 'n'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.escape_cr:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 'r'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.escape_tab:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 't'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
    jmp     .advance
.control_char:
    mov     byte [json_char_buf], '?'
    mov     byte [json_char_buf + 1], 0
    lea     rdi, [json_char_buf]
    call    print_cstr
.advance:
    inc     rbx
    jmp     .loop
.done:
    pop     rbx
    ret

json_print_candidate_bytes:
    push    rbx
    push    r12
    push    r13

    mov     rbx, [json_current_record]
    mov     r12, [rbx + GADGET_BYTE_START]
    mov     r13, [rbx + GADGET_BYTE_LEN]
    xor     rbx, rbx
.byte_loop:
    cmp     rbx, r13
    jae     .done
    mov     rdx, [json_base_ptr]
    add     rdx, r12
    movzx   rdi, byte [rdx + rbx]
    call    print_hex8
    inc     rbx
    jmp     .byte_loop
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

json_print_regs_array:
    push    rbx
    push    r12

    mov     rbx, rdi
    xor     r12, r12
    lea     rdi, [j_array_open]
    call    print_cstr

    JSON_REG_IF_SET REG_RAX_BIT, reg_rax_s
    JSON_REG_IF_SET REG_RBX_BIT, reg_rbx_s
    JSON_REG_IF_SET REG_RCX_BIT, reg_rcx_s
    JSON_REG_IF_SET REG_RDX_BIT, reg_rdx_s
    JSON_REG_IF_SET REG_RSI_BIT, reg_rsi_s
    JSON_REG_IF_SET REG_RDI_BIT, reg_rdi_s
    JSON_REG_IF_SET REG_RBP_BIT, reg_rbp_s
    JSON_REG_IF_SET REG_RSP_BIT, reg_rsp_s
    JSON_REG_IF_SET REG_R8_BIT, reg_r8_s
    JSON_REG_IF_SET REG_R9_BIT, reg_r9_s
    JSON_REG_IF_SET REG_R10_BIT, reg_r10_s
    JSON_REG_IF_SET REG_R11_BIT, reg_r11_s
    JSON_REG_IF_SET REG_R12_BIT, reg_r12_s
    JSON_REG_IF_SET REG_R13_BIT, reg_r13_s
    JSON_REG_IF_SET REG_R14_BIT, reg_r14_s
    JSON_REG_IF_SET REG_R15_BIT, reg_r15_s

    lea     rdi, [j_array_close]
    call    print_cstr
    pop     r12
    pop     rbx
    ret

json_print_terminator:
    cmp     edi, GADGET_TERM_RET
    je      .ret
    cmp     edi, GADGET_TERM_RET_IMM16
    je      .ret_imm
    lea     rdi, [term_unknown_s]
    jmp     print_cstr
.ret:
    lea     rdi, [term_ret_s]
    jmp     print_cstr
.ret_imm:
    lea     rdi, [term_ret_imm16_s]
    jmp     print_cstr

json_print_pattern:
    cmp     edi, PATTERN_RET
    je      .ret
    cmp     edi, PATTERN_RET_IMM16
    je      .ret_imm
    cmp     edi, PATTERN_POP_RAX_RET
    je      .pop_rax
    cmp     edi, PATTERN_POP_RCX_RET
    je      .pop_rcx
    cmp     edi, PATTERN_POP_RDX_RET
    je      .pop_rdx
    cmp     edi, PATTERN_POP_RBX_RET
    je      .pop_rbx
    cmp     edi, PATTERN_POP_RSP_RET
    je      .pop_rsp
    cmp     edi, PATTERN_POP_RBP_RET
    je      .pop_rbp
    cmp     edi, PATTERN_POP_RSI_RET
    je      .pop_rsi
    cmp     edi, PATTERN_POP_RDI_RET
    je      .pop_rdi
    cmp     edi, PATTERN_POP_R8_RET
    je      .pop_r8
    cmp     edi, PATTERN_POP_R9_RET
    je      .pop_r9
    cmp     edi, PATTERN_POP_R10_RET
    je      .pop_r10
    cmp     edi, PATTERN_POP_R11_RET
    je      .pop_r11
    cmp     edi, PATTERN_POP_R12_RET
    je      .pop_r12
    cmp     edi, PATTERN_POP_R13_RET
    je      .pop_r13
    cmp     edi, PATTERN_POP_R14_RET
    je      .pop_r14
    cmp     edi, PATTERN_POP_R15_RET
    je      .pop_r15
    cmp     edi, PATTERN_LEAVE_RET
    je      .leave
    cmp     edi, PATTERN_SYSCALL_RET
    je      .syscall
    lea     rdi, [pattern_unknown_s]
    jmp     print_cstr
.ret:      lea rdi, [pattern_ret_s]       ; fall through via jmp below
           jmp print_cstr
.ret_imm:  lea rdi, [pattern_ret_imm16_s]
           jmp print_cstr
.pop_rax:  lea rdi, [pattern_pop_rax_s]
           jmp print_cstr
.pop_rcx:  lea rdi, [pattern_pop_rcx_s]
           jmp print_cstr
.pop_rdx:  lea rdi, [pattern_pop_rdx_s]
           jmp print_cstr
.pop_rbx:  lea rdi, [pattern_pop_rbx_s]
           jmp print_cstr
.pop_rsp:  lea rdi, [pattern_pop_rsp_s]
           jmp print_cstr
.pop_rbp:  lea rdi, [pattern_pop_rbp_s]
           jmp print_cstr
.pop_rsi:  lea rdi, [pattern_pop_rsi_s]
           jmp print_cstr
.pop_rdi:  lea rdi, [pattern_pop_rdi_s]
           jmp print_cstr
.pop_r8:   lea rdi, [pattern_pop_r8_s]
           jmp print_cstr
.pop_r9:   lea rdi, [pattern_pop_r9_s]
           jmp print_cstr
.pop_r10:  lea rdi, [pattern_pop_r10_s]
           jmp print_cstr
.pop_r11:  lea rdi, [pattern_pop_r11_s]
           jmp print_cstr
.pop_r12:  lea rdi, [pattern_pop_r12_s]
           jmp print_cstr
.pop_r13:  lea rdi, [pattern_pop_r13_s]
           jmp print_cstr
.pop_r14:  lea rdi, [pattern_pop_r14_s]
           jmp print_cstr
.pop_r15:  lea rdi, [pattern_pop_r15_s]
           jmp print_cstr
.leave:    lea rdi, [pattern_leave_s]
           jmp print_cstr
.syscall:  lea rdi, [pattern_syscall_s]
           jmp print_cstr

json_print_semantic:
    cmp     edi, SEM_ARG_CONTROL
    je      .arg
    cmp     edi, SEM_SYSCALL_NUM_CONTROL
    je      .sysnum
    cmp     edi, SEM_SYSCALL_TRIGGER
    je      .systrig
    cmp     edi, SEM_STACK_PIVOT
    je      .pivot
    cmp     edi, SEM_MEMORY_WRITE
    je      .memwrite
    cmp     edi, SEM_MEMORY_READ
    je      .memread
    cmp     edi, SEM_REG_TRANSFER
    je      .regxfer
    cmp     edi, SEM_ALIGNMENT
    je      .align
    cmp     edi, SEM_CLOBBER_HEAVY
    je      .clobber
    lea     rdi, [semantic_unknown_s]
    jmp     print_cstr
.arg:      lea rdi, [semantic_arg_s]
           jmp print_cstr
.sysnum:   lea rdi, [semantic_sysnum_s]
           jmp print_cstr
.systrig:  lea rdi, [semantic_systrig_s]
           jmp print_cstr
.pivot:    lea rdi, [semantic_pivot_s]
           jmp print_cstr
.memwrite: lea rdi, [semantic_memwrite_s]
           jmp print_cstr
.memread:  lea rdi, [semantic_memread_s]
           jmp print_cstr
.regxfer:  lea rdi, [semantic_regxfer_s]
           jmp print_cstr
.align:    lea rdi, [semantic_align_s]
           jmp print_cstr
.clobber:  lea rdi, [semantic_clobber_s]
           jmp print_cstr
