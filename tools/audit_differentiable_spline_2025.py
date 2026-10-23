"""Independently replay saved primal/dual witnesses without another solve."""
import json
import resource
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,digest,write,split
from differentiable_spline_clearing import initial_parameters
from spline_europe_2025 import load,problem
from run_differentiable_spline_2025 import OUT,PLAN


def run():
    for name,expected in json.loads((OUT/'provenance.json').read_text()).items():
        if digest(ROOT/name)!=expected:raise ValueError('Changed experiment dependency: '+name)
    sealed,data,A=load();design=json.loads(PLAN.read_text());records=[];total=0
    maxima=dict(primal_mw=0.,stationarity_eur_mwh=0.,complementarity_eur=0.)
    for train,test in design['pairs']:
        proposal=OUT/f'proposal-{train:02d}.json'
        if not proposal.exists():continue
        record=json.loads(proposal.read_text());thours,hours=split(train,test)
        if not set(record['training_hours']).issubset(thours.tolist()):raise ValueError('Training fold leakage')
        for kind in ['learned','control']:
            theta=np.array(record['theta']) if kind=='learned' else initial_parameters(len(record['theta']))
            folder=OUT/f'test-{test:02d}-{kind}';seen=[]
            for path in sorted(folder.glob('*.npz')):
                with np.load(path) as z:
                    for k,hour in enumerate(z['hours']):
                        hour=int(hour);seen.append(hour);p=problem(sealed,data,A,theta,hour)
                        full=z['values'][k];x=full[p['active']];nu=z['nu'][k,p['equality_rows']]
                        length=int(z['lengths'][k]);lam=z['lam'][k,:length];slack=z['slack'][k,:length]
                        if len(lam)!=p['G'].shape[0] or min(lam.min(),slack.min())<=0:raise ValueError('Invalid saved dual')
                        if len(p['fixed']):np.testing.assert_allclose(full[p['fixed']],p['fixed_values'],atol=1e-12,rtol=0)
                        _,grad,_=p['cost'].evaluate(x)
                        residual=max(abs(p['equality']@x-p['full_b']).max(initial=0),np.maximum(p['G']@x-p['h'],0).max(initial=0),abs(p['G']@x+slack-p['h']).max(initial=0))*1000
                        stationarity=float(abs(grad+p['E'].T@nu+p['G'].T@lam).max(initial=0));gap=float(slack@lam)*1000
                        np.testing.assert_allclose(z['prices'][k],-z['nu'][k,:sealed['nz']],atol=1e-10,rtol=0)
                        if residual>1e-4 or stationarity>2e-7 or gap>.05:raise ValueError('Saved nonlinear KKT gate failed')
                        for name,value in zip(maxima,[residual,stationarity,gap]):maxima[name]=max(maxima[name],value)
                        total+=1
            if seen!=hours[:len(seen)].tolist():raise ValueError('Missing/duplicate/out-of-fold evaluation hour')
            records.append(dict(train=train,test=test,kind=kind,hours=len(seen),expected=len(hours)))
    complete=len(records)==12 and all(r['hours']==r['expected'] for r in records)
    write(OUT/'audit.json',dict(status='all_8688_even_month_control_and_learned_hours_passed' if complete else 'partial_saved_witnesses_passed',
          independently_replayed_hours=total,complete=complete,records=records,maxima=maxima))
    print(total,'saved nonlinear KKT witnesses replayed; complete=',complete)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
