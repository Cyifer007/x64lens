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
; Current scope:
;   Emit shared `gadgets` and `analyze` reports with schema/tool version,
;   explicit report and command identity, analysis completeness, target and
;   mitigation facts, separated metric counts, primitive coverage, scored
;   gadget records, per-candidate provenance, and explicit limitations.

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
j_object_open:          db "{", 0
j_object_close:         db "}", 0
j_comma:                db ",", 0
j_u00_prefix:           db 0x5c, "u00", 0
j_indent2:              db "  ", 0
j_indent4:              db "    ", 0
j_indent6:              db "      ", 0

field_schema:           db '  "schema_version":"', X64LENS_SCHEMA, '"', 0
field_tool:             db '  "tool":"', X64LENS_NAME, '"', 0
field_tool_version:     db '  "tool_version":"', X64LENS_VERSION, '"', 0
field_report_type:      db '  "report_type":"', 0
field_command:          db '  "command":"', 0
identity_analysis:      db "analysis", 0
identity_gadgets:       db "gadgets", 0
identity_analyze:       db "analyze", 0
identity_unknown:       db "unknown", 0
field_analysis_open:    db '  "analysis":{', 10, 0
field_analysis_complete: db '    "complete":', 0
field_analysis_max_depth: db '    "max_depth":', 0
field_analysis_capacity: db '    "candidate_capacity":', 0
field_analysis_count:   db '    "candidate_count":', 0
field_analysis_truncated: db '    "candidate_truncated":', 0
field_analysis_dropped: db '    "candidate_dropped_count":', 0
field_analysis_dropped_known: db '    "candidate_dropped_count_known":', 0
field_analysis_regions_scanned: db '    "regions_scanned":', 0
field_analysis_regions_total: db '    "regions_total":', 0
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
field_canary:           db '    "canary":"', 0
field_stripped:         db '    "stripped":"', 0
field_rwx:              db '    "rwx_load_segment":', 0
field_dynamic:          db '    "dynamic_linking":', 0
field_bind_now:         db '    "bind_now":', 0
field_dyn_entry_count:  db '    "dynamic_entry_count":', 0
field_dyn_terminated:   db '    "dynamic_terminated":', 0
relro_partial:          db "partial", 0
relro_full:             db "full", 0
relro_none:             db "none", 0
canary_present:         db "present", 0
canary_absent:          db "absent", 0
canary_unknown:         db "unknown", 0
stripped_yes:           db "stripped", 0
stripped_no:            db "not_stripped", 0
stripped_unknown:       db "unknown", 0
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
field_cov_reg_transfer: db '    "reg_transfer":', 0
field_cov_memory_write: db '    "memory_write":', 0
field_cov_memory_read: db '    "memory_read":', 0
field_cov_registers:    db '    "registers":', 0
field_gadgets_open:     db '  "gadgets":[', 10, 0
field_limitations:      db '  "limitations":["Pattern-based scanner, not full x86_64 decoder","Pattern labels describe recognized suffixes, not necessarily complete decoded instruction windows","Analysis completeness covers bounded candidate enumeration, not decoder validation","Exploitability requires an independent vulnerability and runtime context"]', 10, 0

f_va:                   db '      "va":"', 0
f_file_offset:          db '      "file_offset":"', 0
f_section:             db '      "section":', 0
f_bytes:                db '      "bytes":"', 0
f_terminator:           db '      "terminator":"', 0
f_pattern:              db '      "pattern":"', 0
f_semantic:             db '      "semantic_class":"', 0
f_controls:             db '      "controls":', 0
f_stack_pop_order:      db '      "stack_pop_order":', 0
f_register_transfer:    db '      "register_transfer":', 0
f_memory_access:       db '      "memory_access":', 0
f_arch_effects:       db '      "architectural_effects":', 0
f_transfer_source:      db '"source":"', 0
f_transfer_destination: db ',"destination":"', 0
f_memory_direction:   db '"direction":"', 0
f_memory_base:        db ',"base":"', 0
f_memory_index:       db ',"index":', 0
f_memory_scale:       db ',"scale":', 0
f_memory_displacement: db ',"displacement":', 0
f_memory_displacement_known: db ',"displacement_known":', 0
f_memory_width:       db ',"width_bytes":', 0
f_memory_value:       db ',"value_register":"', 0
f_memory_dereference: db ',"dereference":', 0
f_arch_regs_read:     db '"registers_read":', 0
f_arch_regs_written:  db ',"registers_written":', 0
f_arch_flags_read:    db ',"flags_read":', 0
f_arch_flags_written: db ',"flags_written":', 0
f_arch_control:       db ',"control_flow":', 0
f_arch_stack_base:    db ',"stack_base":', 0
f_arch_stack_reads:   db ',"stack_read_count":', 0
f_arch_stack_writes:  db ',"stack_write_count":', 0
f_arch_first_read:    db ',"first_stack_read_offset":', 0
f_arch_stride:        db ',"stack_read_stride":', 0
f_arch_offsets_known: db ',"stack_offsets_known":', 0
f_arch_complete:      db ',"model_complete":', 0
f_clobbers:             db '      "clobbers":', 0
f_side_effects:         db '      "side_effects":', 0
f_stack_delta:          db '      "stack_delta":', 0
f_stack_known:          db '      "stack_delta_known":', 0
f_evidence_open:        db '      "evidence":{', 10, 0
f_evidence_kind:        db '        "kind":"', 0
f_evidence_raw:         db '        "raw_candidate":', 0
f_evidence_exact:       db '        "exact_suffix":', 0
f_evidence_sem_source:  db '        "semantic_source":', 0
f_evidence_validator:   db '        "validator":"', 0
f_evidence_suffix_off:  db '        "matched_suffix_offset":', 0
f_evidence_suffix_len:  db '        "matched_suffix_length":', 0
f_evidence_full_valid:  db '        "full_sequence_valid":', 0
f_evidence_close:       db '      }', 0
f_score:                db '      "score":', 0
candidate_open:         db '    {', 10, 0
candidate_close:        db '    }', 0

