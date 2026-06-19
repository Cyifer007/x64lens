; cli.asm
;
; Purpose:
;   CLI helper routines for command string comparison and usage output. This
;   module should remain focused on user input and should not contain ELF
;   parsing, gadget scanning, reporting, or scoring logic.
;
; Current exported routines:
;   cstr_eq(a, b) -> 1 if equal, 0 otherwise
;   cli_parse_u64(decimal_cstr) -> rax=value, rdx=1 on success or 0 on failure
;   cli_print_help()
;
; Sprint 2 status:
;   The `info <file>` command routes through info.asm. The `mitigations <file>`
;   command routes through mitigations.asm. Sprint 3 adds `gadgets <file>` and
;   a narrow `--max-depth N` option for raw scanner validation. CLI text should
;   stay synchronized with docs/cli-contract.md and tests/run-tests.sh.

bits 64
default rel

extern print_cstr

section .rodata
help_text:
    db "x64lens 0.1.0-dev", 10
    db "", 10
    db "Usage:", 10
    db "  x64lens help", 10
    db "  x64lens version", 10
    db "  x64lens info <file>", 10
    db "  x64lens mitigations <file>", 10
    db "  x64lens gadgets [--format text|json] [--max-depth N] <file>", 10
    db "  x64lens analyze [--format text|json] [--max-depth N] <file>", 10
    db "", 10
    db "Planned commands:", 10
    db "  x64lens bench <file>", 10, 0

section .text
global cstr_eq
global cli_parse_u64
global cli_print_help

; cstr_eq(rdi=a, rsi=b) -> rax=1 if equal, else 0
;
; Inputs:
;   RDI = pointer to first null-terminated string
;   RSI = pointer to second null-terminated string
;
; Output:
;   RAX = 1 when strings match exactly, otherwise 0
;
; Clobbers:
;   RAX, RBX, RDI, RSI
cstr_eq:
    push    rbx
.loop:
    mov     al, [rdi]
    mov     bl, [rsi]
    cmp     al, bl
    jne     .not_equal
    test    al, al
    je      .equal
    inc     rdi
    inc     rsi
    jmp     .loop
.equal:
    mov     rax, 1
    pop     rbx
    ret
.not_equal:
    xor     rax, rax
    pop     rbx
    ret


; cli_parse_u64(rdi=decimal_cstr) -> rax=value, rdx=1 on success, rdx=0 on failure
;
; Inputs:
;   RDI = pointer to a trusted argv string containing decimal ASCII digits
;
; Output:
;   RAX = parsed unsigned integer when successful, 0 otherwise
;   RDX = success flag: 1 for success, 0 for failure
;
; Scope:
;   This deliberately tiny parser exists for Sprint 3's --max-depth option.
;   It accepts digits only and treats an empty string or non-digit as failure.
;   Overflow detection is intentionally conservative: if multiply/add carries,
;   parsing fails rather than wrapping.
;
; Clobbers:
;   RAX, RBX, RCX, RDX, RDI
cli_parse_u64:
    push    rbx

    xor     rax, rax            ; accumulated value
    xor     rdx, rdx            ; success flag starts false
    xor     rcx, rcx            ; digit count

.parse_loop:
    movzx   ebx, byte [rdi]
    test    bl, bl
    je      .end_of_string
    cmp     bl, '0'
    jb      .fail
    cmp     bl, '9'
    ja      .fail

    ; rax = rax * 10 + digit, with carry checks to avoid wrapping.
    imul    rax, rax, 10
    jo      .fail
    sub     bl, '0'
    add     rax, rbx
    jc      .fail

    inc     rdi
    inc     rcx
    jmp     .parse_loop

.end_of_string:
    test    rcx, rcx
    je      .fail
    mov     rdx, 1
    pop     rbx
    ret

.fail:
    xor     rax, rax
    xor     rdx, rdx
    pop     rbx
    ret

; Print stable command help. Keep this synchronized with docs/cli-contract.md.
cli_print_help:
    lea     rdi, [help_text]
    call    print_cstr
    ret
