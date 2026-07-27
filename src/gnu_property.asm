; gnu_property.asm
;
; Purpose:
;   Collect and parse bounded ELF64 GNU property-note evidence without changing
;   public text output or schema 0.2.0. The module canonicalizes exact duplicate
;   physical carriers, retains every original PHDR contributor, rejects
;   non-identical carrier overlap, and derives private x86 IBT/SHSTK states.
;
; Public symbols:
;   x64lens_gnu_property_context_init
;   x64lens_gnu_property_register_carrier
;   x64lens_gnu_property_parse
;
; Boundaries:
;   This module consumes already validated ELF/PHDR facts and bounded file-backed
;   note carriers. It does not map files, choose executable regions, scan gadget
;   bytes, classify candidates, score, or format reports. Unknown note/property
;   types remain private bounded evidence and never become public conclusions.
;
; Safety:
;   All file-derived ranges, record lengths, alignment arithmetic, counts, and
;   padding are checked before dereference. Cap exhaustion returns
;   EXIT_UNSUPPORTED; malformed/truncated data returns EXIT_MALFORMED_ELF.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_bounds_range_end_valid

section .text
global x64lens_gnu_property_context_init
global x64lens_gnu_property_register_carrier
global x64lens_gnu_property_parse

; x64lens_gnu_property_context_init(context=rdi, summary=rsi) -> rax=status
x64lens_gnu_property_context_init:
    test    rdi, rdi
    jz      .init_bounds
    test    rsi, rsi
    jz      .init_bounds

    push    rdi
    mov     rcx, GNU_PROPERTY_CONTEXT_SIZE / 8
    xor     eax, eax
    rep stosq
    pop     rdi

    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT], 0
    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT], 0
    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT], 0
    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT], 0
    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND], 0
    mov     qword [rsi + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR], 0
    xor     eax, eax
    ret
.init_bounds:
    mov     eax, EXIT_BOUNDS
    ret

; x64lens_gnu_property_register_carrier(
;   base=rdi, file_size=rsi, context=rdx, phdr_index=rcx, phdr_ptr=r8)
;   -> rax=status
;
; Exact duplicate physical ranges share a canonical carrier slot. Every original
; PHDR index/type still receives its own contributor record. Non-identical physical
; overlap is counted for diagnostics and rejected as malformed before reporting.
x64lens_gnu_property_register_carrier:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56

    mov     r15, rdi            ; mapped base (identity check only)
    mov     r14, rsi            ; file size
    mov     r13, rdx            ; context
    mov     r12, rcx            ; original PHDR index
    mov     rbp, r8             ; PHDR pointer

    test    r15, r15
    jz      .carrier_bounds
    test    r13, r13
    jz      .carrier_bounds
    test    rbp, rbp
    jz      .carrier_bounds

    mov     eax, [rbp + P_TYPE]
    cmp     eax, PT_NOTE
    je      .carrier_note
    cmp     eax, PT_GNU_PROPERTY
    je      .carrier_property
    jmp     .carrier_bounds
.carrier_note:
    mov     qword [rsp + 8], GNU_PROPERTY_CARRIER_KIND_NOTE
    mov     qword [rsp + 40], GNU_PROPERTY_CARRIER_ALIGN_4
    mov     rax, [rbp + P_ALIGN]
    cmp     rax, 8
    je      .carrier_note_align8
    cmp     rax, 4
    je      .carrier_type_ok
    cmp     rax, 1
    je      .carrier_type_ok
    test    rax, rax
    jz      .carrier_type_ok
    jmp     .carrier_unsupported
.carrier_note_align8:
    mov     qword [rsp + 40], GNU_PROPERTY_CARRIER_ALIGN_8
    jmp     .carrier_type_ok
