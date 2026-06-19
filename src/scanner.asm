; scanner.asm
;
; Purpose:
;   Raw gadget candidate scanner.
;
; Module scope:
;   Walk executable PT_LOAD + PF_X regions, discover bounded raw candidate
;   windows around return terminators, and store those facts in gadget_record
;   structures for reporters, later pattern matching, and future benchmarks.
;
; Sprint 3 scope:
;   Detect `ret` (0xc3) and `ret imm16` (0xc2 xx xx) terminators over the
;   executable regions created by phdr.asm/regions.asm. This module does not
;   classify semantic primitives, score gadgets, or render text output. Patch
;   010 keeps the scanner storage-agnostic by consuming a caller-provided
;   capacity and candidate-record pointer.
;
; Safety model:
;   Target binaries are untrusted. The scanner revalidates every executable
;   region's file range before reading bytes and never reads before the start
;   or past the end of a file-backed executable region.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"
%include "structs.inc"

section .text
global x64lens_scanner_find_ret_candidates

; x64lens_scanner_find_ret_candidates(base=rdi, file_size=rsi, phdr_summary=rdx,
;                                     regions=rcx, gadget_summary=r8,
;                                     gadget_records=r9) -> rax=status
;
; Inputs:
;   RDI = mapped target file base
;   RSI = mapped target file size
;   RDX = phdr_summary record containing executable-region count
;   RCX = executable_region[] buffer
;   R8  = writable gadget_summary record. MAX_DEPTH must be pre-filled.
;   R9  = writable gadget_record[] buffer with caller-supplied capacity
;
; Output:
;   RAX = stable x64lens exit code
;
; Clobbers:
;   Caller-saved registers plus the writable summary/candidate buffers.
x64lens_scanner_find_ret_candidates:
    push    rbp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     r15, rdi            ; mapped file base
    mov     r14, rsi            ; file size
    mov     r13, rdx            ; phdr_summary pointer
    mov     r12, rcx            ; executable_region[] pointer
    mov     rbx, r8             ; gadget_summary pointer
    ; R9 is kept as the gadget_record[] base throughout this routine.

    ; Load and validate max-depth before clearing the other summary fields.
    mov     rbp, [rbx + GADGET_SUMMARY_MAX_DEPTH]
    test    rbp, rbp
    jz      .unsupported
    cmp     rbp, GADGET_MAX_DEPTH_LIMIT
    ja      .unsupported

    ; Initialize scanner summary fields. Keep MAX_DEPTH and CAPACITY values
    ; supplied by the command layer so report_text.asm and future benchmark
    ; emitters can render the actual storage contract. If capacity was not
    ; supplied, fall back to the default Sprint 3 candidate limit.
    cmp     qword [rbx + GADGET_SUMMARY_CAPACITY], 0
    jne     .capacity_ready
    mov     qword [rbx + GADGET_SUMMARY_CAPACITY], GADGET_RECORD_MAX
.capacity_ready:
    mov     qword [rbx + GADGET_SUMMARY_COUNT], 0
    mov     qword [rbx + GADGET_SUMMARY_RET_COUNT], 0
    mov     qword [rbx + GADGET_SUMMARY_RET_IMM_COUNT], 0
    mov     qword [rbx + GADGET_SUMMARY_PATTERN_COUNT], 0

    xor     r11, r11            ; region index
.region_loop:
    cmp     r11, [r13 + PHDR_SUMMARY_EXEC_COUNT]
    jae     .ok

    ; R8 = current executable_region record pointer.
    mov     rax, r11
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     r8, [r12 + rax]

    ; Revalidate the region's file-backed byte range before scanning.
    mov     rsi, [r8 + EXEC_REGION_FILE_OFFSET] ; region_start file offset
    mov     rdx, [r8 + EXEC_REGION_FILESZ]      ; region_size in file bytes
    cmp     rsi, r14
    ja      .malformed
    mov     rax, r14
    sub     rax, rsi
    cmp     rdx, rax
    ja      .malformed
    test    rdx, rdx
    jz      .next_region

    ; R10 = region_end file offset. RDI = current cursor file offset.
    lea     r10, [rsi + rdx]
    mov     rdi, rsi
.byte_loop:
    cmp     rdi, r10
    jae     .next_region

    mov     al, [r15 + rdi]
    cmp     al, 0xc3
    je      .found_ret
    cmp     al, 0xc2
    je      .maybe_ret_imm16
    inc     rdi
    jmp     .byte_loop

