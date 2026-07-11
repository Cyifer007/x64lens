# ADR 0028: Portable Bundle Policy and External Decoder-Gap Evidence

## Status

Accepted for Sprint 09 Patch 042.

## Context

Patch 041 established candidate-index provenance and passed native, Docker,
capacity, schema, command-parity, and ABI validation. Its follow-up review found
one release-validation defect: public ZIP hygiene depended on incomplete path
patterns and accepted private material under several root layouts. The same
review confirmed that the next product-research risk is decoder disagreement,
not another primitive-family expansion.

Two boundaries therefore need to advance together:

1. public source artifacts must fail closed for unsafe, private, and generated
   members regardless of archive root or host filesystem behavior;
2. decoder-gap evidence must be measured externally before any runtime decoder
   dependency is selected.

## Decision

### Portable bundle policy

The public entry point remains:

```bash
BUNDLE=/path/to/archive.zip make patch-bundle-hygiene
```

The shell helper delegates to a Python policy implementation that inspects ZIP
metadata without extraction. The policy:

- normalizes and case-folds member paths for comparison;
- rejects absolute, drive-qualified, traversing, backslash, control-character,
  and Windows-ambiguous paths;
- rejects duplicate or case-colliding members;
- rejects symbolic links and encrypted members;
- rejects special-file members, per-member comments, and arbitrary archive
  comments while allowing a source-identity hash comment;
- rejects Git, local context, agent state, environment files, private/course
  material, secrets, generated outputs, and nested archives under any root;
- preserves explicit allowlists such as `.env.example` and
  `benchmarks/results/.gitkeep`.

The regression smoke calls the same policy implementation directly and also
exercises the public shell wrapper. This avoids a second pattern implementation
inside the test.

### External decoder-gap campaign

Patch 042 adds a development-only GNU `objdump` reconciliation tool. It records:

- target, analyzer, and external-tool identity;
- analyzer, campaign implementation, controlled expectation, validator,
  Python, GNU time, external-tool, and target SHA-256 hashes plus exact
  commands;
- x64lens schema `0.2.0` reports with candidate provenance;
- raw objdump disassembly;
- smoke-level wall time and maximum RSS;
- raw terminator agreement and disagreement;
- exact-suffix canonical-boundary agreement;
- supported canonical suffixes not selected by the one-record-per-terminator
  model;
- duplicate terminator and canonical-sequence facts;
- canonical return-ending sequences outside the current exact-pattern catalog.

`objdump` is comparison evidence only. It does not become ELF mapping authority,
runtime classification logic, score policy, or a new report producer.

Two Make targets separate stable regression from host-dependent research:

```bash
make decoder-gap-smoke
make decoder-gap-campaign
```

The controlled smoke is part of native and Docker aggregate validation. The
selected-system campaign preserves generated artifacts under the ignored
`tests/results/decoder-gap/` directory and does not assert distro-specific
counts.

### Decision authority

The campaign produces facts, not an automatic architecture verdict. The
embedded-decoder decision must apply the criteria in
`docs/design/decoder-gap-decision-gate.md`, including correctness impact,
coverage impact, dependency/license cost, runtime/RSS cost, and preservation of
the raw scanner.

## Consequences

- Release validation becomes portable across zero-root, one-root, and arbitrary
  archive layouts.
- Private state cannot bypass the checker through case variation, Windows path
  semantics, symlinks, or nested archives.
- Decoder disagreement is measurable without changing x64lens runtime output.
- Raw, exact, semantic-exact, unknown, and scored metrics remain unchanged.
- The controlled campaign can block regressions, while system-binary gaps remain
  research observations until interpreted.
- An embedded decoder remains deferred until measured evidence satisfies the
  decision gate.
- Decoder-gap regeneration refuses to replace an unrelated existing directory;
  only a directory carrying the campaign's own manifest is replaceable.
