; analyze.asm
;
; Purpose:
;   Command-level orchestration for `x64lens analyze <file>`.
;
; Module scope:
;   Produce the first integrated checkpoint report by running the current
;   validated pipeline once: file mapping, ELF64 validation, program-header
;   mitigation analysis, executable-region discovery, raw gadget candidate
;   scanning, exact pattern matching, semantic classification, candidate
;   evidence and memory-effect materialization, scoring, and text or JSON
;   reporting.
;
; Current scope:
;   `analyze` intentionally reuses the same internal records as `info`,
;   `mitigations`, and `gadgets`. JSON output uses the same schema 0.2.0
;   adapter as `gadgets --format json`, with distinct command identity and the
;   same target, mitigation, candidate, primitive, score, completeness, and
;   limitation facts.
;
; Non-goal:
;   This command does not claim exploitability. It reports static facts that
;   help defenders prioritize binaries for deeper review.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_file_map
extern x64lens_file_unmap
extern x64lens_elf64_validate
extern x64lens_phdr_analyze
extern x64lens_shdr_classify_stripped
extern x64lens_shdr_annotate_exec_regions
extern x64lens_shdr_annotate_gadgets
extern x64lens_scanner_find_ret_candidates
extern x64lens_patterns_match_exact
extern x64lens_classifier_apply_exact
extern x64lens_candidate_evidence_from_exact
extern x64lens_memory_effect_from_exact
extern x64lens_candidate_effect_from_exact
extern x64lens_scoring_apply
extern x64lens_analysis_summary_mark_complete
extern x64lens_report_text_elf64_info
extern x64lens_report_text_mitigations_body
extern x64lens_report_text_gadgets_body
extern x64lens_report_json_gadgets
extern x64lens_error_print_status
extern x64lens_arena_init
extern x64lens_arena_alloc
extern x64lens_arena_destroy

section .bss
ana_mapped_file:     resb FILEMAP_RECORD_SIZE
ana_phdr_summary:    resb PHDR_SUMMARY_RECORD_SIZE
ana_regions:         resb EXEC_REGION_RECORD_SIZE * EXEC_REGION_MAX
ana_gadget_summary:  resb GADGET_SUMMARY_RECORD_SIZE
ana_analysis_summary: resb ANALYSIS_SUMMARY_RECORD_SIZE
ana_candidate_arena: resb ARENA_RECORD_SIZE

section .text
global x64lens_command_analyze
global x64lens_command_analyze_json

; Public wrappers select output format while sharing the integrated pipeline.
x64lens_command_analyze:
    xor     edx, edx            ; 0 = text
    jmp     x64lens_command_analyze_with_format

x64lens_command_analyze_json:
    mov     edx, 1              ; 1 = JSON
    jmp     x64lens_command_analyze_with_format

