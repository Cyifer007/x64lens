#!/usr/bin/env python3
"""Exercise adversarial transaction and cleanup boundaries of the diagnostic runner.

This regression promotes Patch 058 review probes into the maintained Sprint 11
validation surface. It proves that future artifact names cannot redirect writes,
that stage identity follows the owned inode across rename, that publication
cannot commit a substituted tree, and that repeated termination does not leave
runner-owned staging residue.
"""
from __future__ import annotations

import errno
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"


class SmokeError(RuntimeError):
    """Raised when an adversarial runner contract is not enforced."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def load_runner(name: str):
    module_spec = importlib.util.spec_from_file_location(name, RUNNER)
    require(module_spec is not None and module_spec.loader is not None, "cannot load diagnostic runner")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def write_probe_tool(path: Path, victim_file: Path, victim_dir: Path, escaped_stage: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import os, sys\n"
        "mode = sys.argv[1]\n"
        "if mode == 'version': print('probe-tool 1.0'); raise SystemExit(0)\n"
        "stage = Path.cwd().parents[2]\n"
        "if mode == 'symlink-rows':\n"
        f"    (stage / 'rows.tsv').symlink_to({str(victim_file)!r})\n"
        "elif mode == 'prime-work':\n"
        "    future = stage / 'outputs' / 'measured-001-02-follow' / 'work'\n"
        "    future.parent.mkdir(parents=True, exist_ok=True)\n"
        f"    future.symlink_to({str(victim_dir)!r}, target_is_directory=True)\n"
        "elif mode == 'follow':\n"
        "    (Path.cwd() / 'runner-cwd-marker').write_text('unexpected traversal\\n', encoding='utf-8')\n"
        "elif mode == 'escape-stage':\n"
        f"    os.rename(stage, {str(escaped_stage)!r})\n"
        "    stage.mkdir(mode=0o700)\n"
        "    (stage / 'foreign-marker').write_text('replacement\\n', encoding='utf-8')\n"
        "print(mode)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_spec(path: Path, campaign_id: str, tool: Path, target: Path, modes: list[str]) -> None:
    conditions = [
        {
            "id": mode,
            "task_scope": "baseline_gadget_report",
            "profile_id": "core-1w",
            "worker_count": 1,
            "tool": "probe",
            "target": "target",
            "argv": ["{tool}", mode, "{target}"],
            "extractor": "none",
            "output_scope": "diagnostic transaction regression",
        }
        for mode in modes
    ]
    value = {
        "schema_version": 2,
        "campaign_id": campaign_id,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "warmup_runs": 0,
        "measured_runs": 1,
        "timeout_seconds": 4,
        "order_policy": "listed",
        "cache_policy": "uncontrolled",
        "fail_campaign_on_error": True,
        "capture_limits": {"maximum_stdout_bytes": 4096, "maximum_stderr_bytes": 4096},
        "environment": {},
        "timer_floor": {"probe": "/bin/true", "runs": 5, "threshold_multiplier": 2},
        "tools": [{"id": "probe", "path": str(tool), "version": "1.0", "version_argv": ["{tool}", "version"]}],
        "targets": [{"id": "target", "path": str(target), "license": "project-generated probe"}],
        "conditions": conditions,
    }
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_cli(spec: Path, output: Path, timeout: int = 45) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--spec", str(spec), "--output-root", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def assert_future_paths_and_stage_identity(base: Path) -> None:
    base.mkdir()
    victim_file = base / "rows-victim.txt"
    victim_file.write_text("ORIGINAL ROWS VICTIM\n", encoding="utf-8")
    victim_dir = base / "work-victim"
    victim_dir.mkdir()
    escaped_stage = base / "escaped-stage"
    tool = base / "probe-tool.py"
    target = base / "target.bin"
    target.write_bytes(b"probe target\n")
    write_probe_tool(tool, victim_file, victim_dir, escaped_stage)

    rows_spec = base / "rows-spec.json"
    rows_output = base / "rows-output"
    write_spec(rows_spec, "rows-symlink-regression", tool, target, ["symlink-rows"])
    rows_result = run_cli(rows_spec, rows_output)
    require(rows_result.returncode == 2, f"rows symlink case returned {rows_result.returncode}: {rows_result.stderr}")
    require(victim_file.read_text(encoding="utf-8") == "ORIGINAL ROWS VICTIM\n", "rows.tsv symlink changed an external victim")
    require(not (rows_output / "rows-symlink-regression").exists(), "rows symlink case published a result")

    work_spec = base / "work-spec.json"
    work_output = base / "work-output"
    write_spec(work_spec, "work-symlink-regression", tool, target, ["prime-work", "follow"])
    work_result = run_cli(work_spec, work_output)
    require(work_result.returncode == 2, f"work symlink case returned {work_result.returncode}: {work_result.stderr}")
    require(not (victim_dir / "runner-cwd-marker").exists(), "future work symlink was traversed")
    require(not (victim_dir / "environment").exists(), "runner created environment state through a future work symlink")
    require(not (work_output / "work-symlink-regression").exists(), "work symlink case published a result")

    escape_spec = base / "escape-spec.json"
    escape_output = base / "escape-output"
    write_spec(escape_spec, "stage-escape-regression", tool, target, ["escape-stage"])
    escape_result = run_cli(escape_spec, escape_output)
    require(escape_result.returncode == 2, f"escaped-stage case returned {escape_result.returncode}: {escape_result.stderr}")
    require(not escaped_stage.exists(), "renamed runner-owned stage survived cleanup")
    replacements = sorted(escape_output.glob(".*.staging-*"))
    require(len(replacements) == 1, f"foreign replacement stage was not preserved exactly once: {replacements}")
    require((replacements[0] / "foreign-marker").read_text(encoding="utf-8") == "replacement\n", "foreign replacement changed")
    # The foreign object is deliberately not runner-owned; the smoke removes it only after proving preservation.
    for child in replacements[0].iterdir():
        child.unlink()
    replacements[0].rmdir()


def assert_publication_and_partial_create(base: Path) -> None:
    base.mkdir()
    module = load_runner("x64lens_p059_runner_transaction_probe")

    root = base / "publish-substitution"
    root.mkdir()
    owned = module.OwnedStage.create(root, ".owned.staging")
    (owned.path / "owned.txt").write_text("owned\n", encoding="utf-8")
    escaped = root / ".escaped-owned"
    final = root / "published"
    original_publish = module.atomic_publish_noreplace

    def substitute_then_publish(stage: Path, destination: Path) -> None:
        os.rename(stage, escaped)
        stage.mkdir()
        (stage / "foreign.txt").write_text("foreign\n", encoding="utf-8")
        original_publish(stage, destination)

    module.atomic_publish_noreplace = substitute_then_publish
    try:
        try:
            module._publish_owned_stage(owned, final, "runner publication substitution regression")
        except module.RunnerError as exc:
            require("substituted directory" in str(exc), f"unexpected publication substitution error: {exc}")
        else:
            raise SmokeError("runner committed a substituted publication tree")
        require(owned.committed is False, "substituted publication was marked committed")
        require((final / "foreign.txt").read_text(encoding="utf-8") == "foreign\n", "foreign publication tree changed")
        owned.cleanup("runner publication substitution cleanup")
        require(not escaped.exists(), "escaped runner-owned publication tree survived cleanup")
        require(final.is_dir(), "owned cleanup deleted the foreign publication tree")
    finally:
        module.atomic_publish_noreplace = original_publish
        owned.close()

    # A durability error after the rename preserves the complete tree but remains an error.
    tool = base / "publish-tool.py"
    target = base / "publish-target"
    tool.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        "if sys.argv[1] == 'version': print('publish-tool 1.0'); raise SystemExit(0)\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    tool.chmod(0o755)
    target.write_bytes(b"target\n")
    spec = base / "publish-error-spec.json"
    output = base / "publish-error-output"
    write_spec(spec, "publish-error-regression", tool, target, ["run"])

    def rename_then_fail(stage: Path, destination: Path) -> None:
        os.rename(stage, destination)
        raise OSError(errno.EIO, "injected durability failure after rename")

    module.atomic_publish_noreplace = rename_then_fail
    try:
        try:
            module.run_campaign(spec, output, None)
        except OSError as exc:
            require(exc.errno == errno.EIO, f"unexpected post-rename error: {exc}")
        else:
            raise SmokeError("post-rename durability error was converted into success")
    finally:
        module.atomic_publish_noreplace = original_publish
    require((output / "publish-error-regression" / "manifest.json").is_file(), "committed result was lost after durability error")

    # A descriptor-open failure immediately after mkdir must remove the partial object.
    create_root = base / "partial-create"
    create_root.mkdir()
    original_open = module.os.open

    def fail_stage_open(path, flags, *args, **kwargs):
        if path == ".partial.staging" and kwargs.get("dir_fd") is not None:
            raise OSError(errno.EIO, "injected stage descriptor failure")
        return original_open(path, flags, *args, **kwargs)

    module.os.open = fail_stage_open
    try:
        try:
            module.OwnedStage.create(create_root, ".partial.staging")
        except OSError as exc:
            require(exc.errno == errno.EIO, f"unexpected partial-create error: {exc}")
        else:
            raise SmokeError("partial stage descriptor failure was not injected")
    finally:
        module.os.open = original_open
    require(not (create_root / ".partial.staging").exists(), "partial staging directory survived creation failure")


def early_stage_signal_case(base: Path) -> None:
    """Reject an interruption at the stage-creation return boundary without residue."""
    base.mkdir()
    module = load_runner("x64lens_p059_runner_early_stage_signal_probe")
    tool = base / "early-tool.py"
    target = base / "target"
    tool.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        "if sys.argv[1] == 'version': print('early-tool 1.0'); raise SystemExit(0)\n"
        "print('unexpected execution')\n",
        encoding="utf-8",
    )
    tool.chmod(0o755)
    target.write_bytes(b"target\n")
    spec = base / "spec.json"
    output = base / "output"
    write_spec(spec, "early-stage-signal-regression", tool, target, ["run"])

    original_create = module.OwnedStage.create.__func__
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def interrupting_create(cls, parent, name, registry=None):
        os.kill(os.getpid(), signal.SIGTERM)
        return original_create(cls, parent, name, registry)

    module.OwnedStage.create = classmethod(interrupting_create)
    module.INTERRUPTED_BY = None
    module.install_signal_handlers()
    try:
        try:
            module.run_campaign(spec, output, None)
        except module.RunnerInterrupted:
            pass
        else:
            raise SmokeError("early stage-creation SIGTERM did not interrupt the runner")
    finally:
        module.OwnedStage.create = classmethod(original_create)
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        module.CREATING_STAGE = False
        module.INTERRUPTED_BY = None

    require(not list(output.glob(".*.staging-*")), "early stage-creation signal left staging residue")
    require(not (output / "early-stage-signal-regression").exists(), "early stage-creation signal published a result")


def interrupt_case(base: Path, repeated: bool) -> None:
    base.mkdir()
    ready = base / "ready"
    tool = base / "interrupt-tool.py"
    tool.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys, time\n"
        "if sys.argv[1] == 'version': print('interrupt-tool 1.0'); raise SystemExit(0)\n"
        "bulk = Path.cwd() / 'bulk'; bulk.mkdir()\n"
        "for index in range(4000): (bulk / f'{index:05d}').write_bytes(b'x')\n"
        f"Path({str(ready)!r}).write_text('ready\\n', encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    tool.chmod(0o755)
    target = base / "target"
    target.write_bytes(b"target\n")
    spec = base / "spec.json"
    write_spec(spec, "repeated-interrupt-regression", tool, target, ["bulk"])
    output = base / "output"
    process = subprocess.Popen(
        [sys.executable, str(RUNNER), "--spec", str(spec), "--output-root", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 20
    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    require(ready.exists(), "interrupt cleanup tool did not become ready")
    os.kill(process.pid, signal.SIGTERM)
    if repeated:
        for _ in range(24):
            time.sleep(0.003)
            if process.poll() is not None:
                break
            os.kill(process.pid, signal.SIGTERM)
    _stdout, stderr = process.communicate(timeout=30)
    require(process.returncode == 143, f"interrupted runner returned {process.returncode}: {stderr}")
    require(not list(output.glob(".*.staging-*")), "interrupted runner left staging residue")
    require(not (output / "repeated-interrupt-regression").exists(), "interrupted runner published a result")


def main() -> int:
    require(RUNNER.is_file() and os.access(RUNNER, os.X_OK), "missing executable diagnostic runner")
    with tempfile.TemporaryDirectory(prefix="x64lens-diagnostic-transaction-smoke-") as raw:
        base = Path(raw)
        assert_future_paths_and_stage_identity(base / "path-and-stage")
        assert_publication_and_partial_create(base / "publication")
        early_stage_signal_case(base / "early-stage-signal")
        interrupt_case(base / "single-interrupt", repeated=False)
        interrupt_case(base / "repeated-interrupt", repeated=True)
    print(
        "diagnostic-transaction-smoke: ok "
        "future_paths=2 stage_identity=1 publish_substitution=1 post_rename_error=1 "
        "partial_create=1 early_stage_signal=1 interruption_cleanup=2"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"diagnostic-transaction-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
