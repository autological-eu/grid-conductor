"""Rebuild bids and replay saved daily network/water witnesses without solving."""
import argparse
import json
from pathlib import Path

import numpy as np
import pypsa

from daily_market_clearing import write_json, residual, TOL
from simple_daily_market import daily_lp, native_day
from simple_resource_bids import prepare_storage, storage_bids, compile_case, ROOT
from european_reservoir_clearing_2025 import setup, REFERENCE
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest


def audit(folder,native=False):
    folder=Path(folder);summary=json.loads((folder/'summary.json').read_text());p=summary['provenance']
    if digest(SOURCE)!=p['source'] or digest(ROOT/'tools/simple_daily_market.py')!=p['producer']:
        raise ValueError('Source/producer changed')
    if digest(REFERENCE/'annual-state.npz')!=p['boundary_sha256']:raise ValueError('Boundary source changed')
    if digest(ROOT/p['cost_source']['path'])!=p['cost_source']['sha256']:raise ValueError('Cost source changed')
    for name,sha in p['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Dependency changed '+name)
    market=None
    if p['price_inputs_sha256'] is not None:
        path=folder/'fuel-inputs.json';market=json.loads(path.read_text())
        # Copy is canonicalised; compare the saved original semantic content hash separately.
        if digest(path)!=p['saved_price_inputs_sha256']:raise ValueError('Price input changed')
    n,reference,_,_,_,_,_=setup();weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu')
    checks=[]
    for row in summary['cases']:
        root=folder/row['case'];case,m,_=compile_case(n,reference,p['investments'] if row['case']=='investment' else [],
                                                     weather,p['settings'],p['thermal_assumptions'],market)
        current=np.r_[p['initial_inventory_mwh'],np.zeros(len(case.storage_units)-len(p['initial_inventory_mwh']))]
        terminal=current.copy();ns=len(case.storage_units);nb=m['A'].shape[1]
        path=root/'preparation.npz'
        if digest(path)!=row['preparation_sha256']:raise ValueError('Preparation changed')
        with np.load(path,allow_pickle=False) as a: saved={k:a[k].copy() for k in a.files}
        prepared=prepare_storage(case,m,saved['forecast'],current,terminal,p['settings'])
        for key,value in saved.items():np.testing.assert_allclose(prepared[key],value,atol=1e-10,rtol=0)
        max_primal=0.;max_water=0.;max_join=0.;operating=0.;bidtotal=0.;shortage=0.;native_checks=[]
        for day,start in enumerate(range(0,p['hours'],24)):
            path=root/f'{day:03d}.npz';receipt=root/f'{day:03d}.json';r=json.loads(receipt.read_text())
            if digest(receipt)!=row['receipts_sha256'][receipt.name] or digest(path)!=r['witness_sha256']:
                raise ValueError('Daily witness/receipt changed')
            if r['start_hour']!=start or r['end_hour']!=start+24 or r['day']!=day:raise ValueError('Calendar changed')
            with np.load(path,allow_pickle=False) as a: witness={k:a[k].copy() for k in a.files}
            join=float(abs(current-witness['initial']).max());max_join=max(max_join,join)
            if join>TOL:raise ValueError('Broken inventory carry')
            bids=storage_bids(case,m,start,start+24,current,terminal,prepared,p['settings'])
            for key,value in bids.items():
                if isinstance(value,np.ndarray):np.testing.assert_allclose(value,witness[key],atol=1e-10,rtol=0)
            if bids['operators']!=r['bid_rules']:raise ValueError('Bid rule declaration changed')
            lp=daily_lp(case,m,start,start+24,current,terminal,bids);v=witness['values'];prices=witness['prices']
            if v.shape!=(24,lp['width']) or prices.shape!=(24,m['nz']) or not np.isfinite(v).all() or not np.isfinite(prices).all():
                raise ValueError('Invalid primal/price shape or values')
            max_primal=max(max_primal,residual(lp,v.ravel()))
            c=v[:,nb:nb+ns];d=v[:,nb+ns:nb+2*ns];soc=v[:,nb+2*ns:nb+3*ns];spill=v[:,nb+3*ns:]
            water=float(abs(soc-np.vstack([current,soc[:-1]])*lp['phi']-c*lp['eta_c']+d/lp['eta_d']-lp['inflow']+spill).max())
            max_water=max(max_water,water)
            if max_primal>TOL or water>TOL or np.any((c>1e-6)&(d>1e-6)):raise ValueError('Physical replay failed')
            cost=float(lp['operating_cost']@v.ravel());bid=float(lp['cost']@v.ravel())
            for value,key in [(cost,'operating_cost_eur'),(bid,'bid_objective_eur')]:
                if abs(value-r[key])>max(.05,abs(value)*1e-8):raise ValueError('Objective replay failed')
            operating+=cost;bidtotal+=bid;shortage+=float(v[:,:m['ng']][:,m['emergency_mask']].sum())
            if native and day in {0,p['hours']//48,p['hours']//24-1}:
                check=native_day(case,m,start,start+24,current,bids);difference=check['bid_objective_eur']-bid
                if abs(difference)>max(.05,abs(bid)*1e-8):raise ValueError('Native full bid mismatch')
                native_checks.append(dict(day=day,difference_eur=difference,
                                           price_maximum_difference_eur_mwh=float(abs(check['prices']-prices).max())))
            cap=(case.storage_units.p_nom*case.storage_units.max_hours).values
            current=np.minimum(np.maximum(soc[-1],0),cap)
        closure=float(abs(current-terminal).max())
        if closure>TOL:raise ValueError('Closure failed')
        for actual,key in [(operating,'operating_cost_eur'),(bidtotal,'bid_objective_eur')]:
            if abs(actual-row[key])>max(.05,abs(actual)*1e-8):raise ValueError('Summary objective changed')
        checks.append(dict(case=row['case'],maximum_primal_residual=max_primal,maximum_water_residual=max_water,
                           maximum_join_residual_mwh=max_join,closure_residual_mwh=closure,
                           operating_cost_eur=operating,bid_objective_eur=bidtotal,
                           emergency_supply_mwh=shortage,native_checks=native_checks))
    return dict(status='saved_daily_rules_and_physics_replayed',summary_sha256=digest(folder/'summary.json'),
                checker_sha256=digest(__file__),checks=checks,
                scope='Rule reproduction and chronological primal replay; forecast optimality not independently re-solved; no annual optimum/empirical/integration claim')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--native',action='store_true')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    write_json(args.output,audit(args.folder,args.native))
