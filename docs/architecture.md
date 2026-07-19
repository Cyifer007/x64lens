# Architecture

## High-level design

x64lens uses a hybrid architecture:

1. **Path 1, engine:** bounded assembly-first ELF64 parsing and gadget candidate scanning.
2. **Path 2, value layer:** semantic primitive classification, mitigation-aware analysis, scoring, and reporting.

```text
x64lens CLI
  -> command orchestrator
  -> file mapper
  -> ELF64 parser
  -> executable region mapper
  -> bounded gadget candidate scanner
  -> pattern matcher and ordered structural facts
  -> semantic primitive classifier and explicit effects
  -> candidate evidence side-car materializer
  -> memory-effect side-car materializer
  -> architectural-effect side-car materializer
  -> scoring engine
  -> mitigation-aware interpretation
  -> text and JSON reporters
```

## Module boundary contract

| Module | Responsibility | Must not do |
| ------ | -------------- | ----------- |
| `main.asm` | Entrypoint, dispatch, high-level flow | Deep parsing or scanning |
| `analyze.asm` | Integrated command orchestration over shared records | Duplicate parser, scanner, classifier, score, or formatter logic |
| `cli.asm` | Argument parsing, command routing helpers | ELF parsing |
| `info.asm` | Coordinate `info` command mapping, validation, reporting, and cleanup | Own ELF parsing or formatting internals |
| `syscalls.asm` | Linux syscall wrappers | Business logic |
| `filemap.asm` | Open, stat, mmap, munmap, close | Interpret binary format |
| `arena.asm` | Command-lifetime mmap-backed allocation for analysis records | Interpret binary format or emit reports |
| `bounds.asm` | Offset, size, and overflow checks | Print user reports |
| `elf64.asm` | ELF64 header validation and metadata | Scan gadgets |
| `phdr.asm` | Program header parsing | Section label formatting |
| `shdr.asm` | Section header metadata, stripped indicator, and section-label annotations | Runtime mapping authority |
| `regions.asm` | Executable region model | Decode instructions |
| `mitigations.asm` | NX, PIE, RELRO, canary indicators, RWX | Claim exploitability alone |
| `scanner.asm` | Candidate byte window discovery | Semantic scoring |
| `patterns.asm` | Exact opcode-template matching, pattern IDs, and bounded ordered structural facts | File parsing, semantic scoring, or exploitability interpretation |
| `classifier.asm` | Semantic primitive classification plus controlled, clobbered, stack, and represented side-effect facts | Raw file I/O or score policy |
| `candidate_evidence.asm` | Dense per-candidate raw/exact-suffix/semantic-exact provenance side-car | Scan bytes, decode instructions, score, or report |
| `memory_effect.asm` | Dense per-candidate structured memory-access side-car | Parse ELF, scan candidates, decide scores, or format output |
| `candidate_effect.asm` | Dense per-candidate architectural GPR, flag, control-flow, stack-source, and model-completeness facts | Parse ELF, scan bytes, classify, score, or format output |
| `scoring.asm` | Gadget and primitive usefulness scoring | CLI handling |
| `analysis_summary.asm` | Command identity and bounded analysis-completeness facts after successful shared analysis | Scan, classify, score, or enable partial output |
| `report_context.asm` | Short-lived text composition context for integrated reports | Analysis decisions or long-lived global state |
| `report_text.asm` | Human-readable output | Analysis decisions |
| `report_json.asm` | JSON output | Analysis decisions |


## Sprint 1 implemented flow: `info <file>`

The Sprint 1 `info` command now follows this flow:

```text
main.asm
  -> x64lens_command_info(path) in info.asm
     -> x64lens_file_map(path, record) in filemap.asm
        -> openat/fstat/mmap/close through syscalls.asm
     -> x64lens_elf64_validate(base, size) in elf64.asm
        -> size/range checks through bounds.asm
     -> x64lens_report_text_elf64_info(path, base, size) in report_text.asm
     -> x64lens_file_unmap(record) in filemap.asm
```

This preserves module boundaries while still giving Sprint 1 a working, demonstrable command.

## Design decision 1: program headers are authoritative

For runtime exploitability reasoning, program headers are the primary execution model because the loader maps segments, not sections. x64lens therefore treats `PT_LOAD` segments with `PF_X` as the authoritative executable regions.

Section headers are still valuable for human readability and are used only to annotate records with labels such as `.text`, `.plt`, `.init`, and `.fini`. They do not select executable regions.

## Design decision 2: direct Linux syscalls

The initial implementation should use Linux syscalls where possible:

- `open` or `openat`,
- `fstat`,
- `mmap`,
- `munmap`,
- `close`,
- `write`,
- `exit`.

This aligns with the assembly-first goal and avoids unnecessary runtime dependencies.

## Design decision 3: pattern-based scanner first

The validated `0.1.0-dev` checkpoint implements a byte-oriented scanner that:

1. finds supported terminator bytes;
2. walks backward up to `--max-depth`;
3. records bounded candidate windows;
4. recognizes exact suffix templates; and
5. promotes only supported exact-suffix facts through the conservative
   classifier.

This preserves raw and exact evidence while leaving an additive decoder seam.

## Future decoder integration contract

A future decoder may augment retained candidate windows through candidate-indexed
side-car facts. It must not replace raw discovery, exact-suffix recognition, or
semantic-exact provenance.

The future interface should look conceptually like:

```text
scan_region(region) -> candidate_windows
candidate_window -> exact_suffix_matcher -> exact_evidence
candidate_window -> optional_decoder -> decode_record
exact_evidence + optional decode_record -> evidence-qualified semantic_record
```

The classifier should consume evidence-qualified instruction facts rather than
infer decoded validity from raw byte windows.

## Design decision 4: scanner and classifier separation

The scanner finds candidate byte windows. The classifier explains what they mean. This separation is mandatory because future research will modify semantic models independently from raw scanning.

## Design decision 5: internal records by Sprint 3

Sprint 1 may print directly after validation. By Sprint 3, analysis facts should be stored in internal records before being emitted as text, JSON, benchmark rows, or future SARIF.

Initial gadget record contract:

