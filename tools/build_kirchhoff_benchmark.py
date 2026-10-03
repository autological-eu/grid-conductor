"""Add source AC reactances to the existing benchmark without changing dispatch inputs."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import pypsa
from fetch_pypsa_benchmark import fetch
ROOT=Path(__file__).resolve().parents[1]
def build():
    directory=ROOT/'public/research/network-benchmark'
    raw=(directory/'input.json').read_bytes();data=json.loads(raw)
    source=pypsa.Network(fetch());source.calculate_dependent_values()
    omitted=[];branches=[]
    for identity,line in source.lines.iterrows():
        if not np.isfinite(line.x_pu_eff) or line.x_pu_eff<=0:
            if line.s_nom!=0:raise ValueError('Unsupported active reactance')
            omitted.append('ac:'+identity);continue
        branches.append(dict(edge_id='ac:'+identity,reactance=float(line.x_pu_eff)))
    data['edges']=[e for e in data['edges'] if e['id'] not in omitted]
    data['schema_version']=3;data['ac_branches']=branches
    data['dataset_id']='pypsa-eur-37-2013-168h-kirchhoff'
    data['provenance']['assumptions'] += [
      'Linearised lossless AC Kirchhoff voltage constraints use source x_pu_eff; controllable HVDC links remain outside AC cycles.',
      'Omitted zero-capacity AC branch ac:3 has infinite source reactance; its fixed zero flow has no baseline/scenario effect. Interventions on it are unsupported.',
      'Exactly one Swedish physical cluster, SE2 0; the identifier does not denote Swedish bidding zone SE2 or SE4.']
    output=directory/'kirchhoff-input.json';payload=(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n').encode();output.write_bytes(payload)
    manifest=dict(parent_input_file_sha256=hashlib.sha256(raw).hexdigest(),input_file_sha256=hashlib.sha256(payload).hexdigest(),ac_branches=len(branches),omitted_zero_capacity_edges=omitted,physics='linearised lossless AC (DC power flow) with controllable HVDC',status='experimental_not_historically_validated')
    (directory/'kirchhoff-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(manifest)
if __name__=='__main__':build()
