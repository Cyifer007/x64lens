#!/usr/bin/env bash
# validate-gadget-fixture.sh
#
# Purpose:
#   Validate the hand-authored gadget fixture against the current scanner,
#   exact-pattern, semantic-classifier, and scoring pipeline. This is a
#   correctness smoke test, not a performance benchmark.
#
# Usage:
#   tools/validate-gadget-fixture.sh [x64lens-binary] [fixture]
#
# Contract notes:
#   - The fixture is intentionally tiny and deterministic.
#   - This script validates report identity/completeness, scanner counts, exact
#     pattern labels, semantic classifier facts, and scores for the fixture.
#   - This script exists to catch scanner/classifier regressions before
#     benchmarking.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="${1:-$ROOT/build/x64lens}"
FIXTURE="${2:-$ROOT/tests/bin/gadgets}"
TMPDIR="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPDIR/x64lens-gadget-fixture.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

if [[ ! -x "$TOOL" ]]; then
  echo "error: x64lens binary is not executable: $TOOL" >&2
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "error: fixture does not exist: $FIXTURE" >&2
  echo "hint: run 'make samples' first" >&2
  exit 1
fi

if ! command -v objdump >/dev/null 2>&1; then
  echo "error: objdump is required for fixture validation" >&2
  exit 127
fi

DEFAULT_OUT="$WORK/gadgets-default.txt"
DEPTH4_OUT="$WORK/gadgets-depth4.txt"
OBJDUMP_OUT="$WORK/objdump.txt"

"$TOOL" gadgets "$FIXTURE" >"$DEFAULT_OUT"
"$TOOL" gadgets --max-depth 4 "$FIXTURE" >"$DEPTH4_OUT"
objdump -d -Mintel "$FIXTURE" >"$OBJDUMP_OUT"

require_line() {
  local pattern="$1"
  local file="$2"
  local description="$3"
  if ! grep -Eq "$pattern" "$file"; then
    echo "error: missing expected signal: $description" >&2
    echo "pattern: $pattern" >&2
    echo "file: $file" >&2
    echo "--- file excerpt ---" >&2
    sed -n '1,120p' "$file" >&2
    exit 1
  fi
}

# Validate objdump's view of the fixture first. This ensures the ground truth
# has not drifted before checking x64lens output.
require_line '401000:.*pop[[:space:]]+rdi' "$OBJDUMP_OUT" 'objdump pop rdi fixture instruction'
require_line '401001:.*ret' "$OBJDUMP_OUT" 'objdump ret after pop rdi'
require_line '401014:.*syscall' "$OBJDUMP_OUT" 'objdump syscall fixture instruction'
require_line '401017:.*ret[[:space:]]+0x10' "$OBJDUMP_OUT" 'objdump ret imm16 fixture instruction'

