/*
 * Sprint 10 Patch 049 controlled memory-effect fixture.
 *
 * Six exact no-displacement/no-index 64-bit memory moves are followed by six
 * deliberately unsupported forms that must fall back to bare ret semantics.
 * Matching bytes are also present in non-executable data to preserve loader-
 * authoritative PT_LOAD + PF_X scanning.
 */

.section .text
.global _start
_start:
    mov %rax, (%rdi)
    ret
    mov %r9, (%r8)
    ret
    mov %rdx, (%r14)
    ret

    mov (%rdi), %rax
    ret
    mov (%r8), %r9
    ret
    mov (%r14), %rdx
    ret

    mov %rax, (%rsp)          /* SIB base: fallback */
    ret
    mov %rax, 8(%rdi)         /* displacement: fallback */
    ret
    mov 8(%rdi), %rax         /* displacement: fallback */
    ret
    mov %rsp, (%rdi)          /* RSP value: fallback */
    ret
    mov (%rdi), %rsp          /* RSP destination/pivot: fallback */
    ret
    mov (%rdi), %eax          /* 32-bit form: fallback */
    ret

.section .rodata
nonexec_memory_bytes:
    .byte 0x48, 0x89, 0x07, 0xc3
    .byte 0x4d, 0x8b, 0x08, 0xc3
