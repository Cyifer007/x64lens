# Sprint 09 Patch 042 Validation

## Scope

Patch 042 corrects the Patch 041 public-bundle boundary defect, resolves adjacent
documentation drift, and introduces the first external decoder-gap measurement
surface. It does not alter ELF parsing, executable-region authority, candidate
scanning, exact matching, semantic classification, scoring, schema output, or
capacity behavior.

Patch-generation base:

```text
commit: 1c79197ff8fa748d96a61356829c1b1d053fa027
repository tree: exact Patch 041 commit contents
```

## Corrective findings

Patch 042 must reject, under any archive root:

- version-control metadata and other local-only non-source workspace state;
- `AGENTS.override.md`, `.env` other than `.env.example`, project context files,
  private notes, secrets, proprietary/malware/course material;
- generated build, test, benchmark, and toy-binary outputs;
- unsafe, non-portable, duplicate/case-colliding, symlink, encrypted, and nested
  archive members.

It also aligns Ubuntu setup commands with the required `python3-jsonschema`
dependency and narrows historical schema wording to retained representative
final-shape `0.1.0` fixtures.

## Required native checks

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make dev-tools-check
make clean
make
make samples
make patch-bundle-hygiene-smoke
make decoder-gap-smoke
make schema-compat-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

Expected focused outputs:

```text
patch-bundle-hygiene-smoke: ok cases=38 accepted=5 rejected=33
decoder-gap-smoke: ok targets=1 exact_boundary_disagreements=0 canonical_only_terminators=0 ...
schema-compat-smoke: ok legacy=0.1.0 patch040=0.2.0 current=0.2.0 formal_rejections=13 semantic_rejections=7
validation-smoke: ok
shellcheck-smoke: ok
```

## Selected-system campaign

```bash
make decoder-gap-campaign
```

The target succeeds when each available target is analyzed, the current JSON
report validates, objdump completes, target bytes reconcile with candidate
bytes, and result artifacts are written. System-binary counts are observations,
not fixed regression expectations.

Expected layout:

```text
tests/results/decoder-gap/
  manifest.json
  decoder-gap-summary.json
  decoder-gap-summary.tsv
  <target-id>/
    x64lens.json
    x64lens.stderr
    x64lens.json.time
    objdump.txt
    objdump.stderr
    objdump.txt.time
    comparison.json
```

## Docker checks

```bash
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A Buildx metadata failure outside the repository is an environment defect only
when the same product path passes with writable Buildx metadata.

## Acceptance criteria

- all 38 bundle-policy regression cases behave as specified;
- `.env.example` and `benchmarks/results/.gitkeep` remain allowed;
- the controlled decoder-gap fixture matches all expected counts;
- controlled duplicate terminator, duplicate exact-evidence, and duplicate
  canonical-sequence counts are zero;
- selected-system artifacts contain hashes for the campaign implementation,
  controlled expectation, analyzer, validator, Python, GNU time, objdump, and
  targets plus versions, commands, raw reports, raw disassembly, timings, RSS,
  and categorized differences;
- objdump remains external evidence and does not feed runtime facts;
- no runtime, schema, metric, capacity, malformed-input, or command-parity
  regression occurs;
- public docs contain no private coordination details;
- the `v0.1.0-dev` tag remains unchanged.

The campaign must refuse to replace an existing directory unless that directory
contains a recognized `x64lens-decoder-gap-manifest-v1` manifest. This prevents
an output-path mistake from recursively deleting unrelated evidence or source
data.

## Deferred decision

Patch 042 establishes the evidence generator and explicit decision gate. The
embedded-decoder verdict is made only after authoritative WSL2 campaign evidence
is reviewed. Broad primitive expansion remains deferred to Sprint 10.
