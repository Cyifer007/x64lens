#!/usr/bin/env bash
# Benchmark x64lens.
#
# Purpose:
#   Provide a stable wrapper that records wall-clock time, max RSS, and
#   exit code in a format that can later be summarized for the paper.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <x64lens-binary> <target-file>"
  exit 2
fi

TOOL="$1"
TARGET="$2"
RUNS="${RUNS:-5}"
COMMAND="${X64LENS_BENCH_COMMAND:-version}"

if [[ ! -x "$TOOL" ]]; then
  echo "error: tool is not executable: $TOOL"
  exit 1
fi

if [[ ! -e "$TARGET" ]]; then
  echo "error: target does not exist: $TARGET"
  exit 1
fi

echo "tool=x64lens"
echo "tool_path=$TOOL"
echo "target=$TARGET"
echo "runs=$RUNS"
echo "command=$COMMAND"

for i in $(seq 1 "$RUNS"); do
  /usr/bin/time -f "run=$i wall=%e maxrss_kb=%M exit=%x" "$TOOL" "$COMMAND" "$TARGET" >/dev/null
done
