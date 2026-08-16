#!/usr/bin/env python3
"""Run the bounded P088 two-build split-debug packaging experiment."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
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
import zlib

AUTH_SCHEMA = "x64lens-sprint13-split-debug-packaging-v1"
RESULT_SCHEMA = "x64lens-sprint13-split-debug-packaging-result-v1"
MAX_JSON = 8 * 1024 * 1024
MAX_STREAM = 16 * 1024 * 1024
LOCAL_PREFIXES = (b"/tmp/", b"/home/", b"/mnt/")


class SplitDebugError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SplitDebugError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-split-debug-packaging-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    raw = path.read_bytes()
    require(len(raw) <= MAX_JSON, f"JSON exceeds bound: {path}")
    return json.loads(raw, object_pairs_hook=strict)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(raw: str) -> str:
    require(isinstance(raw, str) and raw, "empty path")
    path = PurePosixPath(raw)
    require(not path.is_absolute() and "\\" not in raw and ".." not in path.parts, f"unsafe path: {raw!r}")
    require(path.as_posix() == raw, f"noncanonical path: {raw!r}")
    return raw


def resolve_tool(raw: str) -> Path:
    candidate = Path(raw)
    if "/" not in raw:
        value = shutil.which(raw)
        require(value is not None, f"required tool unavailable: {raw}")
        candidate = Path(value)
    candidate = candidate.resolve(strict=True)
    st = candidate.stat()
    require(stat.S_ISREG(st.st_mode) and os.access(candidate, os.X_OK), f"tool is not executable: {candidate}")
    return candidate


def run(argv: list[str], *, cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, check=False, timeout=timeout)
    require(len(cp.stdout) <= MAX_STREAM and len(cp.stderr) <= MAX_STREAM, "command output exceeded bound")
    return cp


def tool_record(path: Path, version_args: list[str]) -> dict[str, Any]:
    cp = run([os.fspath(path), *version_args], cwd=path.parent)
    require(cp.returncode == 0, f"tool version command failed: {path}")
    return {"sha256": sha(path), "size_bytes": path.stat().st_size,
            "version_sha256": sha_bytes(cp.stdout + cp.stderr)}


def verify_member(root: Path, record: dict[str, Any], executable: bool) -> Path:
    path = root / safe_rel(record["path"])
    st = os.lstat(path)
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, f"unsafe producer member: {record['path']}")
    require(st.st_size == record["size_bytes"] and sha(path) == record["sha256"],
            f"producer member bytes changed: {record['path']}")
    require(f"{stat.S_IMODE(st.st_mode):04o}" == record["mode"], f"producer member mode changed: {record['path']}")
    require(bool(st.st_mode & 0o111) == executable, f"producer member executable state changed: {record['path']}")
    return path


def validate_authority(authority: dict[str, Any], expected: dict[str, Any]) -> None:
    require(authority.get("schema") == AUTH_SCHEMA and authority.get("sprint") == 13 and authority.get("patch") == 88,
            "authority identity changed")
    require(authority.get("experiment_id") == expected.get("experiment_id"), "experiment identity changed")
    require(authority.get("evidence_class") == "diagnostic" and authority.get("publication_eligible") is False
            and authority.get("product_adoption_authorized") is False, "evidence boundary changed")
    require(authority.get("builds") == expected.get("builds") == 2, "build denominator changed")
    profiles = authority.get("behavior_profiles")
    require(isinstance(profiles, list) and len(profiles) == expected.get("behavior_profiles") == 15,
            "behavior profile denominator changed")
    require(len({x["id"] for x in profiles}) == 15, "behavior profile IDs are not unique")
    den = authority.get("required_denominators")
    for key in ("behavior_executions", "behavior_pairs", "companion_controls", "symbol_resolutions"):
        require(den.get(key) == expected.get(key), f"denominator changed: {key}")
    require(len(authority.get("known_symbols", [])) == 6, "symbol denominator changed")
    require(len(authority.get("companion_controls", [])) == 8, "control denominator changed")
    require(authority["packaging"]["minimum_runtime_size_reduction"] == expected["minimum_runtime_size_reduction"] == 0.5,
            "size threshold changed")
    require(authority["packaging"]["build_id_policy"] == "must_be_absent_for_current_experiment",
            "build-ID policy changed")
    public = authority["public_boundary"]
    require(public == {"public_fields_added": 0, "runtime_product_adoption": False,
                       "schema_changed": False, "score_changes": 0, "semantic_changes": 0},
            "public boundary changed")


def elf_sections(path: Path) -> dict[str, tuple[int, int]]:
    data = path.read_bytes()
    require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01", f"unsupported ELF: {path}")
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    entsize = struct.unpack_from("<H", data, 0x3A)[0]
    count = struct.unpack_from("<H", data, 0x3C)[0]
    names_index = struct.unpack_from("<H", data, 0x3E)[0]
    require(entsize >= 64 and count > 0 and names_index < count, "unsupported section table")
    require(shoff <= len(data) and count <= (len(data) - shoff) // entsize, "section table out of range")
    names_entry = shoff + names_index * entsize
    names_off = struct.unpack_from("<Q", data, names_entry + 0x18)[0]
    names_size = struct.unpack_from("<Q", data, names_entry + 0x20)[0]
    require(names_off <= len(data) and names_size <= len(data) - names_off, "section names out of range")
    names = data[names_off:names_off + names_size]
    out: dict[str, tuple[int, int]] = {}
    for index in range(count):
        entry = shoff + index * entsize
        name_offset = struct.unpack_from("<I", data, entry)[0]
        section_type = struct.unpack_from("<I", data, entry + 4)[0]
        offset = struct.unpack_from("<Q", data, entry + 0x18)[0]
        size = struct.unpack_from("<Q", data, entry + 0x20)[0]
        require(name_offset < len(names), "section name offset out of range")
        end = names.find(b"\0", name_offset)
        require(end >= 0, "unterminated section name")
        name = names[name_offset:end].decode("ascii", "strict")
        if section_type != 8:  # SHT_NOBITS
            require(offset <= len(data) and size <= len(data) - offset, f"section out of range: {name}")
            out[name] = (offset, size)
        else:
            out[name] = (offset, 0)
    return out


def parse_debuglink(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    offset, size = elf_sections(path)[".gnu_debuglink"]
    payload = data[offset:offset + size]
    end = payload.find(b"\0")
    require(end > 0, "malformed debuglink filename")
    crc_offset = (end + 4) & ~3
    require(crc_offset + 4 <= len(payload), "malformed debuglink CRC")
    return payload[:end].decode("ascii"), struct.unpack_from("<I", payload, crc_offset)[0]


def redact_paths(path: Path) -> int:
    data = bytearray(path.read_bytes())
    token = b"/x64lens/p088/redacted"
    count = 0
    for match in list(re.finditer(rb"[ -~]{4,}", data)):
        value = bytes(match.group())
        if any(prefix in value for prefix in LOCAL_PREFIXES):
            require(len(value) >= len(token), "path string shorter than redaction token")
            data[match.start():match.end()] = token + b"x" * (len(value) - len(token))
            count += 1
    path.write_bytes(data)
    require(not any(prefix in data for prefix in LOCAL_PREFIXES), "local path remained after redaction")
    return count


def package_once(analyzer: Path, destination: Path, objcopy: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, mode=0o755)
    original = destination / "original.debug"
    debug = destination / "x64lens.debug"
    core = destination / "runtime.core"
    runtime = destination / "x64lens"
    cp = run([os.fspath(objcopy), "--only-keep-debug", os.fspath(analyzer), os.fspath(debug)], cwd=destination)
    require(cp.returncode == 0, "objcopy --only-keep-debug failed")
    shutil.copyfile(debug, original)
    redactions = redact_paths(debug)
    shutil.copyfile(analyzer, core)
    cp = run([os.fspath(objcopy), "--strip-all", os.fspath(core)], cwd=destination)
    require(cp.returncode == 0, "objcopy --strip-all failed")
    shutil.copyfile(core, runtime)
    cp = run([os.fspath(objcopy), "--add-gnu-debuglink=x64lens.debug", "x64lens"], cwd=destination)
    require(cp.returncode == 0, "objcopy --add-gnu-debuglink failed")
    runtime.chmod(0o755); core.chmod(0o755); debug.chmod(0o644); original.chmod(0o644)
    name, crc = parse_debuglink(runtime)
    require(name == "x64lens.debug" and crc == (zlib.crc32(debug.read_bytes()) & 0xffffffff),
            "debuglink filename/CRC mismatch")
    require(".gnu_debuglink" not in elf_sections(core), "runtime core already has debuglink")
    require(".note.gnu.build-id" not in elf_sections(analyzer), "unexpected GNU build ID")
    require(not any(prefix in runtime.read_bytes() + debug.read_bytes() for prefix in LOCAL_PREFIXES),
            "packaged output leaks a local path")
    return {"runtime": runtime, "debug": debug, "core": core, "original": original,
            "crc": crc, "redactions": redactions}


def symbol_addresses(analyzer: Path, nm: Path, symbols: list[str], cwd: Path) -> dict[str, str]:
    cp = run([os.fspath(nm), "-n", "--defined-only", os.fspath(analyzer)], cwd=cwd)
    require(cp.returncode == 0, "nm failed")
    found: dict[str, str] = {}
    for line in cp.stdout.decode("utf-8", "strict").splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[-1] in symbols:
            found[fields[-1]] = "0x" + fields[0]
    require(set(found) == set(symbols), "known symbol set changed")
    return found


def resolve(addr2line: Path, cwd: Path, runtime: str, address: str) -> tuple[str, str]:
    cp = run([os.fspath(addr2line), "-f", "-e", runtime, address], cwd=cwd)
    require(cp.returncode == 0, "addr2line failed")
    lines = cp.stdout.decode("utf-8", "replace").splitlines()
    require(len(lines) >= 2, "addr2line output incomplete")
    return lines[0], lines[1]


def write_file(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data); path.chmod(mode)
    return {"sha256": sha_bytes(data), "size_bytes": len(data), "mode": f"{mode:04o}"}


def behavior(authority: dict[str, Any], build: int, unstripped: Path, runtime: Path,
             effects_source: Path, pairs_source: Path, retained: Path) -> tuple[int, int]:
    work = runtime.parent
    effects = work / "effects"; pairs = work / "pairs"
    shutil.copyfile(effects_source, effects); shutil.copyfile(pairs_source, pairs)
    effects.chmod(0o444); pairs.chmod(0o444)
    targets = {"effects": effects.name, "pairs": pairs.name}
    executions = pairs_count = 0
    rows = []
    for profile in authority["behavior_profiles"]:
        args = list(profile["args"])
        if profile["target"] is not None:
            args.append(targets[profile["target"]])
        observed = {}
        for variant, binary in (("unstripped", unstripped), ("runtime", runtime)):
            cp = run([os.fspath(binary), *args], cwd=work)
            observed[variant] = cp
            root = retained / "raw" / profile["id"]
            stdout = write_file(root / f"{variant}.stdout", cp.stdout, 0o444)
            stderr = write_file(root / f"{variant}.stderr", cp.stderr, 0o444)
            rows.append({"profile": profile["id"], "variant": variant, "args": args,
                         "exit_code": cp.returncode, "stdout": stdout, "stderr": stderr})
            executions += 1
        require(observed["unstripped"].returncode == observed["runtime"].returncode
                and observed["unstripped"].stdout == observed["runtime"].stdout
                and observed["unstripped"].stderr == observed["runtime"].stderr,
                f"behavior closure mismatch: build {build}/{profile['id']}")
        pairs_count += 1
    write_file(retained / "behavior.json", canonical(rows), 0o444)
    return executions, pairs_count


def rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    require(function is not None, "renameat2 unavailable")
    rc = function(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if rc != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), os.fspath(destination))


def checksums(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            rows.append(f"{sha(path)}  {path.relative_to(root).as_posix()}")
    write_file(root / "SHA256SUMS.txt", ("\n".join(rows) + "\n").encode(), 0o444)


def validate_result(result: dict[str, Any], expected: dict[str, Any], tree: str) -> None:
    require(result.get("schema") == RESULT_SCHEMA and result.get("source_candidate_tree") == tree,
            "result identity changed")
    summary = result.get("summary", {})
    for key in ("builds", "behavior_executions", "behavior_pairs", "companion_controls",
                "symbol_resolutions", "local_path_leaks"):
        require(summary.get(key) == expected.get(key), f"result denominator changed: {key}")
    require(summary.get("minimum_runtime_size_reduction", 0) >= expected["minimum_runtime_size_reduction"],
            "runtime reduction below threshold")
    require(summary.get("build_id_present") is False
            and summary.get("runtime_bytes_equal_between_builds") is True
            and summary.get("companion_bytes_equal_between_builds") is True, "packaging equivalence changed")
    require(result.get("public_boundary") == {"public_fields_added":0,"runtime_product_adoption":False,
            "schema_changed":False,"score_changes":0,"semantic_changes":0}, "public boundary changed")


def run_experiment(authority_path: Path, expected_path: Path, producer_root: Path,
                   producer_manifest_path: Path, result_dir: Path, source_tree: str,
                   objcopy_raw: str, nm_raw: str, addr2line_raw: str) -> dict[str, Any]:
    authority = load(authority_path); expected = load(expected_path)
    validate_authority(authority, expected)
    producer = load(producer_manifest_path)
    require(producer.get("schema") == "x64lens-sprint13-producer-authority-v1"
            and producer.get("source_candidate_tree") == source_tree, "producer authority mismatch")
    generations = producer.get("generations")
    require(isinstance(generations, list) and len(generations) >= 2, "two independent builds required")
    require(not result_dir.exists(), "result already exists")
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    objcopy = resolve_tool(objcopy_raw); nm = resolve_tool(nm_raw); addr2line = resolve_tool(addr2line_raw)
    stage: Path | None = Path(tempfile.mkdtemp(prefix=".p088-split-debug-stage.", dir=result_dir.parent))
    try:
        with tempfile.TemporaryDirectory(prefix="x64lens-p088-split-debug-") as raw:
            workspace = Path(raw)
            build_results = []; packages = []; original_debugs = []; cores = []
            total_exec = total_pairs = total_symbols = 0
            controls: list[str] = []
            for index, generation in enumerate(generations[:2], 1):
                analyzer = verify_member(producer_root, generation["analyzer"], True)
                effects = verify_member(producer_root, generation["effects_fixture"], False)
                pairs = verify_member(producer_root, generation["ordered_pairs_fixture"], False)
                first = package_once(analyzer, workspace / f"build-{index}/a", objcopy)
                second = package_once(analyzer, workspace / f"build-{index}/b", objcopy)
                for key in ("runtime", "debug", "core"):
                    require(first[key].read_bytes() == second[key].read_bytes(), f"nondeterministic {key}: build {index}")
                retained = stage / f"build-{index}"
                retained.mkdir(mode=0o755)
                runtime = retained / "x64lens"; debug = retained / "x64lens.debug"
                shutil.copyfile(first["runtime"], runtime); shutil.copyfile(first["debug"], debug)
                runtime.chmod(0o555); debug.chmod(0o444)
                unstripped = workspace / f"build-{index}/unstripped"
                shutil.copyfile(analyzer, unstripped); unstripped.chmod(0o755)
                executed, paired = behavior(authority, index, unstripped, first["runtime"], effects, pairs, retained)
                total_exec += executed; total_pairs += paired
                addresses = symbol_addresses(unstripped, nm, authority["known_symbols"], first["runtime"].parent)
                resolutions = []
                for symbol in authority["known_symbols"]:
                    name, location = resolve(addr2line, first["runtime"].parent, "x64lens", addresses[symbol])
                    require(name == symbol and not any(p.decode() in location for p in LOCAL_PREFIXES),
                            f"symbol resolution failed: build {index}/{symbol}")
                    resolutions.append({"symbol":symbol,"address":addresses[symbol],"location":location})
                    total_symbols += 1
                controls.extend([f"build{index}_debuglink_name_crc", f"build{index}_symbol_resolution"])
                reduction = (analyzer.stat().st_size - runtime.stat().st_size) / analyzer.stat().st_size
                require(reduction >= 0.5, f"runtime reduction below threshold: build {index}")
                packages.append(first); original_debugs.append(first["original"]); cores.append(first["core"])
                build_results.append({"build":index,"producer_build_id":generation["build_id"],
                    "unstripped_sha256":sha(analyzer),"unstripped_size_bytes":analyzer.stat().st_size,
                    "runtime":{"sha256":sha(runtime),"size_bytes":runtime.stat().st_size,"mode":"0555"},
                    "companion":{"sha256":sha(debug),"size_bytes":debug.stat().st_size,"mode":"0444"},
                    "runtime_size_reduction":reduction,"debuglink_crc32":first["crc"],
                    "redacted_local_path_strings":first["redactions"],"symbol_resolutions":resolutions,
                    "behavior_executions":executed,"behavior_pairs":paired,"build_id_present":False})
            first = packages[0]; work = first["runtime"].parent; debug = work / "x64lens.debug"
            saved = debug.read_bytes(); absent = work / "x64lens.debug.absent"; debug.rename(absent)
            name, _ = resolve(addr2line, work, "x64lens", build_results[0]["symbol_resolutions"][0]["address"])
            require(name == "??", "missing companion accepted"); absent.rename(debug)
            controls.append("companion_absent_rejected")
            corrupt = bytearray(saved); corrupt[128] ^= 1; debug.write_bytes(corrupt)
            name, _ = resolve(addr2line, work, "x64lens", build_results[0]["symbol_resolutions"][0]["address"])
            require(name == "??", "CRC-mismatched companion accepted"); debug.write_bytes(saved)
            controls.append("companion_crc_mismatch_rejected")
            cross = workspace / "cross"; cross.mkdir(); runtime_orig = cross / "runtime"; canonical_debug = cross / "x64lens.debug"
            shutil.copyfile(cores[0], runtime_orig); shutil.copyfile(original_debugs[0], canonical_debug)
            cp = run([os.fspath(objcopy), "--add-gnu-debuglink=x64lens.debug", "runtime"], cwd=cross)
            require(cp.returncode == 0, "cross-build control setup failed")
            shutil.copyfile(original_debugs[1], canonical_debug)
            name, _ = resolve(addr2line, cross, "runtime", build_results[0]["symbol_resolutions"][0]["address"])
            require(name == "??", "cross-build pre-normalization companion accepted")
            controls.append("cross_build_substitution_rejected_before_normalization")
            require(".gnu_debuglink" not in elf_sections(cores[0]), "runtime core contains debuglink")
            controls.append("runtime_core_has_no_debuglink")
            require(len(controls) == 8 and set(controls) == set(authority["companion_controls"]),
                    "companion-control closure changed")
            runtime_equal = packages[0]["runtime"].read_bytes() == packages[1]["runtime"].read_bytes()
            debug_equal = packages[0]["debug"].read_bytes() == packages[1]["debug"].read_bytes()
            require(runtime_equal and debug_equal, "normalized artifacts differ across builds")
            result = {"schema":RESULT_SCHEMA,"sprint":13,"patch":88,"experiment_id":authority["experiment_id"],
                "evidence_class":"diagnostic","publication_eligible":False,"product_adoption_authorized":False,
                "source_candidate_tree":source_tree,"producer_manifest_sha256":sha(producer_manifest_path),
                "tools":{"objcopy":tool_record(objcopy,["--version"]),"nm":tool_record(nm,["--version"]),
                         "addr2line":tool_record(addr2line,["--version"])},
                "build_results":build_results,"companion_controls":[{"id":x,"passed":True} for x in controls],
                "summary":{"builds":2,"behavior_executions":total_exec,"behavior_pairs":total_pairs,
                    "companion_controls":len(controls),"symbol_resolutions":total_symbols,
                    "minimum_runtime_size_reduction":min(x["runtime_size_reduction"] for x in build_results),
                    "build_id_present":False,"local_path_leaks":0,"runtime_bytes_equal_between_builds":runtime_equal,
                    "companion_bytes_equal_between_builds":debug_equal},
                "public_boundary":authority["public_boundary"],"limitations":authority["limitations"]}
            validate_result(result, expected, source_tree)
            write_file(stage / "manifest.json", canonical(result), 0o444)
            for path in stage.rglob("*"):
                if path.is_file() and path.name not in {"manifest.json","x64lens"}:
                    path.chmod(0o444)
            checksums(stage)
            rename_noreplace(stage, result_dir)
            stage = None
            return result
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)


def verify(authority_path: Path, expected_path: Path, result_dir: Path, source_tree: str) -> dict[str, Any]:
    authority = load(authority_path); expected = load(expected_path); validate_authority(authority, expected)
    result = load(result_dir / "manifest.json"); validate_result(result, expected, source_tree)
    declared = {}
    for line in (result_dir / "SHA256SUMS.txt").read_text().splitlines():
        digest, raw = line.split("  ", 1); rel = safe_rel(raw); require(rel not in declared, "duplicate checksum row"); declared[rel] = digest
    actual = {p.relative_to(result_dir).as_posix():sha(p) for p in result_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    require(declared == actual, "result checksum closure changed")
    return result


def selftest(authority_path: Path, expected_path: Path) -> None:
    authority = load(authority_path); expected = load(expected_path); validate_authority(authority, expected)
    mutations = 0
    for key, value in (("builds",1),("publication_eligible",True),("product_adoption_authorized",True)):
        changed = json.loads(json.dumps(authority)); changed[key] = value
        try: validate_authority(changed, expected)
        except SplitDebugError: mutations += 1
        else: raise SplitDebugError(f"authority mutation accepted: {key}")
    changed = json.loads(json.dumps(authority)); changed["required_denominators"]["behavior_executions"] = 59
    try: validate_authority(changed, expected)
    except SplitDebugError: mutations += 1
    else: raise SplitDebugError("denominator mutation accepted")
    changed = json.loads(json.dumps(authority)); changed["public_boundary"]["score_changes"] = 1
    try: validate_authority(changed, expected)
    except SplitDebugError: mutations += 1
    else: raise SplitDebugError("public-boundary mutation accepted")
    require(mutations == 5, "mutation denominator changed")
    print("sprint13-split-debug-packaging-smoke: ok mode=selftest builds=2 behavior_profiles=15 behavior_executions=60 behavior_pairs=30 companion_controls=8 symbol_resolutions=12 minimum_reduction=0.50 product_adoption=0 mutation_rejections=5")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    for action in ("selftest","run","verify"):
        p = sub.add_parser(action); p.add_argument("--authority",type=Path,required=True); p.add_argument("--expected",type=Path,required=True)
        if action != "selftest": p.add_argument("--result-dir",type=Path,required=True); p.add_argument("--expected-source-tree",required=True)
        if action == "run":
            p.add_argument("--producer-root",type=Path,required=True); p.add_argument("--producer-manifest",type=Path,required=True)
            p.add_argument("--objcopy",default="objcopy"); p.add_argument("--nm",default="nm"); p.add_argument("--addr2line",default="addr2line")
    args = parser.parse_args()
    if args.action == "selftest": selftest(args.authority,args.expected)
    elif args.action == "run":
        result = run_experiment(args.authority,args.expected,args.producer_root.resolve(strict=True),args.producer_manifest.resolve(strict=True),
                                args.result_dir,args.expected_source_tree,args.objcopy,args.nm,args.addr2line)
        print(f"sprint13-split-debug-packaging-smoke: ok mode=run builds=2 behavior_executions={result['summary']['behavior_executions']} behavior_pairs=30 companion_controls=8 symbol_resolutions=12 minimum_reduction={result['summary']['minimum_runtime_size_reduction']:.6f} product_adoption=0")
    else:
        result=verify(args.authority,args.expected,args.result_dir,args.expected_source_tree)
        print(f"sprint13-split-debug-packaging-smoke: ok mode=verify builds=2 behavior_executions={result['summary']['behavior_executions']} companion_controls=8 symbol_resolutions=12")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (SplitDebugError,OSError,subprocess.SubprocessError,json.JSONDecodeError) as exc: fail(str(exc))
