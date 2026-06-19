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
    docs/sprints/sprint-06-patch-024-validation.md
)

for path in "${required[@]}"; do
    [[ -f "$path" ]] || fail "missing required file: $path"
done

sprint_count=0
for sprint in $(seq -w 7 18); do
    path="docs/sprints/sprint-${sprint}-plan.md"
    [[ -f "$path" ]] || fail "missing sprint plan: $path"
    grep -q '^## Status$' "$path" || fail "missing Status section: $path"
    grep -q '^## Sprint goal$' "$path" || fail "missing Sprint goal section: $path"
    if grep -qi 'candidate extended-semester sprint' "$path"; then
        fail "superseded candidate status remains in $path"
    fi
    sprint_count=$((sprint_count + 1))
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
grep -q 'schema `0.2.0`' docs/design/schema-evolution.md \
    || fail 'schema transition gate is missing'

printf 'planning-docs-check: ok sprints=%d\n' "$sprint_count"