.carrier_property:
    mov     qword [rsp + 8], GNU_PROPERTY_CARRIER_KIND_PROPERTY
    ; The ELF64 GNU property program header is a native-word-aligned note
    ; carrier. A different alignment is not a weaker negative fact: it is a
    ; structurally contradictory PT_GNU_PROPERTY representation.
    cmp     qword [rbp + P_ALIGN], 8
    jne     .carrier_malformed
    mov     qword [rsp + 40], GNU_PROPERTY_CARRIER_ALIGN_8
.carrier_type_ok:

    ; Note carriers are file-backed metadata. Unlike PT_LOAD, their p_memsz is
    ; not used as a file-range authority; p_offset/p_filesz and the mapped file
    ; bound the bytes consumed here.
    mov     rax, [rbp + P_FILESZ]
    mov     [rsp + 16], rax     ; new size
    mov     rax, [rbp + P_OFFSET]
    mov     [rsp + 24], rax     ; new offset

    mov     rdi, r14
    mov     rsi, [rsp + 24]
    mov     rdx, [rsp + 16]
    lea     rcx, [rsp + 32]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .carrier_malformed
    cmp     qword [rsp + 16], GNU_PROPERTY_CARRIER_SCAN_MAX
    ja      .carrier_unsupported

    mov     rax, [r13 + GNU_PROPERTY_CTX_CARRIER_COUNT]
    cmp     rax, GNU_PROPERTY_CARRIER_MAX
    ja      .carrier_bounds
    mov     rbx, -1             ; selected carrier slot
    xor     rcx, rcx
.carrier_find_loop:
    cmp     rcx, rax
    jae     .carrier_find_done
    mov     rdx, rcx
    imul    rdx, GNU_PROPERTY_CARRIER_RECORD_SIZE
    lea     r9, [r13 + GNU_PROPERTY_CTX_CARRIERS]
    add     r9, rdx

    mov     rdx, [r9 + GNU_PROPERTY_CARRIER_OFFSET]
    cmp     rdx, [rsp + 24]
    jne     .carrier_overlap_check
    mov     rdx, [r9 + GNU_PROPERTY_CARRIER_SIZE]
    cmp     rdx, [rsp + 16]
    jne     .carrier_overlap_check
    mov     rbx, rcx
    mov     rdx, [rsp + 8]
    or      [r9 + GNU_PROPERTY_CARRIER_KIND_MASK], rdx
    mov     rdx, [rsp + 40]
    or      [r9 + GNU_PROPERTY_CARRIER_ALIGN_MASK], rdx
    jmp     .carrier_find_done

.carrier_overlap_check:
    ; Zero-length carriers cannot overlap. Existing context ranges were checked
    ; when registered, so their exclusive end can be formed without overflow.
    cmp     qword [rsp + 16], 0
    je      .carrier_find_next
    mov     rdx, [r9 + GNU_PROPERTY_CARRIER_SIZE]
    test    rdx, rdx
    jz      .carrier_find_next
    mov     r8, [r9 + GNU_PROPERTY_CARRIER_OFFSET]
    mov     r10, r8
    add     r10, rdx
    jc      .carrier_bounds
    cmp     qword [rsp + 24], r10
    jae     .carrier_find_next
    cmp     r8, [rsp + 32]
    jae     .carrier_find_next
    inc     qword [r13 + GNU_PROPERTY_CTX_OVERLAP_COUNT]
    ; Partially overlapping note carriers are ambiguous evidence. Exact-range
    ; aliases are canonicalized above; any other overlap fails before facts can
    ; reach a reporter.
    jmp     .carrier_malformed
.carrier_find_next:
    inc     rcx
    jmp     .carrier_find_loop

