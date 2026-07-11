# ADR 0026: Report identity and analysis completeness foundation

## Status

Accepted for Sprint 9 Patch 040.

## Context

Schema `0.1.0` gave `gadgets --format json` and `analyze --format json` one
shared record-backed report shape, but the document did not identify which
command produced it. Successful reports also exposed candidate capacity and
candidate count only indirectly through existing sections; they did not state
whether every executable region was scanned or whether candidate discovery was
truncated.

The current scanner has an explicit 4096-record capacity. Discovery of a 4097th
candidate returns `EXIT_UNSUPPORTED` before either text or JSON output begins.
Because that fail-closed path stops immediately, a total dropped-candidate count
is not known without changing the scanner to continue counting. Inventing a
dropped count or emitting a partial report would violate the existing capacity
and complete-report contracts.

Sprint 9 also requires a stable envelope for later per-candidate provenance and
decoder evidence. That envelope must not move file mapping, ELF parsing,
executable-region authority, scanning, classification, scoring, or output
formatting into the wrong module.

## Decision

Patch 040 introduces schema `0.2.0` with a command-owned, fixed-size
`analysis_summary` record. `gadgets` and `analyze` construct the record only
after the shared analysis pipeline has completed successfully, then pass it to
the existing text and JSON adapters.

The record and JSON `analysis` object carry:

- report type and command identity,
- selected maximum depth,
- candidate capacity and emitted candidate count,
- candidate truncation state,
- dropped-candidate count plus an explicit known flag,
- executable regions scanned and total,
- overall analysis completion.

Current successful reports have:

```text
report_type = analysis
complete = true
candidate_truncated = false
candidate_dropped_count = 0
candidate_dropped_count_known = true
regions_scanned = regions_total
```

The 4097-candidate case remains unchanged: exit code `6`, the stable unsupported
feature diagnostic on stderr, and empty stdout. Patch 040 does not introduce a
partial-report mode and does not claim a dropped count for a report that is not
emitted.

Top-level JSON adds:

```json
{
  "report_type": "analysis",
  "command": "gadgets",
  "analysis": {}
}
```

`command` is `gadgets` or `analyze`. Both commands continue to use one JSON
implementation and the same scanner, classifier, scoring, mitigation, and
candidate records.

A historical schema snapshot and representative `0.1.0` report are retained.
The bundled validator accepts both `0.1.0` and `0.2.0`, while current producer
validation requires `0.2.0` and the expected command identity.

Per-candidate evidence side-car records, target digests, decoder-validation
facts, and decoder-gap measurement remain later Sprint 9 work. They will extend
the new report envelope rather than replace it.

## Consequences

Schema `0.2.0` is an intentional minor-schema transition. Existing raw, exact,
semantic, unknown, and scored counts keep their historical meanings. Program
headers remain authoritative for executable mappings, section and dynamic data
remain bounded evidence, and reporters remain passive adapters.

Automation that requires the current producer must request schema `0.2.0`.
Historical consumers can validate retained `0.1.0` reports with the versioned
schema and validator path. Benchmark datasets from the two schema versions must
remain separate unless an explicit normalization is documented.

A future partial-analysis mode will require scanner behavior that can state
truthful region progress and dropped-count knowledge. It must not be inferred
from the successful-report state introduced here.
