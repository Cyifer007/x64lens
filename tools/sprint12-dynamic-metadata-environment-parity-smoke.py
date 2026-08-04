#!/usr/bin/env python3
"""Prove full private dynamic-metadata parity across native and Docker builds.

The two planes build from the same authenticated tracked source but use separate
analyzer and fact-probe binaries. Held-out fixture bytes are mounted read-only;
the completed native plane is never mounted into the container; and the
container receives one empty writable output root. Comparison covers all 36
statuses, complete private JSON including every textrel and RPATH/RUNPATH field,
and 144 normalized public command closures.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

class Error(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Error(m)
def strict_pairs(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items:
        if k in out: raise Error(f"duplicate JSON key: {k}")
        out[k]=v
    return out
def strict_json(raw:str)->Any: return json.loads(raw,object_pairs_hook=strict_pairs)
def sha(path:Path)->tuple[str,int]:
    h=hashlib.sha256(); n=0
    with path.open("rb") as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b); n+=len(b)
    return h.hexdigest(),n
def safe(raw:str)->str:
    p=PurePosixPath(raw); require(raw and not p.is_absolute() and p.as_posix()==raw and "\\" not in raw and all(x not in {"",".",".."} for x in p.parts),f"unsafe source path: {raw!r}"); return raw
def run(argv:list[str],cwd:Path|None=None,timeout:int=180)->subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=timeout)
def load_matrix(repo:Path):
    path=repo/"tools/sprint12-search-path-matrix-smoke.py"; spec=importlib.util.spec_from_file_location("x64lens_search_path_matrix",path); require(spec is not None and spec.loader is not None,"cannot load search-path matrix")
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module
def canonical_json(value:Any)->bytes: return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
def normalized_stream(command:str,stdout:bytes,target:Path)->bytes:
    marker=os.fsencode(str(target))
    if command in {"gadgets","analyze"}:
        value=strict_json(stdout.decode("utf-8")); require(isinstance(value,dict),"public JSON is not object")
        if isinstance(value.get("target"),dict) and "path" in value["target"]: value["target"]["path"]="<target>"
        return canonical_json(value)
    return stdout.replace(marker,b"<target>")
def source_manifest(repo:Path)->dict[str,Any]:
    cp=run(["git","ls-files","-s","-z"],cwd=repo); require(cp.returncode==0,"git ls-files failed")
    files=[]
    for item in cp.stdout.split(b"\0"):
        if not item: continue
        header,path_raw=item.split(b"\t",1); fields=header.split(); require(len(fields)==3 and fields[2]==b"0", "non-stage-zero source entry")
        mode=fields[0].decode(); expected_oid=fields[1].decode(); path=safe(os.fsdecode(path_raw)); require(mode in {"100644","100755"},f"unsupported source mode for parity: {path}")
        full=repo/path; st=full.lstat(); require(stat.S_ISREG(st.st_mode) and st.st_nlink==1,f"unsafe source member: {path}"); digest,size=sha(full)
        observed_oid=run(["git","hash-object","--",path],cwd=repo); require(observed_oid.returncode==0 and observed_oid.stdout.decode().strip()==expected_oid,f"source bytes disagree with index: {path}")
        files.append({"path":path,"mode":mode,"git_oid":expected_oid,"sha256":digest,"size_bytes":size})
    unstaged=run(["git","diff","--quiet","--"],cwd=repo); require(unstaged.returncode==0,"working tree differs from authenticated index")
    tree=run(["git","write-tree"],cwd=repo); require(tree.returncode==0,"git write-tree failed")
    return {"schema":"x64lens-p076-parity-source-v1","candidate_tree":tree.stdout.decode().strip(),"files":files}
def verify_source(root:Path,manifest:dict[str,Any])->None:
    require(manifest.get("schema")=="x64lens-p076-parity-source-v1" and isinstance(manifest.get("files"),list),"source manifest changed")
    for item in manifest["files"]:
        require(isinstance(item,dict) and set(item)=={"path","mode","git_oid","sha256","size_bytes"},"source record changed"); path=safe(item["path"]); full=root/path; st=full.lstat(); require(stat.S_ISREG(st.st_mode) and st.st_nlink==1,f"source type changed: {path}"); require((stat.S_IMODE(st.st_mode)&0o111!=0)==(item["mode"]=="100755"),f"source mode changed: {path}"); digest,size=sha(full); require((digest,size)==(item["sha256"],item["size_bytes"]),f"source bytes changed: {path}")
        observed_oid=run(["git","hash-object","--",path],cwd=root); require(observed_oid.returncode==0 and observed_oid.stdout.decode().strip()==item["git_oid"],f"source Git object changed: {path}")
    tree=run(["git","write-tree"],cwd=root); require(tree.returncode==0 and tree.stdout.decode().strip()==manifest["candidate_tree"],"source tree identity changed")
def build_fixtures(repo:Path,out:Path)->dict[str,Any]:
    matrix=load_matrix(repo); out.mkdir(mode=0o755)
    rows=[]
    for case in matrix.CASES:
        built=matrix.build(case); target=out/(case.name+".elf"); target.write_bytes(built.image); target.chmod(0o444); digest,size=sha(target); rows.append({"case":case.name,"path":target.name,"sha256":digest,"size_bytes":size,"mode":"0444"})
    manifest={"schema":"x64lens-p076-parity-fixtures-v1","count":len(rows),"files":rows}; (out/"manifest.json").write_bytes(canonical_json(manifest)); (out/"manifest.json").chmod(0o444); return manifest
def verify_fixtures(root:Path,manifest:dict[str,Any])->None:
    require(manifest.get("schema")=="x64lens-p076-parity-fixtures-v1" and manifest.get("count")==36,"fixture manifest changed")
    for item in manifest["files"]:
        target=root/item["path"]; st=target.lstat(); require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o444 and st.st_nlink==1,f"fixture mode/type changed: {item['path']}"); require(sha(target)==(item["sha256"],item["size_bytes"]),f"fixture bytes changed: {item['path']}")
def execute_plane(repo:Path,source_root:Path,source_path:Path,fixtures:Path,result:Path,analyzer:Path,probe:Path,schema:Path,authority:Path,plane_id:str)->dict[str,Any]:
    require(not result.exists(),"plane result already exists"); result.mkdir(mode=0o755)
    source=strict_json(source_path.read_text()); verify_source(source_root,source)
    fixture_manifest=strict_json((fixtures/"manifest.json").read_text()); verify_fixtures(fixtures,fixture_manifest)
    matrix=load_matrix(repo); matrix.load_authority(authority); matrix.load_schema(schema)
    for binary,label in ((analyzer,"analyzer"),(probe,"fact_probe"),(schema,"schema"),(authority,"authority")):
        require(binary.is_file() and not binary.is_symlink(),f"missing {label}")
    identities={}
    for binary,label in ((analyzer,"analyzer"),(probe,"fact_probe"),(schema,"schema"),(authority,"authority"),(source_path,"source_manifest"),(fixtures/"manifest.json","fixture_manifest")):
        digest,size=sha(binary); identities[label]={"path":str(binary),"sha256":digest,"size_bytes":size,"mode":f"{stat.S_IMODE(binary.stat().st_mode):04o}"}
    rows=[]; private_cells=0; public_cells=0
    cases={c.name:c for c in matrix.CASES}
    for item in fixture_manifest["files"]:
        case=cases[item["case"]]; target=fixtures/item["path"]; built=matrix.build(case)
        proc=run([str(probe),str(target)]); require(proc.returncode==0,f"{plane_id} probe process failed: {case.name}"); matrix.validate_probe(case,built,proc.stdout); facts=strict_json(proc.stdout.decode()); private_cells+=len(matrix.PROBE_KEYS)-1+sum(len(r) for r in facts["paths"])
        rows.append({"case":case.name,"surface":"private","status":facts["status"],"normalized_sha256":hashlib.sha256(canonical_json(facts)).hexdigest(),"normalized_size":len(canonical_json(facts)),"facts":facts})
        for command in matrix.COMMANDS:
            argv=[str(analyzer),command]
            if command in ("gadgets","analyze"): argv += ["--format","json","--max-depth","4"]
            argv.append(str(target)); cp=run(argv); expected=0 if command=="info" or case.expected_status==0 else case.expected_status; require(cp.returncode==expected,f"{plane_id} public exit mismatch {case.name}/{command}"); require(expected==0 or not cp.stdout,f"{plane_id} partial stdout {case.name}/{command}")
            normalized=normalized_stream(command,cp.stdout,target); rows.append({"case":case.name,"surface":command,"status":cp.returncode,"normalized_sha256":hashlib.sha256(normalized).hexdigest(),"normalized_size":len(normalized),"stderr_sha256":hashlib.sha256(cp.stderr.replace(os.fsencode(str(target)),b"<target>")).hexdigest(),"stderr_size":len(cp.stderr)}); public_cells+=1
    manifest={"schema":"x64lens-p076-dynamic-parity-plane-v1","plane":plane_id,"source_tree":source["candidate_tree"],"objects":36,"private_processes":36,"public_processes":144,"private_field_cells":private_cells,"public_closures":public_cells,"identities":identities,"rows":rows}
    verify_source(source_root, source)
    (result/"manifest.json").write_bytes(canonical_json(manifest)); (result/"manifest.json").chmod(0o444); return manifest
def compare(native:dict[str,Any],container:dict[str,Any],out:Path)->dict[str,Any]:
    require(native["source_tree"]==container["source_tree"],"plane source trees differ"); n={(r["case"],r["surface"]):r for r in native["rows"]}; c={(r["case"],r["surface"]):r for r in container["rows"]}; require(set(n)==set(c),"plane row membership differs")
    mismatches=[]; private=public=0
    for key in sorted(n):
        a=n[key]; b=c[key]; fields=("status","normalized_sha256","normalized_size") if key[1]=="private" else ("status","normalized_sha256","normalized_size","stderr_sha256","stderr_size")
        if any(a[f]!=b[f] for f in fields): mismatches.append({"case":key[0],"surface":key[1]})
        if key[1]=="private": private+=1
        else: public+=1
    require(not mismatches,f"native/container dynamic parity mismatch: {mismatches[:8]}")
    result={"schema":"x64lens-p076-dynamic-parity-comparison-v1","source_tree":native["source_tree"],"objects":36,"private_records_compared":private,"public_closures_compared":public,"mismatches":0,"native_analyzer_sha256":native["identities"]["analyzer"]["sha256"],"container_analyzer_sha256":container["identities"]["analyzer"]["sha256"],"native_probe_sha256":native["identities"]["fact_probe"]["sha256"],"container_probe_sha256":container["identities"]["fact_probe"]["sha256"],"separate_build_origins":True,"native_plane_mounted_into_container":False}
    out.write_bytes(canonical_json(result)); out.chmod(0o444); return result
def publish(stage:Path,destination:Path)->None:
    require(not destination.exists(),"parity result identity already exists"); os.rename(stage,destination)
def command_run(ns:argparse.Namespace)->int:
    repo=Path(os.path.abspath(ns.repo)); destination=Path(os.path.abspath(ns.result_dir)); require(destination.parent.is_dir(),"result parent missing")
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-parity-",dir=destination.parent) as td:
        work=Path(td); fixtures=work/"fixtures"; build_fixtures(repo,fixtures)
        source=source_manifest(repo)
        authority_root=work/"authority"; authority_root.mkdir(mode=0o555)
        source_path=authority_root/"source-manifest.json"; source_path.write_bytes(canonical_json(source)); source_path.chmod(0o444)
        container_output=work/"container-output"; container_output.mkdir(mode=0o777); os.chmod(container_output,0o777)
        native_dir=work/"native"; native=execute_plane(repo,repo,source_path,fixtures,native_dir,Path(ns.analyzer),Path(ns.fact_probe),Path(ns.schema),Path(ns.authority),"native")
        docker_cmd=[ns.docker,"run","--rm","-v",f"{fixtures}:/inputs:ro","-v",f"{source_path}:/authority/source-manifest.json:ro","-v",f"{container_output}:/output:rw",ns.docker_image,"bash","-lc",
          "set -euo pipefail; cd /work; python3 tools/sprint12-dynamic-metadata-environment-parity-smoke.py verify-source --root /work --manifest /authority/source-manifest.json; make clean; make; make build/tests/dynamic-metadata-fact-probe; python3 tools/sprint12-dynamic-metadata-environment-parity-smoke.py plane --repo /work --source-root /work --source-manifest /authority/source-manifest.json --fixtures /inputs --result /output/container --analyzer /work/build/x64lens --fact-probe /work/build/tests/dynamic-metadata-fact-probe --schema /work/schemas/x64lens-report.schema.json --authority /work/benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json --plane-id container; python3 tools/sprint12-dynamic-metadata-environment-parity-smoke.py verify-source --root /work --manifest /authority/source-manifest.json"]
        cp=run(docker_cmd,timeout=900); require(cp.returncode==0,f"Docker dynamic parity failed: {cp.stderr.decode(errors='replace')[-2000:]}")
        container=strict_json((container_output/"container/manifest.json").read_text()); comparison=compare(native,container,work/"comparison.json")
        # Publish the read-only source authority only after both isolated planes retained it by digest.
        stage=destination.parent/(destination.name+f".staging.{os.getpid()}"); require(not stage.exists(),"staging exists"); stage.mkdir(mode=0o755)
        shutil.copytree(work/"native",stage/"native")
        shutil.copytree(container_output/"container",stage/"container")
        shutil.copy2(work/"comparison.json",stage/"comparison.json"); shutil.copy2(source_path,stage/"source-manifest.json"); shutil.copytree(fixtures,stage/"fixtures")
        manifest={"schema":"x64lens-p076-dynamic-parity-result-v1","source_tree":source["candidate_tree"],"objects":36,"private_records_compared":36,"public_closures_compared":144,"mismatches":0,"native_plane_mounted_into_container":False,"container_writable_roots":1,"comparison_sha256":sha(stage/"comparison.json")[0]}; (stage/"manifest.json").write_bytes(canonical_json(manifest)); (stage/"manifest.json").chmod(0o444); publish(stage,destination)
    print(f"sprint12-dynamic-metadata-environment-parity-smoke: ok objects=36 private_records=36 public_closures=144 mismatches=0 separate_build_origins=1 native_plane_mounted=0 result={destination}"); return 0
def command_plane(ns:argparse.Namespace)->int:
    repo=Path(ns.repo); execute_plane(repo,Path(ns.source_root),Path(ns.source_manifest),Path(ns.fixtures),Path(ns.result),Path(ns.analyzer),Path(ns.fact_probe),Path(ns.schema),Path(ns.authority),ns.plane_id); return 0
def command_verify_source(ns:argparse.Namespace)->int:
    verify_source(Path(ns.root),strict_json(Path(ns.manifest).read_text())); print("p076-parity-source-verify: ok"); return 0
def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    runp=sub.add_parser("run"); runp.add_argument("--repo",default="."); runp.add_argument("--authority",required=True); runp.add_argument("--analyzer",required=True); runp.add_argument("--fact-probe",required=True); runp.add_argument("--schema",required=True); runp.add_argument("--docker",default="docker"); runp.add_argument("--docker-image",required=True); runp.add_argument("--result-dir",required=True)
    plane=sub.add_parser("plane"); plane.add_argument("--repo",required=True); plane.add_argument("--source-root",required=True); plane.add_argument("--source-manifest",required=True); plane.add_argument("--fixtures",required=True); plane.add_argument("--result",required=True); plane.add_argument("--analyzer",required=True); plane.add_argument("--fact-probe",required=True); plane.add_argument("--schema",required=True); plane.add_argument("--authority",required=True); plane.add_argument("--plane-id",required=True)
    verify=sub.add_parser("verify-source"); verify.add_argument("--root",required=True); verify.add_argument("--manifest",required=True)
    ns=ap.parse_args(); return {"run":command_run,"plane":command_plane,"verify-source":command_verify_source}[ns.cmd](ns)
if __name__=="__main__":
    try: raise SystemExit(main())
    except (Error,OSError,subprocess.TimeoutExpired,json.JSONDecodeError,UnicodeDecodeError) as exc:
        print(f"sprint12-dynamic-metadata-environment-parity-smoke: error: {exc}",file=sys.stderr); raise SystemExit(1)