evidence_kind_raw_s:       db "raw_only", 0
evidence_kind_exact_s:     db "exact_suffix", 0
evidence_kind_sem_exact_s: db "semantic_exact", 0
evidence_kind_decoded_s:   db "decoder_validated", 0
evidence_kind_sem_dec_s:   db "semantic_decoded", 0
evidence_source_exact_s:   db "exact", 0
evidence_source_decoded_s: db "decoded", 0
evidence_validator_raw_s:  db "x64lens-raw-scanner", 0
evidence_validator_exact_s: db "x64lens-exact-suffix", 0
evidence_validator_decoder_s: db "x64lens-decoder", 0
evidence_validator_unknown_s: db "unknown", 0

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
pattern_multi_pop_s:    db "pop reg; pop reg; ret", 0
pattern_mov_reg_reg_s:  db "mov reg, reg; ret", 0
pattern_add_rsp_imm8_s: db "add rsp, imm8; ret", 0
pattern_mov_mem_reg_s: db "mov [base], value; ret", 0
pattern_mov_reg_mem_s: db "mov value, [base]; ret", 0
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
side_effect_stack_read_s:  db "stack_read", 0
side_effect_stack_pivot_s: db "stack_pivot", 0
side_effect_syscall_s:     db "syscall", 0
side_effect_ret_imm16_s:   db "ret_imm16", 0
side_effect_register_write_s: db "register_write", 0
side_effect_stack_adjust_s: db "stack_adjust", 0
side_effect_flags_write_s: db "flags_write", 0
side_effect_memory_read_s: db "memory_read", 0
side_effect_memory_write_s: db "memory_write", 0
side_effect_control_transfer_s: db "control_transfer", 0
arch_flag_cf_s:        db "cf", 0
arch_flag_pf_s:        db "pf", 0
arch_flag_af_s:        db "af", 0
arch_flag_zf_s:        db "zf", 0
arch_flag_sf_s:        db "sf", 0
arch_flag_tf_s:        db "tf", 0
arch_flag_if_s:        db "if", 0
arch_flag_df_s:        db "df", 0
arch_flag_of_s:        db "of", 0
arch_control_return_s: db "return", 0
arch_control_syscall_s: db "syscall", 0
arch_stack_rsp_s:      db "entry_rsp", 0
arch_stack_rbp_s:      db "entry_rbp", 0
arch_stack_dynamic_s:  db "dynamic", 0
memory_direction_read_s: db "read", 0
memory_direction_write_s: db "write", 0

section .bss
json_path_ptr:          resq 1
json_base_ptr:          resq 1
json_file_size:         resq 1
json_phdr_summary:      resq 1
json_gadget_summary:    resq 1
json_gadget_records:    resq 1
json_analysis_summary:  resq 1
json_candidate_evidence: resq 1
json_memory_effects:    resq 1
json_candidate_effects: resq 1
json_current_record:    resq 1
json_current_evidence:  resq 1
json_current_memory:    resq 1
json_current_effect:    resq 1
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

%macro JSON_EFFECT_IF_SET 2
    test    rbx, %1
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
;                             gadget_records=r9, analysis_summary=stack_arg_7,
;                             candidate_evidence=stack_arg_8,
;                             memory_effects=stack_arg_9,
;                             candidate_effects=stack_arg_10)
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
    ; Six saved registers move caller stack arguments seven through ten to
    ; [rsp+56], [rsp+64], [rsp+72], and [rsp+80]. Load them before correcting the inherited 8-byte
    ; entry misalignment. The extra slot keeps RSP 16-byte aligned before every
    ; nested System V call made by this reporter.
    mov     rax, [rsp + 56]
    mov     [json_analysis_summary], rax
    mov     rax, [rsp + 64]
    mov     [json_candidate_evidence], rax
    mov     rax, [rsp + 72]
    mov     [json_memory_effects], rax
    mov     rax, [rsp + 80]
    mov     [json_candidate_effects], rax
    sub     rsp, 8

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
    call    json_print_report_identity
    JSON_FIELD_COMMA_NL
    call    json_print_analysis
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

    add     rsp, 8
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

