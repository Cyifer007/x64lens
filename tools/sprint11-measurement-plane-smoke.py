#!/usr/bin/env python3
"""Validate the Patch 059 matched-relation and provenance measurement plane.

The smoke builds a three-role provisional corpus, runs one authenticated
four-tool diagnostic matrix, derives x64lens and baseline relation artifacts,
records runtime closures, and calibrates displayed addresses without creating a
generic gadget count or release-facing result.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"
CORPUS_BUILDER = ROOT / "benchmarks/scripts/build-provisional-corpus.py"
CORPUS_SPEC = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
X_EXTRACTOR = ROOT / "benchmarks/scripts/x64lens-relation-extractor.py"
BASELINE_ADAPTER = ROOT / "benchmarks/scripts/baseline-output-adapter.py"
CLOSURE = ROOT / "benchmarks/scripts/runtime-closure-manifest.py"
CALIBRATOR = ROOT / "benchmarks/scripts/address-coordinate-calibrator.py"
CORPUS_ID = "s11-p059-measurement-plane-smoke-v1"
ROLE_TARGETS = {
    "et_exec": "gcc-o0-exec-nopie-minimal",
    "pie_et_dyn": "gcc-o0-exec-pie-minimal",
    "shared_et_dyn": "gcc-o0-shared-minimal",
}
TOOLS = ("x64lens", "ropgadget", "ropper", "ropr")


class SmokeError(RuntimeError):
    """Raised when the measurement-plane contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def run(argv: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def build_three_role_corpus(base: Path) -> Path:
    spec = json.loads(CORPUS_SPEC.read_text(encoding="utf-8"))
    spec["corpus_id"] = CORPUS_ID
    spec["source"]["path"] = str((ROOT / "benchmarks/corpus/sources/sprint11-provisional-control-flow.c").resolve())
    spec["source"]["license_path"] = str((ROOT / "LICENSE").resolve())
    spec["toolchains"] = [spec["toolchains"][0]]
    spec["optimization_profiles"] = [spec["optimization_profiles"][0]]
    spec["hardening_profiles"] = [spec["hardening_profiles"][0]]
    spec["target_count"] = 3
    spec_path = base / "corpus-spec.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    output = base / "corpus"
    output.mkdir()
    result = run([sys.executable, str(CORPUS_BUILDER), "--spec", str(spec_path), "--output-root", str(output)], timeout=180)
    require(result.returncode == 0, f"three-role corpus build failed: {result.stderr}")
    corpus = output / CORPUS_ID
    verify = run([sys.executable, str(CORPUS_BUILDER), "--verify", str(corpus)], timeout=60)
    require(verify.returncode == 0, f"three-role corpus verification failed: {verify.stderr}")
    return corpus


def write_fake_tool(path: Path, tool_id: str, coordinate_map: dict[str, dict[str, str]]) -> None:
    versions = {
        "x64lens": "x64lens 0.1.0-dev schema 0.2.0",
        "ropgadget": "Version: ROPgadget v1.0",
        "ropper": "Version: Ropper 1.0",
        "ropr": "ropr 1.0",
    }
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import hashlib, json, pathlib, sys\n"
        f"TOOL={tool_id!r}\n"
        f"VERSION={versions[tool_id]!r}\n"
        f"COORD={json.dumps(coordinate_map, sort_keys=True)!r}\n"
        "if (TOOL == 'x64lens' and sys.argv[1:] == ['version']) or (TOOL != 'x64lens' and sys.argv[1:] == ['--version']):\n"
        "    print(VERSION); raise SystemExit(0)\n"
        "if TOOL == 'ropgadget': target = pathlib.Path(sys.argv[sys.argv.index('--binary') + 1])\n"
        "elif TOOL == 'ropper': target = pathlib.Path(sys.argv[sys.argv.index('--file') + 1])\n"
        "else: target = pathlib.Path(sys.argv[-1])\n"
        "digest = hashlib.sha256(target.read_bytes()).hexdigest()\n"
        "entry = json.loads(COORD)[digest]\n"
        "if TOOL == 'x64lens':\n"
        "    report = {\n"
        "      'schema_version':'0.2.0','tool':'x64lens','tool_version':'0.1.0-dev',\n"
        "      'report_type':'analysis','command':'gadgets',\n"
        "      'analysis':{'complete':True,'max_depth':4,'candidate_capacity':4096,'candidate_count':1,'candidate_truncated':False,'candidate_dropped_count':0,'candidate_dropped_count_known':True,'regions_scanned':1,'regions_total':1},\n"
        "      'target':{'path':str(target)},'mitigations':{},\n"
        "      'counts':{'raw_candidate_count':1,'ret_count':1,'ret_imm16_count':0,'exact_pattern_count':1,'semantic_candidate_count':1,'unknown_candidate_count':0,'scored_candidate_count':1},\n"
        "      'primitive_coverage':{'arg_control':True},\n"
        "      'gadgets':[{'va':entry['va_terminator'],'file_offset':entry['offset_terminator'],'section':None,'bytes':'5fc3','terminator':'ret','pattern':'pop rdi; ret','semantic_class':'arg_control','controls':['rdi'],'stack_pop_order':['rdi'],'register_transfer':None,'clobbers':[],'side_effects':['stack_read'],'stack_delta':16,'stack_delta_known':True,'evidence':{'kind':'semantic_exact','raw_candidate':True,'exact_suffix':True,'semantic_source':'exact','validator':'x64lens-exact-suffix','matched_suffix_offset':0,'matched_suffix_length':2,'full_sequence_valid':None},'score':90,'memory_access':None,'architectural_effects':{'registers_read':['rsp'],'registers_written':['rdi','rsp'],'flags_read':[],'flags_written':[],'control_flow':['return'],'stack_base':'entry_rsp','stack_read_count':2,'stack_write_count':0,'first_stack_read_offset':0,'stack_read_stride':8,'stack_offsets_known':True,'model_complete':True}}],\n"
        "      'limitations':['project-generated diagnostic smoke report']\n"
        "    }\n"
        "    print(json.dumps(report, sort_keys=True)); raise SystemExit(0)\n"
        "if TOOL == 'ropgadget': address = entry['va_start']\n"
        "elif TOOL == 'ropper': address = entry['offset_start']\n"
        "else: address = entry['mismatch'] if entry['role'] == 'shared_et_dyn' else entry['va_start']\n"
        "print(f'{address}: pop rdi ; ret')\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def campaign_spec(base: Path, corpus: Path) -> tuple[Path, dict[str, Path]]:
    manifest = json.loads((corpus / "corpus-manifest.json").read_text(encoding="utf-8"))
    targets = {item["id"]: corpus / item["relative_path"] for item in manifest["targets"]}
    coordinate_map: dict[str, dict[str, str]] = {}
    starts = {
        "et_exec": (0x401000, 0x100),
        "pie_et_dyn": (0x1000, 0x180),
        "shared_et_dyn": (0x2000, 0x200),
    }
    for role, target_id in ROLE_TARGETS.items():
        va, offset = starts[role]
        digest = sha256(targets[target_id])
        coordinate_map[digest] = {
            "role": role,
            "va_start": f"0x{va:016x}",
            "va_terminator": f"0x{va + 1:016x}",
            "offset_start": f"0x{offset:016x}",
            "offset_terminator": f"0x{offset + 1:016x}",
            "mismatch": f"0x{0x700000 + len(coordinate_map):016x}",
        }

    tool_dir = base / "tools"
    tool_dir.mkdir()
    tool_paths: dict[str, Path] = {}
    for tool_id in TOOLS:
        path = tool_dir / f"{tool_id}.py"
        write_fake_tool(path, tool_id, coordinate_map)
        tool_paths[tool_id] = path

    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    baseline_by_id = {item["id"]: item for item in authority["baselines"]}
    target_records = []
    for role, target_id in ROLE_TARGETS.items():
        target_records.append({"id": target_id, "path": str(targets[target_id]), "license": "Apache-2.0 generated diagnostic corpus"})
    tools = [
        {"id": "x64lens", "path": str(tool_paths["x64lens"]), "version": "0.1.0-dev", "version_argv": ["{tool}", "version"]},
        {"id": "ropgadget", "path": str(tool_paths["ropgadget"]), "version": "Version: ROPgadget v1.0", "version_argv": ["{tool}", "--version"]},
        {"id": "ropper", "path": str(tool_paths["ropper"]), "version": "Version: Ropper 1.0", "version_argv": ["{tool}", "--version"]},
        {"id": "ropr", "path": str(tool_paths["ropr"]), "version": "ropr 1.0", "version_argv": ["{tool}", "--version"]},
    ]
    conditions: list[dict[str, Any]] = []
    for role, target_id in ROLE_TARGETS.items():
        conditions.append({
            "id": f"x64lens-gadget-json--{target_id}",
            "task_scope": "gadget_report",
            "profile_id": "core-1w",
            "worker_count": 1,
            "tool": "x64lens",
            "target": target_id,
            "argv": ["{tool}", "gadgets", "--format", "json", "--max-depth", "4", "{target}"],
            "extractor": "x64lens_json_0_2",
            "expected_report_command": "gadgets",
            "output_scope": f"matched x64lens relation calibration for {role}",
        })
        for tool_id in TOOLS[1:]:
            baseline = baseline_by_id[tool_id]
            conditions.append({
                "id": f"{baseline['condition_id']}--{target_id}",
                "task_scope": baseline["task_scope"],
                "profile_id": "baseline-native",
                "worker_count": 1,
                "tool": tool_id,
                "target": target_id,
                "argv": ["{tool}" if item == "<tool>" else "{target}" if item == "<target>" else item for item in baseline["command_template"]],
                "extractor": "none",
                "output_scope": f"tool-native exact relation calibration for {role}",
            })
    spec = {
        "schema_version": 2,
        "campaign_id": "s11-p059-measurement-plane-smoke",
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "warmup_runs": 0,
        "measured_runs": 1,
        "timeout_seconds": 10,
        "order_policy": "listed",
        "cache_policy": "uncontrolled",
        "fail_campaign_on_error": True,
        "capture_limits": {"maximum_stdout_bytes": 16777216, "maximum_stderr_bytes": 1048576},
        "environment": {},
        "timer_floor": {"probe": "/bin/true", "runs": 5, "threshold_multiplier": 2},
        "tools": tools,
        "targets": target_records,
        "conditions": conditions,
    }
    path = base / "campaign.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return path, tool_paths


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def invoke(script: Path, args: list[str], expected_prefix: str, timeout: int = 180) -> None:
    result = run([sys.executable, str(script), *args], timeout=timeout)
    require(result.returncode == 0, f"{script.name} failed: {result.stderr}")
    require(result.stdout.startswith(expected_prefix), f"unexpected {script.name} banner: {result.stdout!r}")


def main() -> int:
    for path in (RUNNER, CORPUS_BUILDER, AUTHORITY, X_EXTRACTOR, BASELINE_ADAPTER, CLOSURE, CALIBRATOR):
        require(path.is_file(), f"missing measurement-plane component: {path}")
    local_tmp = ROOT / ".local"
    local_tmp.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="x64lens-sprint11-measurement-plane-", dir=local_tmp) as raw:
        base = Path(raw)
        corpus = build_three_role_corpus(base)
        spec, tool_paths = campaign_spec(base, corpus)
        campaign_output = base / "campaign-output"
        campaign = run([sys.executable, str(RUNNER), "--spec", str(spec), "--output-root", str(campaign_output)], timeout=180)
        require(campaign.returncode == 0, f"measurement-plane campaign failed rc={campaign.returncode}: stdout={campaign.stdout!r} stderr={campaign.stderr!r}")
        result_root = campaign_output / "s11-p059-measurement-plane-smoke"
        rows = read_rows(result_root / "rows.tsv")
        require(len(rows) == 12 and all(row["phase"] == "measured" and row["outcome"] == "success" for row in rows), "measurement-plane campaign row matrix is incomplete")
        row_by_condition = {row["condition_id"]: row for row in rows}

        artifacts_root = base / "artifacts"
        artifacts_root.mkdir()
        calibration_roles: list[dict[str, Any]] = []
        closure_count = 0
        for role, target_id in ROLE_TARGETS.items():
            artifacts: dict[str, str] = {}
            x_condition = f"x64lens-gadget-json--{target_id}"
            x_row = row_by_condition[x_condition]
            x_output = artifacts_root / f"{role}-x64lens.json"
            invoke(X_EXTRACTOR, ["--campaign-result", str(result_root), "--run-id", x_row["run_id"], "--task-authority", str(AUTHORITY), "--output", str(x_output)], "x64lens-relation-extractor: ok")
            x_artifact = json.loads(x_output.read_text(encoding="utf-8"))
            require(x_artifact["metrics"]["canonical_exact_pop_rdi_ret_record_count"] == 1, f"x64lens relation missing for {role}")
            artifacts["x64lens"] = {"path": str(x_output), "campaign_result": str(result_root)}

            for tool_id in TOOLS[1:]:
                base_id = next(item["condition_id"] for item in json.loads(AUTHORITY.read_text())["baselines"] if item["id"] == tool_id)
                row = row_by_condition[f"{base_id}--{target_id}"]
                output = artifacts_root / f"{role}-{tool_id}.json"
                invoke(BASELINE_ADAPTER, ["--campaign-result", str(result_root), "--run-id", row["run_id"], "--task-authority", str(AUTHORITY), "--output", str(output)], "baseline-output-adapter: ok")
                normalized = json.loads(output.read_text(encoding="utf-8"))
                require(normalized["metrics"]["canonical_exact_pop_rdi_ret_record_count"] == 1, f"baseline relation missing: {role}/{tool_id}")
                require("gadget_count" not in json.dumps(normalized), "adapter emitted a generic gadget count")
                artifacts[tool_id] = {"path": str(output), "campaign_result": str(result_root)}
            calibration_roles.append({"id": role, "corpus_target_id": target_id, "artifacts": artifacts})

        # The closure generator must use the retained execution snapshot rather
        # than rereading a mutable source entrypoint after the campaign.
        tool_paths["ropgadget"].write_text("#!/usr/bin/env python3\nraise SystemExit(99)\n", encoding="utf-8")
        tool_paths["ropgadget"].chmod(0o755)

        # Record one runtime closure for every tool from the ET_EXEC rows.
        et_target = ROLE_TARGETS["et_exec"]
        closure_conditions = {
            "x64lens": f"x64lens-gadget-json--{et_target}",
        }
        authority_data = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        for baseline in authority_data["baselines"]:
            closure_conditions[baseline["id"]] = f"{baseline['condition_id']}--{et_target}"
        for tool_id in TOOLS:
            row = row_by_condition[closure_conditions[tool_id]]
            output = artifacts_root / f"closure-{tool_id}.json"
            invoke(CLOSURE, ["--campaign-result", str(result_root), "--run-id", row["run_id"], "--task-authority", str(AUTHORITY), "--output", str(output)], "runtime-closure-manifest: ok", timeout=240)
            closure = json.loads(output.read_text(encoding="utf-8"))
            require(closure["status"] in {"complete", "partial"} and closure["totals"]["runtime_file_count"] > 0, f"runtime closure is empty: {tool_id}")
            require(closure["closure_mode"] == "python_console_entrypoint", f"unexpected fake-tool closure mode: {tool_id}")
            campaign_manifest = json.loads((result_root / "manifest.json").read_text(encoding="utf-8"))
            retained_tool = next(item for item in campaign_manifest["tools"] if item["id"] == tool_id)
            require(closure["campaign"]["tool_sha256"] == retained_tool["sha256"], f"runtime closure did not bind retained snapshot: {tool_id}")
            closure_count += 1

        calibration_spec = base / "calibration-input.json"
        calibration_spec.write_text(json.dumps({"schema_version": 2, "roles": calibration_roles}, indent=2) + "\n", encoding="utf-8")
        calibration_output = artifacts_root / "address-calibration.json"
        invoke(CALIBRATOR, ["--corpus-result", str(corpus), "--input-spec", str(calibration_spec), "--task-authority", str(AUTHORITY), "--output", str(calibration_output)], "address-coordinate-calibrator: ok", timeout=240)
        calibration = json.loads(calibration_output.read_text(encoding="utf-8"))
        require(calibration["tools"]["ropgadget"]["status"] == "virtual_address", "ROPgadget virtual-address calibration failed")
        require(calibration["tools"]["ropper"]["status"] == "file_offset", "Ropper file-offset calibration failed")
        require(calibration["tools"]["ropr"]["status"] == "mismatch", "ropr mismatch control was not retained")

        # Role substitution must fail even when every derived artifact remains checksummed.
        invalid_spec = base / "invalid-calibration-input.json"
        invalid = json.loads(calibration_spec.read_text(encoding="utf-8"))
        invalid["roles"][0]["corpus_target_id"] = ROLE_TARGETS["shared_et_dyn"]
        invalid_spec.write_text(json.dumps(invalid, indent=2) + "\n", encoding="utf-8")
        invalid_result = run([sys.executable, str(CALIBRATOR), "--corpus-result", str(corpus), "--input-spec", str(invalid_spec), "--task-authority", str(AUTHORITY), "--output", str(artifacts_root / "invalid.json")], timeout=120)
        require(invalid_result.returncode == 2 and "does not satisfy role" in invalid_result.stderr, "role-substituted calibration input was accepted")

        # Generator identity and native hashes are insufficient if normalized
        # fields can be forged.  A modified relation must fail reproduction.
        forged_relation = base / "forged-x64lens-relation.json"
        forged = json.loads(Path(calibration_roles[0]["artifacts"]["x64lens"]["path"]).read_text(encoding="utf-8"))
        forged["normalized_relations"][0]["virtual_address_start"] = "0x00000000deadbeef"
        forged_relation.write_text(json.dumps(forged, indent=2) + "\n", encoding="utf-8")
        forged_spec = base / "forged-calibration-input.json"
        forged_input = json.loads(calibration_spec.read_text(encoding="utf-8"))
        forged_input["roles"][0]["artifacts"]["x64lens"]["path"] = str(forged_relation)
        forged_spec.write_text(json.dumps(forged_input, indent=2) + "\n", encoding="utf-8")
        forged_result = run([sys.executable, str(CALIBRATOR), "--corpus-result", str(corpus), "--input-spec", str(forged_spec), "--task-authority", str(AUTHORITY), "--output", str(artifacts_root / "forged.json")], timeout=120)
        require(forged_result.returncode == 2 and "does not reproduce" in forged_result.stderr, "forged normalized relation was accepted")

        # Derived artifacts are no-replace publications.
        x_row = row_by_condition[f"x64lens-gadget-json--{et_target}"]
        overwrite = run([sys.executable, str(X_EXTRACTOR), "--campaign-result", str(result_root), "--run-id", x_row["run_id"], "--task-authority", str(AUTHORITY), "--output", calibration_roles[0]["artifacts"]["x64lens"]["path"]], timeout=60)
        require(overwrite.returncode == 2 and "output already exists" in overwrite.stderr, "relation artifact overwrite was accepted")

    print(
        "sprint11-measurement-plane-smoke: ok "
        "targets=3 runner_rows=12 relation_artifacts=12 runtime_closures=4 "
        "coordinate_roles=3 calibrated_tools=2 mismatch_controls=1 adversarial_cases=3 source_drift=1 forged_relations=1 generic_counts=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"sprint11-measurement-plane-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
