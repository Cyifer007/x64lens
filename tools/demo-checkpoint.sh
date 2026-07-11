#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
X64LENS=${1:-"$ROOT_DIR/build/x64lens"}
TARGET=${2:-"$ROOT_DIR/tests/bin/gadgets"}
MAX_DEPTH=${MAX_DEPTH:-4}

if [[ ! -x "$X64LENS" ]]; then
    echo "checkpoint-demo: missing executable: $X64LENS" >&2
    echo "Run 'make' before invoking this script directly." >&2
    exit 2
fi
if [[ ! -f "$TARGET" ]]; then
    echo "checkpoint-demo: missing target: $TARGET" >&2
    echo "Run 'make samples' for the default fixture." >&2
    exit 2
fi

TMP_JSON=$(mktemp "${TMPDIR:-/tmp}/x64lens-checkpoint-demo.XXXXXX.json")
trap 'rm -f "$TMP_JSON"' EXIT

printf '\n== x64lens checkpoint: version ==\n'
"$X64LENS" version

printf '\n== x64lens checkpoint: target metadata ==\n'
"$X64LENS" info "$TARGET"

printf '\n== x64lens checkpoint: mitigations and executable regions ==\n'
"$X64LENS" mitigations "$TARGET"

printf '\n== x64lens checkpoint: scored semantic gadget report ==\n'
"$X64LENS" gadgets --max-depth "$MAX_DEPTH" "$TARGET"

printf '\n== x64lens checkpoint: integrated analysis ==\n'
"$X64LENS" analyze --max-depth "$MAX_DEPTH" "$TARGET"

printf '\n== x64lens checkpoint: machine-readable analysis ==\n'
"$X64LENS" analyze --format json --max-depth "$MAX_DEPTH" "$TARGET" >"$TMP_JSON"
python3 -m json.tool "$TMP_JSON" >/dev/null

MODE=system
TARGET_CANON=$(readlink -f "$TARGET")
FIXTURE_CANON=$(readlink -f "$ROOT_DIR/tests/bin/gadgets")
if [[ "$TARGET_CANON" == "$FIXTURE_CANON" ]]; then
    MODE=fixture
fi
python3 "$ROOT_DIR/tools/validate-json-report.py" --mode "$MODE" --require-schema 0.2.0 --expected-command analyze "$TMP_JSON"
python3 - "$TMP_JSON" <<'PYJSON'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
counts = report["counts"]
coverage = report["primitive_coverage"]
print(f"report: {report['report_type']} command={report['command']}")
print(f"complete: {report['analysis']['complete']} truncated={report['analysis']['candidate_truncated']}")
print(f"target: {report['target']['path']}")
print(f"raw candidates: {counts['raw_candidate_count']}")
print(f"semantic candidates: {counts['semantic_candidate_count']}")
print(f"scored candidates: {counts['scored_candidate_count']}")
print("register coverage: " + (", ".join(coverage["registers"]) or "none"))
print("JSON report: syntactically and semantically valid")
PYJSON

printf '\ncheckpoint-demo: ok target=%s max_depth=%s\n' "$TARGET" "$MAX_DEPTH"
