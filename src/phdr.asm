; phdr.asm
;
; Purpose:
;   ELF64 program-header analyzer.
;
; Module scope:
;   Safely iterate validated program headers, derive loader-relevant facts,
;   populate the Sprint 2 mitigation summary, and store executable PT_LOAD
;   regions for later scanner use.
;
; Why program headers matter:
;   Program headers describe what the Linux loader maps into memory. For
;   exploitability analysis, PT_LOAD + PF_X is the authoritative source for
;   executable runtime regions. Section headers remain useful labels later,
;   but they are not runtime mapping authority.
;
; Public module exports:
;   x64lens_phdr_validate_loader_contract(base, size, phnum)
;   x64lens_phdr_analyze(base, size, summary, regions, max_regions, private_metadata_context)
;
; Contract:
;   Do not print, parse CLI arguments, or classify gadgets here. This module
;   produces normalized facts for mitigations.asm, regions.asm, scanners, and
;   reporters.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_bounds_range_end_valid
extern x64lens_bounds_add_u64_checked
extern x64lens_bounds_table_extent_valid
extern x64lens_bounds_table_entry_offset
extern x64lens_regions_store_from_phdr
extern x64lens_gnu_property_context_init
extern x64lens_gnu_property_register_carrier
extern x64lens_gnu_property_parse
extern x64lens_dynamic_metadata_context_init
extern x64lens_dynamic_metadata_record
extern x64lens_dynamic_metadata_resolve_search_path
extern x64lens_dynamic_metadata_finalize

section .text
global x64lens_phdr_validate_loader_contract
global x64lens_phdr_analyze

; x64lens_phdr_validate_loader_contract(base=rdi, file_size=rsi, phnum=rdx)
;   -> rax=status
;
; Validates the ordinary program-header contract shared by ELF identity and
; command-level PHDR analysis. Extended numbering is resolved or rejected by
; elf64.asm before this helper is called.
;
; Validated facts:
;   - the complete fixed-stride program-header table is file-backed;
;   - every p_align is zero, one, or a power of two;
;   - every PT_LOAD has p_filesz <= p_memsz and a bounded file range;
;   - every PT_LOAD virtual range has a non-wrapping exclusive end;
;   - PT_LOAD offset/vaddr congruence holds when p_align > 1; and
;   - a nonzero ELF entrypoint lies inside an executable PT_LOAD memory range.
;
; The entrypoint check uses the half-open loader interval [p_vaddr,
; p_vaddr+p_memsz). Entry at the exclusive end, in a gap, or in a non-executable
; load is malformed. An entrypoint of zero remains an explicit no-entry value.
x64lens_phdr_validate_loader_contract:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 32             ; call alignment and checked-arithmetic scratch

    mov     r15, rdi            ; mapped base
    mov     r14, rsi            ; file size
    mov     r13, rdx            ; ordinary program-header count
    mov     r12, [r15 + E_ENTRY]
    mov     qword [rsp + 16], 0 ; executable-entrypoint match flag

    test    r13, r13
    jnz     .loader_table
    ; A zero program-header count has no table. Requiring e_phoff to be zero
    ; prevents contradictory dormant-table metadata from being accepted by the
    ; shared loader contract.
    cmp     qword [r15 + E_PHOFF], 0
    jne     .loader_malformed
    test    r12, r12
    jnz     .loader_malformed
    xor     rax, rax
    jmp     .loader_done

.loader_table:
    cmp     word [r15 + E_PHENTSIZE], ELF64_PHDR_SIZE
    jne     .loader_malformed
    mov     rsi, [r15 + E_PHOFF]
    test    rsi, rsi
    jz      .loader_malformed
    mov     rdi, r14
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, r13
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .loader_malformed

    xor     rbx, rbx
.loader_loop:
    cmp     rbx, r13
    jae     .loader_entrypoint_result

    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, r13
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .loader_malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    ; ELF p_align is either zero/one (no alignment requirement) or a power of
    ; two. Rejecting the invalid form here keeps later congruence arithmetic
    ; deterministic and bounded.
    mov     rax, [r10 + P_ALIGN]
    cmp     rax, 1
    jbe     .loader_type
    mov     rcx, rax
    dec     rcx
    test    rax, rcx
    jnz     .loader_malformed