.carrier_find_done:
    cmp     rbx, -1
    jne     .carrier_append_contributor
    cmp     rax, GNU_PROPERTY_CARRIER_MAX
    jae     .carrier_unsupported
    mov     rbx, rax
    mov     rdx, rax
    imul    rdx, GNU_PROPERTY_CARRIER_RECORD_SIZE
    lea     r9, [r13 + GNU_PROPERTY_CTX_CARRIERS]
    add     r9, rdx
    mov     rdx, [rsp + 24]
    mov     [r9 + GNU_PROPERTY_CARRIER_OFFSET], rdx
    mov     rdx, [rsp + 16]
    mov     [r9 + GNU_PROPERTY_CARRIER_SIZE], rdx
    mov     rdx, [rsp + 8]
    mov     [r9 + GNU_PROPERTY_CARRIER_KIND_MASK], rdx
    mov     rdx, [rsp + 40]
    mov     [r9 + GNU_PROPERTY_CARRIER_ALIGN_MASK], rdx
    inc     qword [r13 + GNU_PROPERTY_CTX_CARRIER_COUNT]

.carrier_append_contributor:
    mov     rax, [r13 + GNU_PROPERTY_CTX_CONTRIBUTOR_COUNT]
    cmp     rax, GNU_PROPERTY_CONTRIBUTOR_MAX
    jae     .carrier_unsupported
    mov     rdx, rax
    imul    rdx, GNU_PROPERTY_CONTRIB_RECORD_SIZE
    lea     r9, [r13 + GNU_PROPERTY_CTX_CONTRIBUTORS]
    add     r9, rdx
    mov     [r9 + GNU_PROPERTY_CONTRIB_PHDR_INDEX], r12
    mov     eax, [rbp + P_TYPE]
    mov     [r9 + GNU_PROPERTY_CONTRIB_PHDR_TYPE], rax
    mov     [r9 + GNU_PROPERTY_CONTRIB_CARRIER_SLOT], rbx
    inc     qword [r13 + GNU_PROPERTY_CTX_CONTRIBUTOR_COUNT]
    xor     eax, eax
    jmp     .carrier_done
.carrier_malformed:
    mov     eax, EXIT_MALFORMED_ELF
    jmp     .carrier_done
.carrier_unsupported:
    mov     eax, EXIT_UNSUPPORTED
    jmp     .carrier_done
.carrier_bounds:
    mov     eax, EXIT_BOUNDS
.carrier_done:
    add     rsp, 56
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; x64lens_gnu_property_parse(base=rdi, file_size=rsi, context=rdx, summary=rcx)
;   -> rax=status
;
; Parses canonical carriers as bounded ELF note streams. Only notes with the
; exact GNU owner and NT_GNU_PROPERTY_TYPE_0 type are interpreted as GNU
; property descriptors. Unknown notes, properties, and feature bits remain
; bounded private facts. Malformed recognized property structures fail closed.
x64lens_gnu_property_parse:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 152

    mov     r15, rdi            ; mapped base
    mov     r14, rsi            ; file size
    mov     r13, rdx            ; context
    mov     r12, rcx            ; summary
    test    r15, r15
    jz      .parse_bounds
    test    r13, r13
    jz      .parse_bounds
    test    r12, r12
    jz      .parse_bounds

    mov     rax, [r13 + GNU_PROPERTY_CTX_CARRIER_COUNT]
    cmp     rax, GNU_PROPERTY_CARRIER_MAX
    ja      .parse_bounds
    mov     rax, [r13 + GNU_PROPERTY_CTX_CONTRIBUTOR_COUNT]
    cmp     rax, GNU_PROPERTY_CONTRIBUTOR_MAX
    ja      .parse_bounds
    mov     rax, [r13 + GNU_PROPERTY_CTX_NOTE_COUNT]
    cmp     rax, GNU_PROPERTY_NOTE_MAX
    ja      .parse_bounds

    mov     qword [rsp + 112], 0 ; global property-entry count
    mov     qword [rsp + 120], 0 ; global note-header count
    xor     rbx, rbx             ; carrier slot
