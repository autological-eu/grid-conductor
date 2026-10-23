"""Fresh chronological storage-bid candidates on the accepted resource_full LP."""
import argparse
import fcntl
import json
import logging
import resource
import time
import numpy as np
import pandas as pd
import pypsa
import highspy
from shapely.geometry import Point
from generation_mix_2025 import ROOT,digest
from europe_linked_clearing_2025 import load
from bidding_zone_network_2025 import boundaries,locate
from synthetic_bids_2025 import SOURCE
from hourly_storage_bids import validate_assets,future_reference,coefficients,advance,matrix,certificate

PLAN=ROOT/'config/hourly-storage-bids-2025.json'
OUT=ROOT/'data/bidding-zone-network-2025/hourly-storage-bids-v1'
NATIVE=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
PLANTS=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/powerplants_s_128.csv'


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def fleet():
    source=pypsa.Network(SOURCE);native=pypsa.Network(NATIVE);shapes,countries,sources=boundaries();frame=pd.read_csv(PLANTS)
    frame=frame[(frame.Fueltype=='Hydro')&(frame.Technology=='Pumped Storage')&(frame.DateIn.isna()|(frame.DateIn<=2025))&(frame.DateOut.isna()|(frame.DateOut>2025))]
    table=source.storage_units.query("carrier=='PHS' and p_nom>0");inflow=source.get_switchable_as_dense('StorageUnit','inflow')[table.index].values;assert not np.any(inflow),'PHS natural inflow needs a different model'
    assets=[];records=[]
    for name,r in table.iterrows():
        candidates=native.buses.loc[[b for b in native.buses.index if str(b).split('::')[0]==r.bus]]
        zones=sorted(set(candidates.bidding_zone.replace({'ES-IB-MA':'ES'})));assert zones,(name,'No retained parent mapping')
        weights={};matched=[]
        if len(zones)==1:weights={zones[0]:1.};method='single modeled parent zone'
        else:
            local=frame[frame.bus.astype(str)==str(r.bus)]
            for i,plant in local.iterrows():
                if not np.isfinite(plant.lon+plant.lat) or not np.isfinite(plant.Capacity) or plant.Capacity<=0:continue
                try:z,_,_=locate(Point(plant.lon,plant.lat),str(plant.Country),shapes,countries)
                except ValueError:continue
                z='ES' if z=='ES-IB-MA' else z
                if z in zones:weights[z]=weights.get(z,0.)+float(plant.Capacity);matched.append(int(i))
            if weights:
                total=sum(weights.values());weights={z:w/total for z,w in weights.items()};method='located dated source pumped-storage plant MW'
            else:
                counts=candidates.bidding_zone.replace({'ES-IB-MA':'ES'}).value_counts();weights={z:float(counts[z]/counts.sum()) for z in counts.index};method='modeled refined-bus count proxy; unresolved plant allocation'
        assert -r.p_min_pu>0 and r.p_max_pu>0
        for z,w in weights.items():
            assets.append(dict(id=str(name)+'::'+z,source_id=str(name),zone=z,technology='PHS',charge_mw=float(-r.p_nom*r.p_min_pu*w),discharge_mw=float(r.p_nom*r.p_max_pu*w),energy_mwh=float(r.p_nom*r.max_hours*w),eta_charge=float(r.efficiency_store),eta_discharge=float(r.efficiency_dispatch),standing_loss=float(r.standing_loss),source_share=float(w),mapping_method=method))
        records.append(dict(source_id=str(name),source_bus=str(r.bus),source_country=str(source.buses.loc[r.bus,'country']),power_mw=float(r.p_nom),energy_mwh=float(r.p_nom*r.max_hours),max_hours=float(r.max_hours),shares=weights,method=method,matched_plant_rows=matched))
    assert abs(sum(r['discharge_mw'] for r in assets)-table.p_nom.sum())<1e-6
    assert abs(sum(r['energy_mwh'] for r in assets)-(table.p_nom*table.max_hours).sum())<1e-5
    return assets,records,sources


def solver(A,c,lo,hi,rl,ru):
    h=highspy.Highs()
    for k,v in [('output_flag',False),('threads',1),('solver','simplex'),('primal_feasibility_tolerance',1e-8),('dual_feasibility_tolerance',1e-9)]:h.setOptionValue(k,v)
    lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0];lp.col_cost_=c;lp.col_lower_=lo;lp.col_upper_=hi;lp.row_lower_=rl;lp.row_upper_=ru;lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    if h.passModel(lp)==highspy.HighsStatus.kError:raise RuntimeError('Storage matrix load failed')
    return h


def hour(h,A,c,lo,hi,rl,ru,limit):
    cols=np.arange(len(c),dtype=np.int32);rows=np.arange(len(rl),dtype=np.int32)
    h.changeColsCost(len(c),cols,c);h.changeColsBounds(len(c),cols,lo,hi);h.changeRowsBounds(len(rl),rows,rl,ru)
    for attempt in range(3):
        if attempt==1:h.clearSolver()
        if attempt==2:
            h=solver(A,c,lo,hi,rl,ru);h.setOptionValue('solver','ipm');h.setOptionValue('run_crossover','off');h.setOptionValue('ipm_optimality_tolerance',1e-12)
        h.setOptionValue('time_limit',h.getRunTime()+limit);h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:continue
        sol=h.getSolution();x=np.array(sol.col_value);y=np.array(sol.row_dual)
        try:cert=certificate(A,c,lo,hi,rl,ru,x,y)
        except ValueError:
            if attempt==2:raise
            continue
        return h,x,y,cert
    raise RuntimeError('Unresolved hourly storage solve '+h.modelStatusToString(h.getModelStatus()))