.loader_type:
    cmp     dword [r10 + P_TYPE], PT_LOAD
    jne     .loader_next

    mov     rax, [r10 + P_FILESZ]
    cmp     rax, [r10 + P_MEMSZ]
    ja      .loader_malformed

    mov     rdi, r14
    mov     rsi, [r10 + P_OFFSET]
    mov     rdx, [r10 + P_FILESZ]
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .loader_malformed

    ; Re-form the entry pointer after calling a helper because R10 is
    ; caller-saved under the System V ABI.
    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, r13
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .loader_malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    mov     rdi, [r10 + P_VADDR]
    mov     rsi, [r10 + P_MEMSZ]
    lea     rdx, [rsp + 8]
    call    x64lens_bounds_add_u64_checked
    cmp     rax, 1
    jne     .loader_malformed

    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, r13
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .loader_malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    mov     rax, [r10 + P_ALIGN]
    cmp     rax, 1
    jbe     .loader_entry_check
    mov     rcx, rax
    dec     rcx                ; alignment mask
    mov     rax, [r10 + P_OFFSET]
    xor     rax, [r10 + P_VADDR]
    test    rax, rcx
    jnz     .loader_malformed

.loader_entry_check:
    test    r12, r12
    jz      .loader_next
    mov     eax, [r10 + P_FLAGS]
    test    eax, PF_X
    jz      .loader_next
    mov     rax, [r10 + P_VADDR]
    cmp     r12, rax
    jb      .loader_next
    cmp     r12, [rsp + 8]
    jae     .loader_next
    mov     qword [rsp + 16], 1

.loader_next:
    inc     rbx
    jmp     .loader_loop

.loader_entrypoint_result:
    test    r12, r12
    jz      .loader_ok
    cmp     qword [rsp + 16], 1
    jne     .loader_malformed
.loader_ok:
    xor     rax, rax
    jmp     .loader_done
.loader_malformed:
    mov     rax, EXIT_MALFORMED_ELF
.loader_done:
    add     rsp, 32
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; x64lens_phdr_analyze(base=rdi, file_size=rsi, summary=rdx, regions=rcx,
;                        max_regions=r8, private_metadata_context=r9)
;
; Inputs:
;   RDI = mmap base for an already ELF64-validated target
;   RSI = target file size
;   RDX = writable phdr_summary record
;   RCX = writable executable_region[] buffer
;   R8  = max executable-region records available
;   R9  = writable PRIVATE_METADATA_CONTEXT_SIZE command-lifetime buffer
;
; Output:
;   RAX = stable x64lens status code
;
; Clobbers:
;   Caller-saved registers. Callee-saved registers are restored.
;
; Safety:
;   The shared loader contract is revalidated before iteration. Each PT_LOAD
;   file range is also checked at the point where it contributes to region or
;   mitigation facts. This duplicate point-of-use validation is intentional
;   defense-in-depth.
x64lens_phdr_analyze:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 120            ; align calls and reserve parser scratch slots

    mov     [rsp + 56], r9      ; composite private metadata context
    lea     rax, [r9 + PRIVATE_METADATA_DYNAMIC_OFFSET]
    mov     [rsp + 64], rax      ; bounded dynamic-metadata side-car
    mov     r15, rdi            ; mapped base
    mov     r14, rsi            ; file size
    mov     r13, rdx            ; phdr_summary record
    mov     r12, rcx            ; executable_region buffer
    mov     rbp, r8             ; max region records

    ; Initialize all qword fields in the summary record. Keeping the record
    ; deterministic avoids stale values when analysis fails early.
    mov     qword [r13 + PHDR_SUMMARY_PHNUM], 0
    mov     qword [r13 + PHDR_SUMMARY_LOAD_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_EXEC_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_RWX_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_GNU_STACK_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_GNU_STACK_EXEC], 0
    mov     qword [r13 + PHDR_SUMMARY_RELRO_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_PIE], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_NULL_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 0
    mov     qword [r13 + PHDR_SUMMARY_CANARY_STATE], CANARY_STATE_UNKNOWN
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_VADDR], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN], 0
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ], 0
    mov     qword [r13 + PHDR_SUMMARY_STRIPPED_STATE], STRIPPED_STATE_UNKNOWN
    mov     qword [r13 + PHDR_SUMMARY_INTERP_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_FLAGS1_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_FLAGS1_VALUE], 0
    mov     qword [r13 + PHDR_SUMMARY_SONAME_COUNT], 0
    mov     qword [r13 + PHDR_SUMMARY_SONAME_VALUE], 0
    mov     qword [r13 + PHDR_SUMMARY_ROLE_EVIDENCE], 0
    mov     qword [r13 + PHDR_SUMMARY_ROLE_STATE], BINARY_ROLE_UNKNOWN
    movzx   rax, word [r15 + E_TYPE]
    mov     [r13 + PHDR_SUMMARY_ELF_TYPE], rax
    mov     rax, [r15 + E_ENTRY]
    mov     [r13 + PHDR_SUMMARY_ELF_ENTRY], rax

    mov     rdi, [rsp + 56]
    mov     rsi, r13
    call    x64lens_gnu_property_context_init
    test    rax, rax
    jne     .done

    mov     rdi, [rsp + 64]
    call    x64lens_dynamic_metadata_context_init
    test    rax, rax
    jne     .done

    ; PIE baseline: ET_DYN is the common static indicator for PIE executables.
    ; Shared objects are also ET_DYN, so user-facing wording must remain
    ; careful and avoid overclaiming runtime exploitability.
    cmp     word [r15 + E_TYPE], ET_DYN
    jne     .pie_done
    mov     qword [r13 + PHDR_SUMMARY_PIE], 1
