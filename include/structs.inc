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
%define PHDR_SUMMARY_STRIPPED_STATE 136
%define PHDR_SUMMARY_RECORD_SIZE    144

; Canary indicator states. This is an evidence-qualified static indicator,
; not proof that every function in the target is stack-protected.
%define CANARY_STATE_UNKNOWN         0
%define CANARY_STATE_ABSENT          1
%define CANARY_STATE_PRESENT         2

; Stripped indicator states. This is section-header evidence only. A missing
; section table leaves the state unknown. A validated section table without
; SHT_SYMTAB is treated as stripped. A validated SHT_SYMTAB is not stripped.
%define STRIPPED_STATE_UNKNOWN       0
%define STRIPPED_STATE_STRIPPED      1
%define STRIPPED_STATE_NOT_STRIPPED  2

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
%define EXEC_REGION_SECTION_NAME_PTR 40
%define EXEC_REGION_SECTION_NAME_LEN 48
%define EXEC_REGION_SECTION_INDEX    56
%define EXEC_REGION_RECORD_SIZE      64

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
%define GADGET_SUMMARY_REG_TRANSFER_COUNT 120
%define GADGET_SUMMARY_MEMORY_WRITE_COUNT 128
%define GADGET_SUMMARY_MEMORY_READ_COUNT  136
%define GADGET_SUMMARY_RECORD_SIZE        144

; analysis_summary record offsets
;
; Sprint 9 keeps report identity and run-completeness facts separate from the
; scanner-owned gadget summary and candidate records. The record is fixed-size,
; command-lifetime state that both text and JSON reporters consume. It is
; populated only after the shared analysis pipeline completes successfully.
;
; Candidate truncation remains false for emitted reports in Patch 040 because
; arena exhaustion still fails before report emission. A future deliberate
; partial-report mode can populate the same fields without redefining existing
; raw, exact, semantic, unknown, or scored counts.
%define ANALYSIS_SUMMARY_REPORT_TYPE             0
%define ANALYSIS_SUMMARY_COMMAND                 8
%define ANALYSIS_SUMMARY_MAX_DEPTH               16
%define ANALYSIS_SUMMARY_CANDIDATE_CAPACITY      24
%define ANALYSIS_SUMMARY_CANDIDATE_COUNT         32
%define ANALYSIS_SUMMARY_CANDIDATE_TRUNCATED     40
%define ANALYSIS_SUMMARY_DROPPED_COUNT           48
%define ANALYSIS_SUMMARY_DROPPED_COUNT_KNOWN     56
%define ANALYSIS_SUMMARY_REGIONS_SCANNED         64
%define ANALYSIS_SUMMARY_REGIONS_TOTAL           72
%define ANALYSIS_SUMMARY_COMPLETE                80
%define ANALYSIS_SUMMARY_RECORD_SIZE             88

; Public report and command identities stored in analysis_summary.
%define REPORT_TYPE_ANALYSIS                     1
%define REPORT_COMMAND_GADGETS                    1
%define REPORT_COMMAND_ANALYZE                    2

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

; Sprint 9 candidate evidence side-car capacity. The evidence array is dense and
; keyed by the same candidate index as gadget_record[]. It lives in the same
; command-lifetime arena without changing the scanner-owned gadget record stride.
%define CANDIDATE_EVIDENCE_ARENA_BYTES     (CANDIDATE_EVIDENCE_RECORD_SIZE * GADGET_RECORD_MAX)
%define CANDIDATE_EVIDENCE_RECORD_ALIGN 16

; Sprint 10 memory-effect side-car. The dense record is keyed by candidate index
; and remains separate from scanner-owned candidate facts and provenance. The
; packed 16-byte layout adds at most 64 KiB at the 4096-candidate boundary.
%define MEMORY_EFFECT_ARENA_BYTES        (MEMORY_EFFECT_RECORD_SIZE * GADGET_RECORD_MAX)
%define MEMORY_EFFECT_RECORD_ALIGN       16
%define ANALYSIS_RECORD_ARENA_BYTES      (GADGET_RECORD_ARENA_BYTES + CANDIDATE_EVIDENCE_ARENA_BYTES + MEMORY_EFFECT_ARENA_BYTES)

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
%define PATTERN_MULTI_POP_RET          21
%define PATTERN_MOV_REG_REG_RET        22
%define PATTERN_ADD_RSP_IMM8_RET       23
%define PATTERN_MOV_MEM_REG_RET        24
%define PATTERN_MOV_REG_MEM_RET        25

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
%define GADGET_SECTION_NAME_PTR     80
%define GADGET_SECTION_NAME_LEN     88
%define GADGET_SECTION_INDEX        96
; Sprint 10 reuses the reserved final eight bytes of the existing 112-byte
; record for bounded exact-pattern register operands. Pop patterns store
; execution order, least-significant nibble first. Register-transfer patterns
; store destination then source. Memory patterns store base then value register;
; the pattern ID establishes read or write direction. The explicit count makes
; register ID zero (RAX) unambiguous and keeps the raw-record footprint stable.
%define GADGET_PATTERN_REG_COUNT    104
%define GADGET_PATTERN_REG_ORDER    108
%define GADGET_RECORD_SIZE          112

