/*
 * gadgets.S
 *
 * Purpose:
 *   Hand-authored x86_64 gadget corpus with known byte patterns. Later
 *   scanner/classifier tests should verify that x64lens can detect these
 *   exact primitives and report their semantic classes correctly.
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

    pop %rax
    ret

    leave
    ret

    syscall
    ret
