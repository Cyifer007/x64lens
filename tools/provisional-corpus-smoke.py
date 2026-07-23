#!/usr/bin/env python3
"""Validate the Sprint 11 provisional corpus contract and regeneration path."""
from __future__ import annotations

import hashlib
import importlib.util
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
    os.chmod(checksum, 0o644)
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != checksum:
            lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    checksum.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(checksum, 0o444)


def assert_no_stage_or_final(output_root: pathlib.Path, corpus_id: str) -> None:
    require(not (output_root / corpus_id).exists(), f"failed corpus build published final result: {corpus_id}")
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
    assert_no_stage_or_final(output_root, spec["corpus_id"])




def load_builder_module(name: str):
    module_spec = importlib.util.spec_from_file_location(name, BUILDER)
    require(module_spec is not None and module_spec.loader is not None, "cannot load provisional corpus builder module")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def stage_identity_probe(temporary: pathlib.Path) -> None:
    """Remove the creation-time stage after rename without deleting a replacement."""
    module = load_builder_module("x64lens_corpus_stage_identity_probe")
    root = temporary / "stage-substitution-root"
    root.mkdir()
    owned = module.OwnedStage.create(root, ".owned.staging")
    try:
        (owned.path / "owned.txt").write_text("owned\n", encoding="utf-8")
        escaped = root / ".escaped-original"
        os.rename(owned.path, escaped)
        replacement = root / ".owned.staging"
        replacement.mkdir()
        (replacement / "foreign.txt").write_text("foreign\n", encoding="utf-8")
        owned.cleanup("corpus stage substitution probe")
        require(not escaped.exists(), "renamed builder-owned stage survived cleanup")
        require(replacement.is_dir(), "foreign replacement stage was deleted")
        require((replacement / "foreign.txt").read_text(encoding="utf-8") == "foreign\n", "foreign replacement changed")
    finally:
        owned.close()


def publish_commit_probe(temporary: pathlib.Path) -> None:
    """Retain committed state when publication reporting fails after rename."""
    module = load_builder_module("x64lens_corpus_publish_probe")
    root = temporary / "publish-commit-root"
    root.mkdir()
    owned = module.OwnedStage.create(root, ".publish.staging")
    final = root / "published"
    (owned.path / "corpus-manifest.json").write_text("{}\n", encoding="utf-8")
    original = module.atomic_publish_noreplace

    def publish_then_interrupt(stage: pathlib.Path, destination: pathlib.Path) -> None:
        original(stage, destination)
        raise module.CorpusInterrupted(signal.SIGINT)

    module.atomic_publish_noreplace = publish_then_interrupt
    try:
        try:
            module.publish_owned_stage(owned, final, "corpus publish commit probe")
        except module.CorpusInterrupted:
            pass
        else:
            raise SmokeError("post-rename corpus interruption was not injected")
        require(owned.committed is True, "post-rename corpus interruption lost committed state")
        require(final.is_dir() and (final / "corpus-manifest.json").is_file(), "committed corpus result was not retained")
    finally:
        module.atomic_publish_noreplace = original
        owned.close()



def publish_substitution_probe(temporary: pathlib.Path) -> None:
    """Reject a foreign directory substituted at the final publication path."""
    module = load_builder_module("x64lens_corpus_publish_substitution_probe")
    root = temporary / "publish-substitution-root"
    root.mkdir()
    owned = module.OwnedStage.create(root, ".publish-substitution.staging")
    final = root / "published"
    (owned.path / "corpus-manifest.json").write_text("{}\n", encoding="utf-8")
    original = module.atomic_publish_noreplace

    def substitute_after_move(stage: pathlib.Path, destination: pathlib.Path) -> None:
        escaped = root / ".owned-after-publication"
        os.rename(stage, escaped)
        destination.mkdir()
        (destination / "foreign.txt").write_text("foreign\n", encoding="utf-8")

    module.atomic_publish_noreplace = substitute_after_move
    try:
        try:
            module.publish_owned_stage(owned, final, "corpus publication substitution probe")
        except module.CorpusError as exc:
            require("substituted directory" in str(exc), f"unexpected substitution diagnostic: {exc}")
        else:
            raise SmokeError("foreign publication substitution was accepted")
        require(owned.committed is False, "foreign publication substitution marked the owned stage committed")
        require(final.is_dir(), "foreign published directory disappeared")
        require((final / "foreign.txt").read_text(encoding="utf-8") == "foreign\n", "foreign published directory changed")
        owned.cleanup("corpus publication substitution cleanup")
        require(not (root / ".owned-after-publication").exists(), "escaped owned corpus stage survived cleanup")
        require(final.is_dir(), "owned-stage cleanup deleted the foreign published directory")
    finally:
        module.atomic_publish_noreplace = original
        owned.close()