.pie_done:

    movzx   rax, word [r15 + E_PHNUM]
    mov     [r13 + PHDR_SUMMARY_PHNUM], rax

    ; Reapply the complete shared loader contract before the zero-PHDR fast
    ; path. This keeps a future direct caller from accepting a nonzero entrypoint
    ; merely because the ELF identity gate was skipped.
    mov     rdi, r15
    mov     rsi, r14
    mov     rdx, [r13 + PHDR_SUMMARY_PHNUM]
    call    x64lens_phdr_validate_loader_contract
    test    rax, rax
    jne     .done
    cmp     qword [r13 + PHDR_SUMMARY_PHNUM], 0
    je      .finalize_dynamic_metadata ; zero PHDRs imply empty private metadata views

    xor     rbx, rbx            ; program-header index
.loop:
    cmp     rbx, [r13 + PHDR_SUMMARY_PHNUM]
    jae     .finalize_dynamic_metadata

    ; R10 = current program header pointer. The helper validates the
    ; index, checked index-times-stride arithmetic, checked table offset
    ; addition, and the final per-entry byte range before we form a pointer.
    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, [r13 + PHDR_SUMMARY_PHNUM]
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    mov     eax, [r10 + P_TYPE]
    cmp     eax, PT_LOAD
    je      .handle_load
    cmp     eax, PT_GNU_STACK
    je      .handle_gnu_stack
    cmp     eax, PT_GNU_RELRO
    je      .handle_gnu_relro
    cmp     eax, PT_DYNAMIC
    je      .handle_dynamic
    cmp     eax, PT_INTERP
    je      .handle_interp
    cmp     eax, PT_NOTE
    je      .handle_property_carrier
    cmp     eax, PT_GNU_PROPERTY
    je      .handle_property_carrier
    jmp     .next

.handle_load:
    inc     qword [r13 + PHDR_SUMMARY_LOAD_COUNT]

    ; Validate that p_filesz does not exceed p_memsz and that the file-backed
    ; part of the segment stays inside the mapped file.
    mov     rax, [r10 + P_FILESZ]
    cmp     rax, [r10 + P_MEMSZ]
    ja      .malformed

    mov     rdi, r14
    mov     rsi, [r10 + P_OFFSET]
    mov     rdx, [r10 + P_FILESZ]
    lea     rcx, [rsp + 8]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .malformed

    ; Recompute R10 after the helper call to avoid relying on caller-saved
    ; registers across module boundaries.
    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, [r13 + PHDR_SUMMARY_PHNUM]
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    mov     eax, [r10 + P_FLAGS]
    mov     ecx, eax
    and     ecx, PF_W | PF_X
    cmp     ecx, PF_W | PF_X
    jne     .check_exec
    inc     qword [r13 + PHDR_SUMMARY_RWX_COUNT]

