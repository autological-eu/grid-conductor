"""Training-only selected-loss replay and smooth-to-LP inference mismatch."""
import json
import resource
import time
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,write,split,digest
from supply_knot_network_2025 import load,clear_hour,clear_lp,generation
from supply_knot_splines_2025 import initial_parameters
from run_supply_knots_lp_2025 import OUT,PLAN,guesses,joint_loss
from run_differentiable_spline_2025 import targets,fixed_month


def run():
    began=time.perf_counter();sealed,data,A,emergency,source_capacity=load();design=json.loads(PLAN.read_text());records=[]
    for train,test in design['pairs']:
        path=OUT/f'proposal-{train:02d}.json'
        while not path.exists():
            if (OUT/'failure.json').exists():raise RuntimeError('Producer failure')
            if time.perf_counter()-began>7200:raise TimeoutError('Proposal waiting budget')
            time.sleep(5)
        proposal=json.loads(path.read_text());theta=np.array(proposal['theta']);hours=np.array(proposal['training_hours']);all_train,_=split(train,test)
        initial=guesses(sealed,train);results=[clear_hour(sealed,data,A,theta,int(h),initial[int(h)]) for h in hours]
        pp=np.array([r['prices'] for r in results]);xx=np.array([r['full_x'] for r in results]);lp,info=clear_lp(sealed,data,A,emergency,theta,hours,design['lp_tranches_per_curve'])
        target=targets(data,hours,train);fixed=fixed_month(sealed,data,all_train)
        loss,*_=joint_loss(sealed,data,source_capacity,design,theta,initial_parameters(len(theta)),pp,xx,hours,len(all_train),target,fixed)
        if abs(loss-proposal['selected_training_loss'])>2e-5:raise ValueError('Selected training loss did not replay')
        # Slice and poison every target outside the declared odd month. The
        # loss/derivative boundary must be identical, not merely similar.
        poisoned=data.copy();poisoned['observed_prices']=data['observed_prices'].copy();outside=np.ones(8760,bool);outside[all_train]=False;poisoned['observed_prices'][outside]=1e12
        poisoned['ember']=data['ember'].copy();poisoned['ember'][:]=1e12;poisoned['ember'][train-1]=data['ember'][train-1]
        original=joint_loss(sealed,data,source_capacity,design,theta,initial_parameters(len(theta)),pp,xx,hours,len(all_train),target,fixed)
        replay=joint_loss(sealed,poisoned,source_capacity,design,theta,initial_parameters(len(theta)),pp,xx,hours,len(all_train),targets(poisoned,hours,train),fixed)
        for first,second in zip(original[:4],replay[:4]):np.testing.assert_array_equal(first,second)
        smooth_q=xx[:,:len(theta)]*1000;sg=generation(sealed,data,source_capacity,smooth_q,hours);lg=generation(sealed,data,source_capacity,lp['quantities'],hours)
        row=dict(train=train,test=test,hours=len(hours),selected_loss=loss,loss_replay_absolute_error=abs(loss-proposal['selected_training_loss']),
                 mean_price_difference_eur_mwh=float(abs(pp-lp['row_duals'][:,:sealed['nz']]).mean()),max_price_difference_eur_mwh=float(abs(pp-lp['row_duals'][:,:sealed['nz']]).max()),
                 mean_country_technology_dispatch_difference_mw=float(abs(sg-lg).mean()),lp_certificate=info['certificate'],proposal_sha256=digest(path),nontraining_target_poisoning='identical_loss_and_derivatives')
        records.append(row);write(OUT/'transfer-progress.json',dict(pairs=records));print('TRANSFER',row,flush=True)
    write(OUT/'transfer.json',dict(status='all_six_training_selections_replayed_and_transfer_measured',pairs=records))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