; x64lens_command_analyze_with_format(path_cstr=rdi, max_depth=rsi, format=rdx) -> rax=status
;
; Inputs:
;   RDI = target path C string from argv
;   RSI = bounded maximum backward byte depth from each terminator
;   RDX = output format, 0 for text or 1 for JSON
;
; Output:
;   RAX = stable x64lens exit code
x64lens_command_analyze_with_format:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 24             ; local effect pointer plus call alignment

    mov     r12, rdi            ; preserve target path for reporting
    mov     r14, rsi            ; max depth from CLI or default
    mov     ebx, edx            ; output format: 0=text, 1=json
    xor     r15, r15            ; arena-backed gadget_record[] pointer
    xor     r13, r13            ; candidate_evidence_record[] pointer
    xor     rbp, rbp            ; memory_effect_record[] pointer
    mov     qword [rsp], 0       ; candidate_effect_record[] pointer

    ; Map target file read-only. The analyzer treats target bytes as data and
    ; never executes them.
    mov     rdi, r12
    lea     rsi, [ana_mapped_file]
    call    x64lens_file_map
    test    rax, rax
    jne     .error

    ; Validate ELF64 x86_64 identity before reading ELF fields.
    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    call    x64lens_elf64_validate
    test    rax, rax
    jne     .error

    ; Program-header facts drive both mitigation reporting and scanner region
    ; selection. Section headers remain non-authoritative for executable range
    ; selection.
    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    lea     rdx, [ana_phdr_summary]
    lea     rcx, [ana_regions]
    mov     r8, EXEC_REGION_MAX
    call    x64lens_phdr_analyze
    test    rax, rax
    jne     .error

    ; Section-derived metadata is an analyst indicator only. It must never
    ; change executable-region boundaries selected from PT_LOAD + PF_X.
    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    lea     rdx, [ana_phdr_summary]
    call    x64lens_shdr_classify_stripped
    test    rax, rax
    jne     .error

    ; Add optional section labels to executable-region records. Section
    ; labels are metadata annotations, not loader authority.
    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    lea     rdx, [ana_regions]
    mov     rcx, [ana_phdr_summary + PHDR_SUMMARY_EXEC_COUNT]
    call    x64lens_shdr_annotate_exec_regions
    test    rax, rax
    jne     .error

    ; Allocate bounded candidate storage from the same arena-backed record
    ; model used by the gadgets command.
    lea     rdi, [ana_candidate_arena]
    mov     rsi, ANALYSIS_RECORD_ARENA_BYTES
    call    x64lens_arena_init
    test    rax, rax
    jne     .error

    lea     rdi, [ana_candidate_arena]
    mov     rsi, GADGET_RECORD_ARENA_BYTES
    mov     rdx, GADGET_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     r15, rax

    lea     rdi, [ana_candidate_arena]
    mov     rsi, CANDIDATE_EVIDENCE_ARENA_BYTES
    mov     rdx, CANDIDATE_EVIDENCE_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     r13, rax

    lea     rdi, [ana_candidate_arena]
    mov     rsi, MEMORY_EFFECT_ARENA_BYTES
    mov     rdx, MEMORY_EFFECT_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     rbp, rax

    lea     rdi, [ana_candidate_arena]
    mov     rsi, CANDIDATE_EFFECT_ARENA_BYTES
    mov     rdx, CANDIDATE_EFFECT_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     [rsp], rax            ; dense candidate_effect_record[] side-car

    mov     [ana_gadget_summary + GADGET_SUMMARY_MAX_DEPTH], r14
    mov     qword [ana_gadget_summary + GADGET_SUMMARY_CAPACITY], GADGET_RECORD_MAX

    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    lea     rdx, [ana_phdr_summary]
    lea     rcx, [ana_regions]
    lea     r8, [ana_gadget_summary]
    mov     r9, r15
    call    x64lens_scanner_find_ret_candidates
    test    rax, rax
    jne     .error

    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    lea     rsi, [ana_gadget_summary]
    mov     rdx, r15
    call    x64lens_patterns_match_exact
    test    rax, rax
    jne     .error

    lea     rdi, [ana_gadget_summary]
    mov     rsi, r15
    mov     rdx, [ana_mapped_file + FILEMAP_ADDR]
    call    x64lens_classifier_apply_exact
    test    rax, rax
    jne     .error

    ; Materialize the same candidate-index provenance side-car used by gadgets.
    ; The integrated command must not create a second evidence interpretation.
    lea     rdi, [ana_gadget_summary]
    mov     rsi, r15
    mov     rdx, r13
    call    x64lens_candidate_evidence_from_exact
    test    rax, rax
    jne     .error

    lea     rdi, [ana_gadget_summary]
    mov     rsi, r15
    mov     rdx, rbp
    call    x64lens_memory_effect_from_exact
    test    rax, rax
    jne     .error

    ; Materialize architectural register, represented flag, stack-source, and
    ; control-flow effects before scoring. The scorer consumes these validated
    ; facts and never reconstructs instruction semantics from pattern names.
    lea     rdi, [ana_gadget_summary]
    mov     rsi, r15
    mov     rdx, rbp
    mov     rcx, [rsp]
    call    x64lens_candidate_effect_from_exact
    test    rax, rax
    jne     .error

    lea     rdi, [ana_gadget_summary]
    mov     rsi, r15
    mov     rdx, [rsp]
    call    x64lens_scoring_apply
    test    rax, rax
    jne     .error

    ; Add optional section labels to candidate records after scoring.
    mov     rdi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rsi, [ana_mapped_file + FILEMAP_SIZE]
    mov     rdx, r15
    mov     rcx, [ana_gadget_summary + GADGET_SUMMARY_COUNT]
    call    x64lens_shdr_annotate_gadgets
    test    rax, rax
    jne     .error

    ; Construct report identity and completeness only after every shared
    ; analysis stage has succeeded. The integrated command receives its own
    ; command identity while preserving the same underlying analysis facts.
    lea     rdi, [ana_analysis_summary]
    mov     rsi, REPORT_COMMAND_ANALYZE
    mov     rdx, r14
    lea     rcx, [ana_phdr_summary]
    lea     r8, [ana_gadget_summary]
    call    x64lens_analysis_summary_mark_complete
    test    rax, rax
    jne     .error

    cmp     ebx, 1
    je      .emit_json

