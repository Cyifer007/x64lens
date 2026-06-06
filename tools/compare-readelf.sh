#!/usr/bin/env bash
# Compare x64lens parser output against readelf manually.
# Sprint 1 uses this for sanity checking ELF header and program header parsing.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file>"
  exit 2
fi

TARGET="$1"
command -v readelf >/dev/null 2>&1 || { echo "error: readelf not found"; exit 127; }

readelf -h "$TARGET"
readelf -l "$TARGET" | sed -n '1,160p'
