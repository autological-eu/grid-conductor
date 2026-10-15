"""Independent LP certificates, chronological targets and finite-selection replay."""
import argparse
import csv
import json
import logging
import resource
import signal
import time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,EMBER,CARRIER,digest
from compare_native_exchange_reference import CODES
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from audit_nve_hydro_diagnostics_2025 import physics
from price_mechanism_2025 import dual_replay


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text());selection=json.loads((folder/'selection.json').read_text())
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    assert digest(ROOT/'tools/run_bid_calibration_2025.py')==s['producer_sha256']
    for file,key in [('design.json','design_sha256'),('selection.json','selection_sha256'),('training-targets.npz','training_target_sha256'),('evaluation-targets.npz','evaluation_target_sha256')]:assert digest(folder/file)==s[key]
    assert selection['training_target_sha256']==s['training_target_sha256'] and selection['design_sha256']==s['design_sha256']
    design=json.loads((folder/'design.json').read_text());assert design==s['design']
    n,raw_cost,fixed,mapping,original,old,hp=build();m,off=compile_global(n,raw_cost,fixed,'bidding_zone');offsets=branch_offsets(n,off)
    from bid_calibration_2025 import immutable_hashes
    assert immutable_hashes(m,offsets)==s['immutable_inputs']
    groups={};labels=[];countries=s['countries'];fuels=['Wind','Solar','Nuclear','Gas','Coal'];fmap={f:fuel for fuel in fuels for f in EMBER[fuel]}
    for j,(_,g) in enumerate(n.generators.iterrows()):
        groups.setdefault((m['buszone'][g.bus],raw_cost[:,j].tobytes(),g.carrier=='emergency'),[]).append(j)
        labels.append((n.buses.loc[g.bus,'country'],CARRIER[g.carrier]))
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    meta=[];classes=[]
    for k,ids in enumerate(groups.values()):
        kinds={('gas' if n.generators.iloc[i].carrier in ['CCGT','OCGT'] else 'coal' if n.generators.iloc[i].carrier in ['coal','lignite'] else 'nuclear' if n.generators.iloc[i].carrier=='nuclear' else None) for i in ids}
        assert len(kinds)==1;classes.append(next(iter(kinds)))
        total=av[:,ids].sum(axis=1);sub=[];ct=[]
        for c in {labels[i][0] for i in ids}:
            j=countries.index(c);cs=[i for i in ids if labels[i][0]==c and labels[i][1]!='emergency']
            ct.append((j,av[:,cs].sum(axis=1)))
            for fuel in fuels:
                fs=[i for i in cs if fmap.get(labels[i][1])==fuel]
                if fs:sub.append((j,fuels.index(fuel),av[:,fs].sum(axis=1)))
        meta.append((total,sub,ct))
    assert classes==s['classes']
    demand=np.zeros((8760,len(countries)));water=np.zeros_like(demand);loads=n.get_switchable_as_dense('Load','p_set')
    for j,c in enumerate(countries):
        bs=n.buses.index[n.buses.country==c];demand[:,j]=loads[n.loads.index[n.loads.bus.isin(bs)]].sum(axis=1);water[:,j]=fixed[bs].sum(axis=1)
    # Reference arrays rebuilt independently. Future reference arrays never participate in selection below.
    price=np.full((8760,m['nz']),np.nan);root=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    for z in json.loads((root/'manifest.json').read_text())['zones']:
        area='IE-SEM' if z=='IE' else z
        if area in m['zones']:price[:,m['zones'].index(area)]=np.array(json.loads((root/(z+'.json')).read_text()),float)
    bank={}
    with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:
        for row in csv.DictReader(f):
            if row['Date'].startswith('2025-') and row['Area type'] in ['Country','Country or economy'] and row['Generation (TWh)'].strip():
                bank[(row['ISO 3 code'],row['Electricity source'],int(row['Date'][5:7]))]=float(row['Generation (TWh)'])
    targets={}
    for name,months,start,stop in [('training',range(1,7),0,4344),('evaluation',range(7,13),4344,8760)]:
        with np.load(folder/(name+'-targets.npz')) as z:target={k:z[k] for k in z.files}
        np.testing.assert_array_equal(target['prices'],price[start:stop]);np.testing.assert_array_equal(target['months'],list(months))
        for t,month in enumerate(months):
            for j,c in enumerate(countries):
                for k,fuel in enumerate(fuels):
                    ref=bank.get((CODES.get(c),fuel,month));actual=target['generation'][t,j,k]
                    assert (ref is None and np.isnan(actual)) or actual==ref
                ref=bank.get((CODES.get(c),'Net imports',month));actual=target['trade'][t,j]
                assert (ref is None and np.isnan(actual)) or actual==-ref
        targets[name]=target
    def quantities(x,start):
        T=len(x);gl=np.zeros((13,len(countries),len(fuels)));gu=np.zeros_like(gl)
        cl=np.zeros((13,len(countries)));cu=np.zeros_like(cl);cp=np.zeros_like(cl);dm=np.zeros_like(cl)
        months=MONTH[start:start+T]
        def add(v):return np.bincount(months,weights=v,minlength=13)/1e6
        for k,(total,sub,ct) in enumerate(meta):
            a=total[start:start+T];q=np.clip(x[:,k],0,a)
            for j,f,cap in sub:
                cap=cap[start:start+T];gl[:,j,f]+=add(np.maximum(q-a+cap,0));gu[:,j,f]+=add(np.minimum(q,cap))
            for j,cap in ct:
                cap=cap[start:start+T];cl[:,j]+=add(np.maximum(q-a+cap,0));cu[:,j]+=add(np.minimum(q,cap));cp[:,j]+=add(np.divide(q*cap,a,out=np.zeros(T),where=a>0))
        for j in range(len(countries)):
            hydro=add(water[start:start+T,j]);d=add(demand[start:start+T,j]);cl[:,j]+=hydro-d;cu[:,j]+=hydro-d;dm[:,j]=d;cp[:,j]+=hydro
        return dict(lo=gl,hi=gu,trade_lo=cl,trade_hi=cu,demand=dm,total_point=cp)
    def raw_loss(p,q,target):
        errors=[]
        for j in range(m['nz']):
            known=np.isfinite(target['prices'][:,j])
            if known.any():errors.append(abs(p[known,j]-target['prices'][known,j]).mean())
        months=target['months'];ref=target['generation'];known=np.isfinite(ref)
        dist=np.maximum(np.maximum(q['lo'][months]-ref,ref-q['hi'][months]),0)/np.maximum(ref,.25)
        trade=target['trade'];tk=np.isfinite(trade);td=np.maximum(np.maximum(q['trade_lo'][months]-trade,trade-q['trade_hi'][months]),0)/np.maximum(q['demand'][months],1.)
        return dict(price=float(np.mean(errors)),generation=float(dist[known].mean()),trade=float(td[tk].mean()),price_areas=len(errors),generation_targets=int(known.sum()),trade_targets=int(tk.sum()))
    def compare_raw(a,b):
        for key in a:assert abs(a[key]-b[key])<1e-8,(key,a[key],b[key])
    certificates=[];raws={};eval_results={}
    def verify(path,params,T,stored):
        assert digest(path)==stored['witness_sha256']
        with np.load(path) as packed:x=packed['values'];y=packed['row_duals'];obj=packed['objectives'];valid=packed['optimal']
        assert len(x)==T and int(valid.sum())==stored['optimal_hours']
        assert np.flatnonzero(~valid).tolist()==[r['hour'] for r in stored['failures']]
        if not valid.all():
            assert np.isnan(x[~valid]).all();return None
        adjusted=m['cost']+np.array([0. if c is None else params[['gas','coal','nuclear'].index(c)] for c in classes])
        case=m|{k:m[k][:T] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=adjusted[:T]
        primal=physics(n,case,x,case['load'],off.iloc[:T].reset_index(drop=True).copy(),0)
        actual=(x[:,:m['ng']]*adjusted[:T]).sum(axis=1);objective_error=float(abs(actual-obj).max());assert objective_error<.05
        costs=np.c_[adjusted[:T],np.zeros((T,m['nl']+m['nz']))];reduced=costs-(m['A'].T@y.T).T
        certificate=dual_replay(case,x,y,reduced,obj,offsets[:T])
        certificates.append(dict(file=path.name,hours=T,maximum_primal_mw=primal,maximum_objective_error_eur=objective_error,**certificate))
        trainq=quantities(x[:4344],0);raw=raw_loss(y[:4344,:m['nz']],trainq,targets['training'])
        evaluation=None
        if T==8760:
            testq=quantities(x[4344:],4344);evaluation=raw_loss(y[4344:,:m['nz']],testq,targets['evaluation'])
            eval_results[path.name]=(y.copy(),trainq,testq)
        return raw,evaluation
    control=verify(folder/'control.npz',[0.,0.,0.],8760,s['control']);assert control is not None
    baseline=control[0]
    for r in selection['training_records']:
        params=r['params'];assert all(p in levels for p,levels in zip(params,[[-30,0,30],[-30,0,30],[-15,0,15]]))
        if r.get('control'):raw=baseline
        else:
            result=verify(folder/f"train-{r['index']:02d}.npz",params,4344,r)
            if result is None:assert r['score'] is None;continue
            raw=result[0]
        compare_raw(raw,r['raw']);reg=.05*np.mean((np.array(params)/[30,30,15])**2)
        value=float(np.mean([raw[k]/max(baseline[k],1e-9) for k in ['price','generation','trade']])+reg)
        assert abs(value-r['score'])<1e-8;raws[r['index']]=value
        print('Replayed training trial',r['index'],'score',round(value,6),flush=True)
    def best(indices):
        good=[selection['training_records'][i] for i in indices if i in raws];value=min(raws[r['index']] for r in good)
        return min([r for r in good if raws[r['index']]<=value+1e-12],key=lambda r:(sum((p/b)**2 for p,b in zip(r['params'],[30,30,15])),tuple(r['params'])))
    current=[0.,0.,0.];assert len(selection['steps'])==6
    visited=set([0])
    for t,step in enumerate(selection['steps']):
        axis=t%3;assert step['sweep']==t//3+1 and step['axis']==['gas','coal','nuclear'][axis]
        for index,value in zip(step['candidates'],[[-30.,0.,30.],[-30.,0.,30.],[-15.,0.,15.]][axis]):
            p=current.copy();p[axis]=value;assert selection['training_records'][index]['params']==p;visited.add(index)
        winner=best(step['candidates']);assert step['selected_index']==winner['index'];current=winner['params']
    assert visited==set(r['index'] for r in selection['training_records'])
    winner=best(sorted(visited));assert winner['index']==selection['selected_index'] and winner['params']==selection['params']
    if s['annual'].get('uses_control_witness'):selected=control;eval_results['selected.npz']=eval_results['control.npz']
    else:selected=verify(folder/'selected.npz',winner['params'],8760,s['annual'])
    assert selected is not None
    def check_outcomes(saved_outcomes,result,filename):
        compare_raw(result[0],saved_outcomes['training']['objective_components']);compare_raw(result[1],saved_outcomes['evaluation']['objective_components'])
        y,trainq,testq=eval_results[filename]
        for period,start,stop,q in [('training',0,4344,trainq),('evaluation',4344,8760,testq)]:
            saved=saved_outcomes[period];target=targets[period];maes=[];correlations=[]
            for j,row in enumerate(saved['zones']):
                assert row['zone']==m['zones'][j];known=np.isfinite(target['prices'][:,j]);assert row['known_hours']==int(known.sum())
                if not known.any():continue
                p=y[start:stop,:m['nz']][known,j];o=target['prices'][known,j];error=p-o
                for key,v in [('mae_eur_mwh',abs(error).mean()),('bias_eur_mwh',error.mean()),('rmse_eur_mwh',np.sqrt((error**2).mean()))]:assert abs(row[key]-v)<1e-8
                corr=float(np.corrcoef(p,o)[0,1]) if p.std()>1e-12 and o.std()>1e-12 else None;assert row['correlation']==corr
                maes.append(float(abs(error).mean()))
                if corr is not None:correlations.append(corr)
            assert abs(saved['equal_zone_mae']-np.mean(maes))<1e-8 and abs(saved['mean_zonal_correlation']-np.mean(correlations))<1e-8
            for row in saved['generation']:
                j=countries.index(row['country']);k=fuels.index(row['fuel']);month=row['month'];t=target['months'].tolist().index(month);ref=target['generation'][t,j,k]
                assert (row['reference_twh'] is None and np.isnan(ref)) or row['reference_twh']==ref
                assert abs(row['lower_twh']-q['lo'][month,j,k])<1e-8 and abs(row['upper_twh']-q['hi'][month,j,k])<1e-8
    for name,result,filename in [('control',control,'control.npz'),('calibrated',selected,'selected.npz')]:
        check_outcomes(s['outcomes'][name],result,filename)
    diagnostic=folder/'diagnostic-evaluation-v1';ds=json.loads((diagnostic/'summary.json').read_text());dd=json.loads((diagnostic/'design.json').read_text())
    assert ds['primary_summary_sha256']==digest(folder/'summary.json') and ds['choices_sha256']==digest(diagnostic/'design.json')
    assert ds['producer_sha256']==digest(ROOT/'tools/evaluate_bid_calibration_probes_2025.py')
    for name,sha in ds['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    nonzero=[r for r in selection['training_records'] if r['score'] is not None and any(r['params'])]
    expected=[min(nonzero,key=lambda r:(r['score'],tuple(r['params']))),min(nonzero,key=lambda r:(r['raw']['price'],sum(v*v for v in r['params']),tuple(r['params'])))]
    assert len(ds['probes'])==len(dd['choices'])==2
    for chosen,probe,expected_record in zip(dd['choices'],ds['probes'],expected):
        assert chosen['training_record_index']==expected_record['index'] and chosen['params']==expected_record['params']==probe['params']
        assert chosen['label']==probe['label']
        checked=verify(diagnostic/probe['witness'],probe['params'],8760,probe)
        if checked is None:assert probe['outcomes'] is None
        else:
            check_outcomes(probe['outcomes'],checked,probe['witness'])
            compare_raw(checked[0],expected_record['raw'])
    assert immutable_hashes(m,offsets)==s['immutable_inputs']
    result=dict(status='bid_cost_physics_duality_training_selection_and_temporal_metrics_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
        selected_params=winner['params'],training_trials=len(selection['training_records']),complete_lp_certificates=len(certificates),
        failed_training_trials=sum(r['score'] is None for r in selection['training_records']),certificates=certificates,
        diagnostic_summary_sha256=digest(diagnostic/'summary.json'),diagnostic_training_selectors_replayed=True,
        elapsed_seconds=time.perf_counter()-began,scope='Retrospective temporal calibration; no global search optimum, empirical acceptance or uniquely identified real bids')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Independent calibration replay passed',winner['params'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    output=a.out or a.folder/'verification-v1';output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);audit(a.folder,output)
