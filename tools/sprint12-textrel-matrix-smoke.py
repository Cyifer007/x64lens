#!/usr/bin/env python3
"""Validate complete private DT_TEXTREL/DF_TEXTREL evidence and public non-projection.

The matrix constructs 24 bounded ELF64 objects, checks an independent GNU
``readelf -dW`` disposition, and in full mode validates every private aggregate,
all public command exits, no-partial-output behavior, and the actual schema
authority. Public leakage checks inspect JSON keys structurally; target or value
strings containing ``textrel`` are not mistaken for new schema fields.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from typing import Any, Iterable

EXIT_OK=0; EXIT_MALFORMED=5; EXIT_UNSUPPORTED=6
STATE_UNKNOWN=0; STATE_ABSENT=1; STATE_PRESENT=2; STATE_CONTRADICTORY=3
FIRST_NONE=(1<<64)-1
DT_NULL=0; DT_TEXTREL=22; DT_FLAGS=30
DF_TEXTREL=0x4; DF_BIND_NOW=0x8
ET_EXEC=2; EM_X86_64=62; PT_LOAD=1; PT_DYNAMIC=2; PF_X=1; PF_W=2; PF_R=4
ELF64_EHDR_SIZE=64; ELF64_PHDR_SIZE=56
COMMANDS=("info","mitigations","gadgets","analyze")
PROBE_KEYS={
 "status","carrier_count","textrel_tag_count","flags_count","flags_first_value",
 "flags_and","flags_or","full_value_conflicts","textrel_conflicts","table_complete",
 "textrel_state","search_record_count","search_bytes_used","rpath_carrier_count",
 "runpath_carrier_count","rpath_value_count","runpath_value_count",
 "rpath_value_conflicts","runpath_value_conflicts","rpath_first_record",
 "runpath_first_record","rpath_state","runpath_state","paths",
}
PROBE_INTEGER_KEYS=PROBE_KEYS-{"paths"}
PRIVATE_PUBLIC_KEYS={
 "carrier_count","textrel_tag_count","flags_count","flags_first_value","flags_and",
 "flags_or","full_value_conflicts","textrel_conflicts","table_complete","textrel_state",
 "search_record_count","search_bytes_used","rpath_carrier_count","runpath_carrier_count",
 "rpath_value_count","runpath_value_count","rpath_value_conflicts",
 "runpath_value_conflicts","rpath_first_record","runpath_first_record","rpath_state",
 "runpath_state","paths","dynamic_metadata","textrel","rpath","runpath",
}
PRIVATE_TEXT_TOKENS=("textrel_state","textrel_conflicts","rpath_state","runpath_state")

class Error(RuntimeError): pass

@dataclass(frozen=True)
class Case:
    name:str
    kind:str
    entries:tuple[tuple[int,int],...]=()
    expected_state:int=STATE_UNKNOWN
    expected_status:int=EXIT_OK
    readelf_eligible:bool=False
    readelf_textrel:bool=False
    zero_dynamic:bool=False
    mutation:str=""

CASES=(
 Case("no_dynamic","valid",expected_state=STATE_UNKNOWN),
 Case("dynamic_zero_size","valid",expected_state=STATE_UNKNOWN,zero_dynamic=True),
 Case("null_only","valid",((DT_NULL,0),),STATE_ABSENT,readelf_eligible=True),
 Case("textrel_tag","valid",((DT_TEXTREL,0),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("flags_textrel","valid",((DT_FLAGS,DF_TEXTREL),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("textrel_and_flags","valid",((DT_TEXTREL,0),(DT_FLAGS,DF_TEXTREL),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("flags_zero","valid",((DT_FLAGS,0),(DT_NULL,0)),STATE_ABSENT,readelf_eligible=True),
 Case("flags_bind_now_only","valid",((DT_FLAGS,DF_BIND_NOW),(DT_NULL,0)),STATE_ABSENT,readelf_eligible=True),
 Case("duplicate_equal_flags_textrel","valid",((DT_FLAGS,DF_TEXTREL),(DT_FLAGS,DF_TEXTREL),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("duplicate_equal_flags_zero","valid",((DT_FLAGS,0),(DT_FLAGS,0),(DT_NULL,0)),STATE_ABSENT,readelf_eligible=True),
 Case("flags_unrelated_disagree_absent","valid",((DT_FLAGS,0),(DT_FLAGS,DF_BIND_NOW),(DT_NULL,0)),STATE_ABSENT,readelf_eligible=True),
 Case("flags_unrelated_disagree_present","valid",((DT_FLAGS,DF_TEXTREL),(DT_FLAGS,DF_TEXTREL|DF_BIND_NOW),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("flags_textrel_contradiction","valid",((DT_FLAGS,0),(DT_FLAGS,DF_TEXTREL),(DT_NULL,0)),STATE_CONTRADICTORY,readelf_eligible=True,readelf_textrel=True),
 Case("duplicate_textrel_tags","valid",((DT_TEXTREL,0),(DT_TEXTREL,0),(DT_NULL,0)),STATE_PRESENT,readelf_eligible=True,readelf_textrel=True),
 Case("null_early_ignores_textrel","valid",((DT_NULL,0),(DT_TEXTREL,0)),STATE_ABSENT),
 Case("no_null_textrel","valid",((DT_TEXTREL,0),),STATE_UNKNOWN),
 Case("no_null_flags_textrel","valid",((DT_FLAGS,DF_TEXTREL),),STATE_UNKNOWN),
 Case("carrier_64","valid",tuple([(DT_TEXTREL,0)]*64+[(DT_NULL,0)]),STATE_PRESENT),
 Case("three_consistent_textrel_flags","valid",((DT_FLAGS,DF_TEXTREL),(DT_FLAGS,DF_TEXTREL|DF_BIND_NOW),(DT_FLAGS,DF_TEXTREL|0x20),(DT_NULL,0)),STATE_PRESENT),
 Case("filesz_gt_memsz","malformed",((DT_NULL,0),),expected_status=EXIT_MALFORMED,mutation="filesz_gt_memsz"),
 Case("nonintegral_dynamic","malformed",((DT_NULL,0),),expected_status=EXIT_MALFORMED,mutation="nonintegral"),
 Case("out_of_range_dynamic","malformed",((DT_NULL,0),),expected_status=EXIT_MALFORMED,mutation="out_of_range"),
 Case("duplicate_dynamic","malformed",((DT_NULL,0),),expected_status=EXIT_MALFORMED,mutation="duplicate_dynamic"),
 Case("carrier_65","unsupported",tuple([(DT_TEXTREL,0)]*65+[(DT_NULL,0)]),expected_status=EXIT_UNSUPPORTED),
)

AUTHORITY={
 "schema":"x64lens-sprint12-textrel-private-evidence-v1",
 "evidence_class":"diagnostic","frozen":False,"publication_eligible":False,
 "public_projection":False,"schema_version":"0.2.0","carrier_capacity":64,
 "state_values":{"unknown":0,"absent":1,"present":2,"contradictory":3},
 "fixture_counts":{"valid":19,"malformed":4,"unsupported":1,"total":24,
   "private_probe_outcomes":24,"public_command_outcomes":96,
   "external_dispositions":24,"total_outcome_cells":144,"eligible_readelf":12},
 "public_commands":["info","mitigations","gadgets","analyze"],
 "external_command":["readelf","-dW","<target>"],
 "interpretation":"DT_TEXTREL and DF_TEXTREL are private static carrier evidence. They do not establish a runtime relocation event, vulnerability, or exploitability.",
}

def strict_pairs(items:list[tuple[str,Any]])->dict[str,Any]:
    out:dict[str,Any]={}
    for key,value in items:
        if key in out: raise Error(f"duplicate JSON key: {key}")
        out[key]=value
    return out

def strict_json(raw:str)->Any:
    return json.loads(raw,object_pairs_hook=strict_pairs)

def require_int(value:Any,label:str)->int:
    if type(value) is not int or value < 0: raise Error(f"{label} must be a nonnegative integer")
    return value

def dyn(entries:Iterable[tuple[int,int]])->bytes:
    return b"".join(struct.pack("<QQ",t,v) for t,v in entries)

def phdr(ptype:int,flags:int,off:int,vaddr:int,filesz:int,memsz:int,align:int)->bytes:
    return struct.pack("<IIQQQQQQ",ptype,flags,off,vaddr,vaddr,filesz,memsz,align)

def build(case:Case)->bytes:
    dynamic_payload=dyn(case.entries)
    include_dynamic=case.name!="no_dynamic"
    phnum=1+(1 if include_dynamic else 0)+(1 if case.mutation=="duplicate_dynamic" else 0)
    dyn_off=0x2000
    dyn_filesz=0 if case.zero_dynamic else len(dynamic_payload)
    dyn_memsz=dyn_filesz
    dyn_record_off=dyn_off
    if case.mutation=="filesz_gt_memsz": dyn_memsz=max(0,dyn_filesz-1)
    if case.mutation=="nonintegral": dyn_filesz=max(1,dyn_filesz-1); dyn_memsz=dyn_filesz
    if case.mutation=="out_of_range": dyn_record_off=0x80000000
    size=max(0x2200,dyn_off+len(dynamic_payload),ELF64_EHDR_SIZE+phnum*ELF64_PHDR_SIZE)
    image=bytearray(size)
    ident=bytearray(16); ident[:4]=b"\x7fELF"; ident[4]=2; ident[5]=1; ident[6]=1
    image[:16]=ident
    struct.pack_into("<HHIQQQIHHHHHH",image,16,ET_EXEC,EM_X86_64,1,0x401000,ELF64_EHDR_SIZE,0,0,ELF64_EHDR_SIZE,ELF64_PHDR_SIZE,phnum,0,0,0)
    image[ELF64_EHDR_SIZE:ELF64_EHDR_SIZE+ELF64_PHDR_SIZE]=phdr(PT_LOAD,PF_R|PF_X,0x1000,0x401000,0x20,0x20,0x1000)
    image[0x1000:0x1020]=b"\x90"*31+b"\xc3"
    idx=1
    if include_dynamic:
        start=ELF64_EHDR_SIZE+idx*ELF64_PHDR_SIZE
        image[start:start+ELF64_PHDR_SIZE]=phdr(PT_DYNAMIC,PF_R|PF_W,dyn_record_off,0x402000,dyn_filesz,dyn_memsz,8)
        idx+=1
        image[dyn_off:dyn_off+len(dynamic_payload)]=dynamic_payload
    if case.mutation=="duplicate_dynamic":
        start=ELF64_EHDR_SIZE+idx*ELF64_PHDR_SIZE
        image[start:start+ELF64_PHDR_SIZE]=phdr(PT_DYNAMIC,PF_R|PF_W,dyn_off,0x402000,len(dynamic_payload),len(dynamic_payload),8)
    return bytes(image)

def run(argv:list[str])->subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=10)

def load_authority(path:Path)->dict[str,Any]:
    value=strict_json(path.read_text())
    if value!=AUTHORITY: raise Error("authority semantics changed")
    return value

def load_schema(path:Path)->dict[str,Any]:
    value=strict_json(path.read_text())
    if not isinstance(value,dict): raise Error("schema authority must be an object")
    if value.get("$schema")!="https://json-schema.org/draft/2020-12/schema": raise Error("schema draft changed")
    props=value.get("properties")
    if not isinstance(props,dict) or props.get("schema_version")!={"const":"0.2.0"}: raise Error("schema version authority changed")
    required=value.get("required")
    needed={"schema_version","tool","tool_version","report_type","command","analysis","target","mitigations","counts","primitive_coverage","gadgets","limitations"}
    if not isinstance(required,list) or not needed.issubset(set(required)): raise Error("schema required-field authority changed")
    return value

def expected_facts(case:Case)->dict[str,Any]:
    base={
      "status":case.expected_status,"carrier_count":0,"textrel_tag_count":0,"flags_count":0,
      "flags_first_value":0,"flags_and":0,"flags_or":0,"full_value_conflicts":0,
      "textrel_conflicts":0,"table_complete":0,"textrel_state":STATE_UNKNOWN,
      "search_record_count":0,"search_bytes_used":0,"rpath_carrier_count":0,
      "runpath_carrier_count":0,"rpath_value_count":0,"runpath_value_count":0,
      "rpath_value_conflicts":0,"runpath_value_conflicts":0,
      "rpath_first_record":FIRST_NONE,"runpath_first_record":FIRST_NONE,
      "rpath_state":STATE_UNKNOWN,"runpath_state":STATE_UNKNOWN,"paths":[],
    }
    if case.mutation in {"filesz_gt_memsz","nonintegral","out_of_range","duplicate_dynamic"}:
        return base
    values=[]; null_seen=False
    if case.name!="no_dynamic" and not case.zero_dynamic:
        for tag,value in case.entries:
            if tag==DT_NULL:
                null_seen=True; break
            if tag in (DT_TEXTREL,DT_FLAGS):
                if len(values)>=64: break
                values.append((tag,value))
    base["carrier_count"]=len(values)
    textrels=[v for t,v in values if t==DT_TEXTREL]
    flags=[v for t,v in values if t==DT_FLAGS]
    base["textrel_tag_count"]=len(textrels)
    base["flags_count"]=len(flags)
    if flags:
        base["flags_first_value"]=flags[0]
        and_value=flags[0]; or_value=flags[0]
        for value in flags[1:]:
            if value!=flags[0]: base["full_value_conflicts"]+=1
            and_value &= value; or_value |= value
        base["flags_and"]=and_value; base["flags_or"]=or_value
        base["textrel_conflicts"]=int(bool(or_value&DF_TEXTREL)!=bool(and_value&DF_TEXTREL))
    complete=case.name!="no_dynamic" and null_seen and case.expected_status==EXIT_OK
    base["table_complete"]=int(complete)
    if complete:
        if base["textrel_conflicts"]: base["textrel_state"]=STATE_CONTRADICTORY
        elif textrels or (base["flags_or"]&DF_TEXTREL): base["textrel_state"]=STATE_PRESENT
        else: base["textrel_state"]=STATE_ABSENT
        base["rpath_state"]=STATE_ABSENT; base["runpath_state"]=STATE_ABSENT
    if case.expected_status==EXIT_UNSUPPORTED:
        base["carrier_count"]=64; base["textrel_tag_count"]=64
    if case.expected_status==EXIT_OK and base["textrel_state"]!=case.expected_state:
        raise Error(f"internal expected-state disagreement for {case.name}")
    return base

def validate_probe(case:Case,raw:bytes)->dict[str,Any]:
    try: value=strict_json(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise Error(f"invalid probe JSON for {case.name}: {exc}") from exc
    if not isinstance(value,dict) or set(value)!=PROBE_KEYS: raise Error(f"probe shape changed for {case.name}")
    for key in PROBE_INTEGER_KEYS: require_int(value[key],f"{case.name}.{key}")
    if not isinstance(value["paths"],list): raise Error(f"{case.name}.paths must be an array")
    expected=expected_facts(case)
    if value!=expected:
        differences={key:(expected[key],value.get(key)) for key in expected if value.get(key)!=expected[key]}
        raise Error(f"probe facts mismatch for {case.name}: {differences}")
    return value

def readelf_has_textrel(output:bytes)->bool:
    return "TEXTREL" in output.decode("utf-8","replace").upper()

def walk_keys(value:Any)->Iterable[str]:
    if isinstance(value,dict):
        for key,item in value.items():
            yield key; yield from walk_keys(item)
    elif isinstance(value,list):
        for item in value: yield from walk_keys(item)

def validate_public_json(case:Case,command:str,raw:bytes)->None:
    try: report=strict_json(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise Error(f"invalid public JSON {case.name}/{command}: {exc}") from exc
    if not isinstance(report,dict) or report.get("schema_version")!="0.2.0" or report.get("command")!=command:
        raise Error(f"public schema identity changed for {case.name}/{command}")
    leaked=sorted(set(walk_keys(report))&PRIVATE_PUBLIC_KEYS)
    if leaked: raise Error(f"private keys leaked for {case.name}/{command}: {leaked}")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--authority",type=Path,required=True)
    ap.add_argument("--oracle-only",action="store_true")
    ap.add_argument("--readelf",required=True)
    ap.add_argument("--analyzer",type=Path)
    ap.add_argument("--fact-probe",type=Path)
    ap.add_argument("--schema",type=Path)
    ns=ap.parse_args()
    load_authority(ns.authority)
    if not ns.oracle_only:
        if ns.analyzer is None or ns.fact_probe is None or ns.schema is None: raise Error("full mode requires analyzer, fact probe, and schema")
        load_schema(ns.schema)
    eligible=matches=0; public_runs=probe_runs=0
    # The deliberate textrel-bearing parent name proves value/path strings are
    # not confused with private JSON keys.
    with tempfile.TemporaryDirectory(prefix="x64lens-textrel-target-path-") as td:
        root=Path(td)
        for case in CASES:
            target=root/(case.name+".elf"); target.write_bytes(build(case)); target.chmod(0o444)
            result=run([ns.readelf,"-dW",str(target)])
            observed=readelf_has_textrel(result.stdout+result.stderr)
            if case.readelf_eligible:
                if result.returncode!=0: raise Error(f"readelf process failed for eligible case {case.name}: {result.returncode}")
                eligible+=1
                if observed!=case.readelf_textrel: raise Error(f"readelf disposition mismatch for {case.name}: expected {case.readelf_textrel}, observed {observed}")
                matches+=1
            if ns.oracle_only: continue
            probe=run([str(ns.fact_probe),str(target)]); probe_runs+=1
            if probe.returncode!=0: raise Error(f"fact probe process failed for {case.name}: {probe.returncode}")
            validate_probe(case,probe.stdout)
            for command in COMMANDS:
                argv=[str(ns.analyzer),command]
                if command in ("gadgets","analyze"): argv += ["--format","json","--max-depth","4"]
                argv.append(str(target))
                proc=run(argv); public_runs+=1
                expected=0 if command=="info" or case.expected_status==0 else case.expected_status
                if proc.returncode!=expected: raise Error(f"public exit mismatch {case.name}/{command}: {proc.returncode} != {expected}")
                if expected!=0 and proc.stdout: raise Error(f"partial public stdout for {case.name}/{command}")
                if expected==0 and command in ("gadgets","analyze"):
                    validate_public_json(case,command,proc.stdout)
                else:
                    low=proc.stdout.decode("utf-8","replace").lower()
                    if any(token in low for token in PRIVATE_TEXT_TOKENS): raise Error(f"private text leaked in {case.name}/{command}")
    if eligible!=12 or matches!=12: raise Error(f"readelf denominator mismatch: {matches}/{eligible}")
    if ns.oracle_only:
        print("sprint12-textrel-readelf-oracle: ok fixtures=24 valid=19 malformed=4 unsupported=1 external_dispositions=24 eligible_matches=12 carrier_cap=64")
    else:
        if probe_runs!=24 or public_runs!=96: raise Error("full denominator mismatch")
        print("sprint12-textrel-matrix-smoke: ok fixtures=24 private_probe_outcomes=24 public_command_outcomes=96 external_dispositions=24 total_outcome_cells=144 eligible_matches=12 carrier_cap=64 schema_consumed=1 aggregate_fields=22 public_fields_added=0")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (Error,subprocess.TimeoutExpired,OSError) as exc:
        print(f"sprint12-textrel-matrix-smoke: error: {exc}",file=os.sys.stderr)
        raise SystemExit(1)
