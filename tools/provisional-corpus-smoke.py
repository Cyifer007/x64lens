#!/usr/bin/env python3
"""Validate the Sprint 11 provisional corpus contract and regeneration path."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER = ROOT / "benchmarks/scripts/build-provisional-corpus.py"
SPEC = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
CORPUS_ID = "s11-p056-provisional-v1"
EXPECTED_TARGETS = 24


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def run(*args: str, env: dict[str, str] | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def tree_identity(root: pathlib.Path) -> dict[str, tuple[str, str, int, int, int]]:
    result: dict[str, tuple[str, str, int, int, int]] = {}
    for path in [root, *sorted(root.rglob("*"))]:
        metadata = path.stat(follow_symlinks=False)
        relative = "." if path == root else path.relative_to(root).as_posix()
        if stat.S_ISDIR(metadata.st_mode):
            result[relative] = ("directory", "", 0, stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns)
        elif stat.S_ISREG(metadata.st_mode):
            result[relative] = (
                "file",
                sha256(path),
                metadata.st_size,
                stat.S_IMODE(metadata.st_mode),
                metadata.st_mtime_ns,
            )
        else:
            result[relative] = ("other", "", metadata.st_size, stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns)
    return result


def write_spec(path: pathlib.Path, mutate: Any) -> None:
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    data["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    data["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    mutate(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def regenerate_checksums(root: pathlib.Path) -> None:
    checksum = root / "SHA256SUMS.txt"
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != checksum:
            lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    checksum.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(checksum, 0o444)


def assert_no_stage_or_final(output_root: pathlib.Path) -> None:
    require(not (output_root / CORPUS_ID).exists(), "failed corpus build published a final result")
    stage_names = [path.name for path in output_root.iterdir() if ".staging." in path.name]
    require(not stage_names, f"failed corpus build left staging paths: {stage_names}")


def pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def interruption_probe(base_spec: dict[str, Any], temporary: pathlib.Path) -> None:
    fake_dir = temporary / "fake-tools"
    fake_dir.mkdir()
    marker = temporary / "fake-compiler-pids.txt"
    fake = fake_dir / "x64lens-fake-cc"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ ${1:-} == --version ]]; then echo 'x64lens fake compiler 1.0'; exit 0; fi\n"
        "if [[ ${1:-} == -dumpmachine ]]; then echo 'x86_64-unknown-linux-gnu'; exit 0; fi\n"
        "setsid bash -c 'sleep 60' & child=$!\n"
        f"tmp={marker!s}.tmp.$$\n"
        "printf '%s\\n%s\\n' \"$$\" \"$child\" > \"$tmp\"\n"
        f"mv \"$tmp\" {marker!s}\n"
        "wait \"$child\"\n",
        encoding="utf-8",
    )
    os.chmod(fake, 0o755)

    spec = json.loads(json.dumps(base_spec))
    spec["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    spec["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    spec["toolchains"] = [{"id": "fake", "command": fake.name, "required": True}]
    spec["optimization_profiles"] = [spec["optimization_profiles"][0]]
    spec["artifact_profiles"] = [spec["artifact_profiles"][0]]
    spec["hardening_profiles"] = [spec["hardening_profiles"][0]]
    spec["target_count"] = 1
    interrupt_spec = temporary / "interrupt-spec.json"
    interrupt_spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    output_root = temporary / "interrupt-output"
    output_root.mkdir()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_dir}{os.pathsep}{environment.get('PATH', '')}"
    process = subprocess.Popen(
        [sys.executable, str(BUILDER), "--spec", str(interrupt_spec), "--output-root", str(output_root)],
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 15
    pids: list[int] = []
    while time.monotonic() < deadline:
        if marker.exists():
            lines = marker.read_text(encoding="utf-8").splitlines()
            if len(lines) >= 2:
                pids = [int(line) for line in lines]
                break
        if process.poll() is not None:
            break
        time.sleep(0.05)
    if len(pids) != 2:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
        raise SmokeError(f"interruption probe did not record compiler and descendant PIDs: {pids}")
    process.send_signal(signal.SIGINT)
    stdout, stderr = process.communicate(timeout=15)
    require(process.returncode == 130, f"interrupted builder returned {process.returncode}: {stdout} {stderr}")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and any(pid_exists(pid) for pid in pids):
        time.sleep(0.05)
    require(not any(pid_exists(pid) for pid in pids), f"interrupted compiler process survived: {pids}")
    assert_no_stage_or_final(output_root)



def capture_limit_probe(base_spec: dict[str, Any], temporary: pathlib.Path) -> None:
    fake_dir = temporary / "capture-limit-tools"
    fake_dir.mkdir()
    marker = temporary / "capture-limit-pid.txt"
    fake = fake_dir / "x64lens-noisy-cc"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ ${1:-} == --version ]]; then echo 'x64lens noisy compiler 1.0'; exit 0; fi\n"
        "if [[ ${1:-} == -dumpmachine ]]; then echo 'x86_64-unknown-linux-gnu'; exit 0; fi\n"
        f"printf '%s\\n' \"$$\" > {marker!s}\n"
        "exec python3 -c 'import sys,time; sys.stdout.buffer.write(b\"x\"*8192); sys.stdout.flush(); time.sleep(60)'\n",
        encoding="utf-8",
    )
    os.chmod(fake, 0o755)

    spec = json.loads(json.dumps(base_spec))
    spec["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    spec["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    spec["toolchains"] = [{"id": "noisy", "command": fake.name, "required": True}]
    spec["optimization_profiles"] = [spec["optimization_profiles"][0]]
    spec["artifact_profiles"] = [spec["artifact_profiles"][0]]
    spec["hardening_profiles"] = [spec["hardening_profiles"][0]]
    spec["target_count"] = 1
    spec["limits"]["maximum_log_bytes"] = 4096
    capture_spec = temporary / "capture-limit-spec.json"
    capture_spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    output_root = temporary / "capture-limit-output"
    output_root.mkdir()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_dir}{os.pathsep}{environment.get('PATH', '')}"
    result = run("--spec", str(capture_spec), "--output-root", str(output_root), env=environment, timeout=30)
    require(result.returncode == 2, f"oversized compiler output was accepted: {result.stdout} {result.stderr}")
    require(
        "command stdout exceeded the 4096-byte capture limit" in result.stderr,
        f"unexpected capture-limit diagnostic: {result.stderr}",
    )
    require(marker.is_file(), "capture-limit compiler did not start")
    pid = int(marker.read_text(encoding="utf-8").strip())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and pid_exists(pid):
        time.sleep(0.05)
    require(not pid_exists(pid), f"capture-limit compiler survived: {pid}")
    assert_no_stage_or_final(output_root)


def spawn_window_probe(temporary: pathlib.Path) -> None:
    probe = temporary / "spawn-window-probe.py"
    worker = temporary / "spawn-window-worker.sh"
    worker.write_text("#!/usr/bin/env bash\nset -euo pipefail\nsleep 60\n", encoding="utf-8")
    os.chmod(worker, 0o755)
    probe.write_text(
        "from __future__ import annotations\n"
        "import importlib.util, os, pathlib, signal, sys\n"
        f"builder_path = pathlib.Path({str(BUILDER)!r})\n"
        "spec = importlib.util.spec_from_file_location('x64lens_corpus_builder_probe', builder_path)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "sys.modules[spec.name] = module\n"
        "spec.loader.exec_module(module)\n"
        "real_popen = module.subprocess.Popen\n"
        "spawned = []\n"
        "def injecting_popen(*args, **kwargs):\n"
        "    process = real_popen(*args, **kwargs)\n"
        "    spawned.append(process.pid)\n"
        "    os.kill(os.getpid(), signal.SIGINT)\n"
        "    return process\n"
        "module.subprocess.Popen = injecting_popen\n"
        "module.enable_subreaper()\n"
        "module.install_signal_handlers()\n"
        "try:\n"
        f"    module.run_command([{str(worker)!r}], pathlib.Path({str(temporary)!r}), dict(os.environ), 30, 4096)\n"
        "except module.CorpusInterrupted as exc:\n"
        "    if exc.signum != signal.SIGINT:\n"
        "        raise\n"
        "else:\n"
        "    raise SystemExit('spawn-window signal was not retained')\n"
        "if module.direct_child_pids():\n"
        "    raise SystemExit(f'children survived: {sorted(module.direct_child_pids())}')\n"
        "for pid in spawned:\n"
        "    try:\n"
        "        os.kill(pid, 0)\n"
        "    except ProcessLookupError:\n"
        "        continue\n"
        "    raise SystemExit(f'spawn-window process survived: {pid}')\n"
        "print('spawn-window-probe: ok')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(probe)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0, f"spawn-window probe failed: {completed.stdout} {completed.stderr}")
    require(completed.stdout.strip() == "spawn-window-probe: ok", f"unexpected spawn-window probe output: {completed.stdout!r}")


def main() -> int:
    require(BUILDER.is_file() and os.access(BUILDER, os.X_OK), "missing executable provisional corpus builder")
    require(SPEC.is_file(), "missing provisional corpus specification")
    source = ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c"
    require(source.is_file(), "missing provisional corpus source")

    platform_result = run("--spec", str(SPEC), "--platform-check", timeout=30)
    require(platform_result.returncode == 0, f"platform check failed: {platform_result.stderr}")
    require(
        platform_result.stdout.strip()
        == "provisional-corpus-platform-check: ok compilers=2 linker=gnu-ld-bfd tools=3 subreaper=enabled",
        f"unexpected platform banner: {platform_result.stdout!r}",
    )

    base_spec = json.loads(SPEC.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="x64lens-provisional-corpus-smoke-") as raw:
        temporary = pathlib.Path(raw)
        first_root = temporary / "first"
        second_root = temporary / "second"
        first_root.mkdir()
        second_root.mkdir()

        first = run("--spec", str(SPEC), "--output-root", str(first_root))
        require(first.returncode == 0, f"first corpus build failed: {first.stderr}")
        second = run("--spec", str(SPEC), "--output-root", str(second_root))
        require(second.returncode == 0, f"second corpus build failed: {second.stderr}")
        first_corpus = first_root / CORPUS_ID
        second_corpus = second_root / CORPUS_ID
        require(first_corpus.is_dir() and second_corpus.is_dir(), "corpus build did not publish both results")

        first_identity = tree_identity(first_corpus)
        second_identity = tree_identity(second_corpus)
        require(first_identity == second_identity, "independent corpus builds are not byte/mode reproducible")
        require("corpus-manifest.json" in first_identity and "commands.tsv" in first_identity, "missing corpus evidence artifacts")
        require(all(".staging." not in name for name in first_identity), "retained corpus contains a staging path")
        require(all(record[3] == (0o755 if record[0] == "directory" else record[3]) for record in first_identity.values()), "corpus directory modes are not normalized")
        require(all(record[4] == 0 for record in first_identity.values()), "corpus mtimes are not normalized")

        verify = run("--verify", str(first_corpus), timeout=30)
        require(verify.returncode == 0, f"corpus verification failed: {verify.stderr}")
        expected_banner = (
            "provisional-corpus-verify: ok corpus=s11-p056-provisional-v1 "
            "targets=24 compilers=2 optimizations=2 artifacts=3 hardening=2"
        )
        require(verify.stdout.strip() == expected_banner, f"unexpected verification banner: {verify.stdout!r}")

        manifest_text = (first_corpus / "corpus-manifest.json").read_text(encoding="utf-8")
        require(str(first_root) not in manifest_text and str(second_root) not in manifest_text, "manifest retained output-root paths")
        require(".staging." not in manifest_text, "manifest retained a staging path")
        manifest = json.loads(manifest_text)
        require(manifest["target_count"] == EXPECTED_TARGETS, "unexpected target count")
        require(manifest["matrix"] == {
            "toolchains": 2,
            "optimization_profiles": 2,
            "artifact_profiles": 3,
            "hardening_profiles": 2,
        }, "unexpected corpus matrix dimensions")
        require({tool["id"] for tool in manifest["tools"]} == {"gcc", "clang", "gnu-ld-bfd"}, "tool identity set is incomplete")
        targets = manifest["targets"]
        require(len({target["id"] for target in targets}) == EXPECTED_TARGETS, "target identifiers are not unique")
        require(sum(target["elf"]["elf_type"] == "ET_EXEC" for target in targets) == 8, "unexpected ET_EXEC count")
        require(sum(target["elf"]["elf_type"] == "ET_DYN" for target in targets) == 16, "unexpected ET_DYN count")
        require(sum(target["elf"]["gnu_stack_executable"] for target in targets) == 12, "unexpected executable-stack count")
        require(sum(target["elf"]["gnu_property_x86_ibt"] for target in targets) == 12, "unexpected IBT-property count")
        require(sum(target["elf"]["gnu_property_x86_shstk"] for target in targets) == 12, "unexpected SHSTK-property count")
        require(sum(target["elf"]["gnu_relro_present"] for target in targets) == 8, "unexpected RELRO count")
        require(all(target["elf"]["rwx_load_count"] == 0 for target in targets), "generated corpus contains an RWX PT_LOAD")
        require(all(target["target_executed"] is False for target in targets), "target execution policy changed")
        require(all(target["mode"] == "0444" for target in targets), "generated target mode is not 0444")

        before_no_replace = tree_identity(first_corpus)
        no_replace = run("--spec", str(SPEC), "--output-root", str(first_root), timeout=30)
        require(no_replace.returncode == 2, "builder replaced or accepted an existing corpus")
        require("will not be replaced" in no_replace.stderr or "already exists" in no_replace.stderr, "unexpected no-replace diagnostic")
        require(tree_identity(first_corpus) == before_no_replace, "existing corpus changed during no-replace rejection")

        invalid_cases = [
            ("missing-publication", lambda data: data.pop("publication_eligible"), "fields do not match"),
            ("publication-true", lambda data: data.__setitem__("publication_eligible", True), "publication_eligible=false"),
            ("source-hash", lambda data: data["source"].__setitem__("sha256", "0" * 64), "source SHA-256"),
            ("target-count", lambda data: data.__setitem__("target_count", 23), "matrix product"),
            ("duplicate-tool", lambda data: data["toolchains"][1].__setitem__("id", data["toolchains"][0]["id"]), "duplicate toolchains id"),
            ("outside-source", lambda data: data["source"].__setitem__("path", "/etc/passwd"), "outside the repository"),
            ("reserved-env", lambda data: data["build_environment"].__setitem__("PATH", "/tmp"), "reserved key"),
        ]
        for name, mutation, expected in invalid_cases:
            path = temporary / f"{name}.json"
            write_spec(path, mutation)
            result = run("--spec", str(path), "--platform-check", timeout=30)
            require(result.returncode == 2, f"invalid spec {name} was accepted")
            require(expected in result.stderr, f"invalid spec {name} produced unexpected diagnostic: {result.stderr}")

        missing_spec = temporary / "missing-tool.json"
        write_spec(missing_spec, lambda data: data["toolchains"][0].__setitem__("command", "x64lens-no-such-compiler"))
        missing_output = temporary / "missing-output"
        missing_output.mkdir()
        missing = run("--spec", str(missing_spec), "--output-root", str(missing_output), timeout=30)
        require(missing.returncode == 2, "missing compiler was not rejected")
        require("required tool is missing" in missing.stderr, f"unexpected missing-tool diagnostic: {missing.stderr}")
        assert_no_stage_or_final(missing_output)

        tampered = temporary / CORPUS_ID
        shutil.copytree(first_corpus, tampered)
        target = next((tampered / "targets").iterdir())
        os.chmod(target, 0o644)
        mode_failure = run("--verify", str(tampered), timeout=30)
        require(mode_failure.returncode == 2 and "target mode changed" in mode_failure.stderr, "target mode tamper was not rejected")
        os.chmod(target, 0o444)

        manifest_path = tampered / "corpus-manifest.json"
        tampered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered_manifest["publication_eligible"] = True
        os.chmod(manifest_path, 0o644)
        manifest_path.write_text(json.dumps(tampered_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(manifest_path, 0o444)
        regenerate_checksums(tampered)
        publication_failure = run("--verify", str(tampered), timeout=30)
        require(
            publication_failure.returncode == 2 and "publication_eligible=false" in publication_failure.stderr,
            "publication eligibility tamper was not rejected semantically",
        )

        shutil.rmtree(tampered)
        shutil.copytree(first_corpus, tampered)
        commands_path = tampered / "commands.tsv"
        os.chmod(commands_path, 0o644)
        command_lines = commands_path.read_text(encoding="utf-8").splitlines()
        fields = command_lines[1].split("\t")
        fields[-1] = "0" * 64
        command_lines[1] = "\t".join(fields)
        commands_path.write_text("\n".join(command_lines) + "\n", encoding="utf-8")
        os.chmod(commands_path, 0o444)
        regenerate_checksums(tampered)
        command_failure = run("--verify", str(tampered), timeout=30)
        require(
            command_failure.returncode == 2 and "command output hash" in command_failure.stderr,
            "commands.tsv semantic tamper was not rejected",
        )

        shutil.rmtree(tampered)
        shutil.copytree(first_corpus, tampered)
        commands_path = tampered / "commands.tsv"
        os.chmod(commands_path, 0o644)
        command_lines = commands_path.read_text(encoding="utf-8").splitlines()
        fields = command_lines[1].split("\t")
        argv = json.loads(fields[7])
        argv[argv.index("-O0")] = "-O1"
        fields[7] = json.dumps(argv, separators=(",", ":"), ensure_ascii=True)
        command_lines[1] = "\t".join(fields)
        commands_path.write_text("\n".join(command_lines) + "\n", encoding="utf-8")
        os.chmod(commands_path, 0o444)
        regenerate_checksums(tampered)
        command_scope_failure = run("--verify", str(tampered), timeout=30)
        require(
            command_scope_failure.returncode == 2
            and "canonical command mismatch" in command_scope_failure.stderr,
            "canonical command tamper was not rejected",
        )

        symlinked = temporary / f"{CORPUS_ID}-symlink-source"
        shutil.copytree(first_corpus, symlinked)
        renamed = temporary / CORPUS_ID
        shutil.rmtree(tampered)
        symlinked.rename(renamed)
        (renamed / "unexpected-link").symlink_to("corpus-manifest.json")
        symlink_failure = run("--verify", str(renamed), timeout=30)
        require(symlink_failure.returncode == 2 and "non-regular" in symlink_failure.stderr, "symlink member was not rejected")

        interruption_probe(base_spec, temporary)
        spawn_window_probe(temporary)
        capture_limit_probe(base_spec, temporary)

    print(
        "provisional-corpus-smoke: ok "
        "targets=24 rebuilds=2 invalid_specs=8 tamper_cases=5 interruption_cleanup=2 capture_limits=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"provisional-corpus-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