.parse_carrier_loop:
    cmp     rbx, [r13 + GNU_PROPERTY_CTX_CARRIER_COUNT]
    jae     .parse_finalize

    mov     rax, rbx
    imul    rax, GNU_PROPERTY_CARRIER_RECORD_SIZE
    lea     rbp, [r13 + GNU_PROPERTY_CTX_CARRIERS]
    add     rbp, rax
    mov     rax, [rbp + GNU_PROPERTY_CARRIER_OFFSET]
    mov     [rsp + 0], rax       ; carrier start
    mov     rdx, [rbp + GNU_PROPERTY_CARRIER_SIZE]
    mov     [rsp + 8], rdx       ; carrier size
    mov     rax, [rbp + GNU_PROPERTY_CARRIER_ALIGN_MASK]
    test    rax, GNU_PROPERTY_CARRIER_ALIGN_8
    jnz     .parse_carrier_align8
    test    rax, GNU_PROPERTY_CARRIER_ALIGN_4
    jz      .parse_bounds
    mov     qword [rsp + 128], 4 ; carrier note alignment
    jmp     .parse_carrier_alignment_ready
.parse_carrier_align8:
    mov     qword [rsp + 128], 8 ; strongest exact-duplicate carrier view
.parse_carrier_alignment_ready:
    mov     rdi, r14
    mov     rsi, [rsp + 0]
    mov     rdx, [rsp + 8]
    lea     rcx, [rsp + 16]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .parse_malformed
    mov     rax, [rsp + 0]
    mov     [rsp + 24], rax      ; current note offset

.parse_note_loop:
    mov     rax, [rsp + 24]
    cmp     rax, [rsp + 16]
    jae     .parse_next_carrier
    mov     rcx, [rsp + 16]
    sub     rcx, rax             ; remaining carrier bytes
    cmp     rcx, ELF64_NHDR_SIZE
    jae     .parse_note_header

    ; Permit only all-zero final alignment padding shorter than a note header.
    xor     rdx, rdx
.parse_tail_zero_loop:
    cmp     rdx, rcx
    jae     .parse_next_carrier
    mov     r8, rax
    add     r8, rdx
    cmp     byte [r15 + r8], 0
    jne     .parse_malformed
    inc     rdx
    jmp     .parse_tail_zero_loop

.parse_note_header:
    inc     qword [rsp + 120]
    cmp     qword [rsp + 120], GNU_PROPERTY_NOTE_SCAN_MAX
    ja      .parse_unsupported
    mov     rdx, rax
    add     rdx, ELF64_NHDR_SIZE
    jc      .parse_malformed
    cmp     rdx, [rsp + 16]
    ja      .parse_malformed
    mov     [rsp + 32], rax      ; note start
    mov     eax, [r15 + rax + N_NAMESZ]
    mov     [rsp + 40], rax      ; namesz
    mov     rdx, [rsp + 32]
    mov     eax, [r15 + rdx + N_DESCSZ]
    mov     [rsp + 48], rax      ; descsz
    mov     eax, [r15 + rdx + N_TYPE]
    mov     [rsp + 56], rax      ; note type

    mov     rax, [rsp + 32]
    add     rax, ELF64_NHDR_SIZE
    jc      .parse_malformed
    mov     [rsp + 64], rax      ; name start
    add     rax, [rsp + 40]
    jc      .parse_malformed
    cmp     rax, [rsp + 16]
    ja      .parse_malformed
    mov     rdx, [rsp + 128]
    dec     rdx
    add     rax, rdx
    jc      .parse_malformed
    not     rdx
    and     rax, rdx
    cmp     rax, [rsp + 16]
    ja      .parse_malformed
    mov     [rsp + 72], rax      ; desc start
    add     rax, [rsp + 48]
    jc      .parse_malformed
    cmp     rax, [rsp + 16]
    ja      .parse_malformed
    mov     [rsp + 80], rax      ; desc end
    mov     rdx, [rsp + 128]
    dec     rdx
    add     rax, rdx
    jc      .parse_malformed
    not     rdx
    and     rax, rdx
    cmp     rax, [rsp + 16]
    ja      .parse_malformed
    mov     [rsp + 88], rax      ; next note offset

    ; Canonical note padding is part of the private evidence contract. Check
    ; the owner-to-descriptor and descriptor-to-next-note gaps before deciding
    ; whether the note is recognized. This keeps malformed padding from being
    ; laundered through an unrelated or duplicate carrier view.
    mov     r10, [rsp + 64]
    add     r10, [rsp + 40]      ; name end
    jc      .parse_malformed