def duplicate_tool_manifest_probe(corpus: pathlib.Path, temporary: pathlib.Path) -> None:
    """Reject a checksummed corpus whose tool inventory contains a duplicate record."""
    parent = temporary / "duplicate-tool-record"
    parent.mkdir()
    duplicate = parent / CORPUS_ID
    shutil.copytree(corpus, duplicate)
    manifest_path = duplicate / "corpus-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tools"].append(json.loads(json.dumps(manifest["tools"][0])))
    os.chmod(manifest_path, 0o644)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o444)
    regenerate_checksums(duplicate)
    result = run("--verify", str(duplicate), timeout=30)
    require(
        result.returncode == 2 and "tool records are duplicated" in result.stderr,
        f"duplicate authenticated tool record was not rejected: {result.stderr}",
    )

def early_signal_probe(temporary: pathlib.Path) -> None:
    """Prove SIGTERM is handled before any staging directory can be orphaned."""
    module = load_builder_module("x64lens_corpus_early_signal_probe")
    output = temporary / "early-signal-output"
    output.mkdir()
    original_create = module.OwnedStage.create.__func__
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def interrupting_create(cls, parent, name, registry=None):
        os.kill(os.getpid(), signal.SIGTERM)
        return original_create(cls, parent, name, registry)

    module.OwnedStage.create = classmethod(interrupting_create)
    try:
        try:
            module.build_corpus(SPEC, output, ROOT)
        except module.CorpusInterrupted as exc:
            require(exc.signum == signal.SIGTERM, "early signal identity mismatch")
        else:
            raise SmokeError("early SIGTERM did not interrupt corpus construction")
    finally:
        module.OwnedStage.create = classmethod(original_create)
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        module.CREATING_STAGE = False
        module.INTERRUPTED_BY = None
    assert_no_stage_or_final(output, CORPUS_ID)


def update_spec_snapshot_and_manifest(corpus: pathlib.Path, mutate: Any) -> None:
    spec_path = corpus / "inputs/spec/corpus-spec.json"
    manifest_path = corpus / "corpus-manifest.json"
    spec_value = json.loads(spec_path.read_text(encoding="utf-8"))
    mutate(spec_value)
    os.chmod(spec_path, 0o644)
    spec_path.write_text(json.dumps(spec_value, indent=2) + "\n", encoding="utf-8")
    os.chmod(spec_path, 0o444)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["spec"]["sha256"] = sha256(spec_path)
    manifest["inputs"]["spec"]["size_bytes"] = spec_path.stat().st_size
    os.chmod(manifest_path, 0o644)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o444)


