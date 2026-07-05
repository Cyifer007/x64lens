# ADR 0022: Historical findings hardening and byte-safe report evidence

## Status

Accepted for Sprint 8 Patch 036.

## Context

The historical patch review and follow-up validation passes identified several current hardening gaps that were not new feature goals, but did affect report fidelity, private-file boundaries, and validation evidence quality:

- JSON report strings could preserve JSON syntax while losing byte fidelity for target paths, and section-label JSON could emit invalid UTF-8 for high-bit section-name bytes.
- Section labels were file-offset based, but hostile section tables can advertise a section virtual address that does not cover the candidate virtual address.
- The Docker build context excluded private local workspaces but did not explicitly exclude `.env` and `.env.*` files.
- Benchmark smoke scripts accepted invalid run counts or impossible metric domains and could summarize unrelated artifacts as one aggregate.
- Some validation helpers used fixed temporary file names, and one development-tool diagnostic relied on `cat` even when `PATH` was damaged.

These gaps do not change the raw scanner, semantic classifier, scoring model, or mitigation model. They affect the trustworthiness of surrounding evidence and the safe rendering of metadata.

## Decision

Patch 036 hardens these seams without changing schema version or redefining candidate semantics:

- JSON text emission is byte-safe. Unsafe bytes in C strings and bounded section names are emitted as JSON escapes, including `\u00NN` for control and high-bit bytes.
- Section labels require both file-offset containment and virtual-address containment. Labels remain optional annotations and are omitted when file-offset and virtual-address evidence disagree.
- Docker build context filtering excludes `.env` and `.env.*`, while preserving a future `.env.example` allowlist.
- Benchmark smoke scripts reject non-positive `RUNS`, invalid `MAX_DEPTH`, nonnumeric timing/RSS fields, and negative timing/RSS values before producing normal evidence.
- Benchmark metadata records dereferenced target size for analyzed paths. Broad `bench-summary` refuses mixed TSV aggregation by default; `bench-summary-latest` selects the newest nonempty TSV artifact.
- Test helpers allocate per-run temporary directories with cleanup traps.
- The JSON report validator now checks that `primitive_coverage.registers` covers every register that appears in candidate control lists.
- The development-tool install hint uses shell builtins so a badly damaged `PATH` does not mask the actionable diagnostic.

## Consequences

Patch 036 favors evidence correctness over silent convenience. Some benchmark commands that previously appeared to succeed with empty or invalid artifacts now fail early. Users who intentionally want to aggregate multiple benchmark TSV files must opt in by setting `ALLOW_MIXED_BENCH_SUMMARY=1` and should treat the result as exploratory only.

The section-label policy remains conservative. It may omit labels on malformed or contradictory section tables, but it does not guess. Program headers and file-backed `PT_LOAD + PF_X` regions remain the runtime authority.
