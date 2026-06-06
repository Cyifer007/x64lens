; elf64.inc
; ELF64 constants and structure offsets.
;
; Purpose:
;   Defines the byte offsets and numeric constants used to parse ELF64 files
;   without relying on C headers. These offsets are part of the parser
;   correctness contract. Treat target binaries as untrusted input and validate
;   file bounds before reading through any offset defined here.
;
; Maintenance rule:
;   Keep these constants aligned with the System V ELF64 layout. Changes here
;   affect elf64.asm, phdr.asm, shdr.asm, mitigations.asm, and tests.

%ifndef X64LENS_ELF64_INC
%define X64LENS_ELF64_INC

; e_ident offsets
%define EI_MAG0              0
%define EI_MAG1              1
%define EI_MAG2              2
%define EI_MAG3              3
%define EI_CLASS             4
%define EI_DATA              5
%define EI_VERSION           6
%define EI_OSABI             7
%define EI_ABIVERSION        8

; magic bytes
%define ELFMAG0              0x7f
%define ELFMAG1              'E'
%define ELFMAG2              'L'
%define ELFMAG3              'F'

; class and endian
%define ELFCLASS32           1
%define ELFCLASS64           2
%define ELFDATA2LSB          1
%define ELFDATA2MSB          2

; machine
%define EM_X86_64            62

; ELF type
%define ET_NONE              0
%define ET_REL               1
%define ET_EXEC              2
%define ET_DYN               3

; ELF64 header size and field offsets
%define ELF64_EHDR_SIZE      64
%define E_IDENT              0x00
%define E_TYPE               0x10
%define E_MACHINE            0x12
%define E_VERSION_OFF        0x14
%define E_ENTRY              0x18
%define E_PHOFF              0x20
%define E_SHOFF              0x28
%define E_FLAGS              0x30
%define E_EHSIZE             0x34
%define E_PHENTSIZE          0x36
%define E_PHNUM              0x38
%define E_SHENTSIZE          0x3a
%define E_SHNUM              0x3c
%define E_SHSTRNDX           0x3e

; Program header offsets
%define ELF64_PHDR_SIZE      56
%define P_TYPE               0x00
%define P_FLAGS              0x04
%define P_OFFSET             0x08
%define P_VADDR              0x10
%define P_PADDR              0x18
%define P_FILESZ             0x20
%define P_MEMSZ              0x28
%define P_ALIGN              0x30

; Program header types
%define PT_NULL              0
%define PT_LOAD              1
%define PT_DYNAMIC           2
%define PT_INTERP            3
%define PT_NOTE              4
%define PT_SHLIB             5
%define PT_PHDR              6
%define PT_TLS               7
%define PT_GNU_EH_FRAME      0x6474e550
%define PT_GNU_STACK         0x6474e551
%define PT_GNU_RELRO         0x6474e552

; Program header flags
%define PF_X                 0x1
%define PF_W                 0x2
%define PF_R                 0x4

%endif
