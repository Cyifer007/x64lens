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
; Current Sprint 2 export:
;   x64lens_phdr_analyze(base, size, summary, regions, max_regions)
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
extern x64lens_bounds_table_extent_valid
extern x64lens_bounds_table_entry_offset
extern x64lens_regions_store_from_phdr

section .text
global x64lens_phdr_analyze

; x64lens_phdr_analyze(base=rdi, file_size=rsi, summary=rdx, regions=rcx, max_regions=r8)
;
; Inputs:
;   RDI = mmap base for an already ELF64-validated target
;   RSI = target file size
;   RDX = writable phdr_summary record
;   RCX = writable executable_region[] buffer
;   R8  = max executable-region records available
;
; Output:
;   RAX = stable x64lens status code
;
; Safety:
;   The program-header table range is revalidated before iteration. Each
;   PT_LOAD file range is validated before the segment contributes to region
;   facts. This duplicate validation is intentional defense-in-depth.
x64lens_phdr_analyze:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56             ; align calls and reserve parser scratch slots

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

    ; PIE baseline: ET_DYN is the common static indicator for PIE executables.
    ; Shared objects are also ET_DYN, so user-facing wording must remain
    ; careful and avoid overclaiming runtime exploitability.
    cmp     word [r15 + E_TYPE], ET_DYN
    jne     .pie_done
    mov     qword [r13 + PHDR_SUMMARY_PIE], 1
.pie_done:

    movzx   rax, word [r15 + E_PHNUM]
    mov     [r13 + PHDR_SUMMARY_PHNUM], rax
    test    rax, rax
    je      .ok                 ; unusual but safely analyzable as no PHDRs

    ; Revalidate the PHDR table before iterating. This duplicates Sprint 1
    ; ELF validation so this module remains safe when reused by future command
    ; paths.
    cmp     word [r15 + E_PHENTSIZE], ELF64_PHDR_SIZE
    jne     .malformed
    mov     rsi, [r15 + E_PHOFF]
    test    rsi, rsi
    je      .malformed
    mov     rdi, r14
    mov     rdx, ELF64_PHDR_SIZE
    mov     rcx, [r13 + PHDR_SUMMARY_PHNUM]
    lea     r8, [rsp]
    call    x64lens_bounds_table_extent_valid
    cmp     rax, 1
    jne     .malformed

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
    lea     rdx, [r15 + rax]    ; RDX = checked Elf64_Dyn pointer
    inc     qword [r13 + PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT]

    mov     rax, [rdx + D_TAG]
    cmp     rax, DT_NULL
    je      .dynamic_null
    cmp     rax, DT_STRTAB
    je      .dynamic_strtab
    cmp     rax, DT_STRSZ
    je      .dynamic_strsz
    cmp     rax, DT_BIND_NOW
    je      .dynamic_bind_now
    cmp     rax, DT_FLAGS
    je      .dynamic_flags
    cmp     rax, DT_FLAGS_1
    je      .dynamic_flags_1
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

.dynamic_bind_now:
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
    jmp     .dynamic_advance

.dynamic_flags:
    mov     rax, [rdx + D_UN]
    test    rax, DF_BIND_NOW
    jz      .dynamic_advance
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
    jmp     .dynamic_advance

.dynamic_flags_1:
    mov     rax, [rdx + D_UN]
    test    rax, DF_1_NOW
    jz      .dynamic_advance
    mov     qword [r13 + PHDR_SUMMARY_BIND_NOW], 1
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
    ; Canary detection is an evidence-qualified bounded dynamic-string scan.
    ; If DT_STRTAB/DT_STRSZ are absent, leave the state unknown rather than
    ; guessing that stack canaries are absent. If both are present, the string
    ; table reference must resolve to a file-backed PT_LOAD range before it is
    ; searched for an exact "__stack_chk_fail" string.
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN], 0
    je      .ok
    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN], 0
    je      .ok

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

    cmp     qword [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ], CANARY_SYMBOL_LEN_WITH_NUL
    jb      .ok

    mov     rax, [rsp + 48]
    lea     rdi, [r15 + rax]
    mov     rsi, [r13 + PHDR_SUMMARY_DYNAMIC_STRSZ]
    call    .scan_canary_string_table
    cmp     rax, 1
    jne     .ok
    mov     qword [r13 + PHDR_SUMMARY_CANARY_STATE], CANARY_STATE_PRESENT
    jmp     .ok

.strtab_next_load:
    inc     rbx
    jmp     .strtab_load_loop

.ok:
    xor     rax, rax
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
    jmp     .done
.unsupported:
    mov     rax, EXIT_UNSUPPORTED
.done:
    add     rsp, 56
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
