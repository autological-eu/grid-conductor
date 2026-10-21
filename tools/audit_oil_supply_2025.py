"""Independent oil-source, expanded-matrix, native-component and annual KKT replay.

Does not import the oil compiler or annual driver. No fresh optimisation.
"""
import argparse, datetime as dt, json, logging, resource, signal, time
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, coo_matrix
from generation_mix_2025 import ROOT, MONTH, digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from seasonal_calendar_bids_2025 import bids
from inverse_bid_ensemble_2025 import costs, fingerprint
from audit_inverse_bid_ensemble_2025 import quantities
from audit_nve_hydro_diagnostics_2025 import physics
from audit_seasonal_calendar_bids_2025 import compare, price_summary
from price_mechanism_2025 import dual_replay
from intraday_offer_bids_2025 import TIMEZONES


def audit(folder, out):
    began=time.perf_counter(); out.mkdir(parents=True,exist_ok=False)
    s=json.loads((folder/'summary.json').read_text()); design=s['design']
    assert design==json.loads((ROOT/'config/oil-supply-2025.json').read_text())
    assert design['cases']==['control','daily_oil','missing_capacity','capacity_and_daily_oil']
    assert design['maximum_annual_solves']==4 and design['capacity_fill_countries']==['PL','SK','SI']
    assert s['producer_sha256']==digest(ROOT/'tools/run_oil_supply_2025.py')
    assert s['helper_sha256']==digest(ROOT/'tools/oil_supply_2025.py')
    for p,h in s['source_hashes'].items(): assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items(): assert digest(ROOT/'tools'/p)==h
    root=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1'
    latest=ROOT/'data/bidding-zone-network-2025/weekly-bids-v1'; key='inverse_joint-nordic_higher-w100'
    old=json.loads((root/'summary.json').read_text()); ls=json.loads((latest/'summary.json').read_text())
    joint=ROOT/'data/bidding-zone-network-2025/joint-network-calibration-v4'; js=json.loads((joint/'summary.json').read_text())
    prior=ROOT/js['prior_inverse_folder']; ps=json.loads((prior/'summary.json').read_text())
    n,raw,fixed,*_=build(); base,off=compile_global(n,raw,fixed,'bidding_zone'); flow=branch_offsets(n,off)
    layout=json.loads((root/'layout.json').read_text()); parents=np.array(layout['parent']); ng=len(parents)
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    m=base.copy(); m['ng']=ng
    m['A']=base['A'][:,np.r_[parents,np.arange(base['ng'],base['A'].shape[1])]].tocsc()
    m['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
    for field in ['offer_zones','emergency_mask']: m[field]=base[field][parents]
    m['cost']=base['cost'][:,parents]
    with np.load(root/'calendar.npz') as z: cal,season,shares=z['features'],z['season'],z['country_shares']
    prop=json.loads((root/'proposal-refit.json').read_text())
    c=bids(m,layout,cal,season,np.array(prop['beta']),np.array(prop['gamma']),shares,old['refit_variant'])
    c=costs(m,layout,c,cal[:,:,[0,1,2,3,4]],shares,json.loads((prior/(js['bid_parent']+'-parameters.json')).read_text()),ps['design'])
    coefficients=json.loads((latest/'coefficients.json').read_text())[key]['coefficients']
    clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    for zi,zone in enumerate(m['zones']):
        weekend=(clock.tz_convert(TIMEZONES[zone[:2]]).dayofweek>=5).astype(float); w=weekend-weekend.mean()
        for j,family in enumerate(layout['kinds']):
            if m['offer_zones'][j]==zone and family in ['gas','coal','nuclear']:
                c[:,j]=np.maximum(0,c[:,j]+w*coefficients[zi][['gas','coal','nuclear'].index(family)])
    assert fingerprint(c)==next(r for r in ls['results'] if r['anchor']==key)['bid_sha256']
    factors=[]
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            branch=n.df(component).loc[name]
            factor=1.15 if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'} else 1.
            factors.append(factor); n.df(component).loc[name,'s_max_pu']*=factor
    m['ratings']=m['ratings']*factors
    with np.load(root/'development-targets.npz') as z: target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z: target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    # Independent XML capacity read: no collector/parser dependency.
    capacity=json.loads((ROOT/'data/oil-market-2025/capacity.json').read_text()); cap={}
    for row in capacity['countries']:
        raw=ROOT/row['raw_path']; assert digest(raw)==row['sha256']
        doc=ET.fromstring(raw.read_bytes())
        for e in doc.iter(): e.tag=e.tag.split('}')[-1]
        candidates=[ts for ts in doc.findall('TimeSeries') if ts.findtext('MktPSRType/psrType')=='B06']
        assert len(candidates)==1; ts=candidates[0]
        assert ts.findtext('quantity_Measure_Unit.name')=='MAW' and ts.findtext('inBiddingZone_Domain.mRID')==row['domain']
        periods=ts.findall('Period'); assert len(periods)==1; period=periods[0]
        assert period.findtext('resolution')=='P1Y' and period.findtext('timeInterval/start')=='2024-12-31T23:00Z' and period.findtext('timeInterval/end')=='2025-12-31T23:00Z'
        points=period.findall('Point'); assert len(points)==1 and points[0].findtext('position')=='1'
        mw=float(points[0].findtext('quantity')); assert 0<=mw<100000 and mw==row['mw']; cap[row['country']]=mw
    countries=design['capacity_fill_countries']; extra_cap=np.array([cap[k] for k in countries]); assert (extra_cap>0).all()
    for country in countries:
        assert n.generators[(n.generators.carrier=='oil')&n.generators.bus.map(n.buses.country).eq(country)].p_nom.sum()==0
    # Reconstruct daily fuel from the retained original 2025 quote rows and FX.
    market=json.loads((ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json').read_text())
    monthly=np.array([r['oil_eur_mwh_th'] for r in market['hours']]); carbon=np.array([r['co2_eur_t'] for r in market['hours']])
    quote_folder=ROOT/'data/fuel-prices/daily-inputs-v1'; fuel_summary=json.loads((quote_folder/'summary.json').read_text())
    quotes=pd.read_csv(quote_folder/'brent-quotes-2025.csv'); fx=pd.read_csv(ROOT/'data/fuel-prices/ecb-2025-api.csv')
    assert digest(quote_folder/'brent-quotes-2025.csv')==fuel_summary['eia']['quote_csv_sha256']
    for p,h in fuel_summary['sources'].items(): assert digest(ROOT/p)==h
    quote={dt.date.fromisoformat(r.date):r.brent_usd_barrel for r in quotes.itertuples()}
    rates={dt.date.fromisoformat(r.TIME_PERIOD):r.OBS_VALUE for r in fx.itertuples()}
    assert all(k.year==2025 and np.isfinite(v) and v>0 for k,v in quote.items())
    daily=monthly.copy(); fallback=0
    for i,date in enumerate(clock.date):
        qd=max((d for d in quote if d<=date),default=None); fd=max((d for d in rates if d<=date),default=None)
        if qd is None or fd is None: fallback+=1; continue
        assert (date-qd).days<=5 and (date-fd).days<=5
        daily[i]=quote[qd]/rates[fd]/market['assumptions']['oil_mwh_th_per_barrel']
    with np.load(quote_folder/'inputs.npz') as z: np.testing.assert_allclose(daily,z['oil'],atol=1e-12,rtol=0)
    tech=pd.read_csv(ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/costs_2025_processed.csv').set_index('technology').loc['oil']
    assert float(tech['efficiency'])==.35
    oil=[]
    for j,ids in enumerate(layout['members']):
        carriers=n.generators.iloc[ids].carrier
        if not (carriers=='oil').any(): continue
        assert (carriers=='oil').all()
        eta=n.generators.iloc[ids].efficiency.values; assert np.ptp(eta)<1e-10
        weights=n.generators.iloc[ids].p_nom.groupby(n.generators.iloc[ids].bus.map(n.buses.country)).sum()
        oil.append((j,float(eta[0]),(weights/weights.sum()).to_dict()))
    certificates=[]; bid_ranges={}
    for name in design['cases']:
        extra=name in ['missing_capacity','capacity_and_daily_oil']; use_daily=name in ['daily_oil','capacity_and_daily_oil']
        fuel=daily if use_daily else monthly; case=m.copy(); cost=c.copy()
        for j,eta,_ in oil: cost[:,j]+=(fuel-monthly)/eta
        if extra:
            count=len(countries); cols=coo_matrix((np.ones(count),([m['zones'].index(v) for v in countries],np.arange(count))),shape=(m['A'].shape[0],count)).tocsc()
            case['A']=hstack([m['A'][:,:ng],cols,m['A'][:,ng:]],format='csc'); case['ng']=ng+count
            case['availability']=np.c_[m['availability'],np.tile(extra_cap,(8760,1))]
            case['offer_zones']=np.r_[m['offer_zones'],countries]; case['emergency_mask']=np.r_[m['emergency_mask'],np.zeros(count,bool)]
            new_cost=(fuel+carbon*float(tech['CO2 intensity']))/.35+float(tech['VOM'])
            cost=np.c_[cost,np.tile(new_cost[:,None],(1,count))]
        case['cost']=cost; info=s['annuals'][name]; path=folder/info['witness']; assert digest(path)==info['witness_sha256']
        ranges={}
        for j,eta,weights in oil:
            for country in weights:
                previous=ranges.get(country,[float('inf'),float('-inf')])
                ranges[country]=[min(previous[0],float(cost[:,j].min())),max(previous[1],float(cost[:,j].max()))]
        if extra:
            for j,country in enumerate(countries): ranges[country]=[float(cost[:,ng+j].min()),float(cost[:,ng+j].max())]
        bid_ranges[name]=ranges
        with np.load(path) as z:
            x,y,obj=z['values'],z['row_duals'],z['objectives']; assert z['optimal'].all(); np.testing.assert_array_equal(z['hours'],np.arange(8760))
        primal=max(float(np.maximum(-x[:,:case['ng']],0).max()),float(np.maximum(x[:,:case['ng']]-case['availability'],0).max()))
        assert primal<=1e-4
        objective=float(abs((x[:,:case['ng']]*cost).sum(axis=1)-obj).max()); assert objective<.05
        reduced=np.c_[cost,np.zeros((8760,case['nl']+case['nz']))]-(case['A'].T@y.T).T
        dual=dual_replay(case,x,y,reduced,obj,flow)
        # Independent component replay: collapse old split columns, retain source-backed new bounds.
        original=np.zeros((8760,base['ng']))
        for j,parent in enumerate(parents): original[:,parent]+=x[:,j]
        native=base.copy(); native['ratings']=m['ratings']
        if extra:
            native['ng']=base['ng']+len(countries); native['offer_zones']=np.r_[base['offer_zones'],countries]
            native['availability']=np.c_[base['availability'],np.tile(extra_cap,(8760,1))]
            original=np.c_[original,x[:,ng:case['ng']]]
        residual=physics(n,native,np.c_[original,x[:,case['ng']:]],base['load'],off.copy(),0)
        price=price_summary(y[:,:case['nz']],target['prices'],case['zones']); compare(price,s['outcomes'][name]['prices'])
        mon,_,lo,hi,cl,cu,dm=quantities(n,case,fixed,layout,av,x,s['countries'])
        oil_q=np.zeros((8760,len(s['countries'])))
        for j,eta,weights in oil:
            for country,w in weights.items(): oil_q[:,s['countries'].index(country)]+=x[:,j]*w
        if extra:
            for j,country in enumerate(countries):
                ci=s['countries'].index(country); oil_q[:,ci]+=x[:,ng+j]
                added=np.bincount(MONTH,weights=x[:,ng+j],minlength=13)[1:]/1e6
                for month in range(12):
                    for field in ['generation_point_twh','net_export_lower_twh','net_export_upper_twh','net_export_point_twh']: mon[month][field][ci]+=float(added[month])
                cl[:,ci]+=added; cu[:,ci]+=added
        compare(mon,s['outcomes'][name]['monthly_quantities'])
        ref=target['generation']; tr=target['trade']; known=np.isfinite(ref); tk=np.isfinite(tr)
        q=dict(price=price['equal_zone_mae'],generation=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean()),
               trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean()),price_areas=41,generation_targets=int(known.sum()),trade_targets=int(tk.sum()))
        compare(q,s['outcomes'][name]['quantity_errors'])
        compare((oil_q.sum(axis=0)/1e6).tolist(),s['outcomes'][name]['oil_generation_twh'])
        compare([(oil_q[MONTH==i].sum(axis=0)/1e6).tolist() for i in range(1,13)],s['outcomes'][name]['oil_by_month_twh'])
        assert digest(folder/(name+'-oil.npz'))==s['outcomes'][name]['oil_arrays_sha256']
        with np.load(folder/(name+'-oil.npz')) as z: np.testing.assert_allclose(oil_q,z['generation_mwh'],atol=1e-8,rtol=0)
        emergency=float(x[:,:case['ng']][:,case['emergency_mask']].sum()); assert emergency<=1e-6
        if name=='control': assert abs(price['equal_zone_mae']-ls['outcomes'][key]['prices']['equal_zone_mae'])<1e-7
        certificates.append(dict(case=name,hours=8760,native_residual_mw=residual,offer_bound_mw=primal,objective_error_eur=objective,emergency_mwh=emergency,**dual))
        print('Replayed',name,price['equal_zone_mae'],'oil TWh',oil_q.sum()/1e6,flush=True)
    result=dict(status='passed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,
                daily_oil_fallback_hours=fallback,capacity_fill_mw=dict(zip(countries,extra_cap.tolist())),
                existing_oil_capacity_mw=n.generators[n.generators.carrier=='oil'].p_nom.groupby(n.generators[n.generators.carrier=='oil'].bus.map(n.buses.country)).sum().to_dict(),
                bid_ranges_eur_mwh=bid_ranges,seconds=time.perf_counter()-began)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR); p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder.resolve(),a.out.resolve())