.parse_name_padding_loop:
    cmp     r10, [rsp + 72]
    jae     .parse_desc_padding_start
    cmp     byte [r15 + r10], 0
    jne     .parse_malformed
    inc     r10
    jmp     .parse_name_padding_loop
.parse_desc_padding_start:
    mov     r10, [rsp + 80]
.parse_desc_padding_loop:
    cmp     r10, [rsp + 88]
    jae     .parse_note_identity
    cmp     byte [r15 + r10], 0
    jne     .parse_malformed
    inc     r10
    jmp     .parse_desc_padding_loop

.parse_note_identity:

    cmp     qword [rsp + 40], GNU_NOTE_NAME_SIZE
    jne     .parse_note_advance
    mov     rax, [rsp + 64]
    cmp     dword [r15 + rax], GNU_NOTE_NAME_DWORD
    jne     .parse_note_advance
    cmp     qword [rsp + 56], NT_GNU_PROPERTY_TYPE_0
    jne     .parse_note_advance
    cmp     qword [rsp + 48], GNU_PROPERTY_DESC_SCAN_MAX
    ja      .parse_unsupported
    cmp     qword [rsp + 48], GNU_PROPERTY_ENTRY_HEADER_SIZE
    jb      .parse_malformed
    test    qword [rsp + 48], 7
    jnz     .parse_malformed

    ; Deduplicate the recognized physical note range. A partial overlap between
    ; two recognized views is ambiguous and fails closed.
    mov     r10, [rsp + 88]
    sub     r10, [rsp + 32]      ; complete note physical size
    xor     rcx, rcx
    mov     r11, -1
.parse_note_find_loop:
    cmp     rcx, [r13 + GNU_PROPERTY_CTX_NOTE_COUNT]
    jae     .parse_note_find_done
    mov     rax, rcx
    imul    rax, GNU_PROPERTY_NOTE_RECORD_SIZE
    lea     r9, [r13 + GNU_PROPERTY_CTX_NOTES]
    add     r9, rax
    mov     rax, [r9 + GNU_PROPERTY_NOTE_OFFSET]
    cmp     rax, [rsp + 32]
    jne     .parse_note_overlap_check
    cmp     qword [r9 + GNU_PROPERTY_NOTE_SIZE], r10
    jne     .parse_note_overlap_check
    mov     r11, rcx
    jmp     .parse_note_find_done
.parse_note_overlap_check:
    mov     rdx, [r9 + GNU_PROPERTY_NOTE_SIZE]
    test    rdx, rdx
    jz      .parse_note_find_next
    mov     r8, rax
    add     r8, rdx
    jc      .parse_bounds
    cmp     qword [rsp + 32], r8
    jae     .parse_note_find_next
    mov     r8, [rsp + 32]
    add     r8, r10
    jc      .parse_malformed
    cmp     rax, r8
    jae     .parse_note_find_next
    jmp     .parse_malformed
.parse_note_find_next:
    inc     rcx
    jmp     .parse_note_find_loop
.parse_note_find_done:
    cmp     r11, -1
    jne     .parse_note_advance
    mov     rax, [r13 + GNU_PROPERTY_CTX_NOTE_COUNT]
    cmp     rax, GNU_PROPERTY_NOTE_MAX
    jae     .parse_unsupported
    mov     rdx, rax
    imul    rdx, GNU_PROPERTY_NOTE_RECORD_SIZE
    lea     r9, [r13 + GNU_PROPERTY_CTX_NOTES]
    add     r9, rdx
    mov     rdx, [rsp + 32]
    mov     [r9 + GNU_PROPERTY_NOTE_OFFSET], rdx
    mov     [r9 + GNU_PROPERTY_NOTE_SIZE], r10
    inc     qword [r13 + GNU_PROPERTY_CTX_NOTE_COUNT]

    ; Parse the GNU property descriptor as 8-byte-aligned property records.
    mov     rax, [rsp + 72]
    mov     [rsp + 96], rax      ; property cursor
    mov     qword [rsp + 136], 0 ; prior property type
    mov     qword [rsp + 144], 0 ; prior property type valid
