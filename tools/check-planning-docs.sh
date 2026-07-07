#!/usr/bin/env bash
# Validate the structural planning contract for the post-checkpoint roadmap.
# This check confirms that canonical roadmap, release, design, ADR, and sprint
# files exist and that superseded planning language is not active in Sprint 7
# through Sprint 18 plans. It does not replace editorial or technical review.

set -euo pipefail

fail() {
    printf 'planning-docs-check: error: %s\n' "$*" >&2
    exit 1
}

required=(
    README.md
    docs/roadmap-18-sprints.md
    docs/roadmap-12-sprints.md
    docs/research-release-plan.md
    docs/design/evidence-provenance-model.md
    docs/design/schema-evolution.md
    docs/design/decoder-roadmap.md
    docs/design/metric-boundaries.md
    docs/design/parser-safety-and-fuzzing.md
    docs/adr/0012-roadmap-expansion-and-research-release-gates.md
    docs/adr/0013-deterministic-hostile-input-regression-harness.md
    docs/adr/0014-deterministic-mitigation-oracle.md
    docs/adr/0015-shared-checked-parser-arithmetic.md
    docs/adr/0016-bounded-dynamic-table-view.md
    docs/adr/0017-relro-refinement-and-duplicate-dynamic-policy.md
    docs/adr/0018-canary-indicator-and-dynamic-string-scan.md
    docs/adr/0019-stripped-indicator-and-dynamic-singleton-policy.md
    docs/adr/0020-section-label-annotations.md
    docs/adr/0021-section-label-rendering-and-ambiguity.md
    docs/adr/0022-historical-findings-hardening.md
    docs/adr/0023-comparator-and-benchmark-integrity-gates.md
    docs/adr/0024-sprint8-closeout-and-helper-hardening.md
    docs/adr/0025-sprint8-closeout-correction.md
    docs/design/mitigation-fixture-matrix.md
    docs/sprints/sprint-06-patch-024-validation.md
    docs/sprints/sprint-07-patch-025-validation.md
    docs/sprints/sprint-07-patch-026-validation.md
    docs/sprints/sprint-07-patch-027-validation.md
    docs/sprints/sprint-07-patch-028-validation.md
    docs/sprints/sprint-07-patch-029-validation.md
    docs/sprints/sprint-08-patch-030-validation.md
    docs/sprints/sprint-08-patch-031-validation.md
    docs/sprints/sprint-08-patch-032-validation.md
    docs/sprints/sprint-08-patch-033-validation.md
    docs/sprints/sprint-08-patch-034-validation.md
    docs/sprints/sprint-08-patch-035-validation.md
    docs/sprints/sprint-08-patch-036-validation.md
    docs/sprints/sprint-08-patch-037-validation.md
    docs/sprints/sprint-08-patch-038-validation.md
    docs/sprints/sprint-08-patch-039-validation.md
    docs/sprints/sprint-07-retro.md
    docs/sprints/sprint-08-retro.md
    tests/malformed/README.md
    tests/malformed/regressions/README.md
    tests/malformed/regressions/elf64-shentsize-63.bin
    tools/malformed-elf-smoke.py
    tools/validate-capacity-fixture.sh
    tools/mitigation-matrix-smoke.py
    tools/section-label-smoke.py
    tools/benchmark-integrity-smoke.py
    tools/readelf-comparison-smoke.py
    tools/optional-mitigation-comparison-smoke.py
)

for path in "${required[@]}"; do
    [[ -f "$path" ]] || fail "missing required file: $path"
done

plan_count=0
for sprint in $(seq -w 1 18); do
    path="docs/sprints/sprint-${sprint}-plan.md"
    [[ -f "$path" ]] || fail "missing sprint plan: $path"
    plan_count=$((plan_count + 1))
done

forward_count=0
for sprint in $(seq -w 9 18); do
    path="docs/sprints/sprint-${sprint}-plan.md"
    grep -q '^## Status$' "$path" || fail "missing Status section: $path"
    grep -q '^## Sprint goal$' "$path" || fail "missing Sprint goal section: $path"
    if grep -qi 'candidate extended-semester sprint' "$path"; then
        fail "superseded candidate status remains in $path"
    fi
    forward_count=$((forward_count + 1))
done

grep -q 'docs/roadmap-18-sprints.md' README.md \
    || fail 'README does not reference the canonical eighteen-sprint roadmap'
