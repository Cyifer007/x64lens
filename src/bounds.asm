; bounds.asm
;
; Purpose:
;   Bounds-check helpers for untrusted target-file parsing.
;
; Module scope:
;   Validate file offsets, sizes, pointer ranges, table extents, and
;   overflow-sensitive arithmetic before parser modules read target bytes.
;
; Contract:
;   Keep this module policy-light. It returns true/false facts. Parser modules
;   decide whether a failed check means malformed input, unsupported input, or
;   an internal bounds failure. Helpers in this file must not print, parse ELF
;   policy, or mutate analysis records.

bits 64
default rel

section .text
global x64lens_bounds_has_size
global x64lens_bounds_range_valid
global x64lens_bounds_range_end_valid
global x64lens_bounds_mul_u64_checked
global x64lens_bounds_add_u64_checked
global x64lens_bounds_table_extent_valid
global x64lens_bounds_table_entry_offset

; x64lens_bounds_has_size(file_size=rdi, needed_size=rsi) -> rax=1/0
;
; Returns true when file_size >= needed_size.
x64lens_bounds_has_size:
    xor     rax, rax
    cmp     rdi, rsi
    jb      .done
    mov     rax, 1
.done:
    ret

; x64lens_bounds_range_valid(file_size=rdi, offset=rsi, length=rdx) -> rax=1/0
;
; Returns true when [offset, offset + length) fits inside file_size.
; The check avoids overflow by subtracting offset from file_size before
; comparing length. Use x64lens_bounds_range_end_valid when the caller also
; needs the checked exclusive end offset.
x64lens_bounds_range_valid:
    xor     rax, rax
    cmp     rsi, rdi            ; offset > file_size is invalid
    ja      .done
    mov     rcx, rdi
    sub     rcx, rsi            ; rcx = remaining bytes from offset to EOF
    cmp     rdx, rcx
    ja      .done
    mov     rax, 1
.done:
    ret

; x64lens_bounds_range_end_valid(file_size=rdi, offset=rsi, length=rdx, end_out=rcx)
;   -> rax=1/0
;
; Returns true when offset + length does not overflow and the exclusive end
; offset is <= file_size. On success, stores the exclusive end offset through
; end_out when end_out is nonzero.
x64lens_bounds_range_end_valid:
    xor     rax, rax
    mov     r8, rcx             ; optional output pointer
    mov     r9, rsi             ; preserve offset for checked addition
    add     r9, rdx
    jc      .done
    cmp     r9, rdi
    ja      .done
    test    r8, r8
    jz      .ok
    mov     [r8], r9
.ok:
    mov     rax, 1
.done:
    ret

; x64lens_bounds_mul_u64_checked(a=rdi, b=rsi, out=rdx) -> rax=1/0
;
; Unsigned 64-bit multiply. On success, stores a * b through out when out is
; nonzero. On overflow, returns false and does not store.
x64lens_bounds_mul_u64_checked:
    mov     rcx, rdx            ; optional output pointer
    mov     rax, rdi
    mul     rsi                 ; unsigned RDX:RAX = RAX * RSI
    test    rdx, rdx
    jnz     .overflow
    test    rcx, rcx
    jz      .ok
    mov     [rcx], rax
.ok:
    mov     rax, 1
    ret
.overflow:
    xor     rax, rax
    ret

; x64lens_bounds_add_u64_checked(a=rdi, b=rsi, out=rdx) -> rax=1/0
;
; Unsigned 64-bit addition. On success, stores a + b through out when out is
; nonzero. On carry, returns false and does not store.
x64lens_bounds_add_u64_checked:
    mov     rcx, rdx            ; optional output pointer
    mov     rax, rdi
    add     rax, rsi
    jc      .overflow
    test    rcx, rcx
    jz      .ok
    mov     [rcx], rax
.ok:
    mov     rax, 1
    ret
.overflow:
    xor     rax, rax
    ret

; x64lens_bounds_table_extent_valid(file_size=rdi, table_offset=rsi,
;                                   entry_size=rdx, entry_count=rcx,
;                                   table_end_out=r8) -> rax=1/0
;
; Validates the full byte extent of a file-backed table:
;   entry_count * entry_size must not overflow,
;   table_offset + table_bytes must not overflow,
;   table_end must be <= file_size.
;
; A zero-count table is considered empty and valid when table_offset <=
; file_size. When table_end_out is nonzero, the checked exclusive table end is
; stored on success.
x64lens_bounds_table_extent_valid:
    xor     rax, rax
    mov     r9, r8              ; optional output pointer

    test    rcx, rcx
    jnz     .nonzero_count
    cmp     rsi, rdi
    ja      .done
    test    r9, r9
    jz      .empty_ok
    mov     [r9], rsi
.empty_ok:
    mov     rax, 1
    ret

.nonzero_count:
    test    rdx, rdx            ; nonzero count needs a nonzero stride
    jz      .done

    mov     r8, rdi             ; file_size
    mov     r10, rsi            ; table_offset
    mov     rax, rdx            ; entry_size
    mul     rcx                 ; RDX:RAX = entry_size * entry_count
    test    rdx, rdx
    jnz     .done

    add     rax, r10            ; checked table_end
    jc      .done
    cmp     rax, r8
    ja      .done
    test    r9, r9
    jz      .ok
    mov     [r9], rax
.ok:
    mov     rax, 1
.done:
    ret

; x64lens_bounds_table_entry_offset(file_size=rdi, table_offset=rsi,
;                                   entry_size=rdx, entry_count=rcx,
;                                   index=r8, entry_offset_out=r9) -> rax=1/0
;
; Computes the file offset for one table entry only when:
;   entry_size is nonzero,
;   index < entry_count,
;   index * entry_size does not overflow,
;   table_offset + entry_delta does not overflow,
;   [entry_offset, entry_offset + entry_size) fits inside file_size.
;
; This is the narrow assembly helper form of the bounded-table view described
; in the architecture docs. It deliberately returns an offset, not a pointer,
; so the caller remains responsible for adding the already-trusted mmap base.
x64lens_bounds_table_entry_offset:
    xor     rax, rax
    test    rcx, rcx
    jz      .done
    cmp     r8, rcx
    jae     .done
    test    rdx, rdx
    jz      .done
    test    r9, r9
    jz      .done

    mov     r10, rdx            ; entry_size
    mov     r11, rsi            ; table_offset
    mov     rax, r10
    mul     r8                  ; RDX:RAX = entry_size * index
    test    rdx, rdx
    jnz     .done

    add     rax, r11            ; entry_offset
    jc      .done

    mov     rdx, rax            ; entry_end = entry_offset + entry_size
    add     rdx, r10
    jc      .done
    cmp     rdx, rdi
    ja      .done

    mov     [r9], rax
    mov     rax, 1
.done:
    ret
