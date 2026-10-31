"""Joint A75 fleet, A11 network, and bounded hydro timing trial.

Frozen inherited bid curves are deliberately retained. This is a candidate,
not a baseline promotion or a verified turbine-capacity reconstruction.
"""
from __future__ import annotations

import csv
import json
import logging
import time

import numpy as np

from baselines.compact.evaluation import saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.nordic_storage import WATER, sha, sources
from baselines.compact.source import ROOT, grouped_fit_inputs
from tools.run_generation_power_lp_2025 import candidate as generation_candidate
from tools.test_europe_seasonal_water_value_2025 import exact_hourly_schedule, island_safe_basis, load_water

OUT=ROOT/'data/bidding-zone-network-2025/combined-model-update-v2'
SUMMARY=ROOT/'research/data/combined-model-update-v2-2025.json'
REFERENCE=ROOT/'data/bidding-zone-network-2025/generation-power-lp-v2/a11.npz'
REFERENCE_SUMMARY=ROOT/'research/data/generation-power-lp-v2-2025.json'
POWER_CSV=ROOT/'research/data/zone-tech-power-envelope-2025.csv'
POWER_RECEIPT=ROOT/'research/data/zone-tech-power-envelope-2025.json'
POWER_HOURLY=ROOT/'data/bidding-zone-network-2025/zone-tech-power-envelope-v2/hourly.npz'


def corrected_turbines(native,units,allocation):
    """Dated zonal A75 minimum assigned to one pure-zone Swedish unit.

    This is a provisional allocation for a sensitivity, not plant-level evidence.
    """
    receipt=json.loads(POWER_RECEIPT.read_text())
    if sha(POWER_CSV)!=receipt['csv_sha256'] or sha(POWER_HOURLY)!=receipt['hourly_sha256']:
        raise ValueError('Changed A75 turbine-power evidence')
    rows={r['zone']:r for r in csv.DictReader(POWER_CSV.open()) if r['technology']=='reservoir'}
    with np.load(POWER_HOURLY) as archive:
        keys=[tuple(map(str,row)) for row in archive['keys']]
        peak=archive['demonstrated_running_peak_mw']
    index={key:i for i,key in enumerate(keys)}
    limits=np.broadcast_to(units.p_nom.to_numpy(),(8760,len(units))).copy()
    details=[]
    for zone in ('SE2','SE3','SE4'):
        row=rows[zone]
        source=float(row['original_fleet_nameplate_mw'])
        observed=float(row['observed_peak_mw'])
        if observed<=source+1 or int(row['observed_hours'])<1:
            raise ValueError(f'No matched A75 reservoir peak above source in {zone}')
        pure=[]
        for j,name in enumerate(units.index):
            assigned={native.buses.loc[bus,'bidding_zone']:share for bus,share in allocation[name].items()
                      if share>1e-5}
            if len(assigned)==1 and assigned.get(zone,0)>1-1e-8:
                pure.append(j)
        if not pure:
            raise ValueError(f'No pure-zone reservoir unit for {zone}')
        target=max(pure,key=lambda j:units.p_nom.iloc[j])
        running=peak[:,index[zone,'reservoir']]
        extra=np.maximum(0.,np.nan_to_num(running,nan=0.)-source)
        if np.max(extra)<observed-source-1e-4 or np.any(np.diff(extra)<-1e-6):
            raise ValueError('A75 reservoir ceiling is not a dated running peak')
        limits[:,target]+=extra
        details.append(dict(zone=zone,source_zone_turbine_mw=source,
                            observed_peak_mw=observed,incremental_turbine_mw=float(extra.max()),
                            assigned_unit=str(units.index[target]),
                            first_eligible_hour=int(np.flatnonzero(extra>0)[0])))
    return limits,details


def prepare():
    model,cost,review=generation_candidate('a11')
    receipt=json.loads(REFERENCE_SUMMARY.read_text())
    if sha(REFERENCE)!=receipt['outcomes']['a11']['witness_sha256']:
        raise ValueError('Changed generation+A11 witness')
    with np.load(REFERENCE) as archive:
        reference_prices=archive['row_duals'][:,:model['nz']].copy()
    native,original,_,_,allocation=sources()
    units=original.storage_units.query("carrier=='hydro'")
    water,no_ids=load_water(original,units)
    shares,branch,island_drift=island_safe_basis(native,units,allocation,model['zones'])
    turbines,turbine_details=corrected_turbines(native,units,allocation)
    signal=reference_prices@shares.T
    change=np.zeros_like(water['power'])
    eligible=[];skipped=[]
    for j,name in enumerate(units.index):
        if island_drift[j]>1e-10:
            skipped.append(dict(unit=name,reason='physical_island_shift'))
            continue
        if water['capacity'][j]<=1 or water['power'][:,j].sum()<=1:
            skipped.append(dict(unit=name,reason='no_storage_or_generation'))
            continue
        single={key:value[:,j] if value.ndim==2 else value[j] for key,value in water.items()}
        proposed,_=exact_hourly_schedule(single,turbines[:,j],signal[:,j])
        change[:,j]=proposed
        eligible.append(name)
    if len(eligible)!=79:
        raise ValueError('Changed European hydro candidate coverage')
    return model,cost,review,water,units,change,shares,branch,reference_prices,eligible,skipped,turbines,turbine_details


