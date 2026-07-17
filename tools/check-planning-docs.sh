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
    docs/design/decoder-gap-decision-gate.md
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
    docs/adr/0026-report-identity-and-analysis-completeness.md
    docs/adr/0027-candidate-evidence-sidecar-and-contract-hardening.md
    docs/adr/0028-decoder-gap-evidence-and-portable-bundle-policy.md
    docs/adr/0029-decoder-free-default-and-campaign-transaction-safety.md
    docs/adr/0030-campaign-integrity-and-bounded-acceleration-gates.md
    docs/adr/0031-sprint9-closeout-and-defensive-deployment-profile.md
    docs/adr/0032-ordered-multi-pop-foundation.md
    docs/adr/0033-exact-register-transfer-effects.md
    docs/design/candidate-scoped-decoder-and-parallelism.md
    docs/design/primitive-effect-model.md
    docs/design/defensive-deployment-profile.md
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
    docs/sprints/sprint-09-patch-040-validation.md
    docs/sprints/sprint-09-patch-041-validation.md
    docs/sprints/sprint-09-patch-042-validation.md
    docs/sprints/sprint-09-patch-043-validation.md
    docs/sprints/sprint-09-patch-044-validation.md
    docs/sprints/sprint-09-patch-045-validation.md
    docs/sprints/sprint-10-patch-046-validation.md
    docs/sprints/sprint-10-patch-047-validation.md
    docs/sprints/sprint-07-retro.md
    docs/sprints/sprint-08-retro.md
    docs/sprints/sprint-09-retro.md
    tests/malformed/README.md
    tests/malformed/regressions/README.md
    tests/malformed/regressions/elf64-shentsize-63.bin
    tools/malformed-elf-smoke.py
    tools/validate-capacity-fixture.sh
    tools/mitigation-matrix-smoke.py
    tools/section-label-smoke.py
    tools/benchmark-integrity-smoke.py
    tools/patch-bundle-hygiene-smoke.py
    tools/check-patch-bundle-hygiene.py
    tools/decoder-gap-smoke.py
    tools/decoder-gap-hardening-smoke.py
    tools/public-docs-hygiene-smoke.sh
    tools/readelf-comparison-smoke.py
    tools/optional-mitigation-comparison-smoke.py
    tools/schema-compat-smoke.py
    tools/validate-report-parity.py
    tools/json-effect-consistency-smoke.py
    tools/validate-sprint10-transfer-disassembly.py
    schemas/x64lens-report-0.1.0.schema.json
    schemas/x64lens-report.schema.json
    tests/expected/x64lens-report-0.1.0.json
    tests/expected/x64lens-report-0.2.0.json
    tests/expected/x64lens-report-0.2.0-p040.json
    tests/expected/x64lens-report-sprint10-0.2.0.json
    tests/expected/x64lens-report-sprint10-transfer-0.2.0.json
    tests/expected/decoder-gap-controlled.json
    tests/toy-src/gadgets_sprint10.S
    tests/toy-src/gadgets_sprint10_transfer.S
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
grep -Eq '^(Closed|Complete)' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 is not marked closed or complete'
grep -Eq '^(Next|Active)' docs/sprints/sprint-10-plan.md \
    || fail 'Sprint 10 is not marked as the next or active implementation tranche'
grep -q 'Patch 046' docs/sprints/sprint-10-plan.md \
    || fail 'Sprint 10 plan does not record the Patch 046 entry boundary'
grep -q 'Patch 047' docs/sprints/sprint-10-plan.md \
    || fail 'Sprint 10 plan does not record the Patch 047 register-transfer boundary'
grep -qi 'ordered multi-pop' docs/adr/0032-ordered-multi-pop-foundation.md \
    || fail 'ADR 0032 does not record the ordered multi-pop decision'
grep -qi 'register-transfer' docs/adr/0033-exact-register-transfer-effects.md \
    || fail 'ADR 0033 does not record the exact register-transfer decision'
grep -q 'stack_pop_order' docs/design/primitive-effect-model.md \
    || fail 'primitive-effect model does not define ordered pop facts'
grep -q 'sprint10-primitive-smoke' docs/sprints/sprint-10-patch-046-validation.md \
    || fail 'Patch 046 validation does not name the focused primitive gate'
grep -q 'sprint10-register-transfer-smoke' docs/sprints/sprint-10-patch-047-validation.md \
    || fail 'Patch 047 validation does not name the transfer fixture gate'
grep -q 'json-effect-consistency-smoke' docs/sprints/sprint-10-patch-047-validation.md \
    || fail 'Patch 047 validation does not name the effect consistency gate'
