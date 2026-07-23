#!/usr/bin/env python3
"""Record the observed runtime closure of one authenticated diagnostic tool row.

The manifest binds one authenticated measured task row to the retained tool and
target snapshots, the interpreter and Python imports observed on that task path,
and recursively resolved ELF interpreter/DT_NEEDED objects. It is diagnostic
provenance for the named command/profile rather than a universal package claim.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diagnostic_artifact import (  # noqa: E402
    ArtifactError,
    MAX_JSON_BYTES,
    MAX_MEMBER_BYTES,
    atomic_publish_bytes,
    canonical_json_bytes,
    load_authority,
    load_campaign,
    load_regular_path,
    require,
    require_regular_path_identity,
    safe_id,
)

AUTHORITY_SCHEMA = 3
AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
GENERATOR_ID = "x64lens-sprint11-runtime-closure-v1"
ARTIFACT_SCHEMA = 1
MAX_OBSERVED_FILES = 16384
MAX_OBSERVED_BYTES = 1024 * 1024 * 1024
MAX_TRACE_OUTPUT = 32 * 1024 * 1024
MAX_TRACE_SECONDS = 30
NEEDED = re.compile(r"\(NEEDED\).*Shared library: \[([^\]]+)\]")
RPATH = re.compile(r"\((?:RPATH|RUNPATH)\).*Library (?:rpath|runpath): \[([^\]]*)\]")
INTERP = re.compile(r"Requesting program interpreter: ([^\]]+)\]")
ELF_MAGIC = b"\x7fELF"


class ClosureError(ArtifactError):
    """Raised when runtime closure evidence cannot be safely constructed."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-result", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def resolved_regular(path: Path, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    resolved = path.resolve(strict=True)
    data, identity = load_regular_path(resolved, MAX_MEMBER_BYTES, label)
    require(stat.S_ISREG(os.stat(resolved, follow_symlinks=False).st_mode), f"{label} is not regular")
    identity["path_resolved"] = str(resolved)
    return resolved, data, identity


def identity_record(identity: dict[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": identity["path_resolved"],
        "sha256": identity["sha256"],
        "size_bytes": identity["size_bytes"],
        "mode": f"{identity['mode']:04o}",
    }


def parse_shebang(data: bytes) -> list[str] | None:
    first = data.splitlines()[0] if data.splitlines() else b""
    if not first.startswith(b"#!"):
        return None
    try:
        text = first[2:].decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise ClosureError(f"tool shebang is not UTF-8: {exc}") from exc
    parts = text.split()
    require(parts, "tool shebang is empty")
    return parts


def resolve_shebang_interpreter(parts: list[str]) -> tuple[Path, list[str]]:
    executable = Path(parts[0])
    arguments = parts[1:]
    if executable.name == "env":
        require(arguments, "env shebang does not name an interpreter")
        while arguments and arguments[0].startswith("-"):
            require(arguments[0] not in {"-S", "--split-string"}, "split-string env shebang is unsupported")
            arguments = arguments[1:]
        require(arguments, "env shebang does not name an interpreter")
        found = shutil.which(arguments[0])
        require(found is not None, f"shebang interpreter is missing: {arguments[0]}")
        return Path(found).resolve(strict=True), arguments[1:]
    require(executable.is_absolute(), "tool shebang interpreter must be absolute")
    return executable.resolve(strict=True), arguments


def run_bounded(argv: list[str], *, timeout: int = MAX_TRACE_SECONDS) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=SCRIPT_DIR.parents[1],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env={
                "HOME": "/nonexistent",
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "TZ": "UTC",
            },
        )
    except subprocess.TimeoutExpired as exc:
        raise ClosureError(f"closure helper timed out: {argv[0]}") from exc
    require(len(result.stdout) <= MAX_TRACE_OUTPUT and len(result.stderr) <= MAX_TRACE_OUTPUT, "closure helper output exceeded its bound")
    return result


def tracer_source() -> str:
    return r'''
import importlib.metadata as metadata
import json, os, runpy, sys
entry = sys.argv[1]
entry_args = json.loads(sys.argv[2])
sys.argv = [entry, *entry_args]
exit_code = 0
try:
    runpy.run_path(entry, run_name="__main__")
except SystemExit as exc:
    if isinstance(exc.code, int): exit_code = exc.code
    elif exc.code not in (None, 0): exit_code = 1
except BaseException as exc:
    print(json.dumps({"trace_error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
    exit_code = 125
modules = []
for name, module in sorted(sys.modules.items()):
    path = getattr(module, "__file__", None)
    if isinstance(path, str):
        try: resolved = os.path.realpath(path)
        except OSError: continue
        if os.path.isfile(resolved): modules.append({"name": name, "path": resolved})
package_map = metadata.packages_distributions()
distributions = {}
for record in modules:
    root = record["name"].split(".", 1)[0]
    for distribution in package_map.get(root, ()):
        try: version = metadata.version(distribution)
        except metadata.PackageNotFoundError: version = "unknown"
        distributions[distribution] = version
mapped = []
try:
    with open("/proc/self/maps", "r", encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip().split(None, 5)
            if len(fields) == 6 and fields[5].startswith("/"):
                path = os.path.realpath(fields[5])
                if os.path.isfile(path): mapped.append(path)
except OSError:
    pass
print(json.dumps({"exit_code": exit_code, "modules": modules, "distributions": distributions, "mapped_files": sorted(set(mapped))}, sort_keys=True))
raise SystemExit(0)
'''.strip()


def observe_python(
    interpreter: Path,
    entrypoint: Path,
    task_arguments: list[str],
) -> tuple[dict[str, Any], list[Path]]:
    result = run_bounded(
        [str(interpreter), "-c", tracer_source(), str(entrypoint), json.dumps(task_arguments, separators=(",", ":"))]
    )
    require(result.returncode == 0, f"Python closure tracer failed: {result.stderr.decode('utf-8', errors='replace')[:400]}")
    lines = result.stdout.decode("utf-8", errors="strict").splitlines()
    require(lines, "Python closure tracer emitted no result")
    try:
        observed = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise ClosureError(f"Python closure tracer result is invalid JSON: {exc}") from exc
    require(isinstance(observed, dict) and isinstance(observed.get("modules"), list), "Python closure trace is malformed")
    require(observed.get("exit_code") == 0, f"tool task path exited {observed.get('exit_code')} under closure tracing")
    paths: list[Path] = []
    module_records: list[dict[str, str]] = []
    for item in observed["modules"]:
        require(isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("path"), str), "Python module trace entry is invalid")
        path = Path(item["path"])
        if path.is_file():
            resolved = path.resolve(strict=True)
            paths.append(resolved)
            module_records.append({"name": item["name"], "path": str(resolved)})
    mapped: list[str] = []
    for value in observed.get("mapped_files", []):
        if isinstance(value, str) and Path(value).is_file():
            resolved = Path(value).resolve(strict=True)
            paths.append(resolved)
            mapped.append(str(resolved))
    distributions = observed.get("distributions")
    require(isinstance(distributions, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in distributions.items()), "Python distribution trace is invalid")
    return {
        "trace_command": ["{interpreter}", "-c", "<embedded-runtime-closure-tracer>", "{entrypoint}", *task_arguments],
        "observation_scope": "measured_task_command",
        "task_arguments": task_arguments,
        "version_path_exit_code": observed["exit_code"],
        "imported_modules": module_records,
        "distributions": [{"name": name, "version": distributions[name]} for name in sorted(distributions)],
        "mapped_native_files": sorted(set(mapped)),
    }, paths


