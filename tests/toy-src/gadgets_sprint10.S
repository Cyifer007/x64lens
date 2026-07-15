/*
 * gadgets_sprint10.S
 *
 * Purpose:
 *   Controlled Sprint 10 fixture for conservative two-pop argument-control
 *   recognition. Three distinct supported pairs must receive the generic
 *   multi-pop exact pattern and ordered register facts. Duplicate or
 *   unsupported leading pops must fall back to the strongest existing
 *   single-pop suffix ending at the same return.
 */

.global _start
.text

_start:
    pop %rdi
    pop %rsi
    ret

    pop %r8
    pop %r9
    ret

    pop %rdx
    pop %rcx
    ret

    /* Duplicate controls are not promoted as a multi-pop family. */
    pop %rdi
    pop %rdi
    ret

    /* RBX is outside the Patch 046 multi-pop argument-control subset. */
    pop %rbx
    pop %rdi
    ret

    /* The fixture is analyzed, not executed. */
    mov $60, %rax
    xor %rdi, %rdi
    syscall

.data
non_exec_sprint10_ret_bytes:
    .byte 0x5f, 0x5e, 0xc3
