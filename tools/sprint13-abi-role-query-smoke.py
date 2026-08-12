#!/usr/bin/env python3
"""Freeze and validate the private Sprint 13 named ABI-role query contract.

The contract has two independent surfaces:

* 36 source-attested present/absent/unknown role queries, split into 24
  development and 12 source-disjoint confirmation queries; and
* 96 public command closures over 24 controlled ELF64 objects proving that the
  private role lattice remains disabled in text and schema 0.2.0 JSON output.

The tool does not change runtime semantics, scores, schema, or public output.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-abi-role-query-v1.json"
EXPECTED = ROOT / "tests/expected/sprint13-abi-role-query-v1.json"
REGISTERS = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")
REG_TOKENS = tuple(f"REG_{name.upper()}_BIT" for name in REGISTERS)
COMMANDS = ("info", "mitigations", "gadgets_json", "analyze_json")
MAX_OUTPUT = 16 * 1024 * 1024


class QueryError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise QueryError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-abi-role-query-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} shape changed: {sorted(set(value) ^ keys)}")
    return value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_constant(expr: str) -> int:
    expr = expr.strip()
    if expr.startswith("(") and expr.endswith(")"):
        expr = expr[1:-1].strip()
    match = re.fullmatch(r"1\s*<<\s*(\d+)", expr)
    if match:
        return 1 << int(match.group(1))
    if re.fullmatch(r"0x[0-9a-fA-F]+|\d+", expr):
        return int(expr, 0)
    raise QueryError(f"unsupported constant expression: {expr}")


def source_masks(authority: dict[str, Any]) -> dict[str, int]:
    for record in authority["source_authorities"]:
        path = ROOT / record["path"]
        require(path.is_file() and sha256_file(path) == record["sha256"], f"source authority changed: {record['path']}")

    structs = (ROOT / "include/structs.inc").read_text(encoding="utf-8")
    constants: dict[str, int] = {}
    for name, expr in re.findall(r"^%define\s+(CANDIDATE_ROLE_[A-Z0-9_]+)\s+(.+?)\s*$", structs, re.MULTILINE):
        try:
            constants[name] = parse_constant(expr)
        except QueryError:
            continue
    required = {
        "CANDIDATE_ROLE_GENERIC_CONTROL",
        *(f"CANDIDATE_ROLE_SYSV_ARG{i}" for i in range(1, 7)),
        *(f"CANDIDATE_ROLE_SYSCALL_ARG{i}" for i in range(1, 7)),
    }
    require(required <= constants.keys(), "candidate-role constants are incomplete")

    source = (ROOT / "src/candidate_role.asm").read_text(encoding="utf-8")
    ids_text = source.split("pop_pattern_reg_ids:", 1)[1].split("pop_pattern_role_masks:", 1)[0]
    observed_tokens = tuple(re.findall(r"REG_[A-Z0-9]+_BIT", ids_text))
    require(observed_tokens == REG_TOKENS, "candidate-role register order changed")
    masks_text = source.split("pop_pattern_role_masks:", 1)[1].split("section .text", 1)[0]
    expressions = [line.split("dq", 1)[1].strip() for line in masks_text.splitlines() if line.strip().startswith("dq ")]
    require(len(expressions) == 16, "candidate-role mask table denominator changed")
    observed: dict[str, int] = {}
    for register, expression in zip(REGISTERS, expressions, strict=True):
        value = 0
        for term in (part.strip() for part in expression.split("|")):
            value |= constants[term] if term in constants else parse_constant(term)
        observed[register] = value
    expected = {item["register"]: item["mask"] for item in authority["register_masks"]}
    require(observed == expected, "candidate-role source masks disagree with authority")
    return observed


def validate_authority(authority: Any) -> dict[str, Any]:
    exact_keys(authority, {
        "schema", "sprint", "patch", "purpose", "evidence_class",
        "publication_eligible", "register_masks", "queries", "public_closure",
        "contract", "claim_boundary", "source_authorities", "limitations",
    }, "authority")
    require(authority["schema"] == "x64lens-sprint13-abi-role-query-authority-v1", "authority schema changed")
    require(authority["sprint"] == 13 and authority["patch"] == 84, "authority identity changed")
    require(authority["evidence_class"] == "diagnostic" and authority["publication_eligible"] is False, "authority evidence boundary changed")

    masks = authority["register_masks"]
    require(isinstance(masks, list) and len(masks) == 16, "register mask denominator changed")
    require([item["register"] for item in masks] == list(REGISTERS), "register mask ordering changed")
    require(all(type(item["mask"]) is int and item["mask"] >= 0 for item in masks), "register masks must be nonnegative integers")

    queries = authority["queries"]
    require(isinstance(queries, list) and len(queries) == 36, "query denominator changed")
    require(len({item["id"] for item in queries}) == 36, "query IDs are not unique")
    require(sum(item["split"] == "development" for item in queries) == 24, "development query denominator changed")
    require(sum(item["split"] == "confirmation" for item in queries) == 12, "confirmation query denominator changed")
    require({item["expected"] for item in queries} <= {"present", "absent", "unknown"}, "query state vocabulary changed")

    closure = exact_keys(authority["public_closure"], {
        "targets", "commands", "target_count", "command_count",
        "closure_denominator", "forbidden_public_tokens",
    }, "public closure")
    require(closure["commands"] == list(COMMANDS), "public command ordering changed")
    require(closure["target_count"] == 24 and len(closure["targets"]) == 24, "public target denominator changed")
    require(closure["command_count"] == 4 and closure["closure_denominator"] == 96, "public closure denominator changed")
    require(len({item["id"] for item in closure["targets"]}) == 24, "public target IDs are not unique")

    contract = authority["contract"]
    require(contract == {
        "all_16_exact_single_pop_registers": True,
        "confirmation_queries": 12,
        "development_confirmation_disjoint": True,
        "development_queries": 24,
        "linux_syscall_argument_4": "r10",
        "linux_syscall_number": "rax",
        "query_states": ["present", "absent", "unknown"],
        "query_total": 36,
        "stack_pivot": "rsp",
        "sysv_argument_4": "rcx",
    }, "ABI-role contract changed")
    require(authority["claim_boundary"] == {
        "human_blind_claim": False,
        "private_contract_frozen": True,
        "public_fields_added": 0,
        "publication_claim_authorized": False,
        "schema_changed": False,
        "score_changes": 0,
        "semantic_changes": 0,
    }, "ABI-role claim boundary changed")
    require(len(authority["source_authorities"]) == 3, "source authority denominator changed")
    return authority


def evaluate_query(query: dict[str, Any], masks: dict[str, int], bits: dict[str, int]) -> str:
    if query["candidate_state"] == "unknown":
        return "unknown"
    register = query["register"]
    require(register in masks, f"unknown register in query: {query['id']}")
    facet = query["facet"]
    index = query["argument_index"]
    if facet == "generic_control":
        present = bool(masks[register] & bits["CANDIDATE_ROLE_GENERIC_CONTROL"])
    elif facet == "sysv_argument":
        require(type(index) is int and 1 <= index <= 6, f"invalid SysV query index: {query['id']}")
        present = bool(masks[register] & bits[f"CANDIDATE_ROLE_SYSV_ARG{index}"])
    elif facet == "syscall_argument":
        require(type(index) is int and 1 <= index <= 6, f"invalid syscall query index: {query['id']}")
        present = bool(masks[register] & bits[f"CANDIDATE_ROLE_SYSCALL_ARG{index}"])
    elif facet == "syscall_number":
        present = register == "rax"
    elif facet == "stack_pivot":
        present = register == "rsp"
    else:
        raise QueryError(f"unknown query facet: {query['id']}")
    return "present" if present else "absent"


def role_bits() -> dict[str, int]:
    source = (ROOT / "include/structs.inc").read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for name, expr in re.findall(r"^%define\s+(CANDIDATE_ROLE_(?:GENERIC_CONTROL|SYSV_ARG[1-6]|SYSCALL_ARG[1-6]))\s+(.+?)\s*$", source, re.MULTILINE):
        out[name] = parse_constant(expr)
    require(len(out) == 13, "role-bit authority changed")
    return out


def contract_result(authority: dict[str, Any]) -> dict[str, Any]:
    masks = source_masks(authority)
    bits = role_bits()
    states = {"present": 0, "absent": 0, "unknown": 0}
    for query in authority["queries"]:
        observed = evaluate_query(query, masks, bits)
        require(observed == query["expected"], f"query disagrees: {query['id']}: {observed}")
        states[observed] += 1
    result = {
        "schema": "x64lens-sprint13-abi-role-query-result-v1",
        "sprint": 13,
        "patch": 84,
        "registers": 16,
        "queries": 36,
        "development_queries": 24,
        "confirmation_queries": 12,
        "query_states": states,
        "source_masks_attested": 16,
        "sysv_arg4_rcx": True,
        "syscall_arg4_r10": True,
        "syscall_number_rax": True,
        "stack_pivot_rsp": True,
        "public_target_count": 24,
        "public_closure_denominator": 96,
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
        "decision": "private_contract_frozen_public_projection_disabled",
    }
    require(result == load(EXPECTED), "ABI-role contract result differs from expected authority")
    return result


def build_elf(payload: bytes, slot: int) -> bytes:
    size = 512
    offset = 0x100 + (slot % 8) * 16
    require(offset + len(payload) <= size, "controlled payload exceeds ELF")
    base = 0x400000 + slot * 0x10000
    ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\x00" * 7
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 2, 62, 1, base + offset, 64, 0, 0, 64, 56, 1, 64, 0, 0)
    phdr = struct.pack("<IIQQQQQQ", 1, 5, 0, base, base, size, size, 0x1000)
    data = bytearray(size)
    data[:len(header)] = header
    data[64:64 + len(phdr)] = phdr
    data[offset:offset + len(payload)] = payload
    return bytes(data)


def target_payload(record: dict[str, Any]) -> bytes:
    if record["kind"] == "single_pop":
        register = record["register"]
        index = REGISTERS.index(register)
        if index < 8:
            return bytes([0x58 + index, 0xC3])
        return bytes([0x41, 0x58 + (index - 8), 0xC3])
    require(record["kind"] == "bytes", f"unknown target kind: {record['id']}")
    return bytes.fromhex(record["bytes_hex"])


def nested_forbidden(value: Any, tokens: tuple[str, ...]) -> bool:
    if isinstance(value, dict):
        return any(any(token in str(key).lower() for token in tokens) or nested_forbidden(item, tokens) for key, item in value.items())
    if isinstance(value, list):
        return any(nested_forbidden(item, tokens) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(token in lowered for token in tokens)
    return False


def tool_identity(path: Path) -> dict[str, Any]:
    path = path.resolve(strict=True)
    meta = path.stat()
    require(stat.S_ISREG(meta.st_mode) and meta.st_mode & stat.S_IXUSR, "analyzer is not one executable regular file")
    return {"sha256": sha256_file(path), "size_bytes": meta.st_size, "mode": f"{stat.S_IMODE(meta.st_mode):04o}"}


def source_authority(root: Path, manifest_path: Path, expected_tree: str) -> dict[str, Any]:
    require(re.fullmatch(r"[0-9a-f]{40}", expected_tree) is not None, "invalid expected candidate tree")
    helper = load_module("s13_p084_query_gitless", ROOT / "tools/gitless-source-manifest.py")
    manifest = helper.load_manifest(manifest_path.resolve(strict=True))
    helper.verify(root.resolve(strict=True), manifest)
    require(manifest["candidate_tree"] == expected_tree, "ABI-role source tree differs from expected candidate tree")
    return {
        "candidate_tree": expected_tree,
        "source_manifest_sha256": sha256_file(manifest_path.resolve(strict=True)),
        "source_files": len(manifest["files"]),
        "source_directories": len(manifest["directories"]),
        "schema": manifest["schema"],
    }


def run_closures(args: argparse.Namespace, authority: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    analyzer = args.analyzer.resolve(strict=True)
    result_dir = Path(os.path.abspath(args.result_dir))
    require(not result_dir.exists(), "ABI-role result directory already exists")
    source = source_authority(args.source_root, args.source_manifest, args.expected_candidate_tree)
    stage = Path(tempfile.mkdtemp(prefix=f".{result_dir.name}.stage.", dir=result_dir.parent))
    tokens = tuple(authority["public_closure"]["forbidden_public_tokens"])
    closures: list[dict[str, Any]] = []
    try:
        target_root = stage / "targets"
        output_root = stage / "outputs"
        target_root.mkdir(mode=0o755)
        for slot, target in enumerate(authority["public_closure"]["targets"]):
            path = target_root / f"{target['id']}.elf"
            payload = build_elf(target_payload(target), slot)
            path.write_bytes(payload)
            path.chmod(0o444)
            target_sha = hashlib.sha256(payload).hexdigest()
            for command in COMMANDS:
                if command == "info":
                    argv = [os.fspath(analyzer), "info", os.fspath(path)]
                elif command == "mitigations":
                    argv = [os.fspath(analyzer), "mitigations", os.fspath(path)]
                elif command == "gadgets_json":
                    argv = [os.fspath(analyzer), "gadgets", "--format", "json", "--max-depth", "4", os.fspath(path)]
                else:
                    argv = [os.fspath(analyzer), "analyze", "--format", "json", "--max-depth", "4", os.fspath(path)]
                cp = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
                require(cp.returncode == 0, f"public closure failed: {target['id']}/{command}: {cp.stderr[-1000:]!r}")
                require(len(cp.stdout) <= MAX_OUTPUT and len(cp.stderr) <= MAX_OUTPUT, "public closure output exceeded bound")
                if command.endswith("_json"):
                    value = json.loads(cp.stdout, object_pairs_hook=strict_pairs)
                    expected_command = command.removesuffix("_json")
                    require(value.get("schema_version") == "0.2.0" and value.get("command") == expected_command, "public JSON identity changed")
                    require(not nested_forbidden(value, tokens), f"private role projection leaked into JSON: {target['id']}/{command}")
                else:
                    combined = (cp.stdout + b"\n" + cp.stderr).decode("utf-8", "replace").lower()
                    require(not any(token in combined for token in tokens), f"private role projection leaked into text: {target['id']}/{command}")
                out_dir = output_root / target["id"] / command
                out_dir.mkdir(parents=True, mode=0o755)
                (out_dir / "stdout").write_bytes(cp.stdout); (out_dir / "stdout").chmod(0o444)
                (out_dir / "stderr").write_bytes(cp.stderr); (out_dir / "stderr").chmod(0o444)
                closures.append({
                    "target_id": target["id"], "target_sha256": target_sha,
                    "command": command, "exit_code": cp.returncode,
                    "stdout_sha256": hashlib.sha256(cp.stdout).hexdigest(),
                    "stderr_sha256": hashlib.sha256(cp.stderr).hexdigest(),
                })
        require(len(closures) == 96, "public closure denominator changed")
        require(source_authority(args.source_root, args.source_manifest, args.expected_candidate_tree) == source, "ABI-role source authority changed during closures")
        manifest = {
            "schema": "x64lens-sprint13-abi-role-query-evidence-v1",
            "sprint": 13, "patch": 84, "evidence_class": "diagnostic",
            "publication_eligible": False,
            "authority_sha256": sha256_file(args.authority.resolve(strict=True)),
            "expected_sha256": sha256_file(args.expected.resolve(strict=True)),
            "source_authority": source,
            "analyzer": tool_identity(analyzer),
            "query_contract": contract,
            "public_closure_count": len(closures),
            "closures": closures,
            "claim_boundary": authority["claim_boundary"],
        }
        (stage / "manifest.json").write_bytes(canonical(manifest)); (stage / "manifest.json").chmod(0o444)
        lines=[]
        for path in sorted((p for p in stage.rglob("*") if p.is_file()), key=lambda p: os.fsencode(p.relative_to(stage).as_posix())):
            lines.append(f"{sha256_file(path)}  {path.relative_to(stage).as_posix()}\n")
        (stage / "SHA256SUMS.txt").write_text("".join(lines), encoding="utf-8"); (stage / "SHA256SUMS.txt").chmod(0o444)
        os.rename(stage, result_dir)
        stage = result_dir
        return manifest
    finally:
        if stage.exists() and stage != result_dir:
            shutil.rmtree(stage, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("contract", "run"))
    parser.add_argument("--authority", type=Path, default=AUTHORITY)
    parser.add_argument("--expected", type=Path, default=EXPECTED)
    parser.add_argument("--analyzer", type=Path)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--expected-candidate-tree")
    args = parser.parse_args()
    try:
        authority = validate_authority(load(args.authority.resolve(strict=True)))
        contract = contract_result(authority)
        if args.action == "run":
            for name in ("analyzer", "result_dir", "source_root", "source_manifest", "expected_candidate_tree"):
                require(getattr(args, name) is not None, f"--{name.replace('_', '-')} is required for run")
            manifest = run_closures(args, authority, contract)
            require(manifest["public_closure_count"] == 96, "public closure result changed")
        print(
            "sprint13-abi-role-query-smoke: ok queries=36 development=24 confirmation=12 "
            "source_masks=16 sysv_arg4=rcx syscall_arg4=r10 query_states=3 "
            f"public_closures={96 if args.action == 'run' else 'deferred'} "
            "public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0"
        )
    except (OSError, QueryError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
