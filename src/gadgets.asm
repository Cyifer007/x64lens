; gadgets.asm
;
; Purpose:
;   Command-level orchestration for `x64lens gadgets <file>`.
;
; Module scope:
;   Map a target file, validate ELF64 identity, reuse the Sprint 2 program-
;   header analyzer to discover executable PT_LOAD regions, run the Sprint 3
;   raw gadget scanner, run exact byte-template pattern matching, classify and
;   score supported candidates, and emit bounded records as text or JSON.
;
; Current scope:
;   This command discovers raw `ret` and `ret imm16` candidates, tags
;   recognized exact byte-template patterns, maps supported patterns into
;   semantic classes, applies conservative first-pass scoring, constructs
;   command identity and bounded completeness facts, and emits text or
;   schema-versioned JSON. It does not generate chains or claim exploitability.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

extern x64lens_file_map
extern x64lens_file_unmap
extern x64lens_elf64_validate
extern x64lens_phdr_analyze
extern x64lens_shdr_classify_stripped
extern x64lens_shdr_annotate_gadgets
extern x64lens_scanner_find_ret_candidates
extern x64lens_patterns_match_exact
extern x64lens_classifier_apply_exact
extern x64lens_candidate_evidence_from_exact
extern x64lens_scoring_apply
extern x64lens_analysis_summary_mark_complete
extern x64lens_report_text_gadgets
extern x64lens_report_json_gadgets
extern x64lens_error_print_status
extern x64lens_arena_init
extern x64lens_arena_alloc
extern x64lens_arena_destroy

section .bss
gad_mapped_file:     resb FILEMAP_RECORD_SIZE
gad_phdr_summary:    resb PHDR_SUMMARY_RECORD_SIZE
gad_regions:         resb EXEC_REGION_RECORD_SIZE * EXEC_REGION_MAX
gad_summary:         resb GADGET_SUMMARY_RECORD_SIZE
gad_analysis_summary: resb ANALYSIS_SUMMARY_RECORD_SIZE
gad_candidate_arena: resb ARENA_RECORD_SIZE

section .text
global x64lens_command_gadgets
global x64lens_command_gadgets_json

; Public wrappers select output format while sharing the same analysis pipeline.
x64lens_command_gadgets:
    xor     edx, edx            ; 0 = text
    jmp     x64lens_command_gadgets_with_format

x64lens_command_gadgets_json:
    mov     edx, 1              ; 1 = JSON
    jmp     x64lens_command_gadgets_with_format

