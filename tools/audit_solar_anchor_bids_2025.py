"""Independent bounded-bid reconstruction, annual native/KKT and mix checks."""
import json
import logging
import resource
import time
import numpy as np
import pandas as pd
import pycountry
import pypsa
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,MONTH,digest,ember_rows
from price_mechanism_2025 import dual_replay
from audit_nve_hydro_diagnostics_2025 import physics
from hourly_offer_curves_2025 import shape_metrics

OUT=ROOT/'data/bidding-zone-network-2025/solar-anchor-bids-v1'
SOLAR=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
FLEET=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'


def audit():
    began=time.perf_counter();sealed=json.loads((OUT/'inputs.json').read_text());summary=json.loads((OUT/'summary.json').read_text());design=sealed['design']
    assert summary['inputs_sha256']==digest(OUT/'inputs.json') and summary['producer_sha256']==sealed['producer_sha256']==digest(ROOT/'tools/solar_anchor_bids_2025.py')
    assert design==json.loads((ROOT/'config/solar-anchor-bids-2025.json').read_text())
    for f,h in sealed['sources'].items():assert digest(ROOT/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert digest(OUT/'proposal.npz')==sealed['proposal_sha256']
    previous=json.loads((SOLAR/'audit.json').read_text());assert previous['summary_sha256']==digest(SOLAR/'summary.json') and previous['inputs_sha256']==digest(SOLAR/'inputs.json')
    p=json.loads((ANCHOR/'inputs.json').read_text());s=dict(np.load(ANCHOR/'inputs.npz'));prop=dict(np.load(OUT/'proposal.npz'));ng,nl,nz=p['ng'],p['nl'],p['nz'];kinds=sealed['kinds']
    av=s['availability']+s['solar_aligned']*86/90-s['solar_original']+np.load(SOLAR/'delta.npz')['delta']
    for r,v in zip(p['capacity'],s['thermal'],strict=True):av+=(r['factor']-1)*v
    target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];known=np.isfinite(target).all(axis=0);assert known.sum()==41
    from seasonal_calendar_bids_2025 import calendar
    from weekly_supply_bids_2025 import weekly
    cal,_=calendar(p['zones']);w,_=weekly(p['zones']);features=np.concatenate([cal,w[:,:,None]],axis=2)
    np.testing.assert_array_equal(features,prop['features'])
    with np.load(ROOT/sealed['control']) as z:control_x=z['values'];control_y=z['row_duals'][:,:nz]
    # Augmented least-squares independently checks the producer's normal equations.
    for zi,zone in enumerate(p['zones']):
        for fi,family in enumerate(design['resources']):
            ids=[j for j,k in enumerate(kinds) if k==family and s['offer_zones'][j]==zone]
            interior=np.zeros(8760,bool)
            for j in ids:interior|=(control_x[:,j]>.001)&(av[:,j]-control_x[:,j]>.001)&(abs(s['cost'][:,j]-control_y[:,zi])<=1e-5)
            for key,mask in [('calendar',np.ones(8760,bool)),('resource',interior)]:
                good=mask&np.isfinite(target[:,zi]);beta=np.zeros(16)
                if good.sum()>=design['minimum_hours']:
                    a=np.r_[features[good,zi],np.sqrt(design['ridge'])*np.eye(16)]
                    b=np.r_[np.clip(target[good,zi]-control_y[good,zi],-design['residual_clip_eur_mwh'],design['residual_clip_eur_mwh']),np.zeros(16)]
                    beta=np.linalg.lstsq(a,b,rcond=None)[0]
                np.testing.assert_allclose(beta,prop[key][zi,fi],rtol=0,atol=1e-9)
    n=pypsa.Network(ANCHOR/'native.nc');n.determine_network_topology()
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            table=n.components[component].static;branch=table.loc[name]
            if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:table.loc[name,'s_max_pu']*=1.15
    native_arrays=dict(np.load(ANCHOR/'native-base.npz'));A=load_npz(ANCHOR/'network.npz');layout=json.loads((ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json').read_text())
    # Country/resource membership is exact for these compiled thermal columns.
    groups={}
    for j,family in enumerate(kinds):
        if family not in design['resources']:continue
        countries={str(n.buses.loc[n.generators.iloc[i].bus,'country']) for i in layout['members'][j]}
        assert len(countries)==1,'Mixed national membership needs explicit allocation bounds'
        key=(next(iter(countries)),dict(gas='Gas',coal='Coal',nuclear='Nuclear')[family]);groups.setdefault(key,[]).append(j)
    ember_path=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=json.loads((ember_path.parent/'receipt.json').read_text());assert digest(ember_path)==receipt['sha256'];bank=ember_rows(ember_path)
    solar_inputs=json.loads((FLEET/'inputs.json').read_text());solar_factors={r['country']:r['factor'] for r in json.loads((SOLAR/'inputs.json').read_text())['factors']};components=dict(np.load(FLEET/'components.npz'))
    fitted=json.loads((SOLAR/'inputs.json').read_text())['fitted_countries'];results={}
    for case,strength in design['cases'].items():
        record=summary['cases'][case];path=ROOT/record['annual']['witness'];assert digest(path)==record['annual']['witness_sha256']
        with np.load(path) as z:x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        c=s['cost'].copy();coef=prop['resource' if case=='resource_full' else 'calendar']
        for j,family in enumerate(kinds):
            if family not in design['resources']:continue
            zi=p['zones'].index(s['offer_zones'][j]);fi=design['resources'].index(family);bound=design['bounds_eur_mwh'][fi]
            shift=np.minimum(bound,np.maximum(-bound,(features[:,zi]*coef[zi,fi]).sum(axis=1)))*strength
            c[:,j]=np.maximum(0,s['cost'][:,j]+shift)
        maximum=dict(primal_mw=0.,objective_eur=0.,duality_gap_maximum_eur=0.,complementarity_maximum_eur=0.)
        for start in range(0,8760,168):
            sl=slice(start,min(start+168,8760));T=len(x[sl]);m={k:s[k][sl] for k in ['load','link_min','link_max','island_rhs']}
            m.update(cost=c[sl],ng=ng,nl=nl,nz=nz,A=A,availability=av[sl],islands=[None]*p['islands'],ratings=s['ratings'])
            rc=np.c_[m['cost'],np.zeros((T,nl+nz))]-(A.T@y[sl].T).T
            cert=dual_replay(m,x[sl],y[sl],rc,obj[sl],s['flow'][sl]);ax=(A@x[sl].T).T
            lo=np.c_[m['load'],m['island_rhs'],-m['ratings']-s['flow'][sl]];hi=np.c_[m['load'],m['island_rhs'],m['ratings']-s['flow'][sl]]
            maximum['primal_mw']=max(maximum['primal_mw'],float(np.maximum(lo-ax,0).max()),float(np.maximum(ax-hi,0).max()))
            maximum['objective_eur']=max(maximum['objective_eur'],float(abs((x[sl,:ng]*c[sl]).sum(axis=1)-obj[sl]).max()))
            for k in ['duality_gap_maximum_eur','complementarity_maximum_eur']:maximum[k]=max(maximum[k],cert[k])
        assert maximum['primal_mw']<=1e-4 and maximum['objective_eur']<.05
        collapsed=x[:,:p['reference_ng']].copy()
        for extra in p['extras']:collapsed[:,extra['parent']]+=x[:,extra['column']]
        native_values=np.zeros((8760,p['base_ng']));native_av=native_arrays['availability'].copy();change=av-s['availability']
        for j,parent in enumerate(p['parents']):native_values[:,parent]+=collapsed[:,j];native_av[:,parent]+=change[:,j]
        native_values=np.c_[native_values,collapsed[:,p['original_ng']:p['reference_ng']],x[:,ng:]]
        native=dict(ng=p['base_ng']+len(p['additions']),nl=nl,nz=nz,zones=p['zones'],weights=p['weights'],offer_zones=p['base_offer_zones']+[r['zone'] for r in p['additions']],availability=np.c_[native_av,np.tile([r['mw'] for r in p['additions']],(8760,1))],link_min=s['link_min'],link_max=s['link_max'])
        residual=physics(n,native,native_values,s['load'],pd.DataFrame(native_arrays['off'].copy(),columns=p['native_off_columns']),0)
        emergency=float(np.maximum(x[:,:ng][:,s['emergency_mask']],0).sum());assert emergency<=1e-6
        rows=[dict(zone=zone,**shape_metrics(y[:,j],target[:,j])) for j,zone in enumerate(p['zones'])];mae=float(np.mean([r['mae_eur_mwh'] for r in rows if r['known_hours']==8760]));assert abs(mae-record['europe_mae'])<1e-9
        thermal=[]
        for (country,fuel),ids in sorted(groups.items()):
            iso='XKX' if country=='XK' else pycountry.countries.get(alpha_2=country).alpha_3
            for month in range(1,13):
                observed=bank.get((iso,fuel,month));predicted=float(x[MONTH==month][:,ids].sum()/1e6)
                thermal.append(dict(country=country,fuel=fuel,month=month,model_twh=predicted,observed_twh=observed,normalized_error=abs(predicted-observed)/max(observed,.25) if observed is not None else None))
        solar=[];q=np.clip(x[:,:ng],0,av)
        for country in fitted:
            ids=np.array(solar_inputs['native_countries'])==country;cap=(components['pv'][:,ids]@components['mapping'][ids])*(86/90)*solar_factors[country]
            point=np.divide(q*cap,av,out=np.zeros_like(q),where=av>0).sum(axis=1);lower=np.maximum(q-av+cap,0).sum(axis=1);upper=np.minimum(q,cap).sum(axis=1)
            for month in range(1,13):
                mask=MONTH==month;observed=solar_inputs['ember'][f'{country}_{month:02d}']
                solar.append(dict(country=country,month=month,model_twh=float(point[mask].sum()/1e6),lower_twh=float(lower[mask].sum()/1e6),upper_twh=float(upper[mask].sum()/1e6),observed_twh=observed))
        results[case]=dict(europe_mae=mae,native_residual_mw=residual,emergency_mwh=emergency,**maximum,prices=rows,thermal=thermal,solar=solar,solar_monthly_mae=float(np.mean([abs(r['model_twh']-r['observed_twh']) for r in solar])),thermal_monthly_normalized_error=float(np.mean([r['normalized_error'] for r in thermal if r['normalized_error'] is not None])))
        print(case,{k:v for k,v in results[case].items() if k not in ['prices','thermal','solar']},flush=True)
    control=results['control'];eligible=[]
    for case,r in results.items():
        r['eligible']=r['solar_monthly_mae']<=1.05*control['solar_monthly_mae']+1e-12 and r['thermal_monthly_normalized_error']<=1.05*control['thermal_monthly_normalized_error']+1e-12
        if r['eligible']:eligible.append(case)
    winner=min(eligible,key=lambda k:(results[k]['europe_mae'],list(results).index(k)))
    deps=['price_mechanism_2025.py','audit_nve_hydro_diagnostics_2025.py','hourly_offer_curves_2025.py','generation_mix_2025.py','seasonal_calendar_bids_2025.py','weekly_supply_bids_2025.py']
    result=dict(status='all_35040_source_bid_native_kkt_replays_passed',auditor_sha256=digest(__file__),dependencies={f:digest(ROOT/'tools'/f) for f in deps},inputs_sha256=digest(OUT/'inputs.json'),summary_sha256=digest(OUT/'summary.json'),selected=winner,cases=results,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