json_print_report_identity:
    sub     rsp, 8              ; align nested System V calls
    mov     rbx, [json_analysis_summary]

    lea     rdi, [field_report_type]
    call    print_cstr
    cmp     qword [rbx + ANALYSIS_SUMMARY_REPORT_TYPE], REPORT_TYPE_ANALYSIS
    jne     .report_type_unknown
    lea     rdi, [identity_analysis]
    call    print_cstr
    jmp     .report_type_done
.report_type_unknown:
    lea     rdi, [identity_unknown]
    call    print_cstr
.report_type_done:
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_command]
    call    print_cstr
    cmp     qword [rbx + ANALYSIS_SUMMARY_COMMAND], REPORT_COMMAND_GADGETS
    je      .command_gadgets
    cmp     qword [rbx + ANALYSIS_SUMMARY_COMMAND], REPORT_COMMAND_ANALYZE
    je      .command_analyze
    lea     rdi, [identity_unknown]
    call    print_cstr
    jmp     .command_done
.command_gadgets:
    lea     rdi, [identity_gadgets]
    call    print_cstr
    jmp     .command_done
.command_analyze:
    lea     rdi, [identity_analyze]
    call    print_cstr
.command_done:
    lea     rdi, [j_q]
    call    print_cstr
    add     rsp, 8
    ret

json_print_analysis:
    sub     rsp, 8              ; align nested System V calls
    mov     rbx, [json_analysis_summary]
    lea     rdi, [field_analysis_open]
    call    print_cstr

    lea     rdi, [field_analysis_complete]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_COMPLETE]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_max_depth]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_MAX_DEPTH]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_capacity]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_CANDIDATE_CAPACITY]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_count]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_CANDIDATE_COUNT]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_truncated]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_CANDIDATE_TRUNCATED]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_dropped]
    call    print_cstr
    cmp     qword [rbx + ANALYSIS_SUMMARY_DROPPED_COUNT_KNOWN], 0
    je      .dropped_unknown
    mov     rdi, [rbx + ANALYSIS_SUMMARY_DROPPED_COUNT]
    call    print_u64_dec
    jmp     .dropped_done
.dropped_unknown:
    lea     rdi, [j_null]
    call    print_cstr
.dropped_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_dropped_known]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_DROPPED_COUNT_KNOWN]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_regions_scanned]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_REGIONS_SCANNED]
    call    print_u64_dec
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_analysis_regions_total]
    call    print_cstr
    mov     rdi, [rbx + ANALYSIS_SUMMARY_REGIONS_TOTAL]
    call    print_u64_dec
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    add     rsp, 8
    ret

json_print_target:
    sub     rsp, 8              ; align nested System V calls
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
    add     rsp, 8
    ret

json_print_mitigations:
    sub     rsp, 8              ; align nested System V calls
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

    lea     rdi, [field_canary]
    call    print_cstr
    mov     rax, [rbx + PHDR_SUMMARY_CANARY_STATE]
    cmp     rax, CANARY_STATE_PRESENT
    je      .canary_present
    cmp     rax, CANARY_STATE_ABSENT
    je      .canary_absent
    lea     rdi, [canary_unknown]
    call    print_cstr
    jmp     .canary_done
.canary_present:
    lea     rdi, [canary_present]
    call    print_cstr
    jmp     .canary_done
.canary_absent:
    lea     rdi, [canary_absent]
    call    print_cstr
.canary_done:
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_stripped]
    call    print_cstr
    mov     rax, [rbx + PHDR_SUMMARY_STRIPPED_STATE]
    cmp     rax, STRIPPED_STATE_STRIPPED
    je      .stripped_yes
    cmp     rax, STRIPPED_STATE_NOT_STRIPPED
    je      .stripped_no
    lea     rdi, [stripped_unknown]
    call    print_cstr
    jmp     .stripped_done
.stripped_yes:
    lea     rdi, [stripped_yes]
    call    print_cstr
    jmp     .stripped_done
.stripped_no:
    lea     rdi, [stripped_no]
    call    print_cstr
.stripped_done:
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
    add     rsp, 8
    ret

json_print_counts:
    sub     rsp, 8              ; align nested System V calls
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
    add     rsp, 8
    ret

json_print_coverage:
    sub     rsp, 8              ; align nested System V calls
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

    lea     rdi, [field_cov_reg_transfer]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_REG_TRANSFER_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_memory_write]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_MEMORY_WRITE_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_memory_read]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_MEMORY_READ_COUNT]
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [field_cov_registers]
    call    print_cstr
    mov     rdi, [rbx + GADGET_SUMMARY_REGS_CONTROLLED]
    call    json_print_regs_array
    call    print_nl

    lea     rdi, [field_object_close]
    call    print_cstr
    add     rsp, 8
    ret

json_print_gadget_array:
    sub     rsp, 8              ; align nested System V calls
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

    mov     rax, rbp
    imul    rax, rax, CANDIDATE_EVIDENCE_RECORD_SIZE
    mov     rdx, [json_candidate_evidence]
    add     rdx, rax
    mov     [json_current_evidence], rdx

    mov     rax, rbp
    imul    rax, rax, MEMORY_EFFECT_RECORD_SIZE
    mov     rdx, [json_memory_effects]
    add     rdx, rax
    mov     [json_current_memory], rdx

    mov     rax, rbp
    imul    rax, rax, CANDIDATE_EFFECT_RECORD_SIZE
    mov     rdx, [json_candidate_effects]
    add     rdx, rax
    mov     [json_current_effect], rdx

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
    add     rsp, 8
    ret

