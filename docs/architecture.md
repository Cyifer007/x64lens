# Architecture

## High-level design

x64lens uses a hybrid architecture:

1. **Path 1, engine:** fast assembly-first ELF64 parsing and gadget candidate scanning.
2. **Path 2, value layer:** semantic primitive classification, mitigation-aware analysis, scoring, and reporting.

```text
x64lens CLI
  -> command orchestrator
  -> file mapper
  -> ELF64 parser
  -> executable region mapper
  -> fast gadget candidate scanner
  -> pattern matcher
  -> semantic primitive classifier
  -> scoring engine
  -> mitigation-aware interpretation
  -> text and JSON reporters
```

## Module boundary contract

| Module | Responsibility | Must not do |
| ------ | -------------- | ----------- |
| `main.asm` | Entrypoint, dispatch, high-level flow | Deep parsing or scanning |
| `cli.asm` | Argument parsing, command routing helpers | ELF parsing |
| `info.asm` | Coordinate `info` command mapping, validation, reporting, and cleanup | Own ELF parsing or formatting internals |
| `syscalls.asm` | Linux syscall wrappers | Business logic |
| `filemap.asm` | Open, stat, mmap, munmap, close | Interpret binary format |
| `arena.asm` | Command-lifetime mmap-backed allocation for analysis records | Interpret binary format or emit reports |
| `bounds.asm` | Offset, size, and overflow checks | Print user reports |
| `elf64.asm` | ELF64 header validation and metadata | Scan gadgets |
| `phdr.asm` | Program header parsing | Section label formatting |
| `shdr.asm` | Section header parsing and labels | Runtime mapping authority |
| `regions.asm` | Executable region model | Decode instructions |
| `mitigations.asm` | NX, PIE, RELRO, canary indicators, RWX | Claim exploitability alone |
| `scanner.asm` | Candidate byte window discovery | Semantic scoring |
| `patterns.asm` | Exact opcode-template matching and pattern IDs | File parsing, semantic scoring, or exploitability interpretation |
| `classifier.asm` | Semantic primitive classification | Raw file I/O |
| `scoring.asm` | Gadget and primitive usefulness scoring | CLI handling |
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

Section headers are still valuable for human readability and will be used later to label regions such as `.text`, `.plt`, `.init`, and `.fini`.

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

Sprint 1 through Sprint 6 will not implement a full x86_64 instruction decoder. The first scanner will:

1. find terminator bytes,
2. walk backward up to `--max-depth`,
3. match known opcode templates,
4. classify exact or near-exact gadget forms.

This keeps the semester deliverable achievable while preserving future decoder integration.

## Future decoder integration contract

The scanner must be written so that a future decoder can replace or augment pattern matching without replacing the full tool.

The future interface should look conceptually like:

```text
scan_region(region) -> candidate_windows
candidate_window -> decoder_or_pattern_matcher -> instruction_sequence
instruction_sequence -> classifier -> semantic_record
```

The classifier should accept abstract instruction facts where possible, not raw byte-only assumptions.

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
- Score fields remain unset until Sprint 5.


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
- `scoring.asm` remains the future usefulness layer.
- `report_text.asm` renders facts but does not decide facts.

This means Sprint 5 can add scoring and JSON without rewriting the scanner, pattern matcher, or classifier.

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
4. Add section labels as optional annotations, not as runtime mapping authority.
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

It intentionally does not implement scoring or exploitability interpretation. Those remain Sprint 5 and later work.

## Reviewer-readiness architecture seams

Patch 14 records several future-facing seams that should prevent large refactors later.

### NASM engine boundary

The NASM implementation is the first engine, not a claim that every future layer must be pure assembly. The engine should remain small, measurable, and explicit. Higher-level value comes from semantic classification, mitigation-aware interpretation, JSON contracts, and reproducible benchmarks.

### Raw, exact, semantic, and decoded records

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

Raw candidate count, exact pattern count, semantic primitive count, and scored gadget count must remain distinct in internal records, benchmark TSVs, JSON reports, and paper tables.


## Sprint 4 closeout architecture note

Patch 015 validation confirms that semantic classification landed without collapsing module boundaries. The classifier consumes exact pattern IDs from internal records, writes semantic facts back into `gadget_record` and `gadget_summary`, and leaves scoring and JSON generation for later modules.

Two future seams should be preserved:

1. a decode side-car record for future instruction-boundary validation,
2. an explicit stack-delta-known or stack-delta-kind field for JSON and possible text output improvements.
