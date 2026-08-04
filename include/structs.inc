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

; Sprint 12 internal binary-role evidence. These fields preserve raw loader and
; dynamic-table facts without changing the public PIE indicator or schema. The
; binary_role module classifies the bounded evidence after PHDR analysis.
%define PHDR_SUMMARY_INTERP_COUNT    144
%define PHDR_SUMMARY_FLAGS1_COUNT    152
%define PHDR_SUMMARY_FLAGS1_VALUE    160
%define PHDR_SUMMARY_SONAME_COUNT    168
%define PHDR_SUMMARY_SONAME_VALUE    176
%define PHDR_SUMMARY_ROLE_EVIDENCE   184
%define PHDR_SUMMARY_ROLE_STATE      192

; Completed ELF header facts consumed by the role classifier. Keeping these in
; the summary prevents binary_role.asm from reaching back into mapped bytes.
%define PHDR_SUMMARY_ELF_TYPE         200
%define PHDR_SUMMARY_ELF_ENTRY        208

; Private bounded GNU-property evidence. These facts are intentionally not part
; of public schema 0.2.0 yet. The parser records canonical carrier/note views in
; GNU_PROPERTY_CONTEXT and emits only bounded aggregate facts here.
%define PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT        216
%define PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT 224
%define PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT        232
%define PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT    240
%define PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND      248
%define PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR       256
%define PHDR_SUMMARY_RECORD_SIZE                     264

; Internal binary-role lattice. These facts are intentionally not public output
; yet; ET_DYN alone remains insufficient to distinguish PIE from a shared object.
%define BINARY_ROLE_UNKNOWN           0
%define BINARY_ROLE_EXECUTABLE_LIKE   1
%define BINARY_ROLE_SHARED_OBJECT_LIKE 2
%define BINARY_ROLE_AMBIGUOUS         3
%define BINARY_ROLE_CONTRADICTORY     4

; Evidence and contradiction bits retained in PHDR_SUMMARY_ROLE_EVIDENCE.
%define ROLE_EVIDENCE_ET_EXEC          (1 << 0)
%define ROLE_EVIDENCE_ET_DYN           (1 << 1)
%define ROLE_EVIDENCE_ENTRY_NONZERO    (1 << 2)
%define ROLE_EVIDENCE_PT_INTERP        (1 << 3)
%define ROLE_EVIDENCE_DF_1_PIE         (1 << 4)
%define ROLE_EVIDENCE_DT_SONAME        (1 << 5)
%define ROLE_EVIDENCE_DUP_INTERP       (1 << 6)
%define ROLE_EVIDENCE_DUP_FLAGS1       (1 << 7)
%define ROLE_EVIDENCE_DUP_SONAME       (1 << 8)
%define ROLE_EVIDENCE_CONFLICT_FLAGS1  (1 << 9)
%define ROLE_EVIDENCE_CONFLICT_SONAME  (1 << 10)
%define ROLE_EVIDENCE_PARSE_MASK       (ROLE_EVIDENCE_DT_SONAME | ROLE_EVIDENCE_CONFLICT_FLAGS1 | ROLE_EVIDENCE_CONFLICT_SONAME)


; Private GNU-property indicator states. ABSENT is justified only after at least
; one bounded GNU property note was parsed and the named bit was absent from the
; canonical AND evidence. UNKNOWN means no qualifying bounded property evidence.
%define GNU_PROPERTY_STATE_UNKNOWN        0
%define GNU_PROPERTY_STATE_ABSENT         1
%define GNU_PROPERTY_STATE_PRESENT        2
%define GNU_PROPERTY_STATE_CONTRADICTORY  3

; Bounded canonical-view context used only during one command. Original PHDR
; contributor identity is retained separately from canonical physical ranges.
%define GNU_PROPERTY_CARRIER_MAX          32
%define GNU_PROPERTY_CONTRIBUTOR_MAX      64
%define GNU_PROPERTY_NOTE_MAX             32
%define GNU_PROPERTY_NOTE_SCAN_MAX        256
%define GNU_PROPERTY_ENTRY_MAX            256
%define GNU_PROPERTY_DESC_SCAN_MAX        65536
%define GNU_PROPERTY_CARRIER_SCAN_MAX     1048576

