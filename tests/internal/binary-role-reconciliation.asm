; binary-role-reconciliation.asm
;
; Purpose:
;   Validate the private Sprint 12 PIE/DSO role-evidence lattice and its bounded
;   PT_INTERP, DT_FLAGS_1, and DT_SONAME acquisition paths.
;
; Scope:
;   The harness proves all five internal states, duplicate/conflict behavior,
;   bounded SONAME string evidence, malformed and unsupported interpreter paths,
;   and the fixed summary growth. It changes no public text or JSON output.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_phdr_analyze
extern x64lens_binary_role_classify
global _start

%define IMAGE_SIZE 1024
%define PH0 64
%define PH1 (PH0 + ELF64_PHDR_SIZE)
%define PH2 (PH1 + ELF64_PHDR_SIZE)
%define INTERP_OFF 704
%define DYNAMIC_OFF 768
%define STRTAB_OFF 896
%define STRTAB_SIZE 32

%if PHDR_SUMMARY_RECORD_SIZE != 264
    %error "Patch 065 binary-role and GNU-property facts require a 264-byte phdr_summary"
%endif

section .rodata
ok_message: db "sprint12-binary-role-smoke: ok cases=21 states=5 malformed=7 unsupported=1 summary_bytes=264 classifier_bounds=1", 10
ok_message_len: equ $ - ok_message

section .bss
align 16
image:    resb IMAGE_SIZE
summary:  resb PHDR_SUMMARY_RECORD_SIZE
regions:  resb EXEC_REGION_RECORD_SIZE * 4
property_context: resb PRIVATE_METADATA_CONTEXT_SIZE

section .text
%macro EXPECT_ROLE 1
    call    run_role
    test    eax, eax
    jne     .fail
    cmp     qword [summary + PHDR_SUMMARY_ROLE_STATE], %1
    jne     .fail
%endmacro

%macro EXPECT_PHDR_STATUS 1
    call    run_phdr
    cmp     eax, %1
    jne     .fail
%endmacro

