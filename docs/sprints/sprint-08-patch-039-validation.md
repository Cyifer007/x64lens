# Sprint 08 Patch 039 validation

## Purpose

Patch 039 corrects the Patch 038 closeout validation findings and completes the
Sprint 8 context handoff.

Patch 038 correctly hardened optional comparator helper argument handling and
closed public Sprint 8 planning, but local validation found that the
benchmark-integrity smoke script did not actually generate the intended
non-finite-RSS fixture files, strict shell lint still had actionable findings,
and the private local project-context handoff remained stale.

## Implemented corrections

- Add explicit benchmark-integrity fixtures for:
  - `nan-rss.tsv`,
  - `inf-rss.tsv`,
  - `neg-inf-rss.tsv`.
- Keep summarizer behavior fail-closed for non-finite RSS values.
- Remove shellcheck-overlapping unsafe-path `case` patterns from patch-bundle
  hygiene by using explicit `[[ ... ]]` path checks.
- Document intentional literal Markdown-backtick grep strings for strict
  shellcheck in the planning-docs checker.
- Regenerate the public project-context and private local orchestration bundles
  externally as local-only handoff artifacts.

## Required native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make help
make print-vars
make dev-tools-check
make baseline-tools-check
make analysis-tools-check
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
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make benchmark-integrity-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make shellcheck-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Required targeted checks

```bash
make benchmark-integrity-smoke
for f in nan-rss.tsv inf-rss.tsv neg-inf-rss.tsv; do
  test -f "tests/results/benchmark-integrity/$f"
  python3 benchmarks/scripts/summarize.py "tests/results/benchmark-integrity/$f" && exit 1 || true
done

bash tools/compare-checksec.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-checksec.sh ./build/x64lens ./tests/bin/minimal_pie_canary
bash tools/compare-rabin2.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-rabin2.sh ./build/x64lens ./tests/bin/minimal_pie_canary
```

The comparator commands require `checksec` and `rabin2` respectively. If either
optional tool is absent, classify the absence as an environment fact and rely on
`make optional-tool-comparison-smoke` skip/record behavior.

## Required Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

If Docker Buildx metadata writes fail under a restricted filesystem sandbox but
unsandboxed reruns pass, classify the first failure as an environment defect,
not a product defect.

## Acceptance criteria

- `make validation-smoke` exits 0 and ends with `validation-smoke: ok`.
- `make benchmark-integrity-smoke` creates the three non-finite-RSS fixture
  files and the summarizer rejects each one.
- `SHELLCHECK_STRICT=1 make shellcheck-smoke` exits 0 when `shellcheck` is
  installed.
- Comparator helpers still pass both documented and mission-order argument
  forms and still reject same-file analyzer/target mistakes.
- Public planning docs report `planning-docs-check: ok plans=18 forward_plans=10`.
- External context bundles describe Patch 039 / Sprint 8 closeout and do not
  leave `.local/project-context` at Patch 029 / Sprint 7.
