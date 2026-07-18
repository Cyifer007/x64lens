#!/usr/bin/env bash
# Validate x64lens against installed ELF64 system binaries.
#
# Purpose:
#   Exercise info, mitigations, text gadgets, JSON gadgets, and integrated
#   analyze reports against real binaries that vary across Linux distributions. This is a smoke/regression
#   check, not a publication benchmark. It intentionally validates invariants
#   and output shape instead of asserting distro-specific gadget counts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="${1:-$ROOT/build/x64lens}"
MAX_DEPTH="${MAX_DEPTH:-4}"
TMPROOT="${TMPDIR:-/tmp}"
TMPDIR="$(mktemp -d "$TMPROOT/x64lens-system-smoke.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

if [[ $# -gt 0 ]]; then
  shift
fi

if [[ ! -x "$TOOL" ]]; then
  echo "system-binary-smoke: error: x64lens binary not executable: $TOOL" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "system-binary-smoke: error: python3 is required" >&2
  exit 1
fi

if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
else
  TARGETS=(/bin/ls /bin/cat /bin/sh /usr/bin/env /usr/bin/printf)
fi

tested=0
for target in "${TARGETS[@]}"; do
  [[ -e "$target" && ! -d "$target" ]] || continue

  info_out="$TMPDIR/x64lens-system-info-$(basename "$target").txt"
  mitigations_out="$TMPDIR/x64lens-system-mitigations-$(basename "$target").txt"
  gadgets_out="$TMPDIR/x64lens-system-gadgets-$(basename "$target").txt"
  json_out="$TMPDIR/x64lens-system-gadgets-$(basename "$target").json"
  analyze_out="$TMPDIR/x64lens-system-analyze-$(basename "$target").txt"
  analyze_json_out="$TMPDIR/x64lens-system-analyze-$(basename "$target").json"

  set +e
  "$TOOL" info "$target" >"$info_out" 2>"$TMPDIR/x64lens-system-info.err"
  status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    echo "system-binary-smoke: skipping unsupported or non-ELF target: $target"
    continue
  fi

  grep -q "Type: ELF64" "$info_out"
  grep -q "Machine: x86_64" "$info_out"

  "$TOOL" mitigations "$target" >"$mitigations_out"
  grep -q "Mitigations:" "$mitigations_out"
  grep -q "Executable LOAD regions:" "$mitigations_out"

  "$TOOL" gadgets --max-depth "$MAX_DEPTH" "$target" >"$gadgets_out"
  grep -q "Analysis:" "$gadgets_out"
  grep -q "Command: gadgets" "$gadgets_out"
  grep -q "Complete: yes" "$gadgets_out"
  grep -q "Raw gadget candidates:" "$gadgets_out"
  grep -q "Candidate count:" "$gadgets_out"
  grep -q "Exact pattern count:" "$gadgets_out"
  grep -q "Semantic primitive count:" "$gadgets_out"
  grep -q "Scored candidate count:" "$gadgets_out"

  "$TOOL" gadgets --format json --max-depth "$MAX_DEPTH" "$target" >"$json_out"
  python3 "$ROOT/tools/validate-json-report.py" --mode system --require-schema 0.2.0 --expected-command gadgets --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$json_out" >/dev/null

  "$TOOL" analyze --max-depth "$MAX_DEPTH" "$target" >"$analyze_out"
  grep -q "Format:" "$analyze_out"
  grep -q "Mitigations:" "$analyze_out"
  grep -q "Analysis:" "$analyze_out"
  grep -q "Command: analyze" "$analyze_out"
  grep -q "Complete: yes" "$analyze_out"
  grep -q "Raw gadget candidates:" "$analyze_out"

  "$TOOL" analyze --format json --max-depth "$MAX_DEPTH" "$target" >"$analyze_json_out"
  python3 "$ROOT/tools/validate-json-report.py" --mode system --require-schema 0.2.0 --expected-command analyze --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$analyze_json_out" >/dev/null
  python3 "$ROOT/tools/validate-report-parity.py" "$json_out" "$analyze_json_out" >/dev/null

  tested=$((tested + 1))
  echo "system-binary-smoke: ok target=$target"
done

if [[ "$tested" -eq 0 ]]; then
  echo "system-binary-smoke: error: no usable ELF64 x86_64 system targets were validated" >&2
  exit 1
fi

echo "system-binary-smoke: ok targets=$tested max_depth=$MAX_DEPTH"
