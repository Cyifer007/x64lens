
# Sprint 06 Patch 023 Validation

## Scope

Patch 023 closes the integrated checkpoint by adding a repeatable demo path, composable text report sections, benchmark-smoke interpretation, paper-scaffold alignment, local tag guidance, and public-documentation hygiene checks.

## Required validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make validation-smoke
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-test
```

## Text-output regression

```bash
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets   > /tmp/x64lens-analyze-023.txt
test "$(grep -c '^x64lens ' /tmp/x64lens-analyze-023.txt)" -eq 1
test "$(grep -c '^Target: ' /tmp/x64lens-analyze-023.txt)" -eq 1
```

## Expected result

- Focused commands retain complete banners.
- `analyze` emits one version line and one target line.
- `Format:`, `Mitigations:`, `Executable regions:`, and `Raw gadget candidates:` remain present.
- JSON shape and analysis facts remain unchanged.
- The controlled and system demonstrations finish with `checkpoint-demo: ok`.
- Public documentation contains no private local paths or coordination wording.

## Tagging step

After the patch is committed, run `make checkpoint-tag-help` and create the local annotated `v0.1.0-dev` tag. Tag creation is not part of automated validation because it mutates repository history metadata.
