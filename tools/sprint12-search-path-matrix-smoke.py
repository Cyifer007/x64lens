#!/usr/bin/env python3
"""Validate bounded distinct private DT_RPATH and DT_RUNPATH evidence.

The controlled matrix exercises mixed carrier counts 0/1/32/63/64/65,
aggregate exact-value work 0/1/4096/4097 bytes, duplicate equality and
contradiction, hostile bytes, literal separators and $ORIGIN, malformed string
metadata, and no-partial-output behavior. GNU readelf is an independent
presence comparator; it is not runtime or policy authority.
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
from typing import Any

EXIT_OK=0; EXIT_MALFORMED=5; EXIT_UNSUPPORTED=6
UNKNOWN=0; ABSENT=1; PRESENT=2; CONTRADICTORY=3
FIRST_NONE=(1<<64)-1
DT_NULL=0; DT_STRTAB=5; DT_STRSZ=10; DT_RPATH=15; DT_TEXTREL=22; DT_RUNPATH=29
ET_EXEC=2; EM_X86_64=62; PT_LOAD=1; PT_DYNAMIC=2; PF_X=1; PF_W=2; PF_R=4
EHDR=64; PHDR=56; DYN=16; DYNAMIC_MAX=4096; STRING_SCAN_MAX=1048576
COMMANDS=("info","mitigations","gadgets","analyze")
PATH_RECORD_KEYS={"tag","dynamic_index","dynamic_file_offset","string_table_offset","string_file_offset","byte_pool_offset","byte_length","bytes_hex"}
PROBE_KEYS={
 "status","carrier_count","textrel_tag_count","flags_count","flags_first_value","flags_and","flags_or","full_value_conflicts","textrel_conflicts","table_complete","textrel_state",
 "search_record_count","search_bytes_used","rpath_carrier_count","runpath_carrier_count","rpath_value_count","runpath_value_count","rpath_value_conflicts","runpath_value_conflicts","rpath_first_record","runpath_first_record","rpath_state","runpath_state","paths",
}
PRIVATE_KEYS=PROBE_KEYS|{"dynamic_metadata","search_paths","rpath","runpath"}

class Error(RuntimeError): pass
@dataclass(frozen=True)
class Case:
    name:str
    kind:str
    paths:tuple[tuple[int,bytes],...]=()
    textrel_count:int=0
    no_dynamic:bool=False
    no_null:bool=False
    mutation:str=""
    expected_status:int=EXIT_OK
    expected_rpath:int=ABSENT
    expected_runpath:int=ABSENT
    readelf_eligible:bool=False

CASES=(
 Case("no_dynamic","valid",no_dynamic=True,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("null_only","valid",readelf_eligible=False),
 Case("rpath_empty","valid",((DT_RPATH,b""),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("rpath_one_byte","valid",((DT_RPATH,b"x"),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("rpath_simple","valid",((DT_RPATH,b"/lib"),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("runpath_simple","valid",((DT_RUNPATH,b"/usr/lib"),),expected_runpath=PRESENT,readelf_eligible=True),
 Case("both_distinct","valid",((DT_RPATH,b"/old"),(DT_RUNPATH,b"/new")),expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("rpath_duplicate_equal","valid",((DT_RPATH,b"/same"),(DT_RPATH,b"/same")),expected_rpath=PRESENT,readelf_eligible=True),
 Case("rpath_duplicate_different","valid",((DT_RPATH,b"/one"),(DT_RPATH,b"/two")),expected_rpath=CONTRADICTORY,readelf_eligible=True),
 Case("runpath_duplicate_equal","valid",((DT_RUNPATH,b"/same"),(DT_RUNPATH,b"/same")),expected_runpath=PRESENT,readelf_eligible=True),
 Case("runpath_duplicate_different","valid",((DT_RUNPATH,b"/one"),(DT_RUNPATH,b"/two")),expected_runpath=CONTRADICTORY,readelf_eligible=True),
 Case("both_same_bytes","valid",((DT_RPATH,b"/same"),(DT_RUNPATH,b"/same")),expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("hostile_bytes","valid",((DT_RPATH,b"$ORIGIN:\xff\x01\\raw"),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("colon_sequence","valid",((DT_RUNPATH,b"/a::/b:"),),expected_runpath=PRESENT,readelf_eligible=True),
 Case("origin_literal","valid",((DT_RPATH,b"$ORIGIN/../lib"),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("empty_then_nonempty","valid",((DT_RPATH,b""),(DT_RPATH,b"x")),expected_rpath=CONTRADICTORY,readelf_eligible=True),
 Case("no_null_rpath","valid",((DT_RPATH,b"/incomplete"),),no_null=True,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("mixed_carrier_32","valid",((DT_RPATH,b"r"),(DT_RUNPATH,b"u")),textrel_count=30,expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("mixed_carrier_63","valid",((DT_RPATH,b"r"),(DT_RUNPATH,b"u")),textrel_count=61,expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("mixed_carrier_64","valid",((DT_RPATH,b"r"),(DT_RUNPATH,b"u")),textrel_count=62,expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("path_bytes_4096","valid",((DT_RPATH,b"a"*4096),),expected_rpath=PRESENT,readelf_eligible=True),
 Case("aggregate_bytes_4096","valid",((DT_RPATH,b"a"*2048),(DT_RUNPATH,b"b"*2048)),expected_rpath=PRESENT,expected_runpath=PRESENT,readelf_eligible=True),
 Case("missing_strtab","malformed",((DT_RPATH,b"x"),),mutation="missing_strtab",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("missing_strsz","malformed",((DT_RUNPATH,b"x"),),mutation="missing_strsz",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("offset_equal_strsz","malformed",((DT_RPATH,b"x"),),mutation="offset_equal_strsz",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("unterminated_value","malformed",((DT_RUNPATH,b"unterminated"),),mutation="unterminated",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("unmapped_strtab","malformed",((DT_RPATH,b"x"),),mutation="unmapped_strtab",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("duplicate_strtab","malformed",((DT_RPATH,b"x"),),mutation="duplicate_strtab",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("duplicate_strsz","malformed",((DT_RUNPATH,b"x"),),mutation="duplicate_strsz",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("nonintegral_dynamic","malformed",((DT_RPATH,b"x"),),mutation="nonintegral",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("out_of_range_dynamic","malformed",((DT_RPATH,b"x"),),mutation="out_of_range",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("duplicate_dynamic","malformed",((DT_RPATH,b"x"),),mutation="duplicate_dynamic",expected_status=EXIT_MALFORMED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("mixed_carrier_65","unsupported",((DT_RPATH,b"r"),(DT_RUNPATH,b"u")),textrel_count=63,expected_status=EXIT_UNSUPPORTED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("path_bytes_4097","unsupported",((DT_RPATH,b"a"*4097),),expected_status=EXIT_UNSUPPORTED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("aggregate_bytes_4097","unsupported",((DT_RPATH,b"a"*2048),(DT_RUNPATH,b"b"*2049)),expected_status=EXIT_UNSUPPORTED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
 Case("strtab_scan_cap","unsupported",((DT_RPATH,b"x"),),mutation="strtab_scan_cap",expected_status=EXIT_UNSUPPORTED,expected_rpath=UNKNOWN,expected_runpath=UNKNOWN),
)

AUTHORITY={
 "schema":"x64lens-sprint12-search-path-private-evidence-v1","evidence_class":"diagnostic","frozen":False,"publication_eligible":False,"public_projection":False,"schema_version":"0.2.0",
 "mixed_carrier_capacity":64,"search_record_capacity":64,"aggregate_value_byte_capacity":4096,
 "state_values":{"unknown":0,"absent":1,"present":2,"contradictory":3},
 "fixture_counts":{"valid":22,"malformed":10,"unsupported":4,"total":36,"private_probe_outcomes":36,"public_command_outcomes":144,"external_dispositions":36,"total_outcome_cells":216,"eligible_readelf":19},
 "public_commands":["info","mitigations","gadgets","analyze"],"external_command":["readelf","-dW","<target>"],
 "value_semantics":{"rpath_and_runpath_are_distinct":True,"split_on_colon":False,"expand_origin":False,"resolve_filesystem_paths":False,"additional_target_derived_opens":0,"loader_order_or_security_judgment":False},
 "interpretation":"DT_RPATH and DT_RUNPATH are separate private static carrier/value facts with exact byte provenance. They are not expanded, resolved, opened, collapsed into one state, or projected into public schema 0.2.0.",
}

def strict_pairs(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items:
        if k in out: raise Error(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def strict_json(raw:str)->Any: return json.loads(raw,object_pairs_hook=strict_pairs)
def require(c:bool,m:str)->None:
    if not c: raise Error(m)
def pack_dyn(entries:list[tuple[int,int]])->bytes: return b"".join(struct.pack("<QQ",t,v) for t,v in entries)
def pack_phdr(t:int,f:int,o:int,v:int,fs:int,ms:int,a:int)->bytes: return struct.pack("<IIQQQQQQ",t,f,o,v,v,fs,ms,a)

@dataclass
class Built:
    image:bytes
    entries:list[tuple[int,int]]
    value_by_entry:dict[int,bytes]
    strtab_offset:int
    strsz:int

def build(case:Case)->Built:
    if case.no_dynamic:
        entries=[]; value_by_entry={}; strtab=b""; strtab_file=0x3000; strsz=0
    else:
        strtab=bytearray(); value_offsets=[]
        for _,value in case.paths:
            value_offsets.append(len(strtab)); strtab.extend(value)
            if case.mutation!="unterminated": strtab.append(0)
        if not strtab and case.paths: strtab.append(0)
        if case.mutation=="strtab_scan_cap":
            strtab.extend(b"\0"*(STRING_SCAN_MAX+1-len(strtab)))
        strtab_file=0x3000; strsz=len(strtab)
        strtab_vaddr=0x403000 if case.mutation!="unmapped_strtab" else 0x70000000
        entries=[]
        if case.mutation!="missing_strtab": entries.append((DT_STRTAB,strtab_vaddr))
        if case.mutation=="duplicate_strtab": entries.append((DT_STRTAB,strtab_vaddr))
        if case.mutation!="missing_strsz": entries.append((DT_STRSZ,strsz))
        if case.mutation=="duplicate_strsz": entries.append((DT_STRSZ,strsz))
        entries.extend((DT_TEXTREL,0) for _ in range(case.textrel_count))
        value_by_entry={}
        for (tag,value),offset in zip(case.paths,value_offsets):
            if case.mutation=="offset_equal_strsz": offset=strsz
            value_by_entry[len(entries)]=value
            entries.append((tag,offset))
        if not case.no_null: entries.append((DT_NULL,0))
    dyn_payload=pack_dyn(entries)
    dyn_off=0x2000; dyn_file_off=dyn_off
    dyn_filesz=len(dyn_payload); dyn_memsz=dyn_filesz
    if case.mutation=="nonintegral": dyn_filesz=max(1,dyn_filesz-1); dyn_memsz=dyn_filesz
    if case.mutation=="out_of_range": dyn_file_off=0x80000000
    phnum=1+(0 if case.no_dynamic else 2)+(1 if case.mutation=="duplicate_dynamic" else 0)
    data_end=max(dyn_off+len(dyn_payload),strtab_file+len(strtab) if not case.no_dynamic else 0x2200)
    size=max(data_end,EHDR+phnum*PHDR,0x3200)
    image=bytearray(size)
    ident=bytearray(16); ident[:4]=b"\x7fELF"; ident[4]=2; ident[5]=1; ident[6]=1; image[:16]=ident
    struct.pack_into("<HHIQQQIHHHHHH",image,16,ET_EXEC,EM_X86_64,1,0x401000,EHDR,0,0,EHDR,PHDR,phnum,0,0,0)
    image[EHDR:EHDR+PHDR]=pack_phdr(PT_LOAD,PF_R|PF_X,0x1000,0x401000,0x20,0x20,0x1000); image[0x1000:0x1020]=b"\x90"*31+b"\xc3"
    if not case.no_dynamic:
        data_filesz=max(len(dyn_payload),0x1000+len(strtab))
        image[EHDR+PHDR:EHDR+2*PHDR]=pack_phdr(PT_LOAD,PF_R|PF_W,0x2000,0x402000,data_filesz,data_filesz,0x1000)
        image[EHDR+2*PHDR:EHDR+3*PHDR]=pack_phdr(PT_DYNAMIC,PF_R|PF_W,dyn_file_off,0x402000,dyn_filesz,dyn_memsz,8)
        image[dyn_off:dyn_off+len(dyn_payload)]=dyn_payload
        image[strtab_file:strtab_file+len(strtab)]=strtab
        if case.mutation=="duplicate_dynamic":
            image[EHDR+3*PHDR:EHDR+4*PHDR]=pack_phdr(PT_DYNAMIC,PF_R|PF_W,dyn_off,0x402000,len(dyn_payload),len(dyn_payload),8)
    return Built(bytes(image),entries,value_by_entry,strtab_file,strsz)

def expected(case:Case,built:Built)->dict[str,Any]:
    facts={"status":case.expected_status,"carrier_count":0,"textrel_tag_count":0,"flags_count":0,"flags_first_value":0,"flags_and":0,"flags_or":0,"full_value_conflicts":0,"textrel_conflicts":0,"table_complete":0,"textrel_state":UNKNOWN,
      "search_record_count":0,"search_bytes_used":0,"rpath_carrier_count":0,"runpath_carrier_count":0,"rpath_value_count":0,"runpath_value_count":0,"rpath_value_conflicts":0,"runpath_value_conflicts":0,"rpath_first_record":FIRST_NONE,"runpath_first_record":FIRST_NONE,"rpath_state":UNKNOWN,"runpath_state":UNKNOWN,"paths":[]}
    if case.no_dynamic: return facts
    if case.mutation in {"nonintegral","out_of_range","duplicate_dynamic"}:
        return facts
    carriers=[]; null=False
    for index,(tag,value) in enumerate(built.entries):
        if tag==DT_NULL: null=True; break
        if tag in (DT_TEXTREL,DT_RPATH,DT_RUNPATH):
            if len(carriers)>=64: break
            carriers.append((index,tag,value))
    facts["carrier_count"]=len(carriers)
    facts["textrel_tag_count"]=sum(tag==DT_TEXTREL for _,tag,_ in carriers)
    facts["rpath_carrier_count"]=sum(tag==DT_RPATH for _,tag,_ in carriers)
    facts["runpath_carrier_count"]=sum(tag==DT_RUNPATH for _,tag,_ in carriers)
    complete=null and case.expected_status not in {EXIT_UNSUPPORTED} and case.mutation!="duplicate_dynamic"
    facts["table_complete"]=int(complete)
    if complete: facts["textrel_state"]=PRESENT if facts["textrel_tag_count"] else ABSENT
    if case.expected_status!=EXIT_OK or not complete or case.mutation in {"missing_strtab","missing_strsz","offset_equal_strsz","unterminated","unmapped_strtab","duplicate_strtab","duplicate_strsz","strtab_scan_cap"}:
        return facts
    pool=0; first_value:dict[int,bytes]={}; first_index:dict[int,int]={}; conflicts={DT_RPATH:0,DT_RUNPATH:0}; counts={DT_RPATH:0,DT_RUNPATH:0}
    for dyn_index,tag,_offset in carriers:
        if tag not in (DT_RPATH,DT_RUNPATH): continue
        value=built.value_by_entry[dyn_index]
        if pool+len(value)>4096: break
        record_index=len(facts["paths"])
        if tag not in first_value: first_value[tag]=value; first_index[tag]=record_index
        elif value!=first_value[tag]: conflicts[tag]+=1
        facts["paths"].append({"tag":tag,"dynamic_index":dyn_index,"dynamic_file_offset":0x2000+dyn_index*16,"string_table_offset":built.entries[dyn_index][1],"string_file_offset":built.strtab_offset+built.entries[dyn_index][1],"byte_pool_offset":pool,"byte_length":len(value),"bytes_hex":value.hex()})
        pool+=len(value); counts[tag]+=1
    facts["search_record_count"]=len(facts["paths"]); facts["search_bytes_used"]=pool
    facts["rpath_value_count"]=counts[DT_RPATH]; facts["runpath_value_count"]=counts[DT_RUNPATH]
    facts["rpath_value_conflicts"]=conflicts[DT_RPATH]; facts["runpath_value_conflicts"]=conflicts[DT_RUNPATH]
    if DT_RPATH in first_index: facts["rpath_first_record"]=first_index[DT_RPATH]
    if DT_RUNPATH in first_index: facts["runpath_first_record"]=first_index[DT_RUNPATH]
    facts["rpath_state"]=CONTRADICTORY if conflicts[DT_RPATH] else (PRESENT if counts[DT_RPATH] else ABSENT)
    facts["runpath_state"]=CONTRADICTORY if conflicts[DT_RUNPATH] else (PRESENT if counts[DT_RUNPATH] else ABSENT)
    require(facts["rpath_state"]==case.expected_rpath and facts["runpath_state"]==case.expected_runpath,f"expected state model disagreement: {case.name}")
    return facts

def run(argv:list[str])->subprocess.CompletedProcess[bytes]: return subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=20)
def load_authority(path:Path)->None:
    if strict_json(path.read_text())!=AUTHORITY: raise Error("search-path authority semantics changed")
def load_schema(path:Path)->None:
    value=strict_json(path.read_text()); require(isinstance(value,dict) and value.get("properties",{}).get("schema_version")=={"const":"0.2.0"},"schema authority changed")
def readelf_presence(raw:bytes)->tuple[bool,bool]:
    text=raw.decode("utf-8","replace").upper(); return ("(RPATH)" in text,"(RUNPATH)" in text)
def walk_keys(v:Any):
    if isinstance(v,dict):
        for k,x in v.items(): yield k; yield from walk_keys(x)
    elif isinstance(v,list):
        for x in v: yield from walk_keys(x)
def validate_probe(case:Case,built:Built,raw:bytes)->None:
    value=strict_json(raw.decode("utf-8")); require(isinstance(value,dict) and set(value)==PROBE_KEYS,f"probe shape changed: {case.name}")
    for key in PROBE_KEYS-{"paths"}: require(type(value[key]) is int and value[key]>=0,f"probe integer type changed: {case.name}.{key}")
    require(isinstance(value["paths"],list),f"paths is not list: {case.name}")
    for rec in value["paths"]:
        require(isinstance(rec,dict) and set(rec)==PATH_RECORD_KEYS,f"path record shape changed: {case.name}")
        for key in PATH_RECORD_KEYS-{"bytes_hex"}: require(type(rec[key]) is int and rec[key]>=0,f"path record integer changed: {case.name}.{key}")
        require(isinstance(rec["bytes_hex"],str) and len(rec["bytes_hex"])==2*rec["byte_length"],f"path bytes encoding changed: {case.name}")
    exp=expected(case,built)
    if value!=exp:
        diff={k:(exp[k],value.get(k)) for k in exp if exp[k]!=value.get(k)}; raise Error(f"private facts mismatch for {case.name}: {diff}")
def validate_public(case:Case,command:str,raw:bytes)->None:
    report=strict_json(raw.decode("utf-8")); require(isinstance(report,dict) and report.get("schema_version")=="0.2.0" and report.get("command")==command,f"public schema identity changed: {case.name}/{command}")
    leaked=sorted(set(walk_keys(report))&PRIVATE_KEYS); require(not leaked,f"private keys leaked: {case.name}/{command}: {leaked}")

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--authority",type=Path,required=True); ap.add_argument("--readelf",required=True); ap.add_argument("--oracle-only",action="store_true"); ap.add_argument("--analyzer",type=Path); ap.add_argument("--fact-probe",type=Path); ap.add_argument("--schema",type=Path); ns=ap.parse_args()
    load_authority(ns.authority)
    if not ns.oracle_only:
        require(ns.analyzer is not None and ns.fact_probe is not None and ns.schema is not None,"full mode requires analyzer, fact probe, and schema"); load_schema(ns.schema)
    eligible=matches=probe_runs=public_runs=0
    with tempfile.TemporaryDirectory(prefix="x64lens-search-path-") as td:
        root=Path(td)
        for case in CASES:
            built=build(case); target=root/(case.name+".elf"); target.write_bytes(built.image); target.chmod(0o444)
            ext=run([ns.readelf,"-dW",str(target)]); observed=readelf_presence(ext.stdout+ext.stderr)
            if case.readelf_eligible:
                eligible+=1; expected_presence=(any(t==DT_RPATH for t,_ in case.paths),any(t==DT_RUNPATH for t,_ in case.paths))
                require(observed==expected_presence,f"readelf presence mismatch for {case.name}: {observed} != {expected_presence}"); matches+=1
            if ns.oracle_only: continue
            probe=run([str(ns.fact_probe),str(target)]); probe_runs+=1; require(probe.returncode==0,f"probe process failed: {case.name}/{probe.returncode}"); validate_probe(case,built,probe.stdout)
            for command in COMMANDS:
                argv=[str(ns.analyzer),command]
                if command in ("gadgets","analyze"): argv += ["--format","json","--max-depth","4"]
                argv.append(str(target)); proc=run(argv); public_runs+=1
                exp=0 if command=="info" or case.expected_status==0 else case.expected_status
                require(proc.returncode==exp,f"public exit mismatch {case.name}/{command}: {proc.returncode}!={exp}")
                require(exp==0 or not proc.stdout,f"partial public stdout: {case.name}/{command}")
                if exp==0 and command in ("gadgets","analyze"): validate_public(case,command,proc.stdout)
                else:
                    low=proc.stdout.decode("utf-8","replace").lower(); require("rpath_state" not in low and "runpath_state" not in low,f"private text leaked: {case.name}/{command}")
    require((eligible,matches)==(19,19),f"readelf denominator mismatch: {matches}/{eligible}")
    if ns.oracle_only: print("sprint12-search-path-readelf-oracle: ok fixtures=36 valid=22 malformed=10 unsupported=4 eligible_matches=19 mixed_carrier_cap=64 aggregate_byte_cap=4096")
    else:
        require((probe_runs,public_runs)==(36,144),"full denominator mismatch")
        print("sprint12-search-path-matrix-smoke: ok fixtures=36 private_probe_outcomes=36 public_command_outcomes=144 external_dispositions=36 total_outcome_cells=216 eligible_matches=19 mixed_carrier_cap=64 aggregate_byte_cap=4096 distinct_families=2 public_fields_added=0 target_derived_opens=0")
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (Error,OSError,subprocess.TimeoutExpired,json.JSONDecodeError,UnicodeDecodeError) as exc:
        print(f"sprint12-search-path-matrix-smoke: error: {exc}",file=os.sys.stderr); raise SystemExit(1)
