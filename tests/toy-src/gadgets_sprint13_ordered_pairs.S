/*
 * gadgets_sprint13_ordered_pairs.S
 *
 * Purpose:
 *   Controlled producer fixture containing exactly one executable return-
 *   ending candidate for each of the 30 ordered distinct pairs among the six
 *   System V argument registers.  Patch 082 uses independently built analyzer
 *   generations to prove the existing exact pattern, stack_pop_order,
 *   semantic, and score facts rather than trusting static fixtures alone.
 *
 * Safety:
 *   Validation maps and analyzes this fixture but never executes it.
 */

.global _start
.text

_start:
    .byte 0x5f, 0x5e, 0xc3             /* 01: rdi-rsi */
    .byte 0x5f, 0x5a, 0xc3             /* 02: rdi-rdx */
    .byte 0x5f, 0x59, 0xc3             /* 03: rdi-rcx */
    .byte 0x5f, 0x41, 0x58, 0xc3       /* 04: rdi-r8 */
    .byte 0x5f, 0x41, 0x59, 0xc3       /* 05: rdi-r9 */
    .byte 0x5e, 0x5f, 0xc3             /* 06: rsi-rdi */
    .byte 0x5e, 0x5a, 0xc3             /* 07: rsi-rdx */
    .byte 0x5e, 0x59, 0xc3             /* 08: rsi-rcx */
    .byte 0x5e, 0x41, 0x58, 0xc3       /* 09: rsi-r8 */
    .byte 0x5e, 0x41, 0x59, 0xc3       /* 10: rsi-r9 */
    .byte 0x5a, 0x5f, 0xc3             /* 11: rdx-rdi */
    .byte 0x5a, 0x5e, 0xc3             /* 12: rdx-rsi */
    .byte 0x5a, 0x59, 0xc3             /* 13: rdx-rcx */
    .byte 0x5a, 0x41, 0x58, 0xc3       /* 14: rdx-r8 */
    .byte 0x5a, 0x41, 0x59, 0xc3       /* 15: rdx-r9 */
    .byte 0x59, 0x5f, 0xc3             /* 16: rcx-rdi */
    .byte 0x59, 0x5e, 0xc3             /* 17: rcx-rsi */
    .byte 0x59, 0x5a, 0xc3             /* 18: rcx-rdx */
    .byte 0x59, 0x41, 0x58, 0xc3       /* 19: rcx-r8 */
    .byte 0x59, 0x41, 0x59, 0xc3       /* 20: rcx-r9 */
    .byte 0x41, 0x58, 0x5f, 0xc3       /* 21: r8-rdi */
    .byte 0x41, 0x58, 0x5e, 0xc3       /* 22: r8-rsi */
    .byte 0x41, 0x58, 0x5a, 0xc3       /* 23: r8-rdx */
    .byte 0x41, 0x58, 0x59, 0xc3       /* 24: r8-rcx */
    .byte 0x41, 0x58, 0x41, 0x59, 0xc3 /* 25: r8-r9 */
    .byte 0x41, 0x59, 0x5f, 0xc3       /* 26: r9-rdi */
    .byte 0x41, 0x59, 0x5e, 0xc3       /* 27: r9-rsi */
    .byte 0x41, 0x59, 0x5a, 0xc3       /* 28: r9-rdx */
    .byte 0x41, 0x59, 0x59, 0xc3       /* 29: r9-rcx */
    .byte 0x41, 0x59, 0x41, 0x58, 0xc3 /* 30: r9-r8 */

    /* The fixture is analyzed, not executed. */
    mov $60, %rax
    xor %rdi, %rdi
    syscall

.section .rodata
non_exec_control_bytes:
    .byte 0x5f, 0x5f, 0xc3       /* duplicate register control */
    .byte 0x5c, 0x5f, 0xc3       /* rsp remains outside the family */
    .byte 0x41, 0x5a, 0x5f, 0xc3 /* r10 remains outside SysV pair family */