def run():
    if SUMMARY.exists() or (OUT/'annual.npz').exists():
        raise FileExistsError('Combined annual witness already exists')
    model,cost,review,water,units,change,shares,branch,reference_prices,eligible,skipped,turbines,turbine_details=prepare()
    _,baseline=saved_annual()
    schema,data,_=grouped_fit_inputs()
    observed=data['observed_prices'];mask=np.isfinite(observed)
    updated=model|dict(load=model['load'].copy(),flow=model['flow'].copy())
    highs=solver(updated,cost)
    solved=None
    started=time.perf_counter()
    for scale in (1.,.5,.25,.125,.0625,.03125):
        updated['load'][:]=model['load']-scale*(change@shares)
        updated['flow'][:]=model['flow']+scale*(change@branch)
        values=np.empty((8760,model['A'].shape[1]))
        duals=np.empty((8760,model['A'].shape[0]))
        objectives=np.empty(8760)
        residual=0.
        try:
            for hour in range(8760):
                values[hour],duals[hour],objectives[hour],error=clear_hour(highs,updated,cost,hour)
                residual=max(residual,error)
            emergency=float(values[:,:model['ng']][:,model['emergency_mask']].sum())
            if emergency<=1e-6 and residual<1e-4:
                solved=(scale,values,duals,objectives,residual,emergency)
                break
        except RuntimeError as exc:
            if 'Infeasible' not in str(exc):
                raise
    if solved is None:
        raise RuntimeError('Combined model infeasible without emergency supply')
    scale,values,duals,objectives,residual,emergency=solved
    output=water['power']+scale*change
    stock=water['initial']+np.cumsum(water['inflow']-water['spill']-output/water['eta'],axis=0)
    stock_error=max(0.,float(np.max(np.maximum(-stock,stock-water['capacity']))))
    terminal_error=float(np.max(abs(stock[-1]-water['terminal'])))
    turbine_error=max(0.,float(np.max(output-turbines)))
    if max(stock_error,terminal_error,turbine_error)>1e-4:
        raise ValueError('Combined annual water/turbine replay failed')
    prices=duals[:,:model['nz']]
    zones={zone:dict(baseline=float(abs(baseline['row_duals'][mask[:,j],j]-observed[mask[:,j],j]).mean()),
                     generation_a11=float(abs(reference_prices[mask[:,j],j]-observed[mask[:,j],j]).mean()),
                     combined=float(abs(prices[mask[:,j],j]-observed[mask[:,j],j]).mean()))
           for j,zone in enumerate(model['zones']) if mask[:,j].any()}
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'annual.npz'
    np.savez_compressed(path,values=values,row_duals=duals,objectives=objectives,
                        hydro_power=output,hydro_inventory=stock,
                        hours=np.arange(8760),optimal=np.ones(8760,bool))
    result=dict(status='combined_frozen_bid_2025_candidate_not_baseline',hours=8760,
                generation_columns=len(review),added_supply_available_twh=float(sum(r['incremental_available_twh'] for r in review)),
                added_supply_dispatch_twh=float(values[:,799:model['ng']].sum()/1e6),
                a11_connection_gaps_revised=19,
                hydro_units=len(units),hydro_eligible_units=len(eligible),hydro_skipped_units=skipped,
                hydro_network_scale=scale,hydro_absolute_timing_shift_twh=float(abs(scale*change).sum()/1e6),
                annual_reservoir_generation_twh=float(output.sum()/1e6),
                water_stock_violation_mwh=stock_error,water_terminal_error_mwh=terminal_error,
                turbine_violation_mw=turbine_error,
                primal_residual_mw=residual,emergency_mwh=emergency,
                baseline_price_mae=float(abs(baseline['row_duals'][:,:model['nz']][mask]-observed[mask]).mean()),
                generation_a11_price_mae=float(abs(reference_prices[mask]-observed[mask]).mean()),
                combined_price_mae=float(abs(prices[mask]-observed[mask]).mean()),
                zones=zones,solve_seconds=time.perf_counter()-started,
                source_sha256={'generation_a11':sha(REFERENCE),'europe_hydro_source':sha(WATER/'water.npz'),
                               'a75_reservoir_hourly':sha(POWER_HOURLY),'combined_witness':sha(path)},
                turbine_evidence={'dated_provisional_pure_zone_assignments':turbine_details,
                                  'model_treatment':'Observed zonal peak shortfall assigned to a pure-zone source unit after first dated A75 exceedance; storage energy unchanged'},
                limitations=['Frozen old fitted bids for changed generation and network; incremental technology bids are provisional proxies',
                             'Retrospective A75 peaks and A11 physical flow do not establish prospective availability or market domain',
                             'Hydro is bounded exogenous timing, not endogenous bidding; pure-zone Swedish turbine assignment is a provisional allocation, not a verified plant inventory',
                             'Original run-of-river water split and renewable weather availability remain unchanged',
                             'No independent generation-mix, A09 exchange, scenario-response or out-of-sample acceptance claim'])
    SUMMARY.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    result=run()
    print(json.dumps({k:v for k,v in result.items() if k not in ('zones','hydro_skipped_units')},indent=2))