```text
gadget_record:
  file_offset                       qword
  virtual_address                   qword
  byte_start                        qword
  byte_len                          qword
  terminator_type                   dword
  semantic_class                    dword
  registers_controlled_bitmap       qword
  registers_clobbered_bitmap        qword
  stack_delta                       qword
  side_effect_flags                 qword
  score                             dword
  pattern_id                        dword
```

Register bitmap:

```text
bit 0  rax
bit 1  rbx
bit 2  rcx
bit 3  rdx
bit 4  rsi
bit 5  rdi
bit 6  rbp
bit 7  rsp
bit 8  r8
bit 9  r9
bit 10 r10
bit 11 r11
bit 12 r12
bit 13 r13
bit 14 r14
bit 15 r15
```

## Design decision 6: arena allocator by the end of Sprint 3

Fixed buffers were acceptable during Sprint 1 and Sprint 2. Sprint 3 Phase A used a fixed candidate buffer to validate scanner correctness first. Sprint 3 Phase C introduces `src/arena.asm`, a minimal mmap-backed bump allocator. The first consumer is the raw `gadget_record` array used by `x64lens gadgets`. Capacity remains bounded, but storage is now command-lifetime arena memory rather than static `.bss` storage.

## Design decision 7: benchmark-first research design

Benchmarking is a first-class feature, not an afterthought. Every analysis change should preserve the ability to measure:

- runtime,
- max RSS,
- throughput,
- gadget count,
- semantic primitive count,
- output size,
- error count.



## Sprint 3 and Sprint 4 implemented flow: `gadgets <file>`

Patch 008 began the Sprint 3 raw scanner path. Patch 010 kept the same scanner/reporting contract while moving candidate storage into an arena. Patch 011 tags raw candidates with exact byte-template pattern IDs. Patch 015 adds Sprint 4 semantic classification over those pattern IDs:

```text
main.asm
  -> x64lens_command_gadgets(path, max_depth) in gadgets.asm
     -> x64lens_file_map(path, record) in filemap.asm
     -> x64lens_elf64_validate(base, size) in elf64.asm
     -> x64lens_phdr_analyze(base, size, summary, regions, max_regions) in phdr.asm
     -> x64lens_arena_init / x64lens_arena_alloc in arena.asm
     -> x64lens_scanner_find_ret_candidates(base, size, phdr_summary, regions, gadget_summary, gadget_records) in scanner.asm
     -> x64lens_patterns_match_exact(mapped_base, gadget_summary, gadget_records) in patterns.asm
     -> x64lens_classifier_apply_exact(gadget_summary, gadget_records, mapped_base) in classifier.asm
     -> x64lens_report_text_gadgets(path, gadget_summary, gadget_records, mapped_base) in report_text.asm
     -> x64lens_file_unmap(record) in filemap.asm
```

The Sprint 3 scanner operates only over executable regions produced from `PT_LOAD + PF_X`. It stores raw facts in bounded `gadget_record` entries before output. After Patch 010, the candidate buffer is arena-backed, but the scanner remains storage-agnostic and receives only a pointer plus capacity metadata. After Patch 011, pattern matching remains separate from semantic classification: `patterns.asm` assigns `PATTERN_*` IDs. Patch 015 implements the first classifier path in `classifier.asm`, which translates supported exact pattern IDs into semantic classes, register bitmaps, stack deltas, side-effect flags, and semantic summary counts.

Current raw candidate semantics:

- `GADGET_FILE_OFFSET` is the terminator byte file offset.
- `GADGET_VIRTUAL_ADDRESS` is the terminator virtual address.
- `GADGET_BYTE_START` is the beginning of the bounded backward byte window.
- `GADGET_BYTE_LEN` is the full raw byte-window length including the terminator.
- `GADGET_TERMINATOR_TYPE` is `ret` or `ret imm16`.
- Semantic, register, stack, and side-effect fields are populated by `classifier.asm` for supported exact patterns as of Patch 015.
- Score fields are populated by `scoring.asm` for supported semantic records. Unknown candidates remain unscored.


## Sprint 4 classifier boundary

The Sprint 4 classifier is intentionally conservative. It consumes `PATTERN_*` IDs, not raw text output, and populates semantic facts only when the exact suffix pattern supports a clear primitive claim. Unsupported exact patterns remain `unknown_candidate`. This preserves the metric boundary between raw candidate discovery, exact suffix labeling, semantic primitive classification, and future scoring.

The current classifier maps:

- `ret` and `ret imm16` to `alignment`,
- `pop rdi/rsi/rdx/rcx/r8/r9; ret` to `arg_control`,
- `pop rax; ret` to `syscall_num_control`,
- `syscall; ret` to `syscall_trigger`,
- `leave; ret` and `pop rsp; ret` to `stack_pivot`.

The classifier does not perform full instruction decoding and does not claim exploitability.

## Future scalability model

Long-term architecture should support:

```text
formats/elf64
formats/pe64
formats/macho64
arch/x86_64
arch/aarch64
arch/riscv64
outputs/text
outputs/json
outputs/sarif
benchmarks/corpus
research/papers
```

The current repository does not split modules that way yet because premature abstraction would slow Sprint 1. The documentation preserves the long-term seam.

## Sprint 2 implemented flow: `mitigations <file>`

The Sprint 2 `mitigations` command follows this flow:

```text
main.asm
  -> x64lens_command_mitigations(path) in mitigations.asm
     -> x64lens_file_map(path, record) in filemap.asm
     -> x64lens_elf64_validate(base, size) in elf64.asm
     -> x64lens_phdr_analyze(base, size, summary, regions, max_regions) in phdr.asm
        -> x64lens_regions_store_from_phdr(regions, index, phdr) in regions.asm
     -> x64lens_report_text_mitigations(path, base, size, summary, regions) in report_text.asm
     -> x64lens_file_unmap(record) in filemap.asm
```

The Sprint 2 internal fact model is split into two record families:

- `phdr_summary`, which stores mitigation and program-header counts.
- `executable_region`, which stores file offsets, virtual addresses, sizes, and flags for executable `PT_LOAD + PF_X` regions.

This keeps the later scanner from needing to rediscover executable byte ranges and keeps reporters from scraping human-readable output.

## Sprint 3 raw scanner behavior

