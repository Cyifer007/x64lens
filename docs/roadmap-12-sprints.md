# Twelve-Sprint Roadmap, Superseded Planning View

## Status

This file is retained for link compatibility and historical context. The canonical roadmap is now [`roadmap-18-sprints.md`](roadmap-18-sprints.md).

## Why the roadmap expanded

The original plan grew from six sprints to twelve as the repository reached scoring, JSON, validation hardening, baseline smoke benchmarking, and integrated analysis earlier than expected. Sprint 6 then completed the `v0.1.0-dev` checkpoint.

The Patch 024 review found that the remaining twelve-sprint ceiling did not allocate enough distinct space for:

- hostile-input regression and parser safety,
- mitigation accuracy,
- candidate evidence provenance,
- higher-resolution benchmarking,
- a reproducible corpus,
- an operational case study,
- schema stabilization,
- replication and publication freeze.

Those concerns are now separated across Sprints 7 through 18.

## Current first twelve sprints

| Sprint | Current theme |
|---|---|
| 1 | ELF64 identity |
| 2 | Loader mapping and baseline mitigations |
| 3 | Scanner foundation and exact suffix patterns |
| 4 | Semantic classification |
| 5 | Scoring, JSON, validation, and benchmark plumbing |
| 6 | Integrated `analyze` checkpoint and demo |
| 7 | Hostile-input hardening |
| 8 | Mitigation and metadata depth |
| 9 | Candidate provenance and decoder-gap measurement |
| 10 | Primitive expansion |
| 11 | Reproducible corpus |
| 12 | High-resolution benchmark infrastructure and research preview candidate |

Sprints 13 through 18 continue through the comparative campaign, triage model, automation stabilization, infrastructure case study, replication freeze, and first research release.

## Compatibility rule

New planning changes should update `docs/roadmap-18-sprints.md`. This compatibility file should change only when the relationship between the historical twelve-sprint view and the canonical roadmap changes.