.check_exec:
    test    eax, PF_X
    jz      .next

    ; Store executable region if capacity allows. Silent truncation would
    ; corrupt later scanner and benchmark results, so fail explicitly instead.
    mov     rax, [r13 + PHDR_SUMMARY_EXEC_COUNT]
    cmp     rax, rbp
    jae     .unsupported

    mov     rdi, r12
    mov     rsi, rax
    mov     rdx, r10
    mov     rcx, rbx            ; preserve original PHDR table index
    call    x64lens_regions_store_from_phdr
    inc     qword [r13 + PHDR_SUMMARY_EXEC_COUNT]
    jmp     .next

.handle_gnu_stack:
    mov     qword [r13 + PHDR_SUMMARY_GNU_STACK_SEEN], 1
    mov     eax, [r10 + P_FLAGS]
    test    eax, PF_X
    jz      .next
    mov     qword [r13 + PHDR_SUMMARY_GNU_STACK_EXEC], 1
    jmp     .next

.handle_gnu_relro:
    mov     qword [r13 + PHDR_SUMMARY_RELRO_SEEN], 1
    jmp     .next

.handle_interp:
    ; PT_INTERP is bounded role evidence. The path must be a nonempty,
    ; file-backed, NUL-terminated byte string within the implementation cap.
    ; More than one carrier is retained as contradictory role evidence rather
    ; than silently applying first- or last-wins semantics.
    mov     rax, [r10 + P_FILESZ]
    test    rax, rax
    jz      .malformed
    cmp     rax, [r10 + P_MEMSZ]
    ja      .malformed
    cmp     rax, INTERP_PATH_SCAN_MAX
    ja      .unsupported
    mov     [rsp + 48], rax
    mov     rax, [r10 + P_OFFSET]
    mov     [rsp + 40], rax

    mov     rdi, r14
    mov     rsi, [rsp + 40]
    mov     rdx, [rsp + 48]
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .malformed

    mov     rax, [rsp + 40]
    lea     rdx, [r15 + rax]    ; bounded interpreter bytes
    cmp     byte [rdx], 0       ; reject NUL-only/empty represented path
    je      .malformed
    mov     rcx, [rsp + 48]
    dec     rcx
    cmp     byte [rdx + rcx], 0
    jne     .malformed
    xor     r8, r8
.interp_interior_loop:
    cmp     r8, rcx
    jae     .interp_valid
    cmp     byte [rdx + r8], 0
    je      .malformed
    inc     r8
    jmp     .interp_interior_loop
.interp_valid:
    inc     qword [r13 + PHDR_SUMMARY_INTERP_COUNT]
    jmp     .next

.handle_property_carrier:
    ; PT_NOTE and PT_GNU_PROPERTY are bounded metadata carriers. Exact duplicate
    ; physical ranges share one canonical view while each original PHDR index
    ; remains visible through a contributor record.
    mov     rdi, r15
    mov     rsi, r14
    mov     rdx, [rsp + 56]
    mov     rcx, rbx
    mov     r8, r10
    call    x64lens_gnu_property_register_carrier
    test    rax, rax
    jne     .done
    jmp     .next

