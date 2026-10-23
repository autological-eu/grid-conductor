"""Replay every saved daily matrix/dual/profit/storage certificate without solves.

Uses frozen source-book construction, not the new price-check/clearing functions.
The small exhaustive tests separately exercise discrete selection and cut bounds.
"""
import json
import resource
import time
import numpy as np
from scipy.sparse import coo_matrix,vstack
from generation_mix_2025 import ROOT,digest
from europe_linked_clearing_2025 import load,daily_book
from cached_linked_book import CachedBook

OUT=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-robust-v1'


def audit():
    began=time.perf_counter();inputs=json.loads((OUT/'inputs.json').read_text());summary=json.loads((OUT/'annual-summary.json').read_text())
    assert summary['inputs_sha256']==digest(OUT/'inputs.json')
    assert inputs['producer_sha256']==digest(ROOT/'tools/run_robust_priced_europe_2025.py')
    for f,h in inputs['files'].items():assert digest(ROOT/f)==h,f
    loaded=load();d,active,p,s,m,c,families,reference,_=loaded;cache=CachedBook();rows=[]
    expected=np.arange('2025-01-01','2026-01-01',dtype='datetime64[D]').astype(str).tolist()
    for record in summary['cases']:
        if record['status']!='price_checked_incumbent':continue
        day=record['day'];assert record['inputs_sha256']==digest(OUT/'inputs.json')
        if record.get('seed_record'):
            assert digest(ROOT/record['seed_record'])==record['seed_record_sha256']
            seed=json.loads((ROOT/record['seed_record']).read_text());assert seed['witness_sha256']==record['witness_sha256']
        path=ROOT/record['witness'];assert digest(path)==record['witness_sha256']
        book=daily_book(day,loaded);base,orders,reservations,storage,parts,hours,start=book;lp=cache.compile(base,orders,reservations,storage);T=len(hours);n=m['A'].shape[1];nr=m['A'].shape[0]
        lookup={r['id']:j for j,r in enumerate(orders)}
        for iteration in record['history']:
            roots=iteration['rejected_roots']
            if roots:
                cols=[lp['binary_orders'][lookup[name]] for name in roots]
                cuts=coo_matrix((np.ones(len(cols)),(np.arange(len(cols)),cols)),shape=(len(cols),len(lp['c']))).tocsc()
                lp=lp|dict(A=vstack([lp['A'],cuts],format='csc'),row_lower=np.r_[lp['row_lower'],np.full(len(cols),-np.inf)],row_upper=np.r_[lp['row_upper'],np.zeros(len(cols))])
        with np.load(path) as z:x=z['values'];y=z['row_duals'];ratios=z['ratios'];day_x=z['effective_hourly_dispatch'];saved_injections=z['storage_injection'];stored_hours=z['hours']
        np.testing.assert_array_equal(stored_hours,start+hours);np.testing.assert_allclose(x[T*n:T*n+len(orders)],ratios,rtol=0,atol=1e-10)
        assert len(y)==lp['A'].shape[0]
        ax=lp['A']@x;lower=lp['lower'].copy();upper=lp['upper'].copy()
        assert np.maximum(lower-x,0).max(initial=0)<=1e-4 and np.maximum(x-upper,0).max(initial=0)<=1e-4
        lower[lp['integers']]=np.rint(x[lp['integers']]);upper[lp['integers']]=lower[lp['integers']]
        assert abs(x[lp['integers']]-np.rint(x[lp['integers']])).max(initial=0)<1e-6
        small=(lower>upper)&(lower-upper<=1e-7);upper[small]=lower[small]
        primal=float(max(np.maximum(lp['row_lower']-ax,0).max(initial=0),np.maximum(ax-lp['row_upper'],0).max(initial=0),np.maximum(lower-x,0).max(initial=0),np.maximum(x-upper,0).max(initial=0)));assert primal<=1e-4
        rc=lp['c']-lp['A'].T@y;rl=np.isfinite(lp['row_lower']);rh=np.isfinite(lp['row_upper']);cl=np.isfinite(lower);cu=np.isfinite(upper)
        assert max(np.maximum(y[~rl],0).max(initial=0),np.maximum(-y[~rh],0).max(initial=0),np.maximum(rc[~cl],0).max(initial=0),np.maximum(-rc[~cu],0).max(initial=0))<1e-5
        value=float(lp['c']@x);dual=float(np.maximum(y[rl],0)@lp['row_lower'][rl]+np.minimum(y[rh],0)@lp['row_upper'][rh]+np.maximum(rc[cl],0)@lower[cl]+np.minimum(rc[cu],0)@upper[cu])
        gap=abs(value-dual);comp=max(float(abs(np.maximum(y[rl],0)*(ax[rl]-lp['row_lower'][rl])).max(initial=0)),float(abs(np.minimum(y[rh],0)*(ax[rh]-lp['row_upper'][rh])).max(initial=0)),float(abs(np.maximum(rc[cl],0)*(x[cl]-lower[cl])).max(initial=0)),float(abs(np.minimum(rc[cu],0)*(x[cu]-upper[cu])).max(initial=0)))
        assert gap<.05 and comp<.05 and abs(value-record['incumbent_eur'])<.05
        own=np.array([float(ratios[j]*(np.asarray(lp['A'][:T*nr,T*n+j].T@y[:T*nr]).item()-r['price']*np.array(r['profile']).sum())) for j,r in enumerate(orders)])
        minimum_surplus=None
        for j,r in enumerate(orders):
            if ratios[j]<=1e-7:continue
            # This benchmark explicitly uses roots plus leaf children only.
            children=[k for k,v in enumerate(orders) if r['id'] in v.get('parents',[])];assert all(not any(orders[k]['id'] in v.get('parents',[]) for v in orders) for k in children)
            profit=float(own[j]+own[children].sum());assert profit>=-.05
            minimum_surplus=profit if minimum_surplus is None else min(minimum_surplus,profit)
        # Rebuild source gas output and full-day storage chronology independently.
        generators=x[:T*n].reshape(T,n).copy();gas_mask=np.isin(hours,d['gas_window_hours_utc'])
        for part in parts:
            ids=part['columns'];av=m['availability'][start+hours][:,ids];reserved=av*gas_mask[:,None]*min(1.,d['gas_package_max_mw']/av.sum(axis=1).max())
            np.testing.assert_allclose(reserved,part['reserved'],rtol=0,atol=1e-8)
            generators[:,ids]+=reserved*d['minimum_output_fraction']*ratios[part['parent']]
            for j,col,profile in part['children']:generators[:,col]+=profile*ratios[j]
        expected_day=reference['values'][start:start+24].copy();expected_day[hours]=generators
        np.testing.assert_allclose(day_x,expected_day,rtol=0,atol=1e-7)
        injections=np.zeros((24,p['nz']));terminal_max=0.
        for name,asset in storage.items():
            charge=np.zeros(24);discharge=np.zeros(24)
            for j,r in enumerate(orders):
                if r.get('asset')!=name:continue
                profile=np.zeros(24);profile[hours]=np.array(r['profile'])*ratios[j];zone=p['zones'].index(str(s['offer_zones'][r['injection_column']]))
                injections[:,zone]+=profile;charge+=np.maximum(-profile,0);discharge+=np.maximum(profile,0)
            energy=asset['initial_mwh']+np.cumsum(charge*asset['eta_charge']-discharge/asset['eta_discharge']);terminal_max=max(terminal_max,abs(energy[-1]-asset['terminal_mwh']))
            assert energy.min()>=-1e-4 and energy.max()<=asset['energy_mwh']+1e-4 and terminal_max<=1e-4
            assert charge.max()<=asset['charge_mw']+1e-4 and discharge.max()<=asset['discharge_mw']+1e-4 and np.minimum(charge,discharge).max()<=1e-4
        np.testing.assert_allclose(injections[hours],saved_injections,rtol=0,atol=1e-7)
        day_ax=(m['A']@day_x.T).T;day_ax[:,:p['nz']]+=injections;sl=slice(start,start+24)
        lo=np.c_[s['load'][sl],s['island_rhs'][sl],-s['ratings']-s['flow'][sl]];hi=np.c_[s['load'][sl],s['island_rhs'][sl],s['ratings']-s['flow'][sl]]
        original_lower=np.c_[np.zeros((24,p['ng'])),s['link_min'][sl],np.full((24,p['nz']),-np.inf)];original_upper=np.c_[m['availability'][sl],s['link_max'][sl],np.full((24,p['nz']),np.inf)]
        physical=float(max(np.maximum(lo-day_ax,0).max(),np.maximum(day_ax-hi,0).max(),np.maximum(original_lower-day_x,0).max(),np.maximum(day_x-original_upper,0).max()));assert physical<=1e-4
        emergency=float(np.maximum(day_x[:,:p['ng']][:,s['emergency_mask']],0).sum());assert emergency<=1e-6
        bound=record['initial_allocation_lower_bound_eur'];assert value>=bound-.05
        rows.append(dict(day=day,primal_mw=primal,original_matrix_residual_mw=physical,duality_gap_eur=gap,complementarity_eur=comp,minimum_family_surplus_eur=minimum_surplus,storage_terminal_error_mwh=terminal_max,emergency_mwh=emergency,conservative_offer_cost_gap_eur=max(0.,value-bound)))
    complete=summary['status']=='complete' and [r['day'] for r in rows]==expected;assert len(rows)==summary['completed_days']
    deps=['europe_linked_clearing_2025.py','cached_linked_book.py','linked_profile_orders.py','generation_mix_2025.py']
    result=dict(status='all365_certificates_replayed' if complete else 'partial_certificates_replayed_not_annual',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'annual-summary.json'),inputs_sha256=digest(OUT/'inputs.json'),dependencies={f:digest(ROOT/'tools'/f) for f in deps},days=len(rows),hours=len(rows)*24,cases=rows,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(result['status'],'days',len(rows),'seconds',result['seconds'],flush=True)


if __name__=='__main__':resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