grep -q 'Patch 040' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the Patch 040 foundation'
grep -q 'Patch 041' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the Patch 041 provenance foundation'
grep -q 'Patch 042' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the Patch 042 decoder-gap foundation'
grep -q 'Patch 043' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the Patch 043 campaign-hardening decision'
grep -qi 'decoder-free' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the decoder-free default decision'
grep -q 'Patch 044' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the Patch 044 corrective boundary'
grep -q 'Patch 045' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not preserve the Patch 045 closeout boundary'
grep -q 'Sprint 10' docs/sprints/sprint-09-retro.md \
    || fail 'Sprint 9 retrospective does not hand off to Sprint 10'
grep -qi 'defensive deployment' docs/adr/0031-sprint9-closeout-and-defensive-deployment-profile.md \
    || fail 'Sprint 9 closeout ADR does not record the defensive deployment profile'
grep -qi 'air-gapped' docs/design/defensive-deployment-profile.md \
    || fail 'defensive deployment profile does not record air-gapped operation'
grep -qi 'candidate-scoped' docs/sprints/sprint-09-plan.md \
    || fail 'Sprint 9 plan does not record the bounded decoder direction'
grep -qi 'parallel' docs/design/candidate-scoped-decoder-and-parallelism.md \
    || fail 'bounded acceleration design does not record the parallelism gate'
grep -q 'decoder-gap-smoke' docs/sprints/sprint-09-patch-042-validation.md \
    || fail 'Patch 042 validation does not name the controlled decoder-gap gate'
grep -q 'require-provenance' docs/sprints/sprint-09-patch-041-validation.md \
    || fail 'Patch 041 validation does not require current candidate provenance'
grep -q 'schema-compat-smoke' docs/sprints/sprint-09-patch-040-validation.md \
    || fail 'Patch 040 validation does not name schema compatibility'
# The grep pattern intentionally contains literal Markdown backticks.
# shellcheck disable=SC2016
grep -qi 'schema `0.2.0`' docs/json-schema.md \
    || fail 'current JSON schema documentation is not at 0.2.0'
grep -q '%define X64LENS_SCHEMA       "0.2.0"' include/constants.inc \
    || fail 'compiled schema version is not 0.2.0'
grep -q '^SCHEMA       := 0.2.0$' Makefile \
    || fail 'Makefile schema variable is not 0.2.0'
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
grep -q '^patch-bundle-hygiene-smoke:' Makefile \
    || fail 'Makefile does not define patch-bundle-hygiene-smoke'
grep -q '^decoder-gap-smoke:' Makefile \
    || fail 'Makefile does not define decoder-gap-smoke'
grep -q '^decoder-gap-campaign:' Makefile \
    || fail 'Makefile does not define decoder-gap-campaign'
grep -q '^decoder-gap-hardening-smoke:' Makefile \
    || fail 'Makefile does not define decoder-gap-hardening-smoke'
grep -q '^public-docs-hygiene-smoke:' Makefile \
    || fail 'Makefile does not define public-docs-hygiene-smoke'
grep -q '^readelf-comparison-smoke:' Makefile \
    || fail 'Makefile does not define readelf-comparison-smoke'
grep -q '^optional-tool-comparison-smoke:' Makefile \
    || fail 'Makefile does not define optional-tool-comparison-smoke'
grep -q '^schema-compat-smoke:' Makefile \
    || fail 'Makefile does not define schema-compat-smoke'
grep -q '^sprint10-primitive-smoke:' Makefile \
    || fail 'Makefile does not define sprint10-primitive-smoke'
grep -q '^sprint10-register-transfer-smoke:' Makefile \
    || fail 'Makefile does not define sprint10-register-transfer-smoke'
grep -q '^json-effect-consistency-smoke:' Makefile \
    || fail 'Makefile does not define json-effect-consistency-smoke'
grep -q '^sprint-closeout-smoke:' Makefile \
    || fail 'Makefile does not define sprint-closeout-smoke'
grep -Eq '^validation-smoke:.*public-docs-hygiene-smoke.*benchmark-integrity-smoke.*patch-bundle-hygiene-smoke.*schema-compat-smoke.*decoder-gap-hardening-smoke.*decoder-gap-smoke.*sprint10-primitive-smoke.*sprint10-register-transfer-smoke.*json-effect-consistency-smoke.*capacity-smoke.*malformed-smoke.*mitigation-matrix-smoke.*section-label-smoke.*readelf-comparison-smoke.*optional-tool-comparison-smoke' Makefile \
    || fail 'validation-smoke does not include public-document, benchmark, bundle, schema, decoder hardening, decoder-gap, Sprint 10 primitive/effect, capacity, malformed, mitigation, section-label, readelf, and optional-tool gates'

printf 'planning-docs-check: ok plans=%d forward_plans=%d\n' \
    "$plan_count" "$forward_count"
