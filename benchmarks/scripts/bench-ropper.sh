#!/usr/bin/env bash
# Benchmark Ropper for comparison against x64lens.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file>"
  exit 2
fi

TARGET="$1"
RUNS="${RUNS:-5}"

command -v ropper >/dev/null 2>&1 || { echo "error: ropper not found"; exit 127; }

for i in $(seq 1 "$RUNS"); do
  /usr/bin/time -f "run=$i wall=%e maxrss_kb=%M exit=%x" ropper --file "$TARGET" >/dev/null
done