; x64lens_command_gadgets_with_format(path_cstr=rdi, max_depth=rsi, format=rdx) -> rax=status
;
; Inputs:
;   RDI = target path C string from argv
;   RSI = bounded maximum backward byte depth from each terminator
;
; Output:
;   RAX = stable x64lens exit code
;
; Cleanup:
;   The mapped file is always unmapped on the success and error paths once the
;   mapping has been attempted. Error reporting remains centralized through
;   x64lens_error_print_status.
x64lens_command_gadgets_with_format:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     r12, rdi            ; preserve target path for reporting
    mov     r14, rsi            ; max depth from CLI or default
    mov     ebx, edx            ; output format: 0=text, 1=json
    xor     r15, r15            ; arena-backed gadget_record[] pointer
    xor     r13, r13            ; parallel candidate_evidence_record[] pointer

    ; Map target file read-only. The scanner treats the mapped bytes as data,
    ; never as executable code.
    mov     rdi, r12
    lea     rsi, [gad_mapped_file]
    call    x64lens_file_map
    test    rax, rax
    jne     .error

    ; Validate ELF64 x86_64 identity before reading ELF fields.
    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rsi, [gad_mapped_file + FILEMAP_SIZE]
    call    x64lens_elf64_validate
    test    rax, rax
    jne     .error

    ; Reuse the Sprint 2 loader-facing program-header model. This ensures the
    ; scanner reads only executable PT_LOAD + PF_X file ranges.
    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rsi, [gad_mapped_file + FILEMAP_SIZE]
    lea     rdx, [gad_phdr_summary]
    lea     rcx, [gad_regions]
    mov     r8, EXEC_REGION_MAX
    call    x64lens_phdr_analyze
    test    rax, rax
    jne     .error

    ; Section-derived metadata is an analyst indicator only. It must never
    ; change executable-region boundaries selected from PT_LOAD + PF_X.
    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rsi, [gad_mapped_file + FILEMAP_SIZE]
    lea     rdx, [gad_phdr_summary]
    call    x64lens_shdr_classify_stripped
    test    rax, rax
    jne     .error

    ; Allocate candidate storage from the Sprint 3 arena. The scanner still
    ; receives a plain gadget_record[] pointer, so later callers do not care
    ; whether storage came from .bss, mmap, or a growable allocator.
    lea     rdi, [gad_candidate_arena]
    mov     rsi, ANALYSIS_RECORD_ARENA_BYTES
    call    x64lens_arena_init
    test    rax, rax
    jne     .error

    lea     rdi, [gad_candidate_arena]
    mov     rsi, GADGET_RECORD_ARENA_BYTES
    mov     rdx, GADGET_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     r15, rax            ; arena-backed gadget_record[] pointer

    lea     rdi, [gad_candidate_arena]
    mov     rsi, CANDIDATE_EVIDENCE_ARENA_BYTES
    mov     rdx, CANDIDATE_EVIDENCE_RECORD_ALIGN
    call    x64lens_arena_alloc
    test    rax, rax
    jz      .arena_alloc_failed
    mov     r13, rax            ; dense candidate_evidence_record[] side-car

    ; Scan executable regions and populate raw candidate records. The scanner
    ; owns candidate discovery but does not print or classify. Store the
    ; bounded scanner depth and candidate capacity in the summary record before
    ; the scanner resets count fields.
    mov     [gad_summary + GADGET_SUMMARY_MAX_DEPTH], r14
    mov     qword [gad_summary + GADGET_SUMMARY_CAPACITY], GADGET_RECORD_MAX

    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rsi, [gad_mapped_file + FILEMAP_SIZE]
    lea     rdx, [gad_phdr_summary]
    lea     rcx, [gad_regions]
    lea     r8, [gad_summary]
    mov     r9, r15
    call    x64lens_scanner_find_ret_candidates
    test    rax, rax
    jne     .error

    ; Tag raw candidates with exact byte-template pattern IDs. patterns.asm
    ; records what suffix template matched without deciding exploit semantics.
    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    lea     rsi, [gad_summary]
    mov     rdx, r15
    call    x64lens_patterns_match_exact
    test    rax, rax
    jne     .error

    ; Translate exact pattern facts into conservative semantic primitive facts.
    ; classifier.asm owns this interpretation layer so scanners and pattern
    ; matching remain reusable when a future decoder side-car is introduced.
    lea     rdi, [gad_summary]
    mov     rsi, r15
    mov     rdx, [gad_mapped_file + FILEMAP_ADDR]
    call    x64lens_classifier_apply_exact
    test    rax, rax
    jne     .error

    ; Materialize additive raw/exact/semantic provenance into a dense side-car.
    ; This stage records existing evidence only and does not change counts,
    ; semantic classes, scores, or section annotations.
    lea     rdi, [gad_summary]
    mov     rsi, r15
    mov     rdx, r13
    call    x64lens_candidate_evidence_from_exact
    test    rax, rax
    jne     .error

    ; Score classified candidates after semantic facts exist. Unknown
    ; candidates remain unscored and are excluded from scored_candidate_count.
    lea     rdi, [gad_summary]
    mov     rsi, r15
    call    x64lens_scoring_apply
    test    rax, rax
    jne     .error

    ; Add optional section labels to candidate records after discovery and
    ; scoring so annotations cannot alter scanner or scoring metrics.
    mov     rdi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rsi, [gad_mapped_file + FILEMAP_SIZE]
    mov     rdx, r15
    mov     rcx, [gad_summary + GADGET_SUMMARY_COUNT]
    call    x64lens_shdr_annotate_gadgets
    test    rax, rax
    jne     .error

    ; Construct report identity and completeness only after every shared
    ; analysis stage has succeeded. Reporters consume this record but do not
    ; decide whether analysis was complete.
    lea     rdi, [gad_analysis_summary]
    mov     rsi, REPORT_COMMAND_GADGETS
    mov     rdx, r14
    lea     rcx, [gad_phdr_summary]
    lea     r8, [gad_summary]
    call    x64lens_analysis_summary_mark_complete
    test    rax, rax
    jne     .error

    ; Emit candidate records for human inspection, tests, or automation.
    cmp     ebx, 1
    je      .emit_json

.emit_text:
    mov     rdi, r12
    lea     rsi, [gad_summary]
    mov     rdx, r15
    mov     rcx, [gad_mapped_file + FILEMAP_ADDR]
    lea     r8, [gad_analysis_summary]
    call    x64lens_report_text_gadgets
    jmp     .emit_done

.emit_json:
    mov     rdi, r12
    mov     rsi, [gad_mapped_file + FILEMAP_ADDR]
    mov     rdx, [gad_mapped_file + FILEMAP_SIZE]
    lea     rcx, [gad_phdr_summary]
    lea     r8, [gad_summary]
    mov     r9, r15
    ; System V passes arguments seven and eight on the stack. The 16-byte
    ; reservation keeps the call-site aligned while carrying command-owned
    ; completeness and the dense candidate evidence side-car.
    sub     rsp, 16
    lea     rax, [gad_analysis_summary]
    mov     [rsp], rax
    mov     [rsp + 8], r13
    call    x64lens_report_json_gadgets
    add     rsp, 16

.emit_done:

    lea     rdi, [gad_candidate_arena]
    call    x64lens_arena_destroy
    lea     rdi, [gad_mapped_file]
    call    x64lens_file_unmap
    xor     rax, rax
    jmp     .done

.arena_alloc_failed:
    mov     rax, EXIT_BOUNDS

.error:
    mov     r13, rax
    lea     rdi, [gad_candidate_arena]
    call    x64lens_arena_destroy
    lea     rdi, [gad_mapped_file]
    call    x64lens_file_unmap
    mov     rdi, r13
    call    x64lens_error_print_status
    mov     rax, r13

.done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