.parse_property_loop:
    mov     rax, [rsp + 96]
    cmp     rax, [rsp + 80]
    jae     .parse_note_advance
    mov     rcx, [rsp + 80]
    sub     rcx, rax
    cmp     rcx, GNU_PROPERTY_ENTRY_HEADER_SIZE
    jb      .parse_malformed
    inc     qword [rsp + 112]
    cmp     qword [rsp + 112], GNU_PROPERTY_ENTRY_MAX
    ja      .parse_unsupported

    mov     edx, [r15 + rax]
    mov     [rsp + 104], rdx     ; property type
    cmp     qword [rsp + 144], 0
    je      .parse_property_order_first
    cmp     edx, [rsp + 136]
    jb      .parse_malformed
.parse_property_order_first:
    mov     [rsp + 136], edx
    mov     qword [rsp + 144], 1
    mov     edx, [r15 + rax + 4]
    mov     [rsp + 108], edx     ; property data size (dword scratch)
    add     rax, GNU_PROPERTY_ENTRY_HEADER_SIZE
    jc      .parse_malformed
    mov     r10, rax             ; data start
    mov     edx, [rsp + 108]
    add     rax, rdx
    jc      .parse_malformed
    cmp     rax, [rsp + 80]
    ja      .parse_malformed
    mov     r11, rax             ; data end
    ; GNU property entry alignment is relative to the descriptor origin, not
    ; the absolute file offset. A descriptor beginning at file-offset mod 8 == 4
    ; is valid when each entry is aligned within that descriptor.
    mov     rdx, rax
    sub     rdx, [rsp + 72]
    jc      .parse_malformed
    add     rdx, 7
    jc      .parse_malformed
    and     rdx, -8
    mov     rax, [rsp + 72]
    add     rax, rdx
    jc      .parse_malformed
    cmp     rax, [rsp + 80]
    ja      .parse_malformed
    mov     [rsp + 96], rax      ; next property cursor

    ; Alignment padding is required to be zero for deterministic canonical
    ; evidence. Nonzero padding is malformed rather than ignored.
.parse_property_padding:
    cmp     r11, rax
    jae     .parse_property_dispatch
    cmp     byte [r15 + r11], 0
    jne     .parse_malformed
    inc     r11
    jmp     .parse_property_padding

.parse_property_dispatch:
    cmp     dword [rsp + 104], GNU_PROPERTY_X86_FEATURE_1_AND
    jne     .parse_unknown_property
    cmp     dword [rsp + 108], 4
    jne     .parse_malformed
    mov     eax, [r15 + r10]
    mov     rdx, rax
    and     rdx, ~(GNU_PROPERTY_X86_FEATURE_1_IBT | GNU_PROPERTY_X86_FEATURE_1_SHSTK)
    jz      .parse_feature_known_bits
    inc     qword [r13 + GNU_PROPERTY_CTX_UNKNOWN_COUNT]
.parse_feature_known_bits:
    cmp     qword [r13 + GNU_PROPERTY_CTX_FEATURE1_COUNT], 0
    jne     .parse_feature_accumulate
    mov     [r13 + GNU_PROPERTY_CTX_FEATURE1_AND], rax
    mov     [r13 + GNU_PROPERTY_CTX_FEATURE1_OR], rax
    jmp     .parse_feature_count
.parse_feature_accumulate:
    cmp     [r13 + GNU_PROPERTY_CTX_FEATURE1_AND], rax
    je      .parse_feature_no_conflict
    inc     qword [r13 + GNU_PROPERTY_CTX_CONFLICT_COUNT]
