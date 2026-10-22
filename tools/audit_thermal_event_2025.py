"""Independent native-network, thermal-history, objective and KKT replay.

Does not import the experiment compiler, driver or their validation helper.
Checks both forecast/implemented hours and exact cross-day state carry.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.sparse import load_npz,block_diag
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/thermal-event-v1';RUN=OUT/'runs-v7'
def audit():
    start=time.perf_counter();s=json.loads((RUN/'summary.json').read_text());m=json.loads((OUT/'inputs-protocol-v2.json').read_text());design=json.loads((ROOT/'config/thermal-event-2025.json').read_text());assert s['design']==design and s['input_summary_sha256']==digest(OUT/'inputs-protocol-v2.json')
    assert s['producer_sha256']==digest(ROOT/'tools/run_thermal_event_2025.py') and s['helper_sha256']==digest(ROOT/'tools/thermal_event_model_2025.py') and s['design_sha256']==digest(ROOT/'config/thermal-event-2025.json')
    if s['parent_version'] is not None:
        parent_run=OUT/s['parent_version'];assert s['parent_progress_sha256']==digest(parent_run/'progress.json')
        if s['parent_summary_sha256'] is not None:assert s['parent_summary_sha256']==digest(parent_run/'summary.json')
    parent=m['protocol_binding'];assert parent['parent_sha256']==digest(OUT/parent['parent_file']) and parent['producer_sha256']==digest(ROOT/'tools'/parent['producer_file'])
    for path,sha in m['source_hashes'].items():assert digest(ROOT/path)==sha
    for path,sha in m['files'].items():assert digest(OUT/path)==sha
    for path,sha in s['files'].items():assert digest(RUN/path)==sha
    with np.load(OUT/'inputs.npz') as z:source={k:z[k] for k in z.files}
    with np.load(OUT/'resource-components.npz') as z:solar,wind=z['solar'],z['wind']
    resource=json.loads((OUT/'resource-components.json').read_text());assert resource['components_sha256']==digest(OUT/'resource-components.npz') and s['resource_components_sha256']==digest(OUT/'resource-components.json')
    assert resource['producer_sha256']==digest(ROOT/'tools/thermal_event_resources_2025.py')
    for path,sha in resource['source_hashes'].items():assert digest(ROOT/path)==sha
    renewable=(solar+wind).sum(axis=0)>0
    np.testing.assert_allclose((solar+wind)[:,renewable],source['availability'][:,renewable],rtol=1e-10,atol=1e-7)
    A=load_npz(OUT/'network.npz');n=A.shape[1];nr=A.shape[0];G=len(m['groups']);ng=m['ng'];nz=m['nz'];T=48;network=block_diag([A]*48,format='csc');certificates={};overall_native=overall_temporal=overall_gap=overall_comp=0.
    def maximum(a):return float(np.max(np.asarray(a),initial=0))
    def equality(a,b):return maximum(abs(np.asarray(a)-np.asarray(b)))
    for name in design['cases']:
        commitment=name in ['commitment','weather_commitment','firm_stress'];ramp=name in ['ramp','commitment','weather_ramp','weather_commitment','firm_stress'];weather=name.startswith('weather') or name=='firm_stress';firm=.7 if name=='firm_stress' else 1.
        forecast_emergency_max=0.
        matrix=load_npz(RUN/(name+'-matrix.npz'));assert (matrix[:T*nr,:T*n]-network).nnz==0 and matrix[:T*nr,T*n:].nnz==0
        caps=np.array([g['capacity_mw']*firm for g in m['groups']]);minimum=np.array([design['parameters'][g['carrier']]['minimum_output_fraction'] for g in m['groups']]);prior_q=np.clip(np.array([source['initial'][g['columns']].sum()*firm for g in m['groups']]),0,caps);prior_online=np.minimum(caps,prior_q/minimum);starts=np.zeros((16,G));stops=starts.copy();daycert=[];allq=[];allp=[]
        for day,record in enumerate(s['cases'][name]['days']):
            t0=24*day;sl=slice(t0,t0+48);file=RUN/f'{name}-{day:02d}.npz'
            if record.get('reused_checkpoint'):assert record['reused_checkpoint_sha256']==digest(ROOT/record['reused_checkpoint'])
            with np.load(file) as z:values={k:z[k] for k in z.files}
            x=values['values'];y=values['row_duals'];rc=values['col_duals'];obj=float(values['objective']);dispatch=x[:T*n].reshape(T,n);forecast_emergency_max=max(forecast_emergency_max,float(dispatch[:,np.flatnonzero(source['emergency_mask'])].sum(axis=1).max()));cost=np.c_[source['cost'][sl],np.zeros((T,m['nl']+nz))].ravel();av=source['availability'][sl].copy()
            if weather:av=av-.5*solar[sl]-.3*wind[sl]
            if firm<1:
                for group in m['groups']:av[:,group['columns']]*=firm
            col_lo=np.c_[np.zeros((T,ng)),source['link_min'][sl],np.full((T,nz),-np.inf)].ravel();col_hi=np.c_[av,source['link_max'][sl],np.full((T,nz),np.inf)].ravel()
            if commitment:
                expected_cost=np.array([[design['parameters'][g['carrier']][field] for g in m['groups']] for field in ['online_eur_per_mw_hour','startup_eur_per_mw']]);cost=np.r_[cost,np.tile(expected_cost[0],48),np.tile(expected_cost[1],48),np.zeros(48*G)];col_lo=np.r_[col_lo,np.zeros(3*48*G)];col_hi=np.r_[col_hi,np.tile(caps,3*48)]
            np.testing.assert_array_equal(values['cost'],cost);np.testing.assert_allclose(values['col_lower'],col_lo,rtol=0,atol=1e-10);np.testing.assert_allclose(values['col_upper'],col_hi,rtol=0,atol=1e-7)
            for key,expected in [('initial_q',prior_q),('initial_online',prior_online),('initial_starts',starts),('initial_stops',stops)]:np.testing.assert_allclose(values[key],expected,rtol=0,atol=1e-8)
            native=(A@dispatch.T).T;native_lo=np.c_[source['load'][sl],source['island_rhs'][sl],-source['ratings']-source['flow'][sl]];native_hi=np.c_[source['load'][sl],source['island_rhs'][sl],source['ratings']-source['flow'][sl]]
            np.testing.assert_allclose(values['row_lower'][:T*nr],native_lo.ravel(),rtol=0,atol=1e-10);np.testing.assert_allclose(values['row_upper'][:T*nr],native_hi.ravel(),rtol=0,atol=1e-10)
            native_error=max(maximum(native_lo-native),maximum(native-native_hi),maximum(col_lo-x),maximum(x-col_hi));assert native_error<=1e-4
            temporal=0.;groupq=np.column_stack([dispatch[:,g['columns']].sum(axis=1) for g in m['groups']]);previous=np.r_[prior_q[None,:],groupq[:-1]]
            if ramp:
                if not commitment:
                    for j,g in enumerate(m['groups']):temporal=max(temporal,maximum(abs(groupq[:,j]-previous[:,j])-design['parameters'][g['carrier']]['ramp_fraction_per_hour']*caps[j]))
                else:
                    u,su,sd=x[T*n:].reshape(3,T,G);prevu=np.r_[prior_online[None,:],u[:-1]];allstarts=np.r_[starts,su];allstops=np.r_[stops,sd]
                    for j,g in enumerate(m['groups']):
                        p=design['parameters'][g['carrier']];arrival=allstarts[16+np.arange(T)-p['startup_lead_hours'],j];minimum=p['minimum_output_fraction'];rate=p['ramp_fraction_per_hour']
                        temporal=max(temporal,equality(u[:,j]-prevu[:,j],arrival-sd[:,j]),maximum(groupq[:,j]-u[:,j]),maximum(minimum*u[:,j]-groupq[:,j]),maximum(groupq[:,j]-previous[:,j]-rate*prevu[:,j]-minimum*arrival),maximum(previous[:,j]-groupq[:,j]-rate*u[:,j]-minimum*sd[:,j]))
                        for t in range(T):
                            recent_up=allstarts[16+t-p['startup_lead_hours']-np.arange(p['minimum_up_hours']),j].sum();recent_down=allstops[16+t-np.arange(p['minimum_down_hours']),j].sum();temporal=max(temporal,max(0,recent_up-u[t,j]),max(0,recent_down+u[t,j]-caps[j]))
            assert temporal<=1e-4,(name,day,temporal)
            ax=matrix@x;stationarity=maximum(abs(cost-matrix.T@y-rc));primal=max(maximum(values['row_lower']-ax),maximum(ax-values['row_upper']));dual=0.;comp=0.
            for bound,part,v in [(values['row_lower'],np.maximum(y,0),ax),(values['row_upper'],np.minimum(y,0),ax),(col_lo,np.maximum(rc,0),x),(col_hi,np.minimum(rc,0),x)]:
                good=np.isfinite(bound);assert maximum(abs(part[~good]))<1e-6;dual+=float(part[good]@bound[good]);comp=max(comp,maximum(abs(part[good]*(v[good]-bound[good]))))
            gap=abs(obj-dual);objective_error=abs(obj-cost@x);assert primal<=1e-4 and stationarity<1e-5 and gap<.05 and comp<.05 and objective_error<.05,(name,day,primal,stationarity,gap,comp)
            if day==7:
                price=y[16*nr+m['zones'].index('DE-LU')];probe=record['price_probes'];assert len(probe)==2 and probe[0]['delta_mw']==-.1 and probe[1]['delta_mw']==.1;assert probe[0]['slope_eur_mwh']-.001<=price<=probe[1]['slope_eur_mwh']+.001
                for point in probe:assert abs((point['objective_eur']-obj)/point['delta_mw']-point['slope_eur_mwh'])<1e-8
            daycert.append(dict(native_residual_mw=native_error,temporal_residual_mw=temporal,primal_residual_mw=primal,stationarity_eur_mwh=stationarity,duality_gap_eur=gap,complementarity_eur=comp,objective_error_eur=objective_error))
            allq.append(dispatch[:24]);allp.append(y[:T*nr].reshape(T,nr)[:24,:nz]);prior_q=groupq[23]
            if commitment:prior_online=u[23];starts=np.r_[starts,su[:24]][-16:];stops=np.r_[stops,sd[:24]][-16:]
            overall_native=max(overall_native,native_error);overall_temporal=max(overall_temporal,temporal);overall_gap=max(overall_gap,gap);overall_comp=max(overall_comp,comp)
        dispatch=np.concatenate(allq);prices=np.concatenate(allp);assert len(prices)==216
        with np.load(RUN/(name+'-implemented.npz')) as z:np.testing.assert_array_equal(z['dispatch'],dispatch);np.testing.assert_array_equal(z['prices'],prices)
        if name=='control':np.testing.assert_allclose(np.sum(dispatch[:,:ng]*source['cost'][:216],axis=1),source['baseline_objectives'][:216],rtol=0,atol=.05)
        emergency=dispatch[:,np.flatnonzero(source['emergency_mask'])].sum(axis=1);assert abs(emergency.sum()-s['cases'][name]['total_emergency_mwh'])<1e-7 and s['cases'][name]['case_acceptable_supply']==bool(emergency.sum()<1e-6 and forecast_emergency_max<1e-6)
        eligible=np.isfinite(source['observed'][:216]).all(axis=0);mae=float(np.mean(np.abs(prices[48:,eligible]-source['observed'][48:216,eligible])));assert abs(mae-s['cases'][name]['mae_eur_mwh'])<1e-10
        certificates[name]=dict(days=9,implemented_hours=216,evaluated_hours=168,forecast_checks=9*48,certificates=daycert,total_emergency_mwh=float(emergency.sum()),maximum_forecast_emergency_mw=forecast_emergency_max)
        print('Replayed',name,'temporal/native/KKT/price probes',flush=True)
    result=dict(status='all_daily_event_alternatives_independently_replayed',summary_sha256=digest(RUN/'summary.json'),auditor_sha256=digest(__file__),cases=certificates,maximum_native_residual_mw=overall_native,maximum_temporal_residual_mw=overall_temporal,maximum_duality_gap_eur=overall_gap,maximum_complementarity_eur=overall_comp,seconds=time.perf_counter()-start)
    (RUN/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':audit()