Patch 008 introduced the raw byte scanner. The scanner walks executable `PT_LOAD + PF_X` file-backed ranges, detects return-terminator bytes, extracts bounded backward byte windows, and stores candidate facts in `gadget_record` records before reporting.

Important limitation: this is a byte-pattern scanner, not a full instruction decoder. It may report unaligned raw candidates when a byte such as `0xc2` appears inside another instruction encoding. That remains acceptable because the scanner's role is to discover candidate byte windows. `patterns.asm` and `classifier.asm` add exact suffix labels and first-pass semantic facts, but a future decoder integration layer will be needed before claiming full instruction-sequence validity.

The current `--max-depth` means the maximum number of bytes considered before the terminator. Total printed window length can therefore be `max-depth + terminator_length`, where `ret` has length 1 and `ret imm16` has length 3.


## Sprint 3 exact pattern matching behavior

Patch 011 introduces the first exact byte-template matcher. It recognizes suffix patterns around already-discovered raw return terminators. The implemented Sprint 3 patterns are:

- `ret`,
- `ret imm16`,
- `pop rax; ret`, `pop rcx; ret`, `pop rdx; ret`, `pop rbx; ret`, `pop rsp; ret`, `pop rbp; ret`, `pop rsi; ret`, `pop rdi; ret`,
- `pop r8; ret` through `pop r15; ret`,
- `leave; ret`,
- `syscall; ret`.

This remains byte-template matching, not full decoding. On real binaries, especially for raw `ret imm16` candidates, some pattern labels can still correspond to unaligned byte sequences. Sprint 4 semantic classification preserves this limitation by mapping only supported exact suffix evidence and keeping unsupported cases as `unknown_candidate`.

## Sprint 4 architecture checkpoint

Sprint 4 extends the first full engine-side candidate path with semantic classification:

```text
filemap.asm
  -> elf64.asm
  -> phdr.asm
  -> regions.asm
  -> scanner.asm
  -> arena.asm
  -> patterns.asm
  -> classifier.asm
  -> report_text.asm
```

The implemented layering is intentionally conservative:

- `scanner.asm` discovers raw terminator-centered candidate windows.
- `arena.asm` provides command-lifetime storage for candidate records.
- `patterns.asm` tags exact suffix byte templates.
- `classifier.asm` maps supported exact pattern IDs into semantic primitive facts.
- `scoring.asm` adds the first usefulness layer from semantic facts.
- `report_text.asm` and `report_json.asm` render facts but do not decide facts.

This layering allowed Sprint 5 scoring/JSON and Sprint 6 `analyze` integration to land without rewriting the scanner, pattern matcher, or classifier.

## Exact pattern interpretation rule

A Sprint 3 pattern label describes the exact suffix ending at the terminator, not necessarily the entire raw backward byte window.

Example:

```text
bytes: 5f c3 5e c3
pattern: pop rsi; ret
```

The pattern label means the suffix immediately before the terminator is `5e c3`. The earlier bytes are part of the bounded raw window retained for future decoding and analyst visibility.

## Extension seams

The current design should scale if future work follows these rules:

1. Add semantic fields through `classifier.asm`, not `patterns.asm`.
2. Add score fields through `scoring.asm`, not `classifier.asm`.
3. Add full decoder output as side-car records keyed by candidate index, not by replacing raw candidate records.
4. Keep section labels as optional annotations, not as runtime mapping authority.
5. Add JSON output from internal records, not from text output.
6. Add benchmark summaries from raw TSV results, not from hand-edited tables.

## Candidate record evolution guidance

`gadget_record` is the raw candidate fact record. It should remain stable enough for tests and reporters. If future sprints need decoded instruction sequences, avoid bloating the raw record with variable-length fields. Prefer a side-car model such as:

```text
gadget_record[]
semantic_record[] keyed by candidate index
decode_record[] keyed by candidate index, optional future work
```

This preserves the current scanner while allowing a future decoder, richer classifier, or JSON reporter to evolve independently.

## Sprint 4 implemented classifier layer

Patch 015 adds:

```text
patterns.asm -> classifier.asm -> report_text.asm
```

The first classifier populates:

- semantic class,
- controlled-register bitmap,
- stack delta,
- minimal side-effect flags,
- semantic summary counts,
- controlled-register coverage.

The Sprint 4 classifier intentionally does not decide scores or exploitability. Sprint 5 added scoring in a separate module, and exploitability verdicts remain out of scope.

## Reviewer-readiness architecture seams

Patch 14 records several future-facing seams that should prevent large refactors later.

### NASM engine boundary

The NASM implementation is the first engine, not a claim that every future layer must be pure assembly. The engine should remain small, measurable, and explicit. Higher-level value comes from semantic classification, mitigation-aware interpretation, JSON contracts, and reproducible benchmarks.

### Raw, exact-suffix, semantic-exact, decoder, and score records

Do not collapse all gadget facts into one overloaded record. Preserve this conceptual split:

```text
gadget_record[]        raw candidate facts from scanner.asm
semantic_record[]      semantic facts from classifier.asm, keyed by candidate index
decode_record[]        optional future decoder facts, keyed by candidate index
score_record[]         optional scoring facts, keyed by candidate index
```

This lets a future decoder augment the pipeline without replacing the raw scanner.

### Decoder seam

The future decoder interface should consume candidate windows and produce decoded instruction facts. It should not own file mapping, program-header parsing, executable-region discovery, or raw candidate enumeration.

### Safety seam

Any future parser expansion, especially dynamic-section, symbol-table, string-table, note, and section-label parsing, must preserve the same explicit bounds-checking discipline used by the ELF and program-header paths.

### Metric seam

Raw-candidate, exact-pattern, semantic-candidate, unknown-candidate, and scored-candidate counts must remain distinct in internal records, benchmark TSVs, JSON reports, and paper tables. Any future decoder-validated and semantic-decoded counts remain additive layers.


## Sprint 4 closeout architecture note

Patch 015 validation confirms that semantic classification landed without collapsing module boundaries. The classifier consumes exact pattern IDs from internal records, writes semantic facts back into `gadget_record` and `gadget_summary`, and leaves scoring and JSON generation for later modules.

Two future seams should be preserved:

1. a decode side-car record for future instruction-boundary validation,
2. an explicit stack-delta-known or stack-delta-kind field for JSON and possible text output improvements.


## Design decision 8: scoring and JSON from internal records

Sprint 5 adds the first scoring and JSON output path. Scoring consumes semantic facts in `gadget_record`; JSON consumes internal records and summaries directly. JSON must not scrape text output.

Implemented Sprint 5 pipeline:

```text
scanner -> exact pattern matcher -> semantic classifier -> scoring -> text reporter
                                                     \-> JSON reporter
```

This keeps the repository adaptable because future decoder records, mitigation-aware interpretation, or SARIF output can be added as side-car consumers of the same internal fact model.

Patch 017 intentionally implemented JSON first for `gadgets --format json`. Patch 022 follows the planned seam by implementing `analyze` through the same record model rather than duplicating scanner/classifier/scoring logic.

## Validation architecture added in Sprint 5 Patch 018

Patch 018 does not change the analyzer pipeline. It adds validation infrastructure around the existing pipeline:

```text
controlled fixture -> text report checks -> JSON report validator
system binaries -> info/mitigations/gadgets/json smoke -> JSON report validator
patch ZIP -> hygiene checker -> public source bundle gate
Docker environment -> availability check -> container validation
```

The analyzer boundary remains unchanged:

```text
scanner -> patterns -> classifier -> scoring -> text/json reporters
```

The new validators consume public outputs and generated patch artifacts. They do not become part of the runtime analyzer and do not alter analysis decisions.

## Development-environment guardrail layer

The repository treats development-environment validation as part of the architecture around the analyzer. The assembly engine remains independent of these helper scripts, but the project requires predictable setup and validation before benchmark evidence can be trusted.

Patch 020 adds a diagnostic layer around the build and validation workflow:

```text
Makefile -> tools/check-dev-tools.sh -> build/test/benchmark targets
```

This layer separates:

- build-only requirements,
- toy-corpus sample requirements,
- normal development validation requirements,
- optional baseline comparison tools,
- Docker availability,
- patch-bundle hygiene.

This keeps missing tools from being misdiagnosed as analyzer defects and supports reproducible onboarding for future contributors and reviewers.


## Sprint 6 integrated analyze command

Patch 022 introduces `src/analyze.asm` as a command-level orchestrator for the first integrated checkpoint report.

The command owns orchestration only:

```text
map target read-only
validate ELF64 x86_64 identity
analyze program headers
allocate bounded candidate arena
scan executable PT_LOAD regions
match exact suffix patterns
classify semantic primitives
apply scores
emit text or JSON
cleanup arena and mapping
```

`analyze` deliberately reuses the same internal records used by `info`, `mitigations`, and `gadgets`:

- `mapped_file`,
- `phdr_summary`,
- `executable_region[]`,
- `gadget_summary`,
- arena-backed `gadget_record[]`.

This keeps the checkpoint feature from becoming a second analysis implementation. Text output currently reuses the existing section renderers. JSON output reuses the existing schema-backed gadget report because it already includes target metadata, mitigation facts, metric counts, primitive coverage, scored candidates, and limitations.

Patch 023 completed the single-banner text composition path. A future JSON report identity and evidence wrapper is planned for schema `0.2.0`; that remains an output and provenance change over shared analysis records.

## Integrated text report composition

`analyze` owns orchestration but not section formatting. It emits the complete information report once, then calls body-only mitigation and gadget wrappers from `src/report_context.asm`.

```text
analyze.asm
  -> x64lens_report_text_elf64_info
  -> x64lens_report_text_mitigations_body
  -> x64lens_report_text_gadgets_body
```

The wrappers set a short-lived single-threaded report-context flag. `report_text.asm` skips only the repeated banner and preserves the established section implementations. This avoids duplicate formatting logic and keeps focused command behavior stable.


## Post-checkpoint architecture plan

Patch 024 preserves the validated engine and adds explicit seams for Sprints 7 through 18.

### Bounded parser views

New dynamic, symbol, string, note, and section parsers should consume validated table views rather than repeating open-coded pointer arithmetic. A bounded view should carry enough information to prove each dereference is inside the mapped file:

```text
bounded_table_view:
  file_base
  file_size
  table_offset
  entry_size
  entry_count
  table_end
```

The exact implementation may remain a set of assembly helpers rather than a public record, but the safety invariant is fixed: validate the complete table range and each derived entry before use.

### Evidence side-car records

The raw `gadget_record` remains the scanner-owned candidate fact. Candidate validity and provenance should be added through side-car records keyed by candidate index:

```text
gadget_record[]
candidate_evidence_record[]
decode_record[]          optional
```

This preserves existing raw-candidate, exact-suffix, semantic-exact, unknown-candidate,
and scored metrics while allowing decoder-backed facts to be added later.

### Analysis completeness

Research reports must state whether the scan completed within configured capacity. Future summary state should expose candidate capacity, truncation, dropped count when known, scanned region count, total region count, and overall completion. Silent truncation is not permitted for preview or release evidence.

### Schema boundary

Schema `0.2.0` is the current producer contract after Sprint 9 Patch 040. It adds report and command identity plus complete-analysis state while retaining a versioned `0.1.0` compatibility path. Patch 041 implements per-candidate provenance as an additive, Patch-040-compatible `0.2.x` extension.

### Release architecture

The release path is staged:

```text
v0.1.0-dev  integrated checkpoint
v0.1.0-rc1  hardened preview with corpus and high-resolution benchmark tooling
v0.1.0      fixed research campaign, case study, replication package, and paper-ready evidence
```

See `docs/roadmap-22-sprints.md`, `docs/design/evidence-provenance-model.md`, `docs/design/schema-evolution.md`, and `docs/research-release-plan.md`.

## Sprint 7 hostile-input validation layer

Patch 025 adds a validation layer around the existing parser without placing mutation logic inside the analyzer process:

```text
controlled ELF64 seed
  -> deterministic field mutations
  -> bounded command execution
  -> exit, signal, timeout, timing, and output capture
  -> ignored TSV and metadata evidence
  -> durable regression promotion when a defect is found
```

The analyzer remains responsible for fail-closed validation. The external harness is responsible for deriving reviewed inputs and recording behavior. This separation avoids coupling production parsing code to a development-only mutator.

