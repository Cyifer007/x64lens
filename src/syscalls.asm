; syscalls.asm
;
; Purpose:
;   Thin Linux x86_64 syscall wrappers. These are intentionally small and
;   boring so higher-level modules can call named routines instead of
;   scattering syscall numbers everywhere.
;
; Design rule:
;   Wrappers should not hide policy. They perform one syscall and return the
;   kernel result in RAX. Callers decide how to interpret errors and cleanup.

bits 64
default rel

%include "constants.inc"

section .text
global x64_sys_write
global x64_sys_exit
global x64_sys_openat
global x64_sys_fstat
global x64_sys_close
global x64_sys_mmap
global x64_sys_munmap

; x64_sys_write(fd=rdi, buf=rsi, len=rdx) -> rax
x64_sys_write:
    mov     rax, SYS_WRITE
    syscall
    ret

; x64_sys_exit(code=rdi), does not return.
x64_sys_exit:
    mov     rax, SYS_EXIT
    syscall
    hlt

; x64_sys_openat(dirfd=rdi, pathname=rsi, flags=rdx, mode=r10) -> rax
; Sprint 1 will use AT_FDCWD + O_RDONLY for local target files.
x64_sys_openat:
    mov     rax, SYS_OPENAT
    syscall
    ret

; x64_sys_fstat(fd=rdi, statbuf=rsi) -> rax
; The caller owns stat buffer layout and size assumptions.
x64_sys_fstat:
    mov     rax, SYS_FSTAT
    syscall
    ret

; x64_sys_close(fd=rdi) -> rax
x64_sys_close:
    mov     rax, SYS_CLOSE
    syscall
    ret

; x64_sys_mmap(addr=rdi, len=rsi, prot=rdx, flags=r10, fd=r8, off=r9) -> rax
x64_sys_mmap:
    mov     rax, SYS_MMAP
    syscall
    ret

; x64_sys_munmap(addr=rdi, len=rsi) -> rax
x64_sys_munmap:
    mov     rax, SYS_MUNMAP
    syscall
    ret
