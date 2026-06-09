#!/usr/bin/env bash
# bench-scanner-smoke.sh
#
# Purpose:
#   Capture the first reproducible scanner smoke measurements for Sprint 3.
#   This is not a publication benchmark. It is a development benchmark used to
#   prove that x64lens can run repeated gadget scans, preserve raw results,
#   preserve exact pattern counts, and produce a machine-readable timing table
#   for later analysis.
#
# Usage:
#   benchmarks/scripts/bench-scanner-smoke.sh [x64lens-binary] [target ...]
#
# Environment variables:
#   RUNS=5              Number of repeated runs per target.
#   MAX_DEPTH=4         Scanner max-depth passed to x64lens gadgets.
#   OUT_DIR=...         Output directory for result files.
#   STAMP=...           Override timestamp for reproducible file names.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="${1:-$ROOT/build/x64lens}"
if [[ $# -gt 0 ]]; then
  shift
fi

RUNS="${RUNS:-5}"
MAX_DEPTH="${MAX_DEPTH:-4}"
OUT_DIR="${OUT_DIR:-$ROOT/benchmarks/results}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS="$OUT_DIR/scanner-smoke-$STAMP.tsv"
META="$OUT_DIR/scanner-smoke-$STAMP.meta"
TMPDIR="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPDIR/x64lens-scanner-smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

if [[ ! -x "$TOOL" ]]; then
  echo "error: x64lens binary is not executable: $TOOL" >&2
  exit 1
fi

if ! command -v /usr/bin/time >/dev/null 2>&1; then
  echo "error: /usr/bin/time is required for benchmark smoke measurements" >&2
  exit 127
fi

mkdir -p "$OUT_DIR"

TARGETS=()
if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
else
  [[ -f "$ROOT/tests/bin/gadgets" ]] && TARGETS+=("$ROOT/tests/bin/gadgets")
  [[ -f "$ROOT/tests/bin/minimal_nopie" ]] && TARGETS+=("$ROOT/tests/bin/minimal_nopie")
  [[ -x /bin/ls ]] && TARGETS+=("/bin/ls")
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "error: no benchmark targets found" >&2
  echo "hint: run 'make samples' or pass target paths explicitly" >&2
  exit 1
fi

hex_value_from_line() {
  local label="$1"
  local file="$2"
  local value
  value="$(grep -m1 "$label" "$file" | sed -E 's/.*0x([0-9a-fA-F]+).*/0x\1/' || true)"
  if [[ -z "$value" ]]; then
    echo ""
  else
    printf "%d" "$value"
  fi
}

{
  echo "tool=x64lens"
  echo "tool_path=$TOOL"
  echo "tool_version=$($TOOL version 2>/dev/null || true)"
  echo "command=gadgets --max-depth $MAX_DEPTH <target>"
  echo "runs=$RUNS"
  echo "timestamp_utc=$STAMP"
  echo "uname=$(uname -a)"
  echo "nasm_version=$(nasm -v 2>/dev/null || true)"
  echo "ld_version=$(ld --version 2>/dev/null | head -n 1 || true)"
  echo "gcc_version=$(gcc --version 2>/dev/null | head -n 1 || true)"
} >"$META"

printf 'tool\tcommand\tmax_depth\ttarget\ttarget_size_bytes\trun\twall_s\tmaxrss_kb\texit_code\tcandidate_count\tret_count\tret_imm16_count\texact_pattern_count\toutput_bytes\n' >"$RESULTS"

for target in "${TARGETS[@]}"; do
  if [[ ! -f "$target" ]]; then
    echo "warning: skipping non-file target: $target" >&2
    continue
  fi

  target_size="$(stat -c '%s' "$target")"

  for run in $(seq 1 "$RUNS"); do
    out="$WORK/out-$run.txt"
    timefile="$WORK/time-$run.txt"

    set +e
    /usr/bin/time -o "$timefile" -f '%e\t%M\t%x' \
      "$TOOL" gadgets --max-depth "$MAX_DEPTH" "$target" >"$out" 2>"$WORK/stderr-$run.txt"
    status=$?
    set -e

    read -r wall maxrss time_exit <"$timefile"
    candidate_count="$(hex_value_from_line 'Candidate count:' "$out")"
    ret_count="$(hex_value_from_line 'ret count:' "$out")"
    ret_imm_count="$(hex_value_from_line 'ret imm16 count:' "$out")"
    pattern_count="$(hex_value_from_line 'Exact pattern count:' "$out")"
    output_bytes="$(wc -c <"$out" | tr -d ' ')"

    printf 'x64lens\tgadgets\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$MAX_DEPTH" "$target" "$target_size" "$run" "$wall" "$maxrss" "$status" \
      "${candidate_count:-NA}" "${ret_count:-NA}" "${ret_imm_count:-NA}" \
      "${pattern_count:-NA}" "$output_bytes" >>"$RESULTS"

    if [[ "$status" -ne 0 ]]; then
      echo "error: benchmark command failed for $target run $run with exit $status" >&2
      echo "--- stderr ---" >&2
      cat "$WORK/stderr-$run.txt" >&2
      exit "$status"
    fi
  done
done

cat <<MSG
scanner-smoke benchmark complete
  results: $RESULTS
  metadata: $META
  runs: $RUNS
  max_depth: $MAX_DEPTH
MSG
