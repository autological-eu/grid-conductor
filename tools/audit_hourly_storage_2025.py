"""Independent annual stock, original-network, LP dual and observed-score replay."""
import json
import logging
import resource
import time
import numpy as np
import pycountry
import pypsa
import xarray as xr
from scipy.sparse import coo_matrix,hstack
from generation_mix_2025 import ROOT,digest,MONTH,ember_rows
from europe_linked_clearing_2025 import load
from hourly_offer_curves_2025 import shape_metrics

OUT=ROOT/'data/bidding-zone-network-2025/hourly-storage-bids-v1'


def audit():
    started=time.perf_counter();sealed=json.loads((OUT/'inputs.json').read_text());summary=json.loads((OUT/'summary.json').read_text());design=sealed['design']
    assert summary['status']=='two_complete_chronological_storage_candidates_not_adopted' and summary['inputs_sha256']==digest(OUT/'inputs.json')
    assert sealed['producer_sha256']==summary['producer_sha256']==digest(ROOT/'tools/run_hourly_storage_2025.py')
    for f,h in sealed['sources'].items():assert digest(ROOT/f)==h,f
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h,f
    assert list(summary['cases'])==design['cases'] and len(design['cases'])==2
    from synthetic_bids_2025 import SOURCE
    with xr.open_dataset(SOURCE) as ds:
        names=ds.storage_units_i.values.astype(str);carriers=ds.storage_units_carrier.values.astype(str);power=ds.storage_units_p_nom.values
        source_ids=set(names[(carriers=='PHS')&(power>0)])
        assert {r['source_id'] for r in sealed['assets']}==source_ids
        for name in source_ids:
            j=list(names).index(name);rows=[r for r in sealed['assets'] if r['source_id']==name]
            def field(k,default):return float(ds['storage_units_'+k].values[j]) if 'storage_units_'+k in ds else default
            assert abs(sum(r['source_share'] for r in rows)-1)<1e-10
            assert abs(sum(r['discharge_mw'] for r in rows)-power[j]*field('p_max_pu',1))<1e-6
            assert abs(sum(r['charge_mw'] for r in rows)+power[j]*field('p_min_pu',-1))<1e-6
            assert abs(sum(r['energy_mwh'] for r in rows)-power[j]*field('max_hours',1))<1e-5
            for r in rows:
                assert r['eta_charge']==field('efficiency_store',1) and r['eta_discharge']==field('efficiency_dispatch',1)
                assert r['standing_loss']==field('standing_loss',0)
    _,active,p,s,m,gen_cost,_,reference,layout_path=load();n=m['A'].shape[1];nz=p['nz'];T=8760
    own=reference['row_duals'][:,:nz];forecast=np.empty_like(own)
    for t in range(T):forecast[t]=np.maximum(0,np.percentile(own[min(t+1,T-1):min(t+1+design['forecast_hours'],T)],50,axis=0))
    assert digest(OUT/'forecast.npz')==summary['forecast_sha256']
    np.testing.assert_allclose(forecast,np.load(OUT/'forecast.npz')['reference'],rtol=0,atol=1e-10)
    target_path=ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz';target=np.load(target_path)['prices'];known=np.isfinite(target).all(axis=0);assert known.sum()==41
    native_path=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc';native=pypsa.Network(native_path);layout=json.loads(layout_path.read_text());groups={}
    for j,kind in enumerate(layout['kinds']):
        if kind not in ['gas','coal','nuclear']:continue
        countries={str(native.buses.loc[native.generators.iloc[i].bus,'country']) for i in layout['members'][j]};assert len(countries)==1
        groups.setdefault((next(iter(countries)),{'gas':'Gas','coal':'Coal','nuclear':'Nuclear'}[kind]),[]).append(j)
    bank_path=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt_path=bank_path.parent/'receipt.json';assert digest(bank_path)==json.loads(receipt_path.read_text())['sha256'];bank=ember_rows(bank_path)
    renewable=[j for j,k in enumerate(layout['kinds']) if k=='renewable'];results={}
    for case,record in [('baseline',None),*summary['cases'].items()]:
        if case=='baseline':values=reference['values'];duals=reference['row_duals'];seconds=active['witness']['clearing_seconds'];physical=None;storage=None
        else:
            path=ROOT/record['witness'];assert digest(path)==record['witness_sha256']
            with np.load(path) as z:
                values=z['values'];duals=z['row_duals'];energy=z['energy_mwh'];initial=z['initial_energy_mwh'];objectives=z['objectives'];clip=z['state_clip_mwh'];np.testing.assert_array_equal(z['hours'],np.arange(T))
            assert record['assets']==sealed['assets']+(design['battery_demo'] if case=='phs_plus_battery_demo' else [])
            assets=record['assets'];S=len(assets);cap=np.array([r['energy_mwh'] for r in assets]);eta_c=np.array([r['eta_charge'] for r in assets]);eta_d=np.array([r['eta_discharge'] for r in assets]);phi=1-np.array([r['standing_loss'] for r in assets]);zone_ids=[p['zones'].index(r['zone']) for r in assets]
            assert np.all(initial==0) and record['hours']==T
            previous=np.vstack([initial,energy[:-1]]);charge=values[:,n:n+S];discharge=values[:,n+S:];balance=previous*phi+charge*eta_c-discharge/eta_d
            water=float(abs(balance-energy).max());assert water<=1e-4 and energy.min()>=-1e-4 and np.maximum(energy-cap,0).max()<=1e-4
            assert min(charge.min(),discharge.min())>=-1e-4 and np.minimum(charge,discharge).max()<=1e-6
            charge_max=np.minimum(np.array([r['charge_mw'] for r in assets]),np.maximum(cap-previous*phi,0)/eta_c);discharge_max=np.minimum(np.array([r['discharge_mw'] for r in assets]),previous*phi*eta_d)
            assert np.maximum(charge-charge_max,0).max()<=1e-4 and np.maximum(discharge-discharge_max,0).max()<=1e-4
            for day in range(1,365):assert np.max(abs(previous[day*24]-energy[day*24-1]))==0
            B=coo_matrix((np.ones(S),(zone_ids,np.arange(S))),shape=(m['A'].shape[0],S)).tocsc();A=hstack([m['A'],-B,B],format='csc')
            maximum=dict(primal_mw=0.,duality_gap_eur=0.,complementarity_eur=0.,free_reduced_cost_eur_mwh=0.);finite=np.r_[np.arange(p['ng']+p['nl']),np.arange(n,n+2*S)];free=np.arange(p['ng']+p['nl'],n)
            for start in range(0,T,168):
                sl=slice(start,min(T,start+168));L=len(values[sl]);buy=eta_c*eta_d*forecast[sl][:,zone_ids]-design['bid_margin_eur_mwh'];sell=forecast[sl][:,zone_ids]+design['bid_margin_eur_mwh'];cost=np.c_[gen_cost[sl],np.zeros((L,p['nl']+nz)),-buy,sell]
                lower=np.c_[np.zeros((L,p['ng'])),s['link_min'][sl],np.full((L,nz),-np.inf),np.zeros((L,2*S))];upper=np.c_[m['availability'][sl],s['link_max'][sl],np.full((L,nz),np.inf),charge_max[sl],discharge_max[sl]]
                lo=np.c_[s['load'][sl],s['island_rhs'][sl],-s['ratings']-s['flow'][sl]];hi=np.c_[s['load'][sl],s['island_rhs'][sl],s['ratings']-s['flow'][sl]];x=values[sl];y=duals[sl];ax=(A@x.T).T;rc=cost-(A.T@y.T).T
                primal=float(max(np.maximum(lower-x,0).max(),np.maximum(x-upper,0).max(),np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max()));obj=(cost*x).sum(axis=1);np.testing.assert_allclose(obj,objectives[sl],rtol=0,atol=.05)
                dual=(np.maximum(y,0)*lo+np.minimum(y,0)*hi).sum(axis=1)+(np.maximum(rc[:,finite],0)*lower[:,finite]+np.minimum(rc[:,finite],0)*upper[:,finite]).sum(axis=1)
                gap=float(abs(obj-dual).max());comp=float(max(abs(np.maximum(y,0)*(ax-lo)).max(),abs(np.minimum(y,0)*(ax-hi)).max(),abs(np.maximum(rc[:,finite],0)*(x[:,finite]-lower[:,finite])).max(),abs(np.minimum(rc[:,finite],0)*(x[:,finite]-upper[:,finite])).max()));fr=float(abs(rc[:,free]).max())
                assert primal<=1e-4 and gap<.05 and comp<.05 and fr<1e-5
                for k,v in dict(primal_mw=primal,duality_gap_eur=gap,complementarity_eur=comp,free_reduced_cost_eur_mwh=fr).items():maximum[k]=max(maximum[k],v)
            emergency=float(np.maximum(values[:,:p['ng']][:,s['emergency_mask']],0).sum());assert emergency<=1e-6
            losses=float((previous*(1-phi)).sum());ledger=float(abs(energy[-1].sum()-initial.sum()-(charge*eta_c).sum()+(discharge/eta_d).sum()+losses))
            assert ledger<.01
            physical=maximum|dict(maximum_stock_residual_mwh=water,annual_ledger_residual_mwh=ledger,emergency_mwh=emergency,maximum_recorded_clip_mwh=float(clip.max()))
            storage=dict(charge_twh=float(charge.sum()/1e6),discharge_twh=float(discharge.sum()/1e6),initial_twh=float(initial.sum()/1e6),final_twh=float(energy[-1].sum()/1e6),standing_loss_twh=losses/1e6,simultaneous_hours=int(np.any((charge>1e-6)&(discharge>1e-6),axis=1).sum()),assets=len(assets),power_gw=sum(r['discharge_mw'] for r in assets)/1000,capacity_gwh=cap.sum()/1000);seconds=record['case_wall_seconds']
        price_rows=[dict(zone=z,**shape_metrics(duals[:,j],target[:,j])) for j,z in enumerate(p['zones'])];mae=float(np.mean([r['mae_eur_mwh'] for r in price_rows if r['known_hours']==T]))
        if case=='baseline':assert abs(mae-active['prices']['equal_zone_mae'])<1e-9
        else:assert abs(mae-record['price_mae'])<1e-9
        thermal=[]
        for (country,fuel),ids in sorted(groups.items()):
            iso='XKX' if country=='XK' else pycountry.countries.get(alpha_2=country).alpha_3
            for month in range(1,13):
                obs=bank.get((iso,fuel,month));v=float(values[MONTH==month][:,ids].sum()/1e6);thermal.append(dict(country=country,fuel=fuel,month=month,model_twh=v,observed_twh=obs,absolute_error_twh=abs(v-obs) if obs is not None else None))
        scores={fuel:float(np.mean([r['absolute_error_twh'] for r in thermal if r['fuel']==fuel and r['absolute_error_twh'] is not None])) for fuel in ['Gas','Coal','Nuclear']}
        results[case]=dict(price_mae=mae,mean_correlation=float(np.mean([r['correlation'] for r in price_rows if r['known_hours']==T])),prices=price_rows,thermal=thermal,thermal_monthly_mae=scores,renewable_available_twh=float(m['availability'][:,renewable].sum()/1e6),renewable_dispatch_twh=float(values[:,renewable].sum()/1e6),seconds=seconds,physical=physical,storage=storage)
        print(case,'MAE',mae,'storage',storage,flush=True)
    sources={str(f.relative_to(ROOT)):digest(f) for f in [target_path,bank_path,receipt_path,native_path,layout_path]}
    result=dict(status='all_17520_hourly_storage_physics_and_lp_certificates_replayed',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),inputs_sha256=digest(OUT/'inputs.json'),cases=results,sources=sources,dependencies={f:digest(ROOT/'tools'/f) for f in ['generation_mix_2025.py','europe_linked_clearing_2025.py','hourly_offer_curves_2025.py','compare_daily_dispatch_prices.py']},seconds=time.perf_counter()-started)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(result['status'],'seconds',result['seconds'],flush=True)


if __name__=='__main__':logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
