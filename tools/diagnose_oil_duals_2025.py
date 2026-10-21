"""Compare every saved oil-control price and objective, including unobserved areas."""
import argparse, json
from pathlib import Path
import numpy as np
from generation_mix_2025 import digest


def run(folder):
    summary=json.loads((folder/'summary.json').read_text())
    changes={}; baseline=None; objectives=None
    for name,info in summary['annuals'].items():
        path=folder/info['witness']; assert digest(path)==info['witness_sha256']
        with np.load(path) as z:
            prices=z['row_duals'][:,:len(summary['zones'])]; obj=z['objectives']
        if name=='control': baseline=prices; objectives=obj
        delta=prices-baseline
        eligible=np.array([r['known_hours']==8760 for r in summary['outcomes'][name]['prices']['zones']])
        rows=[]
        for t,j in np.argwhere(abs(delta)>1e-5):
            rows.append(dict(utc=str(np.datetime64('2025-01-01T00')+np.timedelta64(int(t),'h')),zone=summary['zones'][j],
                eligible_observed_price=bool(eligible[j]),control=float(baseline[t,j]),trial=float(prices[t,j])))
        changes[name]=dict(maximum_all_area_change=float(abs(delta).max()),maximum_eligible_change=float(abs(delta[:,eligible]).max()),
                           maximum_objective_change_eur=float(abs(obj-objectives).max()),changed_price_cells=rows)
    out=dict(summary_sha256=digest(folder/'summary.json'),producer_sha256=digest(__file__),changes=changes)
    (folder/'price-witness-comparison.json').write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);run(p.parse_args().folder.resolve())
