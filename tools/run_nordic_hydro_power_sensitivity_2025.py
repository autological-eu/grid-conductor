"""Isolated full-year Norwegian run-of-river turbine/profile hypothesis.

This is NOT a water-verified candidate. It adds parallel zero-bid run-of-river
offer capacity with the existing model's hourly profile shape, while leaving
every original offer and fixed reservoir schedule intact.
"""
from __future__ import annotations

import csv
import fcntl
import json
import time

import numpy as np
from scipy.sparse import hstack

from baselines.compact.evaluation import a11_component_lp, offer_groups, physical_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

SOURCE = ROOT/'research/data/zone-tech-power-envelope-2025.csv'
SOURCE_RECEIPT = ROOT/'research/data/zone-tech-power-envelope-2025.json'
POWER = ROOT/'data/bidding-zone-network-2025/zone-tech-power-envelope-v2/hourly.npz'
OUT = ROOT/'data/bidding-zone-network-2025/nordic-ror-power-sensitivity-v2'
SUMMARY = ROOT/'research/data/nordic-ror-power-sensitivity-v2-2025.json'
ZONES = ('NO1','NO2','NO3','NO4')


def candidate(network):
    model = physical_lp() if network == 'original' else a11_component_lp()
    costs, _ = saved_annual()
    schema, data, _ = grouped_fit_inputs()
    summary = json.loads(SOURCE_RECEIPT.read_text())
    if digest(SOURCE) != summary['csv_sha256']:
        raise ValueError('Changed A75 power source')
    if digest(POWER) != summary['hourly_sha256']:
        raise ValueError('Changed dated A75 power witness')
    with np.load(POWER) as archive:
        power_keys=[tuple(map(str,row)) for row in archive['keys']]
        running_peak=archive['demonstrated_running_peak_mw']
    key_index={key:j for j,key in enumerate(power_keys)}
    rows = {(r['zone'],r['technology']):r for r in csv.DictReader(SOURCE.open())}
    grouped, _ = offer_groups(schema,model)
    lookup = {(g['zone'],g['technology']):i for i,g in enumerate(schema['groups'])}
    additions=[]; columns=[]
    first = np.datetime64('2025-01-01T00')
    for zone in ZONES:
        row = rows[zone,'ror']
        original = float(row['original_fleet_nameplate_mw'])
        observed = float(row['observed_peak_mw'])
        if original <= 0 or observed <= original + 1 or int(row['observed_hours']) < 1:
            raise ValueError(f'No matched A75 power evidence for {zone}')
        stamp = np.datetime64(row['first_observed_above_nameplate_utc'].rstrip('Z'))
        start = int((stamp-first)/np.timedelta64(1,'h'))
        if not 0 <= start < 8760:
            raise ValueError('A75 observation outside 2025')
        group = lookup[zone,'ror']
        source_ids = grouped[group]
        if len(source_ids) != 1:
            raise ValueError(f'Expected one isolated run-of-river offer for {zone}')
        old = model['availability'][:,source_ids[0]]
        np.testing.assert_allclose(old,data['capacity'][:,group],atol=1e-5,rtol=0)
        # Dated *running* observed power only: no future-year peak backfill.
        # Separate parallel-facility profile; original offer stays untouched.
        demonstrated=running_peak[:,key_index[zone,'ror']]
        factor=np.where(demonstrated>original+1,demonstrated/original-1,0)
        increase=old*factor
        if np.any(increase[:start]>1e-8) or np.any(np.diff(demonstrated)<-1e-8):
            raise ValueError('A75 power leaked before first observed exceedance')
        if np.any((old==0)&(increase!=0)):
            raise ValueError('Created water in original zero-profile hours')
        columns.append(model['A'][:,source_ids[0]])
        additions.append(dict(zone=zone,technology='ror',source_nameplate_mw=original,
            observed_peak_mw=observed,first_observed_hour=start,
            source_profile_available_twh=float(old.sum()/1e6),
            final_added_turbine_ceiling_mw=float(observed-original),
            added_profile_available_twh=float(increase.sum()/1e6),
            new_availability=increase))
    A=hstack([model['A'][:,:model['ng']],*columns,model['A'][:,model['ng']:]],format='csc')
    candidate_model=model|dict(A=A,ng=model['ng']+len(additions),
        availability=np.column_stack([model['availability'],*[x['new_availability'] for x in additions]]),
        emergency_mask=np.r_[model['emergency_mask'],np.zeros(len(additions),bool)],
        offer_zones=np.r_[model['offer_zones'],list(ZONES)])
    candidate_cost=np.column_stack([costs,np.zeros((8760,len(additions)))])
    return candidate_model,candidate_cost,additions


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if SUMMARY.exists() or any((OUT/f'{n}.npz').exists() for n in ('original','a11')):
            raise FileExistsError('Existing Nordic run-of-river trial')
        _,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs()
        observed=data['observed_prices'];mask=np.isfinite(observed)
        outcomes={}
        for network in ('original','a11'):
            model,costs,additions=candidate(network)
            highs=solver(model,costs)
            values=np.empty((8760,model['A'].shape[1]));duals=np.empty((8760,model['A'].shape[0]))
            objectives=np.empty(8760);residual=0
            started=time.perf_counter()
            for hour in range(8760):
                values[hour],duals[hour],objectives[hour],error=clear_hour(highs,model,costs,hour)
                residual=max(residual,error)
                if objectives[hour]>baseline['objectives'][hour]+.1:
                    raise ValueError('Relaxed candidate raised optimal cost')
            seconds=time.perf_counter()-started
            emergency=float(values[:,:model['ng']][:,model['emergency_mask']].sum())
            if emergency>1e-6 or residual>=1e-4:
                raise ValueError('Full-year RoR trial failed feasibility/no-emergency gate')
            for j,row in enumerate(additions):
                row['added_offer_dispatch_twh']=float(values[:,799+j].sum()/1e6)
                del row['new_availability']
            path=OUT/f'{network}.npz'
            np.savez_compressed(path,values=values,row_duals=duals,objectives=objectives,
                                hours=np.arange(8760),optimal=np.ones(8760,bool))
            prices=duals[:,:model['nz']]
            outcomes[network]=dict(hours=8760,solve_seconds=seconds,
                max_primal_residual_mw=residual,emergency_mwh=emergency,
                added_available_twh=sum(r['added_profile_available_twh'] for r in additions),
                added_dispatch_twh=sum(r['added_offer_dispatch_twh'] for r in additions),
                price_mae_eur_mwh=float(abs(prices[mask]-observed[mask]).mean()),
                witness_sha256=digest(path),zones=additions,
                nordic_price_mae={zone:float(abs(prices[mask[:,j],j]-observed[mask[:,j],j]).mean())
                                  for j,zone in enumerate(model['zones']) if zone in ZONES})
        report=dict(status='unverified_parallel_run_of_river_profile_sensitivity_not_baseline',
            source_a75_review_sha256=digest(SOURCE),source_a75_hourly_sha256=digest(POWER),
            original_baseline_price_mae_eur_mwh=float(abs(baseline['row_duals'][:,:len(schema['zones'])][mask]-observed[mask]).mean()),
            outcomes=outcomes,
            limitations=['Original modeled RoR availability and fixed reservoir water remain unchanged',
                         'Parallel RoR profile assumes additional inflow follows existing per-unit shape; not independently validated',
                         'Observed A75 dispatch is only a dated turbine-power floor, not hourly availability',
                         'Swedish reservoir turbine limit alone changes no fixed hourly schedule',
                         'No bid refit, observed generation mix audit or investment-response validation'])
        SUMMARY.write_text(json.dumps(report,indent=2)+'\n')
        return report


if __name__=='__main__':
    result=run()
    print(json.dumps({k:{field:val for field,val in v.items() if field not in ('zones','nordic_price_mae')}
                      for k,v in result['outcomes'].items()},indent=2))
