#!/usr/bin/env python3
"""Validate the sealed lifecycle prefix and nondecreasing evidence denominators."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-lifecycle-denominator-authority-v1.json'
DEFAULT_EXPECTED=ROOT/'tests/expected/sprint13-lifecycle-denominator-authority-v1.json'

class LifecycleError(RuntimeError): pass

def require(ok:bool,msg:str)->None:
    if not ok: raise LifecycleError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-lifecycle-denominator-smoke: error: {msg}',file=sys.stderr); raise SystemExit(1)
def strict(pairs:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in pairs:
        require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def load(path:Path)->Any: return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict)

def validate(value:Any)->dict[str,Any]:
    require(isinstance(value,dict) and set(value)=={'schema','sprint','patch','purpose','sealed_prefix','successor_deltas','negative_lineage','denominator_floors','policy','limitations'},'authority shape changed')
    require(value['schema']=='x64lens-sprint13-lifecycle-denominator-authority-v1' and value['sprint']==13 and value['patch']==84,'authority identity changed')
    prefix=value['sealed_prefix']
    require(prefix=={'aliases':29,'canonical_leaves':30,'canonical_roots':20,'events':87,'folds':2,'lineage_records':161,'next_event':88,'through_patch':79,'tombstones':15},'sealed prefix changed')
    deltas=value['successor_deltas']
    require(isinstance(deltas,list) and [d['patch'] for d in deltas]==[80,81,82,83],'successor patch sequence changed')
    require(all(set(d)=={'patch','status','new_canonical_roots','new_canonical_leaves','new_aliases','new_folds','new_tombstones','new_events','summary'} for d in deltas),'successor delta shape changed')
    require(all(d['status']=='unsealed_explicit_delta' for d in deltas),'successor delta status changed')
    require(all(all(type(d[key]) is int and d[key]>=0 for key in ('new_canonical_roots','new_canonical_leaves','new_aliases','new_folds','new_tombstones','new_events')) for d in deltas),'successor delta counts invalid')
    require(all(sum(d[key] for d in deltas)==0 for key in ('new_canonical_roots','new_canonical_leaves','new_aliases','new_folds','new_tombstones','new_events')),'unsealed patches silently changed canonical counts')
    negative=value['negative_lineage']
    require(negative['canonical_tombstones_retained']==15 and negative['reopening_requires_explicit_authority'] is True,'negative lineage changed')
    require(negative['noncanonical_aliases']==[{'canonical_tombstone':False,'disposition':'rejected_negative_alias','id':'P083-N01-redundant-ordered-two-pop-tuple'}],'negative alias changed')
    floors=value['denominator_floors']
    require(isinstance(floors,dict) and len(floors)==24,'denominator floor set changed')
    require(all(type(v) is int and v>0 for v in floors.values()),'denominator floors must be positive integers')
    required={'candidate_capacity':4096,'batch_transaction_cases':29,'batch_transaction_executions':87,'role_property_objects':96,'role_property_private_probe_executions':288,'role_property_public_command_executions':384,'role_property_field_dispositions':1728,'role_property_eligible_matches':1224,'natural_coordinate_targets':12,'natural_coordinate_executions':48,'natural_coordinate_cells':9,'natural_coordinate_controls':108,'workload_confirmation_batches':162,'workload_confirmation_members':3402,'abi_role_queries':36,'abi_role_public_closures':96}
    require(all(floors.get(k)==v for k,v in required.items()),'material denominator floor changed')
    policy=value['policy']
    require(policy=={'denominator_decrease_authorized':False,'event_88_authorized':False,'new_canonical_ids_authorized':False,'provisional_items_must_not_disappear':True,'public_fields_added':0,'schema_changed':False,'score_changes':0,'semantic_changes':0,'supersession_requires_named_authority':True},'lifecycle policy changed')
    return value

def mutation_rejections(value:dict[str,Any])->int:
    mutations=[]
    for field in ('canonical_roots','canonical_leaves','aliases','folds','tombstones','lineage_records','events'):
        m=copy.deepcopy(value); m['sealed_prefix'][field]-=1; mutations.append(m)
    m=copy.deepcopy(value); m['successor_deltas'].pop(); mutations.append(m)
    m=copy.deepcopy(value); m['successor_deltas'][0]['new_events']=1; mutations.append(m)
    m=copy.deepcopy(value); m['denominator_floors']['natural_coordinate_executions']=47; mutations.append(m)
    m=copy.deepcopy(value); m['policy']['event_88_authorized']=True; mutations.append(m)
    m=copy.deepcopy(value); m['negative_lineage']['canonical_tombstones_retained']=16; mutations.append(m)
    rejected=0
    for mutation in mutations:
        try: validate(mutation)
        except LifecycleError: rejected+=1
        else: raise LifecycleError('lifecycle mutation was accepted')
    require(rejected==12,'mutation denominator changed')
    return rejected

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--authority',type=Path,default=DEFAULT_AUTHORITY); ap.add_argument('--expected',type=Path,default=DEFAULT_EXPECTED); args=ap.parse_args()
    try:
        value=validate(load(args.authority)); rejected=mutation_rejections(value); p=value['sealed_prefix']
        result={'schema':'x64lens-sprint13-lifecycle-denominator-result-v1','sprint':13,'patch':84,'sealed_roots':p['canonical_roots'],'sealed_leaves':p['canonical_leaves'],'sealed_aliases':p['aliases'],'sealed_folds':p['folds'],'sealed_tombstones':p['tombstones'],'sealed_lineage_records':p['lineage_records'],'sealed_events':p['events'],'successor_deltas':len(value['successor_deltas']),'denominator_floors':len(value['denominator_floors']),'mutation_rejections':rejected,'event_88_authorized':value['policy']['event_88_authorized'],'new_canonical_ids_authorized':value['policy']['new_canonical_ids_authorized'],'decision':'prefix_and_successor_deltas_preserved'}
        require(result==load(args.expected),'lifecycle result differs from expected authority')
    except (OSError,json.JSONDecodeError,LifecycleError) as exc: fail(str(exc))
    print('sprint13-lifecycle-denominator-smoke: ok roots=20 leaves=30 aliases=29 folds=2 tombstones=15 lineage=161 events=87 successor_deltas=4 floors=24 mutations=12 event88=0 new_ids=0')
    return 0
if __name__=='__main__': raise SystemExit(main())
