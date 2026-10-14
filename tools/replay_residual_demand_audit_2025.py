"""Independently reconstruct zonal source-input sums and saved residual identities."""
import argparse,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
import pandas as pd
from bidding_zone_network_2025 import ROOT,build
from nve_hydro_diagnostics import digest
from residual_demand_audit_2025 import FAMILIES,TYPES
from input_sensitivity_2025 import wind_source_check

def replay(folder):
    start=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert digest(folder/'hourly.npz')==s['witness_sha256']
    assert digest(folder/'design.json')==s['design_sha256']
    assert digest(folder/'generation-replay.json')==s['generation_replay_sha256']
    base=ROOT/'data/bidding-zone-network-2025/annual-v7'
    assert digest(base/'summary.json')==s['baseline_summary_sha256']
    assert digest(base/'annual.npz')==s['baseline_witness_sha256']
    manifest=json.loads((folder/'generation-replay.json').read_text())
    for area in manifest['zones']:
        for month in area['monthly']:
            if month['status']!='raw_interval_energy_replayed':continue
            zone=area['zone'];label={'DK1':'DK-DK1','DK2':'DK-DK2'}.get(zone,zone);m=month['month']
            begin=f'2025{m:02d}01';end='20260101' if m==12 else f'2025{m+1:02d}01'
            raw=ROOT/f'data/carbon-pilot/entsoe/raw/{label}-{begin}-{end}.xml'
            assert digest(raw)==month['raw_sha256']
            assert digest(ROOT/f'data/carbon-pilot/map-2025/{zone}/{m:02d}.json')==month['processed_sha256']
    n,cost,fixed,mapping,original,old,hp=build();assert mapping==s['mapping']
    with np.load(folder/'hourly.npz') as a:
        zones=a['zones'].tolist();labels=n.buses.bidding_zone.replace({'ES-IB-MA':'ES'})
        gzone=n.generators.bus.map(labels);lzone=n.loads.bus.map(labels)
        av=n.get_switchable_as_dense('Generator','p_max_pu')*n.generators.p_nom
        load=n.get_switchable_as_dense('Load','p_set');worst=0.
        for j,z in enumerate(zones):
            expected={'demand':load.loc[:,lzone.eq(z)].sum(axis=1).values,
                'fixed_hydro':fixed.loc[:,labels.eq(z)].sum(axis=1).values}
            for k,types in FAMILIES.items():expected[k]=av.loc[:,gzone.eq(z)&n.generators.carrier.isin(types)].sum(axis=1).values
            for k,v in expected.items():
                error=float(abs(v-a[k][:,j]).max());worst=max(worst,error);assert error<1e-7
            np.testing.assert_allclose(a['residual_vre'][:,j],expected['demand']-expected['wind']-expected['solar'],atol=1e-7,rtol=1e-12)
            np.testing.assert_allclose(a['residual_low_cost'][:,j],a['residual_vre'][:,j]-sum(expected[k] for k in ['nuclear','ror','biomass','fixed_hydro']),atol=1e-7,rtol=1e-12)
            # Independent replay of reported family quantities from hashed monthly rows.
            area=next((r for r in manifest['zones'] if r['zone']==z),None)
            if not area:
                for k in TYPES:assert np.isnan(a['reported_'+k][:,j]).all()
                continue
            source={k:np.full(8760,np.nan) for k in TYPES};offset=0
            for m in range(1,13):
                start_month=np.datetime64(f'2025-{m:02d}-01')
                end_month=np.datetime64('2026-01-01') if m==12 else np.datetime64(f'2025-{m+1:02d}-01')
                count=int((end_month-start_month)/np.timedelta64(1,'h'))
                meta=area['monthly'][m-1]
                if meta['status']=='raw_interval_energy_replayed':
                    rows=json.loads((ROOT/f'data/carbon-pilot/map-2025/{z}/{m:02d}.json').read_text());assert len(rows)==count
                    for t,row in enumerate(rows):
                        for k,types in TYPES.items():
                            included=[x for x in row['reported_types'] if x in types]
                            if included and not any(x in row['missing_types'] for x in included):
                                source[k][offset+t]=sum(row['generation_mwh_by_type'][x] for x in included)
                offset+=count
            assert offset==8760
            for k,v in source.items():np.testing.assert_array_equal(v,a['reported_'+k][:,j])
    p=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';assert digest(p)==s['ember_receipt']['sha256']
    reference=pd.read_csv(p,usecols=['Date','ISO 3 code','Area type','Electricity source','Generation (TWh)'])
    reference=reference[reference.Date.str.startswith('2025')&reference['Area type'].str.lower().str.startswith('country')&reference['Electricity source'].eq('Demand')]
    lc=n.loads.bus.map(n.buses.country);loads=n.get_switchable_as_dense('Load','p_set')
    for row in s['national_demand']:
        modeled=loads.loc[:,lc.eq(row['country'])].sum(axis=1)
        for month in row['monthly']:
            assert abs(modeled[n.snapshots.month==month['month']].sum()/1e6-month['model_twh'])<1e-8
            ref=reference[reference['ISO 3 code'].eq(row['iso3'])&reference.Date.str.startswith(f"2025-{month['month']:02d}")]
            assert len(ref)<=1
            if len(ref):assert float(ref['Generation (TWh)'].iloc[0])==month['ember_twh']
            else:assert month['ember_twh'] is None
    # Source-replayed Norwegian metering remains a different demand scope.
    provenance=wind_source_check(n,n.get_switchable_as_dense('Generator','p_max_pu').values)
    frame=pd.read_csv(ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1/hourly.csv')
    nor=[]
    for zone in ['NO1','NO2','NO3','NO4','NO5']:
        source=frame[frame.zone.eq(zone)].sort_values('utc');values=source.metered_consumption_mwh.to_numpy(float)
        modeled=loads.loc[:,lzone.eq(zone)].sum(axis=1).values;known=np.isfinite(values)
        nor.append(dict(zone=zone,known_hours=int(known.sum()),model_on_known_hours_twh=float(modeled[known].sum()/1e6),
            elhub_metered_twh=float(values[known].sum()/1e6),hourly_mae_mw=float(abs(modeled[known]-values[known]).mean()),
            shape_correlation=float(np.corrcoef(modeled[known],values[known])[0,1])))
    result=dict(status='saved_zonal_input_and_reported_quantity_replay_passed_not_market_acceptance',
        areas=len(zones),hours=8760,maximum_input_sum_difference_mw=worst,
        verified_generation_area_months=manifest['verified_area_months'],summary_sha256=digest(folder/'summary.json'),
        auditor_sha256=digest(__file__),norway_metered_demand=nor,elhub_provenance=provenance,
        metering_limit='Metered consumption is not certified total load; losses, self-consumption and reporting coverage remain unresolved.',
        elapsed_seconds=time.perf_counter()-start)
    (folder/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);replay(a.folder)