%define GNU_PROPERTY_CTX_CARRIER_COUNT      0
%define GNU_PROPERTY_CTX_CONTRIBUTOR_COUNT  8
%define GNU_PROPERTY_CTX_NOTE_COUNT         16
%define GNU_PROPERTY_CTX_UNKNOWN_COUNT      24
%define GNU_PROPERTY_CTX_FEATURE1_COUNT     32
%define GNU_PROPERTY_CTX_CONFLICT_COUNT     40
%define GNU_PROPERTY_CTX_OVERLAP_COUNT      48
%define GNU_PROPERTY_CTX_FEATURE1_AND       56
%define GNU_PROPERTY_CTX_FEATURE1_OR        64
%define GNU_PROPERTY_CTX_IBT_STATE          72
%define GNU_PROPERTY_CTX_SHSTK_STATE        80
%define GNU_PROPERTY_CTX_HEADER_SIZE        88

; Canonical carrier: exact physical offset/size plus carrier-kind and note-
; alignment masks. Exact duplicate PT_NOTE/PT_GNU_PROPERTY carriers share one
; record. Partial overlaps increment the overlap fact and fail malformed before
; any property state reaches a reporter.
;
; ELF note alignment is a carrier property. PT_GNU_PROPERTY requires the
; native ELF64 eight-byte note alignment. PT_NOTE may carry either ordinary
; four-byte note streams or eight-byte GNU-property streams. Exact duplicate
; physical views OR the masks so the canonical parser applies the strongest
; represented alignment once without losing the original contributors.
%define GNU_PROPERTY_CARRIER_OFFSET         0
%define GNU_PROPERTY_CARRIER_SIZE           8
%define GNU_PROPERTY_CARRIER_KIND_MASK      16
%define GNU_PROPERTY_CARRIER_ALIGN_MASK     24
%define GNU_PROPERTY_CARRIER_RECORD_SIZE    32
%define GNU_PROPERTY_CARRIER_KIND_NOTE      (1 << 0)
%define GNU_PROPERTY_CARRIER_KIND_PROPERTY  (1 << 1)
%define GNU_PROPERTY_CARRIER_ALIGN_4         (1 << 0)
%define GNU_PROPERTY_CARRIER_ALIGN_8         (1 << 1)

%define GNU_PROPERTY_CONTRIB_PHDR_INDEX     0
%define GNU_PROPERTY_CONTRIB_PHDR_TYPE      8
%define GNU_PROPERTY_CONTRIB_CARRIER_SLOT   16
%define GNU_PROPERTY_CONTRIB_RECORD_SIZE    24

; Canonical recognized GNU property note view. Exact duplicate note bytes found
; through overlapping/exact-duplicate carriers are represented once.
%define GNU_PROPERTY_NOTE_OFFSET            0
%define GNU_PROPERTY_NOTE_SIZE              8
%define GNU_PROPERTY_NOTE_RECORD_SIZE       16

%define GNU_PROPERTY_CTX_CARRIERS           GNU_PROPERTY_CTX_HEADER_SIZE
%define GNU_PROPERTY_CTX_CONTRIBUTORS       (GNU_PROPERTY_CTX_CARRIERS + (GNU_PROPERTY_CARRIER_MAX * GNU_PROPERTY_CARRIER_RECORD_SIZE))
%define GNU_PROPERTY_CTX_NOTES              (GNU_PROPERTY_CTX_CONTRIBUTORS + (GNU_PROPERTY_CONTRIBUTOR_MAX * GNU_PROPERTY_CONTRIB_RECORD_SIZE))
%define GNU_PROPERTY_CONTEXT_SIZE           (GNU_PROPERTY_CTX_NOTES + (GNU_PROPERTY_NOTE_MAX * GNU_PROPERTY_NOTE_RECORD_SIZE))