.found_ret:
    mov     eax, GADGET_TERM_RET
    mov     ecx, 1              ; terminator length
    jmp     .store_candidate

.maybe_ret_imm16:
    ; ret imm16 is three bytes. Only record it if the full immediate fits
    ; inside the executable region. If not, treat this byte as ordinary data.
    mov     rax, rdi
    add     rax, 3
    jc      .advance_one
    cmp     rax, r10
    ja      .advance_one
    mov     eax, GADGET_TERM_RET_IMM16
    mov     ecx, 3              ; terminator length
    jmp     .store_candidate

.store_candidate:
    ; Capacity check. Silent truncation would invalidate research counts.
    mov     rdx, [rbx + GADGET_SUMMARY_COUNT]
    cmp     rdx, [rbx + GADGET_SUMMARY_CAPACITY]
    jae     .unsupported

    ; Preserve terminator type and length while we reuse RAX/RCX as scratch
    ; for record addressing and byte-window calculations. No calls occur while
    ; these values are on the stack.
    push    rcx                 ; [rsp + 8] after next push = terminator length
    push    rax                 ; [rsp] = terminator type

    ; R8 = current executable_region record pointer was clobbered by the byte
    ; load path? Recompute it so address translation is deterministic.
    mov     rax, r11
    imul    rax, rax, EXEC_REGION_RECORD_SIZE
    lea     r8, [r12 + rax]

    ; RAX = current candidate record pointer.
    mov     rax, rdx
    imul    rax, rax, GADGET_RECORD_SIZE
    lea     rax, [r9 + rax]

    ; Window start = max(region_start, terminator_offset - max_depth).
    ; RSI still holds region_start, RDI holds terminator file offset.
    mov     rdx, rdi
    sub     rdx, rsi            ; distance from region start to terminator
    cmp     rdx, rbp
    jbe     .window_from_region
    mov     rdx, rdi
    sub     rdx, rbp
    jmp     .window_start_ready
.window_from_region:
    mov     rdx, rsi
.window_start_ready:

    ; Store terminator file offset and virtual address. The virtual address is
    ; region_vaddr + (terminator_file_offset - region_file_offset).
    mov     [rax + GADGET_FILE_OFFSET], rdi
    mov     rcx, rdi
    sub     rcx, [r8 + EXEC_REGION_FILE_OFFSET]
    add     rcx, [r8 + EXEC_REGION_VADDR]
    mov     [rax + GADGET_VIRTUAL_ADDRESS], rcx

    ; Store byte window start and length. The saved terminator length accounts
    ; for one-byte `ret` and three-byte `ret imm16` candidates. RSI remains the
    ; region_start value for the next candidate in the same region.
    mov     [rax + GADGET_BYTE_START], rdx
    mov     rcx, rdi
    sub     rcx, rdx
    add     rcx, [rsp + 8]
    mov     [rax + GADGET_BYTE_LEN], rcx

    ; Store raw terminator type and clear downstream semantic/scoring fields so
    ; downstream code never reads stale data.
    mov     edx, [rsp]
    mov     [rax + GADGET_TERMINATOR_TYPE], edx
    mov     dword [rax + GADGET_SEMANTIC_CLASS], SEM_UNKNOWN_CANDIDATE
    mov     qword [rax + GADGET_REGS_CONTROLLED], 0
    mov     qword [rax + GADGET_REGS_CLOBBERED], 0
    mov     qword [rax + GADGET_STACK_DELTA], 0
    mov     qword [rax + GADGET_SIDE_EFFECT_FLAGS], 0
    mov     dword [rax + GADGET_SCORE], 0
    mov     dword [rax + GADGET_PATTERN_ID], PATTERN_UNKNOWN

    inc     qword [rbx + GADGET_SUMMARY_COUNT]
    cmp     dword [rax + GADGET_TERMINATOR_TYPE], GADGET_TERM_RET
    jne     .count_ret_imm
    inc     qword [rbx + GADGET_SUMMARY_RET_COUNT]
    add     rsp, 16
    jmp     .advance_one
.count_ret_imm:
    inc     qword [rbx + GADGET_SUMMARY_RET_IMM_COUNT]
    add     rsp, 16

.advance_one:
    inc     rdi
    jmp     .byte_loop

.next_region:
    inc     r11
    jmp     .region_loop

.ok:
    xor     rax, rax
    jmp     .done
.malformed:
    mov     rax, EXIT_MALFORMED_ELF
    jmp     .done
.unsupported:
    mov     rax, EXIT_UNSUPPORTED
.done:
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret
