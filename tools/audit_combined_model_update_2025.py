"""Independent annual LP, water, and source-covered generation audit."""
from __future__ import annotations

import json
import hashlib

import numpy as np

from baselines.compact.evaluation import CARRIER, LAYOUT, offer_groups, physical_lp, saved_annual
from baselines.compact.nordic_storage import sha, sources
from baselines.compact.source import ROOT, grouped_fit_inputs
from tools.price_mechanism_2025 import dual_replay
from tools.run_combined_model_update_2025 import OUT, SUMMARY, prepare

AUDIT=ROOT/'research/data/combined-model-update-v2-audit-2025.json'


def modeled_generation(schema,data,base,native,original,values,hydro_change,units,new_offers):
    groups,mixed=offer_groups(schema,base)
    keys={(g['zone'],g['technology']):i for i,g in enumerate(schema['groups'])}
    quantity=np.zeros((8760,len(schema['groups'])))
    for g,ids in groups.items():
        if ids:
            quantity[:,g]=values[:,ids].sum(axis=1)
    layout=json.loads(LAYOUT.read_text())
    carriers=native.generators.carrier.to_numpy(dtype=str)
    available=(native.get_switchable_as_dense('Generator','p_max_pu').to_numpy()
               *native.generators.p_nom.to_numpy())
    for column in mixed:
        members=layout['members'][column]
        zone=str(base['offer_zones'][column])
        kinds={CARRIER[carriers[member]] for member in members}
        denominator=available[:,members].sum(axis=1)
        fallback=sum((data['capacity'][:,keys[zone,kind]] for kind in kinds
                      if (zone,kind) in keys),start=np.zeros(8760))
        use=np.where(denominator>1e-8,denominator,fallback)
        if np.any((use<=1e-8)&(values[:,column]>1e-5)):
            raise ValueError('Mixed offer lacks member availability')
        for kind in kinds:
            if (zone,kind) not in keys:
                continue
            ids=[i for i in members if CARRIER[carriers[i]]==kind]
            numerator=np.where(denominator>1e-8,available[:,ids].sum(axis=1),
                               data['capacity'][:,keys[zone,kind]])
            quantity[:,keys[zone,kind]]+=np.divide(values[:,column]*numerator,use,
                                                    out=np.zeros(8760),where=use>0)
    country_ids={name:i for i,name in enumerate(schema['countries'])}
    tech_ids={name:i for i,name in enumerate(schema['technologies'])}
    country_by_zone={g['zone']:g['country'] for g in schema['groups']}
    result=data['fixed_generation'].copy()
    for g,row in enumerate(schema['groups']):
        result[:,row['country_id'],tech_ids[row['technology']]]+=quantity[:,g]
    for j,row in enumerate(new_offers):
        country=country_by_zone[row['zone']]
        result[:,country_ids[country],tech_ids[row['technology']]]+=values[:,799+j]
    for j,name in enumerate(units.index):
        country=original.buses.loc[units.loc[name,'bus'],'country']
        result[:,country_ids[country],tech_ids['reservoir']]+=hydro_change[:,j]
    return result


def score(modeled,observed):
    mask=np.isfinite(observed)
    if not mask.any():
        raise ValueError('No generation targets')
    volume=float(np.mean(abs(modeled[mask]-observed[mask]))/1000)
    known_model=np.where(mask,modeled,0.)
    known_observed=np.where(mask,observed,0.)
    model_total=known_model.sum(axis=2,keepdims=True)
    observed_total=known_observed.sum(axis=2,keepdims=True)
    shares=mask&(model_total>1e-6)&(observed_total>1e-6)
    model_share=np.divide(known_model,model_total,out=np.zeros_like(known_model),where=model_total>1e-6)
    observed_share=np.divide(known_observed,observed_total,out=np.zeros_like(known_observed),where=observed_total>1e-6)
    return dict(covered_cells=int(mask.sum()),hourly_generation_mae_gw=volume,
                mix_share_mae=float(np.mean(abs(model_share[shares]-observed_share[shares]))))


def zonal_hydro_a75(native,units,allocation,water,power):
    """Direct hourly B12 category comparison; no availability substitution."""
    results={}
    source_digest=hashlib.sha256()
    for zone in ('SE2','SE3','SE4','NO1','NO2','NO3','NO4'):
        weight=np.array([sum(share for bus,share in allocation[name].items()
                             if native.buses.loc[bus,'bidding_zone']==zone)
                         for name in units.index])
        before=water['power']@weight
        after=power@weight
        observed=[]
        for month in range(1,13):
            path=ROOT/f'data/carbon-pilot/map-2025/{zone}/{month:02d}.json'
            source_digest.update(str(path.relative_to(ROOT)).encode())
            source_digest.update(path.read_bytes())
            for row in json.loads(path.read_text()):
                if row['zone']!=zone or row['basis']!='reported_primary_production':
                    raise ValueError('Unexpected A75 hydro scope')
                observed.append(row.get('generation_mwh_by_type',{}).get('B12',float('nan')))
        actual=np.asarray(observed,dtype=float)
        if actual.shape!=(8760,) or not np.isfinite(actual).all():
            raise ValueError(f'Incomplete A75 reservoir target in {zone}')
        results[zone]=dict(hours=8760,observed_twh=float(actual.sum()/1e6),
                           baseline_twh=float(before.sum()/1e6),candidate_twh=float(after.sum()/1e6),
                           baseline_hourly_mae_gw=float(np.mean(abs(before-actual))/1000),
                           candidate_hourly_mae_gw=float(np.mean(abs(after-actual))/1000))
    return results,source_digest.hexdigest()


def audit():
    receipt=json.loads(SUMMARY.read_text())
    path=OUT/'annual.npz'
    if sha(path)!=receipt['source_sha256']['combined_witness']:
        raise ValueError('Combined witness changed')
    model,cost,review,water,units,change,shares,branch,_,_,_,turbines,_=prepare()
    scale=receipt['hydro_network_scale']
    model=model|dict(load=model['load']-scale*(change@shares),
                     flow=model['flow']+scale*(change@branch))
    with np.load(path) as archive:
        x=archive['values'];y=archive['row_duals'];objective=archive['objectives']
        power=archive['hydro_power'];stock=archive['hydro_inventory']
        if not archive['optimal'].all() or not np.array_equal(archive['hours'],np.arange(8760)):
            raise ValueError('Incomplete annual chronology')
    if x.shape!=(8760,model['A'].shape[1]) or y.shape!=(8760,model['A'].shape[0]):
        raise ValueError('Combined LP witness shape changed')
    np.testing.assert_allclose(power,water['power']+scale*change,atol=1e-6,rtol=0)
    replay=water['initial']+np.cumsum(water['inflow']-water['spill']-power/water['eta'],axis=0)
    water_error=float(abs(replay-stock).max())
    if water_error>1e-4 or np.max(np.maximum(-stock,stock-water['capacity']))>1e-4 or np.max(power-turbines)>1e-4:
        raise ValueError('Independent water stock replay failed')
    if abs(stock[-1]-water['terminal']).max()>1e-4:
        raise ValueError('Annual reservoir terminal stock changed')
    ng,nl,nz=(model[key] for key in ('ng','nl','nz'))
    maximum=dict(primal_residual_mw=0.,objective_residual_eur=0.)
    for start in range(0,8760,168):
        stop=min(start+168,8760);sl=slice(start,stop)
        rating=model['ratings'][sl] if model['ratings'].ndim==2 else model['ratings']
        case={key:model[key] for key in ('A','ng','nl','nz','islands')}
        case.update(cost=cost[sl],availability=model['availability'][sl],
                    link_min=model['link_min'][sl],link_max=model['link_max'][sl],
                    load=model['load'][sl],island_rhs=model['island_rhs'][sl],ratings=rating)
        full_cost=np.c_[cost[sl],np.zeros((stop-start,nl+nz))]
        reduced=full_cost-(model['A'].T@y[sl].T).T
        checks=dual_replay(case,x[sl],y[sl],reduced,objective[sl],model['flow'][sl])
        for key,value in checks.items():
            maximum[key]=max(maximum.get(key,0.),value)
        actual=(model['A']@x[sl].T).T
        low=np.c_[model['load'][sl],model['island_rhs'][sl],-rating-model['flow'][sl]]
        high=np.c_[model['load'][sl],model['island_rhs'][sl],rating-model['flow'][sl]]
        maximum['primal_residual_mw']=max(maximum['primal_residual_mw'],
            float(np.maximum(low-actual,0).max()),float(np.maximum(actual-high,0).max()))
        maximum['objective_residual_eur']=max(maximum['objective_residual_eur'],
            float(abs((x[sl,:ng]*cost[sl]).sum(axis=1)-objective[sl]).max()))
    if maximum['primal_residual_mw']>=1e-4 or maximum['objective_residual_eur']>=.05 or maximum.get('duality_gap_maximum_eur',0)>=.05:
        raise ValueError('Combined primal/dual gate failed')
    if x[:,:ng][:,model['emergency_mask']].sum()>1e-6:
        raise ValueError('Combined annual witness uses emergency generation')
    native,original,_,_,allocation=sources()
    schema,data,_=grouped_fit_inputs()
    _,baseline=saved_annual()
    old=physical_lp()
    before=modeled_generation(schema,data,old,native,original,baseline['values'],np.zeros_like(change),units,[])
    after=modeled_generation(schema,data,old,native,original,x,power-water['power'],units,review)
    scores=dict(baseline=score(before,data['observed_generation']),
                combined=score(after,data['observed_generation']))
    zonal_hydro,hydro_source_hash=zonal_hydro_a75(native,units,allocation,water,power)
    result=dict(status='combined_annual_primal_dual_water_generation_replay_passed',
                hours=8760,witness_sha256=sha(path),numerical=maximum,
                water_replay_maximum_mwh=water_error,generation=scores,
                zonal_hydro_a75=zonal_hydro,hydro_a75_source_collection_sha256=hydro_source_hash,
                limitations=['Mixed renewable offer dispatch is allocated illustratively by member availability',
                             'Source-covered country/technology generation score is in-sample and excludes unreported cells',
                             'A09 commercial exchange and scenario-response audits remain outstanding'])
    AUDIT.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
