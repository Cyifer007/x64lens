/*
 * gadgets_sprint10_transfer.S
 *
 * Purpose:
 *   Controlled Sprint 10 fixture for exact register-direct transfer facts.
 *   Four distinct 64-bit register transfers must receive the generic
 *   register-transfer pattern. Self moves, RSP participation, and a 32-bit
 *   move conservatively fall back to the existing ret suffix. The two memory
 *   forms intentionally exercise Patch 049 cross-family promotion so this
 *   fixture also detects stale transfer-only expectations.
 *
 * Safety:
 *   The fixture is analyzed and disassembled but never executed by validation.
 */

.global _start
.text

_start:
    mov %rax, %rdi
    ret

    mov %r9, %r8
    ret

    /* Exercise opcode 8b with an extended destination. */
    .byte 0x4c, 0x8b, 0xea       /* mov r13, rdx */
    ret

    /* Exercise opcode 8b with an extended source. */
    .byte 0x49, 0x8b, 0xde       /* mov rbx, r14 */
    ret

    /* Same-register transfers are semantic no-ops and remain ret fallbacks. */
    mov %rdi, %rdi
    ret

    /* RSP participation is deliberately outside the bounded transfer family. */
    mov %rax, %rsp
    ret

    mov %rsp, %rdi
    ret

    /* Memory forms are outside transfer semantics but inside the separate
     * bounded memory family. The 32-bit form remains a bare-ret fallback. */
    mov %rdi, (%rax)
    ret

    mov %eax, %edi
    ret

    mov (%rax), %rdi
    ret

    mov $60, %rax
    xor %rdi, %rdi
    syscall

.data
non_exec_transfer_ret_bytes:
    .byte 0x48, 0x89, 0xc7, 0xc3
