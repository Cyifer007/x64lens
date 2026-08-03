#!/usr/bin/env python3
"""Validate the active Sprint 12 Patch 075 continuation authority."""
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
def main()->int:
    try:
        a=load(AUTH); stages=load(STAGES)
        require(type(a.get('schema_version')) is int and a['schema_version']==1,'schema_version')
        require(type(a.get('sprint')) is int and a['sprint']==12,'sprint')
        require(a.get('status')=='active','Sprint 12 must be active')
        require(type(a.get('current_patch')) is int and a['current_patch']==75,'current_patch')
        require(type(a.get('superseded_closeout_patch')) is int and a['superseded_closeout_patch']==74,'superseded closeout')
        require(a.get('next_patch')==76 and a.get('acceptance_target')=='sprint12-p075-acceptance-smoke','next/acceptance')
        require(stages.get('completed_sprints')==11 and stages.get('active_sprint')==12,'stage chronology')
        b=a.get('patch075_boundary'); require(isinstance(b,dict),'boundary')
        require(b.get('remaining_patch074_corrections') is True,'corrections')
        require(b.get('private_dynamic_metadata_sidecar') is True,'sidecar')
        require(type(b.get('textrel_carrier_capacity')) is int and b['textrel_carrier_capacity']==64,'carrier cap')
        require(b.get('textrel_state')=='private' and b.get('public_fields_added')==0,'public boundary')
        require(b.get('existing_coarse_pie_field_reinterpreted') is False and b.get('runtime_cet_enforcement_claimed') is False and b.get('schema_changed') is False,'policy boundary')
        for rel in a.get('required_documents',[]): require((ROOT/rel).is_file(),f'missing {rel}')
        s12=(ROOT/'docs/sprints/sprint-12-plan.md').read_text(); s13=(ROOT/'docs/sprints/sprint-13-plan.md').read_text()
        require('Active at Patch 075' in s12,'Sprint 12 active marker')
        require('Planned semantic capability completion sprint' in s13,'Sprint 13 planned marker')
    except (OSError,json.JSONDecodeError,Error) as exc:
        print(f'sprint12-continuation-smoke: error: {exc}',file=sys.stderr); return 1
    print('sprint12-continuation-smoke: ok sprint=12 status=active patch=75 textrel=private public_fields_added=0 next_patch=76')
    return 0
if __name__=='__main__': raise SystemExit(main())
