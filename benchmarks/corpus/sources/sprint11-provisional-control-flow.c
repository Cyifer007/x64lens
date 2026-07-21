// SPDX-License-Identifier: Apache-2.0
//
// Purpose:
//   Provide one small, freestanding, project-authored C source for the Sprint 11
//   provisional diagnostic corpus. The build matrix compiles this source with
//   GCC and Clang across optimization, ELF role, and hardening profiles.
//
// Safety and scope:
//   Generated binaries are static-analysis inputs only. The corpus builder does
//   not execute them. This source uses a direct Linux exit syscall so it can be
//   linked without libc, libgcc, a language runtime, or startup objects.
//
// Future work:
//   Sprint 12 may add separate loader/mitigation fixtures. Do not overload this
//   source with expected parser truth or publication-facing corpus membership.

typedef unsigned long x64lens_u64;

static volatile x64lens_u64 x64lens_corpus_sink;

__attribute__((noreturn, no_stack_protector, visibility("hidden")))
void __stack_chk_fail(void) {
    __asm__ volatile(
        "syscall"
        :
        : "a"(60UL), "D"(127UL)
        : "rcx", "r11", "memory"
    );
    __builtin_unreachable();
}

__attribute__((noinline))
static x64lens_u64 x64lens_corpus_mix(x64lens_u64 seed) {
    volatile unsigned char local[64];
    x64lens_u64 value = seed ^ 0x9e3779b97f4a7c15UL;

    for (x64lens_u64 index = 0; index < (x64lens_u64)sizeof(local); ++index) {
        local[index] = (unsigned char)(value + (index * 17UL));
        value = (value << 7) ^ (value >> 3) ^ local[index];
    }

    switch (value & 3UL) {
        case 0:
            value += local[3];
            break;
        case 1:
            value ^= local[11];
            break;
        case 2:
            value -= local[29];
            break;
        default:
            value = (value << 1) | 1UL;
            break;
    }

    x64lens_corpus_sink = value;
    return value;
}

__attribute__((noreturn, visibility("default")))
void _start(void) {
    const x64lens_u64 code = x64lens_corpus_mix(0x58464c454e535631UL) & 0x7fUL;
    __asm__ volatile(
        "syscall"
        :
        : "a"(60UL), "D"(code)
        : "rcx", "r11", "memory"
    );
    __builtin_unreachable();
}
