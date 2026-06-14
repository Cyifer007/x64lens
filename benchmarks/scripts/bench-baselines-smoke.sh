#!/usr/bin/env bash
# bench-baselines-smoke.sh
#
# Purpose:
#   Capture development-level comparison rows for x64lens and optional gadget
#   discovery baselines. This is smoke evidence for benchmark plumbing, not a
#   publication claim. Missing optional baseline tools are recorded in metadata
#   and skipped unless REQUIRE_BASELINES=1 is set.
#
# Usage:
#   benchmarks/scripts/bench-baselines-smoke.sh [x64lens-binary] [target ...]
#
# Environment variables:
#   RUNS=3                  Number of repeated runs per target.
#   MAX_DEPTH=4             x64lens gadget max-depth.
#   OUT_DIR=...             Output directory for result files.
#   STAMP=...               Override timestamp for reproducible file names.
#   REQUIRE_BASELINES=0     If 1, fail when no optional baseline tool is found.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="${1:-$ROOT/build/x64lens}"
if [[ $# -gt 0 ]]; then
  shift
fi

RUNS="${RUNS:-3}"
MAX_DEPTH="${MAX_DEPTH:-4}"
OUT_DIR="${OUT_DIR:-$ROOT/benchmarks/results}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
REQUIRE_BASELINES="${REQUIRE_BASELINES:-0}"
RESULTS="$OUT_DIR/baseline-smoke-$STAMP.tsv"
META="$OUT_DIR/baseline-smoke-$STAMP.meta"
TMPDIR="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPDIR/x64lens-baseline-smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

if [[ ! -x "$TOOL" ]]; then
  echo "error: x64lens binary is not executable: $TOOL" >&2
  exit 1
fi

if ! command -v /usr/bin/time >/dev/null 2>&1; then
  echo "error: /usr/bin/time is required for benchmark measurements" >&2
  exit 127
fi

mkdir -p "$OUT_DIR"

TARGETS=()
if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
else
  [[ -f "$ROOT/tests/bin/gadgets" ]] && TARGETS+=("$ROOT/tests/bin/gadgets")
  [[ -x /bin/ls ]] && TARGETS+=("/bin/ls")
  [[ -x /bin/cat ]] && TARGETS+=("/bin/cat")
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "error: no benchmark targets found" >&2
  echo "hint: run 'make samples' or pass target paths explicitly" >&2
  exit 1
fi

sha256_of() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  else
    echo "NA"
  fi
}

manifest_hash() {
  local manifest="$ROOT/tests/corpus-manifest.json"
  if [[ -f "$manifest" ]] && command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$manifest" | awk '{print $1}'
  else
    echo "NA"
  fi
}

tool_version() {
  local name="$1"
  local path="$2"
  case "$name" in
    x64lens)
      "$path" version 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//'
      ;;
    ROPgadget)
      ROPgadget --version 2>/dev/null | head -n 1 || true
      ;;
    ropper)
      ropper --version 2>/dev/null | head -n 1 || true
      ;;
    ropr)
      ropr --version 2>/dev/null | head -n 1 || true
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

json_count() {
  local path="$1"
  local key="$2"
  python3 - "$path" "$key" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    data = json.load(handle)
value = data.get("counts", {}).get(sys.argv[2])
print("NA" if value is None else value)
PY
}

run_timed() {
  local tool_name="$1"
  local tool_path="$2"
  local command_text="$3"
  local target="$4"
  local run="$5"
  shift 5
  local out="$WORK/${tool_name//[^A-Za-z0-9_]/_}-$run.out"
  local err="$WORK/${tool_name//[^A-Za-z0-9_]/_}-$run.err"
  local timefile="$WORK/${tool_name//[^A-Za-z0-9_]/_}-$run.time"

  set +e
  /usr/bin/time -o "$timefile" -f '%e\t%M\t%x' "$@" >"$out" 2>"$err"
  local status=$?
  set -e

  local wall maxrss time_exit
  read -r wall maxrss time_exit <"$timefile"
  local output_bytes output_lines
  output_bytes="$(wc -c <"$out" | tr -d ' ')"
  output_lines="$(wc -l <"$out" | tr -d ' ')"

  local raw="NA" exact="NA" semantic="NA" unknown="NA" scored="NA" note="ok"

  if [[ "$tool_name" == "x64lens" && "$status" -eq 0 ]]; then
    if ! python3 -m json.tool "$out" >/dev/null; then
      note="invalid_json"
      status=1
    elif ! python3 "$ROOT/tools/validate-json-report.py" --mode system "$out" >/dev/null; then
      note="json_validator_failed"
      status=1
    else
      raw="$(json_count "$out" raw_candidate_count)"
      exact="$(json_count "$out" exact_pattern_count)"
      semantic="$(json_count "$out" semantic_candidate_count)"
      unknown="$(json_count "$out" unknown_candidate_count)"
      scored="$(json_count "$out" scored_candidate_count)"
    fi
  elif [[ "$status" -ne 0 ]]; then
    note="nonzero_exit"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$tool_name" "$tool_path" "$(tool_version "$tool_name" "$tool_path")" "$command_text" "$MAX_DEPTH" \
    "$target" "$(stat -c '%s' "$target")" "$(sha256_of "$target")" "$run" "$wall" "$maxrss" \
    "$status" "$output_bytes" "$output_lines" "$raw" "$exact" "$semantic" "$unknown" "$scored" "$note" \
    >>"$RESULTS"

  if [[ "$tool_name" == "x64lens" && "$status" -ne 0 ]]; then
    echo "error: x64lens benchmark command failed for $target run $run" >&2
    echo "--- stderr ---" >&2
    cat "$err" >&2
    exit "$status"
  fi
}

