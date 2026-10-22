"""Independently replay monthly regression, changed PV, native physics and KKT."""
import csv
import gzip
import json
import logging
import resource
import time
import numpy as np
import pandas as pd
import pycountry
import pypsa
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest
from audit_nve_hydro_diagnostics_2025 import physics
from audit_solar_fleet_2025 import diagnostics
from price_mechanism_2025 import dual_replay

OUT=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
SOLAR=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'


def audit():
    began=time.perf_counter();sealed=json.loads((OUT/'inputs.json').read_text());s=json.loads((OUT/'summary.json').read_text())
    assert s['inputs_sha256']==digest(OUT/'inputs.json') and s['producer_sha256']==sealed['producer_sha256']==digest(ROOT/'tools/solar_country_fit_2025.py')
    assert sealed['design']==json.loads((ROOT/'config/solar-country-fit-2025.json').read_text())
    for f,h in sealed['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert sealed['delta_sha256']==digest(OUT/'delta.npz')
    prior=json.loads((SOLAR/'inputs.json').read_text());old=json.loads((SOLAR/'audit.json').read_text());assert old['inputs_sha256']==digest(SOLAR/'inputs.json') and old['summary_sha256']==digest(SOLAR/'summary.json')
    assert old['auditor_sha256']==digest(ROOT/'tools/audit_solar_fleet_2025.py')
    for f,h in prior['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in prior['anchor_files'].items():assert digest(ANCHOR/f)==h
    p=json.loads((ANCHOR/'inputs.json').read_text());source=dict(np.load(ANCHOR/'inputs.npz'));components=dict(np.load(SOLAR/'components.npz'))
    irena=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))['irena_rows']
    # Read the actual provider CSV, independently of the public country export
    # from which the producer obtained its original raw Ember rows.
    ember_file=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt_file=ember_file.parent/'receipt.json'
    assert digest(ember_file)==json.loads(receipt_file.read_text())['sha256']
    code_to_country={('XKX' if c=='XK' else pycountry.countries.get(alpha_2=c).alpha_3):c for c in prior['countries']}
    bank={}
    with ember_file.open() as f:
        for r in csv.DictReader(f):
            if r['ISO 3 code'] not in code_to_country or r['Area type'] not in ['Country','Country or economy'] or r['Electricity source']!='Solar' or not r['Date'].startswith('2025-'):continue
            key=(code_to_country[r['ISO 3 code']],int(r['Date'][5:7]));assert key not in bank
            bank[key]=float(r['Generation (TWh)']) if r['Generation (TWh)'] else np.nan
    months=pd.date_range('2025-01-01',periods=8760,freq='h').month.to_numpy();factors={};fit_records=[];delta=np.zeros_like(source['availability'])
    for row in sealed['factors']:
        c=row['country'];ids=np.array(prior['native_countries'])==c;pv=components['pv'][:,ids]*86/90
        x=np.array([pv[months==m].sum()/1e6 for m in range(1,13)]);y=np.array([bank.get((c,m),np.nan) for m in range(1,13)])
        np.testing.assert_allclose(x,row['weather_monthly_twh'],rtol=0,atol=1e-10)
        np.testing.assert_allclose(y,[np.nan if v is None else v for v in row['target_monthly_twh']],rtol=0,atol=1e-10)
        raw=None;alpha=1.;status='missing_or_invalid_twelve_month_inputs'
        if np.isfinite(y).all() and (y>=0).all() and y.sum()>0 and x.sum()>0:
            # Independent least-squares implementation, not the producer dot ratio.
            raw=float(np.linalg.lstsq(x[:,None],y,rcond=None)[0][0]);lo=sealed['design']['factor_guard']['minimum'];hi=sealed['design']['factor_guard']['maximum']
            status='fitted' if lo<=raw<=hi else 'outside_reduction_guard_unchanged';alpha=raw if status=='fitted' else 1.
            assert abs(np.dot(x,raw*x-y))<1e-9
        caps={t:next((r for r in irena if r['country']==c and r['technology']==t),None) for t in ['Solar energy','Solar photovoltaic']}
        if None in [caps['Solar energy'],caps['Solar photovoltaic']]:status='missing_parent_pv_capacity_scope';alpha=1.
        elif max(abs(caps['Solar energy'][year]['mw']-caps['Solar photovoltaic'][year]['mw']) for year in ['capacity_2024','capacity_2025'])>2:status='solar_thermal_scope_unchanged';alpha=1.
        if c=='NL':status='national_generation_source_conflict_unchanged';alpha=1.
        assert row['status']==status and abs(alpha-row['factor'])<1e-10
        assert (raw is None and row['raw_factor'] is None) or (raw is not None and abs(raw-row['raw_factor'])<1e-10)
        if np.isfinite(y).all():
            assert abs(np.square(x-y).sum()-row['input_monthly_sse'])<1e-9
            assert abs(np.square(alpha*x-y).sum()-row['scaled_weather_monthly_sse'])<1e-9
        factors[c]=alpha;fit_records.append(dict(country=c,factor=alpha,raw_factor=raw,status=status))
        delta+=(pv*(alpha-1))@components['mapping'][ids]
    np.testing.assert_allclose(delta,np.load(OUT/'delta.npz')['delta'],rtol=0,atol=1e-7)
    assert sorted(c for c in factors if factors[c]!=1)==sorted(sealed['fitted_countries'])
    control=source['availability']+(source['solar_aligned']*86/90)-source['solar_original']
    for r,v in zip(p['capacity'],source['thermal'],strict=True):control+=(r['factor']-1)*v
    n=pypsa.Network(ANCHOR/'native.nc');n.determine_network_topology()
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            table=n.components[component].static;branch=table.loc[name]
            if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:table.loc[name,'s_max_pu']*=1.15
    native_arrays=dict(np.load(ANCHOR/'native-base.npz'));A=load_npz(ANCHOR/'network.npz');ng,nl,nz=p['ng'],p['nl'],p['nz'];certs={};quantities={};monthly={};diurnal={}
    target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];valid=np.isfinite(target).all(axis=0);assert valid.sum()==41
    for case,record in s['cases'].items():
        path=ROOT/record['annual']['witness'];assert digest(path)==record['annual']['witness_sha256']
        with np.load(path) as z:x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        av=control+(delta if case=='country_factors' else 0);assert av.min()>-1e-7
        maximum=dict(primal=0.,objective=0.,duality_gap_maximum_eur=0.,complementarity_maximum_eur=0.)
        for start in range(0,8760,168):
            sl=slice(start,min(start+168,8760));T=len(x[sl]);m={k:source[k][sl] for k in ['cost','load','link_min','link_max','island_rhs']}
            m.update(ng=ng,nl=nl,nz=nz,A=A,availability=av[sl],islands=[None]*p['islands'],ratings=source['ratings'])
            rc=np.c_[m['cost'],np.zeros((T,nl+nz))]-(A.T@y[sl].T).T
            cert=dual_replay(m,x[sl],y[sl],rc,obj[sl],source['flow'][sl])
            ax=(A@x[sl].T).T;lo=np.c_[m['load'],m['island_rhs'],-m['ratings']-source['flow'][sl]];hi=np.c_[m['load'],m['island_rhs'],m['ratings']-source['flow'][sl]]
            primal=float(max(np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max()));objective=float(abs((x[sl,:ng]*m['cost']).sum(axis=1)-obj[sl]).max())
            maximum['primal']=max(maximum['primal'],primal);maximum['objective']=max(maximum['objective'],objective)
            for k in ['duality_gap_maximum_eur','complementarity_maximum_eur']:maximum[k]=max(maximum[k],cert[k])
        assert maximum['primal']<=1e-4 and maximum['objective']<.05
        collapsed=x[:,:p['reference_ng']].copy()
        for extra in p['extras']:collapsed[:,extra['parent']]+=x[:,extra['column']]
        native_values=np.zeros((8760,p['base_ng']));native_av=native_arrays['availability'].copy();change=av-source['availability']
        for j,parent in enumerate(p['parents']):native_values[:,parent]+=collapsed[:,j];native_av[:,parent]+=change[:,j]
        native_values=np.c_[native_values,collapsed[:,p['original_ng']:p['reference_ng']],x[:,ng:]]
        native=dict(ng=p['base_ng']+len(p['additions']),nl=nl,nz=nz,zones=p['zones'],weights=p['weights'],offer_zones=p['base_offer_zones']+[r['zone'] for r in p['additions']],
            availability=np.c_[native_av,np.tile([r['mw'] for r in p['additions']],(8760,1))],link_min=source['link_min'],link_max=source['link_max'])
        residual=physics(n,native,native_values,source['load'],pd.DataFrame(native_arrays['off'].copy(),columns=p['native_off_columns']),0)
        emergency=float(x[:,:ng][:,source['emergency_mask']].sum());assert emergency<=1e-6
        mae=float(abs(y[:,:nz][:,valid]-target[:,valid]).mean());assert abs(mae-record['europe_mae'])<1e-9
        certs[case]=dict(hours=8760,native_residual_mw=residual,emergency_mwh=emergency,europe_mae=mae,**maximum)
        quantities[case]=[];monthly[case]=[];diurnal[case]=[];q=np.clip(x[:,:ng],0,av)
        for ci,c in enumerate(prior['countries']):
            ids=np.array(prior['native_countries'])==c;factor=factors[c] if case=='country_factors' else 1.
            cap=(components['pv'][:,ids]@components['mapping'][ids])*(86/90)*factor
            point=np.divide(q*cap,av,out=np.zeros_like(q),where=av>0).sum(axis=1);lower=np.maximum(q-av+cap,0).sum(axis=1);upper=np.minimum(q,cap).sum(axis=1)
            assert np.max(cap-av)<1e-5 and np.all(lower<=point+1e-5) and np.all(point<=upper+1e-5)
            r,m,h=diagnostics(c,cap.sum(axis=1),point,lower,upper,components['observed'][:,ci],prior['ember'])
            quantities[case].append(r);monthly[case]+=m;diurnal[case]+=h
        print(case,certs[case],flush=True)
    result=dict(status='all_17520_regression_source_native_and_kkt_replays_passed',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),inputs_sha256=digest(OUT/'inputs.json'),
        original_ember_sha256=digest(ember_file),original_ember_receipt_sha256=digest(receipt_file),
        audit_dependencies={f:digest(ROOT/'tools'/f) for f in ['price_mechanism_2025.py','audit_nve_hydro_diagnostics_2025.py','audit_solar_fleet_2025.py']},
        factors=fit_records,cases=certs,quantities=quantities,monthly=monthly,diurnal=diurnal,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