.handle_dynamic:
    ; A conforming executable should expose at most one PT_DYNAMIC table.
    ; Accepting several tables would make dynamic-entry and DT_NULL semantics
    ; ambiguous, so fail closed instead of merging partial evidence.
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_SEEN], 0
    jne     .malformed
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_SEEN], 1

    ; PT_DYNAMIC is a file-backed table of Elf64_Dyn entries. Treat it as an
    ; untrusted bounded table: validate p_filesz <= p_memsz, validate the file
    ; range, require an integral entry count, then walk only entries inside the
    ; checked extent. This establishes the Sprint 8 dynamic-table view without
    ; letting dynamic metadata override loader-authoritative PT_LOAD facts.
    mov     rax, [r10 + P_FILESZ]
    cmp     rax, [r10 + P_MEMSZ]
    ja      .malformed

    mov     rdi, r14
    mov     rsi, [r10 + P_OFFSET]
    mov     rdx, [r10 + P_FILESZ]
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .malformed

    ; Recompute R10 after the helper call; callers must not assume helper
    ; preservation of volatile registers.
    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, [r13 + PHDR_SUMMARY_PHNUM]
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    mov     rax, [r10 + P_FILESZ]
    test    rax, 0xf            ; p_filesz must be a multiple of 16-byte Elf64_Dyn records
    jne     .malformed
    mov     rcx, rax
    shr     rcx, 4              ; rcx = p_filesz / sizeof(Elf64_Dyn)
    cmp     rcx, DYNAMIC_ENTRY_MAX
    ja      .unsupported
    mov     [rsp + 24], rcx     ; bounded dynamic-entry count
    mov     rax, [r10 + P_OFFSET]
    mov     [rsp + 16], rax     ; dynamic table file offset
    mov     qword [rsp + 32], 0 ; dynamic-entry index

.dynamic_loop:
    mov     rax, [rsp + 32]
    cmp     rax, [rsp + 24]
    jae     .next

    mov     rdi, r14
    mov     rsi, [rsp + 16]
    mov     rdx, ELF64_DYN_SIZE
    mov     rcx, [rsp + 24]
    mov     r8, [rsp + 32]
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed

    mov     rax, [rsp]
    mov     [rsp + 72], rax     ; checked dynamic-entry file offset
    lea     rdx, [r15 + rax]    ; RDX = checked Elf64_Dyn pointer
    inc     qword [r13 + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT]

    mov     rax, [rdx + D_TAG]
    cmp     rax, DT_NULL
    je      .dynamic_null
    cmp     rax, DT_STRTAB
    je      .dynamic_strtab
    cmp     rax, DT_STRSZ
    je      .dynamic_strsz
    cmp     rax, DT_TEXTREL
    je      .dynamic_textrel
    cmp     rax, DT_BIND_NOW
    je      .dynamic_bind_now
    cmp     rax, DT_FLAGS
    je      .dynamic_flags
    cmp     rax, DT_FLAGS_1
    je      .dynamic_flags_1
    cmp     rax, DT_SONAME
    je      .dynamic_soname
    cmp     rax, DT_RPATH
    je      .dynamic_rpath
    cmp     rax, DT_RUNPATH
    je      .dynamic_runpath
    jmp     .dynamic_advance

.dynamic_strtab:
    ; DT_STRTAB is singleton evidence for the bounded dynamic string table.
    ; Accepting several values would make canary evidence order-dependent, so
    ; reject duplicates as malformed instead of applying last-wins semantics.
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN], 0
    jne     .malformed
    mov     rax, [rdx + D_UN]
    mov     [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_VADDR], rax
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN], 1
    jmp     .dynamic_advance

.dynamic_strsz:
    ; DT_STRSZ is also singleton evidence. Duplicate sizes can change a
    ; canary-present result into canary-absent or vice versa, so fail closed.
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN], 0
    jne     .malformed
    mov     rax, [rdx + D_UN]
    mov     [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ], rax
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN], 1
    jmp     .dynamic_advance

.dynamic_textrel:
    mov     r8, [rdx + D_UN]
    mov     rdi, [rsp + 64]
    mov     rsi, DT_TEXTREL
    mov     rdx, [rsp + 32]
    mov     rcx, [rsp + 72]
    call    x64lens_dynamic_metadata_record
    test    rax, rax
    jne     .done
    jmp     .dynamic_advance

.dynamic_bind_now:
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
    jmp     .dynamic_advance

.dynamic_flags:
    mov     r8, [rdx + D_UN]
    mov     [rsp + 80], r8
    mov     rdi, [rsp + 64]
    mov     rsi, DT_FLAGS
    mov     rdx, [rsp + 32]
    mov     rcx, [rsp + 72]
    call    x64lens_dynamic_metadata_record
    test    rax, rax
    jne     .done
    mov     rax, [rsp + 80]
    test    rax, DF_BIND_NOW
    jz      .dynamic_advance
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
    jmp     .dynamic_advance

