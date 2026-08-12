#!/usr/bin/env bash
# Prove that the immutable image's configured non-root user can recreate and
# execute inside the dedicated mutable run root without writing beneath /work.
set -euo pipefail

image=${1:?usage: docker-run-root-smoke.sh IMAGE_ID}
command -v docker >/dev/null 2>&1 || {
    printf 'docker-run-root-smoke: error: docker is required\n' >&2
    exit 127
}

for attempt in 1 2; do
    docker run --rm -e X64LENS_RUN_ROOT_ATTEMPT="$attempt" "$image" bash -lc '
        set -euo pipefail
        test "$(id -u)" -ne 0
        case ${X64LENS_RUN_ROOT_ATTEMPT:?} in 1|2) ;; *) exit 1 ;; esac
        run=${X64LENS_RUN_ROOT:?}
        case "$run" in
            ${HOME:?}/*) ;;
            *) printf "unexpected mutable run root: %s\n" "$run" >&2; exit 1 ;;
        esac
        test -w "$(dirname "$run")"
        rm -rf "$run"
        mkdir "$run"
        cat > "$run/probe.sh" <<"PROBE"
#!/usr/bin/env bash
set -euo pipefail
printf "mutable-run-root-probe: ok\\n"
PROBE
        chmod 0755 "$run/probe.sh"
        test "$("$run/probe.sh")" = "mutable-run-root-probe: ok"
        python3 /work/tools/gitless-source-manifest.py verify \
            --root /work --manifest /x64lens-source-manifest.json >/dev/null
        test ! -w /work
        test -z "$(find /work -type d -writable -print -quit)"
        test -z "$(find /work -type f -writable -print -quit)"
        if touch /work/.x64lens-write-probe 2>/dev/null; then
            rm -f /work/.x64lens-write-probe
            printf "authenticated source root is writable\n" >&2
            exit 1
        fi
        if printf "probe\n" >> /work/README.md 2>/dev/null; then
            printf "authenticated source file is writable\n" >&2
            exit 1
        fi
        test ! -e /work/.x64lens-write-probe
        test -z "$(find /work -type f -newer "$run/probe.sh" -print -quit)"
        rm -rf "$run"
        mkdir "$run"
        test -w "$run"
    '
done

printf 'docker-run-root-smoke: ok attempts=2 nonroot=1 writable_parent=1 executable_run_root=1 source_pristine=1 source_readonly=1\n'