def run():
    started=time.perf_counter();OUT.mkdir(exist_ok=False);design=json.loads(PLAN.read_text());_,active,p,s,m,c,_,reference,_=load();assets,inventory,source_paths=fleet();validate_assets(assets,p['zones'])
    own=reference['row_duals'][:,:p['nz']];forecast=future_reference(own,design['forecast_hours']);prepared=time.perf_counter()-started
    paths=[PLAN,SOURCE,NATIVE,PLANTS,ROOT/'config/active-research-baseline.json',*[ROOT/f for f in active['artifacts']]]
    deps=['hourly_storage_bids.py','run_hourly_storage_2025.py','test_hourly_storage_bids.py','europe_linked_clearing_2025.py','solar_anchor_bids_2025.py','bidding_zone_network_2025.py']
    sealed=dict(producer_sha256=digest(__file__),design=design,sources=source_paths|{str(f.relative_to(ROOT)):digest(f) for f in paths},dependencies={f:digest(ROOT/'tools'/f) for f in deps},assets=assets,source_inventory=inventory,zones=p['zones'],preparation_seconds=prepared,forecast_source='cached accepted own-model prices; not observed SDAC prices',forecast_sha256=__import__('hashlib').sha256(forecast.tobytes()).hexdigest())
    write(OUT/'inputs.json',sealed);np.savez_compressed(OUT/'forecast.npz',reference=forecast)
    n=m['A'].shape[1];nr=m['A'].shape[0];results={}
    for case in design['cases']:
        aa=assets+(design['battery_demo'] if case=='phs_plus_battery_demo' else []);validate_assets(aa,p['zones']);S=len(aa);A=matrix(m['A'],aa,p['zones']);energy=np.array([r['energy_mwh']*design['initial_energy_fraction'] for r in aa]);initial=energy.copy()
        xall=np.empty((8760,n+2*S));yall=np.empty((8760,nr));soc=np.empty((8760,S));objectives=np.empty(8760);corrections=np.zeros(8760);days=[];h=None;began=time.perf_counter();maximum={k:0. for k in ['primal_mw','signs_eur_mwh','duality_gap_eur','complementarity_eur']};last=began
        for t in range(8760):
            if time.perf_counter()-began>design['limits']['job_seconds']:raise RuntimeError('Storage annual budget exhausted; not a complete run')
            b=coefficients(aa,p['zones'],energy,forecast[t],design['bid_margin_eur_mwh']);cost=np.r_[c[t],np.zeros(p['nl']+p['nz']),-b['buy'],b['sell']]
            lo=np.r_[np.zeros(p['ng']),s['link_min'][t],np.full(p['nz'],-np.inf),np.zeros(2*S)];hi=np.r_[m['availability'][t],s['link_max'][t],np.full(p['nz'],np.inf),b['charge_max'],b['discharge_max']]
            rl=np.r_[s['load'][t],s['island_rhs'][t],-s['ratings']-s['flow'][t]];ru=np.r_[s['load'][t],s['island_rhs'][t],s['ratings']-s['flow'][t]]
            if h is None:h=solver(A,cost,lo,hi,rl,ru)
            h,x,y,cert=hour(h,A,cost,lo,hi,rl,ru,design['limits']['hour_seconds']);energy,correction=advance(b,x[n:n+S],x[n+S:]);corrections[t]=correction
            if np.maximum(x[:p['ng']][s['emergency_mask']],0).sum()>1e-6:raise ValueError('Emergency dispatch: candidate not accepted')
            xall[t]=x;yall[t]=y;soc[t]=energy;objectives[t]=float(cost@x)
            for k,v in cert.items():maximum[k]=max(maximum[k],v)
            if t%24==23:
                days.append(dict(day=t//24+1,seconds=time.perf_counter()-last,maximum_storage_mwh=float(energy.max(initial=0))))
                write(OUT/'progress.json',dict(case=case,checked_hours=t+1,expected_hours=8760,days=len(days),seconds=time.perf_counter()-began,maximum_certificate=maximum));last=time.perf_counter()
                if len(days)%60==0:print(case,'day',len(days),'seconds',round(time.perf_counter()-began,2),flush=True)
        path=OUT/(case+'.npz');np.savez_compressed(path,values=xall,row_duals=yall,energy_mwh=soc,initial_energy_mwh=initial,objectives=objectives,state_clip_mwh=corrections,hours=np.arange(8760))
        target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];known=np.isfinite(target).all(axis=0)
        results[case]=dict(witness=str(path.relative_to(ROOT)),witness_sha256=digest(path),assets=aa,hours=8760,days=365,maximum_certificate=maximum,clearing_seconds=sum(r['seconds'] for r in days),case_wall_seconds=time.perf_counter()-began,daily_times=days,price_mae=float(abs(yall[:,:p['nz']][:,known]-target[:,known]).mean()),charge_twh=float(np.maximum(xall[:,n:n+S],0).sum()/1e6),discharge_twh=float(np.maximum(xall[:,n+S:],0).sum()/1e6),initial_twh=float(initial.sum()/1e6),final_twh=float(energy.sum()/1e6),maximum_state_clip_mwh=float(corrections.max()),zero_emergency=True)
        write(OUT/'partial-summary.json',dict(inputs_sha256=digest(OUT/'inputs.json'),cases=results));print(case,'complete',results[case]['price_mae'],'seconds',results[case]['case_wall_seconds'],flush=True)
    write(OUT/'summary.json',dict(status='two_complete_chronological_storage_candidates_not_adopted',producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),forecast_sha256=digest(OUT/'forecast.npz'),cases=results,total_wall_seconds=time.perf_counter()-started))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));lock=(OUT.parent/'hourly-storage-bids-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
