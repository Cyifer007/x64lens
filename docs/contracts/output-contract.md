# Output Contract

## Text output

Text output is optimized for human readability. It may change before `1.0.0`, but major changes should be documented.

## JSON output

JSON output is optimized for tools and automation. It must be schema-versioned.

## Required JSON fields

Every current schema `0.2.0` JSON report must include:

- `schema_version`,
- `tool`,
- `tool_version`,
- `report_type`,
- `command`,
- `analysis`,
- `target`,
- `limitations`.

Historical schema `0.1.0` reports predate report identity and analysis
completeness. The retained representative final-shape snapshot remains
consumable through the versioned compatibility path; compatibility is not
claimed for every intermediate pre-release emission.

## Address formatting

Virtual addresses and file offsets are hex strings.

Example:

```json
"va": "0x000000000040118a"
```

## Count separation in output

Reports should separate:

- raw candidate count,
- exact pattern count,
- semantic primitive count,
- unknown candidate count,
- scored candidate count.

Do not infer semantic value from raw scanner output alone.

## Unknown values

Unknown machine-readable values should be represented explicitly:

- JSON unknown numeric values should use `null`, not `0`, when `0` would be ambiguous.
- JSON should pair ambiguous fields with explicit indicators when useful, such as `stack_delta_known`.
- Text output may keep stable legacy representations during early development, but JSON should prefer explicit machine-readable meaning.

## Limitations

Every JSON report should include limitations when the analysis is incomplete or heuristic.

## Exploitability wording

The tool may report primitive availability and plausible exploit strategy constraints. It must not state that a binary is exploitable without an independent vulnerability and runtime context.

## Public repository voice

Public output, documentation, comments, tests, and examples must be written as repository-facing project material. They must not reference private coordination context, attachment history, or tool-assisted workflow details. Public wording should describe repository facts, implementation decisions, validation evidence, and reproducible commands from the project perspective.


## Public validation transcript rule

Public validation snippets should use generic prompts and repository-relative paths where possible. Avoid committing personal hostnames, local usernames, local home-directory paths, private attachment names, or dialogue-style context. Prefer examples such as:

```text
$ make test
tests: ok
```

Use repository facts, reproducible commands, and observed technical outcomes instead of private workflow narration.

## Complete-report failure rule

When bounded storage or a parser precondition prevents a complete report, the command must fail before emitting text or JSON stdout. Silent truncation and syntactically incomplete JSON are prohibited. Candidate-arena exhaustion currently uses exit code `6` and the stable unsupported-feature diagnostic.

Schema `0.2.0` exposes machine-readable completeness and truncation state for successful reports. This does not enable partial output. A future intentional partial-report mode must additionally implement truthful scanner progress and dropped-count semantics, update validators, and preserve complete JSON syntax before release.

## Mitigation consistency rule

The same valid ELF64 program-header evidence must produce compatible mitigation facts in focused text output and integrated JSON. Patch 030 extends this rule to bounded `PT_DYNAMIC` facts: bind-now, dynamic-entry count, and dynamic terminator state must agree between focused mitigation text and integrated JSON. Patch 031 refines RELRO to no, partial, and full states: full RELRO requires `PT_GNU_RELRO` plus bounded bind-now evidence, partial RELRO requires `PT_GNU_RELRO` without bind-now evidence, and no RELRO requires no `PT_GNU_RELRO`. Malformed file-backed `PT_LOAD` and `PT_DYNAMIC` ranges, plus duplicate `PT_DYNAMIC` headers, must fail before any partial stdout is emitted. `info`, `mitigations`, `gadgets`, and `analyze` must return the stable malformed-ELF status and diagnostic for controlled matrix defects when the command path parses the relevant table.

## Canary indicator wording

Text output must use `Canary indicator:` rather than wording that implies complete stack protection. JSON `mitigations.canary` may be `unknown`, `absent`, or `present`. `unknown` is required when bounded metadata is unavailable. `present` means exact `__stack_chk_fail` evidence was found in a validated dynamic string table; it does not prove every function is protected.

## Sprint 8 Patch 033 stripped-status update

Patch 033 reports stripped status as an evidence-qualified mitigation metadata field. Text uses `Stripped indicator: unknown`, `stripped`, or `not stripped`; JSON uses `mitigations.stripped` values `unknown`, `stripped`, or `not_stripped`. The section-header scan is bounded and never selects executable regions or candidate scan ranges. Duplicate `DT_STRTAB` and `DT_STRSZ` dynamic entries fail closed as malformed input so canary evidence is not order-dependent.

## Sprint 8 Patch 034 section-label update

Patch 034 may emit section labels for executable regions and gadget candidates when a bounded section-name table is available. Text output uses `section: <name>` annotations. JSON gadget records may include `section` as a string or `null`. These labels are optional metadata and must not be interpreted as runtime mapping authority.


## Sprint 8 Patch 035 section-label rendering update

