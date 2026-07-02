; structs.inc
; Internal record layout contract.
;
; Purpose:
;   Defines internal analysis record layouts and bitmaps used by x64lens.
;   Sprint 1 uses the mapped-file record so filemap.asm can hand safe,
;   normalized file facts to ELF parsing code. Sprint 2 adds program-header,
;   executable-region, and mitigation summary records so runtime-relevant ELF
;   facts are stored before being rendered. Sprint 3 will begin using gadget
;   records so scanners, classifiers, reporters, and benchmarks consume the
;   same internal facts instead of scraping human-readable text.
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

; phdr_summary record offsets
;
; Sprint 2 uses this record as the internal fact model for program-header
; and baseline mitigation analysis. Reporting code reads this record. Parser
; code writes it. This keeps analysis separate from text output and prepares
; the tool for JSON output later.
;
; All boolean-style fields are qwords containing 0 or 1. Counts are qwords.
; Dynamic-entry count is the number of bounded Elf64_Dyn records inspected,
; including DT_NULL when present.
%define PHDR_SUMMARY_PHNUM          0
%define PHDR_SUMMARY_LOAD_COUNT     8
%define PHDR_SUMMARY_EXEC_COUNT     16
%define PHDR_SUMMARY_RWX_COUNT      24
%define PHDR_SUMMARY_GNU_STACK_SEEN 32
%define PHDR_SUMMARY_GNU_STACK_EXEC 40
%define PHDR_SUMMARY_RELRO_SEEN     48
%define PHDR_SUMMARY_DYNAMIC_SEEN   56
%define PHDR_SUMMARY_PIE            64
%define PHDR_SUMMARY_DYNAMIC_ENTRY_COUNT 72
%define PHDR_SUMMARY_DYNAMIC_NULL_SEEN   80
%define PHDR_SUMMARY_BIND_NOW       88
%define PHDR_SUMMARY_CANARY_STATE   96
%define PHDR_SUMMARY_DYNAMIC_STRTAB_SEEN 104
%define PHDR_SUMMARY_DYNAMIC_STRTAB_VADDR 112
%define PHDR_SUMMARY_DYNAMIC_STRSZ_SEEN 120
%define PHDR_SUMMARY_DYNAMIC_STRSZ  128
%define PHDR_SUMMARY_RECORD_SIZE    136

; Canary indicator states. This is an evidence-qualified static indicator,
; not proof that every function in the target is stack-protected.
%define CANARY_STATE_UNKNOWN         0
%define CANARY_STATE_ABSENT          1
%define CANARY_STATE_PRESENT         2

; Bounded dynamic-table and dynamic-string views. PT_DYNAMIC entries and
; dynamic string data are scanned only up to these caps so large but
; technically file-backed metadata cannot become unbounded analysis-time sinks.
; Exceeding these limits returns EXIT_UNSUPPORTED.
%define DYNAMIC_ENTRY_MAX            4096
%define DYNAMIC_STRING_SCAN_MAX      1048576
%define CANARY_SYMBOL_LEN_WITH_NUL   17

; executable_region record offsets
;
; Executable regions are derived from PT_LOAD program headers with PF_X set.
; They are the scanner input for Sprint 3 and the human-readable executable
; mapping output for Sprint 2.
%define EXEC_REGION_FILE_OFFSET     0
%define EXEC_REGION_VADDR           8
%define EXEC_REGION_FILESZ          16
%define EXEC_REGION_MEMSZ           24
%define EXEC_REGION_FLAGS           32
%define EXEC_REGION_RECORD_SIZE     40

; Sprint 2 fixed-capacity region buffer. A normal ELF binary should have far
; fewer executable PT_LOAD segments than this. If this limit is exceeded, the
; analyzer returns EXIT_UNSUPPORTED rather than silently truncating facts.
%define EXEC_REGION_MAX             64


; raw gadget scanner summary offsets
;
; Sprint 3 stores scanner-wide facts here before report_text.asm renders
; them. This keeps the scanner independent from output formatting and gives
; future JSON/benchmark emitters the same source of truth.
%define GADGET_SUMMARY_COUNT          0
%define GADGET_SUMMARY_RET_COUNT      8
%define GADGET_SUMMARY_RET_IMM_COUNT  16
%define GADGET_SUMMARY_MAX_DEPTH      24
%define GADGET_SUMMARY_CAPACITY       32
%define GADGET_SUMMARY_PATTERN_COUNT      40
%define GADGET_SUMMARY_SEMANTIC_COUNT     48
%define GADGET_SUMMARY_UNKNOWN_COUNT      56
%define GADGET_SUMMARY_ARG_CONTROL_COUNT  64
%define GADGET_SUMMARY_SYSCALL_NUM_COUNT  72
%define GADGET_SUMMARY_SYSCALL_TRIGGER_COUNT 80
%define GADGET_SUMMARY_STACK_PIVOT_COUNT  88
%define GADGET_SUMMARY_ALIGNMENT_COUNT    96
%define GADGET_SUMMARY_REGS_CONTROLLED    104
%define GADGET_SUMMARY_SCORED_COUNT       112
%define GADGET_SUMMARY_RECORD_SIZE        120

