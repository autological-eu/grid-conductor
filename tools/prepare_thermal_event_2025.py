"""Seal the current oil/CHP physical book for a bounded January experiment."""
import json,logging
from pathlib import Path
import numpy as np
from scipy.sparse import save_npz
from oil_supply_2025 import ROOT,anchor,inputs,compile_case as original_case
from oil_chp_bids_2025 import source_inputs,compile_case
from bid_calibration_2025 import immutable_hashes
from generation_mix_2025 import digest

OUT=ROOT/'data/bidding-zone-network-2025/thermal-event-v1'
MODEL=ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2'
START=12*24;STOP=22*24

def write(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def prepare():
    OUT.mkdir(exist_ok=False)
    s=json.loads((MODEL/'summary.json').read_text());a=json.loads((MODEL/'verification-v2/audit.json').read_text());assert a['status']=='passed' and a['summary_sha256']==digest(MODEL/'summary.json')
    n,base,off,m,ctx,layout,c,flow,target=anchor()
    monthly,daily,co2,assumption,additions,oil=inputs(n,m,layout)
    ref,_=original_case(m,ctx,c,monthly,daily,co2,assumption,additions,oil,'capacity_and_daily_oil')
    source=source_inputs(n,ref,layout,oil,additions);case,extras=compile_case(ref,source,daily,assumption,'chp25')
    assert immutable_hashes(case,flow)==s['outcomes']['chp25']['physical_inputs']
    assert extras==json.loads((MODEL/'tranches.json').read_text())['chp25']
    group={}
    for j,(family,ids,parent) in enumerate(zip(layout['kinds'],layout['members'],layout['parent'],strict=True)):
        if family not in ['gas','coal']:continue
        carriers=sorted(set(n.generators.iloc[ids].carrier));assert len(carriers)==1,carriers
        key=(str(case['offer_zones'][j]),carriers[0],parent)
        group.setdefault(key,[]).append(j)
    groups=[]
    for (zone,fuel,parent),cols in group.items():
        av=case['availability'][:,cols].sum(axis=1);assert np.ptp(av)<1e-6
        groups.append(dict(zone=zone,carrier=fuel,parent=int(parent),columns=cols,capacity_mw=float(av.max())))
    columns=[]
    for j,ids in enumerate(layout['members']):columns.append(dict(column=j,carriers=sorted(set(n.generators.iloc[ids].carrier)),zone=str(case['offer_zones'][j])))
    for j in range(len(columns),case['ng']):columns.append(dict(column=j,carriers=['oil'],zone=str(case['offer_zones'][j])))
    witness=MODEL/'chp25.npz';assert digest(witness)==s['annuals']['chp25']['witness_sha256']
    with np.load(witness) as z:x=z['values'][START-1:STOP];y=z['row_duals'][START:STOP];obj=z['objectives'][START:STOP];assert z['optimal'].all()
    targets=ROOT/'data/price-trace/sdac-hourly-2025-v1';pa=json.loads((targets/'audit.json').read_text());assert pa['summary_sha256']==digest(targets/'summary.json')
    with np.load(targets/'prices.npz') as z:observed=z['prices'][START:STOP]
    arrays={k:case[k][START:STOP] for k in ['availability','cost','load','island_rhs','link_min','link_max']}
    arrays.update(flow=flow[START:STOP],ratings=case['ratings'],emergency_mask=case['emergency_mask'],baseline=x[1:],initial=x[0],baseline_duals=y,baseline_objectives=obj,observed=observed)
    np.savez_compressed(OUT/'inputs.npz',**arrays);save_npz(OUT/'network.npz',case['A'])
    sources={str(p.relative_to(ROOT)):digest(p) for p in [MODEL/'summary.json',MODEL/'verification-v2/audit.json',witness,targets/'summary.json',targets/'audit.json',targets/'prices.npz',ROOT/'config/thermal-event-2025.json']}
    write(OUT/'inputs.json',dict(status='current_chp25_physical_book_reconstructed',hours=STOP-START,start_hour=START,stop_hour=STOP,zones=case['zones'],ng=case['ng'],nl=case['nl'],nz=case['nz'],islands=len(case['islands']),groups=groups,columns=columns,producer_sha256=digest(__file__),source_hashes=sources,physical_inputs=s['outcomes']['chp25']['physical_inputs'],files={name:digest(OUT/name) for name in ['inputs.npz','network.npz']}))
    print('Sealed',STOP-START,'hours',len(groups),'thermal groups',case['A'].shape,flush=True)
if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);prepare()
