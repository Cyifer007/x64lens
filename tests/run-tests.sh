#!/usr/bin/env bash
# x64lens test runner
#
# Purpose:
#   Execute the current scaffold-level regression tests. As features are
#   implemented, this script should evolve from scaffold validation into
#   real ELF parsing, mitigation detection, gadget scanning, and JSON
#   schema checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/build/x64lens"

if [[ ! -x "$BIN" ]]; then
  echo "error: $BIN not found or not executable"
  exit 1
fi

echo "[test] version"
"$BIN" version

echo "[test] help"
"$BIN" help >/dev/null

echo "[test] usage failure"
if "$BIN" >/dev/null 2>&1; then
  echo "expected bare x64lens to fail with usage"
  exit 1
fi

echo "[test] info scaffold"
if "$BIN" info "$ROOT/tests/toy-src/minimal.c" >/tmp/x64lens-info-scaffold.txt 2>&1; then
  echo "expected scaffold info command to exit unsupported until Sprint 1 implementation"
  exit 1
fi
if ! grep -q "Sprint 1 target" /tmp/x64lens-info-scaffold.txt; then
  echo "missing scaffold info output"
  cat /tmp/x64lens-info-scaffold.txt
  exit 1
fi

echo "tests: ok"