json_print_one_gadget:
    sub     rsp, 8              ; align nested System V calls
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

    lea     rdi, [f_section]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_SECTION_NAME_PTR]
    test    rdi, rdi
    jz      .section_null
    lea     rdi, [j_q]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_SECTION_NAME_PTR]
    mov     rsi, [rbx + GADGET_SECTION_NAME_LEN]
    call    json_print_escaped_bytes
    lea     rdi, [j_q]
    call    print_cstr
    jmp     .section_done
.section_null:
    lea     rdi, [j_null]
    call    print_cstr
.section_done:
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

    lea     rdi, [f_stack_pop_order]
    call    print_cstr
    mov     rdi, [json_current_record]
    call    json_print_pattern_reg_order
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_register_transfer]
    call    print_cstr
    mov     rdi, [json_current_record]
    call    json_print_register_transfer
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_memory_access]
    call    print_cstr
    mov     rdi, [json_current_memory]
    call    json_print_memory_effect
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_arch_effects]
    call    print_cstr
    mov     rdi, [json_current_effect]
    call    json_print_candidate_effect
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_clobbers]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_REGS_CLOBBERED]
    call    json_print_regs_array
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_side_effects]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     rdi, [rbx + GADGET_SIDE_EFFECT_FLAGS]
    call    json_print_side_effects_array
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_stack_delta]
    call    print_cstr
    mov     rbx, [json_current_record]
    mov     eax, [rbx + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_UNKNOWN
    je      .stack_unknown
    cmp     eax, PATTERN_POP_RSP_RET
    je      .stack_unknown
    cmp     eax, PATTERN_LEAVE_RET
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
    mov     eax, [rbx + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_UNKNOWN
    je      .known_false
    cmp     eax, PATTERN_POP_RSP_RET
    je      .known_false
    cmp     eax, PATTERN_LEAVE_RET
    je      .known_false
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .known_done
.known_false:
    lea     rdi, [j_false]
    call    print_cstr
.known_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_open]
    call    print_cstr
    call    json_print_candidate_evidence
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
    add     rsp, 8
    ret

json_print_candidate_evidence:
    sub     rsp, 8              ; align nested System V calls
    mov     rbx, [json_current_evidence]

    lea     rdi, [f_evidence_kind]
    call    print_cstr
    mov     rax, [rbx + CANDIDATE_EVIDENCE_FLAGS]
    test    rax, EVIDENCE_FLAG_DECODER_VALIDATED
    jz      .kind_not_decoded
    cmp     qword [rbx + CANDIDATE_EVIDENCE_SEMANTIC_SOURCE], EVIDENCE_SEMANTIC_SOURCE_DECODED
    jne     .kind_decoded
    lea     rdi, [evidence_kind_sem_dec_s]
    jmp     .kind_print
.kind_decoded:
    lea     rdi, [evidence_kind_decoded_s]
    jmp     .kind_print
.kind_not_decoded:
    test    rax, EVIDENCE_FLAG_SEMANTIC_EXACT
    jz      .kind_not_sem_exact
    lea     rdi, [evidence_kind_sem_exact_s]
    jmp     .kind_print
.kind_not_sem_exact:
    test    rax, EVIDENCE_FLAG_EXACT_SUFFIX
    jz      .kind_raw
    lea     rdi, [evidence_kind_exact_s]
    jmp     .kind_print
.kind_raw:
    lea     rdi, [evidence_kind_raw_s]
.kind_print:
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_raw]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rdi, [rbx + CANDIDATE_EVIDENCE_FLAGS]
    and     rdi, EVIDENCE_FLAG_RAW_CANDIDATE
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_exact]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rdi, [rbx + CANDIDATE_EVIDENCE_FLAGS]
    and     rdi, EVIDENCE_FLAG_EXACT_SUFFIX
    call    json_print_bool_nonzero
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_sem_source]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rax, [rbx + CANDIDATE_EVIDENCE_SEMANTIC_SOURCE]
    cmp     rax, EVIDENCE_SEMANTIC_SOURCE_EXACT
    je      .sem_source_exact
    cmp     rax, EVIDENCE_SEMANTIC_SOURCE_DECODED
    je      .sem_source_decoded
    lea     rdi, [j_null]
    call    print_cstr
    jmp     .sem_source_done
.sem_source_exact:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [evidence_source_exact_s]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    jmp     .sem_source_done
.sem_source_decoded:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [evidence_source_decoded_s]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
.sem_source_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_validator]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rax, [rbx + CANDIDATE_EVIDENCE_VALIDATOR_ID]
    cmp     rax, EVIDENCE_VALIDATOR_RAW_SCANNER
    je      .validator_raw
    cmp     rax, EVIDENCE_VALIDATOR_EXACT_SUFFIX
    je      .validator_exact
    cmp     rax, EVIDENCE_VALIDATOR_DECODER
    je      .validator_decoder
    lea     rdi, [evidence_validator_unknown_s]
    jmp     .validator_print