.dynamic_flags_1:
    mov     rax, [rdx + D_UN]
    cmp     qword [r13 + PHDR_SUMMARY_FLAGS1_COUNT], 0
    je      .dynamic_flags_1_first
    cmp     [r13 + PHDR_SUMMARY_FLAGS1_VALUE], rax
    je      .dynamic_flags_1_accumulate
    or      qword [r13 + PHDR_SUMMARY_ROLE_EVIDENCE], ROLE_EVIDENCE_CONFLICT_FLAGS1
.dynamic_flags_1_accumulate:
    or      [r13 + PHDR_SUMMARY_FLAGS1_VALUE], rax
    jmp     .dynamic_flags_1_count
.dynamic_flags_1_first:
    mov     [r13 + PHDR_SUMMARY_FLAGS1_VALUE], rax
.dynamic_flags_1_count:
    inc     qword [r13 + PHDR_SUMMARY_FLAGS1_COUNT]
    test    rax, DF_1_NOW
    jz      .dynamic_advance
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
    jmp     .dynamic_advance


.dynamic_rpath:
    mov     r8, [rdx + D_UN]
    mov     rdi, [rsp + 64]
    mov     rsi, DT_RPATH
    mov     rdx, [rsp + 32]
    mov     rcx, [rsp + 72]
    call    x64lens_dynamic_metadata_record
    test    rax, rax
    jne     .done
    jmp     .dynamic_advance

.dynamic_runpath:
    mov     r8, [rdx + D_UN]
    mov     rdi, [rsp + 64]
    mov     rsi, DT_RUNPATH
    mov     rdx, [rsp + 32]
    mov     rcx, [rsp + 72]
    call    x64lens_dynamic_metadata_record
    test    rax, rax
    jne     .done
    jmp     .dynamic_advance

.dynamic_soname:
    mov     rax, [rdx + D_UN]
    cmp     qword [r13 + PHDR_SUMMARY_SONAME_COUNT], 0
    je      .dynamic_soname_first
    cmp     [r13 + PHDR_SUMMARY_SONAME_VALUE], rax
    je      .dynamic_soname_count
    or      qword [r13 + PHDR_SUMMARY_ROLE_EVIDENCE], ROLE_EVIDENCE_CONFLICT_SONAME
    jmp     .dynamic_soname_count
.dynamic_soname_first:
    mov     [r13 + PHDR_SUMMARY_SONAME_VALUE], rax
.dynamic_soname_count:
    inc     qword [r13 + PHDR_SUMMARY_SONAME_COUNT]
    jmp     .dynamic_advance

.dynamic_null:
    mov     qword [r13 + PHDR_SUMMARY_DYNAMIC_NULL_SEEN], 1
    jmp     .next

.dynamic_advance:
    inc     qword [rsp + 32]
    jmp     .dynamic_loop

.next:
    inc     rbx
    jmp     .loop

.finalize_dynamic_metadata:
    mov     rdi, [rsp + 64]
    mov     rsi, r13
    call    x64lens_dynamic_metadata_finalize
    test    rax, rax
    jne     .done

    ; Canary detection is an evidence-qualified bounded dynamic-string scan.
    ; If DT_STRTAB/DT_STRSZ are absent, leave the state unknown rather than
    ; guessing that stack canaries are absent. If both are present, the string
    ; table reference must resolve to a file-backed PT_LOAD range before it is
    ; searched for an exact "__stack_chk_fail" string.
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN], 0
    jne     .dynamic_strtab_present
    cmp     qword [r13 + PHDR_SUMMARY_SONAME_COUNT], 0
    jne     .malformed
    mov     rax, [rsp + 64]
    cmp     qword [rax + DYNAMIC_METADATA_CTX_RPATH_CARRIER_COUNT], 0
    jne     .malformed
    cmp     qword [rax + DYNAMIC_METADATA_CTX_RUNPATH_CARRIER_COUNT], 0
    jne     .malformed
    jmp     .refinalize_dynamic_metadata
