; candidate_mapping.asm
;
; Purpose:
;   Materialize loader-contributor provenance for each retained candidate.
;
; Module scope:
;   Reconcile scanner-owned candidate coordinates with the bounded executable
;   region array produced from PT_LOAD + PF_X program headers.  The result is a
;   dense-region contributor mask stored in candidate_evidence_record[].
;
; Public symbol:
;   x64lens_candidate_mapping_from_regions
;
; Boundary:
;   This module does not parse ELF, choose executable regions, scan bytes,
;   classify candidates, score them, deduplicate overlap observations, or emit
;   reports.  The dense mask is internal provenance for the later Sprint 12
;   overlap-policy decision.  Bit N always means executable-region slot N; the
;   original program-header index remains separately stored in that region.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_candidate_mapping_from_regions

; x64lens_candidate_mapping_from_regions(gadget_summary=rdi,
;                                        gadget_records=rsi,
;                                        phdr_summary=rdx,
;                                        regions=rcx,
;                                        evidence_records=r8) -> rax=status
;
; Inputs:
;   RDI = completed gadget_summary
;   RSI = gadget_record[]
;   RDX = completed phdr_summary
;   RCX = executable_region[]
;   R8  = candidate_evidence_record[] already materialized for the same count
;
; Output:
;   RAX = EXIT_OK or EXIT_BOUNDS for contradictory internal state
;
; Safety:
;   Counts and capacities are rechecked before every dense-array traversal.
;   Candidate and region exclusive ends, plus file-to-virtual translations,
;   are checked for unsigned wrap.  A candidate must retain at least one
;   loader-derived contributor.
;
; Clobbers:
;   Caller-saved registers and CANDIDATE_EVIDENCE_REGION_MASK fields. All
;   System V callee-saved registers are restored.
x64lens_candidate_mapping_from_regions:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    test    rdi, rdi
    jz      .bounds
    test    rsi, rsi
    jz      .bounds
    test    rdx, rdx
    jz      .bounds
    test    rcx, rcx
    jz      .bounds
    test    r8, r8
    jz      .bounds

    mov     r12, rdi            ; gadget_summary
    mov     r13, rsi            ; gadget_record[]
    mov     r14, rdx            ; phdr_summary
    mov     r15, rcx            ; executable_region[]
    mov     rbp, r8             ; candidate_evidence_record[]

    mov     rax, [r12 + GADGET_SUMMARY_CAPACITY]
    cmp     rax, GADGET_RECORD_MAX
    ja      .bounds
    mov     rcx, [r12 + GADGET_SUMMARY_COUNT]
    cmp     rcx, rax
    ja      .bounds
    cmp     rcx, GADGET_RECORD_MAX
    ja      .bounds

    mov     rcx, [r14 + PHDR_SUMMARY_PHNUM]
    cmp     rcx, PN_XNUM
    jae     .bounds
    mov     rax, [r14 + PHDR_SUMMARY_EXEC_COUNT]
    cmp     rax, EXEC_REGION_MAX
    ja      .bounds
    cmp     rax, 64
    ja      .bounds
    cmp     rax, rcx
    ja      .bounds

    ; The executable-region array is retained in original program-header order.
    ; Every original index must be inside the ordinary PHDR table and strictly
    ; increasing. This rejects duplicate or reordered mapping identities before
    ; they can become an ambiguous dense contributor mask.
    xor     rbx, rbx
    mov     r11d, 0xffffffff
.region_index_contract:
    cmp     rbx, [r14 + PHDR_SUMMARY_EXEC_COUNT]
    jae     .region_index_contract_done
    mov     rax, rbx
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    mov     esi, [r15 + rax + EXEC_REGION_PHDR_INDEX]
    cmp     rsi, rcx
    jae     .bounds
    test    rbx, rbx
    jz      .region_index_first
    cmp     esi, r11d
    jbe     .bounds
.region_index_first:
    mov     r11d, esi
    inc     rbx
    jmp     .region_index_contract
.region_index_contract_done:

    ; A valid ELF may have no executable regions and therefore no candidates.
    ; Preserve that historical complete-empty result. Only a nonzero candidate
    ; set requires at least one loader-derived executable contributor.
    cmp     qword [r12 + GADGET_SUMMARY_COUNT], 0
    je      .ok
    cmp     qword [r14 + PHDR_SUMMARY_EXEC_COUNT], 0
    je      .bounds

    xor     rbx, rbx            ; candidate index
.candidate_loop:
    cmp     rbx, [r12 + GADGET_SUMMARY_COUNT]
    jae     .ok

    mov     rax, rbx
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     r9, [r13 + rax]     ; current gadget_record

    mov     rax, rbx
    imul    rax, rax, CANDIDATE_EVIDENCE_RECORD_SIZE
    lea     r10, [rbp + rax]    ; current evidence record

    mov     rdi, [r9 + GADGET_BYTE_START]
    mov     rsi, [r9 + GADGET_BYTE_LEN]
    test    rsi, rsi
    jz      .bounds
    mov     rdx, rdi
    add     rdx, rsi            ; candidate exclusive end
    jc      .bounds

    mov     rcx, [r9 + GADGET_FILE_OFFSET]
    cmp     rcx, rdi
    jb      .bounds
    cmp     rcx, rdx
    jae     .bounds

    xor     r11, r11            ; contributor mask
    xor     r8, r8              ; dense region slot
.region_loop:
    cmp     r8, [r14 + PHDR_SUMMARY_EXEC_COUNT]
    jae     .region_done

    mov     rax, r8
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     rax, [r15 + rax]

    mov     esi, [rax + EXEC_REGION_PHDR_INDEX]
    cmp     esi, PN_XNUM
    jae     .bounds

    mov     rsi, [rax + EXEC_REGION_FILE_OFFSET]
    mov     rdi, [rax + EXEC_REGION_FILESZ]
    add     rdi, rsi            ; region exclusive file end
    jc      .bounds

    mov     rax, [r9 + GADGET_BYTE_START]
    cmp     rax, rsi
    jb      .next_region
    mov     rax, [r9 + GADGET_BYTE_START]
    add     rax, [r9 + GADGET_BYTE_LEN]
    jc      .bounds
    cmp     rax, rdi
    ja      .next_region

    mov     rcx, [r9 + GADGET_FILE_OFFSET]
    cmp     rcx, rsi
    jb      .next_region
    cmp     rcx, rdi
    jae     .next_region
    sub     rcx, rsi

    mov     rax, r8
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     rax, [r15 + rax]
    add     rcx, [rax + EXEC_REGION_VADDR]
    jc      .bounds
    cmp     rcx, [r9 + GADGET_VIRTUAL_ADDRESS]
    jne     .next_region

    bts     r11, r8
.next_region:
    inc     r8
    jmp     .region_loop

.region_done:
    test    r11, r11
    jz      .bounds
    mov     [r10 + CANDIDATE_EVIDENCE_REGION_MASK], r11
    inc     rbx
    jmp     .candidate_loop

.ok:
    mov     eax, EXIT_OK
    jmp     .done
.bounds:
    mov     eax, EXIT_BOUNDS
.done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
