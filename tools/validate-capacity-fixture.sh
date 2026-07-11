#!/usr/bin/env bash
# Validate exact and exceeded candidate-capacity behavior.
#
# The exact fixture contains 4096 return terminators, matching the current
# candidate arena. The overflow fixture contains 4097. The exact boundary must
# produce a complete JSON report, while the overflow case must fail with
# EXIT_UNSUPPORTED (6), emit no partial report, and preserve the stable
# unsupported-feature diagnostic.

set -euo pipefail

X64LENS=${1:-./build/x64lens}
OVERFLOW_FIXTURE=${2:-./tests/bin/gadgets_capacity}
EXACT_FIXTURE=${3:-./tests/bin/gadgets_capacity_exact}
TMP_ROOT=${TMPDIR:-/tmp}
WORK_DIR=$(mktemp -d "$TMP_ROOT/x64lens-capacity-smoke.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

[[ -x "$X64LENS" ]] || { echo "capacity-smoke: error: executable not found: $X64LENS" >&2; exit 2; }
[[ -f "$EXACT_FIXTURE" ]] || { echo "capacity-smoke: error: exact fixture not found: $EXACT_FIXTURE" >&2; exit 2; }
[[ -f "$OVERFLOW_FIXTURE" ]] || { echo "capacity-smoke: error: overflow fixture not found: $OVERFLOW_FIXTURE" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "capacity-smoke: error: python3 is required" >&2; exit 127; }

exact_gadgets_json="$WORK_DIR/exact-capacity-gadgets.json"
exact_analyze_json="$WORK_DIR/exact-capacity-analyze.json"
"$X64LENS" gadgets --format json --max-depth 4 "$EXACT_FIXTURE" >"$exact_gadgets_json"
"$X64LENS" analyze --format json --max-depth 4 "$EXACT_FIXTURE" >"$exact_analyze_json"
python3 "$(dirname "$0")/validate-json-report.py" \
    --mode system --require-schema 0.2.0 --expected-command gadgets --require-provenance \
    "$exact_gadgets_json" >/dev/null
python3 "$(dirname "$0")/validate-json-report.py" \
    --mode system --require-schema 0.2.0 --expected-command analyze --require-provenance \
    "$exact_analyze_json" >/dev/null
python3 "$(dirname "$0")/validate-report-parity.py" \
    "$exact_gadgets_json" "$exact_analyze_json" >/dev/null
python3 - "$exact_gadgets_json" "$exact_analyze_json" <<'PY'
import json
import sys
for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    command = report.get("command", "unknown")
    counts = report.get("counts", {})
    gadgets = report.get("gadgets", [])
    if counts.get("raw_candidate_count") != 4096:
        raise SystemExit(f"capacity-smoke: {command} exact fixture raw count is not 4096")
    if len(gadgets) != 4096:
        raise SystemExit(f"capacity-smoke: {command} exact fixture gadget array is not complete")
    if any("evidence" not in gadget for gadget in gadgets):
        raise SystemExit(f"capacity-smoke: {command} exact fixture evidence array is incomplete")
    analysis = report.get("analysis", {})
    if analysis.get("complete") is not True:
        raise SystemExit(f"capacity-smoke: {command} exact fixture analysis is not complete")
    if analysis.get("candidate_capacity") != 4096:
        raise SystemExit(f"capacity-smoke: {command} exact fixture capacity is not 4096")
    if analysis.get("candidate_count") != 4096:
        raise SystemExit(f"capacity-smoke: {command} exact fixture analysis count is not 4096")
    if analysis.get("candidate_truncated") is not False:
        raise SystemExit(f"capacity-smoke: {command} exact fixture was marked truncated")
    if analysis.get("candidate_dropped_count") != 0:
        raise SystemExit(f"capacity-smoke: {command} exact fixture dropped count is not zero")
    if analysis.get("candidate_dropped_count_known") is not True:
        raise SystemExit(f"capacity-smoke: {command} exact fixture dropped count is not known")
PY

EXPECTED_UNSUPPORTED="$WORK_DIR/expected-unsupported.stderr"
printf '%s\n' 'error: unsupported binary feature' >"$EXPECTED_UNSUPPORTED"

run_expect_unsupported() {
    local name=$1
    shift
    local stdout_file="$WORK_DIR/$name.stdout"
    local stderr_file="$WORK_DIR/$name.stderr"

    set +e
    "$@" >"$stdout_file" 2>"$stderr_file"
    local status=$?
    set -e

    if [[ $status -ne 6 ]]; then
        echo "capacity-smoke: error: expected exit 6, got $status: $*" >&2
        echo "--- stdout ---" >&2
        cat "$stdout_file" >&2
        echo "--- stderr ---" >&2
        cat "$stderr_file" >&2
        exit 1
    fi

    [[ ! -s "$stdout_file" ]] || {
        echo "capacity-smoke: error: partial stdout was emitted for $name" >&2
        exit 1
    }
    cmp -s "$EXPECTED_UNSUPPORTED" "$stderr_file" || {
        echo "capacity-smoke: error: stderr was not byte-exact for $name" >&2
        echo "--- expected ---" >&2
        cat "$EXPECTED_UNSUPPORTED" >&2
        echo "--- actual ---" >&2
        cat "$stderr_file" >&2
        exit 1
    }
}

run_expect_unsupported gadgets-text \
    "$X64LENS" gadgets --max-depth 4 "$OVERFLOW_FIXTURE"
run_expect_unsupported gadgets-json \
    "$X64LENS" gadgets --format json --max-depth 4 "$OVERFLOW_FIXTURE"
run_expect_unsupported analyze-text \
    "$X64LENS" analyze --max-depth 4 "$OVERFLOW_FIXTURE"
run_expect_unsupported analyze-json \
    "$X64LENS" analyze --format json --max-depth 4 "$OVERFLOW_FIXTURE"

echo "capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6"