ELF64 section-header table validation now requires `e_shentsize == 64` whenever `e_shnum != 0`. A merely nonzero stride is insufficient because future section iteration must be able to rely on the fixed ELF64 entry layout.

Candidate-record exhaustion is also an architectural boundary. The scanner arena holds 4096 records. Attempting to append the 4097th candidate returns `EXIT_UNSUPPORTED`; focused and integrated reporters receive no record set and therefore emit no partial text or JSON document. This preserves research-count integrity until a future capacity or streaming design is adopted.

Patch 028 implements the first bounded parser-view seam in assembly. `src/bounds.asm` now owns checked multiplication, checked addition, checked offset-plus-length validation, checked table extents, and bounded per-entry table offsets. `src/elf64.asm` and `src/phdr.asm` consume those helpers before forming program-header pointers or trusting file-backed `PT_LOAD` ranges.

Patch 030 applies that seam to the first Sprint 8 metadata reader. `src/phdr.asm` now treats `PT_DYNAMIC` as a bounded file-backed `Elf64_Dyn` table, validates the dynamic range, caps the inspected entries, derives every entry address through the shared per-entry helper, and records only narrow loader-level facts: bind-now evidence, bounded dynamic-entry count, and `DT_NULL` terminator state. Dynamic metadata does not override `PT_LOAD + PF_X` executable-region authority. Patch 031 consumes the bind-now bit only as mitigation evidence for the RELRO split: `PT_GNU_RELRO` plus bind-now is full RELRO, `PT_GNU_RELRO` without bind-now is partial RELRO, and no `PT_GNU_RELRO` is no RELRO. Patch 032 extends the same bounded evidence path to `DT_STRTAB` and `DT_STRSZ`, then scans only a validated file-backed dynamic string-table range for exact `__stack_chk_fail` canary evidence. Patch 034 preserves half-open range semantics for zero-length dynamic string-table evidence at the exact end of a file-backed load. Patch 035 hardens section-label annotations by escaping text labels, requiring file-backed allocated executable sections, omitting ambiguous executable overlaps, and using stack-local label context.

This is still not a full parser framework. It is the reusable arithmetic layer and first bounded metadata view required before dynamic symbols, relocations, notes, and richer section annotations expand the attack surface.

## Sprint 7 mitigation-oracle validation layer

Patch 026 adds a deterministic program-header fixture builder outside the NASM engine. Temporary controlled ELF64 files exercise the existing `elf64 -> phdr -> mitigation summary -> text/JSON reporter` path. The harness does not bypass internal records or introduce a second mitigation implementation. Shared ELF64 validation now rejects invalid file-backed `PT_LOAD` ranges before any command reports metadata, while `phdr.asm` retains defense-in-depth validation. The matrix, with its Patch 027 zero-region expectation correction, Patch 028 table-end overflow additions, Patch 030 dynamic-table cases, Patch 031 RELRO plus duplicate-dynamic cases, Patch 032 dynamic string-table canary cases, Patch 033 stripped and singleton cases, and Patch 034 zero-length endpoint and section-label checks, is a fixed behavior gate for future mitigation parsing.


## Sprint 7 parser-safety baseline

Sprint 7 establishes the current parser-safety baseline: file-derived table extents and per-entry offsets must flow through checked helpers before pointer formation, malformed parse failures must be fail-closed with no partial report, and loader-level mitigation facts must remain covered by the deterministic mitigation oracle. Sprint 8 Patch 030 proves the first reuse of this model for `PT_DYNAMIC`; Patch 031 proves the first evidence-composition step on top of that view; Patch 032 proves the first bounded string-table scan. Later dynamic-symbol, section, relocation, or note tables must follow the same bounded-view pattern.

## Sprint 8 Patch 032 canary indicator seam

Patch 032 extends the bounded dynamic-table evidence path to collect `DT_STRTAB` and `DT_STRSZ`. The resulting dynamic string-table range is translated only through a file-backed `PT_LOAD` range and is capped before scanning. The only implemented canary evidence is an exact null-terminated `__stack_chk_fail` string. The field is reported as `unknown`, `absent`, or `present`; it is an indicator only and never changes executable-region authority.

## Sprint 8 Patch 033 stripped-status update

Patch 033 reports stripped status as an evidence-qualified mitigation metadata field. Text uses `Stripped indicator: unknown`, `stripped`, or `not stripped`; JSON uses `mitigations.stripped` values `unknown`, `stripped`, or `not_stripped`. The section-header scan is bounded and never selects executable regions or candidate scan ranges. Duplicate `DT_STRTAB` and `DT_STRSZ` dynamic entries fail closed as malformed input so canary evidence is not order-dependent.

## Sprint 8 Patch 034 section-label annotation seam

Patch 034 reuses the bounded section-header seam for optional section labels. `src/shdr.asm` validates the section table and section-name string table before annotating executable regions or gadget candidates. The annotation pass runs only after region discovery, candidate scanning, exact pattern matching, semantic classification, and scoring. Missing or unsafe section-name evidence leaves records unlabeled. Malformed section-table structure remains fail-closed.

The section label is therefore an analyst convenience, not a source of truth. `PT_LOAD + PF_X` remains executable-region authority, and the scanner continues to operate over loader-derived executable file ranges. Text labels are rendered with control-byte escaping, while JSON carries the bounded section string as machine-readable data.


## Sprint 8 Patch 035 section-label hardening

Patch 035 keeps the Patch 034 section-label seam but removes hostile-input ambiguity. The label finder now accepts only unique file-backed sections that carry both `SHF_ALLOC` and `SHF_EXECINSTR`. Non-executable overlap is ignored, and multiple executable sections covering the same file offset produce no label. The helper context is stack-local to the annotation pass. Text reports escape unsafe section-name bytes as `\xNN`, preserving one logical line per region or candidate. Patch 036 adds the second half of the label trust rule: a label must contain both the candidate file offset and the candidate virtual address. If file-offset and virtual-address evidence disagree, the record remains unlabeled.

## Sprint 8 Patch 036 historical-findings hardening

Patch 036 does not change scanner authority or semantic scoring. It hardens report and validation seams discovered during historical review:

