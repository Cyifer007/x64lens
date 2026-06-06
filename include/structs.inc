; structs.inc
; Internal record layout contract.
;
; Purpose:
;   Defines internal analysis record layouts and bitmaps used by x64lens.
;   Sprint 1 uses the mapped-file record so filemap.asm can hand safe,
;   normalized file facts to ELF parsing code. Sprint 3 will begin using
;   gadget records so scanners, classifiers, reporters, and benchmarks all
;   consume the same internal facts instead of scraping human-readable text.
;
; Maintenance rule:
;   These offsets are ABI-like inside this repository. If any offset changes,
;   update docs/architecture.md, docs/json-schema.md where applicable, tests,
;   and the active sprint notes.

%ifndef X64LENS_STRUCTS_INC
%define X64LENS_STRUCTS_INC

; mapped_file record offsets
;
; The mapped-file record is intentionally tiny:
;   fd    = open file descriptor, or -1 after mmap succeeds and fd is closed
;   size  = target file size in bytes from fstat(2)
;   addr  = read-only mmap base address
;
; The record is owned by the command orchestrator. filemap.asm populates it,
; elf64.asm validates the mapped bytes, and filemap.asm later unmaps it.
%define FILEMAP_FD              0
%define FILEMAP_SIZE            8
%define FILEMAP_ADDR            16
%define FILEMAP_RECORD_SIZE     24

; gadget_record offsets
%define GADGET_FILE_OFFSET       0
%define GADGET_VIRTUAL_ADDRESS   8
%define GADGET_BYTE_START        16
%define GADGET_BYTE_LEN          24
%define GADGET_TERMINATOR_TYPE   32
%define GADGET_SEMANTIC_CLASS    36
%define GADGET_REGS_CONTROLLED   40
%define GADGET_REGS_CLOBBERED    48
%define GADGET_STACK_DELTA       56
%define GADGET_SIDE_EFFECT_FLAGS 64
%define GADGET_SCORE             72
%define GADGET_RECORD_SIZE       80

; register bitmap bits
%define REG_RAX_BIT              0
%define REG_RBX_BIT              1
%define REG_RCX_BIT              2
%define REG_RDX_BIT              3
%define REG_RSI_BIT              4
%define REG_RDI_BIT              5
%define REG_RBP_BIT              6
%define REG_RSP_BIT              7
%define REG_R8_BIT               8
%define REG_R9_BIT               9
%define REG_R10_BIT              10
%define REG_R11_BIT              11
%define REG_R12_BIT              12
%define REG_R13_BIT              13
%define REG_R14_BIT              14
%define REG_R15_BIT              15

; semantic classes
%define SEM_UNKNOWN_CANDIDATE    0
%define SEM_ARG_CONTROL          1
%define SEM_SYSCALL_NUM_CONTROL  2
%define SEM_SYSCALL_TRIGGER      3
%define SEM_STACK_PIVOT          4
%define SEM_MEMORY_WRITE         5
%define SEM_MEMORY_READ          6
%define SEM_REG_TRANSFER         7
%define SEM_ALIGNMENT            8
%define SEM_CLOBBER_HEAVY        9

%endif
