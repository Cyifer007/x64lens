#!/usr/bin/env bash
# Benchmark x64lens.
#
# Purpose:
#   Provide a small development wrapper that records wall-clock time, max RSS,
#   and exit code. This wrapper now benchmarks a real target-analyzing workload
#   by default; use X64LENS_BENCH_COMMAND=version only when intentionally
#   measuring startup/version overhead.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <x64lens-binary> <target-file>"
  exit 2
fi

TOOL="$1"
TARGET="$2"
RUNS="${RUNS:-5}"
MAX_DEPTH="${MAX_DEPTH:-4}"
COMMAND="${X64LENS_BENCH_COMMAND:-gadgets-json}"

require_positive_int() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || [[ "$value" -lt 1 ]]; then
    echo "error: $name must be a positive integer, got: $value" >&2
    exit 2
  fi
}

if [[ ! -x "$TOOL" ]]; then
  echo "error: tool is not executable: $TOOL"
  exit 1
fi

if [[ ! -e "$TARGET" ]]; then
  echo "error: target does not exist: $TARGET"
  exit 1
fi

if ! command -v /usr/bin/time >/dev/null 2>&1; then
  echo "error: /usr/bin/time is required for benchmark measurements" >&2
  exit 127
fi

require_positive_int RUNS "$RUNS"
require_positive_int MAX_DEPTH "$MAX_DEPTH"
if [[ "$MAX_DEPTH" -gt 32 ]]; then
  echo "error: MAX_DEPTH must be <= 32, got: $MAX_DEPTH" >&2
  exit 2
fi

case "$COMMAND" in
  gadgets|gadgets-json)
    command_label="gadgets --format json --max-depth $MAX_DEPTH <target>"
    cmd=("$TOOL" gadgets --format json --max-depth "$MAX_DEPTH" "$TARGET")
    ;;
  analyze|analyze-json)
    command_label="analyze --format json --max-depth $MAX_DEPTH <target>"
    cmd=("$TOOL" analyze --format json --max-depth "$MAX_DEPTH" "$TARGET")
    ;;
  version)
    command_label="version"
    cmd=("$TOOL" version)
    ;;
  *)
    echo "error: unsupported X64LENS_BENCH_COMMAND: $COMMAND" >&2
    echo "supported: gadgets-json, analyze-json, version" >&2
    exit 2
    ;;
esac

echo "tool=x64lens"
echo "tool_path=$TOOL"
echo "target=$TARGET"
echo "runs=$RUNS"
echo "max_depth=$MAX_DEPTH"
echo "command=$command_label"

for i in $(seq 1 "$RUNS"); do
  /usr/bin/time -f "run=$i wall=%e maxrss_kb=%M exit=%x" "${cmd[@]}" >/dev/null
done
