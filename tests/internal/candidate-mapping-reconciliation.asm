; candidate-mapping-reconciliation.asm
;
; Purpose:
;   Validate the Sprint 12 executable-region provenance seam independently of
;   the public report surface.
;
; Scope:
;   Prove original PHDR indexes are retained without changing the 64-byte
;   executable-region stride, contributor bits use dense region slots, same-
;   slope overlaps contribute together, different-slope overlaps do not, and
;   contradictory count/coordinate/index states fail closed.
;
; This harness is linked only for development validation.

bits 64
default rel

%include "elf64.inc"
%include "errors.inc"
%include "structs.inc"

extern x64lens_regions_store_from_phdr
extern x64lens_candidate_mapping_from_regions
global _start

%if EXEC_REGION_RECORD_SIZE != 64
    %error "candidate mapping requires the contracted 64-byte executable_region stride"
%endif

section .rodata
ok_message: db "sprint12-overlap-provenance-smoke: ok phdr_indexes=5 dense_masks=1 empty=1 rejected=4 region_stride=64 evidence_stride=56", 10
ok_message_len: equ $ - ok_message
phdr_indexes: dd 0, 63, 64, 255, 65533

section .bss
align 16
phdr:      resb ELF64_PHDR_SIZE
summary:   resb GADGET_SUMMARY_RECORD_SIZE
phsummary: resb PHDR_SUMMARY_RECORD_SIZE
regions:   resb EXEC_REGION_RECORD_SIZE * 5
gadgets:   resb GADGET_RECORD_SIZE
evidence:  resb CANDIDATE_EVIDENCE_RECORD_SIZE

section .text
_start:
    cld

    ; Store and recover original PHDR indexes at representative boundaries.
    xor     ebx, ebx
.index_loop:
    cmp     ebx, 5
    jae     .mapping_setup
    mov     dword [phdr + P_FLAGS], PF_R | PF_X
    mov     rdi, regions
    mov     esi, ebx
    mov     rdx, phdr
    mov     ecx, [phdr_indexes + rbx * 4]
    call    x64lens_regions_store_from_phdr
    test    eax, eax
    jne     .fail
    mov     rax, rbx
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    mov     edx, [regions + rax + EXEC_REGION_PHDR_INDEX]
    cmp     edx, [phdr_indexes + rbx * 4]
    jne     .fail
    inc     ebx
    jmp     .index_loop

.mapping_setup:
    ; Empty analysis is valid when no executable region and no candidate exists.
    call    clear_mapping_state
    call    run_mapping
    test    eax, eax
    jne     .fail

    call    clear_mapping_state
    mov     qword [summary + GADGET_SUMMARY_COUNT], 1
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 1
    mov     qword [phsummary + PHDR_SUMMARY_EXEC_COUNT], 3

    ; Region 0 and region 1 overlap with the same file-to-virtual slope.
    mov     qword [regions + EXEC_REGION_FILE_OFFSET], 0x100
    mov     qword [regions + EXEC_REGION_VADDR], 0x400100
    mov     qword [regions + EXEC_REGION_FILESZ], 0x100
    mov     qword [regions + EXEC_REGION_MEMSZ], 0x100
    mov     dword [regions + EXEC_REGION_FLAGS], PF_R | PF_X
    mov     dword [regions + EXEC_REGION_PHDR_INDEX], 63

    mov     qword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_FILE_OFFSET], 0x110
    mov     qword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_VADDR], 0x400110
    mov     qword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_FILESZ], 0x80
    mov     qword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_MEMSZ], 0x80
    mov     dword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_FLAGS], PF_R | PF_X
    mov     dword [regions + EXEC_REGION_RECORD_SIZE + EXEC_REGION_PHDR_INDEX], 64

    ; Region 2 covers the same file bytes but maps them at another slope.
    mov     qword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_FILE_OFFSET], 0x100
    mov     qword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_VADDR], 0x500100
    mov     qword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_FILESZ], 0x100
    mov     qword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_MEMSZ], 0x100
    mov     dword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_FLAGS], PF_R | PF_X
    mov     dword [regions + (EXEC_REGION_RECORD_SIZE * 2) + EXEC_REGION_PHDR_INDEX], 255

    mov     qword [gadgets + GADGET_BYTE_START], 0x120
    mov     qword [gadgets + GADGET_BYTE_LEN], 4
    mov     qword [gadgets + GADGET_FILE_OFFSET], 0x123
    mov     qword [gadgets + GADGET_VIRTUAL_ADDRESS], 0x400123

    call    run_mapping
    test    eax, eax
    jne     .fail
    cmp     qword [evidence + CANDIDATE_EVIDENCE_REGION_MASK], 3
    jne     .fail

    ; Different virtual slope only: no justified contributor.
    mov     qword [gadgets + GADGET_VIRTUAL_ADDRESS], 0x600123
    call    run_mapping
    cmp     eax, EXIT_BOUNDS
    jne     .fail

    ; More than the fixed 64 dense region slots cannot be represented.
    mov     qword [gadgets + GADGET_VIRTUAL_ADDRESS], 0x400123
    mov     qword [phsummary + PHDR_SUMMARY_EXEC_COUNT], 65
    call    run_mapping
    cmp     eax, EXIT_BOUNDS
    jne     .fail

    ; Candidate count remains globally bounded at 4096.
    mov     qword [phsummary + PHDR_SUMMARY_EXEC_COUNT], 3
    mov     qword [summary + GADGET_SUMMARY_COUNT], 4097
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 4097
    call    run_mapping
    cmp     eax, EXIT_BOUNDS
    jne     .fail

    ; PN_XNUM is a sentinel, not a valid retained ordinary PHDR index.
    mov     qword [summary + GADGET_SUMMARY_COUNT], 1
    mov     qword [summary + GADGET_SUMMARY_CAPACITY], 1
    mov     dword [regions + EXEC_REGION_PHDR_INDEX], PN_XNUM
    call    run_mapping
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

run_mapping:
    lea     rdi, [summary]
    lea     rsi, [gadgets]
    lea     rdx, [phsummary]
    lea     rcx, [regions]
    lea     r8, [evidence]
    call    x64lens_candidate_mapping_from_regions
    ret

clear_mapping_state:
    lea     rdi, [summary]
    xor     eax, eax
    mov     ecx, (GADGET_SUMMARY_RECORD_SIZE + PHDR_SUMMARY_RECORD_SIZE + (EXEC_REGION_RECORD_SIZE * 5) + GADGET_RECORD_SIZE + CANDIDATE_EVIDENCE_RECORD_SIZE) / 8
    rep stosq
    ret