Text section labels are single-line-safe. Printable ASCII bytes are emitted directly except backslash; backslash is escaped as `\\`, and control bytes, DEL, and high-bit bytes are escaped as `\xNN`. JSON section fields remain strings or `null` and use byte-safe JSON escaping. Ambiguous overlapping executable section metadata must not force a label.

## Sprint 8 Patch 036 byte-safe JSON and label-agreement update

Patch 036 requires JSON report strings emitted by the NASM adapters to remain valid JSON for control bytes and high-bit bytes. Bounded section labels are emitted through byte-safe JSON escaping instead of raw byte emission. Section labels are omitted unless the section contains both the record file offset and the record virtual address. This preserves labels as optional metadata and keeps program headers as runtime mapping authority.

Benchmark smoke summaries are evidence artifacts, not report-schema artifacts. They must reject nonnumeric or negative metric fields before normal summarization, and mixed-artifact aggregation requires explicit opt-in.


## Comparator output boundary

`readelf`, `checksec`, and `rabin2` outputs are validation and review artifacts.
They do not change the x64lens JSON schema or text output contract. x64lens
continues to distinguish loader facts, section-derived annotations, raw
candidates, exact suffixes, semantic classes, unknowns, and scored facts.


## Sprint 9 Patch 040 identity and completeness rule

Current JSON reports use `report_type: "analysis"` and identify the producing
command as `gadgets` or `analyze`. The command identity does not create separate
analysis implementations.

The `analysis` object must satisfy:

```text
candidate_count <= candidate_capacity
candidate_count == counts.raw_candidate_count
regions_scanned <= regions_total
complete => !candidate_truncated
complete => candidate_dropped_count_known
complete => candidate_dropped_count == 0
complete => regions_scanned == regions_total
candidate_truncated => !complete
!candidate_dropped_count_known => candidate_dropped_count == null
```

Current producers emit only complete successful reports. The 4097-candidate
capacity failure still returns exit code `6` before stdout, so the tool does not
invent a partial report or a dropped count it did not measure.

Completeness applies to bounded candidate enumeration over program-header-
derived executable regions. It does not mean decoder-valid sequence coverage,
semantic completeness, exploitability, or complete mitigation knowledge.


## Candidate provenance rule

Current schema `0.2.0` producers emit candidate evidence from a side-car keyed
by gadget-array index. Evidence must preserve raw observations when stronger
exact or semantic facts exist. Exact-suffix or semantic-exact evidence must not
be rendered as full decoded validity; current `full_sequence_valid` is `null`.

The formal schema keeps candidate evidence optional for Patch 040 compatibility.
Current-producer validation requires all candidate evidence with
`--require-provenance`. Partial evidence arrays are invalid.

## Sprint 9 closeout output rule

Schema `0.2.0` remains the current output contract. Patch 045 adds no output field. Future decoder and parallel profiles must preserve command identity, completeness, provenance, count meaning, no-partial-output behavior, and deterministic ordering. Profile identity must be represented in release and benchmark provenance before different profiles are compared or aggregated.

## Sprint 10 candidate-effect rule

Current schema `0.2.0` producers emit `stack_pop_order`, `clobbers`, and
`side_effects` for every candidate. Earlier compatible `0.2.0` reports may omit
these additive fields.

- Ordered pop facts come from exact pattern metadata.
- Controlled and clobbered registers come from semantic classification.
- Side effects come from classifier facts, not reporter inference.
- `controls` ordering is canonical bitmap order and must not be interpreted as
  instruction order.
- A semantic candidate may remain unscored when the scoring model has no
  reviewed entry.

The generic Patch 046 multi-pop family must report two ordered distinct argument
registers, a matching controlled-register set, stack delta 24, `stack_read`, an
empty clobber set, and `score: null`.

## Sprint 10 register-transfer output

Patch 047 adds a compatible per-candidate `register_transfer` relation and
`primitive_coverage.reg_transfer`. Source and destination are record-backed
facts. A transfer does not populate `controls` unless a separate semantic rule
justifies control; the exact family currently records the destination in
`clobbers` and emits `register_write`.

Earlier schema `0.2.0` reports without the optional relation remain consumable.
Current producer validation requires the relation field and rejects
source/destination, control, clobber, stack, or side-effect contradictions.

## Sprint 10 stack-adjust output

Patch 048 adds exact pattern `add rsp, imm8; ret` for positive nonzero eight-byte-aligned immediates. A promoted candidate reports semantic class `alignment`, empty controls/order/clobbers, total known stack delta `imm8 + 8`, side effects `stack_adjust` and `flags_write`, and `score:null`.

`flags_write` is an explicit condition-code effect; condition flags are not part of the general-purpose-register clobber bitmap. Unsupported forms remain the existing bare-return fallback. Full-sequence validity remains unknown under semantic-exact evidence.

## Public artifact content rule

Public ZIP acceptance requires both metadata safety and bounded textual-content review. The content gate scans eligible source, documentation, configuration, patch, and diff members in memory without extracting them. A final source tree that is clean does not make a unified diff safe when deleted or added lines preserve prohibited private workflow or host-specific material.
