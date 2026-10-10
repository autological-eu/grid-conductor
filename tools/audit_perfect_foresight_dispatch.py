"""Rehash and replay saved linked-dispatch witnesses without optimisation."""
import argparse,json
from pathlib import Path
import numpy as np
import pypsa
from perfect_foresight_dispatch import compile_case,build_lp
from european_reservoir_clearing_2025 import setup
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest

def audit(folder):
    result=json.loads((folder/'summary.json').read_text());p=result['provenance']
    if digest(SOURCE)!=p['source'] or digest(Path(__file__).with_name('perfect_foresight_dispatch.py'))!=p['producer']:raise ValueError('Producer/source mismatch')
    for name,value in p['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Dependency mismatch '+name)
    n,ref,_,_,_,_,_=setup();weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu').copy();checks=[]
    for row in result['cases']:
        path=folder/(row['case']+'.npz')
        if digest(path)!=row['witness_sha256']:raise ValueError('Witness mismatch')
        case,m=compile_case(n,ref,p['investments'] if row['case']=='investment' else [],weather)
        extra=len(case.storage_units)-len(p['initial_inventory_mwh']);initial=np.r_[p['initial_inventory_mwh'],np.zeros(extra)]
        lp=build_lp(case,m,p['start_hour'],p['start_hour']+p['hours'],initial,initial)
        with np.load(path,allow_pickle=False) as f:values=f['values'].copy()
        x=values.ravel();activity=lp['A']@x
        residual=max(float(np.maximum(lp['lower']-x,0).max()),float(np.maximum(x-lp['upper'],0).max()),float(np.maximum(lp['row_lower']-activity,0).max()),float(np.maximum(activity-lp['row_upper'],0).max()))
        objective=float(lp['cost']@x);difference=objective-row['objective']
        if residual>1e-4 or abs(difference)>max(.05,abs(objective)*1e-8):raise ValueError('Saved primal replay failed')
        checks.append(dict(case=row['case'],maximum_primal_residual=residual,objective_difference_eur=difference,emergency_supply_mwh=float(values[:,:m['ng']][:,m['emergency_mask']].sum()),witness_sha256=digest(path)))
    return dict(summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),checks=checks)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    value=audit(args.folder);args.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
