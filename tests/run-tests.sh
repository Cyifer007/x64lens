#!/usr/bin/env bash
# x64lens test runner
#
# Purpose:
#   Execute regression tests for the current sprint. Sprint 1 verified the
#   no-libc assembly CLI, valid ELF64 metadata reporting, and safe rejection
#   of invalid target files. Sprint 2 extends coverage to program-header
#   analysis, baseline mitigation indicators, executable-region discovery,
#   and malformed program-header rejection.
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
  "$@" >"$TMPDIR/x64lens-test-out.txt" 2>"$TMPDIR/x64lens-test-err.txt"
  local status=$?
  set -e
  if [[ "$status" -ne "$expected" ]]; then
    echo "expected exit $expected but got $status for: $*"
    echo "--- stdout ---"
    cat "$TMPDIR/x64lens-test-out.txt"
    echo "--- stderr ---"
    cat "$TMPDIR/x64lens-test-err.txt"
    exit 1
  fi
}

require_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required for malformed ELF fixture generation"
    exit 1
  fi
}

echo "[test] version"
"$BIN" version | grep -q "x64lens 0.1.0-dev schema 0.1.0"

echo "[test] help"
"$BIN" help | grep -q "x64lens info <file>"
"$BIN" help | grep -q "x64lens mitigations <file>"

echo "[test] usage failure"
expect_exit 2 "$BIN"
expect_exit 2 "$BIN" mitigations

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
  "$BIN" info /bin/ls >"$TMPDIR/x64lens-info-bin-ls.txt"
  grep -q "Machine: x86_64" "$TMPDIR/x64lens-info-bin-ls.txt"
fi

echo "[test] non-ELF rejection"
expect_exit 4 "$BIN" info "$ROOT/tests/invalid/text.txt"
expect_exit 4 "$BIN" mitigations "$ROOT/tests/invalid/text.txt"

echo "[test] truncated ELF rejection"
expect_exit 5 "$BIN" info "$ROOT/tests/invalid/truncated_elf.bin"
expect_exit 5 "$BIN" mitigations "$ROOT/tests/invalid/truncated_elf.bin"

echo "[test] wrong architecture rejection"
expect_exit 4 "$BIN" info "$ROOT/tests/invalid/wrong_arch_elf.bin"
expect_exit 4 "$BIN" mitigations "$ROOT/tests/invalid/wrong_arch_elf.bin"

echo "[test] malformed program header rejection"
require_python3
MALFORMED_PHDR="$TMPDIR/x64lens-malformed-phdr.bin"
cp "$ROOT/tests/bin/minimal_nopie" "$MALFORMED_PHDR"
python3 - "$MALFORMED_PHDR" <<'PY'
import os
import struct
import sys
path = sys.argv[1]
size = os.path.getsize(path)
with open(path, "r+b") as f:
    # ELF64 e_phoff is at offset 0x20. Point it beyond EOF while preserving
    # the rest of the ELF identity so parser range checks must catch it.
    f.seek(0x20)
    f.write(struct.pack("<Q", size + 0x1000))
PY
expect_exit 5 "$BIN" info "$MALFORMED_PHDR"
expect_exit 5 "$BIN" mitigations "$MALFORMED_PHDR"

echo "[test] mitigations non-PIE noexecstack"
MIT_NOPIE="$TMPDIR/x64lens-mitigations-nopie.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_nopie" >"$MIT_NOPIE"
grep -q "Mitigations:" "$MIT_NOPIE"
grep -q "PIE: disabled" "$MIT_NOPIE"
grep -q "NX stack: enabled" "$MIT_NOPIE"
grep -q "Executable regions:" "$MIT_NOPIE"
grep -q "perms R-X" "$MIT_NOPIE"

echo "[test] mitigations PIE RELRO"
MIT_PIE="$TMPDIR/x64lens-mitigations-pie.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_pie_canary" >"$MIT_PIE"
grep -q "PIE: enabled" "$MIT_PIE"
grep -q "NX stack: enabled" "$MIT_PIE"
grep -q "RELRO: present" "$MIT_PIE"

echo "[test] mitigations executable stack"
MIT_EXECSTACK="$TMPDIR/x64lens-mitigations-execstack.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_execstack" >"$MIT_EXECSTACK"
grep -q "NX stack: disabled" "$MIT_EXECSTACK"

echo "tests: ok"
