# Sprint 10 Patch 048 Validation

## Status

Current implementation candidate; authoritative native and Docker validation
required.

## Scope

Patch 048 carries the exact register-transfer foundation forward after correcting
its JSON reporter and validation defects. It adds one bounded exact family:

```text
add rsp, positive-aligned-imm8; ret
```

It also adds a public textual-artifact gate so a distributed patch or diff cannot
reintroduce private process narration that is absent from the final source tree.

## Source and compatibility requirements

- Apply to committed Patch 047 source
  `d4aa9dd8981ec50d41b74090b062327688ab7f02`.
- Preserve tool version `0.1.0-dev` and schema `0.2.0`.
- Preserve the `v0.1.0-dev` checkpoint target.
- Preserve `gadget_record=112`, `candidate_evidence_record=48`,
  `gadget_summary=128`, `analysis_summary=88`, candidate capacity 4096, and
  analysis arena 655360 bytes.
- Introduce no mandatory decoder, thread runtime, interpreter, helper process,
  or shared-library dependency.

## Required focused results

### Patch 047 correction

A clean build must resolve the compact JSON object delimiters. The transfer
fixture remains:

```text
candidates=10 transfers=4 fallback=6 scored=6
```

### Stack-adjust fixture

`make sprint10-stack-adjust-smoke` must report:

```text
sprint10-stack-adjust-smoke: ok candidates=7 stack_adjust=2 fallback=5 scored=5
```

The two promoted records are:

| Exact suffix | Total known stack delta | Side effect | Score |
|---|---:|---|---|
| `48 83 c4 08 c3` | 16 | `stack_adjust`, `flags_write` | null |
| `48 83 c4 20 c3` | 40 | `stack_adjust`, `flags_write` | null |

The following remain bare-return fallbacks:

- `add rsp, 0; ret`;
- `add rsp, -8; ret`;
- `add rsp, 7; ret`;
- `add rax, 8; ret`;
- `sub rsp, 8; ret`.

Matching bytes in the fixture's non-executable data segment must not become
candidates.

### Candidate relationship validation

`make json-effect-consistency-smoke` must reject:

- exact patterns with contradictory terminator labels;
- bare `ret` with nonempty controls;
- bare `ret` with arbitrary stack delta;
- stack-adjust bytes with an unsupported immediate;
- stack-adjust records with a wrong delta or missing effect.

### Public artifact content

`make public-artifact-content-smoke` must accept one clean ZIP and reject both
patch/diff fixtures that preserve prohibited deleted or added text.

The final public overlay must pass both:

```bash
BUNDLE=/path/to/public-overlay.zip make patch-bundle-hygiene
PUBLIC_BUNDLE=/path/to/public-overlay.zip make public-bundle-content-check
```

The first command is metadata-only. The second reads bounded textual payloads
without extracting members.

## Complete native matrix

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make public-artifact-content-smoke
make planning-docs-check
make full-tools-check
make doctor

make clean
make
make samples
make test
make validate-gadget-fixture
make scanner-smoke
make arena-smoke
make pattern-smoke
make semantic-smoke
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make benchmark-integrity-smoke
make patch-bundle-hygiene-smoke
make decoder-gap-hardening-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Docker matrix

Run the default path first. When the only failure is a read-only Buildx metadata
location, retain that evidence and rerun with a writable isolated Buildx
configuration. The qualified path must pass build, core tests, context hygiene,
and the complete validation aggregate.

## Failure contracts

- Candidate 4096 produces a complete report.
- Candidate 4097 exits 6 before stdout.
- Malformed input emits no partial stdout.
- `gadgets` and `analyze` reports differ only by command identity for the same
  target and options.
- Stack-adjust exact evidence does not imply decoded full-sequence validity.

## Acceptance

Patch 048 is accepted only when native and qualified Docker aggregates pass,
the authenticated public overlay passes its file-manifest check and both public
gates, and the tracked worktree remains clean after validation.

## Patch 049 handoff

Patch 049 consumes the accepted Patch 048 runtime foundation, removes generated fixture executables from tracked source, closes the public-content checker self-exclusion, authenticates final-file public overlays, and adds the first fixed memory-effect side-car and bounded qword base-plus-zero memory family.