; Private bounded dynamic-metadata side-car. The GNU-property context remains
; the first member of the composite private metadata buffer so existing private
; property offsets retain their meaning. Patch 075 established the stable first
; 2,128-byte DT_TEXTREL/DF_TEXTREL view. Patch 076 appends distinct bounded
; DT_RPATH and DT_RUNPATH carrier/value evidence without reinterpreting that
; accepted prefix or changing public schema 0.2.0.
%define DYNAMIC_METADATA_STATE_UNKNOWN        0
%define DYNAMIC_METADATA_STATE_ABSENT         1
%define DYNAMIC_METADATA_STATE_PRESENT        2
%define DYNAMIC_METADATA_STATE_CONTRADICTORY  3

; All represented DT_TEXTREL, DT_FLAGS, DT_RPATH, and DT_RUNPATH records share
; one mixed-family carrier budget. Carrier 65 fails closed before report output.
%define DYNAMIC_METADATA_CARRIER_MAX          64

%define DYNAMIC_METADATA_CTX_CARRIER_COUNT          0
%define DYNAMIC_METADATA_CTX_TEXTREL_TAG_COUNT      8
%define DYNAMIC_METADATA_CTX_FLAGS_COUNT            16
%define DYNAMIC_METADATA_CTX_FLAGS_FIRST_VALUE      24
%define DYNAMIC_METADATA_CTX_FLAGS_AND              32
%define DYNAMIC_METADATA_CTX_FLAGS_OR               40
%define DYNAMIC_METADATA_CTX_FULL_VALUE_CONFLICTS   48
%define DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS      56
%define DYNAMIC_METADATA_CTX_TABLE_COMPLETE         64
%define DYNAMIC_METADATA_CTX_TEXTREL_STATE           72
%define DYNAMIC_METADATA_CTX_HEADER_SIZE             80

%define DYNAMIC_METADATA_CARRIER_TAG          0
%define DYNAMIC_METADATA_CARRIER_INDEX        8
%define DYNAMIC_METADATA_CARRIER_FILE_OFFSET  16
%define DYNAMIC_METADATA_CARRIER_VALUE        24
%define DYNAMIC_METADATA_CARRIER_RECORD_SIZE  32

%define DYNAMIC_METADATA_CTX_CARRIERS DYNAMIC_METADATA_CTX_HEADER_SIZE
%define DYNAMIC_METADATA_CONTEXT_V1_SIZE     (DYNAMIC_METADATA_CTX_CARRIERS + (DYNAMIC_METADATA_CARRIER_MAX * DYNAMIC_METADATA_CARRIER_RECORD_SIZE))

; Search-path facts are byte-preserving metadata only. Values are copied from a
; checked DT_STRTAB/DT_STRSZ view into one 4,096-byte aggregate pool. They are
; never split on ':', expanded ($ORIGIN included), resolved against the host
; filesystem, opened, or collapsed into a loader/security judgment.
%define DYNAMIC_METADATA_SEARCH_RECORD_MAX    64
%define DYNAMIC_METADATA_SEARCH_BYTES_MAX     4096
%define DYNAMIC_METADATA_SEARCH_FIRST_NONE    0xffffffffffffffff

%define DYNAMIC_METADATA_CTX_SEARCH_RECORD_COUNT       DYNAMIC_METADATA_CONTEXT_V1_SIZE
%define DYNAMIC_METADATA_CTX_SEARCH_BYTES_USED         (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 8)
%define DYNAMIC_METADATA_CTX_RPATH_CARRIER_COUNT       (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 16)
%define DYNAMIC_METADATA_CTX_RUNPATH_CARRIER_COUNT     (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 24)
%define DYNAMIC_METADATA_CTX_RPATH_VALUE_COUNT         (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 32)
%define DYNAMIC_METADATA_CTX_RUNPATH_VALUE_COUNT       (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 40)
%define DYNAMIC_METADATA_CTX_RPATH_VALUE_CONFLICTS     (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 48)
%define DYNAMIC_METADATA_CTX_RUNPATH_VALUE_CONFLICTS   (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 56)
%define DYNAMIC_METADATA_CTX_RPATH_FIRST_RECORD        (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 64)
%define DYNAMIC_METADATA_CTX_RUNPATH_FIRST_RECORD      (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 72)
%define DYNAMIC_METADATA_CTX_RPATH_STATE               (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 80)
%define DYNAMIC_METADATA_CTX_RUNPATH_STATE             (DYNAMIC_METADATA_CONTEXT_V1_SIZE + 88)
%define DYNAMIC_METADATA_SEARCH_HEADER_SIZE            96