.dynamic_strtab_present:
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN], 0
    jne     .dynamic_string_table_present
    cmp     qword [r13 + PHDR_SUMMARY_SONAME_COUNT], 0
    jne     .malformed
    mov     rax, [rsp + 64]
    cmp     qword [rax + DYNAMIC_METADATA_CTX_RPATH_CARRIER_COUNT], 0
    jne     .malformed
    cmp     qword [rax + DYNAMIC_METADATA_CTX_RUNPATH_CARRIER_COUNT], 0
    jne     .malformed
    jmp     .refinalize_dynamic_metadata
.dynamic_string_table_present:

    mov     rax, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    cmp     rax, DYNAMIC_STRING_SCAN_MAX
    ja      .unsupported

    ; Reaching this point means both DT_STRTAB and DT_STRSZ were present and
    ; bounded. Even a zero-length string table is now validated negative
    ; evidence, so it is classified as absent rather than unknown.
    mov     qword [r13 + PHDR_SUMMARY_CANARY_STATE], CANARY_STATE_ABSENT

    xor     rbx, rbx
.strtab_load_loop:
    cmp     rbx, [r13 + PHDR_SUMMARY_PHNUM]
    jae     .malformed

    mov     rdi, r14
    mov     rsi, [r15 + E_PHOFF]
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, [r13 + PHDR_SUMMARY_PHNUM]
    mov     r8, rbx
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed
    mov     rax, [rsp]
    lea     r10, [r15 + rax]

    cmp     dword [r10 + P_TYPE], PT_LOAD
    jne     .strtab_next_load

    mov     rax, [r10 + P_FILESZ]
    cmp     rax, [r10 + P_MEMSZ]
    ja      .malformed

    mov     rax, [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_VADDR]
    mov     rcx, [r10 + P_VADDR]
    cmp     rax, rcx
    jb      .strtab_next_load
    sub     rax, rcx            ; RAX = strtab offset inside this LOAD mapping
    cmp     rax, [r10 + P_FILESZ]
    ja      .strtab_next_load

    mov     rcx, [r10 + P_FILESZ]
    sub     rcx, rax            ; bytes remaining in file-backed LOAD range
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ], rcx
    ja      .strtab_next_load

    mov     rcx, [r10 + P_OFFSET]
    add     rcx, rax            ; RCX = translated dynamic string-table file offset
    jc      .malformed
    mov     [rsp + 48], rcx

    mov     rdi, r14
    mov     rsi, rcx
    mov     rdx, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    lea     rcx, [rsp]
    call    x64lens_bounds_range_end_valid
    cmp     rax, 1
    jne     .malformed

    ; Resolve every represented dynamic-string carrier from the same checked
    ; DT_STRTAB/DT_STRSZ view. SONAME remains nonempty role evidence. RPATH and
    ; RUNPATH preserve exact bytes separately and never trigger path-derived I/O.
    mov     qword [rsp + 88], 0
.dynamic_string_second_pass:
    mov     rax, [rsp + 88]
    cmp     rax, [rsp + 24]
    jae     .dynamic_string_second_done
    mov     rdi, r14
    mov     rsi, [rsp + 16]
    mov     rdx, ELF64_DYN_SIZE
    mov     rcx, [rsp + 24]
    mov     r8, rax
    lea     r9, [rsp]
    call    x64lens_bounds_table_entry_offset
    cmp     rax, 1
    jne     .malformed
    mov     rax, [rsp]
    mov     [rsp + 72], rax
    lea     rdx, [r15 + rax]
    mov     rax, [rdx + D_TAG]
    cmp     rax, DT_NULL
    je      .dynamic_string_second_done
    cmp     rax, DT_SONAME
    je      .dynamic_string_soname
    cmp     rax, DT_RPATH
    je      .dynamic_string_rpath
    cmp     rax, DT_RUNPATH
    je      .dynamic_string_runpath
    jmp     .dynamic_string_second_advance

.dynamic_string_soname:
    mov     rax, [rdx + D_UN]
    cmp     rax, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    jae     .malformed
    mov     rcx, [rsp + 48]
    add     rcx, rax
    jc      .malformed
    lea     rdx, [r15 + rcx]
    cmp     byte [rdx], 0
    je      .malformed
    mov     rcx, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    sub     rcx, rax
    xor     r8, r8