def retained_limit_probes(source_corpus: pathlib.Path, temporary: pathlib.Path) -> None:
    """Reject self-consistent evidence whose retained files exceed its own limits."""
    output_mutation_root = temporary / "retained-output-limit-root"
    output_mutation_root.mkdir()
    output_mutation = output_mutation_root / CORPUS_ID
    shutil.copytree(source_corpus, output_mutation)
    update_spec_snapshot_and_manifest(
        output_mutation,
        lambda data: data["limits"].__setitem__("maximum_output_bytes", 4096),
    )
    regenerate_checksums(output_mutation)
    output_result = run("--verify", str(output_mutation), timeout=30)
    require(
        output_result.returncode == 2 and "target exceeds retained maximum_output_bytes" in output_result.stderr,
        f"retained output limit mutation was accepted: {output_result.stderr}",
    )

    log_mutation_root = temporary / "retained-log-limit-root"
    log_mutation_root.mkdir()
    log_mutation = log_mutation_root / CORPUS_ID
    shutil.copytree(source_corpus, log_mutation)
    manifest_path = log_mutation / "corpus-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tool = manifest["tools"][0]
    version_stdout = log_mutation / tool["version_stdout_path"]
    os.chmod(version_stdout, 0o644)
    version_stdout.write_bytes(version_stdout.read_bytes() + b"X" * 8192)
    os.chmod(version_stdout, 0o444)
    tool["version_stdout_sha256"] = sha256(version_stdout)
    tool["version_stdout_size_bytes"] = version_stdout.stat().st_size
    os.chmod(manifest_path, 0o644)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o444)
    update_spec_snapshot_and_manifest(
        log_mutation,
        lambda data: data["limits"].__setitem__("maximum_log_bytes", 4096),
    )
    regenerate_checksums(log_mutation)
    log_result = run("--verify", str(log_mutation), timeout=30)
    require(
        log_result.returncode == 2 and "exceeds retained maximum_log_bytes" in log_result.stderr,
        f"retained log limit mutation was accepted: {log_result.stderr}",
    )

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
    assert_no_stage_or_final(output_root, spec["corpus_id"])


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