grep -q 'canonical roadmap' docs/roadmap-18-sprints.md \
    || fail 'canonical roadmap declaration is missing'
grep -qi 'superseded' docs/roadmap-12-sprints.md \
    || fail 'twelve-sprint compatibility document is not marked superseded'
grep -q 'v0.1.0-rc1' docs/research-release-plan.md \
    || fail 'research preview gate is missing'
grep -q 'v0.1.0' docs/research-release-plan.md \
    || fail 'first research release gate is missing'
# The grep pattern intentionally contains literal Markdown backticks.
# shellcheck disable=SC2016
grep -q 'schema `0.2.0`' docs/design/schema-evolution.md \
    || fail 'schema transition gate is missing'
grep -Eq '^(Closed|Complete)' docs/sprints/sprint-07-plan.md \
    || fail 'Sprint 7 is not marked closed or complete'
grep -Eq '^(Closed|Complete)' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 is not marked closed or complete'
grep -Eq '^(Next|Active)' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 is not marked as the next or active implementation tranche'
grep -q 'make malformed-smoke' docs/sprints/sprint-07-plan.md \
    || fail 'Sprint 7 plan does not name the malformed-input gate'
grep -q 'make mitigation-matrix-smoke' docs/sprints/sprint-07-plan.md \
    || fail 'Sprint 7 plan does not name the mitigation oracle gate'
grep -Eq 'checked (table|parser) arithmetic' docs/sprints/sprint-07-plan.md \
    || fail 'Sprint 7 plan does not name the checked parser arithmetic gate'
grep -q '^## Recommended patch sequence$' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 recommended patch sequence is missing'
grep -qi 'bounded dynamic' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name bounded dynamic-table work'
grep -qi 'stripped' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name stripped-state work'
grep -qi 'section labels' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name section-label work'
grep -qi 'historical review findings' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name the Patch 036 historical findings hardening pass'
grep -qi 'readelf' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name the readelf comparison gate'
grep -qi 'checksec' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name the optional checksec comparison gate'
grep -qi 'rabin2' docs/sprints/sprint-08-plan.md \
    || fail 'Sprint 8 plan does not name the optional rabin2 comparison gate'
grep -q 'Sprint 8' docs/sprints/sprint-07-retro.md \
    || fail 'Sprint 7 retrospective does not hand off to Sprint 8'
grep -qi 'mitigation' docs/sprints/sprint-07-retro.md \
    || fail 'Sprint 7 retrospective does not preserve mitigation handoff context'
grep -q 'Sprint 9' docs/sprints/sprint-08-retro.md \
    || fail 'Sprint 8 retrospective does not hand off to Sprint 9'
# The grep pattern intentionally contains literal Markdown backticks.
# shellcheck disable=SC2016
grep -qi 'schema `0.2.0`' docs/sprints/sprint-08-retro.md \
    || fail 'Sprint 8 retrospective does not preserve schema 0.2.0 handoff context'

grep -q '^malformed-smoke:' Makefile \
    || fail 'Makefile does not define malformed-smoke'
grep -q '^capacity-smoke:' Makefile \
    || fail 'Makefile does not define capacity-smoke'
grep -q '^mitigation-matrix-smoke:' Makefile \
    || fail 'Makefile does not define mitigation-matrix-smoke'
grep -q '^section-label-smoke:' Makefile \
    || fail 'Makefile does not define section-label-smoke'
grep -q '^docker-validation-smoke:' Makefile \
    || fail 'Makefile does not define docker-validation-smoke'
grep -q '^benchmark-integrity-smoke:' Makefile \
    || fail 'Makefile does not define benchmark-integrity-smoke'
grep -q '^readelf-comparison-smoke:' Makefile \
    || fail 'Makefile does not define readelf-comparison-smoke'
grep -q '^optional-tool-comparison-smoke:' Makefile \
    || fail 'Makefile does not define optional-tool-comparison-smoke'
grep -Eq '^validation-smoke:.*benchmark-integrity-smoke.*capacity-smoke.*malformed-smoke.*mitigation-matrix-smoke.*section-label-smoke.*readelf-comparison-smoke.*optional-tool-comparison-smoke' Makefile \
    || fail 'validation-smoke does not include benchmark-integrity, capacity, malformed, mitigation, section-label, readelf, and optional-tool gates'

printf 'planning-docs-check: ok plans=%d forward_plans=%d\n' \
    "$plan_count" "$forward_count"