def readelf_metadata(path: Path, readelf: Path) -> tuple[list[str], list[str], str | None]:
    result = run_bounded([str(readelf), "-W", "-l", "-d", str(path)])
    require(result.returncode == 0, f"readelf failed for runtime object {path}")
    text = result.stdout.decode("utf-8", errors="strict")
    needed = NEEDED.findall(text)
    runpaths: list[str] = []
    for raw in RPATH.findall(text):
        runpaths.extend(item for item in raw.split(":") if item)
    match = INTERP.search(text)
    return needed, runpaths, match.group(1) if match else None


def ldconfig_cache(ldconfig: Path | None) -> dict[str, list[Path]]:
    if ldconfig is None:
        return {}
    result = run_bounded([str(ldconfig), "-p"])
    if result.returncode != 0:
        return {}
    cache: dict[str, list[Path]] = {}
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        if "=>" not in line:
            continue
        left, right = line.split("=>", 1)
        name = left.strip().split()[0] if left.strip() else ""
        path = Path(right.strip())
        if name and path.is_file():
            cache.setdefault(name, []).append(path.resolve(strict=True))
    return cache


def resolve_needed(name: str, origin: Path, runpaths: list[str], cache: dict[str, list[Path]]) -> Path | None:
    candidates: list[Path] = []
    for raw in runpaths:
        expanded = raw.replace("$ORIGIN", str(origin)).replace("${ORIGIN}", str(origin))
        candidates.append(Path(expanded) / name)
    candidates.extend(cache.get(name, []))
    for directory in (Path("/lib64"), Path("/lib/x86_64-linux-gnu"), Path("/usr/lib/x86_64-linux-gnu"), Path("/usr/lib64"), Path("/lib"), Path("/usr/lib")):
        candidates.append(directory / name)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.resolve(strict=True)
        except OSError:
            continue
    return None


