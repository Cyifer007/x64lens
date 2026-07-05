#!/usr/bin/env bash
# x64lens test runner
#
# Purpose:
#   Execute regression tests for the current sprint. Sprint 1 verified the
#   no-libc assembly CLI, valid ELF64 metadata reporting, and safe rejection
#   of invalid target files. Sprint 2 extended coverage to program-header
#   analysis, baseline mitigation indicators, executable-region discovery,
#   and malformed program-header rejection. Sprint 3 adds raw gadget scanner
#   coverage for ret and ret-imm candidates. Sprint 4 adds semantic checks.
#   Sprint 5 adds scoring and JSON output checks. Sprint 6 adds the integrated
#   analyze checkpoint command. Sprint 7 adds exact section-entry-size rejection
#   and explicit candidate-capacity regression coverage.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/build/x64lens"
TMPROOT="${TMPDIR:-/tmp}"
TMPDIR="$(mktemp -d "$TMPROOT/x64lens-tests.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

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
"$BIN" help | grep -q "x64lens gadgets \[--format text|json\] \[--max-depth N\] <file>"
"$BIN" help | grep -q "x64lens analyze \[--format text|json\] \[--max-depth N\] <file>"

echo "[test] usage failure"
expect_exit 2 "$BIN"
expect_exit 2 "$BIN" mitigations
expect_exit 2 "$BIN" gadgets
expect_exit 2 "$BIN" gadgets --max-depth
expect_exit 2 "$BIN" gadgets --max-depth 0 "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" gadgets --max-depth 33 "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" gadgets --max-depth nope "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" gadgets --format
expect_exit 2 "$BIN" gadgets --format xml "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" gadgets --format json --max-depth 0 "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" analyze
expect_exit 2 "$BIN" analyze --max-depth
expect_exit 2 "$BIN" analyze --max-depth 0 "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" analyze --max-depth 33 "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" analyze --max-depth nope "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" analyze --format
expect_exit 2 "$BIN" analyze --format xml "$ROOT/tests/bin/gadgets"
expect_exit 2 "$BIN" analyze --format json --max-depth 0 "$ROOT/tests/bin/gadgets"

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
expect_exit 4 "$BIN" gadgets "$ROOT/tests/invalid/text.txt"
expect_exit 4 "$BIN" analyze "$ROOT/tests/invalid/text.txt"

echo "[test] truncated ELF rejection"
expect_exit 5 "$BIN" info "$ROOT/tests/invalid/truncated_elf.bin"
expect_exit 5 "$BIN" mitigations "$ROOT/tests/invalid/truncated_elf.bin"
expect_exit 5 "$BIN" gadgets "$ROOT/tests/invalid/truncated_elf.bin"
expect_exit 5 "$BIN" analyze "$ROOT/tests/invalid/truncated_elf.bin"

echo "[test] wrong architecture rejection"
expect_exit 4 "$BIN" info "$ROOT/tests/invalid/wrong_arch_elf.bin"
expect_exit 4 "$BIN" mitigations "$ROOT/tests/invalid/wrong_arch_elf.bin"
expect_exit 4 "$BIN" gadgets "$ROOT/tests/invalid/wrong_arch_elf.bin"
expect_exit 4 "$BIN" analyze "$ROOT/tests/invalid/wrong_arch_elf.bin"

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
expect_exit 5 "$BIN" gadgets "$MALFORMED_PHDR"
expect_exit 5 "$BIN" analyze "$MALFORMED_PHDR"

echo "[test] malformed table extent overflow rejection"
MALFORMED_TABLE_WRAP="$TMPDIR/x64lens-malformed-table-wrap.bin"
cp "$ROOT/tests/bin/minimal_nopie" "$MALFORMED_TABLE_WRAP"
python3 - "$MALFORMED_TABLE_WRAP" <<'PY'
import struct
import sys
path = sys.argv[1]
with open(path, "r+b") as f:
    # ELF64 e_phoff is at offset 0x20. Put the table near UINT64_MAX so
    # e_phoff + e_phentsize * e_phnum must be caught as checked arithmetic,
    # not as a wrapped pointer into the mmap.
    f.seek(0x20)
    f.write(struct.pack("<Q", 0xFFFFFFFFFFFFFFF0))
