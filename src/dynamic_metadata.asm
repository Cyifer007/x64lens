; dynamic_metadata.asm
;
; Purpose:
;   Retain bounded private PT_DYNAMIC carrier and value evidence for Sprint 12
;   mitigation precision without changing public text, JSON, or schema 0.2.0.
;
; Roadmap role:
;   Patch 075 introduced private DT_TEXTREL / DF_TEXTREL evidence. Patch 076
;   preserves that accepted prefix and appends distinct byte-preserving
;   DT_RPATH and DT_RUNPATH facts through the same fixed-capacity side-car.
;
; Public symbols:
;   x64lens_dynamic_metadata_context_init(context)
;   x64lens_dynamic_metadata_record(context, tag, index, file_offset, value)
;   x64lens_dynamic_metadata_resolve_search_path(context, tag, index,
;                                                 string_file_offset,
;                                                 string_pointer,
;                                                 available_bytes)
;   x64lens_dynamic_metadata_finalize(context, phdr_summary)
;
; Safety and boundaries:
;   The caller supplies already checked Elf64_Dyn entry coordinates and one
;   checked DT_STRTAB/DT_STRSZ byte view. This module stores at most 64 mixed
;   carriers, 64 resolved search-path values, and 4,096 aggregate value bytes.
;   Carrier 65 or byte 4,097 fails closed. It never maps files, follows or opens
;   paths, splits ':', expands $ORIGIN, applies loader order, parses sections,
;   scans gadgets, classifies candidates, scores records, or formats reports.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_dynamic_metadata_context_init
global x64lens_dynamic_metadata_record
global x64lens_dynamic_metadata_resolve_search_path
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
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_FIRST_RECORD], DYNAMIC_METADATA_SEARCH_FIRST_NONE
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_FIRST_RECORD], DYNAMIC_METADATA_SEARCH_FIRST_NONE
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN
    xor     eax, eax
    ret
.bounds:
    mov     eax, EXIT_BOUNDS
    ret

; record(context=rdi, tag=rsi, index=rdx, file_offset=rcx, value=r8)
;   -> rax=status
;
; Clobbers caller-saved registers. The raw value is retained for every family so
; carrier provenance has one stable record shape.
x64lens_dynamic_metadata_record:
    test    rdi, rdi
    jz      .record_bounds
    cmp     rsi, DT_TEXTREL
    je      .tag_ok
    cmp     rsi, DT_FLAGS
    je      .tag_ok
    cmp     rsi, DT_RPATH
    je      .tag_ok
    cmp     rsi, DT_RUNPATH
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
    je      .record_textrel
    cmp     rsi, DT_FLAGS
    je      .record_flags
    cmp     rsi, DT_RPATH
    je      .record_rpath
    inc     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_CARRIER_COUNT]
    xor     eax, eax
    ret
.record_rpath:
    inc     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_CARRIER_COUNT]
    xor     eax, eax
    ret
.record_textrel:
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

; resolve_search_path(context=rdi, tag=rsi, index=rdx,
;                     string_file_offset=rcx, string_pointer=r8,
;                     available_bytes=r9) -> rax=status
;
; The raw carrier must already exist. The supplied pointer/extent is a checked
; suffix of the bounded DT_STRTAB/DT_STRSZ view. Empty strings are retained as
; zero-length values. Missing NUL termination is malformed when the complete
; available extent fits the remaining budget and unsupported when the value or
; aggregate byte work would require byte 4,097.
x64lens_dynamic_metadata_resolve_search_path:
    push    rbx
    push    rbp
    push    r12
    push    r13
    push    r14
    push    r15

    mov     r12, rdi            ; context
    mov     r13, rsi            ; tag
    mov     r14, rdx            ; dynamic index
    mov     r15, rcx            ; translated string file offset
    mov     rbp, r8             ; checked string pointer
    mov     rbx, r9             ; available bytes

    test    r12, r12
    jz      .resolve_bounds
    test    rbp, rbp
    jz      .resolve_bounds
    cmp     r13, DT_RPATH
    je      .resolve_tag_ok
    cmp     r13, DT_RUNPATH
    jne     .resolve_bounds
.resolve_tag_ok:
    test    rbx, rbx
    jz      .resolve_malformed

    ; Find the exact raw carrier by family and dynamic-table index.
    xor     eax, eax
    mov     rcx, [r12 + DYNAMIC_METADATA_CTX_CARRIER_COUNT]