def elf_closure(seeds: Iterable[Path], readelf: Path, ldconfig: Path | None) -> tuple[list[Path], list[dict[str, Any]], list[str]]:
    cache = ldconfig_cache(ldconfig)
    queue = [path.resolve(strict=True) for path in seeds]
    observed: set[Path] = set()
    objects: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    while queue:
        path = queue.pop(0)
        if path in observed:
            continue
        try:
            with path.open("rb") as handle:
                magic = handle.read(4)
        except OSError:
            continue
        if magic != ELF_MAGIC:
            continue
        observed.add(path)
        needed, runpaths, interpreter = readelf_metadata(path, readelf)
        resolved_needed: list[str] = []
        if interpreter:
            interpreter_path = Path(interpreter)
            if interpreter_path.is_file():
                resolved = interpreter_path.resolve(strict=True)
                resolved_needed.append(str(resolved))
                queue.append(resolved)
            else:
                unresolved.add(interpreter)
        for name in needed:
            resolved = resolve_needed(name, path.parent, runpaths, cache)
            if resolved is None:
                unresolved.add(name)
            else:
                resolved_needed.append(str(resolved))
                queue.append(resolved)
        objects.append({
            "path": str(path),
            "needed_names": needed,
            "runpaths": runpaths,
            "resolved_dependencies": sorted(set(resolved_needed)),
        })
        require(len(observed) + len(queue) <= MAX_OBSERVED_FILES, "native runtime closure exceeds file-count bound")
    return sorted(observed), sorted(objects, key=lambda item: item["path"]), sorted(unresolved)


