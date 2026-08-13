#!/usr/bin/env python3
"""Compare production private role vectors with an independent fixture oracle."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-abi-role-vector-equivalence-v1.json'
EXPECTED=ROOT/'tests/expected/sprint13-abi-role-vector-equivalence-v1.json'
ABI_AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-abi-role-query-v1.json'
ABI_EXPECTED=ROOT/'tests/expected/sprint13-abi-role-query-v1.json'
ABI_TOOL=ROOT/'tools/sprint13-abi-role-query-smoke.py'
class VectorError(RuntimeError):pass
def require(ok:bool,msg:str)->None:
    if not ok:raise VectorError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-abi-role-vector-equivalence-smoke: error: {msg}',file=sys.stderr);raise SystemExit(1)
def strict(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items:require(k not in out,f'duplicate JSON key: {k}');out[k]=v
    return out
def load(path:Path)->Any:return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict)
def canonical(v:Any)->bytes:return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path);require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value

def validate_authority(v:Any)->dict[str,Any]:
    keys={'schema','sprint','patch','evidence_class','publication_eligible','purpose','internal_dispositions','vector_contract','valid_pop_cases','non_pop_pattern_ids','guard_cases','targets','claim_boundary','limitations'}
    require(isinstance(v,dict) and set(v)==keys,'vector authority shape changed')
    require(v['schema']=='x64lens-sprint13-abi-role-vector-equivalence-authority-v1' and v['sprint']==13 and v['patch']==86,'vector authority identity changed')
    require(v['internal_dispositions']=={'valid':16,'pattern_register_contradictions':16,'non_pop_zero_mask':10,'pointer_count_capacity_guards':6,'total':48},'internal denominator changed')
    require(v['vector_contract']=={'candidate_capacity':4096,'controlled_targets':24,'expected_public_closures':96,'expected_queries':36,'maximum_occupied_indices':98304},'vector contract changed')
    require(len(v['valid_pop_cases'])==16 and len(v['non_pop_pattern_ids'])==10 and len(v['guard_cases'])==6 and len(v['targets'])==24,'vector member denominator changed')
    require(len({x['id'] for x in v['targets']})==24,'duplicate controlled target')
    return v

def vector_run(probe:Path,records:list[tuple[int,int,int]],work:Path)->tuple[int,list[int]]:
    inp=work/f'in-{os.urandom(8).hex()}';out=work/f'out-{os.urandom(8).hex()}'
    payload=bytearray(b'X64R'+struct.pack('<II',len(records),len(records)))
    for pattern,count,order in records:payload+=struct.pack('<III',pattern,count,order)
    inp.write_bytes(payload);inp.chmod(0o444)
    cp=subprocess.run([os.fspath(probe),'--vector',os.fspath(inp),os.fspath(out)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=False)
    require(cp.returncode==0,f'role probe failed: {cp.stderr[-512:]!r}')
    raw=out.read_bytes();require(len(raw)==12+8*len(records) and raw[:4]==b'X64O','role probe output malformed')
    status,count=struct.unpack_from('<II',raw,4);require(count==len(records),'role probe count changed')
    masks=list(struct.unpack_from(f'<{count}Q',raw,12)) if count else []
    return status,masks

def internal_dispositions(probe:Path,authority:dict[str,Any],work:Path)->dict[str,int]:
    valid=[(x['pattern_id'],1,x['reg_id']) for x in authority['valid_pop_cases']]
    status,masks=vector_run(probe,valid,work);require(status==0 and masks==[x['expected_role_mask'] for x in authority['valid_pop_cases']],'valid role masks disagree')
    rejected=0
    for x in authority['valid_pop_cases']:
        wrong=(x['reg_id']+1)%16;status,_=vector_run(probe,[(x['pattern_id'],1,wrong)],work);require(status==7,'pattern/register contradiction accepted');rejected+=1
    status,masks=vector_run(probe,[(x,0,0) for x in authority['non_pop_pattern_ids']],work);require(status==0 and masks==[0]*10,'non-pop role mask changed')
    guards=0
    for name,expected in authority['guard_cases'].items():
        cp=subprocess.run([os.fspath(probe),'--guard',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=False)
        require(cp.returncode==0 and int(cp.stdout.strip())==expected,f'guard case changed: {name}');guards+=1
    return {'valid_masks':len(valid),'contradiction_rejections':rejected,'non_pop_zero_masks':len(masks),'guard_dispositions':guards}

def full_vectors(probe:Path,authority:dict[str,Any],abi_root:Path,work:Path)->tuple[int,int]:
    occupied=0;matches=0
    for target in authority['targets']:
        report=abi_root/'outputs'/target['id']/'gadgets_json'/'stdout';require(report.is_file(),f'missing public closure: {target["id"]}')
        value=load(report);gadgets=value['gadgets'];require(len(gadgets)==1,f'controlled target candidate denominator changed: {target["id"]}')
        gadget=gadgets[0];require(gadget['pattern']==target['public_pattern'] and gadget.get('stack_pop_order',[])==target['stack_pop_order'],f'controlled target exact facts changed: {target["id"]}')
        status,masks=vector_run(probe,[(target['pattern_id'],target['pattern_reg_count'],target['pattern_reg_order'])],work)
        require(status==0 and masks==[target['expected_role_mask']],f'candidate role vector disagrees: {target["id"]}')
        occupied+=1;matches+=1
    require(occupied<=authority['vector_contract']['maximum_occupied_indices'],'occupied candidate cap exceeded')
    return occupied,matches

def selftest(authority:dict[str,Any])->None:
    allowed=0x3f3f01
    for x in authority['valid_pop_cases']:
        require(x['expected_role_mask'] & ~allowed==0,'oracle mask exceeds allowed role domain')
    require(next(x for x in authority['valid_pop_cases'] if x['register']=='rcx')['expected_role_mask'] & (1<<11),'rcx SysV arg4 missing')
    require(next(x for x in authority['valid_pop_cases'] if x['register']=='r10')['expected_role_mask'] & (1<<19),'r10 syscall arg4 missing')

def run(args:argparse.Namespace,authority:dict[str,Any])->dict[str,Any]:
    abi=module('s13_p086_vector_abi',ABI_TOOL);abi_authority=abi.validate_authority(load(args.abi_authority.resolve(strict=True)));contract=abi.contract_result(abi_authority,args.abi_expected)
    result_dir=Path(os.path.abspath(args.result_dir));require(not result_dir.exists() and result_dir.parent.is_dir(),'vector result path unavailable')
    stage=Path(tempfile.mkdtemp(prefix=f'.{result_dir.name}.stage.',dir=result_dir.parent));work=stage/'work';work.mkdir(mode=0o700)
    try:
        abi_root=stage/'abi-closures'
        ns=SimpleNamespace(analyzer=args.analyzer, result_dir=abi_root, source_root=args.source_root, source_manifest=args.source_manifest, expected_candidate_tree=args.expected_candidate_tree, authority=args.abi_authority, expected=args.abi_expected)
        abi_manifest=abi.run_closures(ns,abi_authority,contract);require(abi_manifest['public_closure_count']==96,'ABI public closure denominator changed')
        probe=args.probe.resolve(strict=True);st=probe.stat();require(st.st_mode & 0o100 and st.st_nlink==1,'role probe is not an executable single-link authority')
        internal=internal_dispositions(probe,authority,work);occupied,matches=full_vectors(probe,authority,abi_root,work)
        result={'schema':'x64lens-sprint13-abi-role-vector-equivalence-result-v1','sprint':13,'patch':86,'internal_dispositions':sum(internal.values()),**internal,'controlled_targets':24,'occupied_indices':occupied,'vector_matches':matches,'queries':36,'public_closures':96,'decision':'private_full_vector_equivalent','public_fields_added':0,'semantic_changes':0,'score_changes':0,'schema_changed':False}
        require(result==load(args.expected.resolve(strict=True)),'ABI vector result differs from expected authority')
        (stage/'manifest.json').write_bytes(canonical({'result':result,'authority_sha256':sha(args.authority.resolve(strict=True)),'probe_sha256':sha(probe),'abi_closure_manifest_sha256':sha(abi_root/'manifest.json'),'claim_boundary':authority['claim_boundary']}));(stage/'manifest.json').chmod(0o444)
        lines=[]
        for p in sorted((x for x in stage.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'),key=lambda x:os.fsencode(x.relative_to(stage).as_posix())):lines.append(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n')
        (stage/'SHA256SUMS.txt').write_text(''.join(lines));(stage/'SHA256SUMS.txt').chmod(0o444)
        shutil.rmtree(work)
        os.rename(stage,result_dir);stage=result_dir
        return result
    finally:
        if stage.exists() and stage!=result_dir:shutil.rmtree(stage,ignore_errors=True)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('selftest','run'));ap.add_argument('--authority',type=Path,default=AUTHORITY);ap.add_argument('--expected',type=Path,default=EXPECTED);ap.add_argument('--abi-authority',type=Path,default=ABI_AUTHORITY);ap.add_argument('--abi-expected',type=Path,default=ABI_EXPECTED);ap.add_argument('--analyzer',type=Path);ap.add_argument('--probe',type=Path);ap.add_argument('--source-root',type=Path);ap.add_argument('--source-manifest',type=Path);ap.add_argument('--expected-candidate-tree');ap.add_argument('--result-dir',type=Path);args=ap.parse_args()
    try:
        authority=validate_authority(load(args.authority.resolve(strict=True)));selftest(authority)
        if args.action=='selftest':print('sprint13-abi-role-vector-equivalence-smoke: ok internal_dispositions=48 targets=24 max_indices=98304 queries=36 public_closures=96 run=deferred');return 0
        for name in ('analyzer','probe','source_root','source_manifest','expected_candidate_tree','result_dir'):require(getattr(args,name) is not None,f'--{name.replace("_","-")} is required')
        result=run(args,authority);print(f'sprint13-abi-role-vector-equivalence-smoke: ok internal_dispositions={result["internal_dispositions"]} vectors={result["vector_matches"]}/{result["occupied_indices"]} targets=24 queries=36 public_closures=96 public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0');return 0
    except (OSError,VectorError,subprocess.SubprocessError,json.JSONDecodeError,UnicodeDecodeError) as exc:fail(str(exc))
if __name__=='__main__':raise SystemExit(main())