.resolve_find_carrier:
    cmp     rax, rcx
    jae     .resolve_bounds
    mov     r10, rax
    shl     r10, 5
    add     r10, DYNAMIC_METADATA_CTX_CARRIERS
    add     r10, r12
    cmp     [r10 + DYNAMIC_METADATA_CARRIER_TAG], r13
    jne     .resolve_find_next
    cmp     [r10 + DYNAMIC_METADATA_CARRIER_INDEX], r14
    je      .resolve_carrier_found
.resolve_find_next:
    inc     rax
    jmp     .resolve_find_carrier

.resolve_carrier_found:
    mov     r9, [r12 + DYNAMIC_METADATA_CTX_SEARCH_BYTES_USED]
    cmp     r9, DYNAMIC_METADATA_SEARCH_BYTES_MAX
    ja      .resolve_bounds
    mov     rdx, DYNAMIC_METADATA_SEARCH_BYTES_MAX
    sub     rdx, r9             ; remaining aggregate bytes
    xor     ecx, ecx            ; candidate value length
.resolve_nul_scan:
    cmp     rcx, rbx
    jae     .resolve_malformed  ; full available string-table suffix had no NUL
    cmp     byte [rbp + rcx], 0
    je      .resolve_length_found
    cmp     rcx, rdx
    jae     .resolve_unsupported ; one more value byte would require byte 4,097
    inc     rcx
    jmp     .resolve_nul_scan

.resolve_length_found:
    ; RCX is exact byte length excluding NUL and is <= remaining budget.
    mov     rbx, [r12 + DYNAMIC_METADATA_CTX_SEARCH_RECORD_COUNT]
    cmp     rbx, DYNAMIC_METADATA_SEARCH_RECORD_MAX
    jae     .resolve_unsupported

    xor     r8d, r8d            ; family-value conflict flag
    cmp     r13, DT_RPATH
    jne     .resolve_compare_runpath
    cmp     qword [r12 + DYNAMIC_METADATA_CTX_RPATH_VALUE_COUNT], 0
    je      .resolve_record
    mov     rax, [r12 + DYNAMIC_METADATA_CTX_RPATH_FIRST_RECORD]
    jmp     .resolve_compare_first
.resolve_compare_runpath:
    cmp     qword [r12 + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_COUNT], 0
    je      .resolve_record
    mov     rax, [r12 + DYNAMIC_METADATA_CTX_RUNPATH_FIRST_RECORD]
.resolve_compare_first:
    cmp     rax, DYNAMIC_METADATA_SEARCH_RECORD_MAX
    jae     .resolve_bounds
    imul    rax, DYNAMIC_METADATA_SEARCH_RECORD_SIZE
    add     rax, DYNAMIC_METADATA_CTX_SEARCH_RECORDS
    add     rax, r12
    cmp     [rax + DYNAMIC_METADATA_SEARCH_RECORD_BYTE_LENGTH], rcx
    jne     .resolve_conflict
    mov     r11, [rax + DYNAMIC_METADATA_SEARCH_RECORD_BYTE_POOL_OFFSET]
    cmp     r11, DYNAMIC_METADATA_SEARCH_BYTES_MAX
    ja      .resolve_bounds
    xor     esi, esi
.resolve_compare_bytes:
    cmp     rsi, rcx
    jae     .resolve_record
    mov     al, [r12 + DYNAMIC_METADATA_CTX_SEARCH_BYTES + r11]
    cmp     al, [rbp + rsi]
    jne     .resolve_conflict
    inc     r11
    inc     rsi
    jmp     .resolve_compare_bytes
.resolve_conflict:
    mov     r8d, 1

.resolve_record:
    mov     r11, rbx
    imul    r11, DYNAMIC_METADATA_SEARCH_RECORD_SIZE
    add     r11, DYNAMIC_METADATA_CTX_SEARCH_RECORDS
    add     r11, r12
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_TAG], r13
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_INDEX], r14
    mov     rax, [r10 + DYNAMIC_METADATA_CARRIER_FILE_OFFSET]
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_DYNAMIC_FILE_OFFSET], rax
    mov     rax, [r10 + DYNAMIC_METADATA_CARRIER_VALUE]
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_STRING_TABLE_OFFSET], rax
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_STRING_FILE_OFFSET], r15
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_BYTE_POOL_OFFSET], r9
    mov     [r11 + DYNAMIC_METADATA_SEARCH_RECORD_BYTE_LENGTH], rcx

    lea     rdi, [r12 + DYNAMIC_METADATA_CTX_SEARCH_BYTES]
    add     rdi, r9
    mov     rsi, rbp
    mov     rdx, rcx            ; preserve length across REP
    rep movsb
    add     [r12 + DYNAMIC_METADATA_CTX_SEARCH_BYTES_USED], rdx
    inc     qword [r12 + DYNAMIC_METADATA_CTX_SEARCH_RECORD_COUNT]

    cmp     r13, DT_RPATH
    jne     .resolve_commit_runpath
    cmp     qword [r12 + DYNAMIC_METADATA_CTX_RPATH_VALUE_COUNT], 0
    jne     .resolve_rpath_existing
    mov     [r12 + DYNAMIC_METADATA_CTX_RPATH_FIRST_RECORD], rbx