.dynamic_string_soname_terminator:
    cmp     r8, rcx
    jae     .malformed
    cmp     byte [rdx + r8], 0
    je      .dynamic_string_second_advance
    inc     r8
    jmp     .dynamic_string_soname_terminator

.dynamic_string_rpath:
    mov     rsi, DT_RPATH
    jmp     .dynamic_string_search_path
.dynamic_string_runpath:
    mov     rsi, DT_RUNPATH
.dynamic_string_search_path:
    ; An unterminated dynamic table keeps path state unknown. Raw carriers stay
    ; retained, but no value is promoted from incomplete table evidence.
    mov     rdi, [rsp + 64]
    cmp     qword [rdi + DYNAMIC_METADATA_CTX_TABLE_COMPLETE], 1
    jne     .dynamic_string_second_advance
    mov     rax, [rdx + D_UN]
    cmp     rax, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    jae     .malformed
    mov     rcx, [rsp + 48]
    add     rcx, rax
    jc      .malformed
    lea     r8, [r15 + rcx]
    mov     r9, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    sub     r9, rax
    mov     rdx, [rsp + 88]
    call    x64lens_dynamic_metadata_resolve_search_path
    test    rax, rax
    jne     .done

.dynamic_string_second_advance:
    inc     qword [rsp + 88]
    jmp     .dynamic_string_second_pass
.dynamic_string_second_done:
    cmp     qword [r13 + PHDR_SUMMARY_SONAME_COUNT], 0
    je      .canary_string_scan
    or      qword [r13 + PHDR_SUMMARY_ROLE_EVIDENCE], ROLE_EVIDENCE_DT_SONAME

.canary_string_scan:
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ], CANARY_SYMBOL_LEN_WITH_NUL
    jb      .refinalize_dynamic_metadata

    mov     rax, [rsp + 48]
    lea     rdi, [r15 + rax]
    mov     rsi, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    call    .scan_canary_string_table
    cmp     rax, 1
    jne     .refinalize_dynamic_metadata
    mov     qword [r13 + PHDR_SUMMARY_CANARY_STATE], CANARY_STATE_PRESENT
    jmp     .refinalize_dynamic_metadata

.strtab_next_load:
    inc     rbx
    jmp     .strtab_load_loop

.refinalize_dynamic_metadata:
    mov     rdi, [rsp + 64]
    mov     rsi, r13
    call    x64lens_dynamic_metadata_finalize
    test    rax, rax
    jne     .done

.finalize_gnu_property:
    mov     rdi, r15
    mov     rsi, r14
    mov     rdx, [rsp + 56]
    mov     rcx, r13
    call    x64lens_gnu_property_parse
    test    rax, rax
    jne     .done
.ok:
    xor     rax, rax
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
    jmp     .done
.unsupported:
    mov     rax, EXIT_UNSUPPORTED
.done:
    add     rsp, 120
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; scan_canary_string_table(ptr=rdi, len=rsi) -> rax=1 if the bounded string
; table contains the exact null-terminated symbol "__stack_chk_fail".
; Caller guarantees that at least len bytes are file-backed and mapped.
.scan_canary_string_table:
    cmp     rsi, CANARY_SYMBOL_LEN_WITH_NUL
    jb      .scan_not_found
    mov     r8, rdi
    mov     r9, rsi
    sub     r9, CANARY_SYMBOL_LEN_WITH_NUL
    xor     rcx, rcx
.scan_loop:
    cmp     rcx, r9
    ja      .scan_not_found
    test    rcx, rcx
    jz      .scan_match_start_ok
    cmp     byte [r8 + rcx - 1], 0
    jne     .scan_next
.scan_match_start_ok:
    mov     rax, 0x5f6b636174735f5f ; "__stack_" little-endian
    cmp     qword [r8 + rcx], rax
    jne     .scan_next
    mov     rax, 0x6c6961665f6b6863 ; "chk_fail" little-endian
    cmp     qword [r8 + rcx + 8], rax
    jne     .scan_next
    cmp     byte [r8 + rcx + 16], 0
    je      .scan_found
.scan_next:
    inc     rcx
    jmp     .scan_loop
.scan_found:
    mov     rax, 1
    ret
.scan_not_found:
    xor     rax, rax
    ret
