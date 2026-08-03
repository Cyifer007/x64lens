; dynamic_metadata.asm
;
; Purpose:
;   Retain bounded private PT_DYNAMIC carrier evidence for Sprint 12 mitigation
;   precision without changing public text, JSON, or schema 0.2.0.
;
; Roadmap role:
;   Patch 075 introduces the shared dynamic-metadata side-car and the first
;   private DT_TEXTREL / DF_TEXTREL state. Patch 076 may add distinct bounded
;   DT_RPATH and DT_RUNPATH facts through this same module.
;
; Public symbols:
;   x64lens_dynamic_metadata_context_init(context)
;   x64lens_dynamic_metadata_record(context, tag, index, file_offset, value)
;   x64lens_dynamic_metadata_finalize(context, phdr_summary)
;
; Safety and boundaries:
;   The caller supplies already checked Elf64_Dyn entry coordinates. This module
;   stores at most 64 represented carriers, fails closed before carrier 65, and
;   never maps files, follows paths, parses sections, scans gadgets, classifies
;   candidates, scores records, or formats reports.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_dynamic_metadata_context_init
global x64lens_dynamic_metadata_record
global x64lens_dynamic_metadata_finalize

; context_init(context=rdi) -> rax=status
x64lens_dynamic_metadata_context_init:
    test    rdi, rdi
    jz      .bounds
    push    rdi
    xor     eax, eax
    mov     rcx, DYNAMIC_METADATA_CONTEXT_SIZE / 8
    rep stosq
    pop     rdi
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_UNKNOWN
    xor     eax, eax
    ret
.bounds:
    mov     eax, EXIT_BOUNDS
    ret

; record(context=rdi, tag=rsi, index=rdx, file_offset=rcx, value=r8)
;   -> rax=status
;
; Clobbers caller-saved registers. The raw value is retained even for DT_TEXTREL
; so every carrier record has one stable shape.
x64lens_dynamic_metadata_record:
    test    rdi, rdi
    jz      .record_bounds
    cmp     rsi, DT_TEXTREL
    je      .tag_ok
    cmp     rsi, DT_FLAGS
    jne     .record_bounds
.tag_ok:
    mov     rax, [rdi + DYNAMIC_METADATA_CTX_CARRIER_COUNT]
    cmp     rax, DYNAMIC_METADATA_CARRIER_MAX
    jae     .record_unsupported
    mov     r9, rax
    shl     r9, 5
    add     r9, DYNAMIC_METADATA_CTX_CARRIERS
    add     r9, rdi
    mov     [r9 + DYNAMIC_METADATA_CARRIER_TAG], rsi
    mov     [r9 + DYNAMIC_METADATA_CARRIER_INDEX], rdx
    mov     [r9 + DYNAMIC_METADATA_CARRIER_FILE_OFFSET], rcx
    mov     [r9 + DYNAMIC_METADATA_CARRIER_VALUE], r8
    inc     qword [rdi + DYNAMIC_METADATA_CTX_CARRIER_COUNT]

    cmp     rsi, DT_TEXTREL
    jne     .record_flags
    inc     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_TAG_COUNT]
    xor     eax, eax
    ret

.record_flags:
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_FLAGS_COUNT], 0
    jne     .record_flags_more
    mov     [rdi + DYNAMIC_METADATA_CTX_FLAGS_FIRST_VALUE], r8
    mov     [rdi + DYNAMIC_METADATA_CTX_FLAGS_AND], r8
    mov     [rdi + DYNAMIC_METADATA_CTX_FLAGS_OR], r8
    inc     qword [rdi + DYNAMIC_METADATA_CTX_FLAGS_COUNT]
    xor     eax, eax
    ret
.record_flags_more:
    cmp     [rdi + DYNAMIC_METADATA_CTX_FLAGS_FIRST_VALUE], r8
    je      .record_flags_accumulate
    inc     qword [rdi + DYNAMIC_METADATA_CTX_FULL_VALUE_CONFLICTS]
.record_flags_accumulate:
    and     [rdi + DYNAMIC_METADATA_CTX_FLAGS_AND], r8
    or      [rdi + DYNAMIC_METADATA_CTX_FLAGS_OR], r8
    inc     qword [rdi + DYNAMIC_METADATA_CTX_FLAGS_COUNT]
    xor     eax, eax
    ret

.record_bounds:
    mov     eax, EXIT_BOUNDS
    ret
.record_unsupported:
    mov     eax, EXIT_UNSUPPORTED
    ret

; finalize(context=rdi, summary=rsi) -> rax=status
;
; A complete bounded table requires one PT_DYNAMIC and a retained DT_NULL.
; Duplicate DT_FLAGS values may disagree in unrelated bits without making the
; text-relocation state contradictory. Only disagreement in DF_TEXTREL does so.
x64lens_dynamic_metadata_finalize:
    test    rdi, rdi
    jz      .finalize_bounds
    test    rsi, rsi
    jz      .finalize_bounds
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TABLE_COMPLETE], 0
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS], 0
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_UNKNOWN

    ; Preserve duplicate-carrier disagreement even when the bounded table lacks
    ; DT_NULL.  The semantic aggregate remains unknown until the table is
    ; complete, but the private carrier-conformance fact must not be erased.
    mov     rax, [rdi + DYNAMIC_METADATA_CTX_FLAGS_OR]
    and     rax, DF_TEXTREL
    mov     rcx, [rdi + DYNAMIC_METADATA_CTX_FLAGS_AND]
    and     rcx, DF_TEXTREL
    cmp     rax, rcx
    je      .textrel_conflict_recorded
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS], 1
.textrel_conflict_recorded:
    cmp     qword [rsi + PHDR_SUMMARY_DYNAMIC_SEEN], 1
    jne     .finalize_ok
    cmp     qword [rsi + PHDR_SUMMARY_DYNAMIC_NULL_SEEN], 1
    jne     .finalize_ok
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TABLE_COMPLETE], 1
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS], 0
    je      .textrel_consistent
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_CONTRADICTORY
    jmp     .finalize_ok
.textrel_consistent:
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_TAG_COUNT], 0
    jne     .textrel_present
    test    rax, rax
    jnz     .textrel_present
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_ABSENT
    jmp     .finalize_ok
.textrel_present:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_PRESENT
.finalize_ok:
    xor     eax, eax
    ret
.finalize_bounds:
    mov     eax, EXIT_BOUNDS
    ret

section .note.GNU-stack noalloc noexec nowrite progbits