; candidate_evidence_record offsets
;
; Sprint 9 keeps provenance in a fixed-size dense side-car keyed by candidate
; index. The record describes evidence already present in the raw/exact/semantic
; pipeline; it does not decode instructions, assign scores, or change counts.
; matched_suffix_offset is a zero-based byte offset within the retained raw
; candidate window. The offset/length pair is meaningful only when the exact
; suffix flag is set.
%define CANDIDATE_EVIDENCE_FLAGS                0
%define CANDIDATE_EVIDENCE_SEMANTIC_SOURCE      8
%define CANDIDATE_EVIDENCE_VALIDATOR_ID         16
%define CANDIDATE_EVIDENCE_FULL_SEQUENCE_STATE  24
%define CANDIDATE_EVIDENCE_SUFFIX_OFFSET        32
%define CANDIDATE_EVIDENCE_SUFFIX_LENGTH        40
%define CANDIDATE_EVIDENCE_RECORD_SIZE          48

; memory_effect_record offsets
;
; Sprint 10 keeps structured memory facts in a separate dense side-car keyed by
; candidate index. DESCRIPTOR packs presence/direction, operand register IDs,
; scale, and width. DISPLACEMENT is signed and meaningful only when the
; displacement-known flag is set. The current family uses base+0 addressing,
; no index, scale 1, and width 8.
%define MEMORY_EFFECT_DESCRIPTOR                 0
%define MEMORY_EFFECT_DISPLACEMENT               8
%define MEMORY_EFFECT_RECORD_SIZE               16

%define MEMORY_EFFECT_FLAG_PRESENT              (1 << 0)
%define MEMORY_EFFECT_FLAG_READ                 (1 << 1)
%define MEMORY_EFFECT_FLAG_WRITE                (1 << 2)
%define MEMORY_EFFECT_FLAG_DEREFERENCE          (1 << 3)
%define MEMORY_EFFECT_FLAG_DISPLACEMENT_KNOWN   (1 << 4)
%define MEMORY_EFFECT_FLAG_INDEX_PRESENT        (1 << 5)
%define MEMORY_EFFECT_BASE_SHIFT                 8
%define MEMORY_EFFECT_INDEX_SHIFT               12
%define MEMORY_EFFECT_VALUE_SHIFT               16
%define MEMORY_EFFECT_SCALE_SHIFT               20
%define MEMORY_EFFECT_WIDTH_SHIFT               24
%define MEMORY_EFFECT_REG_MASK                   0x0f
%define MEMORY_EFFECT_SCALE_MASK                 0x03
%define MEMORY_EFFECT_WIDTH_MASK                 0xff
%define MEMORY_EFFECT_SCALE_1                    0
%define MEMORY_EFFECT_SCALE_2                    1
%define MEMORY_EFFECT_SCALE_4                    2
%define MEMORY_EFFECT_SCALE_8                    3
%define MEMORY_EFFECT_WIDTH_QWORD                8

; Additive evidence flags. Future decoder validation must add facts without
; erasing raw or exact observations.
%define EVIDENCE_FLAG_RAW_CANDIDATE              (1 << 0)
%define EVIDENCE_FLAG_EXACT_SUFFIX               (1 << 1)
%define EVIDENCE_FLAG_SEMANTIC_EXACT             (1 << 2)
%define EVIDENCE_FLAG_DECODER_VALIDATED          (1 << 3)

; Semantic evidence source. NONE is required for raw-only and exact-only
; candidates; current semantic promotions use the exact-suffix source.
%define EVIDENCE_SEMANTIC_SOURCE_NONE            0
%define EVIDENCE_SEMANTIC_SOURCE_EXACT           1
%define EVIDENCE_SEMANTIC_SOURCE_DECODED         2

; Stable validator identities rendered by report_json.asm.
%define EVIDENCE_VALIDATOR_RAW_SCANNER           1
%define EVIDENCE_VALIDATOR_EXACT_SUFFIX          2
%define EVIDENCE_VALIDATOR_DECODER               3

; Full-sequence validity is deliberately unknown until a decoder validates the
; selected candidate start through its terminator.
%define EVIDENCE_FULL_SEQUENCE_UNKNOWN           0
%define EVIDENCE_FULL_SEQUENCE_INVALID           1
%define EVIDENCE_FULL_SEQUENCE_VALID             2

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

; Exact-pattern register metadata supports up to eight ordered register IDs in
; one dword. Sprint 10 emits one or two entries only. Pop patterns use execution
; order; the register-transfer family uses destination then source.
%define PATTERN_REG_ORDER_MAX       8
%define ARG_CONTROL_REG_MASK        ((1 << REG_RDI_BIT) | (1 << REG_RSI_BIT) | (1 << REG_RDX_BIT) | (1 << REG_RCX_BIT) | (1 << REG_R8_BIT) | (1 << REG_R9_BIT))

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
%define STACK_DELTA_TWO_POP_RET     24

; side-effect flags. These are intentionally minimal and should be
; extended only when classifier/scoring behavior needs the distinction.
%define SIDE_EFFECT_NONE            0
%define SIDE_EFFECT_STACK_READ      (1 << 0)
%define SIDE_EFFECT_STACK_PIVOT     (1 << 1)
%define SIDE_EFFECT_SYSCALL         (1 << 2)
%define SIDE_EFFECT_RET_IMM16       (1 << 3)
%define SIDE_EFFECT_REGISTER_WRITE   (1 << 4)
%define SIDE_EFFECT_STACK_ADJUST     (1 << 5)
%define SIDE_EFFECT_FLAGS_WRITE      (1 << 6)
%define SIDE_EFFECT_MEMORY_READ      (1 << 7)
%define SIDE_EFFECT_MEMORY_WRITE     (1 << 8)

%endif
