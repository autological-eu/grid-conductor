"""Derivative replay against frozen bid signatures, original witnesses and sources.

Does not import the review producer or reconstruct/optimise a network.
"""
import argparse, csv, gzip, hashlib, json
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT, digest


def close(a,b):
    np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-8,equal_nan=True)


def check_quantiles(q,v,w):
    good=w>1e-8; v=v[good]; w=w[good]; total=w.sum()
    assert len(q)==5 and np.isfinite(q).all() and np.all(np.diff(q)>=0)
    for value,p in zip(q,[0,.1,.5,.9,1]):
        assert w[v<value].sum()<=p*total+total*1e-10
        assert w[v<=value].sum()+total*1e-10>=p*total
    close(q[0],v.min()); close(q[-1],v.max())


def audit(folder):
    s=json.loads((folder/'summary.json').read_text())
    assert s['producer_sha256']==digest(ROOT/'tools/review_supply_bids_2025.py')
    for p,h in s['source_hashes'].items(): assert digest(ROOT/p)==h
    for p,h in s['files'].items(): assert digest(folder/p)==h
    latest=ROOT/'data/bidding-zone-network-2025/weekly-bids-v1'; ls=json.loads((latest/'summary.json').read_text()); key='inverse_joint-nordic_higher-w100'
    cert=json.loads((latest/'verification-v1/audit.json').read_text()); assert cert['summary_sha256']==digest(latest/'summary.json')
    record=next(r for r in ls['results'] if r['anchor']==key)
    with np.load(folder/'offers.npz') as z: arrays={k:z[k] for k in z.files}
    c,av,x,prices,raw=[arrays[k] for k in ['cost','availability','dispatch','prices','raw_cost']]
    assert hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest()==record['bid_sha256']
    assert hashlib.sha256(np.ascontiguousarray(av).tobytes()).hexdigest()==record['physical_inputs']['availability']
    path=latest/ls['annuals'][key]['witness']; assert digest(path)==ls['annuals'][key]['witness_sha256']
    with np.load(path) as z:
        np.testing.assert_array_equal(x,z['values'][:,:c.shape[1]]); np.testing.assert_array_equal(prices,z['row_duals'][:,:prices.shape[1]])
        close((x*c).sum(axis=1),z['objectives'])
        np.testing.assert_array_equal(arrays['net_injection'],z['values'][:,-prices.shape[1]:])
    assert len(c)==8760 and prices.shape==(8760,48)
    meta=json.loads((folder/'offers.json').read_text()); categories=np.array([r['category'] for r in meta]); zone_ids=np.array([s['zones'].index(r['zone']) for r in meta])
    supply=np.zeros_like(prices)
    for j,zi in enumerate(zone_ids): supply[:,zi]+=x[:,j]
    balance=float(abs(supply-arrays['net_load']-arrays['net_injection']).max()); assert balance<=1e-4
    for row in s['technologies']:
        ids=np.flatnonzero(categories==row['technology']); v=av[:,ids]; a=raw[:,ids]; b=c[:,ids]; q=x[:,ids]
        check_quantiles(row['raw_bid_quantiles'],a,v); check_quantiles(row['final_bid_quantiles'],b,v)
        close(v.sum()/1e6,row['available_twh']); close(q.sum()/1e6,row['generation_twh'])
        close(q.sum()/v.sum(),row['utilisation']); close(((b-a)*v).sum()/v.sum(),row['available_weighted_mean_bid_shift'])
        close(v[abs(b)<=1e-8].sum()/v.sum(),row['zero_bid_available_fraction'])
    # The original source oil formula, including inherited heat-content basis,
    # is replayed without importing the compiler.
    oil=ROOT/'data/bidding-zone-network-2025/oil-supply-v2'; os=json.loads((oil/'summary.json').read_text()); oa=json.loads((oil/'verification-v1/audit.json').read_text())
    assert oa['summary_sha256']==digest(oil/'summary.json'); columns=json.loads((oil/'oil-columns.json').read_text()); assert digest(oil/'oil-columns.json')==os['oil_columns_sha256']
    monthly=json.loads((ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json').read_text())
    fuel=np.array([r['oil_eur_mwh_th'] for r in monthly['hours']]); carbon=np.array([r['co2_eur_t'] for r in monthly['hours']]); assumption=columns['assumption']
    for col in columns['existing']:
        j=col['column']; expected=(fuel+carbon*assumption['emissions_t_mwh_th'])/col['efficiency']+assumption['variable_om_eur_mwh_el']
        close(c[:,j],expected); close(raw[:,j],expected)
        assert (x[:,j]<=1e-4).all() and (c[:,j]-prices[:,zone_ids[j]]>=-1e-5).all()
    trial=oil/os['annuals']['capacity_and_daily_oil']['witness']; assert digest(trial)==os['annuals']['capacity_and_daily_oil']['witness_sha256']
    with np.load(trial) as z: trial_prices=z['row_duals'][:,:48]
    inputs=ROOT/'data/fuel-prices/daily-inputs-v1'; input_meta=json.loads((inputs/'summary.json').read_text()); assert digest(inputs/'inputs.npz')==input_meta['inputs_sha256']
    with np.load(inputs/'inputs.npz') as z: daily=z['oil']
    details=json.loads((folder/'oil-hourly-comparison.json').read_text()); manifest=json.loads((ROOT/'public/research/country-explorer-2025/manifest.json').read_text())
    target_root=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1'
    with np.load(target_root/'development-targets.npz') as z: obs_first=z['prices']
    with np.load(target_root/'evaluation-targets.npz') as z: observed_prices=np.r_[obs_first,z['prices']]
    np.testing.assert_array_equal(observed_prices,arrays['observed_prices'])
    oil_index=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='oil')
    for row in s['oil_countries']:
        country,zone=row['country'],row['zone']; entry=next(r for r in manifest['countries'] if r['code']==country)
        path=ROOT/'public/research/country-explorer-2025'/entry['file']; assert digest(path)==entry['sha256']
        d=json.loads(gzip.decompress(path.read_bytes())); area=next(r for r in d['generation'] if r['id']=='country:'+country)
        o=np.array([np.nan if v is None else v/manifest['generation_scale'] for v in d['series'][area['observed'][oil_index]]]); close(o,np.array(details[country]['observed'],float))
        curves=[]; volume=np.zeros(8760)
        for item in columns['existing']:
            if country in item['countries']:
                curves.append((daily+carbon*assumption['emissions_t_mwh_th'])/item['efficiency']+assumption['variable_om_eur_mwh_el'])
                volume+=av[:,item['column']]
        for item in columns['additions']:
            if item['country']==country:
                curves.append((daily+carbon*assumption['emissions_t_mwh_th'])/item['efficiency']+assumption['variable_om_eur_mwh_el']); volume+=item['mw']
        bid=np.min(curves,axis=0); p=trial_prices[:,s['zones'].index(zone)]; observed=observed_prices[:,s['zones'].index(zone)]
        for name,value in [('cheapest_bid',bid),('available_mw',volume),('model_price',p),('observed_price',observed)]: close(details[country][name],value)
        valid=np.isfinite(o)&np.isfinite(observed); good=valid&(o>.1); weight=o[good].sum()
        close(o[valid].sum()/1e6,row['observed_oil_twh']); close(volume[valid].sum()/1e6,row['available_oil_twh'])
        assert int(valid.sum())==row['known_hours'] and int(good.sum())==row['positive_generation_hours']
        close(o[good&(observed<bid-1e-5)].sum()/weight,row['observed_energy_below_cheapest_oil_bid_fraction'])
        close(np.average((bid-observed)[good],weights=o[good]),row['mean_bid_minus_observed_price_on_oil_generation'])
        assert int((good&(observed<0)).sum())==row['oil_positive_hours_negative_observed_price']
        assert int((o[valid]>volume[valid]+1).sum())==row['reported_above_available_hours']
        # Price plateaus can move by one ULP when the independently equivalent
        # fuel expression is reassociated. Validate the formula above, then
        # check the exact exported sample's CDF without rounding ties away.
        saved_bid=np.array(details[country]['cheapest_bid']); saved_price=np.array(details[country]['model_price'])
        check_quantiles(row['cheapest_oil_bid_quantiles'],saved_bid,volume)
        check_quantiles(row['oil_bid_minus_model_price_quantiles'],saved_bid-saved_price,volume)
    gas=[]
    for fraction in [.5,.35,.15]:
        ids=[r['column'] for r in meta if r['category']=='Gas' and r['fraction']==fraction]
        v,q,b=av[:,ids],x[:,ids],c[:,ids]
        gas.append(dict(capacity_fraction=fraction,available_twh=float(v.sum()/1e6),generation_twh=float(q.sum()/1e6),
            utilisation=float(q.sum()/v.sum()),available_weighted_mean_bid=float((v*b).sum()/v.sum())))
    # Reparse source catalogue labels independently; never assign national
    # observed generation to those units on this basis alone.
    roles={}
    source=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/powerplants_s_128.csv'
    for row in csv.DictReader(source.open()):
        if row['Fueltype']!='Oil' or (row['DateIn'] and float(row['DateIn'])>2025) or (row['DateOut'] and float(row['DateOut'])<=2025): continue
        label=(row['Country'],row['Set'] or 'Unspecified'); roles[label]=roles.get(label,0)+float(row['Capacity'])
    assert set(roles)=={(r['country'],r['role']) for r in s['raw_plant_roles']}
    for row in s['raw_plant_roles']: close(roles[row['country'],row['role']],row['mw'])
    result=dict(status='passed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),hours=8760,offers=len(meta),balance_residual_mw=balance,
                verified='Original annual cost/availability signatures; exact saved dispatch/prices; weighted CDF bounds, Oil formula/reduced costs, source observations and five-country oil comparisons',gas_blocks=gas,new_solves=0)
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);audit(p.parse_args().folder.resolve())
