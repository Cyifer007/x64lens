; binary_role.asm
;
; Purpose:
;   Classify bounded internal ELF role evidence without changing the public PIE
;   indicator or schema. ET_DYN alone is deliberately insufficient to decide
;   whether an object is a PIE executable or a shared object.
;
; Public symbol:
;   x64lens_binary_role_classify
;
; Inputs and outputs:
;   Consumes the validated ELF64 header and completed phdr_summary raw facts.
;   Writes PHDR_SUMMARY_ROLE_EVIDENCE and PHDR_SUMMARY_ROLE_STATE.
;
; Boundary:
;   This module does not parse ELF tables, select executable regions, scan
;   candidate bytes, classify gadgets, score candidates, or format output. The
;   fact lattice is an internal Sprint 12 evidence seam for later public-policy
;   review.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_binary_role_classify

; x64lens_binary_role_classify(mapped_base=rdi, phdr_summary=rsi) -> rax=status
;
; The lattice preserves unknown, ambiguous, and contradictory states. Duplicate
; singleton-style role evidence is contradictory rather than last-wins.
x64lens_binary_role_classify:
    test    rdi, rdi
    jz      .bounds
    test    rsi, rsi
    jz      .bounds

    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_UNKNOWN
    mov     r11, [rsi + PHDR_SUMMARY_ROLE_EVIDENCE]
    and     r11, ROLE_EVIDENCE_PARSE_MASK

    movzx   eax, word [rdi + E_TYPE]
    cmp     eax, ET_EXEC
    jne     .check_et_dyn
    or      r11, ROLE_EVIDENCE_ET_EXEC
    jmp     .entry_fact
.check_et_dyn:
    cmp     eax, ET_DYN
    jne     .entry_fact
    or      r11, ROLE_EVIDENCE_ET_DYN

.entry_fact:
    cmp     qword [rdi + E_ENTRY], 0
    je      .interp_facts
    or      r11, ROLE_EVIDENCE_ENTRY_NONZERO

.interp_facts:
    mov     rcx, [rsi + PHDR_SUMMARY_PHNUM]
    cmp     rcx, PN_XNUM
    jae     .bounds
    mov     rdx, [rsi + PHDR_SUMMARY_INTERP_COUNT]
    cmp     rdx, rcx
    ja      .bounds
    test    rdx, rdx
    jz      .dynamic_facts
    or      r11, ROLE_EVIDENCE_PT_INTERP
    cmp     rdx, 1
    jbe     .dynamic_facts
    or      r11, ROLE_EVIDENCE_DUP_INTERP

.dynamic_facts:
    mov     rcx, [rsi + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT]

    mov     rdx, [rsi + PHDR_SUMMARY_FLAGS1_COUNT]
    cmp     rdx, rcx
    ja      .bounds
    test    rdx, rdx
    jnz     .flags1_present
    cmp     qword [rsi + PHDR_SUMMARY_FLAGS1_VALUE], 0
    jne     .bounds
    jmp     .soname_facts
.flags1_present:
    cmp     qword [rsi + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .bounds
    cmp     rdx, 1
    jbe     .flags1_value
    or      r11, ROLE_EVIDENCE_DUP_FLAGS1
.flags1_value:
    test    qword [rsi + PHDR_SUMMARY_FLAGS1_VALUE], DF_1_PIE
    jz      .soname_facts
    or      r11, ROLE_EVIDENCE_DF_1_PIE

.soname_facts:
    mov     rdx, [rsi + PHDR_SUMMARY_SONAME_COUNT]
    cmp     rdx, rcx
    ja      .bounds
    test    rdx, rdx
    jnz     .soname_present
    cmp     qword [rsi + PHDR_SUMMARY_SONAME_VALUE], 0
    jne     .bounds
    jmp     .classify
.soname_present:
    cmp     qword [rsi + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    je      .bounds
    test    r11, ROLE_EVIDENCE_DT_SONAME
    jz      .bounds
    cmp     rdx, 1
    jbe     .classify
    or      r11, ROLE_EVIDENCE_DUP_SONAME

.classify:
    mov     [rsi + PHDR_SUMMARY_ROLE_EVIDENCE], r11

    ; Duplicate or conflicting role carriers are explicit contradictory state.
    mov     rax, ROLE_EVIDENCE_DUP_INTERP | ROLE_EVIDENCE_DUP_FLAGS1 | ROLE_EVIDENCE_DUP_SONAME | ROLE_EVIDENCE_CONFLICT_FLAGS1 | ROLE_EVIDENCE_CONFLICT_SONAME
    test    r11, rax
    jnz     .contradictory

    movzx   eax, word [rdi + E_TYPE]
    cmp     eax, ET_EXEC
    je      .classify_exec
    cmp     eax, ET_DYN
    je      .classify_dyn

    ; Role-specific evidence on a non-executable/non-dynamic ELF type is a
    ; contradiction. Absence of such evidence remains unknown.
    mov     rax, ROLE_EVIDENCE_PT_INTERP | ROLE_EVIDENCE_DF_1_PIE | ROLE_EVIDENCE_DT_SONAME
    test    r11, rax
    jnz     .contradictory
    jmp     .unknown

.classify_exec:
    ; ET_EXEC plus a SONAME or DF_1_PIE carrier is contradictory. PT_INTERP is
    ; ordinary executable evidence and a zero entrypoint does not erase ET_EXEC.
    mov     rax, ROLE_EVIDENCE_DF_1_PIE | ROLE_EVIDENCE_DT_SONAME
    test    r11, rax
    jnz     .contradictory
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_EXECUTABLE_LIKE
    jmp     .ok

.classify_dyn:
    mov     r8, r11
    and     r8, ROLE_EVIDENCE_PT_INTERP | ROLE_EVIDENCE_DF_1_PIE
    mov     r9, r11
    and     r9, ROLE_EVIDENCE_DT_SONAME

    test    r8, r8
    jz      .dyn_no_strong_exec
    test    r9, r9
    jnz     .contradictory
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_EXECUTABLE_LIKE
    jmp     .ok

.dyn_no_strong_exec:
    test    r9, r9
    jz      .dyn_no_soname
    test    r11, ROLE_EVIDENCE_ENTRY_NONZERO
    jnz     .ambiguous
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_SHARED_OBJECT_LIKE
    jmp     .ok

.dyn_no_soname:
    test    r11, ROLE_EVIDENCE_ENTRY_NONZERO
    jnz     .ambiguous
    jmp     .unknown

.ambiguous:
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_AMBIGUOUS
    jmp     .ok
.contradictory:
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_CONTRADICTORY
    jmp     .ok
.unknown:
    mov     qword [rsi + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_UNKNOWN
.ok:
    mov     eax, EXIT_OK
    ret
.bounds:
    mov     eax, EXIT_BOUNDS
    ret