.emit_text:
    ; Emit one complete top-level header through the information reporter,
    ; then reuse body-only mitigation and gadget sections. The integrated path
    ; does not duplicate formatting or analysis logic.
    mov     rdi, r12
    mov     rsi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rdx, [ana_mapped_file + FILEMAP_SIZE]
    call    x64lens_report_text_elf64_info

    mov     rdi, r12
    mov     rsi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rdx, [ana_mapped_file + FILEMAP_SIZE]
    lea     rcx, [ana_phdr_summary]
    lea     r8, [ana_regions]
    call    x64lens_report_text_mitigations_body

    mov     rdi, r12
    lea     rsi, [ana_gadget_summary]
    mov     rdx, r15
    mov     rcx, [ana_mapped_file + FILEMAP_ADDR]
    lea     r8, [ana_analysis_summary]
    mov     r9, rbp
    mov     rax, [rsp]
    sub     rsp, 16
    mov     [rsp], rax
    call    x64lens_report_text_gadgets_body
    add     rsp, 16
    jmp     .emit_done

.emit_json:
    mov     rdi, r12
    mov     rsi, [ana_mapped_file + FILEMAP_ADDR]
    mov     rdx, [ana_mapped_file + FILEMAP_SIZE]
    lea     rcx, [ana_phdr_summary]
    lea     r8, [ana_gadget_summary]
    mov     r9, r15
    ; System V passes arguments seven through ten on the stack. Reserve a
    ; fourth slot so the call site remains 16-byte aligned.
    mov     r10, [rsp]
    sub     rsp, 32
    lea     rax, [ana_analysis_summary]
    mov     [rsp], rax
    mov     [rsp + 8], r13
    mov     [rsp + 16], rbp
    mov     [rsp + 24], r10
    call    x64lens_report_json_gadgets
    add     rsp, 32

.emit_done:
    lea     rdi, [ana_candidate_arena]
    call    x64lens_arena_destroy
    lea     rdi, [ana_mapped_file]
    call    x64lens_file_unmap
    xor     rax, rax
    jmp     .done

.arena_alloc_failed:
    mov     rax, EXIT_BOUNDS

.error:
    mov     r13, rax
    lea     rdi, [ana_candidate_arena]
    call    x64lens_arena_destroy
    lea     rdi, [ana_mapped_file]
    call    x64lens_file_unmap
    mov     rdi, r13
    call    x64lens_error_print_status
    mov     rax, r13

.done:
    add     rsp, 24
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
