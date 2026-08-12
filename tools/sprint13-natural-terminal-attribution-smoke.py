#!/usr/bin/env python3
"""Attribute each natural-coordinate terminal state at its exact evidence layer."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-natural-frozen-replay-v1.json'
EXPECTED=ROOT/'tests/expected/sprint13-natural-terminal-attribution-v1.json'
NATURAL=ROOT/'tools/sprint13-natural-coordinate-campaign.py'

class AttributionError(RuntimeError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise AttributionError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-natural-terminal-attribution-smoke: error: {msg}',file=sys.stderr); raise SystemExit(1)
def strict(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items:
        require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def load(path:Path)->Any: return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict)
def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec); sys.modules[name]=value; spec.loader.exec_module(value); return value

def validate_authority(value:Any)->dict[str,Any]:
    keys={'schema','sprint','patch','campaign_id','predecessor_campaign_id','evidence_class','frozen','publication_eligible','input_authority','selection','tools','adapters','execution','terminal_attribution','claim_boundary','limitations'}
    require(isinstance(value,dict) and set(value)==keys,'attribution authority shape changed')
    require(value['schema']=='x64lens-sprint13-natural-frozen-replay-authority-v1' and value['sprint']==13 and value['patch']==85,'attribution authority identity changed')
    require(value['campaign_id']=='s13-p085-natural-frozen-replay-v1' and value['predecessor_campaign_id']=='s13-p083-natural-coordinate-v1','campaign lineage changed')
    require(value['evidence_class']=='diagnostic' and value['frozen'] is False and value['publication_eligible'] is False,'evidence boundary changed')
    require(len(value['selection'])==12 and len({item['target_id'] for item in value['selection']})==12,'frozen target denominator changed')
    require({item['role'] for item in value['selection']}=={'et_exec','pie_et_dyn','shared_et_dyn'},'frozen roles changed')
    require(value['execution']=={'cache_policy':'uncontrolled_warm_inherited_from_predecessor','execution_denominator':48,'executions_per_target':4,'reroll':False,'stderr_limit_bytes':4194304,'stdout_limit_bytes':16777216,'timeout_seconds':120,'tools':['x64lens','ropgadget','ropper','ropr']},'replay execution contract changed')
    terminal=value['terminal_attribution']
    require(terminal['execution_outcomes']==48 and terminal['relation_outcomes']==48 and terminal['observations']==36 and terminal['cells']==9 and terminal['precedence_mutations']==16,'terminal denominator changed')
    require(terminal['execution_precedence']==['timeout','output_limit','signal','success','unsupported','nonzero_exit'],'execution precedence changed')
    require(value['claim_boundary']=={'comparison_qualified':False,'coverage_claim_authorized':False,'performance_claim_authorized':False,'publication_claim_authorized':False,'public_fields_added':0,'schema_changed':False,'score_changes':0,'semantic_changes':0},'claim boundary changed')
    return value

def execution_reason(record:dict[str,Any],tool:str)->str:
    if record.get('timeout') is True: return 'timeout'
    if record.get('output_limited') is True: return 'output_limit'
    if record.get('signal') is not None: return 'signal'
    if record.get('exit_code')==0: return 'success'
    if tool=='x64lens' and record.get('exit_code')==6: return 'unsupported'
    return 'nonzero_exit'

def precedence_selftest()->int:
    cases=[
      ({'timeout':True,'output_limited':True,'signal':9,'exit_code':0},'x64lens','timeout'),
      ({'timeout':True,'output_limited':False,'signal':None,'exit_code':6},'x64lens','timeout'),
      ({'timeout':False,'output_limited':True,'signal':9,'exit_code':0},'x64lens','output_limit'),
      ({'timeout':False,'output_limited':True,'signal':None,'exit_code':6},'x64lens','output_limit'),
      ({'timeout':False,'output_limited':False,'signal':9,'exit_code':0},'x64lens','signal'),
      ({'timeout':False,'output_limited':False,'signal':15,'exit_code':6},'x64lens','signal'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':0},'x64lens','success'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':0},'ropper','success'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':6},'x64lens','unsupported'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':6},'ropper','nonzero_exit'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':1},'x64lens','nonzero_exit'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':17},'ropr','nonzero_exit'),
      ({'timeout':True,'output_limited':True,'signal':None,'exit_code':None},'ropr','timeout'),
      ({'timeout':False,'output_limited':True,'signal':None,'exit_code':None},'ropr','output_limit'),
      ({'timeout':False,'output_limited':False,'signal':9,'exit_code':None},'ropr','signal'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':127},'ropgadget','nonzero_exit'),
    ]
    for record,tool,expected in cases: require(execution_reason(record,tool)==expected,f'precedence case failed: {tool}/{expected}')
    return len(cases)

def validate_input(input_dir:Path,authority:dict[str,Any])->dict[str,Any]:
    manifest_path=input_dir/'manifest.json'; freeze_path=input_dir/'selection-freeze.json'
    require(manifest_path.is_file() and freeze_path.is_file(),'natural campaign input is incomplete')
    ia=authority['input_authority']
    require(sha(manifest_path)==ia['manifest_sha256'] and sha(freeze_path)==ia['selection_freeze_sha256'],'natural campaign input digest changed')
    result=load(manifest_path); freeze=load(freeze_path)
    natural=module('s13_p085_attribution_natural',NATURAL); natural.require_structural_complete(result)
    require(result['campaign_id']==authority['predecessor_campaign_id'],'natural campaign lineage changed')
    require(result['source_authority']['candidate_tree']==ia['source_candidate_tree'],'natural source tree changed')
    require(result['cell_counts']==ia['cell_counts'],'predecessor cell counts changed')
    selected={item['target_id']:item for item in authority['selection']}
    observed={item['target_id']:item for item in freeze['selected_targets']}
    require(set(selected)==set(observed),'frozen target membership changed')
    for target_id,expected in selected.items():
        current=observed[target_id]
        for key in ('target_id','role','lineage','binary_package','sha256','size_bytes','slot'):
            require(current.get(key)==expected[key],f'frozen target authority changed: {target_id}/{key}')
        target_path=input_dir/'targets'/target_id
        identity=natural.regular_identity(target_path,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)
        require(identity['size_bytes']==expected['size_bytes'],f'frozen target size changed: {target_id}')
    for tool,expected in authority['tools'].items():
        current=result['tool_identities'][tool]
        for key in ('sha256','size_bytes','mode'): require(current.get(key)==expected[key],f'predecessor tool identity changed: {tool}/{key}')
    return result

def attribute(result:dict[str,Any],authority:dict[str,Any])->dict[str,Any]:
    execution_counts={key:0 for key in ('success','unsupported','timeout','output_limit','signal','nonzero_exit')}
    relation_counts={key:0 for key in authority['terminal_attribution']['relation_reasons']}
    for outcome in result['outcomes'].values():
        for tool,record in outcome['tools'].items():
            execution_counts[execution_reason(record,tool)]+=1
            status=record.get('relation_status'); require(status in relation_counts,f'unknown relation terminal reason: {status}')
            relation_counts[status]+=1
    observation_counts={key:0 for key in authority['terminal_attribution']['observation_reasons']}
    cell_counts={key:0 for key in authority['terminal_attribution']['cell_reasons']}
    for cell in result['cells']:
        state=cell['terminal_state']; require(state in cell_counts,f'unknown cell terminal reason: {state}'); cell_counts[state]+=1
        for observation in cell['observations']:
            state=observation.get('status'); require(state in observation_counts,f'unknown observation terminal reason: {state}'); observation_counts[state]+=1
    out={'schema':'x64lens-sprint13-natural-terminal-attribution-result-v1','sprint':13,'patch':85,'campaign_id':result['campaign_id'],'execution_outcomes':sum(execution_counts.values()),'execution_reasons':execution_counts,'relation_outcomes':sum(relation_counts.values()),'relation_reasons':relation_counts,'observations':sum(observation_counts.values()),'observation_reasons':observation_counts,'cells':sum(cell_counts.values()),'cell_reasons':cell_counts,'precedence_mutations':precedence_selftest(),'decision':'terminal_layers_attributed_without_reinterpretation','public_fields_added':0,'semantic_changes':0,'score_changes':0,'schema_changed':False}
    require(out['execution_outcomes']==48 and out['relation_outcomes']==48 and out['observations']==36 and out['cells']==9,'attribution denominator changed')
    return out

def write_noreplace(path:Path,payload:bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o444)
    try:
        view=memoryview(payload)
        while view:
            n=os.write(fd,view); require(n>0,'short attribution write'); view=view[n:]
        os.fchmod(fd,0o444); os.fsync(fd)
    finally: os.close(fd)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=('selftest','run')); ap.add_argument('--authority',type=Path,default=AUTHORITY); ap.add_argument('--expected',type=Path); ap.add_argument('--input-dir',type=Path); ap.add_argument('--output',type=Path); args=ap.parse_args()
    try:
        authority=validate_authority(load(args.authority.resolve(strict=True))); mutations=precedence_selftest()
        if args.action=='selftest':
            require(mutations==16,'precedence mutation denominator changed')
            print('sprint13-natural-terminal-attribution-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 run=deferred')
            return 0
        require(args.input_dir is not None and args.output is not None,'--input-dir and --output are required for run')
        result=attribute(validate_input(args.input_dir.resolve(strict=True),authority),authority)
        if args.expected is not None:
            require(result==load(args.expected.resolve(strict=True)),'terminal attribution differs from expected predecessor result')
        write_noreplace(Path(os.path.abspath(args.output)),(json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
        print('sprint13-natural-terminal-attribution-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 run=complete')
        return 0
    except (OSError,json.JSONDecodeError,AttributionError) as exc: fail(str(exc))
if __name__=='__main__': raise SystemExit(main())