.validator_raw:
    lea     rdi, [evidence_validator_raw_s]
    jmp     .validator_print
.validator_exact:
    lea     rdi, [evidence_validator_exact_s]
    jmp     .validator_print
.validator_decoder:
    lea     rdi, [evidence_validator_decoder_s]
.validator_print:
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_suffix_off]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rax, [rbx + CANDIDATE_EVIDENCE_FLAGS]
    test    rax, EVIDENCE_FLAG_EXACT_SUFFIX
    jz      .suffix_off_null
    mov     rdi, [rbx + CANDIDATE_EVIDENCE_SUFFIX_OFFSET]
    call    print_u64_dec
    jmp     .suffix_off_done
.suffix_off_null:
    lea     rdi, [j_null]
    call    print_cstr
.suffix_off_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_suffix_len]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rax, [rbx + CANDIDATE_EVIDENCE_FLAGS]
    test    rax, EVIDENCE_FLAG_EXACT_SUFFIX
    jz      .suffix_len_null
    mov     rdi, [rbx + CANDIDATE_EVIDENCE_SUFFIX_LENGTH]
    call    print_u64_dec
    jmp     .suffix_len_done
.suffix_len_null:
    lea     rdi, [j_null]
    call    print_cstr
.suffix_len_done:
    JSON_FIELD_COMMA_NL

    lea     rdi, [f_evidence_full_valid]
    call    print_cstr
    mov     rbx, [json_current_evidence]
    mov     rax, [rbx + CANDIDATE_EVIDENCE_FULL_SEQUENCE_STATE]
    cmp     rax, EVIDENCE_FULL_SEQUENCE_VALID
    je      .full_valid_true
    cmp     rax, EVIDENCE_FULL_SEQUENCE_INVALID
    je      .full_valid_false
    lea     rdi, [j_null]
    call    print_cstr
    jmp     .full_valid_done
.full_valid_true:
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .full_valid_done
.full_valid_false:
    lea     rdi, [j_false]
    call    print_cstr
.full_valid_done:
    call    print_nl

    lea     rdi, [f_evidence_close]
    call    print_cstr
    add     rsp, 8
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
    movzx   rdi, al
    call    json_print_escaped_byte
    inc     rbx
    jmp     .loop
.done:
    pop     rbx
    ret

; json_print_escaped_bytes(ptr=rdi, len=rsi)
;
; Render a bounded byte string as a JSON string payload. This is used for
; section-header names because section metadata is byte-oriented and already
; arrives with a parser-proven length. Bytes outside the conservative printable
; ASCII range are emitted as \u00NN escapes so hostile section names cannot
; produce invalid UTF-8 JSON.
json_print_escaped_bytes:
    push    rbx
    push    r12
    push    r13

    mov     rbx, rdi
    mov     r12, rsi
    xor     r13, r13
.loop:
    cmp     r13, r12
    jae     .done
    movzx   rdi, byte [rbx + r13]
    call    json_print_escaped_byte
    inc     r13
    jmp     .loop
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; json_print_escaped_byte(byte=rdi)
;
; JSON string payload byte printer. It preserves common short escapes for
; readability and uses \u00NN for every other byte that is not safe printable
; ASCII. This prevents control bytes from degrading to '?' and prevents high-bit
; bytes from becoming invalid UTF-8 in JSON output.
json_print_escaped_byte:
    mov     eax, edi
    and     eax, 0xff
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
    jb      .escape_u00
    cmp     al, 0x7e
    ja      .escape_u00
    mov     [json_char_buf], al
    mov     byte [json_char_buf + 1], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_quote:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 0x22
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_backslash:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 0x5c
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_newline:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 'n'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_cr:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 'r'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_tab:
    mov     byte [json_char_buf], 0x5c
    mov     byte [json_char_buf + 1], 't'
    mov     byte [json_char_buf + 2], 0
    lea     rdi, [json_char_buf]
    jmp     print_cstr
.escape_u00:
    push    rbx
    mov     ebx, eax
    lea     rdi, [j_u00_prefix]
    call    print_cstr
    movzx   rdi, bl
    call    print_hex8
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
    sub     rsp, 8              ; align nested System V calls

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
    add     rsp, 8
    pop     r12
    pop     rbx
    ret

json_print_reg_id:
    cmp     edi, REG_RAX_BIT
    je      .reg_id_rax
    cmp     edi, REG_RBX_BIT
    je      .reg_id_rbx
    cmp     edi, REG_RCX_BIT
    je      .reg_id_rcx
    cmp     edi, REG_RDX_BIT
    je      .reg_id_rdx
    cmp     edi, REG_RSI_BIT
    je      .reg_id_rsi
    cmp     edi, REG_RDI_BIT
    je      .reg_id_rdi
    cmp     edi, REG_RBP_BIT
    je      .reg_id_rbp
    cmp     edi, REG_RSP_BIT
    je      .reg_id_rsp
    cmp     edi, REG_R8_BIT
    je      .reg_id_r8
    cmp     edi, REG_R9_BIT
    je      .reg_id_r9
    cmp     edi, REG_R10_BIT
    je      .reg_id_r10
    cmp     edi, REG_R11_BIT
    je      .reg_id_r11
    cmp     edi, REG_R12_BIT
    je      .reg_id_r12
    cmp     edi, REG_R13_BIT
    je      .reg_id_r13
    cmp     edi, REG_R14_BIT
    je      .reg_id_r14
    cmp     edi, REG_R15_BIT
    je      .reg_id_r15
    lea     rdi, [identity_unknown]
    jmp     print_cstr
