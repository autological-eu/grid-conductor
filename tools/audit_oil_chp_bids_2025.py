"""Independent source, two-tranche, oil-output and annual native/KKT replay.

Does not import the new offer compiler or its driver. No new optimization.
"""
import argparse, csv, gzip, json, logging, resource, signal, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from shapely.geometry import Point
from oil_supply_2025 import anchor, inputs, compile_case as original_case
from bidding_zone_network_2025 import boundaries
from generation_mix_2025 import ROOT, MONTH, digest
from audit_nve_hydro_diagnostics_2025 import physics
from audit_seasonal_calendar_bids_2025 import compare, price_summary
from price_mechanism_2025 import dual_replay
from bid_calibration_2025 import month_quantities, immutable_hashes


def audit(folder, out):
    began=time.perf_counter();out.mkdir(parents=True,exist_ok=False)
    s=json.loads((folder/'summary.json').read_text());design=s['design']
    assert design==json.loads((ROOT/'config/oil-chp-bids-2025.json').read_text())
    assert design['cases']==['control','source_costs','chp25','chp50'] and design['maximum_new_annual_solves']==3
    assert s['producer_sha256']==digest(ROOT/'tools/run_oil_chp_bids_2025.py')
    for file,sha in s['source_hashes'].items(): assert digest(ROOT/file)==sha
    for file,sha in s['dependencies'].items(): assert digest(ROOT/'tools'/file)==sha
    for file,sha in s['files'].items(): assert digest(folder/file)==sha
    n,base,off,m,ctx,layout,c,flow,target=anchor()
    monthly,daily,co2,assumption,additions,oil=inputs(n,m,layout)
    reference,context=original_case(m,ctx,c,monthly,daily,co2,assumption,additions,oil,'capacity_and_daily_oil')
    metadata=json.loads((folder/'source-columns.json').read_text())
    # Raw auction rows, grouped explicitly by date without using the input helper.
    eua=ROOT/'data/bidding-zone-network-2025/thermal-bid-audit-v1/eex-eua-auction-2025.xlsx'
    table=pd.read_excel(eua,sheet_name='Primary Market Auction',header=5)
    assert len(table)==213 and set(table.Contract)=={'T3PA'} and set(table.Status)=={'successful'}
    quotes={}
    for date,group in table.groupby('Date'):
        assert date.year==2025
        quotes[date.date()]=float(np.average(group['Auction Price €/tCO2'],weights=group['Auction Volume tCO2']))
    clock=pd.date_range('2025-01-01',periods=8760,freq='h');carbon=[];fallback=0;maximum_age=0
    for date in clock.date:
        previous=max((d for d in quotes if d<=date),default=None)
        if previous is None: carbon.append(80.);fallback+=1
        else: carbon.append(quotes[previous]);maximum_age=max(maximum_age,(date-previous).days)
    carbon=np.array(carbon);assert fallback==144 and maximum_age==16
    market=json.loads((ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json').read_text())
    gas=np.array([r['gas_eur_mwh_th'] for r in market['hours']])
    with np.load(folder/'source-inputs.npz')as z:
        np.testing.assert_allclose(z['carbon'],carbon,rtol=0,atol=1e-12)
        np.testing.assert_array_equal(z['gas'],gas);np.testing.assert_array_equal(z['daily_oil'],daily)
    # Independently match raw plant rows to refined buses using source geometry.
    source=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/powerplants_s_128.csv'
    shapes,countries,_=boundaries();totals={};chp={};inventory=[]
    for idx,row in enumerate(csv.DictReader(source.open())):
        if row['Fueltype']!='Oil' or (row['DateIn'] and float(row['DateIn'])>2025) or (row['DateOut'] and float(row['DateOut'])<=2025):continue
        if not row['lat'] or not row['lon']:continue
        point=Point(float(row['lon']),float(row['lat']));names=sorted(countries.get(row['Country'],set()))
        if not names:continue
        contained=[z for z in names if shapes[z].covers(point)]
        if len(names)==1:zone=names[0]
        elif len(contained)==1:zone=contained[0]
        elif len(contained)>1:continue
        else:
            distance,zone=min((shapes[z].distance(point),z) for z in names)
            if distance>.5:continue
        bus=row['bus']+'::'+zone
        if bus not in n.buses.index:continue
        mw=float(row['Capacity']);totals[bus]=totals.get(bus,0)+mw
        if row['Set']=='CHP':chp[bus]=chp.get(bus,0)+mw
        inventory.append(dict(source_row=idx,country=row['Country'],bus=bus,role=row['Set'] or 'nan',mw=mw))
    compare(inventory,metadata['inventory'])
    records=[]
    for row in oil:
        native=n.generators.iloc[layout['members'][row['column']]]
        numerator=sum(g.p_nom*chp.get(g.bus,0)/totals[g.bus] if totals.get(g.bus,0)>0 else 0 for _,g in native.iterrows())
        share=float(numerator/native.p_nom.sum())
        records.append(row|dict(chp_share=min(1.,share)))
    for j,row in enumerate(additions):
        records.append(dict(column=reference['ng']-len(additions)+j,zone=row['zone'],efficiency=.35,countries={row['country']:1.},chp_share=0.))
    for row in records: row['carbon_weight']=sum(v for country,v in row['countries'].items() if country in design['carbon_countries'])
    compare(records,metadata['records'])
    # Independent observed B06 exports, retaining SK/SI unknown hours.
    explorer=ROOT/'public/research/country-explorer-2025';manifest=json.loads((explorer/'manifest.json').read_text())
    oil_index=next(i for i,t in enumerate(manifest['technologies'])if t['id']=='oil');observations={}
    for country in ['DE','BE','PL','SK','SI']:
        entry=next(r for r in manifest['countries']if r['code']==country);file=explorer/entry['file'];assert digest(file)==entry['sha256']
        doc=json.loads(gzip.decompress(file.read_bytes()));area=next(r for r in doc['generation']if r['id']=='country:'+country)
        observations[country]=np.array([np.nan if v is None else v/manifest['generation_scale']for v in doc['series'][area['observed'][oil_index]]])
    parents=np.array(layout['parent']);certificates=[]
    # Bring native branch limits to the unchanged joint anchor's Nordic ratings.
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            branch=n.df(component).loc[name]
            if {n.buses.loc[branch[k],'country']for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:
                n.df(component).loc[name,'s_max_pu']*=1.15
    for key in design['cases']:
        cost=reference['cost'].copy();av=reference['availability'].copy();extras=[];prices=[];volumes=[]
        for row in records:
            j,eta=row['column'],row['efficiency'];cp=80+(carbon-80)*row['carbon_weight']
            if key!='control':cost[:,j]=daily/eta+cp*assumption['emissions_t_mwh_th']/eta+assumption['variable_om_eur_mwh_el']
            share=design['chp_tranche_fractions'][key]*row['chp_share']
            if share:
                assert eta+design['useful_heat_efficiency_proxy']<=1 and 0<share<=1
                credit=design['useful_heat_efficiency_proxy']*(gas+cp*.198)/(.9*eta)
                prices.append(cost[:,j]-credit);volumes.append(reference['availability'][:,j]*share);av[:,j]-=volumes[-1]
                extras.append(dict(parent=j,column=reference['ng']+len(extras),share=share,zone=row['zone'],efficiency=eta,countries=row['countries']))
        assert json.loads((folder/'tranches.json').read_text())[key]==extras
        case=reference.copy()
        if extras:
            ids=[r['parent']for r in extras]
            case['A']=hstack([reference['A'][:,:reference['ng']],reference['A'][:,ids],reference['A'][:,reference['ng']:]],format='csc')
            av=np.c_[av,np.array(volumes).T];cost=np.c_[cost,np.array(prices).T]
            case['ng']=reference['ng']+len(extras);case['offer_zones']=np.r_[reference['offer_zones'],[r['zone']for r in extras]]
            case['emergency_mask']=np.r_[reference['emergency_mask'],np.zeros(len(extras),bool)]
        case['availability'],case['cost']=av,cost
        for row in extras: np.testing.assert_allclose(av[:,row['parent']]+av[:,row['column']],reference['availability'][:,row['parent']],rtol=0,atol=1e-10)
        compare(immutable_hashes(case,flow),s['outcomes'][key]['physical_inputs'])
        info=s['annuals'][key];path=ROOT/info['witness']if info['reused']else folder/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path)as z:
            x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        ax=(case['A']@x.T).T;lo=np.c_[case['load'],case['island_rhs'],-case['ratings']-flow];hi=np.c_[case['load'],case['island_rhs'],case['ratings']-flow]
        bounds=np.c_[np.zeros((8760,case['ng'])),case['link_min']];upper=np.c_[av,case['link_max']]
        finite=case['ng']+case['nl'];primal=max(float(np.maximum(lo-ax,0).max()),float(np.maximum(ax-hi,0).max()),float(np.maximum(bounds-x[:,:finite],0).max()),float(np.maximum(x[:,:finite]-upper,0).max()));assert primal<=1e-4
        error=float(abs((x[:,:case['ng']]*cost).sum(axis=1)-obj).max());assert error<.05
        reduced=np.c_[cost,np.zeros((8760,case['nl']+case['nz']))]-(case['A'].T@y.T).T
        dual=dual_replay(case,x,y,reduced,obj,flow)
        collapsed=x[:,:reference['ng']].copy()
        for row in extras:collapsed[:,row['parent']]+=x[:,row['column']]
        collapsed=np.c_[collapsed,x[:,case['ng']:]]
        monthly_replay=json.loads(json.dumps(month_quantities(context,collapsed,0),default=lambda a:a.tolist()))
        compare(monthly_replay,s['outcomes'][key]['monthly_quantities'])
        native_values=np.zeros((8760,base['ng']))
        for j,parent in enumerate(parents):native_values[:,parent]+=collapsed[:,j]
        native=base.copy();native['ratings']=reference['ratings'];native['ng']=base['ng']+len(additions)
        native['offer_zones']=np.r_[base['offer_zones'],[r['zone']for r in additions]]
        native['availability']=np.c_[base['availability'],np.tile([r['mw']for r in additions],(8760,1))]
        native_values=np.c_[native_values,collapsed[:,m['ng']:reference['ng']],collapsed[:,reference['ng']:]]
        residual=physics(n,native,native_values,base['load'],off.copy(),0)
        price=price_summary(y[:,:case['nz']],target['prices'],case['zones']);compare(price,s['outcomes'][key]['prices'])
        q=np.zeros((8760,len(s['countries'])))
        for row in records+extras:
            for country,share in row['countries'].items():q[:,s['countries'].index(country)]+=share*x[:,row['column']]
        assert digest(folder/(key+'-oil.npz'))==s['outcomes'][key]['oil_arrays_sha256']
        with np.load(folder/(key+'-oil.npz'))as z:np.testing.assert_allclose(z['generation_mwh'],q,rtol=0,atol=1e-8)
        assert abs(q.sum()/1e6-s['outcomes'][key]['oil_generation_twh'])<1e-9
        for row in s['outcomes'][key]['oil']:
            country=row['country'];a=q[:,s['countries'].index(country)];b=observations[country];known=np.isfinite(b)
            assert row['known_hours']==int(known.sum())
            for field,value in [('observed_twh',b[known].sum()/1e6),('model_known_hours_twh',a[known].sum()/1e6),('model_all_hours_twh',a.sum()/1e6),('annual_bias_twh',(a[known]-b[known]).sum()/1e6),('hourly_mae_mw',abs(a[known]-b[known]).mean()),('hourly_rmse_mw',np.sqrt(np.mean((a[known]-b[known])**2)))]:assert abs(row[field]-value)<1e-8
            r=float(np.corrcoef(a[known],b[known])[0,1])if np.std(a[known])>1e-10 and np.std(b[known])>1e-10 else None
            compare(r,row['hourly_correlation']);assert row['model_active_hours']==int((a[known]>.1).sum())and row['observed_active_hours']==int((b[known]>.1).sum())
            zi=case['zones'].index('DE-LU'if country=='DE'else country)
            for field,p in [('model_oil_at_negative_observed_price_twh',target['prices'][:,zi]),('model_oil_at_negative_model_price_twh',y[:,zi])]:assert abs(row[field]-a[known&(p<0)].sum()/1e6)<1e-9
            for monthly_row in row['monthly']:
                mask=known&(MONTH==monthly_row['month']);assert int(mask.sum())==monthly_row['known_hours']
                assert abs(a[mask].sum()/1e6-monthly_row['model_twh'])<1e-9 and abs(b[mask].sum()/1e6-monthly_row['observed_twh'])<1e-9
        emergency=float(x[:,:case['ng']][:,case['emergency_mask']].sum());assert emergency<=1e-6
        certificates.append(dict(case=key,hours=8760,primal_residual_mw=primal,native_residual_mw=residual,objective_error_eur=error,emergency_mwh=emergency,**dual))
        print('Replayed',key,'oil TWh',q.sum()/1e6,'price MAE',price['equal_zone_mae'],flush=True)
    result=dict(status='passed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,
                fallback_carbon_hours=fallback,maximum_auction_carry_days=maximum_age,seconds=time.perf_counter()-began,
                scope='New source and tranche compiler independently reconstructed; original source anchor reused; no new optimization or empirical certification')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('out',type=Path);args=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(args.folder.resolve(),args.out.resolve())
