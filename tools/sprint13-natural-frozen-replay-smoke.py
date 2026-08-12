#!/usr/bin/env python3
"""Replay the exact twelve frozen natural-coordinate targets with no reroll."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-natural-frozen-replay-v1.json'
NATURAL=ROOT/'tools/sprint13-natural-coordinate-campaign.py'
ATTRIBUTION=ROOT/'tools/sprint13-natural-terminal-attribution-smoke.py'
TOOLS=('x64lens','ropgadget','ropper','ropr')

class ReplayError(RuntimeError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise ReplayError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-natural-frozen-replay-smoke: error: {msg}',file=sys.stderr); raise SystemExit(1)
def strict(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items:
        require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def load(path:Path)->Any:return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict)
def canonical(value:Any)->bytes:return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec); sys.modules[name]=value; spec.loader.exec_module(value); return value

def validate_authority(value:Any)->dict[str,Any]:
    attribution=module('s13_p085_replay_attribution',ATTRIBUTION)
    return attribution.validate_authority(value)

def validate_adapters(authority:dict[str,Any])->None:
    require(len(authority['adapters'])==2,'adapter authority denominator changed')
    for item in authority['adapters']:
        path=ROOT/item['path']; require(path.is_file() and sha(path)==item['sha256'],f'adapter authority changed: {item["path"]}')

def tool_identity(natural:Any,path:Path,expected:dict[str,Any])->dict[str,Any]:
    identity=natural.regular_identity(path,expected_mode=int(expected['mode'],8),expected_sha256=expected['sha256'],require_single_link=True)
    require(identity['size_bytes']==expected['size_bytes'],f'tool size changed: {path}')
    require(bool(int(expected['mode'],8)&0o100),f'tool is not executable: {path}')
    return identity

def copy_target(natural:Any,source:Path,destination:Path,expected:dict[str,Any])->dict[str,Any]:
    payload,source_identity=natural.read_regular_authority(source,64*1024*1024)
    require(source_identity['sha256']==expected['sha256'] and source_identity['size_bytes']==expected['size_bytes'],f'frozen target changed: {expected["target_id"]}')
    natural.write_regular(destination,payload,0o444)
    return natural.regular_identity(destination,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)

def rename_noreplace(source:Path,destination:Path)->None:
    libc=ctypes.CDLL(None,use_errno=True); fn=getattr(libc,'renameat2',None); require(fn is not None,'renameat2 is unavailable')
    fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; fn.restype=ctypes.c_int
    if fn(-100,os.fsencode(source),-100,os.fsencode(destination),1)!=0:
        err=ctypes.get_errno(); raise OSError(err,os.strerror(err),destination)

def selftest(authority:dict[str,Any])->dict[str,Any]:
    validate_adapters(authority)
    roles={item['role'] for item in authority['selection']}
    result={'schema':'x64lens-sprint13-natural-frozen-replay-selftest-v1','sprint':13,'patch':85,'targets':len(authority['selection']),'roles':len(roles),'tools':len(authority['execution']['tools']),'executions':authority['execution']['execution_denominator'],'reroll':authority['execution']['reroll'],'adapters':len(authority['adapters']),'public_fields_added':0,'semantic_changes':0,'score_changes':0,'schema_changed':False}
    require(result['targets']==12 and result['roles']==3 and result['tools']==4 and result['executions']==48 and result['reroll'] is False,'frozen replay selftest changed')
    return result

def run_replay(args:argparse.Namespace,authority:dict[str,Any])->dict[str,Any]:
    natural=module('s13_p085_replay_natural',NATURAL)
    attribution=module('s13_p085_replay_input',ATTRIBUTION)
    input_dir=args.input_dir.resolve(strict=True)
    predecessor=attribution.validate_input(input_dir,authority)
    validate_adapters(authority)
    source=natural.authenticate_source_authority(args.source_root,args.source_manifest,args.expected_candidate_tree)
    result_dir=Path(os.path.abspath(args.result_dir)); require(not result_dir.exists() and not result_dir.is_symlink(),'replay result already exists')
    require(result_dir.parent.is_dir() and not result_dir.parent.is_symlink(),'replay result parent is missing or linked')
    stage=Path(tempfile.mkdtemp(prefix=f'.{result_dir.name}.stage.',dir=result_dir.parent))
    paths={'x64lens':args.x64lens.resolve(strict=True),'ropgadget':args.ropgadget.resolve(strict=True),'ropper':args.ropper.resolve(strict=True),'ropr':args.ropr.resolve(strict=True)}
    try:
        identities={name:tool_identity(natural,path,authority['tools'][name]) for name,path in paths.items()}
        target_root=stage/'targets'; target_root.mkdir(mode=0o755)
        frozen_targets={}
        for expected in authority['selection']:
            frozen_targets[expected['target_id']]=copy_target(natural,input_dir/'targets'/expected['target_id'],target_root/expected['target_id'],expected)
        outcomes={}; execution_count=0; contract=authority['execution']
        for expected in authority['selection']:
            target=target_root/expected['target_id']; frozen=frozen_targets[expected['target_id']]; records={}
            for tool in TOOLS:
                require(natural.regular_identity(target,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)==frozen,f'target changed before replay: {expected["target_id"]}/{tool}')
                require(tool_identity(natural,paths[tool],authority['tools'][tool])==identities[tool],f'tool changed before replay: {tool}')
                argv=natural.tool_commands(tool,paths[tool],target,4)
                result=natural.run_bounded(argv,cwd=ROOT,timeout=contract['timeout_seconds'],stdout_limit=contract['stdout_limit_bytes'],stderr_limit=contract['stderr_limit_bytes'])
                require(natural.regular_identity(target,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)==frozen,f'target changed after replay: {expected["target_id"]}/{tool}')
                require(tool_identity(natural,paths[tool],authority['tools'][tool])==identities[tool],f'tool changed after replay: {tool}')
                member=stage/'runs'/expected['target_id']/tool
                stdout_path=member/'stdout'; stderr_path=member/'stderr'
                stdout_desc=natural.write_regular(stdout_path,result.stdout); stderr_desc=natural.write_regular(stderr_path,result.stderr)
                record={'argv':argv,'exit_code':result.exit_code,'signal':result.signal,'timeout':result.timeout,'output_limited':result.output_limited,'wall_ns':result.wall_ns,'stdout':{**stdout_desc,'path':stdout_path.relative_to(stage).as_posix()},'stderr':{**stderr_desc,'path':stderr_path.relative_to(stage).as_posix()},'relation_status':'unavailable','relation_addresses':[]}
                if result.exit_code==0 and not result.timeout and not result.output_limited:
                    try:
                        if tool=='x64lens':
                            virtual,offsets=natural.relation_sets_x64lens(result.stdout); record['relation_status']='observed' if virtual else 'observed_zero'; record['virtual_addresses']=sorted(virtual); record['file_offsets']=sorted(offsets)
                        else:
                            addresses=natural.relation_set_baseline(tool,result.stdout); record['relation_status']='observed' if addresses else 'observed_zero'; record['relation_addresses']=sorted(addresses)
                    except BaseException as exc:
                        record['relation_status']='parse_error'; record['parse_error']=str(exc)
                records[tool]=record; execution_count+=1
            outcomes[expected['target_id']]={'target':expected,'tools':records}
        cells=[]
        for baseline in natural.BASELINES:
            for role in natural.ROLES:
                observations=[]
                for expected in [item for item in authority['selection'] if item['role']==role]:
                    x=outcomes[expected['target_id']]['tools']['x64lens']; b=outcomes[expected['target_id']]['tools'][baseline]
                    observation={'target_id':expected['target_id'],'target_sha256':expected['sha256']}
                    if x['relation_status'] not in {'observed','observed_zero'} or b['relation_status'] not in {'observed','observed_zero'}: observation['status']='unavailable'
                    else: observation.update(natural.classify(set(b['relation_addresses']),set(x['virtual_addresses']),set(x['file_offsets'])))
                    observations.append(observation)
                cells.append(natural.cell_result(baseline,role,observations))
        result={'schema':'x64lens-sprint13-natural-frozen-replay-result-v1','sprint':13,'patch':85,'campaign_id':authority['campaign_id'],'predecessor_campaign_id':authority['predecessor_campaign_id'],'evidence_class':'diagnostic','frozen':False,'publication_eligible':False,'authority_sha256':sha(args.authority.resolve(strict=True)),'predecessor_manifest_sha256':authority['input_authority']['manifest_sha256'],'source_authority':source,'tool_identities':identities,'selection_freeze':{'selected_count':12,'role_counts':{role:4 for role in natural.ROLES}},'execution_count':execution_count,'complete_execution_denominator':48,'outcomes':outcomes,'cells':cells,'cell_counts':{state:sum(cell['terminal_state']==state for cell in cells) for state in ('qualified','insufficient','unavailable','mismatch','ambiguous')},'control_count':sum(len(cell['controls']) for cell in cells),'claim_boundary':authority['claim_boundary'],'limitations':authority['limitations']}
        natural.require_structural_complete(result)
        require(natural.authenticate_source_authority(args.source_root,args.source_manifest,args.expected_candidate_tree)==source,'source authority changed during replay')
        natural.write_regular(stage/'manifest.json',canonical(result)); lines=[]
        for path in sorted((item for item in stage.rglob('*') if item.is_file() and item.name!='SHA256SUMS.txt'),key=lambda item:os.fsencode(item.relative_to(stage).as_posix())): lines.append(f'{sha(path)}  {path.relative_to(stage).as_posix()}\n')
        natural.write_regular(stage/'SHA256SUMS.txt',''.join(lines).encode())
        rename_noreplace(stage,result_dir); stage=result_dir; return result
    finally:
        if stage.exists() and stage!=result_dir: shutil.rmtree(stage,ignore_errors=True)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=('selftest','run')); ap.add_argument('--authority',type=Path,default=AUTHORITY); ap.add_argument('--input-dir',type=Path); ap.add_argument('--result-dir',type=Path); ap.add_argument('--x64lens',type=Path); ap.add_argument('--ropgadget',type=Path); ap.add_argument('--ropper',type=Path); ap.add_argument('--ropr',type=Path); ap.add_argument('--source-root',type=Path); ap.add_argument('--source-manifest',type=Path); ap.add_argument('--expected-candidate-tree'); args=ap.parse_args()
    try:
        authority=validate_authority(load(args.authority.resolve(strict=True)))
        if args.action=='selftest':
            result=selftest(authority); print('sprint13-natural-frozen-replay-smoke: ok targets=12 roles=3 tools=4 executions=48 reroll=0 adapters=2 run=deferred'); return 0
        for name in ('input_dir','result_dir','x64lens','ropgadget','ropper','ropr','source_root','source_manifest','expected_candidate_tree'): require(getattr(args,name) is not None,f'--{name.replace("_","-")} is required for run')
        result=run_replay(args,authority); print(f'sprint13-natural-frozen-replay-smoke: ok targets=12 executions={result["execution_count"]}/48 cells=9 controls={result["control_count"]}/108 qualified={result["cell_counts"]["qualified"]} reroll=0 diagnostic=1'); return 0
    except (OSError,subprocess.SubprocessError,json.JSONDecodeError,ReplayError) as exc: fail(str(exc))
if __name__=='__main__': raise SystemExit(main())