.reg_id_rax: lea rdi, [reg_rax_s]
    jmp print_cstr
.reg_id_rbx: lea rdi, [reg_rbx_s]
    jmp print_cstr
.reg_id_rcx: lea rdi, [reg_rcx_s]
    jmp print_cstr
.reg_id_rdx: lea rdi, [reg_rdx_s]
    jmp print_cstr
.reg_id_rsi: lea rdi, [reg_rsi_s]
    jmp print_cstr
.reg_id_rdi: lea rdi, [reg_rdi_s]
    jmp print_cstr
.reg_id_rbp: lea rdi, [reg_rbp_s]
    jmp print_cstr
.reg_id_rsp: lea rdi, [reg_rsp_s]
    jmp print_cstr
.reg_id_r8: lea rdi, [reg_r8_s]
    jmp print_cstr
.reg_id_r9: lea rdi, [reg_r9_s]
    jmp print_cstr
.reg_id_r10: lea rdi, [reg_r10_s]
    jmp print_cstr
.reg_id_r11: lea rdi, [reg_r11_s]
    jmp print_cstr
.reg_id_r12: lea rdi, [reg_r12_s]
    jmp print_cstr
.reg_id_r13: lea rdi, [reg_r13_s]
    jmp print_cstr
.reg_id_r14: lea rdi, [reg_r14_s]
    jmp print_cstr
.reg_id_r15: lea rdi, [reg_r15_s]
    jmp print_cstr

; json_print_pattern_reg_order(rdi=gadget_record)
json_print_pattern_reg_order:
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 8

    mov     r12, rdi
    xor     r14d, r14d
    xor     r15d, r15d
    lea     rdi, [j_array_open]
    call    print_cstr
    mov     eax, [r12 + GADGET_PATTERN_ID]
    cmp     eax, PATTERN_MULTI_POP_RET
    je      .pattern_order_load
    cmp     eax, PATTERN_POP_RAX_RET
    jb      .pattern_order_close
    cmp     eax, PATTERN_POP_R15_RET
    ja      .pattern_order_close
.pattern_order_load:
    mov     r13d, [r12 + GADGET_PATTERN_REG_ORDER]
    mov     r12d, [r12 + GADGET_PATTERN_REG_COUNT]
    test    r12d, r12d
    jz      .pattern_order_close
    cmp     r12d, PATTERN_REG_ORDER_MAX
    ja      .pattern_order_close
.pattern_order_loop:
    test    r15d, r15d
    jz      .pattern_order_no_comma
    lea     rdi, [j_comma]
    call    print_cstr
.pattern_order_no_comma:
    lea     rdi, [j_q]
    call    print_cstr
    mov     eax, r13d
    mov     ecx, r14d
    shl     ecx, 2
    shr     eax, cl
    and     eax, 0x0f
    mov     edi, eax
    call    json_print_reg_id
    lea     rdi, [j_q]
    call    print_cstr
    mov     r15d, 1
    inc     r14d
    cmp     r14d, r12d
    jb      .pattern_order_loop
.pattern_order_close:
    lea     rdi, [j_array_close]
    call    print_cstr
    add     rsp, 8
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    ret

; json_print_register_transfer(rdi=gadget_record)
; Emits null for non-transfer candidates or a source/destination object for the
; exact register-direct transfer family.
json_print_register_transfer:
    push    r12
    mov     r12, rdi
    cmp     dword [r12 + GADGET_PATTERN_ID], PATTERN_MOV_REG_REG_RET
    jne     .register_transfer_null
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 2
    jne     .register_transfer_null
    lea     rdi, [j_object_open]
    call    print_cstr
    lea     rdi, [f_transfer_source]
    call    print_cstr
    mov     edi, [r12 + GADGET_PATTERN_REG_ORDER]
    shr     edi, 4
    and     edi, 0x0f
    call    json_print_reg_id
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [f_transfer_destination]
    call    print_cstr
    mov     edi, [r12 + GADGET_PATTERN_REG_ORDER]
    and     edi, 0x0f
    call    json_print_reg_id
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [j_object_close]
    call    print_cstr
    jmp     .register_transfer_done
.register_transfer_null:
    lea     rdi, [j_null]
    call    print_cstr
.register_transfer_done:
    pop     r12
    ret

; json_print_memory_effect(rdi=memory_effect_record)
; Emits null or a structured memory-access object from the dense side-car.
json_print_memory_effect:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     rbx, [r12 + MEMORY_EFFECT_DESCRIPTOR]
    test    rbx, MEMORY_EFFECT_FLAG_PRESENT
    jz      .memory_null
    lea     rdi, [j_object_open]
    call    print_cstr
    lea     rdi, [f_memory_direction]
    call    print_cstr
    test    rbx, MEMORY_EFFECT_FLAG_READ
    jz      .memory_direction_write
    lea     rdi, [memory_direction_read_s]
    call    print_cstr
    jmp     .memory_direction_done