PY
expect_exit 5 "$BIN" info "$MALFORMED_TABLE_WRAP"
expect_exit 5 "$BIN" mitigations "$MALFORMED_TABLE_WRAP"
expect_exit 5 "$BIN" gadgets "$MALFORMED_TABLE_WRAP"
expect_exit 5 "$BIN" analyze "$MALFORMED_TABLE_WRAP"

MALFORMED_SECTION_WRAP="$TMPDIR/x64lens-malformed-section-wrap.bin"
cp "$ROOT/tests/bin/minimal_nopie" "$MALFORMED_SECTION_WRAP"
python3 - "$MALFORMED_SECTION_WRAP" <<'PY'
import struct
import sys
path = sys.argv[1]
with open(path, "r+b") as f:
    # ELF64 e_shoff is at offset 0x28. The seed already has a nonzero section
    # count, so moving the table near UINT64_MAX exercises checked section
    # table-end arithmetic before future SHDR iteration exists.
    f.seek(0x28)
    f.write(struct.pack("<Q", 0xFFFFFFFFFFFFFFF0))
PY
expect_exit 5 "$BIN" info "$MALFORMED_SECTION_WRAP"
expect_exit 5 "$BIN" mitigations "$MALFORMED_SECTION_WRAP"
expect_exit 5 "$BIN" gadgets "$MALFORMED_SECTION_WRAP"
expect_exit 5 "$BIN" analyze "$MALFORMED_SECTION_WRAP"

echo "[test] malformed section header entry size rejection"
MALFORMED_SHENTSIZE="$ROOT/tests/malformed/regressions/elf64-shentsize-63.bin"
expect_exit 5 "$BIN" info "$MALFORMED_SHENTSIZE"
expect_exit 5 "$BIN" mitigations "$MALFORMED_SHENTSIZE"
expect_exit 5 "$BIN" gadgets "$MALFORMED_SHENTSIZE"
expect_exit 5 "$BIN" analyze "$MALFORMED_SHENTSIZE"

echo "[test] mitigations non-PIE noexecstack"
MIT_NOPIE="$TMPDIR/x64lens-mitigations-nopie.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_nopie" >"$MIT_NOPIE"
grep -q "Mitigations:" "$MIT_NOPIE"
grep -q "PIE: disabled" "$MIT_NOPIE"
grep -q "NX stack: enabled" "$MIT_NOPIE"
grep -q "Executable regions:" "$MIT_NOPIE"
grep -q "Dynamic linking: yes" "$MIT_NOPIE"
grep -q "Bind now: no" "$MIT_NOPIE"
grep -q "Dynamic entries: 0x" "$MIT_NOPIE"
grep -q "Dynamic terminator: yes" "$MIT_NOPIE"
grep -q "Canary indicator: absent" "$MIT_NOPIE"
grep -q "Stripped indicator: not stripped" "$MIT_NOPIE"
grep -q "perms R-X" "$MIT_NOPIE"

echo "[test] mitigations PIE RELRO"
MIT_PIE="$TMPDIR/x64lens-mitigations-pie.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_pie_canary" >"$MIT_PIE"
grep -q "PIE: enabled" "$MIT_PIE"
grep -q "NX stack: enabled" "$MIT_PIE"
grep -q "RELRO: full" "$MIT_PIE"
grep -q "Dynamic linking: yes" "$MIT_PIE"
grep -q "Bind now: yes" "$MIT_PIE"
grep -q "Dynamic terminator: yes" "$MIT_PIE"
grep -q "Canary indicator: present" "$MIT_PIE"
grep -q "Stripped indicator: not stripped" "$MIT_PIE"

echo "[test] mitigations fixture section label"
MIT_GADGETS="$TMPDIR/x64lens-mitigations-gadgets.txt"
"$BIN" mitigations "$ROOT/tests/bin/gadgets" >"$MIT_GADGETS"
grep -q "section: .text" "$MIT_GADGETS"

echo "[test] mitigations executable stack"
MIT_EXECSTACK="$TMPDIR/x64lens-mitigations-execstack.txt"
"$BIN" mitigations "$ROOT/tests/bin/minimal_execstack" >"$MIT_EXECSTACK"
grep -q "NX stack: disabled" "$MIT_EXECSTACK"

