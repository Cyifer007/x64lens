#!/usr/bin/env bash
# check-dev-tools.sh
#
# Purpose:
#   Validate that the local development environment has the tools required for
#   building, testing, validating, and benchmarking x64lens. This script is a
#   diagnostic guardrail only. It does not install packages unless the caller
#   explicitly runs a separate installation target.
#
# Modes:
#   --build       Required to assemble and link x64lens.
#   --samples     Required to build the controlled toy corpus.
#   --dev         Required for the normal local validation suite.
#   --baselines   Optional baseline gadget tools; warnings by default.
#   --all         Dev tools plus optional baseline tools.
#   --doctor      Human-readable full environment report.
set -euo pipefail

MODE="${1:---dev}"
REQUIRE_BASELINES="${REQUIRE_BASELINES:-0}"

missing_required=0
missing_optional=0
baseline_found=0

have_command() {
  command -v "$1" >/dev/null 2>&1
}

check_cmd() {
  local name="$1"
  local desc="$2"
  if have_command "$name"; then
    printf 'ok: %-18s %s\n' "$name" "$desc"
  else
    printf 'missing: %-13s %s\n' "$name" "$desc" >&2
    missing_required=1
  fi
}

check_path() {
  local path="$1"
  local desc="$2"
  if [[ -x "$path" ]]; then
    printf 'ok: %-18s %s\n' "$path" "$desc"
  else
    printf 'missing: %-13s %s\n' "$path" "$desc" >&2
    missing_required=1
  fi
}

check_optional_cmd() {
  local name="$1"
  local desc="$2"
  if have_command "$name"; then
    printf 'ok: %-18s %s\n' "$name" "$desc"
  else
    printf 'optional-missing: %-5s %s\n' "$name" "$desc" >&2
    missing_optional=1
  fi
}

check_baseline_tool() {
  local name="$1"
  local desc="$2"
  if have_command "$name"; then
    printf 'ok: %-18s %s\n' "$name" "$desc"
    baseline_found=1
  else
    printf 'optional-missing: %-5s %s\n' "$name" "$desc" >&2
    missing_optional=1
  fi
}

print_install_hint() {
  cat >&2 <<'EOF'

Ubuntu 24.04 development dependency install:
  sudo apt update
  sudo apt install -y nasm binutils gcc gdb make python3 python3-venv python3-pip pipx time git curl ca-certificates unzip zip cargo

Optional baseline gadget tools:
  pipx ensurepath
  pipx install ROPGadget
  pipx install ropper
  cargo install ropr

After installing cargo tools, make sure this is in PATH:
  export PATH="$HOME/.cargo/bin:$PATH"
EOF
}

check_build() {
  check_cmd nasm "NASM assembler for ELF64 objects"
  check_cmd ld "GNU linker from binutils"
}

check_samples() {
  check_cmd gcc "C compiler for controlled toy binaries"
  check_cmd make "build orchestration"
}

check_dev() {
  check_build
  check_samples
  check_cmd python3 "JSON validation and malformed fixture generation"
  check_cmd readelf "ELF comparison and manual validation helper"
  check_cmd objdump "fixture disassembly comparison helper"
  check_path /usr/bin/time "GNU time for benchmark wall/RSS measurements"
  check_cmd git "source control and reproducibility metadata"
  check_cmd curl "retrieving external tooling or documentation when needed"
  check_cmd unzip "patch/context bundle extraction"
  check_cmd zip "patch/context bundle creation"
}

check_baselines() {
  check_baseline_tool ROPgadget "optional ROPgadget baseline comparator"
  check_baseline_tool ropper "optional Ropper baseline comparator"
  check_baseline_tool ropr "optional ropr baseline comparator"
  check_optional_cmd pipx "recommended installer for Python CLI baselines"
  check_optional_cmd cargo "Rust installer/build tool for ropr"
}

case "$MODE" in
  --build)
    check_build
    ;;
  --samples)
    check_samples
    ;;
  --dev)
    check_dev
    ;;
  --baselines)
    check_baselines
    ;;
  --all)
    check_dev
    check_baselines
    ;;
  --doctor)
    echo "x64lens development environment report"
    echo
    echo "[required development tools]"
    check_dev || true
    echo
    echo "[optional baseline tools]"
    check_baselines || true
    echo
    echo "[docker]"
    if have_command docker && docker info >/dev/null 2>&1; then
      echo "ok: docker             Docker is installed and reachable"
    elif have_command docker; then
      echo "optional-missing: docker Docker command exists but daemon is not reachable" >&2
      missing_optional=1
    else
      echo "optional-missing: docker Docker is not installed or not in PATH" >&2
      missing_optional=1
    fi
    ;;
  *)
    echo "usage: $0 [--build|--samples|--dev|--baselines|--all|--doctor]" >&2
    exit 2
    ;;
esac

if [[ "$REQUIRE_BASELINES" == "1" && "$baseline_found" -eq 0 ]]; then
  echo "error: REQUIRE_BASELINES=1 but none of ROPgadget, ropper, or ropr were found" >&2
  print_install_hint
  exit 127
fi

if [[ "$missing_required" -ne 0 ]]; then
  print_install_hint
  exit 127
fi

case "$MODE" in
  --build) echo "build-tools-check: ok" ;;
  --samples) echo "sample-tools-check: ok" ;;
  --dev) echo "dev-tools-check: ok" ;;
  --baselines) echo "baseline-tools-check: ok" ;;
  --all) echo "full-tools-check: ok" ;;
  --doctor) echo "doctor: complete" ;;
esac
