/*
 * gadgets_sprint10_effects.S
 *
 * Purpose:
 *   One-per-pattern Sprint 10 architectural-effect fixture. The executable
 *   stream contains exactly one return-ending candidate for every current
 *   exact PATTERN_* ID. Eight exact single-pop forms remain semantic unknowns,
 *   while their deterministic register and stack effects are still retained.
 *
 * Safety:
 *   Validation analyzes and disassembles this fixture but never executes it.
 */

.global _start
.text

_start:
    /* 1: ret */
    .byte 0xc3

    /* 2: ret imm16 (0x0010) */
    .byte 0xc2, 0x10, 0x00

    /* 3-18: every exact single-pop pattern. */
    .byte 0x58, 0xc3             /* pop rax; ret */
    .byte 0x59, 0xc3             /* pop rcx; ret */
    .byte 0x5a, 0xc3             /* pop rdx; ret */
    .byte 0x5b, 0xc3             /* pop rbx; ret */
    .byte 0x5c, 0xc3             /* pop rsp; ret */
    .byte 0x5d, 0xc3             /* pop rbp; ret */
    .byte 0x5e, 0xc3             /* pop rsi; ret */
    .byte 0x5f, 0xc3             /* pop rdi; ret */
    .byte 0x41, 0x58, 0xc3       /* pop r8; ret */
    .byte 0x41, 0x59, 0xc3       /* pop r9; ret */
    .byte 0x41, 0x5a, 0xc3       /* pop r10; ret */
    .byte 0x41, 0x5b, 0xc3       /* pop r11; ret */
    .byte 0x41, 0x5c, 0xc3       /* pop r12; ret */
    .byte 0x41, 0x5d, 0xc3       /* pop r13; ret */
    .byte 0x41, 0x5e, 0xc3       /* pop r14; ret */
    .byte 0x41, 0x5f, 0xc3       /* pop r15; ret */

    /* 19-20: pivot and syscall patterns. */
    .byte 0xc9, 0xc3             /* leave; ret */
    .byte 0x0f, 0x05, 0xc3       /* syscall; ret */

    /* 21: ordered two-pop argument-control pattern. */
    .byte 0x5f, 0x5e, 0xc3       /* pop rdi; pop rsi; ret */

    /* 22: exact register-direct transfer. */
    .byte 0x48, 0x89, 0xc7, 0xc3 /* mov rdi,rax in Intel syntax */

    /* 23: exact positive aligned stack adjustment. */
    .byte 0x48, 0x83, 0xc4, 0x08, 0xc3

    /* 24-25: exact bounded qword memory write and read. */
    .byte 0x48, 0x89, 0x07, 0xc3 /* mov [rdi],rax */
    .byte 0x48, 0x8b, 0x07, 0xc3 /* mov rax,[rdi] */

    /* The fixture is analyzed, not executed. */
    mov $60, %rax
    xor %rdi, %rdi
    syscall

.section .rodata
non_exec_effect_bytes:
    .byte 0xc3, 0xc2, 0x10, 0x00, 0x5f, 0x5e, 0xc3
    .byte 0x48, 0x89, 0xc7, 0xc3, 0x48, 0x83, 0xc4, 0x08, 0xc3
    .byte 0x48, 0x89, 0x07, 0xc3, 0x48, 0x8b, 0x07, 0xc3
