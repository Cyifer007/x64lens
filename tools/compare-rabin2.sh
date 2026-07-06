#!/usr/bin/env bash
# Compare x64lens mitigation output against rabin2 metadata when rabin2 is available.
set -euo pipefail

usage() {
  echo "usage: $0 <target-file> [x64lens-binary]" >&2
  echo "   or: $0 <x64lens-binary> <target-file>" >&2
}

looks_like_x64lens_path() {
  local candidate="$1"
  [[ -x "$candidate" ]] || return 1
  [[ "$(basename -- "$candidate")" == "x64lens" ]]
}

is_x64lens_binary() {
  local candidate="$1"
  [[ -x "$candidate" ]] || return 1
  local first_line
  first_line="$("$candidate" version 2>/dev/null | sed -n '1p' || true)"
  [[ "$first_line" == x64lens\ * ]]
}
resolve_args() {
  if [[ $# -eq 1 ]]; then
    TARGET="$1"
    TOOL="./build/x64lens"
  elif [[ $# -eq 2 ]]; then
    if [[ "$1" -ef "$2" ]]; then
      echo "error: analyzer and target must be different files" >&2
      usage
      exit 2
    elif looks_like_x64lens_path "$1"; then
      TOOL="$1"
      TARGET="$2"
    elif looks_like_x64lens_path "$2"; then
      TARGET="$1"
      TOOL="$2"
    else
      # Fall back to the documented order for renamed local analyzer builds.
      # Only the resolved TOOL is executed for version validation; the target is
      # never executed during argument inference.
      TARGET="$1"
      TOOL="$2"
    fi
  else
    usage
    exit 2
  fi
}

resolve_args "$@"

command -v rabin2 >/dev/null 2>&1 || { echo "error: rabin2 not found"; exit 127; }
if ! is_x64lens_binary "$TOOL"; then
  echo "error: x64lens binary is not executable or does not report an x64lens version: $TOOL" >&2
  exit 1
fi
if [[ ! -f "$TARGET" ]]; then
  echo "error: target file does not exist: $TARGET" >&2
  exit 1
fi
if [[ "$TARGET" -ef "$TOOL" ]]; then
  echo "error: analyzer and target resolve to the same file: $TARGET" >&2
  exit 2
fi

printf 'compare-rabin2: tool=%s target=%s\n' "$TOOL" "$TARGET"

printf '\n== x64lens mitigations ==\n'
"$TOOL" mitigations "$TARGET"

printf '\n== rabin2 -I ==\n'
rabin2 -I "$TARGET"