available_baselines=()
command -v ROPgadget >/dev/null 2>&1 && available_baselines+=("ROPgadget")
command -v ropper >/dev/null 2>&1 && available_baselines+=("ropper")
command -v ropr >/dev/null 2>&1 && available_baselines+=("ropr")

if [[ "$REQUIRE_BASELINES" == "1" && ${#available_baselines[@]} -eq 0 ]]; then
  echo "error: REQUIRE_BASELINES=1 but no optional baseline tools were found" >&2
  exit 127
fi

{
  echo "benchmark_type=baseline-smoke"
  echo "status=development-smoke-not-publication-claim"
  echo "timestamp_utc=$STAMP"
  echo "runs=$RUNS"
  echo "max_depth=$MAX_DEPTH"
  echo "x64lens_path=$TOOL"
  echo "x64lens_version=$(tool_version x64lens "$TOOL")"
  echo "corpus_manifest=tests/corpus-manifest.json"
  echo "corpus_manifest_sha256=$(manifest_hash)"
  echo "uname=$(uname -a)"
  echo "nasm_version=$(nasm -v 2>/dev/null || true)"
  echo "ld_version=$(ld --version 2>/dev/null | head -n 1 || true)"
  echo "gcc_version=$(gcc --version 2>/dev/null | head -n 1 || true)"
  echo "python_version=$(python3 --version 2>/dev/null || true)"
  if [[ ${#available_baselines[@]} -eq 0 ]]; then
    echo "baseline_tools_available=none"
  else
    echo "baseline_tools_available=${available_baselines[*]}"
  fi
  command -v ROPgadget >/dev/null 2>&1 && echo "ROPgadget_version=$(tool_version ROPgadget ROPgadget)" || echo "ROPgadget_version=missing"
  command -v ropper >/dev/null 2>&1 && echo "ropper_version=$(tool_version ropper ropper)" || echo "ropper_version=missing"
  command -v ropr >/dev/null 2>&1 && echo "ropr_version=$(tool_version ropr ropr)" || echo "ropr_version=missing"
} >"$META"

printf 'tool\ttool_path\ttool_version\tcommand\tmax_depth\ttarget\ttarget_size_bytes\ttarget_sha256\trun\twall_s\tmaxrss_kb\texit_code\toutput_bytes\toutput_lines\traw_candidate_count\texact_pattern_count\tsemantic_candidate_count\tunknown_candidate_count\tscored_candidate_count\tnote\n' >"$RESULTS"

for target in "${TARGETS[@]}"; do
  if [[ ! -f "$target" ]]; then
    echo "warning: skipping non-file target: $target" >&2
    continue
  fi

  for run in $(seq 1 "$RUNS"); do
    run_timed \
      "x64lens" "$TOOL" "gadgets --format json --max-depth $MAX_DEPTH <target>" \
      "$target" "$run" \
      "$TOOL" gadgets --format json --max-depth "$MAX_DEPTH" "$target"

    if command -v ROPgadget >/dev/null 2>&1; then
      run_timed "ROPgadget" "$(command -v ROPgadget)" "ROPgadget --binary <target>" \
        "$target" "$run" ROPgadget --binary "$target"
    fi

    if command -v ropper >/dev/null 2>&1; then
      run_timed "ropper" "$(command -v ropper)" "ropper --file <target>" \
        "$target" "$run" ropper --file "$target"
    fi

    if command -v ropr >/dev/null 2>&1; then
      run_timed "ropr" "$(command -v ropr)" "ropr <target>" \
        "$target" "$run" ropr "$target"
    fi
  done
done

cat <<MSG
baseline-smoke benchmark complete
  results: $RESULTS
  metadata: $META
  runs: $RUNS
  max_depth: $MAX_DEPTH
  optional baselines: ${available_baselines[*]:-none}
MSG