.memory_direction_write:
    lea     rdi, [memory_direction_write_s]
    call    print_cstr
.memory_direction_done:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [f_memory_base]
    call    print_cstr
    mov     r13, rbx
    shr     r13, MEMORY_EFFECT_BASE_SHIFT
    and     r13d, MEMORY_EFFECT_REG_MASK
    mov     edi, r13d
    call    json_print_reg_id
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [f_memory_index]
    call    print_cstr
    lea     rdi, [j_null]
    call    print_cstr
    lea     rdi, [f_memory_scale]
    call    print_cstr
    mov     rdi, 1
    call    print_u64_dec
    lea     rdi, [f_memory_displacement]
    call    print_cstr
    mov     rdi, [r12 + MEMORY_EFFECT_DISPLACEMENT]
    call    print_u64_dec
    lea     rdi, [f_memory_displacement_known]
    call    print_cstr
    lea     rdi, [j_true]
    call    print_cstr
    lea     rdi, [f_memory_width]
    call    print_cstr
    mov     rdi, rbx
    shr     rdi, MEMORY_EFFECT_WIDTH_SHIFT
    and     edi, MEMORY_EFFECT_WIDTH_MASK
    call    print_u64_dec
    lea     rdi, [f_memory_value]
    call    print_cstr
    mov     r13, rbx
    shr     r13, MEMORY_EFFECT_VALUE_SHIFT
    and     r13d, MEMORY_EFFECT_REG_MASK
    mov     edi, r13d
    call    json_print_reg_id
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [f_memory_dereference]
    call    print_cstr
    lea     rdi, [j_true]
    call    print_cstr
    lea     rdi, [j_object_close]
    call    print_cstr
    jmp     .memory_done
.memory_null:
    lea     rdi, [j_null]
    call    print_cstr
.memory_done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; json_print_candidate_effect(rdi=candidate_effect_record)
; Emits null for raw-only candidates or a compact architectural-effect object
; for every recognized exact suffix.
json_print_candidate_effect:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     rbx, [r12 + CANDIDATE_EFFECT_DESCRIPTOR]
    test    rbx, CANDIDATE_EFFECT_FLAG_PRESENT
    jz      .arch_effect_null

    lea     rdi, [j_object_open]
    call    print_cstr

    lea     rdi, [f_arch_regs_read]
    call    print_cstr
    mov     rdi, [r12 + CANDIDATE_EFFECT_REGS_READ]
    call    json_print_regs_array

    lea     rdi, [f_arch_regs_written]
    call    print_cstr
    mov     rdi, [r12 + CANDIDATE_EFFECT_REGS_WRITTEN]
    call    json_print_regs_array

    lea     rdi, [f_arch_flags_read]
    call    print_cstr
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_FLAGS_READ_SHIFT
    and     edi, CANDIDATE_EFFECT_FLAGS_MASK
    call    json_print_arch_flags_array

    lea     rdi, [f_arch_flags_written]
    call    print_cstr
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_FLAGS_WRITE_SHIFT
    and     edi, CANDIDATE_EFFECT_FLAGS_MASK
    call    json_print_arch_flags_array

    lea     rdi, [f_arch_control]
    call    print_cstr
    mov     rdi, rbx
    call    json_print_arch_control_array

    lea     rdi, [f_arch_stack_base]
    call    print_cstr
    mov     rax, rbx
    shr     rax, CANDIDATE_EFFECT_STACK_BASE_SHIFT
    and     eax, CANDIDATE_EFFECT_STACK_BASE_MASK
    cmp     eax, CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP
    je      .arch_stack_rsp
    cmp     eax, CANDIDATE_EFFECT_STACK_BASE_ENTRY_RBP
    je      .arch_stack_rbp
    cmp     eax, CANDIDATE_EFFECT_STACK_BASE_DYNAMIC
    je      .arch_stack_dynamic
    lea     rdi, [j_null]
    call    print_cstr
    jmp     .arch_stack_base_done
.arch_stack_rsp:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [arch_stack_rsp_s]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    jmp     .arch_stack_base_done
.arch_stack_rbp:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [arch_stack_rbp_s]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
    jmp     .arch_stack_base_done
.arch_stack_dynamic:
    lea     rdi, [j_q]
    call    print_cstr
    lea     rdi, [arch_stack_dynamic_s]
    call    print_cstr
    lea     rdi, [j_q]
    call    print_cstr
.arch_stack_base_done:

    lea     rdi, [f_arch_stack_reads]
    call    print_cstr
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT
    and     edi, CANDIDATE_EFFECT_STACK_READ_COUNT_MASK
    call    print_u64_dec

    lea     rdi, [f_arch_stack_writes]
    call    print_cstr
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_STACK_WRITE_COUNT_SHIFT
    and     edi, CANDIDATE_EFFECT_STACK_WRITE_COUNT_MASK
    call    print_u64_dec

    lea     rdi, [f_arch_first_read]
    call    print_cstr
    test    rbx, CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN
    jz      .arch_first_null
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_FIRST_READ_SHIFT
    and     edi, CANDIDATE_EFFECT_FIRST_READ_MASK
    call    print_u64_dec
    jmp     .arch_first_done