- JSON string emission is byte-safe for C strings and bounded section names. Unsafe bytes are escaped rather than emitted as raw high-bit output or replaced with lossy placeholders.
- Section-label assignment requires agreement between file-backed section range and section virtual-address range. This keeps labels as analyst annotations and avoids trusting contradictory section-table metadata.
- Benchmark smoke scripts validate run counts, max-depth values, timing fields, and RSS fields before writing normal evidence.
- Benchmark summaries refuse mixed-artifact aggregation by default because unrelated TSV files can have different tool versions, corpora, schemas, or environments.
- Temporary validation outputs use per-run directories to avoid collisions in parallel local or CI runs.

These changes preserve the core module boundaries: file mapping and bounds, ELF and loader facts, raw scanning, exact suffixes, semantic classification, scoring, and report adapters remain separate.


## Comparator layer

Patch 037 adds comparator smoke tooling around the analyzer without changing
runtime module boundaries. `readelf` comparison validates stable ELF/header and
loader-visible facts. Optional `checksec` and `rabin2` output is captured for
review only and never becomes an internal source of analyzer truth.

## Sprint 8 closeout boundary

Sprint 8 closes with a clear separation between analyzer facts and comparison
helpers. `readelf`, `checksec`, and `rabin2` may be used to compare visible
metadata and mitigation indicators, but they do not replace x64lens parser
contracts or become runtime authority. Program headers remain authoritative for
runtime executable mappings; dynamic and section tables remain bounded evidence
sources; optional external tools remain version-specific review aids.

Patch 038 hardens the direct optional comparison helpers so both accepted
argument orders resolve to exactly one analyzer binary and one analyzed target.
The helpers print an identity line before comparison output, which makes review
logs auditable and prevents the wrong file from being compared silently.


## Sprint 9 Patch 040 report-envelope seam

Patch 040 adds `src/analysis_summary.asm` after scanning, exact matching,
classification, scoring, and optional annotation have all succeeded:

```text
scanner
  -> patterns
  -> classifier
  -> scoring
  -> optional section annotations
  -> analysis summary
  -> text or JSON adapter
```

The command orchestrator owns the fixed-size summary because command identity is
not a scanner or reporter decision. The summary records:

```text
report type
command identity
selected maximum depth
candidate capacity and count
candidate truncation
candidate dropped count and known state
regions scanned and total
analysis completion
```

`gadgets` and `analyze` construct the same facts from their shared records and
pass different command IDs. The reporters render the record but do not decide
whether analysis completed.

The summary is created only on the success path. Scanner capacity exhaustion
continues to return `EXIT_UNSUPPORTED` before report emission. This is important:
Patch 040 does not continue scanning after capacity, cannot know a total dropped
count on that path, and therefore does not fabricate an incomplete report.

The new summary is distinct from the planned candidate evidence side-car:

```text
analysis_summary             one command-level completion record
candidate_evidence_record[]  one future provenance record per candidate index
```

This preserves raw-candidate facts, exact-suffix patterns, semantic-exact
classes, scores, and future decoder evidence as separate layers. Program
headers remain executable-region authority; section and dynamic metadata
remain bounded evidence or annotations.


## Sprint 9 Patch 041 candidate evidence side-car

Patch 041 adds a dense fixed-size `candidate_evidence_record[]` without changing
`gadget_record` layout or scanner ownership:

```text
gadget_record[i]
  raw scanner, exact-suffix pattern, semantic-exact, score, and annotation facts

candidate_evidence_record[i]
  raw-candidate/exact-suffix/semantic-exact evidence flags
  semantic evidence source
  validator identity
  matched suffix offset and length
  full-sequence validity state
```

The array index is the key. The record does not duplicate `candidate_index`,
which prevents a redundant index from disagreeing with array position. Both
arrays are allocated from one command-lifetime arena, remain bounded to 4096
entries, and are destroyed through the existing cleanup path.

The implemented orchestration order is:

```text
scanner
  -> exact pattern matcher
  -> conservative classifier
  -> candidate evidence materializer
  -> scoring
  -> optional section annotation
  -> analysis summary
  -> text or JSON adapter
```

`candidate_evidence.asm` records existing facts only. It does not decode a
candidate, change semantic class, assign score, select an executable region, or
format output. Current full-sequence validity is unknown. A future decoder may
add decoder flags or a separate `decode_record[]`, but it must preserve raw and
exact facts.

Patch 041 also corrects System V stack alignment across the identified nested-
call paths. JSON callers pass the analysis summary and evidence array as stack
arguments seven and eight; the reporter loads both and aligns its frame. Numeric
renderers, text-report helpers, arena mapping, and output/error wrappers now
either align before nested calls or use a true tail jump when no return work
remains.


## Sprint 9 Patch 042 external evidence architecture

Patch 042 does not add a runtime module. It adds two development-only adapters
around the stable analyzer boundary:

```text
public ZIP
  -> metadata-only portable bundle policy
  -> pass or fail before distribution

x64lens schema 0.2.0 JSON + target bytes + GNU objdump disassembly
  -> decoder-gap reconciler
  -> ignored comparison artifacts and decision input
```

The bundle checker never extracts members and does not infer policy from one
expected archive prefix. The shell entry point, regression smoke, and actual
artifact check share one Python policy implementation.

The decoder-gap reconciler consumes public outputs and external disassembly. It
may measure raw terminator overlap, canonical-boundary agreement, duplicate and
selection-model differences, unsupported canonical sequences, and validation
cost. It must not:

- select executable regions,
- reinterpret ELF loader authority,
- mutate `gadget_record[]` or `candidate_evidence_record[]`,
- promote semantic classes,
- assign scores,
- emit x64lens runtime reports.

This keeps the future decoder decision outside the current engine until measured
evidence justifies an adapter. Any approved decoder must still enter through
side-car records after raw scanning, not through a scanner rewrite.

## Sprint 9 Patch 043 campaign and decoder boundary

Patch 043 does not alter the analyzer pipeline. It hardens the development-only
comparison path:

```text
mutable source path
  -> verified immutable snapshot
  -> x64lens JSON over snapshot
  -> canonical external disassembly over the same snapshot
  -> categorized reconciliation plus parser diagnostics
  -> complete staging result
  -> signal-safe transactional publication
```

