"""Review the actual saved annual offer book; no optimisation or fitted changes."""
import argparse, csv, gzip, json, logging, resource, signal, time
from pathlib import Path
import numpy as np
import pandas as pd
from oil_supply_2025 import anchor, inputs, compile_case, ROOT, LATEST, CASE
from generation_mix_2025 import digest

OIL=ROOT/'data/bidding-zone-network-2025/oil-supply-v2'
GROUP={'CCGT':'Gas','OCGT':'Gas','coal':'Coal/lignite','lignite':'Coal/lignite',
       'nuclear':'Nuclear','oil':'Oil','biomass':'Biomass','waste':'Waste','ror':'Run-of-river',
       'geothermal':'Geothermal','emergency':'Emergency'}
for _c in ['onwind','offwind-ac','offwind-dc','offwind-float','solar','solar-hsat']:
    GROUP[_c]='Wind/solar'


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def quantile(values,weights):
    v=np.asarray(values).ravel(); w=np.asarray(weights).ravel(); good=w>1e-8; v=v[good]; w=w[good]
    if not len(v): return None
    order=np.argsort(v,kind='stable'); v=v[order]; w=w[order]; cumulative=np.cumsum(w)
    return [float(v[min(np.searchsorted(cumulative,p*cumulative[-1]),len(v)-1)]) for p in [0,.1,.5,.9,1]]