%define DYNAMIC_METADATA_SEARCH_RECORD_TAG                  0
%define DYNAMIC_METADATA_SEARCH_RECORD_INDEX                8
%define DYNAMIC_METADATA_SEARCH_RECORD_DYNAMIC_FILE_OFFSET  16
%define DYNAMIC_METADATA_SEARCH_RECORD_STRING_TABLE_OFFSET  24
%define DYNAMIC_METADATA_SEARCH_RECORD_STRING_FILE_OFFSET   32
%define DYNAMIC_METADATA_SEARCH_RECORD_BYTE_POOL_OFFSET     40
%define DYNAMIC_METADATA_SEARCH_RECORD_BYTE_LENGTH          48
%define DYNAMIC_METADATA_SEARCH_RECORD_SIZE                 56

%define DYNAMIC_METADATA_CTX_SEARCH_RECORDS (DYNAMIC_METADATA_CONTEXT_V1_SIZE + DYNAMIC_METADATA_SEARCH_HEADER_SIZE)
%define DYNAMIC_METADATA_CTX_SEARCH_BYTES   (DYNAMIC_METADATA_CTX_SEARCH_RECORDS + (DYNAMIC_METADATA_SEARCH_RECORD_MAX * DYNAMIC_METADATA_SEARCH_RECORD_SIZE))
%define DYNAMIC_METADATA_CONTEXT_SIZE       (DYNAMIC_METADATA_CTX_SEARCH_BYTES + DYNAMIC_METADATA_SEARCH_BYTES_MAX)

%define PRIVATE_METADATA_GNU_PROPERTY_OFFSET 0
%define PRIVATE_METADATA_DYNAMIC_OFFSET      GNU_PROPERTY_CONTEXT_SIZE
%define PRIVATE_METADATA_CONTEXT_SIZE        (GNU_PROPERTY_CONTEXT_SIZE + DYNAMIC_METADATA_CONTEXT_SIZE)

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
%define INTERP_PATH_SCAN_MAX          4096

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
%define EXEC_REGION_PHDR_INDEX      36
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

; Sprint 10 Patch 051 architectural-effect side-car. This fixed-size dense
; record carries register, represented flag, stack-source, and control-flow
; facts that do not belong in the scanner-owned gadget_record. The side-car is
; materialized after exact classification and structured memory effects, then
; consumed by scoring and reporters. It adds exactly 96 KiB at capacity.
%define CANDIDATE_EFFECT_ARENA_BYTES     (CANDIDATE_EFFECT_RECORD_SIZE * GADGET_RECORD_MAX)
%define CANDIDATE_EFFECT_RECORD_ALIGN    16
%define ANALYSIS_RECORD_ARENA_BYTES      (GADGET_RECORD_ARENA_BYTES + CANDIDATE_EVIDENCE_ARENA_BYTES + MEMORY_EFFECT_ARENA_BYTES + CANDIDATE_EFFECT_ARENA_BYTES)

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
; Sprint 12 Patch 063 maps each retained candidate back to the dense executable
; region slots whose file and virtual coordinates justify that observation.
; The mask is internal provenance; it does not redefine public candidate counts.
%define CANDIDATE_EVIDENCE_REGION_MASK           48
%define CANDIDATE_EVIDENCE_RECORD_SIZE           56

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

