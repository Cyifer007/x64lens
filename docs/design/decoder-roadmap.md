# Decoder Roadmap

## Purpose

Sprint 3 introduced a byte-oriented raw scanner and exact suffix pattern matcher. This is useful, but it is not a full instruction decoder. This document defines the future decoder seam so the repository can grow without rewriting the scanner.

## Current implemented layers

```text
executable regions -> raw candidate scanner -> exact suffix pattern matcher -> text report
```

The current scanner finds return-terminated byte windows inside executable `PT_LOAD + PF_X` regions. The exact matcher assigns small `PATTERN_*` IDs to suffix byte templates such as `pop rdi; ret`, `leave; ret`, `syscall; ret`, `ret`, and `ret imm16`.

## Important limitation

A Sprint 3 pattern label describes a recognized suffix ending at the terminator. It does not prove that the entire printed byte window is a single intended instruction sequence.

Example:

```text
bytes: 5f c3 5e c3
pattern: pop rsi; ret
```

The label means the suffix `5e c3` matches `pop rsi; ret`. Earlier bytes remain part of the raw candidate window.

## Why this is acceptable now

The current design deliberately separates four concepts:

1. raw byte candidate discovery,
2. exact suffix pattern recognition,
3. semantic primitive classification,
4. future full instruction decoding.

This staged model lets the tool become useful before it becomes a full disassembler.

## Future decoder seam

A future decoder should be added as an optional side-car path, not by replacing raw candidate records.

Recommended model:

```text
gadget_record[]
semantic_record[] keyed by candidate index
decode_record[] keyed by candidate index, optional future work
```

The scanner remains responsible for finding candidate windows. The decoder should explain whether a window corresponds to a valid instruction sequence from a selected start offset.

## External decoder strategy

Before adding a runtime decoder dependency, use external tools as validators and baselines:

- `objdump -d -Mintel` for fixture review,
- ROPgadget for common gadget comparison,
- Ropper for common gadget comparison,
- ropr where available,
- radare2/rabin2 where useful for metadata comparison.

This preserves the dependency-light research claim while still providing evidence against established tools.

## Full decoder decision gate

Do not add an embedded decoder until the project can answer these questions:

- Which correctness gap requires decoding?
- Which baseline shows that exact patterns undercount or overcount in a way that affects research claims?
- Can the decoder be optional?
- Will decoder-backed output be represented as side-car records rather than replacing raw scanner output?
- How will runtime and memory impact be measured separately from raw scanning?

## Near-term sprint impact

Sprint 4 should not implement a full decoder. It should conservatively classify only exact pattern IDs and leave ambiguous candidates as `unknown_candidate`.

Sprint 8 or later can expand patterns. Sprint 10 can quantify gaps against baseline tools. A full decoder belongs after those measurements unless a critical correctness issue appears earlier.