The default analyzer remains decoder-free. A future decoder may attach through a
separate adapter that writes candidate-index side-car facts. It must not own file
mapping, ELF validation, program-header authority, raw enumeration, mitigation
analysis, scoring, or output policy.

## Sprint 9 Patch 044 campaign and bounded acceleration seam

Patch 044 changes no analyzer module. It hardens the development evidence path:

```text
immutable target snapshot
  -> measured x64lens / external comparison child session
  -> normalized external instruction evidence
  -> categorized reconciliation
  -> complete staging tree
  -> signal-safe transactional publication
```

The default runtime remains the existing single-threaded direct-syscall NASM
pipeline. Future decoder facts belong in candidate-index side-cars after the
bounded raw scan. Future parallel work must preserve one deterministic record
order,
one global bounded-capacity result, and no-partial-output failure behavior. It
may not move loader authority, scanning, classification, scoring, or reporting
into external helpers.

## Sprint 9 closeout architecture

Sprint 9 adds two command-owned fact surfaces without changing loader authority:

```text
analysis_summary
  report identity, command identity, bounded completeness, capacity, progress

candidate_evidence_record[]
  index-aligned raw, exact-suffix, semantic-source, validator, validity state
```

The scanner still owns raw terminator-centered windows. Pattern matching owns exact suffix IDs. The classifier owns semantic promotion. Scoring owns relative utility. Reporters render records. External decoder-gap tooling is a development oracle and cannot mutate runtime facts.

The default deployment profile remains static, decoder-free, and single-worker. A future candidate-scoped decoder consumes retained windows and writes additive side-car facts. A future parallel profile must preserve one-worker output order, global capacity semantics, bounded memory, cleanup, and byte-for-byte machine-readable parity.

## Sprint 10 Patch 046 ordered-effect extension

Patch 046 uses the reserved final eight bytes of the existing 112-byte
`gadget_record`:

```text
pattern_register_count   dword
pattern_register_order   dword
```

The packed order uses four-bit canonical register IDs in execution order. This
keeps the record stride, 4,096-candidate capacity, and combined 655,360-byte
analysis arena unchanged.

The first consumer is the exact `pop reg; pop reg; ret` family for two distinct
System V argument registers. Pattern recognition stores exact order;
classification validates it and emits an unordered controlled-register bitmap,
24-byte stack delta, and `stack_read` side effect. Reporters only render those
facts. At the Patch 046 boundary, multi-pop remained unscored; Patch 051 later
calibrates the current score to 95 after architectural-effect validation.

See [ADR 0032](adr/0032-ordered-multi-pop-foundation.md), the
[Primitive Effect Model](design/primitive-effect-model.md), the
[Sprint 10 Plan](sprints/sprint-10-plan.md), the
[Patch 046 Validation Plan](sprints/sprint-10-patch-046-validation.md), and the
[canonical roadmap](roadmap-22-sprints.md).

## Sprint 10 Patch 047 exact register-transfer seam

Patch 047 extends the existing staged path without changing module ownership:

```text
scanner.asm
  -> patterns.asm: exact register-direct move and operand roles
  -> classifier.asm: reg_transfer, destination clobber, stack/effect facts
  -> candidate_evidence.asm: semantic-exact suffix provenance
  -> scoring.asm: no new score rule
  -> report_text.asm / report_json.asm: relation rendering only
```

The matcher accepts only `REX.W` register-direct opcode `89 /r` or `8b /r`
forms followed by `ret`, with distinct non-`rsp` operands. The existing 112-byte
candidate record stores destination then source in its bounded pattern metadata
tail. The candidate arena remains 655,360 bytes with capacity 4,096.

Reporters do not infer operand roles from text or pattern names. They render the
recorded source/destination relation. Full instruction-sequence validity remains
unknown because no decoder is introduced.

See [ADR 0033](adr/0033-exact-register-transfer-effects.md), the
[Primitive Effect Model](design/primitive-effect-model.md), the
[Semantic Taxonomy](semantic-taxonomy.md), the
[JSON Schema Contract](json-schema.md), the
[Sprint 10 Plan](sprints/sprint-10-plan.md), the
[Patch 047 Validation Plan](sprints/sprint-10-patch-047-validation.md), and the
[canonical roadmap](roadmap-22-sprints.md).

## Sprint 10 Patch 048 exact stack-adjust seam

Patch 048 adds one exact matcher/classifier path without changing scanner authority or record allocation:

```text
scanner raw candidate
  -> patterns.asm recognizes 48 83 c4 imm8 c3
  -> classifier.asm validates positive aligned imm8 and records total stack delta
  -> candidate_evidence.asm records five-byte semantic-exact suffix provenance
  -> scoring.asm leaves the family unscored at the Patch 048 boundary
  -> text/JSON reporters render record-backed stack_adjust and flags_write effects
```

Promotion requires a nonzero positive immediate below `0x80` and divisible by eight. Zero, negative, unaligned, wrong-register, and subtraction forms retain the existing bare-return fallback. Arithmetic flag modification is represented as `flags_write`; the current clobber bitmap remains a general-purpose-register fact and does not model condition flags.

Patch 051 later calibrates the current stack-adjust score to 35 after
architectural-effect validation.

The family reuses the existing 112-byte `gadget_record`. Candidate capacity remains 4096 and the combined analysis arena remains 655360 bytes. Full-sequence validity remains unknown because exact suffix evidence is not decoded validity.

Public artifact validation now has two independent layers: metadata-only ZIP safety and bounded textual-content inspection. The latter reads eligible public text members in memory without extracting them. See [ADR 0034](adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md) and the [Patch 048 validation plan](sprints/sprint-10-patch-048-validation.md).

## Sprint 10 Patch 049 bounded memory-effect seam

Patch 049 adds a third dense command-lifetime record array:

```text
gadget_record[4096]              112 bytes each
candidate_evidence_record[4096]   48 bytes each
memory_effect_record[4096]         16 bytes each
```

The combined arena is 720,896 bytes. The fixed increase is 65,536 bytes; candidate capacity remains 4,096. The scanner receives only the raw record array and capacity and remains unaware of the side-cars.

The execution order is:

```text
raw scan
  -> exact patterns and compact operand facts
  -> semantic classification
  -> candidate evidence materialization
  -> memory-effect materialization
  -> scoring
  -> optional annotations
  -> analysis summary
  -> text or JSON reporting
```

`memory_effect.asm` reconciles already-established exact and semantic facts. It cannot scan target bytes, classify a candidate, assign a score, or format output. Reporters receive the memory side-car explicitly.

The first families represent only qword base-plus-zero `mov` loads and stores without SIB, displacement, RIP-relative addressing, or `rsp` participation. This bounded scope establishes the durable operand record before broader memory families.


## Sprint 10 Patch 050 effect-completion boundary

Patch 050 adds no module and no primitive family. It completes facts written by `classifier.asm` for already-supported exact patterns:

```text
all supported return-ending semantics -> stack_read
syscall; ret                         -> rcx/r11 clobbers + register_write
leave; ret                           -> rbp clobber + register_write
```

The classifier remains the only module that assigns these semantic and effect facts. Pattern matching still identifies exact suffixes; reporters still render records without inferring effects. `memory_effect.asm` remains responsible only for structured memory operands after exact matching and classification.

The candidate record remains 112 bytes, the evidence record 48 bytes, the memory-effect record 16 bytes, candidate capacity 4,096, and the command arena 720,896 bytes. Patch 050 therefore changes semantic completeness and test correctness without changing the fixed allocation profile.

Fixture gates are also part of the architecture around the analyzer. Sprint 10 multi-command recipes now execute with fail-fast shell semantics so a failed semantic validator cannot be hidden by a later successful command. The cross-family coverage table is maintained in [`design/sprint10-family-coverage.md`](design/sprint10-family-coverage.md).

## Sprint 10 Patch 051 architectural-effect reconciliation

The governing decision and validation surfaces are
[ADR 0037](adr/0037-architectural-effects-and-contract-reconciliation.md), the
[exact-pattern catalog](design/sprint10-exact-pattern-catalog.md), and the
[Patch 051 validation record](sprints/sprint-10-patch-051-validation.md).

Patch 051 adds a fourth dense candidate-index record family after raw candidates,
provenance, and structured memory effects:

```text
gadget_record[4096]               112 bytes each
candidate_evidence_record[4096]    48 bytes each
memory_effect_record[4096]          16 bytes each
candidate_effect_record[4096]       24 bytes each
combined command arena          819200 bytes
```

`candidate_effect.asm` materializes represented GPR reads/writes, condition-flag
reads/writes, return/syscall control flow, stack source/count/offset facts, and
model-completeness state from already established exact, semantic, and memory
records. It cannot scan bytes, select executable regions, classify candidates,
assign scores, or emit output.

The stage order is:

```text
scanner -> exact matcher -> classifier -> provenance -> memory effects
        -> architectural effects -> scoring -> reporting
```

This order is deliberate: scoring validates and consumes represented effects
rather than becoming a second classifier. The 112-byte scanner record and the
4,096-candidate boundary remain unchanged. The fixed arena grows by 98,304
bytes; this is allocation arithmetic, not measured maximum RSS.


## Sprint 10 Patch 052 corrective architecture

The governing correction and acceptance surfaces are
[ADR 0038](adr/0038-patch051-corrective-effect-and-gate-hardening.md) and the
[Patch 052 validation record](sprints/sprint-10-patch-052-validation.md).

Patch 052 preserves the Patch 051 side-car pipeline and adds no record or arena
growth. The candidate-effect materializer reconstructs the complete current
memory descriptor from exact candidate metadata and requires exact agreement
with the dense memory side-car. This prevents direction conflicts, reserved
bits, displacement drift, and wrong-index records from entering reports or
scores.

Full-width effect descriptors are materialized in registers before qword stores
or comparisons. NASM number-overflow warnings are fatal so an immediate cannot
silently narrow a 64-bit contract. Validation adds a standalone internal
assembly harness; it is linked only for tests and is not part of the runtime
binary.

## Sprint 10 Patch 053 benchmark-informed architecture

Patch 053 changes no analyzer module, record layout, report field, score,
capacity, decoder policy, or worker policy. It corrects the Patch 052 internal
harness symbol and records the evidence sequence that governs the next research
tranche.

The project now separates measurement into two phases:

```text
Sprint 11 diagnostic measurement
  provisional corpus and mutable method
  measures timer floor, task scope, runtime/RSS, output cost, and coverage gaps
  may redirect loader, mitigation, semantic, decoder, or concurrency work

Sprints 12-14 capability hardening
  resolves release-facing ambiguities under new diagnostic campaign IDs

Sprint 15 campaign freeze
  freezes corpus, schema/extractor, runner, baselines, commands, task definitions,
  cache policy, and environment strata

Sprints 16-17 confirmatory measurement
  preview pilot followed by publication-grade repeated trials
```

Diagnostic evidence is deliberately excluded from the frozen preview and
publication datasets after a capability, schema, task, corpus, or method change.
This allows benchmarking to falsify weak design assumptions early without
turning mutable development rows into final claims.

The dependency-free, decoder-free, one-worker analyzer remains the reference
profile. Candidate-scoped decoding, deterministic concurrency, and any broader
ROP family are separate conditional profiles. They are admitted only when a
measured task gap justifies their binary-size, dependency, latency, CPU, RSS,
cleanup, and output-definition costs.

The governing records are [ADR 0039](adr/0039-benchmark-informed-capability-roadmap.md),
[benchmark and capability stage gates](design/benchmark-and-capability-stage-gates.md),
and the [twenty-two-sprint roadmap](roadmap-22-sprints.md).

## Sprint 10 closeout architecture state

Patch 054 closes Sprint 10 without changing analyzer code or record layouts. The current command-lifetime arena contains dense candidate, provenance, memory-effect, and architectural-effect slices while preserving the 4096-candidate fail-closed limit. Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable authority. Exact patterns, semantic roles, side-car effects, scores, and reporters remain separate responsibilities.

Sprint 11 measures this reference profile diagnostically. Candidate-scoped decoder and concurrency profiles remain optional, separately identified experiments and cannot replace the dependency-free one-worker reference without evidence and an explicit architecture decision.