.arch_first_null:
    lea     rdi, [j_null]
    call    print_cstr
.arch_first_done:

    lea     rdi, [f_arch_stride]
    call    print_cstr
    test    rbx, CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN
    jz      .arch_stride_null
    mov     rdi, rbx
    shr     rdi, CANDIDATE_EFFECT_READ_STRIDE_SHIFT
    and     edi, CANDIDATE_EFFECT_READ_STRIDE_MASK
    call    print_u64_dec
    jmp     .arch_stride_done
.arch_stride_null:
    lea     rdi, [j_null]
    call    print_cstr
.arch_stride_done:

    lea     rdi, [f_arch_offsets_known]
    call    print_cstr
    test    rbx, CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN
    jz      .arch_offsets_false
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .arch_offsets_done
.arch_offsets_false:
    lea     rdi, [j_false]
    call    print_cstr
.arch_offsets_done:

    lea     rdi, [f_arch_complete]
    call    print_cstr
    test    rbx, CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE
    jz      .arch_complete_false
    lea     rdi, [j_true]
    call    print_cstr
    jmp     .arch_complete_done
.arch_complete_false:
    lea     rdi, [j_false]
    call    print_cstr
.arch_complete_done:
    lea     rdi, [j_object_close]
    call    print_cstr
    jmp     .arch_effect_done

.arch_effect_null:
    lea     rdi, [j_null]
    call    print_cstr
.arch_effect_done:
    pop     r13
    pop     r12
    pop     rbx
    ret

%macro JSON_ARCH_ITEM_IF_SET 2
    test    rbx, %1
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

json_print_arch_flags_array:
    push    rbx
    push    r12
    sub     rsp, 8
    mov     rbx, rdi
    xor     r12d, r12d
    lea     rdi, [j_array_open]
    call    print_cstr
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_CF, arch_flag_cf_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_PF, arch_flag_pf_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_AF, arch_flag_af_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_ZF, arch_flag_zf_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_SF, arch_flag_sf_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_TF, arch_flag_tf_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_IF, arch_flag_if_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_DF, arch_flag_df_s
    JSON_ARCH_ITEM_IF_SET ARCH_FLAG_OF, arch_flag_of_s
    lea     rdi, [j_array_close]
    call    print_cstr
    add     rsp, 8
    pop     r12
    pop     rbx
    ret

json_print_arch_control_array:
    push    rbx
    push    r12
    sub     rsp, 8
    mov     rbx, rdi
    xor     r12d, r12d
    lea     rdi, [j_array_open]
    call    print_cstr
    JSON_ARCH_ITEM_IF_SET CANDIDATE_EFFECT_CONTROL_RETURN, arch_control_return_s
    JSON_ARCH_ITEM_IF_SET CANDIDATE_EFFECT_CONTROL_SYSCALL, arch_control_syscall_s
    lea     rdi, [j_array_close]
    call    print_cstr
    add     rsp, 8
    pop     r12
    pop     rbx
    ret

; json_print_side_effects_array(rdi=side-effect bitmap)
json_print_side_effects_array:
    push    rbx
    push    r12
    sub     rsp, 8
    mov     rbx, rdi
    xor     r12, r12
    lea     rdi, [j_array_open]
    call    print_cstr
    JSON_EFFECT_IF_SET SIDE_EFFECT_STACK_READ, side_effect_stack_read_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_STACK_PIVOT, side_effect_stack_pivot_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_SYSCALL, side_effect_syscall_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_RET_IMM16, side_effect_ret_imm16_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_REGISTER_WRITE, side_effect_register_write_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_STACK_ADJUST, side_effect_stack_adjust_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_FLAGS_WRITE, side_effect_flags_write_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_MEMORY_READ, side_effect_memory_read_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_MEMORY_WRITE, side_effect_memory_write_s
    JSON_EFFECT_IF_SET SIDE_EFFECT_CONTROL_TRANSFER, side_effect_control_transfer_s
    lea     rdi, [j_array_close]
    call    print_cstr
    add     rsp, 8
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
    cmp     edi, PATTERN_MULTI_POP_RET
    je      .multi_pop
    cmp     edi, PATTERN_MOV_REG_REG_RET
    je      .mov_reg_reg
    cmp     edi, PATTERN_ADD_RSP_IMM8_RET
    je      .add_rsp_imm8
    cmp     edi, PATTERN_MOV_MEM_REG_RET
    je      .mov_mem_reg
    cmp     edi, PATTERN_MOV_REG_MEM_RET
    je      .mov_reg_mem
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
.multi_pop: lea rdi, [pattern_multi_pop_s]
           jmp print_cstr
.mov_reg_reg: lea rdi, [pattern_mov_reg_reg_s]
           jmp print_cstr
.add_rsp_imm8: lea rdi, [pattern_add_rsp_imm8_s]
           jmp print_cstr
.mov_mem_reg: lea rdi, [pattern_mov_mem_reg_s]
           jmp print_cstr
.mov_reg_mem: lea rdi, [pattern_mov_reg_mem_s]
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
