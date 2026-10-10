"""Native PyPSA checks of the entire daily bid objective, with free end inventory."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa
from daily_market_clearing import ROOT, THROUGHPUT_COST
from perfect_foresight_dispatch import compile_case
from european_reservoir_clearing_2025 import setup
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest


def native_policy(n,m,start,end,initial,policy):
    p=n.copy(snapshots=n.snapshots[start:end]);p.remove('GlobalConstraint',p.global_constraints.index)
    p.storage_units.cyclic_state_of_charge=False
    p.storage_units.state_of_charge_initial=pd.Series(initial,index=p.storage_units.index)
    p.storage_units.marginal_cost+=THROUGHPUT_COST
    p.storage_units_t.p_min_pu=pd.DataFrame(-policy['charge_max'][start:end]/p.storage_units.p_nom.values,
                                         index=p.snapshots,columns=p.storage_units.index)
    p.storage_units_t.p_max_pu=pd.DataFrame(policy['discharge_max'][start:end]/p.storage_units.p_nom.values,
                                         index=p.snapshots,columns=p.storage_units.index)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.storage_units.bus=p.storage_units.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators_t.marginal_cost=pd.DataFrame(m['native_cost'][start:end],index=p.snapshots,columns=p.generators.index)
    p.remove('Load',p.loads.index)
    for j,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=pd.Series(m['load'][start:end,j],index=p.snapshots))
    dist={}
    for z,weights in m['weights'].items():
        dist[z]=[]
        for bus,w in weights.items():
            name='redistribute:'+z+':'+bus;dist[z].append((name,w))
            p.add('Link',name,bus0='zone:'+z,bus1=bus,p_nom=1e6,p_min_pu=-1,efficiency=1)
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,ids in dist.items():
            total=v.sel(name=[name for name,_ in ids]).sum('name')
            for name,w in ids:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
        terminal=net.model['StorageUnit-state_of_charge'].sel(snapshot=snapshots[-1])
        def labelled(a):return pd.Series(a,index=p.storage_units.index).rename_axis('name').to_xarray()
        net.model.add_constraints(terminal>=labelled(policy['reachable_lower'][end]),name='reachable-lower')
        net.model.add_constraints(terminal<=labelled(policy['reachable_upper'][end]),name='reachable-upper')
        credit=(labelled(policy['future_value'][end-1])*terminal).sum('name')
        net.model.add_objective(net.model.objective.expression-credit,overwrite=True)
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':180},extra_functionality=extra)
    if status!='ok' or condition!='optimal':raise ValueError('Native daily policy solve failed')
    return float(p.objective),p.buses_t.marginal_price[['zone:'+z for z in m['zones']]].values


def verify(folder):
    s=json.loads((folder/'summary.json').read_text());provenance=s['provenance']
    if digest(SOURCE)!=provenance['source'] or digest(ROOT/'tools/daily_market_clearing.py')!=provenance['producer']:
        raise ValueError('Producer/source changed')
    n,ref,_,_,_,_,_=setup();weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu').copy()
    checks=[]
    for row in s['cases']:
        case,m=compile_case(n,ref,provenance['investments'] if row['case']=='investment' else [],weather)
        root=folder/row['case']
        if digest(root/'policy.npz')!=row['policy_sha256']:raise ValueError('Policy changed')
        with np.load(root/'policy.npz',allow_pickle=False) as f:policy={k:f[k].copy() for k in f.files}
        for day in sorted({0,provenance['hours']//24//2,provenance['hours']//24-1}):
            r=json.loads((root/f'{day:03d}.json').read_text());path=root/f'{day:03d}.npz'
            if digest(path)!=r['witness_sha256']:raise ValueError('Daily witness changed')
            with np.load(path,allow_pickle=False) as f:initial=f['initial'].copy();custom_prices=f['prices'].copy()
            objective,prices=native_policy(case,m,day*24,(day+1)*24,initial,policy)
            difference=objective-r['bid_objective']
            if abs(difference)>max(.05,abs(objective)*1e-8):raise ValueError('Native full bid objective mismatch')
            checks.append(dict(case=row['case'],day=day,native_bid_objective_eur=objective,
                               difference_eur=difference,price_mae_eur_mwh=float(abs(prices-custom_prices).mean()),
                               price_maximum_difference_eur_mwh=float(abs(prices-custom_prices).max())))
            print(row['case'],day,'native full bid objective difference',difference,flush=True)
    return dict(status='sampled_native_full_daily_bid_objectives_verified',
                summary_sha256=digest(folder/'summary.json'),checker_sha256=digest(__file__),checks=checks,
                scope='Free daily closing inventory, same terminal value and reachability/mode policy; no annual bidding equilibrium or native annual optimum claim')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(args.folder);args.output.write_text(json.dumps(result,indent=2)+'\n')
