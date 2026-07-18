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
    db 0                      ; multi-pop length is derived from ordered metadata
    db 4                      ; REX.W + mov r64,r64 + ret
    db 5                      ; add rsp, imm8; ret
    db 4                      ; REX.W + mov [base],value + ret
    db 4                      ; REX.W + mov value,[base] + ret

; Indexed by PATTERN_* ID. Values are canonical register IDs for the single-pop
; family and 0xff for patterns that do not carry one ordered pop register.
pattern_single_pop_regs:
    db 0xff, 0xff, 0xff
    db REG_RAX_BIT, REG_RCX_BIT, REG_RDX_BIT, REG_RBX_BIT
    db REG_RSP_BIT, REG_RBP_BIT, REG_RSI_BIT, REG_RDI_BIT
    db REG_R8_BIT, REG_R9_BIT, REG_R10_BIT, REG_R11_BIT
    db REG_R12_BIT, REG_R13_BIT, REG_R14_BIT, REG_R15_BIT
    db 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff

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
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    ja      .bounds_error
    cmp     eax, PATTERN_MULTI_POP_RET
    je      .multi_pop_suffix_length
    cmp     eax, PATTERN_MOV_REG_REG_RET
    je      .register_transfer_suffix_length
    cmp     eax, PATTERN_MOV_MEM_REG_RET
    je      .memory_suffix_length
    cmp     eax, PATTERN_MOV_REG_MEM_RET
    je      .memory_suffix_length

    cmp     eax, PATTERN_POP_RAX_RET
    jb      .require_no_pop_metadata
    cmp     eax, PATTERN_POP_R15_RET
    jbe     .require_single_pop_metadata

.require_no_pop_metadata:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 0
    jne     .bounds_error
    cmp     dword [r12 + GADGET_PATTERN_REG_ORDER], 0
    jne     .bounds_error
    jmp     .static_suffix_length

.require_single_pop_metadata:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 1
    jne     .bounds_error
    lea     rdx, [rel pattern_single_pop_regs]
    movzx   edx, byte [rdx + rax]
    cmp     edx, 0xff
    je      .bounds_error
    cmp     dword [r12 + GADGET_PATTERN_REG_ORDER], edx
    jne     .bounds_error

.static_suffix_length:
    lea     rdx, [rel pattern_suffix_lengths]
    movzx   ecx, byte [rdx + rax]
    test    ecx, ecx
    jz      .bounds_error
    jmp     .suffix_length_ready

.multi_pop_suffix_length:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     edi, [r12 + GADGET_PATTERN_REG_ORDER]
    test    edi, 0xffffff00
    jne     .bounds_error
    mov     eax, edi
    and     eax, 0x0f
    shr     edi, 4
    and     edi, 0x0f
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     edi, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, edi
    je      .bounds_error
    mov     edx, ARG_CONTROL_REG_MASK
    bt      edx, eax
    jnc     .bounds_error
    bt      edx, edi
    jnc     .bounds_error

    ; One byte for ret plus one byte per legacy pop or two bytes per REX.B pop.
    mov     ecx, 3
    cmp     eax, REG_R8_BIT
    jb      .multi_first_done
    inc     ecx
.multi_first_done:
    cmp     edi, REG_R8_BIT
    jb      .suffix_length_ready
    inc     ecx
    jmp     .suffix_length_ready

.register_transfer_suffix_length:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     edi, [r12 + GADGET_PATTERN_REG_ORDER]
    test    edi, 0xffffff00
    jne     .bounds_error
    mov     eax, edi
    and     eax, 0x0f           ; destination
    shr     edi, 4
    and     edi, 0x0f           ; source
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     edi, REG_R15_BIT
    ja      .bounds_error
    cmp     eax, edi
    je      .bounds_error
    cmp     eax, REG_RSP_BIT
    je      .bounds_error
    cmp     edi, REG_RSP_BIT
    je      .bounds_error
    mov     ecx, 4
    jmp     .suffix_length_ready

.memory_suffix_length:
    cmp     dword [r12 + GADGET_PATTERN_REG_COUNT], 2
    jne     .bounds_error
    mov     edi, [r12 + GADGET_PATTERN_REG_ORDER]
    test    edi, 0xffffff00
    jne     .bounds_error
    mov     eax, edi
    and     eax, 0x0f           ; base
    shr     edi, 4
    and     edi, 0x0f           ; value
    cmp     eax, REG_R15_BIT
    ja      .bounds_error
    cmp     edi, REG_R15_BIT
    ja      .bounds_error
    cmp     edi, REG_RSP_BIT
    je      .bounds_error
    cmp     eax, REG_RSP_BIT
    je      .bounds_error
    cmp     eax, REG_RBP_BIT
    je      .bounds_error
    cmp     eax, REG_R12_BIT
    je      .bounds_error
    cmp     eax, REG_R13_BIT
    je      .bounds_error
    mov     ecx, 4
    jmp     .suffix_length_ready

.suffix_length_ready:
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