# Validate default-depth summary and known raw windows. These counts are tied to
# the current hand-authored tests/toy-src/gadgets.S fixture and the Sprint 3
# Phase A scanner policy.
require_line 'Report type: analysis' "$DEFAULT_OUT" 'analysis report type'
require_line 'Command: gadgets' "$DEFAULT_OUT" 'gadgets command identity'
require_line 'Complete: yes' "$DEFAULT_OUT" 'complete bounded analysis'
require_line 'Candidate truncated: no' "$DEFAULT_OUT" 'candidate truncation state'
require_line 'Candidate dropped count: 0x0000000000000000' "$DEFAULT_OUT" 'candidate dropped count'
require_line 'Regions scanned: 0x0000000000000001' "$DEFAULT_OUT" 'completed executable region count'
require_line 'Regions total: 0x0000000000000001' "$DEFAULT_OUT" 'total executable region count'
require_line 'Max depth: 0x0000000000000008' "$DEFAULT_OUT" 'default max depth'
require_line 'Candidate capacity: 0x0000000000001000' "$DEFAULT_OUT" 'default candidate capacity'
require_line 'Candidate count: 0x000000000000000b' "$DEFAULT_OUT" 'default candidate count'
require_line 'ret count: 0x000000000000000a' "$DEFAULT_OUT" 'default ret count'
require_line 'ret imm16 count: 0x0000000000000001' "$DEFAULT_OUT" 'default ret imm16 count'
require_line 'Exact pattern count: 0x000000000000000b' "$DEFAULT_OUT" 'default exact pattern count'
require_line 'Semantic primitive count: 0x000000000000000b' "$DEFAULT_OUT" 'default semantic primitive count'
require_line 'Scored candidate count: 0x000000000000000b' "$DEFAULT_OUT" 'default scored candidate count'
require_line 'unknown_candidate count: 0x0000000000000000' "$DEFAULT_OUT" 'default unknown semantic count'
require_line 'arg_control count: 0x0000000000000006' "$DEFAULT_OUT" 'arg_control summary count'
require_line 'syscall_num_control count: 0x0000000000000001' "$DEFAULT_OUT" 'syscall number control summary count'
require_line 'syscall_trigger count: 0x0000000000000001' "$DEFAULT_OUT" 'syscall trigger summary count'
require_line 'stack_pivot count: 0x0000000000000002' "$DEFAULT_OUT" 'stack pivot summary count'
require_line 'alignment count: 0x0000000000000001' "$DEFAULT_OUT" 'alignment summary count'
require_line 'Register coverage: rax\|rcx\|rdx\|rsi\|rdi\|rsp\|r8\|r9' "$DEFAULT_OUT" 'controlled register coverage'
require_line 'pattern: pop rdi; ret, semantic: arg_control, regs: rdi, stack delta: 0x0000000000000010, score: 90, bytes: 5f c3' "$DEFAULT_OUT" 'pop rdi; ret semantic classification and score'
require_line 'pattern: pop rsi; ret, semantic: arg_control, regs: rsi, stack delta: 0x0000000000000010, score: 90' "$DEFAULT_OUT" 'pop rsi; ret semantic classification and score'
require_line 'pattern: pop rdx; ret, semantic: arg_control, regs: rdx, stack delta: 0x0000000000000010, score: 90' "$DEFAULT_OUT" 'pop rdx; ret semantic classification and score'
require_line 'pattern: pop rcx; ret, semantic: arg_control, regs: rcx, stack delta: 0x0000000000000010, score: 90' "$DEFAULT_OUT" 'pop rcx; ret semantic classification and score'
require_line 'pattern: pop r8; ret, semantic: arg_control, regs: r8, stack delta: 0x0000000000000010, score: 90' "$DEFAULT_OUT" 'pop r8; ret semantic classification and score'
require_line 'pattern: pop r9; ret, semantic: arg_control, regs: r9, stack delta: 0x0000000000000010, score: 90' "$DEFAULT_OUT" 'pop r9; ret semantic classification and score'
require_line 'pattern: pop rax; ret, semantic: syscall_num_control, regs: rax, stack delta: 0x0000000000000010, score: 85' "$DEFAULT_OUT" 'pop rax; ret semantic classification and score'
require_line 'pattern: pop rsp; ret, semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 70' "$DEFAULT_OUT" 'pop rsp; ret semantic classification and score'
require_line 'pattern: leave; ret, semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 75' "$DEFAULT_OUT" 'leave; ret semantic classification and score'
require_line 'pattern: syscall; ret, semantic: syscall_trigger, regs: none, stack delta: 0x0000000000000008, score: 85, bytes: .*0f 05 c3' "$DEFAULT_OUT" 'syscall; ret semantic classification and score'
require_line 'pattern: ret imm16, semantic: alignment, regs: none, stack delta: 0x0000000000000018, score: 40, bytes: .*c2 10 00' "$DEFAULT_OUT" 'ret imm16 semantic classification and score'

# Validate custom-depth summary. A max depth of 4 means up to four bytes before
# the terminator, so the total byte-window length may be max-depth + terminator
# length. This distinction is documented because `ret imm16` is three bytes.
require_line 'Max depth: 0x0000000000000004' "$DEPTH4_OUT" 'custom max depth'
require_line 'Candidate count: 0x000000000000000b' "$DEPTH4_OUT" 'custom-depth candidate count'
require_line 'Exact pattern count: 0x000000000000000b' "$DEPTH4_OUT" 'custom-depth exact pattern count'
require_line 'Semantic primitive count: 0x000000000000000b' "$DEPTH4_OUT" 'custom-depth semantic primitive count'
require_line 'Scored candidate count: 0x000000000000000b' "$DEPTH4_OUT" 'custom-depth scored candidate count'
require_line 'pattern: ret imm16' "$DEPTH4_OUT" 'custom-depth ret imm16 pattern'

cat <<MSG
validate-gadget-fixture: ok
  fixture: $FIXTURE
  x64lens: $TOOL
  default candidates: 11
  default ret count: 10
  default ret imm16 count: 1
  default exact pattern count: 11
  default semantic primitive count: 11
  default scored candidate count: 11
MSG
