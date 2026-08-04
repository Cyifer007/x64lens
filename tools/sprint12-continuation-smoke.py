#!/usr/bin/env python3
"""Validate the active Sprint 12 Patch 076 continuation authority."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
AUTH=ROOT/'tests/expected/sprint12-continuation.json'
STAGES=ROOT/'tests/expected/research-stage-gates.json'
class Error(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Error(m)
def strict(pairs:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in pairs:
        require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(),object_pairs_hook=strict); require(isinstance(v,dict),f'{p.name} must be object'); return v
def exact_int(v:Any,n:int,label:str)->None:
    require(type(v) is int and v==n,label)
def main()->int:
    try:
        a=load(AUTH); stages=load(STAGES)
        exact_int(a.get('schema_version'),1,'schema_version')
        exact_int(a.get('sprint'),12,'sprint')
        require(a.get('status')=='active','Sprint 12 must be active')
        exact_int(a.get('current_patch'),76,'current_patch')
        exact_int(a.get('superseded_closeout_patch'),74,'superseded closeout')
        exact_int(a.get('next_patch'),77,'next_patch')
        require(a.get('acceptance_target')=='sprint12-p076-acceptance-smoke','acceptance target')
        require(stages.get('completed_sprints')==11 and stages.get('active_sprint')==12,'stage chronology')
        b=a.get('patch076_boundary'); require(isinstance(b,dict),'boundary')
        require(b.get('remaining_patch075_corrections') is True,'corrections')
        require(b.get('private_dynamic_metadata_sidecar') is True,'sidecar')
        exact_int(b.get('mixed_carrier_capacity'),64,'mixed carrier cap')
        exact_int(b.get('search_record_capacity'),64,'search record cap')
        exact_int(b.get('search_value_byte_capacity'),4096,'search byte cap')
        require(b.get('textrel_state')=='private','textrel state')
        require(b.get('rpath_state')=='private_distinct' and b.get('runpath_state')=='private_distinct','path state separation')
        require(b.get('path_splitting') is False and b.get('origin_expansion') is False,'path interpretation boundary')
        exact_int(b.get('target_derived_opens'),0,'target-derived opens')
        exact_int(b.get('public_fields_added'),0,'public fields')
        require(b.get('existing_coarse_pie_field_reinterpreted') is False and b.get('runtime_cet_enforcement_claimed') is False and b.get('schema_changed') is False,'public policy boundary')
        for rel in a.get('required_documents',[]): require((ROOT/rel).is_file(),f'missing {rel}')
        s12=(ROOT/'docs/sprints/sprint-12-plan.md').read_text(); s13=(ROOT/'docs/sprints/sprint-13-plan.md').read_text()
        require('Active at Patch 076' in s12,'Sprint 12 active marker')
        require('Planned semantic capability completion sprint' in s13,'Sprint 13 planned marker')
    except (OSError,json.JSONDecodeError,Error) as exc:
        print(f'sprint12-continuation-smoke: error: {exc}',file=sys.stderr); return 1
    print('sprint12-continuation-smoke: ok sprint=12 status=active patch=76 textrel=private rpath=private runpath=private public_fields_added=0 next_patch=77')
    return 0
if __name__=='__main__': raise SystemExit(main())
