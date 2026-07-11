; candidate_evidence.asm
;
; Purpose:
;   Materialize per-candidate evidence provenance into a fixed-size side-car.
;
; Module scope:
;   Consume completed raw gadget records plus exact-pattern and semantic facts,
;   then populate candidate_evidence_record[] using the same candidate index.
;   This module does not map files, scan bytes, classify primitives, score
;   candidates, annotate sections, decode instructions, or emit reports.
;
; Public symbols:
;   x64lens_candidate_evidence_from_exact
;
; Sprint 9 scope:
;   Preserve raw candidate evidence for every record, identify exact suffix
;   evidence and its offset/length, identify semantic-exact promotion, record a
;   stable validator identity, and keep full-sequence validity explicitly
;   unknown. Future decoder work must add evidence without erasing these facts.

bits 64
default rel

%include "errors.inc"
%include "structs.inc"

section .rodata
; Indexed by PATTERN_* ID. Entry 0 is PATTERN_UNKNOWN. Lengths describe the
; recognized suffix ending at the return terminator, not the complete raw
; backward window retained by scanner.asm.
pattern_suffix_lengths:
    db 0                      ; unknown
    db 1                      ; ret
    db 3                      ; ret imm16
    db 2, 2, 2, 2, 2, 2, 2, 2 ; pop rax..rdi; ret
    db 3, 3, 3, 3, 3, 3, 3, 3 ; pop r8..r15; ret
    db 2                      ; leave; ret
    db 3                      ; syscall; ret

section .text
global x64lens_candidate_evidence_from_exact

; x64lens_candidate_evidence_from_exact(gadget_summary=rdi,
;                                       gadget_records=rsi,
;                                       evidence_records=rdx) -> rax=status
;
; Inputs:
;   RDI = completed gadget_summary
;   RSI = gadget_record[] populated through classifier.asm
;   RDX = writable candidate_evidence_record[] with matching capacity
;
; Output:
;   RAX = EXIT_OK or EXIT_BOUNDS on contradictory internal state
;
; Clobbers:
;   Caller-saved registers and the populated candidate_evidence_record[] array.
;   All System V callee-saved registers are restored before return.
;
; Safety assumptions:
;   The command allocated both dense arrays for GADGET_RECORD_MAX entries and
;   the summary count/capacity passed the scanner's established bounds checks.
;   This routine rechecks count/capacity and every derived suffix range before
;   writing provenance.
x64lens_candidate_evidence_from_exact:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    test    rdi, rdi
    jz      .bounds_error
    test    rsi, rsi
    jz      .bounds_error
    test    rdx, rdx
    jz      .bounds_error

    mov     r13, rdi            ; gadget_summary
    mov     r14, rsi            ; gadget_record[]
    mov     r15, rdx            ; candidate_evidence_record[]

    mov     rax, [r13 + GADGET_SUMMARY_COUNT]
    cmp     rax, [r13 + GADGET_SUMMARY_CAPACITY]
    ja      .bounds_error
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds_error

    xor     rbp, rbp
    xor     r8, r8             ; observed unknown semantic count
    xor     r10, r10           ; observed exact-pattern count
    xor     r11, r11           ; observed semantic count
.loop:
    cmp     rbp, [r13 + GADGET_SUMMARY_COUNT]
    jae     .ok

    mov     rax, rbp
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r12, [r14 + rax]

    mov     rax, rbp
    imul    rax, rax, CANDIDATE_EVIDENCE_RECORD_SIZE
    lea     rbx, [r15 + rax]

    ; Deterministic raw-only baseline. Exact and semantic evidence are promoted
    ; below only when the corresponding upstream facts are internally valid.
    mov     qword [rbx + CANDIDATE_EVIDENCE_FLAGS], EVIDENCE_FLAG_RAW_CANDIDATE
    mov     qword [rbx + CANDIDATE_EVIDENCE_SEMANTIC_SOURCE], EVIDENCE_SEMANTIC_SOURCE_NONE
    mov     qword [rbx + CANDIDATE_EVIDENCE_VALIDATOR_ID], EVIDENCE_VALIDATOR_RAW_SCANNER
    mov     qword [rbx + CANDIDATE_EVIDENCE_FULL_SEQUENCE_STATE], EVIDENCE_FULL_SEQUENCE_UNKNOWN
    mov     qword [rbx + CANDIDATE_EVIDENCE_SUFFIX_OFFSET], 0
    mov     qword [rbx + CANDIDATE_EVIDENCE_SUFFIX_LENGTH], 0

    mov     eax, [r12 + GADGET_PATTERN_ID]
    test    eax, eax
    jz      .require_unknown_semantic
    cmp     eax, PATTERN_SYSCALL_RET
    ja      .bounds_error

    lea     rdx, [rel pattern_suffix_lengths]
    movzx   ecx, byte [rdx + rax]
    test    ecx, ecx
    jz      .bounds_error

    mov     rdx, [r12 + GADGET_BYTE_LEN]
    cmp     rdx, rcx
    jb      .bounds_error
    sub     rdx, rcx

    inc     r10
    or      qword [rbx + CANDIDATE_EVIDENCE_FLAGS], EVIDENCE_FLAG_EXACT_SUFFIX
    mov     qword [rbx + CANDIDATE_EVIDENCE_VALIDATOR_ID], EVIDENCE_VALIDATOR_EXACT_SUFFIX
    mov     [rbx + CANDIDATE_EVIDENCE_SUFFIX_OFFSET], rdx
    mov     [rbx + CANDIDATE_EVIDENCE_SUFFIX_LENGTH], rcx

    mov     eax, [r12 + GADGET_SEMANTIC_CLASS]
    cmp     eax, SEM_UNKNOWN_CANDIDATE
    je      .known_pattern_unknown_semantic
    cmp     eax, SEM_CLOBBER_HEAVY
    ja      .bounds_error
    inc     r11
    or      qword [rbx + CANDIDATE_EVIDENCE_FLAGS], EVIDENCE_FLAG_SEMANTIC_EXACT
    mov     qword [rbx + CANDIDATE_EVIDENCE_SEMANTIC_SOURCE], EVIDENCE_SEMANTIC_SOURCE_EXACT
    jmp     .next

.known_pattern_unknown_semantic:
    inc     r8
    jmp     .next

.require_unknown_semantic:
    cmp     dword [r12 + GADGET_SEMANTIC_CLASS], SEM_UNKNOWN_CANDIDATE
    jne     .bounds_error
    inc     r8

.next:
    inc     rbp
    jmp     .loop

.ok:
    cmp     r10, [r13 + GADGET_SUMMARY_PATTERN_COUNT]
    jne     .bounds_error
    cmp     r11, [r13 + GADGET_SUMMARY_SEMANTIC_COUNT]
    jne     .bounds_error
    cmp     r8, [r13 + GADGET_SUMMARY_UNKNOWN_COUNT]
    jne     .bounds_error
    mov     rax, r11
    add     rax, r8
    jc      .bounds_error
    cmp     rax, [r13 + GADGET_SUMMARY_COUNT]
    jne     .bounds_error

    xor     eax, eax
    jmp     .done

.bounds_error:
    mov     eax, EXIT_BOUNDS

.done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