; arena record offsets
;
; Sprint 3 Phase C uses a tiny mmap-backed arena for analysis records that are
; too large or too lifecycle-sensitive to keep in fixed .bss buffers. The first
; consumer is the raw gadget candidate array. Future consumers may include
; semantic records, JSON staging buffers, or benchmark facts.
%define ARENA_BASE                    0
%define ARENA_SIZE                    8
%define ARENA_USED                    16
%define ARENA_RECORD_SIZE             24

; Sprint 3 candidate capacity. The scanner now receives an arena-backed buffer
; from gadgets.asm, but capacity is still bounded to keep behavior stable and
; testable. Later sprints may make this configurable or growable.
%define GADGET_RECORD_MAX             4096
%define GADGET_RECORD_ARENA_BYTES     (GADGET_RECORD_SIZE * GADGET_RECORD_MAX)
%define GADGET_RECORD_ALIGN           16

; raw scanner terminator types
%define GADGET_TERM_RET               1
%define GADGET_TERM_RET_IMM16         2

; exact byte-template pattern identifiers
;
; Sprint 3 Phase D records exact pattern matches separately from semantic
; classes. patterns.asm owns these IDs. classifier.asm translates
; recognized pattern IDs into semantic classes, register bitmaps, stack deltas,
; and scoring inputs. Keeping this separation protects the module boundary
; between byte-template recognition and exploitability interpretation.
%define PATTERN_UNKNOWN               0
%define PATTERN_RET                   1
%define PATTERN_RET_IMM16             2
%define PATTERN_POP_RAX_RET           3
%define PATTERN_POP_RCX_RET           4
%define PATTERN_POP_RDX_RET           5
%define PATTERN_POP_RBX_RET           6
%define PATTERN_POP_RSP_RET           7
%define PATTERN_POP_RBP_RET           8
%define PATTERN_POP_RSI_RET           9
%define PATTERN_POP_RDI_RET           10
%define PATTERN_POP_R8_RET            11
%define PATTERN_POP_R9_RET            12
%define PATTERN_POP_R10_RET           13
%define PATTERN_POP_R11_RET           14
%define PATTERN_POP_R12_RET           15
%define PATTERN_POP_R13_RET           16
%define PATTERN_POP_R14_RET           17
%define PATTERN_POP_R15_RET           18
%define PATTERN_LEAVE_RET             19
%define PATTERN_SYSCALL_RET           20

; gadget_record offsets
%define GADGET_FILE_OFFSET          0
%define GADGET_VIRTUAL_ADDRESS      8
%define GADGET_BYTE_START           16
%define GADGET_BYTE_LEN             24
%define GADGET_TERMINATOR_TYPE      32
%define GADGET_SEMANTIC_CLASS       36
%define GADGET_REGS_CONTROLLED      40
%define GADGET_REGS_CLOBBERED       48
%define GADGET_STACK_DELTA          56
%define GADGET_SIDE_EFFECT_FLAGS    64
%define GADGET_SCORE                72
%define GADGET_PATTERN_ID           76
%define GADGET_RECORD_SIZE          80

; register bitmap bits
%define REG_RAX_BIT                 0
%define REG_RBX_BIT                 1
%define REG_RCX_BIT                 2
%define REG_RDX_BIT                 3
%define REG_RSI_BIT                 4
%define REG_RDI_BIT                 5
%define REG_RBP_BIT                 6
%define REG_RSP_BIT                 7
%define REG_R8_BIT                  8
%define REG_R9_BIT                  9
%define REG_R10_BIT                 10
%define REG_R11_BIT                 11
%define REG_R12_BIT                 12
%define REG_R13_BIT                 13
%define REG_R14_BIT                 14
%define REG_R15_BIT                 15

; semantic classes
%define SEM_UNKNOWN_CANDIDATE       0
%define SEM_ARG_CONTROL             1
%define SEM_SYSCALL_NUM_CONTROL     2
%define SEM_SYSCALL_TRIGGER         3
%define SEM_STACK_PIVOT             4
%define SEM_MEMORY_WRITE            5
%define SEM_MEMORY_READ             6
%define SEM_REG_TRANSFER            7
%define SEM_ALIGNMENT               8
%define SEM_CLOBBER_HEAVY           9

; stack delta constants for first-pass semantic classification. Values are in
; bytes and describe the suffix pattern effect. STACK_DELTA_UNKNOWN is used for
; pivot primitives where RSP becomes input-dependent.
%define STACK_DELTA_UNKNOWN         0
%define STACK_DELTA_RET             8
%define STACK_DELTA_POP_RET         16

; side-effect flags. These are intentionally minimal and should be
; extended only when classifier/scoring behavior needs the distinction.
%define SIDE_EFFECT_NONE            0
%define SIDE_EFFECT_STACK_READ      (1 << 0)
%define SIDE_EFFECT_STACK_PIVOT     (1 << 1)
%define SIDE_EFFECT_SYSCALL         (1 << 2)
%define SIDE_EFFECT_RET_IMM16       (1 << 3)

%endif
