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
| `bounds.asm` | Offset, size, and overflow checks | Print user reports |
| `elf64.asm` | ELF64 header validation and metadata | Scan gadgets |
| `phdr.asm` | Program header parsing | Section label formatting |
| `shdr.asm` | Section header parsing and labels | Runtime mapping authority |
| `regions.asm` | Executable region model | Decode instructions |
| `mitigations.asm` | NX, PIE, RELRO, canary indicators, RWX | Claim exploitability alone |
| `scanner.asm` | Candidate byte window discovery | Semantic scoring |
| `patterns.asm` | Opcode template matching | File parsing |
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

Fixed buffers are acceptable during Sprint 1 and Sprint 2. By Sprint 3, gadget records should be stored through a simple arena allocator backed by `mmap`.

## Design decision 7: benchmark-first research design

Benchmarking is a first-class feature, not an afterthought. Every analysis change should preserve the ability to measure:

- runtime,
- max RSS,
- throughput,
- gadget count,
- semantic primitive count,
- output size,
- error count.

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