echo "[test] raw gadget scanner default depth"
GADGETS_OUT="$TMPDIR/x64lens-gadgets-default.txt"
"$BIN" gadgets "$ROOT/tests/bin/gadgets" >"$GADGETS_OUT"
grep -q "Raw gadget candidates:" "$GADGETS_OUT"
grep -q "Max depth: 0x0000000000000008" "$GADGETS_OUT"
grep -q "Candidate capacity: 0x0000000000001000" "$GADGETS_OUT"
grep -q "Candidate count: 0x000000000000000b" "$GADGETS_OUT"
grep -q "ret count: 0x000000000000000a" "$GADGETS_OUT"
grep -q "ret imm16 count: 0x0000000000000001" "$GADGETS_OUT"
grep -q "Exact pattern count: 0x000000000000000b" "$GADGETS_OUT"
grep -q "Semantic primitive count: 0x000000000000000b" "$GADGETS_OUT"
grep -q "Scored candidate count: 0x000000000000000b" "$GADGETS_OUT"
grep -q "unknown_candidate count: 0x0000000000000000" "$GADGETS_OUT"
grep -q "arg_control count: 0x0000000000000006" "$GADGETS_OUT"
grep -q "syscall_num_control count: 0x0000000000000001" "$GADGETS_OUT"
grep -q "syscall_trigger count: 0x0000000000000001" "$GADGETS_OUT"
grep -q "stack_pivot count: 0x0000000000000002" "$GADGETS_OUT"
grep -q "alignment count: 0x0000000000000001" "$GADGETS_OUT"
grep -q "Register coverage: rax|rcx|rdx|rsi|rdi|rsp|r8|r9" "$GADGETS_OUT"
grep -q "section: .text" "$GADGETS_OUT"
grep -q "terminator: ret" "$GADGETS_OUT"
grep -q "terminator: ret imm16" "$GADGETS_OUT"
grep -q "pattern: pop rdi; ret" "$GADGETS_OUT"
grep -q "pattern: pop rsi; ret" "$GADGETS_OUT"
grep -q "pattern: pop rdx; ret" "$GADGETS_OUT"
grep -q "pattern: pop rcx; ret" "$GADGETS_OUT"
grep -q "pattern: pop r8; ret" "$GADGETS_OUT"
grep -q "pattern: pop r9; ret" "$GADGETS_OUT"
grep -q "pattern: pop rax; ret" "$GADGETS_OUT"
grep -q "pattern: pop rsp; ret" "$GADGETS_OUT"
grep -q "pattern: leave; ret" "$GADGETS_OUT"
grep -q "pattern: syscall; ret" "$GADGETS_OUT"
grep -q "pattern: ret imm16" "$GADGETS_OUT"
grep -q "semantic: arg_control, regs: rdi, stack delta: 0x0000000000000010, score: 90" "$GADGETS_OUT"
grep -q "semantic: arg_control, regs: rcx, stack delta: 0x0000000000000010, score: 90" "$GADGETS_OUT"
grep -q "semantic: arg_control, regs: r8, stack delta: 0x0000000000000010, score: 90" "$GADGETS_OUT"
grep -q "semantic: arg_control, regs: r9, stack delta: 0x0000000000000010, score: 90" "$GADGETS_OUT"
grep -q "semantic: syscall_num_control, regs: rax, stack delta: 0x0000000000000010, score: 85" "$GADGETS_OUT"
grep -q "semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 70" "$GADGETS_OUT"
grep -q "semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 75" "$GADGETS_OUT"
grep -q "semantic: syscall_trigger, regs: none, stack delta: 0x0000000000000008, score: 85" "$GADGETS_OUT"
grep -q "semantic: alignment, regs: none, stack delta: 0x0000000000000018, score: 40" "$GADGETS_OUT"
grep -q "bytes: 5f c3" "$GADGETS_OUT"
grep -q "c2 10 00" "$GADGETS_OUT"

echo "[test] raw gadget scanner custom max-depth"
GADGETS_DEPTH_OUT="$TMPDIR/x64lens-gadgets-depth.txt"
"$BIN" gadgets --max-depth 4 "$ROOT/tests/bin/gadgets" >"$GADGETS_DEPTH_OUT"
grep -q "Max depth: 0x0000000000000004" "$GADGETS_DEPTH_OUT"
grep -q "Candidate count: 0x000000000000000b" "$GADGETS_DEPTH_OUT"
grep -q "Exact pattern count: 0x000000000000000b" "$GADGETS_DEPTH_OUT"
grep -q "Semantic primitive count: 0x000000000000000b" "$GADGETS_DEPTH_OUT"
grep -q "Scored candidate count: 0x000000000000000b" "$GADGETS_DEPTH_OUT"
grep -q "terminator: ret" "$GADGETS_DEPTH_OUT"
grep -q "pattern: pop rdi; ret" "$GADGETS_DEPTH_OUT"