def clean_target_probe(source_corpus: pathlib.Path, temporary: pathlib.Path) -> None:
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    phony_line = next((line for line in makefile_text.splitlines() if line.startswith(".PHONY:")), "")
    require("clean-provisional-corpus" in phony_line.split(), "clean-provisional-corpus is not phony")
    require('rm -rf "$(PROVISIONAL_CORPUS_PATH)"' not in makefile_text, "clean target still contains unbounded rm -rf")

    root = temporary / "clean-root"
    root.mkdir()
    corpus = root / CORPUS_ID
    shutil.copytree(source_corpus, corpus)
    unrelated = temporary / "clean-victim"
    unrelated.mkdir()
    victim = unrelated / "sentinel.txt"
    victim.write_text("keep", encoding="utf-8")
    clean = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "clean-provisional-corpus",
            f"PROVISIONAL_CORPUS_ROOT={root}",
            f"PROVISIONAL_CORPUS_PATH={unrelated}",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    require(clean.returncode == 0 and not corpus.exists(), f"safe corpus clean failed: {clean.stdout} {clean.stderr}")
    require(victim.read_text(encoding="utf-8") == "keep", "overridden corpus path was deleted")

    forged = root / CORPUS_ID
    forged.mkdir()
    (forged / "corpus-manifest.json").write_text(
        json.dumps({
            "corpus_id": CORPUS_ID,
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
        }) + "\n",
        encoding="utf-8",
    )
    forged_result = subprocess.run(
        ["make", "--no-print-directory", "clean-provisional-corpus", f"PROVISIONAL_CORPUS_ROOT={root}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    require(forged_result.returncode != 0 and forged.exists(), "forged corpus marker was accepted for cleanup")
    shutil.rmtree(forged)

    root_marker = root / "unrelated.txt"
    root_marker.write_text("keep", encoding="utf-8")
    clean_again = subprocess.run(
        ["make", "--no-print-directory", "clean-provisional-corpus", f"PROVISIONAL_CORPUS_ROOT={root}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    require(
        clean_again.returncode == 0 and root_marker.read_text(encoding="utf-8") == "keep",
        "absent corpus cleanup touched unrelated state",
    )


def side_member_probe(base_spec: dict[str, Any], temporary: pathlib.Path) -> None:
    wrapper = temporary / "side-member-compiler.py"
    real_gcc = shutil.which("gcc")
    require(real_gcc is not None, "gcc is required for the side-member probe")
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, subprocess, sys\n"
        "if len(sys.argv) > 1 and sys.argv[1] in {'--version', '-dumpmachine'}:\n"
        "    pathlib.Path('undeclared-side-file.bin').write_bytes(b'X' * 1048576)\n"
        f"    raise SystemExit(subprocess.run([{real_gcc!r}, *sys.argv[1:]]).returncode)\n"
        f"raise SystemExit(subprocess.run([{real_gcc!r}, *sys.argv[1:]]).returncode)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    spec = json.loads(json.dumps(base_spec))
    spec["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    spec["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    spec["corpus_id"] = "s11-p057-side-member-probe"
    spec["toolchains"] = [{"id": "gcc", "command": str(wrapper), "required": True}]
    spec["optimization_profiles"] = spec["optimization_profiles"][:1]
    spec["artifact_profiles"] = spec["artifact_profiles"][:1]
    spec["hardening_profiles"] = spec["hardening_profiles"][:1]
    spec["target_count"] = 1
    path = temporary / "side-member-spec.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    output = temporary / "side-member-output"
    output.mkdir()
    result = run("--spec", str(path), "--output-root", str(output), timeout=60)
    require(result.returncode == 2 and "undeclared workspace member" in result.stderr, f"side member was not rejected: {result.stderr}")
    assert_no_stage_or_final(output, spec["corpus_id"])


def locked_cleanup_probe(base_spec: dict[str, Any], temporary: pathlib.Path) -> None:
    wrapper = temporary / "locked-cleanup-compiler.py"
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "if len(sys.argv) > 1 and sys.argv[1] == '--version': print('fakecc 1.0'); raise SystemExit(0)\n"
        "if len(sys.argv) > 1 and sys.argv[1] == '-dumpmachine': print('x86_64-linux-gnu'); raise SystemExit(0)\n"
        "pathlib.Path('locked').mkdir(); os.chmod('locked', 0); raise SystemExit(7)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    spec = json.loads(json.dumps(base_spec))
    spec["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    spec["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    spec["corpus_id"] = "s11-p057-locked-cleanup-probe"
    spec["toolchains"] = [{"id": "fakecc", "command": str(wrapper), "required": True}]
    spec["optimization_profiles"] = spec["optimization_profiles"][:1]
    spec["artifact_profiles"] = spec["artifact_profiles"][:1]
    spec["hardening_profiles"] = spec["hardening_profiles"][:1]
    spec["target_count"] = 1
    path = temporary / "locked-cleanup-spec.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    output = temporary / "locked-cleanup-output"
    output.mkdir()
    result = run("--spec", str(path), "--output-root", str(output), timeout=60)
    require(result.returncode == 2, "locked cleanup compiler unexpectedly succeeded")
    assert_no_stage_or_final(output, spec["corpus_id"])


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
        assert_no_stage_or_final(missing_output, json.loads(missing_spec.read_text(encoding="utf-8"))["corpus_id"])

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
        early_signal_probe(temporary)
        stage_identity_probe(temporary)
        publish_commit_probe(temporary)
        publish_substitution_probe(temporary)
        duplicate_tool_manifest_probe(first_corpus, temporary)
        capture_limit_probe(base_spec, temporary)
        retained_limit_probes(first_corpus, temporary)
        clean_target_probe(first_corpus, temporary)
        side_member_probe(base_spec, temporary)
        locked_cleanup_probe(base_spec, temporary)

    print(
        "provisional-corpus-smoke: ok "
        "targets=24 rebuilds=2 invalid_specs=8 tamper_cases=5 interruption_cleanup=3 "
        "capture_limits=1 retained_limits=2 clean_guards=1 make_clean_guards=1 "
        "membership_rejections=1 stage_substitution=1 early_signals=1 post_publish_commit=1 "
        "publish_substitution=1 duplicate_tool_records=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"provisional-corpus-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
