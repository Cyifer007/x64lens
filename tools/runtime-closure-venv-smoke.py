#!/usr/bin/env python3
"""Prove task-path runtime closure preserves a pipx/venv launcher context.

The regression creates an offline Python virtual environment, places one marker
module in its site-packages directory, and runs a console-entrypoint-compatible
probe through the diagnostic runner.  The closure generator must execute the
venv launcher pathname rather than its resolved system-Python target, retain the
marker import, and report the venv prefix.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"
CLOSURE = ROOT / "benchmarks/scripts/runtime-closure-manifest.py"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def run(argv: list[str], cwd: Path = ROOT, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def main() -> int:
    require(RUNNER.is_file() and CLOSURE.is_file() and AUTHORITY.is_file(), "runtime-closure smoke prerequisites are missing")
    with tempfile.TemporaryDirectory(prefix="x64lens-runtime-closure-venv-") as raw:
        root = Path(raw)
        venv = root / "venv"
        created = run([sys.executable, "-m", "venv", "--without-pip", str(venv)], cwd=root)
        require(created.returncode == 0, f"cannot create offline venv: {created.stderr}")
        python = venv / "bin/python"
        require(python.exists(), "venv Python launcher is missing")
        version = run([str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], cwd=root)
        require(version.returncode == 0, f"cannot resolve venv site-packages: {version.stderr}")
        site = Path(version.stdout.strip())
        site.mkdir(parents=True, exist_ok=True)
        (site / "x64lens_venv_marker.py").write_text("VALUE = 'venv-context-preserved'\n", encoding="utf-8")

        tool = root / "ROPgadget"
        tool.write_text(
            f"#!{python}\n"
            "import sys\n"
            "import x64lens_venv_marker\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('Version:        ROPgadget v7.7')\n"
            "    raise SystemExit(0)\n"
            "print('0x0000000000401000 : pop rdi ; ret')\n",
            encoding="utf-8",
        )
        tool.chmod(0o755)
        target = root / "target.elf"
        target.write_bytes(b"\x7fELFvenv-closure\n")
        spec = root / "spec.json"
        spec.write_text(json.dumps({
            "schema_version": 2,
            "campaign_id": "runtime-closure-venv-smoke",
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "warmup_runs": 0,
            "measured_runs": 1,
            "timeout_seconds": 10,
            "order_policy": "listed",
            "cache_policy": "uncontrolled",
            "fail_campaign_on_error": True,
            "capture_limits": {"maximum_stdout_bytes": 65536, "maximum_stderr_bytes": 65536},
            "environment": {},
            "timer_floor": {"probe": "/usr/bin/true", "runs": 5, "threshold_multiplier": 2},
            "tools": [{
                "id": "ropgadget",
                "path": str(tool),
                "version": "Version:        ROPgadget v7.7",
                "version_argv": ["{tool}", "--version"],
            }],
            "targets": [{"id": "target", "path": str(target), "license": "project-generated probe"}],
            "conditions": [{
                "id": "ropgadget-rop-report--target",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "ropgadget",
                "target": "target",
                "argv": ["{tool}", "--binary", "{target}", "--depth", "5", "--only", "pop|ret", "--nojop", "--nosys"],
                "extractor": "none",
                "output_scope": "controlled pipx-style baseline output",
            }],
        }, indent=2) + "\n", encoding="utf-8")
        results = root / "results"
        runner = run([sys.executable, str(RUNNER), "--spec", str(spec), "--output-root", str(results)])
        require(runner.returncode == 0, f"runner failed: {runner.stderr}")
        campaign = results / "runtime-closure-venv-smoke"
        with (campaign / "rows.tsv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        require(len(rows) == 1 and rows[0]["process_outcome"] == "success", "controlled runner row is not successful")
        output = root / "closure.json"
        closure = run([
            sys.executable, str(CLOSURE),
            "--campaign-result", str(campaign),
            "--run-id", rows[0]["run_id"],
            "--task-authority", str(AUTHORITY),
            "--output", str(output),
        ])
        require(closure.returncode == 0, f"runtime closure failed: {closure.stderr}")
        artifact = json.loads(output.read_text(encoding="utf-8"))
        require(artifact["status"] == "complete", f"venv closure is not complete: {artifact['status']}")
        observation = artifact["observation"]
        require(Path(observation["sys_prefix"]) == venv, f"venv sys.prefix was lost: {observation.get('sys_prefix')}")
        require(observation["sys_prefix"] != observation["sys_base_prefix"], "venv and base prefixes were collapsed")
        imported = {item["name"] for item in observation["imported_modules"]}
        require("x64lens_venv_marker" in imported, "venv-only marker module was not observed")
        launcher = observation["interpreter_launcher"]
        require(Path(launcher["path"]) == python, "venv launcher pathname was not retained")
        require(launcher["kind"] in {"symlink", "regular"}, "launcher kind is invalid")
        encoded = output.read_text(encoding="utf-8")
        require(".staging" not in encoded, "published closure retained a stale staging pathname")

    print("runtime-closure-venv-smoke: ok launcher_context=1 venv_import=1 closure_complete=1 stale_paths=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"runtime-closure-venv-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
