#!/usr/bin/env bash
# x64lens test runner
#
# Purpose:
#   Execute Sprint 1 regression tests. These tests verify the current
#   no-libc assembly CLI, valid ELF64 metadata reporting, and safe rejection
#   of invalid target files. Later sprints should extend this runner with
#   mitigation detection, gadget scanning, JSON schema checks, and benchmark
#   smoke tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/build/x64lens"
TMPDIR="${TMPDIR:-/tmp}"

if [[ ! -x "$BIN" ]]; then
  echo "error: $BIN not found or not executable"
  exit 1
fi

expect_exit() {
  local expected="$1"
  shift
  set +e
  "$@" >/tmp/x64lens-test-out.txt 2>/tmp/x64lens-test-err.txt
  local status=$?
  set -e
  if [[ "$status" -ne "$expected" ]]; then
    echo "expected exit $expected but got $status for: $*"
    echo "--- stdout ---"
    cat /tmp/x64lens-test-out.txt
    echo "--- stderr ---"
    cat /tmp/x64lens-test-err.txt
    exit 1
  fi
}

echo "[test] version"
"$BIN" version | grep -q "x64lens 0.1.0-dev schema 0.1.0"

echo "[test] help"
"$BIN" help | grep -q "x64lens info <file>"

echo "[test] usage failure"
expect_exit 2 "$BIN"

echo "[test] valid ELF64 info"
INFO_OUT="$TMPDIR/x64lens-info-valid.txt"
"$BIN" info "$ROOT/tests/bin/minimal_nopie" >"$INFO_OUT"
grep -q "Format:" "$INFO_OUT"
grep -q "Type: ELF64" "$INFO_OUT"
grep -q "Machine: x86_64" "$INFO_OUT"
grep -q "Program header offset:" "$INFO_OUT"
grep -q "Section header offset:" "$INFO_OUT"

if [[ -x /bin/ls ]]; then
  echo "[test] system ELF64 info"
  "$BIN" info /bin/ls >/tmp/x64lens-info-bin-ls.txt
  grep -q "Machine: x86_64" /tmp/x64lens-info-bin-ls.txt
fi

echo "[test] non-ELF rejection"
expect_exit 4 "$BIN" info "$ROOT/tests/invalid/text.txt"

echo "[test] truncated ELF rejection"
expect_exit 5 "$BIN" info "$ROOT/tests/invalid/truncated_elf.bin"

echo "[test] wrong architecture rejection"
expect_exit 4 "$BIN" info "$ROOT/tests/invalid/wrong_arch_elf.bin"

echo "tests: ok"
