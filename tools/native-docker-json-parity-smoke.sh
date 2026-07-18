#!/usr/bin/env bash
# Compare native and container reports byte-for-byte for the controlled fixture
# matrix. Both sides invoke repository-relative target paths so path identity is
# part of the comparison rather than normalized after reporting.

set -euo pipefail

IMAGE=${1:-x64lens-dev}
BINARY=${2:-./build/x64lens}

command -v docker >/dev/null 2>&1 || {
    printf 'native-docker-json-parity-smoke: error: docker is required\n' >&2
    exit 127
}
[[ -x "$BINARY" ]] || {
    printf 'native-docker-json-parity-smoke: error: missing native binary: %s\n' "$BINARY" >&2
    exit 1
}

fixtures=(
    gadgets
    gadgets_sprint10
    gadgets_sprint10_transfer
    gadgets_sprint10_stack_adjust
    gadgets_sprint10_memory
    gadgets_sprint10_effects
)
commands=(gadgets analyze)

tmp=$(mktemp -d "${TMPDIR:-/tmp}/x64lens-native-docker-parity.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/native" "$tmp/docker"

for fixture in "${fixtures[@]}"; do
    [[ -f "tests/bin/$fixture" ]] || {
        printf 'native-docker-json-parity-smoke: error: missing fixture: tests/bin/%s\n' "$fixture" >&2
        exit 1
    }
    for command in "${commands[@]}"; do
        "$BINARY" "$command" --format json --max-depth 4 "./tests/bin/$fixture" \
            > "$tmp/native/${command}-${fixture}.json"
    done
done

# The image contains its own source snapshot from docker-build. Stream only the
# generated result tree through tar so container build artifacts never alter the
# host worktree.
docker run --rm "$IMAGE" bash -lc '
    set -euo pipefail
    make clean >/dev/null
    make >/dev/null
    make samples >/dev/null
    out=$(mktemp -d)
    for fixture in \
        gadgets \
        gadgets_sprint10 \
        gadgets_sprint10_transfer \
        gadgets_sprint10_stack_adjust \
        gadgets_sprint10_memory \
        gadgets_sprint10_effects
    do
        for command in gadgets analyze
        do
            ./build/x64lens "$command" --format json --max-depth 4 "./tests/bin/$fixture" \
                > "$out/${command}-${fixture}.json"
        done
    done
    tar -C "$out" -cf - .
' | tar -C "$tmp/docker" -xf -

pairs=0
for fixture in "${fixtures[@]}"; do
    for command in "${commands[@]}"; do
        name="${command}-${fixture}.json"
        python3 -m json.tool "$tmp/native/$name" >/dev/null
        python3 -m json.tool "$tmp/docker/$name" >/dev/null
        cmp "$tmp/native/$name" "$tmp/docker/$name"
        pairs=$((pairs + 1))
    done
done

printf 'native-docker-json-parity-smoke: ok fixtures=%d commands=%d byte_identical_pairs=%d\n' \
    "${#fixtures[@]}" "${#commands[@]}" "$pairs"
