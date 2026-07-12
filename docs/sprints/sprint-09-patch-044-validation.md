# Sprint 09 Patch 044 Validation

## Scope

Patch 044 corrects research-campaign, external-parser, archive-policy, and
public-document defects found during Patch 043 validation. It does not change
analyzer assembly, internal record layouts, schema `0.2.0`, candidate counts,
classification, scoring, or runtime dependencies.

Sprint 9 closeout is deferred to Patch 045 so this corrective patch can be
accepted on focused evidence.

## Required focused gates

```bash
make public-docs-hygiene-smoke
make patch-bundle-hygiene-smoke
make decoder-gap-hardening-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

Expected focused banners:

```text
public-docs-hygiene-smoke: ok cases=9 accepted=1 rejected=8
patch-bundle-hygiene-smoke: ok cases=64 accepted=7 rejected=57 wrapper_replays=64
decoder-gap-hardening-smoke: ok parser=2 snapshots=2 publication_interruptions=10 measured_signal_cleanup=2
shellcheck-smoke: ok
```

## Campaign transaction requirements

- `SIGINT` and `SIGTERM` after the prior result rename but before the next
  Python assignment restore the prior recognized result.
- Signals during GNU-time/analyzer measurement kill and reap the complete child
  process group before campaign exit.
- Cleanup is idempotent and preserves an unrelated destination.
- A complete newly published tree may remain visible after a post-publish
  interruption; an incomplete tree may not.

## Objdump parser requirements

- All 27 reviewed GNU objdump prefix/near-return forms are normalized.
- `retw` and supported near-return variants are recognized.
- Segment- and REX-prefixed jumps/calls remain predecessor barriers.
- Prefix-only, malformed, wrapped, discontinuous, and section-transition rows
  remain bounded and diagnostic.

Objdump evidence remains development comparison evidence only.

## ZIP policy requirements

The production shell wrapper and Python policy must reject:

- local/central filename disagreement;
- local Unicode-path override disagreement;
- local/central encryption and flag disagreement;
- unsupported local extra fields;
- ZIP64 fields without matching sentinels or with wrong ordered values;
- zero-width UID/GID identifiers;
- NTFS reserved/attribute violations;
- duplicate conflicting recognized extra fields;
- every existing private/generated/path/type case under arbitrary roots.

The checker remains metadata-only and must not extract member payloads.

## Public boundary requirements

Public tracked content must not contain real timestamped transfer-artifact
basenames, local home paths, WSL UNC paths, Windows profile paths, or broader
copy/case variants. Negative fixtures use unmistakably synthetic values.

## Full acceptance matrix

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make clean
make
make samples
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make decoder-gap-campaign
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Default Buildx metadata failures must be classified separately. A qualified
writable Buildx configuration must execute the same product validation path.

## Invariants

- no tracked path under `src/`, `include/`, or `schemas/` changes;
- program headers remain executable-region authority;
- raw, exact, semantic, unknown, decoder, and scored metrics remain distinct;
- capacity overflow remains exit 6 with empty stdout;
- malformed failures emit no partial stdout;
- tool version remains `0.1.0-dev` and schema remains `0.2.0`;
- `v0.1.0-dev` remains pinned to its historical checkpoint.