def run(out):
    began=time.perf_counter(); out.mkdir(parents=True,exist_ok=False)
    n,base,off,m,ctx,layout,c,flow,target=anchor()
    old=json.loads((LATEST/'summary.json').read_text()); path=LATEST/old['annuals'][CASE]['witness']
    assert digest(path)==old['annuals'][CASE]['witness_sha256']
    with np.load(path) as z:
        x=z['values']; y=z['row_duals']; objectives=z['objectives']; assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
    assert abs((x[:,:m['ng']]*c).sum(axis=1)-objectives).max()<.05
    # A supply column enters only its market balance; its reduced cost is bid - zonal price.
    matrix=m['A'][:,:m['ng']].toarray(); expected=np.zeros_like(matrix)
    zi=np.array([m['zones'].index(z) for z in m['offer_zones']]); expected[zi,np.arange(m['ng'])]=1
    np.testing.assert_array_equal(matrix,expected)
    categories=[];meta=[]
    for j,ids in enumerate(layout['members']):
        types=sorted({GROUP[n.generators.iloc[i].carrier] for i in ids})
        category=types[0] if len(types)==1 else 'Mixed: '+','.join(types); categories.append(category)
        meta.append(dict(column=j,zone=str(m['offer_zones'][j]),category=category,
            source_carriers=sorted(set(n.generators.iloc[ids].carrier)),fraction=layout['fractions'][j],
            source_nameplate_mw=float(n.generators.iloc[ids].p_nom.sum()*layout['fractions'][j])))
    p=y[:,:m['nz']]; by_offer=p[:,zi]; reduced=c-by_offer
    loads=n.get_switchable_as_dense('Load','p_set')
    demand_zonal=loads.T.groupby(n.loads.bus.map(m['buszone'])).sum().T.reindex(columns=m['zones'],fill_value=0).values
    fixed_zonal=demand_zonal-m['load']
    np.savez_compressed(out/'offers.npz',availability=m['availability'],raw_cost=m['cost'],cost=c,dispatch=x[:,:m['ng']],
        prices=p,observed_prices=target['prices'],net_load=m['load'],net_injection=x[:,m['ng']+m['nl']:],fixed_hydro=fixed_zonal)
    rows=[]
    for category in sorted(set(categories)-{'Emergency'}):
        ids=np.flatnonzero(np.array(categories)==category); av=m['availability'][:,ids]; q=x[:,ids]; cost=c[:,ids]
        if av.sum()<=0: continue
        raw=m['cost'][:,ids]; price=by_offer[:,ids]; offered=av>1e-3
        rows.append(dict(technology=category,offers=len(ids),available_twh=float(av.sum()/1e6),generation_twh=float(q.sum()/1e6),
            utilisation=float(q.sum()/av.sum()),raw_bid_quantiles=quantile(raw,av),final_bid_quantiles=quantile(cost,av),
            available_weighted_mean_bid_shift=float(((cost-raw)*av).sum()/av.sum()),
            zero_bid_available_fraction=float(av[abs(cost)<=1e-8].sum()/av.sum()),
            interior_offer_hours=int(((q>.001)&(av-q>.001)&offered).sum()),
            lower_bound_offer_hours=int(((q<=.001)&offered).sum()),
            maximum_unused_bid_below_price=float(np.maximum(price-cost,0)[(q<=.001)&offered].max(initial=0))))
    monthly,daily,co2,assumption,additions,oil=inputs(n,m,layout)
    trial,_=compile_case(m,ctx,c,monthly,daily,co2,assumption,additions,oil,'capacity_and_daily_oil')
    ts=json.loads((OIL/'summary.json').read_text()); audit=json.loads((OIL/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(OIL/'summary.json')
    trial_path=OIL/ts['annuals']['capacity_and_daily_oil']['witness']; assert digest(trial_path)==ts['annuals']['capacity_and_daily_oil']['witness_sha256']
    with np.load(trial_path) as z: tx=z['values']; tp=z['row_duals'][:,:m['nz']]
    explorer=ROOT/'public/research/country-explorer-2025'; manifest=json.loads((explorer/'manifest.json').read_text())
    oil_index=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='oil')
    country_rows=[]; source_hashes={str(p.relative_to(ROOT)):digest(p) for p in [LATEST/'summary.json',LATEST/'verification-v1/audit.json',path,OIL/'summary.json',OIL/'verification-v1/audit.json',trial_path,explorer/'manifest.json']}
    details={}
    for country,zone in [('DE','DE-LU'),('BE','BE'),('PL','PL'),('SK','SK'),('SI','SI')]:
        entry=next(e for e in manifest['countries'] if e['code']==country); file=explorer/entry['file'];assert digest(file)==entry['sha256'];source_hashes[str(file.relative_to(ROOT))]=digest(file)
        data=json.loads(gzip.decompress(file.read_bytes())); area=next(a for a in data['generation'] if a['id']=='country:'+country)
        observed=np.array([np.nan if v is None else v/manifest['generation_scale'] for v in data['series'][area['observed'][oil_index]]])
        ids=[r['column'] for r in oil if country in r['countries']]
        ids += [m['ng']+j for j,a in enumerate(additions) if a['country']==country]
        assert all(trial['offer_zones'][j]==zone for j in ids)
        bid=np.min(trial['cost'][:,ids],axis=1); volume=trial['availability'][:,ids].sum(axis=1)
        price=tp[:,m['zones'].index(zone)]; actual=target['prices'][:,m['zones'].index(zone)]
        valid=np.isfinite(observed)&np.isfinite(actual); positive=valid&(observed>.1)
        # Oil is homogeneous in every selected column; there is no technology allocation ambiguity here.
        assert tx[:,ids].max(initial=0)<=1e-4
        gap=bid-price; assert gap.min()>-1e-5
        actual_gap=bid-actual; energy=observed[positive].sum()
        country_rows.append(dict(country=country,zone=zone,known_hours=int(valid.sum()),positive_generation_hours=int(positive.sum()),
            observed_oil_twh=float(observed[valid].sum()/1e6),available_oil_twh=float(volume[valid].sum()/1e6),
            reported_peak_mw=float(observed[valid].max()),available_mw=float(volume.min()),
            reported_above_available_hours=int((observed[valid]>volume[valid]+1).sum()),
            cheapest_oil_bid_quantiles=quantile(bid,volume),oil_bid_minus_model_price_quantiles=quantile(gap,volume),
            observed_energy_below_cheapest_oil_bid_fraction=float(observed[positive&(actual_gap>1e-5)].sum()/energy) if energy>0 else None,
            mean_bid_minus_observed_price_on_oil_generation=float(np.average(actual_gap[positive],weights=observed[positive])) if energy>0 else None,
            oil_positive_hours_negative_observed_price=int((positive&(actual<0)).sum())))
        details[country]=dict(observed=observed.tolist(),cheapest_bid=bid.tolist(),model_price=price.tolist(),observed_price=actual.tolist(),available_mw=volume.tolist())
    # Raw plant labels are evidence of omitted roles, not a claim about which unit generated the national B06 volume.
    plant=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/powerplants_s_128.csv';frame=pd.read_csv(plant)
    frame=frame[(frame.Fueltype=='Oil')&(frame.DateIn.isna()|(frame.DateIn<=2025))&(frame.DateOut.isna()|(frame.DateOut>2025))]
    roles=frame.groupby(['Country','Set'],dropna=False).Capacity.sum(); plant_rows=[dict(country=c,role='Unspecified' if pd.isna(role) else role,mw=float(value)) for (c,role),value in roles.items()]
    source_hashes[str(plant.relative_to(ROOT))]=digest(plant)
    write(out/'offers.json',meta)
    # JSON arrays permit missing observations, not non-standard NaN literals.
    details={k:{field:[None if not np.isfinite(v) else v for v in values] for field,values in row.items()} for k,row in details.items()}
    write(out/'oil-hourly-comparison.json',details)
    write(out/'summary.json',dict(status='saved_bid_review_no_new_solve_or_fit',source_hashes=source_hashes,
        producer_sha256=digest(__file__),zones=m['zones'],technologies=rows,oil_countries=country_rows,raw_plant_roles=plant_rows,
        files={p.name:digest(p) for p in [out/'offers.npz',out/'offers.json',out/'oil-hourly-comparison.json']},
        quantile_probabilities=[0,.1,.5,.9,1],quantile_weight='Hourly available MW, excluding zero availability; potential supply, not generation',
        scope='Current displayed joint/weekly offers. Oil-country comparisons use the audited capacity+daily-oil trial; other bids and physical constraints are unchanged. ENTSO-E generation from audited country assets is rounded to0.1MWh/hour. National FR and multi-zone generation-price pooling excluded from oil diagnostics.',
        explanation='Local supply stacks omit imports/delivery/commitment and are not isolated market clears. Fixed reservoir supply is an injection, not a marginal bid. Calibration is in-sample and does not identify real order books.',
        seconds=time.perf_counter()-began))
    for row in rows: print(row['technology'],row['raw_bid_quantiles'],row['final_bid_quantiles'],'generation',row['generation_twh'],flush=True)
    print('Oil source/price comparison',country_rows,flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(p.parse_args().out.resolve())