.parse_feature_no_conflict:
    and     [r13 + GNU_PROPERTY_CTX_FEATURE1_AND], rax
    or      [r13 + GNU_PROPERTY_CTX_FEATURE1_OR], rax
.parse_feature_count:
    inc     qword [r13 + GNU_PROPERTY_CTX_FEATURE1_COUNT]
    jmp     .parse_property_loop

.parse_unknown_property:
    inc     qword [r13 + GNU_PROPERTY_CTX_UNKNOWN_COUNT]
    jmp     .parse_property_loop

.parse_note_advance:
    mov     rax, [rsp + 88]
    mov     [rsp + 24], rax
    jmp     .parse_note_loop

.parse_next_carrier:
    inc     rbx
    jmp     .parse_carrier_loop

.parse_finalize:
    mov     rax, [r13 + GNU_PROPERTY_CTX_CARRIER_COUNT]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT], rax
    mov     rax, [r13 + GNU_PROPERTY_CTX_CONTRIBUTOR_COUNT]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT], rax
    mov     rax, [r13 + GNU_PROPERTY_CTX_NOTE_COUNT]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT], rax
    mov     rax, [r13 + GNU_PROPERTY_CTX_FEATURE1_COUNT]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT], rax
    mov     rax, [r13 + GNU_PROPERTY_CTX_FEATURE1_AND]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND], rax
    mov     rax, [r13 + GNU_PROPERTY_CTX_FEATURE1_OR]
    mov     [r12 + PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR], rax
    ; Detailed unknown/conflict/overlap counts and named feature states remain
    ; in the bounded command-lifetime context. Only the six canonical aggregate
    ; facts above enter phdr_summary, keeping total Patch 065 summary growth at
    ; the accepted 64-byte ceiling.
    mov     qword [r13 + GNU_PROPERTY_CTX_IBT_STATE], GNU_PROPERTY_STATE_UNKNOWN
    mov     qword [r13 + GNU_PROPERTY_CTX_SHSTK_STATE], GNU_PROPERTY_STATE_UNKNOWN
    cmp     qword [r13 + GNU_PROPERTY_CTX_FEATURE1_COUNT], 0
    je      .parse_ok

    mov     rdi, GNU_PROPERTY_X86_FEATURE_1_IBT
    call    .derive_feature_state
    mov     [r13 + GNU_PROPERTY_CTX_IBT_STATE], rax
    mov     rdi, GNU_PROPERTY_X86_FEATURE_1_SHSTK
    call    .derive_feature_state
    mov     [r13 + GNU_PROPERTY_CTX_SHSTK_STATE], rax
.parse_ok:
    xor     eax, eax
    jmp     .parse_done
.parse_malformed:
    mov     eax, EXIT_MALFORMED_ELF
    jmp     .parse_done
.parse_unsupported:
    mov     eax, EXIT_UNSUPPORTED
    jmp     .parse_done
.parse_bounds:
    mov     eax, EXIT_BOUNDS
.parse_done:
    add     rsp, 152
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; derive_feature_state(bit=rdi) -> rax=GNU_PROPERTY_STATE_*
; Uses R13 context from the enclosing parser. OR=0 is a bounded absent result;
; AND=bit is present; OR=bit and AND=0 is contradictory duplicate evidence.
.derive_feature_state:
    mov     rax, [r13 + GNU_PROPERTY_CTX_FEATURE1_OR]
    test    rax, rdi
    jz      .derive_absent
    mov     rax, [r13 + GNU_PROPERTY_CTX_FEATURE1_AND]
    test    rax, rdi
    jz      .derive_contradictory
    mov     eax, GNU_PROPERTY_STATE_PRESENT
    ret
.derive_absent:
    mov     eax, GNU_PROPERTY_STATE_ABSENT
    ret
.derive_contradictory:
    mov     eax, GNU_PROPERTY_STATE_CONTRADICTORY
    ret