.resolve_rpath_existing:
    inc     qword [r12 + DYNAMIC_METADATA_CTX_RPATH_VALUE_COUNT]
    test    r8d, r8d
    jz      .resolve_ok
    inc     qword [r12 + DYNAMIC_METADATA_CTX_RPATH_VALUE_CONFLICTS]
    jmp     .resolve_ok
.resolve_commit_runpath:
    cmp     qword [r12 + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_COUNT], 0
    jne     .resolve_runpath_existing
    mov     [r12 + DYNAMIC_METADATA_CTX_RUNPATH_FIRST_RECORD], rbx
.resolve_runpath_existing:
    inc     qword [r12 + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_COUNT]
    test    r8d, r8d
    jz      .resolve_ok
    inc     qword [r12 + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_CONFLICTS]

.resolve_ok:
    xor     eax, eax
    jmp     .resolve_done
.resolve_malformed:
    mov     eax, EXIT_MALFORMED_ELF
    jmp     .resolve_done
.resolve_unsupported:
    mov     eax, EXIT_UNSUPPORTED
    jmp     .resolve_done
.resolve_bounds:
    mov     eax, EXIT_BOUNDS
.resolve_done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbp
    pop     rbx
    ret

; finalize(context=rdi, summary=rsi) -> rax=status
;
; A complete bounded table requires one PT_DYNAMIC and a retained DT_NULL.
; Duplicate DT_FLAGS values may disagree in unrelated bits without making the
; text-relocation state contradictory. RPATH and RUNPATH states are independent
; and become contradictory only when duplicate values within the same family
; disagree byte-for-byte.
x64lens_dynamic_metadata_finalize:
    test    rdi, rdi
    jz      .finalize_bounds
    test    rsi, rsi
    jz      .finalize_bounds
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TABLE_COMPLETE], 0
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS], 0
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_UNKNOWN
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN

    ; Preserve duplicate-carrier disagreement even when the bounded table lacks
    ; DT_NULL. The semantic aggregate remains unknown until the table is
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
    jmp     .finalize_rpath
.textrel_consistent:
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_TAG_COUNT], 0
    jne     .textrel_present
    test    rax, rax
    jnz     .textrel_present
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_ABSENT
    jmp     .finalize_rpath
.textrel_present:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_TEXTREL_STATE], DYNAMIC_METADATA_STATE_PRESENT

.finalize_rpath:
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_VALUE_CONFLICTS], 0
    jne     .rpath_contradictory
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_VALUE_COUNT], 0
    jne     .rpath_present
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_CARRIER_COUNT], 0
    jne     .rpath_unknown       ; unresolved carrier is not negative evidence
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_ABSENT
    jmp     .finalize_runpath
.rpath_present:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_PRESENT
    jmp     .finalize_runpath
.rpath_contradictory:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_CONTRADICTORY
    jmp     .finalize_runpath
.rpath_unknown:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN

.finalize_runpath:
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_CONFLICTS], 0
    jne     .runpath_contradictory
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_VALUE_COUNT], 0
    jne     .runpath_present
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_CARRIER_COUNT], 0
    jne     .runpath_unknown
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_ABSENT
    jmp     .finalize_ok
.runpath_present:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_PRESENT
    jmp     .finalize_ok
.runpath_contradictory:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_CONTRADICTORY
    jmp     .finalize_ok
.runpath_unknown:
    mov     qword [rdi + DYNAMIC_METADATA_CTX_RUNPATH_STATE], DYNAMIC_METADATA_STATE_UNKNOWN

.finalize_ok:
    xor     eax, eax
    ret
.finalize_bounds:
    mov     eax, EXIT_BOUNDS
    ret

section .note.GNU-stack noalloc noexec nowrite progbits
