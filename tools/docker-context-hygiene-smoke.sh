#!/usr/bin/env bash
# Build a secret-safe isolated Docker context with sentinel .env* files and
# assert that .dockerignore keeps them out of the resulting image.
set -euo pipefail

IMAGE="${1:-x64lens-dev-context-hygiene}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPROOT="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPROOT/x64lens-docker-context.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
CTX="$WORK/context"
mkdir -p "$CTX"

# Copy the public working tree without reading or copying real local env files.
tar \
  --exclude='./.git' \
  --exclude='./.local' \
  --exclude='./.codex' \
  --exclude='./.agents' \
  --exclude='./build' \
  --exclude='./tests/bin' \
  --exclude='./tests/results' \
  --exclude='./benchmarks/results' \
  --exclude='./.env' \
  --exclude='./.env.*' \
  -C "$ROOT" -cf - . | tar -C "$CTX" -xf -

printf 'sentinel only; not a secret\n' > "$CTX/.env"
printf 'sentinel only; not a secret\n' > "$CTX/.env.local"
printf 'sentinel only; not a secret\n' > "$CTX/.env.production"

docker build -t "$IMAGE" "$CTX" >/dev/null

docker run --rm "$IMAGE" bash -lc '
  test ! -e /work/.env &&
  test ! -e /work/.env.local &&
  test ! -e /work/.env.production
'

echo "docker-context-hygiene-smoke: ok image=$IMAGE"
