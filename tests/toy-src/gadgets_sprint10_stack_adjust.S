/*
 * gadgets_sprint10_stack_adjust.S
 *
 * Purpose:
 *   Controlled Sprint 10 fixture for the exact positive aligned
 *   `add rsp, imm8; ret` family. Two supported stack adjustments must receive
 *   the dedicated pattern. Zero, negative, unaligned, wrong-register, and
 *   subtraction forms must conservatively fall back to bare `ret` semantics.
 *
 * Safety:
 *   The fixture is analyzed and disassembled but never executed by validation.
 */

.global _start
.text

_start:
    add $8, %rsp
    ret

    add $0x20, %rsp
    ret

    add $0, %rsp
    ret

    add $-8, %rsp
    ret

    add $7, %rsp
    ret

    add $8, %rax
    ret

    sub $8, %rsp
    ret

    mov $60, %rax
    xor %rdi, %rdi
    syscall

.data
non_exec_stack_adjust_ret_bytes:
    .byte 0x48, 0x83, 0xc4, 0x08, 0xc3