_start:
    cld

    ; 1. ET_DYN alone is unknown, never automatically promoted to PIE.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    EXPECT_ROLE BINARY_ROLE_UNKNOWN

    ; 2. ET_DYN with one bounded PT_INTERP is executable-like.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    call    setup_interp_ph0
    EXPECT_ROLE BINARY_ROLE_EXECUTABLE_LIKE
    cmp     qword [summary + PHDR_SUMMARY_INTERP_COUNT], 1
    jne     .fail

    ; 3. ET_DYN with DF_1_PIE is executable-like.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    mov     rdi, PH0
    mov     rsi, 2
    call    setup_dynamic_phdr
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_FLAGS_1
    mov     qword [image + DYNAMIC_OFF + D_UN], DF_1_PIE
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_NULL
    EXPECT_ROLE BINARY_ROLE_EXECUTABLE_LIKE
    cmp     qword [summary + PHDR_SUMMARY_FLAGS1_COUNT], 1
    jne     .fail

    ; 4. A bounded nonempty SONAME with no executable-like evidence is shared-like.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     rax, STRTAB_OFF
    call    setup_valid_soname_entries
    EXPECT_ROLE BINARY_ROLE_SHARED_OBJECT_LIKE
    test    qword [summary + PHDR_SUMMARY_ROLE_EVIDENCE], ROLE_EVIDENCE_DT_SONAME
    jz      .fail

    ; 5. ET_DYN with only a nonzero entrypoint is ambiguous.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     qword [image + E_ENTRY], 0x100
    mov     word [image + E_PHNUM], 1
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    EXPECT_ROLE BINARY_ROLE_AMBIGUOUS

    ; 6. SONAME plus a weak nonzero entrypoint remains ambiguous.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     qword [image + E_ENTRY], 0x100
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     rax, STRTAB_OFF
    call    setup_valid_soname_entries
    EXPECT_ROLE BINARY_ROLE_AMBIGUOUS

    ; 7. Strong executable and shared-object evidence is contradictory.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 3
    call    setup_interp_ph0
    mov     rdi, PH1
    call    setup_dyn_load_phdr
    mov     rdi, PH2
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     rax, STRTAB_OFF
    call    setup_valid_soname_entries
    EXPECT_ROLE BINARY_ROLE_CONTRADICTORY

    ; 8. Duplicate DT_FLAGS_1 entries are contradictory even when identical.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    mov     rdi, PH0
    mov     rsi, 3
    call    setup_dynamic_phdr
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_FLAGS_1
    mov     qword [image + DYNAMIC_OFF + D_UN], DF_1_PIE
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_FLAGS_1
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], DF_1_PIE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_NULL
    EXPECT_ROLE BINARY_ROLE_CONTRADICTORY

    ; 9. Conflicting duplicate SONAME values are contradictory and visible.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 5
    call    setup_dynamic_phdr
    call    setup_soname_table
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_STRTAB
    mov     qword [image + DYNAMIC_OFF + D_UN], STRTAB_OFF
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_STRSZ
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], STRTAB_SIZE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_UN], 10
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 4) + D_TAG], DT_NULL
    EXPECT_ROLE BINARY_ROLE_CONTRADICTORY
    test    qword [summary + PHDR_SUMMARY_ROLE_EVIDENCE], ROLE_EVIDENCE_CONFLICT_SONAME
    jz      .fail

    ; 10. A normal ET_EXEC object remains executable-like.
    call    setup_base
    mov     word [image + E_TYPE], ET_EXEC
    mov     qword [image + E_ENTRY], 0x400100
    mov     word [image + E_PHNUM], 1
    mov     rdi, PH0
    call    setup_exec_load_phdr
    EXPECT_ROLE BINARY_ROLE_EXECUTABLE_LIKE

    ; 11. ET_EXEC plus bounded SONAME evidence is contradictory.
    call    setup_base
    mov     word [image + E_TYPE], ET_EXEC
    mov     qword [image + E_ENTRY], 0x400100
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_exec_load_phdr
    mov     rdi, PH1
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     rax, 0x400000 + STRTAB_OFF
    call    setup_valid_soname_entries
    EXPECT_ROLE BINARY_ROLE_CONTRADICTORY

    ; 12. A non-NUL-terminated PT_INTERP path is malformed.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    call    setup_interp_ph0
    mov     byte [image + INTERP_OFF + 5], 'x'
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 13. Interpreter evidence above the fixed scan cap is unsupported.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    mov     qword [image + E_PHOFF], PH0
    mov     dword [image + PH0 + P_TYPE], PT_INTERP
    mov     qword [image + PH0 + P_OFFSET], 0
    mov     qword [image + PH0 + P_FILESZ], INTERP_PATH_SCAN_MAX + 1
    mov     qword [image + PH0 + P_MEMSZ], INTERP_PATH_SCAN_MAX + 1
    mov     qword [image + PH0 + P_ALIGN], 1
    EXPECT_PHDR_STATUS EXIT_UNSUPPORTED

    ; 14. A SONAME carrier without bounded string-table metadata is malformed.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    mov     rdi, PH0
    mov     rsi, 2
    call    setup_dynamic_phdr
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_NULL
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 15. A SONAME index at the dynamic string-table end is malformed.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     rax, STRTAB_OFF
    call    setup_valid_soname_entries
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], STRTAB_SIZE
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 16. A nonempty SONAME without an in-range NUL terminator is malformed.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 4
    call    setup_dynamic_phdr
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_STRTAB
    mov     qword [image + DYNAMIC_OFF + D_UN], STRTAB_OFF
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_STRSZ
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], 8
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_TAG], DT_NULL
    mov     rax, 0x7878787878787800
    mov     [image + STRTAB_OFF], rax
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 17. Identical duplicate SONAME carriers remain explicit contradiction.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 5
    call    setup_dynamic_phdr
    call    setup_soname_table
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_STRTAB
    mov     qword [image + DYNAMIC_OFF + D_UN], STRTAB_OFF
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_STRSZ
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], STRTAB_SIZE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 4) + D_TAG], DT_NULL
    EXPECT_ROLE BINARY_ROLE_CONTRADICTORY

    ; 18. A NUL-only PT_INTERP path is malformed, not executable evidence.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    call    setup_interp_ph0
    mov     byte [image + INTERP_OFF], 0
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 19. An embedded NUL before the final terminator is malformed.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 1
    call    setup_interp_ph0
    mov     byte [image + INTERP_OFF + 2], 0
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 20. Every SONAME carrier is validated. A valid first index cannot hide a
    ; malformed second index at the string-table end.
    call    setup_base
    mov     word [image + E_TYPE], ET_DYN
    mov     word [image + E_PHNUM], 2
    mov     rdi, PH0
    call    setup_dyn_load_phdr
    mov     rdi, PH1
    mov     rsi, 5
    call    setup_dynamic_phdr
    call    setup_soname_table
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_STRTAB
    mov     qword [image + DYNAMIC_OFF + D_UN], STRTAB_OFF
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_STRSZ
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], STRTAB_SIZE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_UN], STRTAB_SIZE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 4) + D_TAG], DT_NULL
    EXPECT_PHDR_STATUS EXIT_MALFORMED_ELF

    ; 21. The classifier rejects impossible completed-summary relationships
    ; without reading mapped bytes.
    call    setup_base
    mov     qword [summary + PHDR_SUMMARY_ELF_TYPE], ET_DYN
    mov     qword [summary + PHDR_SUMMARY_PHNUM], 0
    mov     qword [summary + PHDR_SUMMARY_INTERP_COUNT], 1
    lea     rdi, [summary]
    call    x64lens_binary_role_classify
    cmp     eax, EXIT_BOUNDS
    jne     .fail

    mov     eax, 1
    mov     edi, 1
    lea     rsi, [ok_message]
    mov     edx, ok_message_len
    syscall
    xor     edi, edi
    mov     eax, 60
    syscall