echo "[test] gadget JSON output"
GADGETS_JSON="$TMPDIR/x64lens-gadgets.json"
"$BIN" gadgets --format json --max-depth 4 "$ROOT/tests/bin/gadgets" >"$GADGETS_JSON"
python3 -m json.tool "$GADGETS_JSON" >/dev/null
python3 "$ROOT/tools/validate-json-report.py" --mode fixture "$GADGETS_JSON" >/dev/null
python3 - "$GADGETS_JSON" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    report = json.load(f)
sections = {g.get("section") for g in report["gadgets"]}
assert sections == {".text"}, sections
PY

"$BIN" gadgets --max-depth 4 --format json "$ROOT/tests/bin/gadgets" >"$TMPDIR/x64lens-gadgets-json-order2.json"
python3 "$ROOT/tools/validate-json-report.py" --mode fixture "$TMPDIR/x64lens-gadgets-json-order2.json" >/dev/null


echo "[test] analyze integrated text output"
ANALYZE_OUT="$TMPDIR/x64lens-analyze.txt"
"$BIN" analyze --max-depth 4 "$ROOT/tests/bin/gadgets" >"$ANALYZE_OUT"
grep -q "Format:" "$ANALYZE_OUT"
grep -q "Mitigations:" "$ANALYZE_OUT"
grep -q "Raw gadget candidates:" "$ANALYZE_OUT"
grep -q "Bind now: not applicable" "$ANALYZE_OUT"
grep -q "Dynamic entries: 0x0000000000000000" "$ANALYZE_OUT"
grep -q "Dynamic terminator: not applicable" "$ANALYZE_OUT"
grep -q "Canary indicator: unknown" "$ANALYZE_OUT"
grep -q "Stripped indicator: not stripped" "$ANALYZE_OUT"
grep -q "section: .text" "$ANALYZE_OUT"
grep -q "Candidate count: 0x000000000000000b" "$ANALYZE_OUT"
grep -q "Semantic primitive count: 0x000000000000000b" "$ANALYZE_OUT"
grep -q "Scored candidate count: 0x000000000000000b" "$ANALYZE_OUT"
grep -q "Register coverage: rax|rcx|rdx|rsi|rdi|rsp|r8|r9" "$ANALYZE_OUT"
test "$(grep -c '^x64lens ' "$ANALYZE_OUT")" -eq 1
test "$(grep -c '^Target: ' "$ANALYZE_OUT")" -eq 1


echo "[test] analyze JSON output"
ANALYZE_JSON="$TMPDIR/x64lens-analyze.json"
"$BIN" analyze --format json --max-depth 4 "$ROOT/tests/bin/gadgets" >"$ANALYZE_JSON"
python3 -m json.tool "$ANALYZE_JSON" >/dev/null
python3 "$ROOT/tools/validate-json-report.py" --mode fixture "$ANALYZE_JSON" >/dev/null
python3 - "$ANALYZE_JSON" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    report = json.load(f)
sections = {g.get("section") for g in report["gadgets"]}
assert sections == {".text"}, sections
PY

"$BIN" analyze --max-depth 4 --format json "$ROOT/tests/bin/gadgets" >"$TMPDIR/x64lens-analyze-json-order2.json"
python3 "$ROOT/tools/validate-json-report.py" --mode fixture "$TMPDIR/x64lens-analyze-json-order2.json" >/dev/null

echo "[test] candidate capacity rejection"
expect_exit 6 "$BIN" gadgets --max-depth 4 "$ROOT/tests/bin/gadgets_capacity"
expect_exit 6 "$BIN" gadgets --format json --max-depth 4 "$ROOT/tests/bin/gadgets_capacity"
expect_exit 6 "$BIN" analyze --max-depth 4 "$ROOT/tests/bin/gadgets_capacity"
expect_exit 6 "$BIN" analyze --format json --max-depth 4 "$ROOT/tests/bin/gadgets_capacity"
grep -qx "error: unsupported binary feature" "$TMPDIR/x64lens-test-err.txt"

echo "tests: ok"
