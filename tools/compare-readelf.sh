#!/usr/bin/env bash
# Compare x64lens parser output against readelf manually.
#
# Purpose:
#   Provide a repeatable Sprint 2 sanity-check workflow for ELF header and
#   program-header metadata. This script is intentionally comparison-oriented,
#   not a benchmark. It helps reviewers line up x64lens output with the
#   canonical binutils view from readelf.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file> [x64lens-binary]"
  exit 2
fi

TARGET="$1"
TOOL="${2:-./build/x64lens}"

command -v readelf >/dev/null 2>&1 || { echo "error: readelf not found"; exit 127; }
if [[ ! -x "$TOOL" ]]; then
  echo "error: x64lens binary is not executable: $TOOL"
  exit 1
fi

printf '\n== x64lens info ==\n'
"$TOOL" info "$TARGET"

printf '\n== readelf -h ==\n'
readelf -h "$TARGET"

printf '\n== x64lens mitigations ==\n'
"$TOOL" mitigations "$TARGET"

printf '\n== readelf -l ==\n'
readelf -l "$TARGET" | sed -n '1,220p'
