"""Independent dated-source, all-year volume/native and LP optimality replay.

Does not import the eligibility compiler or annual clearing driver.
"""
import json
import logging
import resource
import time
import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest
from audit_nve_hydro_diagnostics_2025 import physics

OUT=ROOT/'data/bidding-zone-network-2025/thermal-eligibility-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'


def audit():
    began=time.perf_counter();sealed=json.loads((OUT/'inputs.json').read_text());s=json.loads((OUT/'summary.json').read_text())
    assert s['inputs_sha256']==digest(OUT/'inputs.json')
    assert sealed['producer_sha256']==s['producer_sha256']==digest(ROOT/'tools/thermal_eligibility_2025.py')
    assert sealed['design']==json.loads((ROOT/'config/thermal-eligibility-2025.json').read_text())
    for file,h in sealed['source_hashes'].items():assert digest(ROOT/file)==h
    for file,h in sealed['anchor_files'].items():assert digest(ANCHOR/file)==h
    for file,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/file)==h
    assert sealed['removal_sha256']==digest(OUT/'removal.npz')
    p=json.loads((ANCHOR/'inputs.json').read_text());aa=json.loads((ANCHOR/'audit.json').read_text())
    assert aa['summary_sha256']==digest(ANCHOR/'summary.json') and aa['inputs_sha256']==digest(ANCHOR/'inputs.json')
    assert aa['auditor_sha256']==digest(ROOT/'tools/audit_annual_solar_alignment_2025.py')
    for file,h in p['source_hashes'].items():assert digest(ROOT/file)==h
    for file,h in p['dependencies'].items():assert digest(ROOT/'tools'/file)==h
    source=dict(np.load(ANCHOR/'inputs.npz'));A=load_npz(ANCHOR/'network.npz')
    pool=load_npz(ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1/pooling.npz').toarray()
    plants=pd.read_csv(GRID/'powerplants_s_128.csv',index_col=0)
    removal=np.zeros_like(source['availability']);dates=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as ds:
        names=list(ds.generators_i.values.astype(str))
        for spec in sealed['design']['units']:
            unit=plants.loc[spec['source_row']]
            assert (unit.Name,unit.Country,unit.Fueltype,unit.bus,float(unit.Capacity))==(spec['name'],'DE','Hard Coal',spec['bus'],spec['source_mw'])
            # Exact aliases manually inspected against these dated legal records,
            # not a present-day role copied backwards or output-derived outage.
            text=' '.join((OUT/'sources'/spec['decision'].replace('.pdf','.txt')).read_text().split())
            assert spec['official_id'] in text
            if spec['name']=='Bergkamen':
                assert '01.11.2024' in text and '31.03.2026' in text
            else:
                assert 'in der Netzreserve gebundenen Anlagen' in text
                assert 'bis zum 31.03.2025' in text and '01.04.2025' in text and '31.03.2031' in text
            j=names.index(spec['bus']+' coal')
            assert abs(plants.loc[(plants.bus==spec['bus'])&(plants.Fueltype=='Hard Coal'),'Capacity'].sum()-float(ds.generators_p_nom[j]))<1e-7
            start=pd.Timestamp(spec['start'],tz='Europe/Berlin').tz_convert('UTC')
            stop=pd.Timestamp(spec['stop'],tz='Europe/Berlin').tz_convert('UTC')
            for col in np.flatnonzero(pool[j]):
                removal[:,col]+=np.where((dates>=start)&(dates<stop),float(unit.Capacity)*pool[j,col],0.)
    np.testing.assert_allclose(removal,np.load(OUT/'removal.npz')['removal'],rtol=0,atol=1e-10)
    assert np.allclose(removal.sum(axis=1),2101.6)
    solar=source['availability']+source['solar_aligned']-source['solar_original'];stock=solar.copy()
    for row,vector in zip(p['capacity'],source['thermal'],strict=True):stock+=(row['factor']-1)*vector
    coal=source['thermal'][0];rescaled=stock.copy()
    # Independent construction by total remaining source MW, not subtraction
    # from the reported-stock control. No capacity above the unscaled fleet.
    for t in range(8760):
        remaining=coal-removal[t];factor=15951./remaining.sum()
        assert 0<factor<=1
        rescaled[t]+=remaining*factor-coal*p['capacity'][0]['factor']
    books=dict(solar_control=solar,eligibility=solar-removal,stock_control=stock,reconciled=rescaled)
    n=pypsa.Network(ANCHOR/'native.nc');n.determine_network_topology()
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            branch=n.df(component).loc[name]
            if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:n.df(component).loc[name,'s_max_pu']*=1.15
    native_arrays=dict(np.load(ANCHOR/'native-base.npz'));ng,nl,nz=p['ng'],p['nl'],p['nz']
    observed=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];certs={};metrics={}
    for name,av in books.items():
        record=s['cases'][name];path=ROOT/record['annual']['witness'];assert digest(path)==record['annual']['witness_sha256']
        with np.load(path) as z:
            x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        maxima=dict(primal=0.,objective=0.,stationarity=0.,duality_gap=0.,complementarity=0.)
        for start in range(0,8760,168):
            sl=slice(start,min(start+168,8760));v=x[sl];yd=y[sl];T=len(v)
            cost=np.c_[source['cost'][sl],np.zeros((T,nl+nz))];rc=cost-(A.T@yd.T).T;ax=(A@v.T).T
            lower=np.c_[np.zeros((T,ng)),source['link_min'][sl],np.full((T,nz),-np.inf)]
            upper=np.c_[av[sl],source['link_max'][sl],np.full((T,nz),np.inf)]
            lo=np.c_[source['load'][sl],source['island_rhs'][sl],-source['ratings']-source['flow'][sl]]
            hi=np.c_[source['load'][sl],source['island_rhs'][sl],source['ratings']-source['flow'][sl]]
            primal=max(np.maximum(lower-v,0).max(),np.maximum(v-upper,0).max(),np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max())
            dual=np.zeros(T);comp=0.
            for bound,part,value in [(lo,np.maximum(yd,0),ax),(hi,np.minimum(yd,0),ax),(lower,np.maximum(rc,0),v),(upper,np.minimum(rc,0),v)]:
                finite=np.isfinite(bound);assert abs(part[~finite]).max(initial=0)<1e-5
                dual+=np.sum(np.where(finite,bound,0)*part,axis=1)
                comp=max(comp,float(abs(part[finite]*(value[finite]-bound[finite])).max(initial=0)))
            vals=dict(primal=float(primal),objective=float(abs((v*cost).sum(axis=1)-obj[sl]).max()),stationarity=float(abs(rc[:,ng+nl:]).max()),duality_gap=float(abs(obj[sl]-dual).max()),complementarity=comp)
            for k,value in vals.items():maxima[k]=max(maxima[k],value)
        assert maxima['primal']<=1e-4 and maxima['stationarity']<1e-5
        assert max(maxima[k] for k in ['objective','duality_gap','complementarity'])<.05
        collapsed=x[:,:p['reference_ng']].copy()
        for extra in p['extras']:collapsed[:,extra['parent']]+=x[:,extra['column']]
        native_values=np.zeros((8760,p['base_ng']));native_av=native_arrays['availability'].copy()
        delta=av-source['availability']
        for j,parent in enumerate(p['parents']):
            native_values[:,parent]+=collapsed[:,j];native_av[:,parent]+=delta[:,j]
        native_values=np.c_[native_values,collapsed[:,p['original_ng']:p['reference_ng']],x[:,ng:]]
        native=dict(ng=p['base_ng']+len(p['additions']),nl=nl,nz=nz,zones=p['zones'],weights=p['weights'],offer_zones=p['base_offer_zones']+[r['zone'] for r in p['additions']],
            availability=np.c_[native_av,np.tile([r['mw'] for r in p['additions']],(8760,1))],link_min=source['link_min'],link_max=source['link_max'])
        off=pd.DataFrame(native_arrays['off'].copy(),index=range(8760),columns=p['native_off_columns'])
        native_max=physics(n,native,native_values,source['load'],off,0)
        emergency=float(x[:,:ng][:,source['emergency_mask']].sum());assert emergency<=1e-6
        rows=[]
        for j,zone in enumerate(p['zones']):
            if not np.isfinite(observed[:,j]).all():continue
            model=y[:,j];obs=observed[:,j];err=model-obs;tail=obs>300
            rows.append(dict(zone=zone,mae=float(abs(err).mean()),bias=float(err.mean()),correlation=float(np.corrcoef(model,obs)[0,1]),
                high_price_hours=int(tail.sum()),high_price_mae=float(abs(err[tail]).mean()) if tail.any() else None,
                missed_above_300=int(((obs>300)&(model<=300)).sum()),false_above_300=int(((obs<=300)&(model>300)).sum())))
            reported=next(r for r in record['metrics']['zones'] if r['zone']==zone)
            assert abs(rows[-1]['mae']-reported['mae_eur_mwh'])<1e-9
        assert len(rows)==41 and abs(np.mean([r['mae'] for r in rows])-record['europe_mae'])<1e-9
        # Allocation is unique only when these are pure coal columns at every hour.
        ids=coal>0
        np.testing.assert_allclose(source['availability'][:,ids],np.broadcast_to(coal[ids],(8760,ids.sum())),rtol=0,atol=1e-7)
        coal_twh=float(x[:,:ng][:,ids].sum()/1e6)
        assert abs(coal_twh-record['german_coal_dispatch_twh'])<1e-8
        assert abs(av[19*24+16,ids].sum()-record['german_coal_available_mw'])<1e-7
        certs[name]=dict(hours=8760,native_residual_mw=native_max,emergency_mwh=emergency,german_coal_dispatch_twh=coal_twh,**maxima)
        metrics[name]=rows
        print(name,certs[name],flush=True)
    write=dict(status='all_35040_source_native_and_kkt_replays_passed',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),
               inputs_sha256=digest(OUT/'inputs.json'),cases=certs,metrics=metrics,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(write,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
