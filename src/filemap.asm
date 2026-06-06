; filemap.asm
;
; Purpose:
;   File mapping helpers for local target analysis.
;
; Module scope:
;   Open a target path read-only, fstat it, mmap it, and populate a small
;   mapped-file record for parser modules. This module must not interpret the
;   binary format. It only establishes a safe read-only memory view.
;
; Security model:
;   Target files are untrusted. This module maps read-only and never executes
;   target bytes. The caller must still validate all offsets before reading.

bits 64
default rel

%include "constants.inc"
%include "errors.inc"
%include "structs.inc"

extern x64_sys_openat
extern x64_sys_fstat
extern x64_sys_close
extern x64_sys_mmap
extern x64_sys_munmap

section .text
global x64lens_file_map
global x64lens_file_unmap

; x64lens_file_map(path_cstr=rdi, mapped_file_record=rsi) -> rax=status
;
; On success:
;   RAX = EXIT_OK
;   record.fd   = -1 because the fd is closed after mmap succeeds
;   record.size = file size in bytes
;   record.addr = mmap base address
;
; On failure:
;   RAX = stable x64lens error code. The record is left safe for unmap.
x64lens_file_map:
    push    rbx
    push    r12
    push    r13

    mov     r13, rdi            ; save path pointer
    mov     rbx, rsi            ; RBX = mapped-file record pointer

    ; Initialize the record first so cleanup is always safe.
    mov     qword [rbx + FILEMAP_FD], -1
    mov     qword [rbx + FILEMAP_SIZE], 0
    mov     qword [rbx + FILEMAP_ADDR], 0

    ; fd = openat(AT_FDCWD, path, O_RDONLY, 0)
    mov     rdi, AT_FDCWD
    mov     rsi, r13
    mov     rdx, O_RDONLY
    xor     r10, r10
    call    x64_sys_openat
    test    rax, rax
    js      .file_error
    mov     [rbx + FILEMAP_FD], rax

    ; Use a stack-local stat buffer. Sprint 1 only needs st_size.
    sub     rsp, STATBUF_SIZE
    mov     rdi, [rbx + FILEMAP_FD]
    mov     rsi, rsp
    call    x64_sys_fstat
    test    rax, rax
    js      .fstat_failed

    mov     r12, [rsp + STAT_ST_SIZE]
    add     rsp, STATBUF_SIZE

    ; A zero-length file cannot be mmap'd and cannot contain an ELF header.
    test    r12, r12
    jle     .malformed_after_open
    mov     [rbx + FILEMAP_SIZE], r12

    ; addr = mmap(NULL, size, PROT_READ, MAP_PRIVATE, fd, 0)
    xor     rdi, rdi
    mov     rsi, r12
    mov     rdx, PROT_READ
    mov     r10, MAP_PRIVATE
    mov     r8, [rbx + FILEMAP_FD]
    xor     r9, r9
    call    x64_sys_mmap
    test    rax, rax
    js      .mmap_failed
    mov     [rbx + FILEMAP_ADDR], rax

    ; The mapping remains valid after closing the fd. Closing early limits
    ; resource lifetime and simplifies later cleanup.
    mov     rdi, [rbx + FILEMAP_FD]
    call    x64_sys_close
    mov     qword [rbx + FILEMAP_FD], -1

    xor     rax, rax
    jmp     .done

.fstat_failed:
    add     rsp, STATBUF_SIZE
    jmp     .close_file_error

.malformed_after_open:
    mov     rax, EXIT_MALFORMED_ELF
    jmp     .close_with_status

.mmap_failed:
    mov     rax, EXIT_FILE
    jmp     .close_with_status

.close_file_error:
    mov     rax, EXIT_FILE
.close_with_status:
    mov     r12, rax
    mov     rdi, [rbx + FILEMAP_FD]
    cmp     rdi, -1
    je      .restore_status
    call    x64_sys_close
    mov     qword [rbx + FILEMAP_FD], -1
.restore_status:
    mov     rax, r12
    jmp     .done

.file_error:
    mov     rax, EXIT_FILE

.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; x64lens_file_unmap(mapped_file_record=rdi)
;
; Releases resources described by the record. It is safe to call after a
; partial failure as long as x64lens_file_map initialized the record.
x64lens_file_unmap:
    push    rbx
    mov     rbx, rdi

    mov     rdi, [rbx + FILEMAP_ADDR]
    test    rdi, rdi
    je      .maybe_close
    mov     rsi, [rbx + FILEMAP_SIZE]
    test    rsi, rsi
    jle     .maybe_close
    call    x64_sys_munmap
    mov     qword [rbx + FILEMAP_ADDR], 0
    mov     qword [rbx + FILEMAP_SIZE], 0

.maybe_close:
    mov     rdi, [rbx + FILEMAP_FD]
    cmp     rdi, -1
    je      .done
    call    x64_sys_close
    mov     qword [rbx + FILEMAP_FD], -1

.done:
    pop     rbx
    ret
