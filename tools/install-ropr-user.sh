#!/usr/bin/env bash
# install-ropr-user.sh
#
# Purpose:
#   Install the optional ropr baseline comparator through cargo when the local
#   Cargo toolchain is new enough. Ubuntu 24.04's apt-provided Cargo can lag
#   behind crates that require newer Rust editions, so this script fails with a
#   clear rustup-based remediation path instead of producing a long compiler
#   error during onboarding.
set -euo pipefail

ROPR_MIN_CARGO="${ROPR_MIN_CARGO:-1.85.0}"

version_ge() {
  local actual="$1"
  local required="$2"
  [[ "$(printf '%s\n%s\n' "$required" "$actual" | sort -V | head -n 1)" == "$required" ]]
}

print_ropr_hint() {
  cat >&2 <<'EOF_HINT'
ropr install requires a current Rust/Cargo toolchain. Ubuntu 24.04's apt cargo
may be too old for crates that use the Rust 2024 edition.

Recommended user-local setup:
  make install-rustup-user
  . "$HOME/.cargo/env"
  make install-ropr-user

Manual equivalent:
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
  . "$HOME/.cargo/env"
  rustup install stable
  rustup default stable
  cargo install ropr
EOF_HINT
}

if command -v ropr >/dev/null 2>&1; then
  echo "install-ropr-user: ropr already available at $(command -v ropr)"
  exit 0
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "install-ropr-user: cargo not found" >&2
  print_ropr_hint
  exit 127
fi

cargo_version="$(cargo --version 2>/dev/null | awk '{print $2}')"
if [[ -z "$cargo_version" ]]; then
  echo "install-ropr-user: unable to parse cargo version" >&2
  print_ropr_hint
  exit 127
fi

if ! version_ge "$cargo_version" "$ROPR_MIN_CARGO"; then
  echo "install-ropr-user: cargo $cargo_version is older than required $ROPR_MIN_CARGO" >&2
  print_ropr_hint
  exit 127
fi

cargo install ropr