; candidate_effect_record offsets
;
; Patch 051 adds exact architectural effects without growing gadget_record.
; Array position is the candidate key. The descriptor is intentionally compact:
; current exact families need represented flags, control flow, and bounded stack
; source facts, while detailed memory operands remain in memory_effect_record.
%define CANDIDATE_EFFECT_REGS_READ                0
%define CANDIDATE_EFFECT_REGS_WRITTEN             8
%define CANDIDATE_EFFECT_DESCRIPTOR               16
%define CANDIDATE_EFFECT_RECORD_SIZE              24

%define CANDIDATE_EFFECT_FLAG_PRESENT             (1 << 0)
%define CANDIDATE_EFFECT_FLAG_MODEL_COMPLETE      (1 << 1)
%define CANDIDATE_EFFECT_FLAG_STACK_OFFSETS_KNOWN (1 << 2)
%define CANDIDATE_EFFECT_STACK_BASE_SHIFT         3
%define CANDIDATE_EFFECT_STACK_BASE_MASK          0x03
%define CANDIDATE_EFFECT_STACK_BASE_NONE          0
%define CANDIDATE_EFFECT_STACK_BASE_ENTRY_RSP     1
%define CANDIDATE_EFFECT_STACK_BASE_ENTRY_RBP     2
%define CANDIDATE_EFFECT_STACK_BASE_DYNAMIC       3
%define CANDIDATE_EFFECT_CONTROL_RETURN           (1 << 5)
%define CANDIDATE_EFFECT_CONTROL_SYSCALL          (1 << 6)
%define CANDIDATE_EFFECT_STACK_READ_COUNT_SHIFT   8
%define CANDIDATE_EFFECT_STACK_READ_COUNT_MASK    0x0f
%define CANDIDATE_EFFECT_STACK_WRITE_COUNT_SHIFT  12
%define CANDIDATE_EFFECT_STACK_WRITE_COUNT_MASK   0x0f
%define CANDIDATE_EFFECT_FIRST_READ_SHIFT         16
%define CANDIDATE_EFFECT_FIRST_READ_MASK          0xff
%define CANDIDATE_EFFECT_READ_STRIDE_SHIFT        24
%define CANDIDATE_EFFECT_READ_STRIDE_MASK         0xff
%define CANDIDATE_EFFECT_FLAGS_READ_SHIFT         32
%define CANDIDATE_EFFECT_FLAGS_WRITE_SHIFT        48
%define CANDIDATE_EFFECT_FLAGS_MASK               0xffff

; Represented architectural flag bits. The current stack-adjustment family
; writes the arithmetic-status subset. SYSCALL reads/saves the represented
; RFLAGS subset into R11 but remains model-incomplete because kernel-mediated
; behavior is outside static suffix analysis.
%define ARCH_FLAG_CF                              (1 << 0)
%define ARCH_FLAG_PF                              (1 << 1)
%define ARCH_FLAG_AF                              (1 << 2)
%define ARCH_FLAG_ZF                              (1 << 3)
%define ARCH_FLAG_SF                              (1 << 4)
%define ARCH_FLAG_TF                              (1 << 5)
%define ARCH_FLAG_IF                              (1 << 6)
%define ARCH_FLAG_DF                              (1 << 7)
%define ARCH_FLAG_OF                              (1 << 8)
%define ARCH_FLAG_ARITHMETIC_WRITE_MASK           (ARCH_FLAG_CF | ARCH_FLAG_PF | ARCH_FLAG_AF | ARCH_FLAG_ZF | ARCH_FLAG_SF | ARCH_FLAG_OF)
%define ARCH_FLAG_SYSCALL_READ_MASK               (ARCH_FLAG_CF | ARCH_FLAG_PF | ARCH_FLAG_AF | ARCH_FLAG_ZF | ARCH_FLAG_SF | ARCH_FLAG_TF | ARCH_FLAG_IF | ARCH_FLAG_DF | ARCH_FLAG_OF)

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
%define SIDE_EFFECT_CONTROL_TRANSFER  (1 << 9)

%endif