.fail:
    mov     edi, 1
    mov     eax, 60
    syscall

setup_base:
    xor     eax, eax
    lea     rdi, [image]
    mov     ecx, IMAGE_SIZE / 8
    rep stosq
    lea     rdi, [summary]
    mov     ecx, PHDR_SUMMARY_RECORD_SIZE / 8
    rep stosq
    lea     rdi, [regions]
    mov     ecx, (EXEC_REGION_RECORD_SIZE * 4) / 8
    rep stosq
    lea     rdi, [property_context]
    mov     ecx, PRIVATE_METADATA_CONTEXT_SIZE / 8
    rep stosq
    mov     qword [image + E_PHOFF], 0
    mov     word [image + E_PHENTSIZE], ELF64_PHDR_SIZE
    ret

setup_interp_ph0:
    mov     qword [image + E_PHOFF], PH0
    mov     dword [image + PH0 + P_TYPE], PT_INTERP
    mov     qword [image + PH0 + P_OFFSET], INTERP_OFF
    mov     qword [image + PH0 + P_FILESZ], 6
    mov     qword [image + PH0 + P_MEMSZ], 6
    mov     qword [image + PH0 + P_ALIGN], 1
    mov     byte [image + INTERP_OFF + 0], 'l'
    mov     byte [image + INTERP_OFF + 1], 'd'
    mov     byte [image + INTERP_OFF + 2], '.'
    mov     byte [image + INTERP_OFF + 3], 's'
    mov     byte [image + INTERP_OFF + 4], 'o'
    mov     byte [image + INTERP_OFF + 5], 0
    ret

