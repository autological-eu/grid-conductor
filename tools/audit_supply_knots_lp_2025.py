"""Independent SciPy node reconstruction, LP dual replay and observed scores."""
import json
import resource
import time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.sparse import hstack
from sigmoid_month_pairs_2025 import ROOT,digest,write,split,certify,metric,FAMILIES
from supply_knot_network_2025 import load,generation
from supply_knot_splines_2025 import initial_parameters
from run_supply_knots_lp_2025 import OUT,PLAN,OLD
from spline_europe_2025 import ZERO_TECH


def independent_costs(sealed,data,theta,hours,bins):
    count=len(sealed['groups']);edges=np.linspace(0,1,bins+1);nodes=np.linspace(0,1,6)
    increments=.001+20*np.logaddexp(0,theta[:,5:]);heights=np.c_[np.zeros(count),increments.cumsum(axis=1)]
    curve=PchipInterpolator(nodes,heights.T,axis=0);primitive=curve.antiderivative()
    average=np.diff(primitive(edges)-edges[:,None]*curve(.5),axis=0).T*bins
    zero=np.array([g['technology'] in ZERO_TECH for g in sealed['groups']]);zi=[g['zone_id'] for g in sealed['groups']]
    shift=80*np.tanh(np.einsum('tgf,gf->tg',data['features'][hours][:,zi],theta[:,:5])/4)
    costs=data['source_cost'][hours,:,None]+shift[:,:,None]+average[None,:,:];costs[:,zero,:]=0
    return np.c_[costs.reshape(len(hours),-1),data['emergency_cost'][hours]]


def run():
    began=time.perf_counter();waited=0.;sealed,data,A,emergency,source_capacity=load();design=json.loads(PLAN.read_text());count=len(sealed['groups']);bins=design['lp_tranches_per_curve'];ng=count*bins+emergency.shape[1]
    matrix=hstack([A[:,np.repeat(np.arange(count),bins)],emergency,A[:,count:]],format='csc')
    checked=0;records=[];maxima=dict(primal_mw=0.,duality_gap_eur=0.,complementarity_eur=0.,free_reduced_cost_eur_mwh=0.)
    def ready(path):
        nonlocal waited
        t=time.perf_counter()
        while not path.exists():
            if (OUT/'failure.json').exists():raise RuntimeError('Runner failed; full audit unavailable')
            if time.perf_counter()-began>7200:raise TimeoutError('Audit waiting budget exceeded')
            time.sleep(5)
        waited+=time.perf_counter()-t
        return json.loads(path.read_text())
    provenance=ready(OUT/'provenance.json')
    for name,expected in provenance.items():
        if digest(ROOT/name)!=expected:raise ValueError('Changed provenance: '+name)
    for train,test in design['pairs']:
        row=ready(OUT/f'pair-{train:02d}-{test:02d}.json');path=OUT/f'proposal-{train:02d}.json';proposal=json.loads(path.read_text())
        if digest(path)!=row['proposal_sha256'] or proposal['train']!=train or proposal['test']!=test:raise ValueError('Proposal/fold mismatch')
        train_hours,hours=split(train,test)
        if not set(proposal['training_hours']).issubset(train_hours.tolist()):raise ValueError('Training leakage')
        if abs(min(r['loss'] for r in proposal['history'])-proposal['selected_training_loss'])>1e-12:raise ValueError('Training selection mismatch')
        old=json.loads((OLD/f'proposal-{train:02d}.json').read_text())
        if not set(old['training_hours']).issubset(train_hours.tolist()):raise ValueError('Initializer fold leakage')
        for kind in ['learned','control']:
            witness=OUT/f'test-{test:02d}-{kind}.npz';record=row['cases'][kind]
            if digest(witness)!=record['witness_sha256']:raise ValueError('Changed witness')
            with np.load(witness) as z:w={key:z[key] for key in z.files}
            np.testing.assert_array_equal(w['hours'],hours)
            theta=np.array(proposal['theta']) if kind=='learned' else initial_parameters(count)
            costs=independent_costs(sealed,data,theta,hours,bins)
            av=np.c_[np.repeat(data['capacity'][hours]/bins,bins,axis=1),data['emergency_available'][hours]]
            np.testing.assert_allclose(av[:,:count*bins].reshape(len(hours),count,bins).sum(axis=2),data['capacity'][hours],atol=1e-8,rtol=0)
            checks=certify(matrix,costs,av,data,hours,w['values'],w['row_duals'],w['objectives'],ng,sealed['nl'],sealed['nz'])
            for key in maxima:maxima[key]=max(maxima[key],checks[key])
            if np.maximum(w['values'][:,count*bins:ng],0).sum()>1e-6:raise ValueError('Emergency generation')
            quantities=w['values'][:,:count*bins].reshape(len(hours),count,bins).sum(axis=2)
            np.testing.assert_allclose(quantities,w['quantities'],atol=1e-8,rtol=0)
            gen=generation(sealed,data,source_capacity,quantities,hours)
            np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
            np.testing.assert_allclose(gen.sum(axis=(1,2)),quantities.sum(axis=1)+data['fixed_generation'][hours].sum(axis=(1,2)),atol=1e-5,rtol=0)
            metrics,monthly=metric(sealed,data,w['row_duals'][:,:sealed['nz']],gen,hours,test)
            for key in metrics:
                if abs(metrics[key]-record['metrics'][key])>1e-9:raise ValueError('Observed score mismatch')
            np.testing.assert_allclose(monthly,record['monthly_generation_twh'],atol=1e-12,rtol=0)
            checked+=len(hours)
        records.append(dict(train=train,test=test,hours=len(hours),status='independent_scipy_costs_LP_duals_and_metrics_passed'))
        write(OUT/'audit-progress.json',dict(pairs=records,checked_hours=checked,maxima=maxima));print('AUDIT',train,test,checked,flush=True)
    summary=ready(OUT/'summary.json')
    if summary['status']!='complete' or checked!=8688:raise ValueError('Incomplete evaluation')
    write(OUT/'audit.json',dict(status='all8688_LP_witness_hours_independent_scipy_costs_and_metrics_passed',checked_hours=checked,pairs=records,maxima=maxima,
          summary_sha256=digest(OUT/'summary.json'),seconds=time.perf_counter()-began-waited,waiting_seconds=waited,auditor_sha256=digest(__file__)))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
