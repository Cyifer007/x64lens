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



## Sprint 3 implemented flow: `gadgets <file>`

Patch 008 began the Sprint 3 raw scanner path. Patch 010 kept the same scanner/reporting contract while moving candidate storage into an arena. Patch 011 tags raw candidates with exact byte-template pattern IDs:

```text
main.asm
  -> x64lens_command_gadgets(path, max_depth) in gadgets.asm
     -> x64lens_file_map(path, record) in filemap.asm
     -> x64lens_elf64_validate(base, size) in elf64.asm
     -> x64lens_phdr_analyze(base, size, summary, regions, max_regions) in phdr.asm
     -> x64lens_arena_init / x64lens_arena_alloc in arena.asm
     -> x64lens_scanner_find_ret_candidates(base, size, phdr_summary, regions, gadget_summary, gadget_records) in scanner.asm
     -> x64lens_patterns_match_exact(mapped_base, gadget_summary, gadget_records) in patterns.asm
     -> x64lens_report_text_gadgets(path, gadget_summary, gadget_records, mapped_base) in report_text.asm
     -> x64lens_file_unmap(record) in filemap.asm
```

The Sprint 3 scanner operates only over executable regions produced from `PT_LOAD + PF_X`. It stores raw facts in bounded `gadget_record` entries before output. After Patch 010, the candidate buffer is arena-backed, but the scanner remains storage-agnostic and receives only a pointer plus capacity metadata. After Patch 011, pattern matching remains separate from semantic classification: `patterns.asm` assigns `PATTERN_*` IDs, while `classifier.asm` will later translate those IDs into semantic classes, register bitmaps, stack deltas, and side-effect facts.

Current raw candidate semantics:

- `GADGET_FILE_OFFSET` is the terminator byte file offset.
- `GADGET_VIRTUAL_ADDRESS` is the terminator virtual address.
- `GADGET_BYTE_START` is the beginning of the bounded backward byte window.
- `GADGET_BYTE_LEN` is the full raw byte-window length including the terminator.
- `GADGET_TERMINATOR_TYPE` is `ret` or `ret imm16`.
- Semantic, register, stack, side-effect, and score fields are initialized but left unset for Sprint 4 and later.

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

Important limitation: this is a byte-pattern scanner, not a full instruction decoder. It may report unaligned raw candidates when a byte such as `0xc2` appears inside another instruction encoding. That is acceptable in Sprint 3 because the scanner's role is to discover candidate byte windows. Later `patterns.asm`, `classifier.asm`, and eventually a decoder integration layer will distinguish semantically meaningful gadgets from raw byte candidates.

The current `--max-depth` means the maximum number of bytes considered before the terminator. Total printed window length can therefore be `max-depth + terminator_length`, where `ret` has length 1 and `ret imm16` has length 3.


## Sprint 3 exact pattern matching behavior

Patch 011 introduces the first exact byte-template matcher. It recognizes suffix patterns around already-discovered raw return terminators. The implemented Sprint 3 patterns are:

- `ret`,
- `ret imm16`,
- `pop rax; ret`, `pop rcx; ret`, `pop rdx; ret`, `pop rbx; ret`, `pop rsp; ret`, `pop rbp; ret`, `pop rsi; ret`, `pop rdi; ret`,
- `pop r8; ret` through `pop r15; ret`,
- `leave; ret`,
- `syscall; ret`.

This remains byte-template matching, not full decoding. On real binaries, especially for raw `ret imm16` candidates, some pattern labels can still correspond to unaligned byte sequences. Sprint 4 semantic classification and future decoder integration must preserve this limitation.

## Sprint 3 closeout architecture checkpoint

Sprint 3 completes the first full engine-side candidate path:

```text
filemap.asm
  -> elf64.asm
  -> phdr.asm
  -> regions.asm
  -> scanner.asm
  -> arena.asm
  -> patterns.asm
  -> report_text.asm
```

The implemented layering is intentionally conservative:

- `scanner.asm` discovers raw terminator-centered candidate windows.
- `arena.asm` provides command-lifetime storage for candidate records.
- `patterns.asm` tags exact suffix byte templates.
- `classifier.asm` remains the future semantic layer.
- `scoring.asm` remains the future usefulness layer.
- `report_text.asm` renders facts but does not decide facts.

This means Sprint 4 can add semantic classification without rewriting the scanner.

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

## Sprint 4 insertion point

Sprint 4 should add:

```text
patterns.asm -> classifier.asm -> report_text.asm
```

The first classifier should populate:

- semantic class,
- controlled-register bitmap,
- stack delta,
- side-effect flags where safe,
- primitive coverage summary.

It should not implement scoring or exploitability interpretation until those semantic facts are stable.