; RDI = PHDR offset, RSI = dynamic-entry count.
setup_dynamic_phdr:
    mov     qword [image + E_PHOFF], PH0
    mov     dword [image + rdi + P_TYPE], PT_DYNAMIC
    mov     qword [image + rdi + P_OFFSET], DYNAMIC_OFF
    mov     rax, rsi
    shl     rax, 4
    mov     qword [image + rdi + P_FILESZ], rax
    mov     qword [image + rdi + P_MEMSZ], rax
    mov     qword [image + rdi + P_ALIGN], 8
    ret

; ET_DYN load: p_offset/vaddr slope zero and entry 0x100 is in range.
setup_dyn_load_phdr:
    mov     qword [image + E_PHOFF], PH0
    mov     dword [image + rdi + P_TYPE], PT_LOAD
    mov     dword [image + rdi + P_FLAGS], PF_R | PF_X
    mov     qword [image + rdi + P_OFFSET], 0
    mov     qword [image + rdi + P_VADDR], 0
    mov     qword [image + rdi + P_FILESZ], IMAGE_SIZE
    mov     qword [image + rdi + P_MEMSZ], IMAGE_SIZE
    mov     qword [image + rdi + P_ALIGN], 0x1000
    ret

; ET_EXEC load: p_offset 0 maps at 0x400000 and contains entry 0x400100.
setup_exec_load_phdr:
    mov     qword [image + E_PHOFF], PH0
    mov     dword [image + rdi + P_TYPE], PT_LOAD
    mov     dword [image + rdi + P_FLAGS], PF_R | PF_X
    mov     qword [image + rdi + P_OFFSET], 0
    mov     qword [image + rdi + P_VADDR], 0x400000
    mov     qword [image + rdi + P_FILESZ], IMAGE_SIZE
    mov     qword [image + rdi + P_MEMSZ], IMAGE_SIZE
    mov     qword [image + rdi + P_ALIGN], 0x1000
    ret

setup_soname_table:
    mov     rax, 0x6f732e7862696c00 ; NUL + "libx.so"
    mov     [image + STRTAB_OFF], rax
    mov     byte [image + STRTAB_OFF + 8], 0
    mov     rax, 0x6f732e7962696c00 ; NUL + "liby.so"
    mov     [image + STRTAB_OFF + 9], rax
    mov     byte [image + STRTAB_OFF + 17], 0
    ret

; RAX = dynamic string-table virtual address.
setup_valid_soname_entries:
    push    rax
    call    setup_soname_table
    pop     rax
    mov     qword [image + DYNAMIC_OFF + D_TAG], DT_STRTAB
    mov     qword [image + DYNAMIC_OFF + D_UN], rax
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_TAG], DT_STRSZ
    mov     qword [image + DYNAMIC_OFF + ELF64_DYN_SIZE + D_UN], STRTAB_SIZE
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_TAG], DT_SONAME
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 2) + D_UN], 1
    mov     qword [image + DYNAMIC_OFF + (ELF64_DYN_SIZE * 3) + D_TAG], DT_NULL
    ret

run_phdr:
    ; SysV AMD64 requires RSP to be 16-byte aligned before a nested call.
    ; The canary turns removal of both adjustments into a deterministic harness
    ; failure instead of allowing a source-shape oracle to false-pass.
    sub     rsp, 8
    call    assert_callee_entry_alignment
    test    eax, eax
    jne     .return
    lea     rdi, [image]
    mov     rsi, IMAGE_SIZE
    lea     rdx, [summary]
    lea     rcx, [regions]
    mov     r8, 4
    lea     r9, [property_context]
    call    x64lens_phdr_analyze
.return:
    add     rsp, 8
    ret

assert_callee_entry_alignment:
    mov     rax, rsp
    and     eax, 15
    cmp     eax, 8
    je      .aligned
    mov     eax, EXIT_BOUNDS
    ret
.aligned:
    xor     eax, eax
    ret

run_role:
    sub     rsp, 8
    call    run_phdr
    test    eax, eax
    jne     .return
    lea     rdi, [summary]
    call    x64lens_binary_role_classify
.return:
    add     rsp, 8
    ret