def task_arguments_from_row(context: Any, row: dict[str, str], tool: dict[str, Any], target: dict[str, Any]) -> list[str]:
    """Reconstruct the retained task argv from the authenticated runner row."""
    try:
        command = json.loads(row["command_json"])
    except json.JSONDecodeError as exc:
        raise ClosureError(f"runner row command is invalid JSON: {exc}") from exc
    require(isinstance(command, list) and command and all(isinstance(item, str) and item for item in command), "runner row command is invalid")
    cwd = context.root.joinpath(*Path(row["command_cwd"]).parts).resolve(strict=True)
    tool_snapshot = context.root.joinpath(*Path(tool["snapshot_path"]).parts).resolve(strict=True)
    target_snapshot = context.root.joinpath(*Path(target["snapshot_path"]).parts).resolve(strict=True)

    def resolved_argument(value: str) -> Path | None:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        try:
            return candidate.resolve(strict=True)
        except OSError:
            return None

    require(resolved_argument(command[0]) == tool_snapshot, "runner row task command is not bound to the retained tool snapshot")
    output: list[str] = []
    target_references = 0
    for value in command[1:]:
        resolved = resolved_argument(value)
        if resolved == target_snapshot:
            output.append(str(target_snapshot))
            target_references += 1
        else:
            output.append(value)
    require(target_references == 1, "runner row task command must reference the retained target exactly once")
    return output


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    safe_id(args.run_id, "run id")
    authority, authority_identity, _ = load_authority(args.task_authority, schema_version=AUTHORITY_SCHEMA, authority_id=AUTHORITY_ID)
    policy = authority.get("runtime_closure_policy")
    require(isinstance(policy, dict), "runtime closure policy is missing")
    require(policy.get("generator_id") == GENERATOR_ID and policy.get("artifact_schema_version") == ARTIFACT_SCHEMA, "runtime closure authority changed")
    repository_root = Path(os.path.abspath(args.task_authority)).parent.parent.parent
    generator_path = Path(__file__).resolve(strict=True)
    require(generator_path == (repository_root / policy["generator_path"]).resolve(strict=True), "running closure generator does not match authority path")
    _generator_data, generator_identity = load_regular_path(
        generator_path, MAX_MEMBER_BYTES, "runtime closure generator"
    )

    context = load_campaign(args.campaign_result)
    external_identities: list[tuple[Path, dict[str, Any], str]] = []
    try:
        row = context.row(args.run_id)
        require(row.get("phase") == "measured", "runtime closure requires a measured runner row")
        require(row.get("process_outcome") == "success" and row.get("outcome") == "success", "runtime closure requires a successful runner row")
        tool = context.tools[row["tool_id"]]
        row_stdout_data, row_stdout_identity = context.load_row_member(row, "stdout")
        row_stderr_data, row_stderr_identity = context.load_row_member(row, "stderr")
        del row_stdout_data, row_stderr_data
        # Load the retained executable and version streams through the campaign root.
        from diagnostic_artifact import load_member
        tool_data, tool_snapshot_identity = load_member(context.root_fd, context.root, tool["snapshot_path"], MAX_MEMBER_BYTES, "tool snapshot")
        version_stdout_data, version_stdout_identity = load_member(
            context.root_fd, context.root, tool["version_stdout_path"], MAX_MEMBER_BYTES, "tool version stdout"
        )
        version_stderr_data, version_stderr_identity = load_member(
            context.root_fd, context.root, tool["version_stderr_path"], MAX_MEMBER_BYTES, "tool version stderr"
        )
        del version_stdout_data, version_stderr_data
        shebang = parse_shebang(tool_data)
        closure_mode = "native_elf"
        observation: dict[str, Any] = {}
        seed_paths: list[Path] = []
        entrypoint_for_trace = context.root / tool["snapshot_path"]
        target = context.targets[row["target_id"]]
        task_arguments = task_arguments_from_row(context, row, tool, target)
        observed_python_paths: list[Path] = []

        if shebang is not None:
            interpreter, shebang_arguments = resolve_shebang_interpreter(shebang)
            interpreter, _interpreter_data, interpreter_identity = resolved_regular(interpreter, "tool interpreter")
            external_identities.append((interpreter, interpreter_identity, "tool interpreter"))
            seed_paths.append(interpreter)
            if "python" in interpreter.name.lower():
                closure_mode = "python_console_entrypoint"
                observation, imported_paths = observe_python(interpreter, entrypoint_for_trace, task_arguments)
                observation["shebang_arguments"] = shebang_arguments
                observed_python_paths.extend(imported_paths)
                seed_paths.extend(imported_paths)
            else:
                closure_mode = "script_interpreter"
                observation = {
                    "observation_scope": "measured_task_command",
                    "shebang_arguments": shebang_arguments,
                    "task_arguments": task_arguments,
                    "trace_status": "interpreter_import_observation_unavailable",
                }
        else:
            require(tool_data.startswith(ELF_MAGIC), "tool snapshot is neither an ELF object nor a supported script")
            # Native closure authority is always the retained campaign snapshot.
            # The mutable pre-snapshot source path is descriptive lineage only.
            seed_paths.append(entrypoint_for_trace)
            observation = {
                "observation_scope": "retained_native_task_entrypoint",
                "task_arguments": task_arguments,
            }

        readelf_value = shutil.which("readelf")
        require(readelf_value is not None, "readelf is required for runtime closure")
        readelf, _readelf_data, readelf_identity = resolved_regular(Path(readelf_value), "readelf")
        external_identities.append((readelf, readelf_identity, "readelf"))
        ldconfig_value = shutil.which("ldconfig") or ("/sbin/ldconfig" if Path("/sbin/ldconfig").is_file() else None)
        ldconfig: Path | None = None
        ldconfig_identity: dict[str, Any] | None = None
        if ldconfig_value:
            ldconfig, _ldconfig_data, ldconfig_identity = resolved_regular(Path(ldconfig_value), "ldconfig")
            external_identities.append((ldconfig, ldconfig_identity, "ldconfig"))
        native_paths, native_graph, unresolved = elf_closure(seed_paths, readelf, ldconfig)

        file_records: list[dict[str, Any]] = []
        total_bytes = 0
        seen: set[Path] = set()
        for path in [*(item[0] for item in external_identities), *observed_python_paths, *native_paths]:
            resolved = path.resolve(strict=True)
            if resolved in seen:
                continue
            seen.add(resolved)
            data, identity = load_regular_path(resolved, MAX_MEMBER_BYTES, f"runtime closure file {resolved}")
            total_bytes += len(data)
            require(len(seen) <= MAX_OBSERVED_FILES and total_bytes <= MAX_OBSERVED_BYTES, "runtime closure exceeds retained bounds")
            external_identities.append((resolved, identity, f"runtime closure file {resolved}"))
            file_records.append(identity_record(identity, role="runtime_object"))
        file_records.sort(key=lambda item: item["path"])

        complete = not unresolved
        artifact = {
            "schema_version": ARTIFACT_SCHEMA,
            "artifact_id": GENERATOR_ID,
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "campaign": {
                "campaign_id": context.manifest["campaign_id"],
                "manifest_sha256": context.manifest_identity["sha256"],
                "rows_sha256": context.rows_identity["sha256"],
                "run_id": row["run_id"],
                "phase": row["phase"],
                "condition_id": row["condition_id"],
                "tool_id": row["tool_id"],
                "tool_sha256": row["tool_sha256"],
                "command_json": row["command_json"],
                "command_cwd": row["command_cwd"],
                "target_id": row["target_id"],
                "target_sha256": row["target_sha256"],
            },
            "generator": {"id": GENERATOR_ID, "sha256": generator_identity["sha256"], "size_bytes": generator_identity["size_bytes"]},
            "authority": {"id": AUTHORITY_ID, "sha256": authority_identity["sha256"], "size_bytes": authority_identity["size_bytes"]},
            "closure_mode": closure_mode,
            "status": "complete" if complete else "partial",
            "entrypoint": {
                "snapshot_path": tool["snapshot_path"],
                "snapshot_sha256": tool_snapshot_identity["sha256"],
                "source_path_resolved_descriptive": tool.get("source_path_resolved"),
                "declared_version": tool["version"],
                "observed_version": tool["version_observed"],
            },
            "observation": observation,
            "runtime_files": file_records,
            "native_dependency_graph": native_graph,
            "unresolved_dependencies": unresolved,
            "totals": {"runtime_file_count": len(file_records), "runtime_bytes": total_bytes, "unresolved_dependency_count": len(unresolved)},
            "claim_boundaries": [
                "The Python closure is observed on the authenticated measured task-command path for this row and profile.",
                "The native closure records bounded PT_INTERP and DT_NEEDED resolution; unresolved names remain explicit.",
                "The manifest authenticates runtime support objects but does not make them x64lens runtime dependencies.",
            ],
        }

        selected = [
            (row["stdout_path"], row_stdout_identity, int(row["stdout_limit_bytes"]), f"row {row['run_id']} stdout"),
            (row["stderr_path"], row_stderr_identity, int(row["stderr_limit_bytes"]), f"row {row['run_id']} stderr"),
            (tool["snapshot_path"], tool_snapshot_identity, MAX_MEMBER_BYTES, "tool snapshot"),
            (tool["version_stdout_path"], version_stdout_identity, MAX_MEMBER_BYTES, "tool version stdout"),
            (tool["version_stderr_path"], version_stderr_identity, MAX_MEMBER_BYTES, "tool version stderr"),
            (target["snapshot_path"], load_member(context.root_fd, context.root, target["snapshot_path"], MAX_MEMBER_BYTES, "target snapshot")[1], MAX_MEMBER_BYTES, "target snapshot"),
        ]

        def reauthenticate() -> None:
            context.reauthenticate(selected)
            require_regular_path_identity(args.task_authority, authority_identity, MAX_JSON_BYTES, "task authority")
            require_regular_path_identity(generator_path, generator_identity, MAX_MEMBER_BYTES, "runtime closure generator")
            dedup: set[tuple[int, int]] = set()
            for path, identity, label in external_identities:
                key = (identity["device"], identity["inode"])
                if key in dedup:
                    continue
                dedup.add(key)
                require_regular_path_identity(path, identity, MAX_MEMBER_BYTES, label)

        atomic_publish_bytes(args.output, canonical_json_bytes(artifact), reauthenticate=reauthenticate)
    finally:
        context.close()
    print(
        "runtime-closure-manifest: ok "
        f"run={args.run_id} status={artifact['status']} files={artifact['totals']['runtime_file_count']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ArtifactError, ClosureError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"runtime-closure-manifest: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
