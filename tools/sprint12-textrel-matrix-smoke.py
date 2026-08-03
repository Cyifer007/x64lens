#!/usr/bin/env python3
"""Validate bounded private DT_TEXTREL/DF_TEXTREL acquisition.

The oracle-only path generates 24 compiler-independent ELF64 fixtures and
reconciles 12 eligible direct states against GNU ``readelf -dW``. Full mode also
runs the private C/assembly fact probe and all four public x64lens commands,
while proving that the new private facts do not leak into schema 0.2.0 output.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Iterable

ELF64_EHDR_SIZE=64; ELF64_PHDR_SIZE=56; ELF64_DYN_SIZE=16
ET_EXEC=2; EM_X86_64=62
PT_LOAD=1; PT_DYNAMIC=2
PF_X=1; PF_W=2; PF_R=4
DT_NULL=0; DT_TEXTREL=22; DT_BIND_NOW=24; DT_FLAGS=30
DF_TEXTREL=0x4; DF_BIND_NOW=0x8
EXIT_OK=0; EXIT_MALFORMED=5; EXIT_UNSUPPORTED=6
STATE_UNKNOWN=0; STATE_ABSENT=1; STATE_PRESENT=2; STATE_CONTRADICTORY=3
COMMANDS=("info","mitigations","gadgets","analyze")
PRIVATE_LEAK_TOKENS=("textrel_state","textrel_tag_count","full_value_conflicts","df_textrel")

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
    # Small file-backed executable load. Program headers remain mapping authority.
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

def load_authority(path:Path)->dict:
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise Error(f"duplicate JSON key: {k}")
            out[k]=v
        return out
    data=json.loads(path.read_text(),object_pairs_hook=pairs)
    if data.get("schema")!="x64lens-sprint12-textrel-private-evidence-v1": raise Error("authority schema mismatch")
    counts=data.get("fixture_counts",{})
    expected={"valid":19,"malformed":4,"unsupported":1,"total":24,"private_probe_outcomes":24,"public_command_outcomes":96,"external_dispositions":24,"total_outcome_cells":144,"eligible_readelf":12}
    if counts!=expected or data.get("carrier_capacity")!=64 or data.get("public_projection") is not False: raise Error("authority denominator or policy mismatch")
    return data

def readelf_has_textrel(output:bytes)->bool:
    text=output.decode("utf-8","replace").upper()
    return "TEXTREL" in text

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
    eligible=matches=0; public_runs=probe_runs=0
    with tempfile.TemporaryDirectory(prefix="x64lens-textrel-") as td:
        root=Path(td)
        for case in CASES:
            target=root/(case.name+".elf"); target.write_bytes(build(case)); target.chmod(0o444)
            result=run([ns.readelf,"-dW",str(target)])
            observed=readelf_has_textrel(result.stdout+result.stderr)
            if case.readelf_eligible:
                eligible+=1
                if observed!=case.readelf_textrel:
                    raise Error(f"readelf disposition mismatch for {case.name}: expected {case.readelf_textrel}, observed {observed}")
                matches+=1
            if ns.oracle_only: continue
            if ns.analyzer is None or ns.fact_probe is None or ns.schema is None: raise Error("full mode requires analyzer, fact probe, and schema")
            probe=run([str(ns.fact_probe),str(target)]); probe_runs+=1
            if probe.returncode!=0: raise Error(f"fact probe process failed for {case.name}: {probe.returncode}")
            try: facts=json.loads(probe.stdout)
            except Exception as exc: raise Error(f"invalid probe JSON for {case.name}: {exc}")
            if facts.get("status")!=case.expected_status: raise Error(f"probe status mismatch for {case.name}: {facts.get('status')} != {case.expected_status}")
            if case.expected_status==0 and facts.get("textrel_state")!=case.expected_state: raise Error(f"private state mismatch for {case.name}")
            for command in COMMANDS:
                argv=[str(ns.analyzer),command]
                if command in ("gadgets","analyze"): argv += ["--format","json","--max-depth","4"]
                argv.append(str(target))
                proc=run(argv); public_runs+=1
                expected=0 if command=="info" else case.expected_status
                if case.expected_status==0: expected=0
                if proc.returncode!=expected: raise Error(f"public exit mismatch {case.name}/{command}: {proc.returncode} != {expected}")
                if expected!=0 and proc.stdout: raise Error(f"partial public stdout for {case.name}/{command}")
                low=proc.stdout.lower()
                if any(token.encode() in low for token in PRIVATE_LEAK_TOKENS): raise Error(f"private fact leaked in {case.name}/{command}")
                if expected==0 and command in ("gadgets","analyze"):
                    report=json.loads(proc.stdout)
                    if report.get("schema_version")!="0.2.0" or "textrel" in json.dumps(report).lower(): raise Error(f"public schema changed for {case.name}/{command}")
    if eligible!=12 or matches!=12: raise Error(f"readelf denominator mismatch: {matches}/{eligible}")
    if ns.oracle_only:
        print("sprint12-textrel-readelf-oracle: ok fixtures=24 valid=19 malformed=4 unsupported=1 external_dispositions=24 eligible_matches=12 carrier_cap=64")
    else:
        if probe_runs!=24 or public_runs!=96: raise Error("full denominator mismatch")
        print("sprint12-textrel-matrix-smoke: ok fixtures=24 private_probe_outcomes=24 public_command_outcomes=96 external_dispositions=24 total_outcome_cells=144 eligible_matches=12 carrier_cap=64 public_fields_added=0")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (Error, subprocess.TimeoutExpired, OSError) as exc:
        print(f"sprint12-textrel-matrix-smoke: error: {exc}",file=os.sys.stderr)
        raise SystemExit(1)
