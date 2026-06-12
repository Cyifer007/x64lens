/*
 * gadgets.S
 *
 * Purpose:
 *   Hand-authored x86_64 gadget corpus with known byte patterns. Sprint 3
 *   scanner tests verify that x64lens detects raw ret and ret-imm terminators
 *   from executable PT_LOAD regions. Sprint 4 and Sprint 5 tests reuse this
 *   same file for semantic primitives, score output, and JSON output.
 */

.global _start
.text

_start:
    pop %rdi
    ret

    pop %rsi
    ret

    pop %rdx
    ret

    pop %rcx
    ret

    pop %r8
    ret

    pop %r9
    ret

    pop %rax
    ret

    pop %rsp
    ret

    leave
    ret

    syscall
    ret

    /* AT&T syntax for `ret imm16`; expected bytes are c2 10 00. */
    ret $0x10

    /* Exit cleanly only if control reaches this point. The fixture is analyzed, not executed. */
    mov $60, %rax
    xor %rdi, %rdi
    syscall

.data
/* Non-executable bytes that look like terminators. The scanner must operate
 * over executable PT_LOAD + PF_X regions, not arbitrary file bytes. */
non_exec_ret_bytes:
    .byte 0xc3, 0xc2, 0x10, 0x00
