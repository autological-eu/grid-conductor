"""Sequential matched 24-hour conditional curve learning-rate trials."""
import os,json,time,traceback,fcntl
import numpy as np
import pandas as pd
from pathlib import Path
import run_independent_hourly_transport_2025 as parent
from conditional_monotone_market_2025 import ConditionalMarket,K,GRID,basis
from intraday_offer_bids_2025 import TIMEZONES
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from run_supply_knots_lp_2025 import joint_loss
ROOT_OUT=ROOT/'data/bidding-zone-network-2025/hour-table-learning-rates-v1'
OUT=ROOT_OUT/'lr-0.05'
RATE=.05
from hour_table_conditioner_2025 import feature_rows,initialize,regularizer

def features(s,d,h,reference):
    utc=pd.Timestamp('2025-01-01',tz='UTC')+pd.to_timedelta(h,unit='h');out=np.ones((len(h),len(s['groups']),7))
    for g,row in enumerate(s['groups']):
        local=utc.tz_convert(TIMEZONES[row['zone'][:2]]);a=np.array(local.hour)*2*np.pi/24
        out[:,g,1:]=np.stack([np.sin(a),np.cos(a),np.sin(2*a),np.cos(2*a),np.asarray(local.dayofweek>=5,dtype=float),d['capacity'][h,g]/1000/reference[g]],axis=-1)
    return out

def audit(m,theta,r):
    # Independent quantity/balance reconstruction using polynomial bid evaluation
    offers=m.offers(theta,r['hours']);p=r['prices'][:,m.zone];q=r['quantities_gw'];u=q/m.reference
    b=offers['anchors'][...,0]+(offers['slopes']*basis(u)).sum(axis=-1)
    b0=offers['anchors'][...,0];a=m.capacity[r['hours']]/m.reference
    ba=b0+(offers['slopes']*basis(a)).sum(axis=-1)
    from batched_transport_dispatch_2025 import softclip
    target=b0+softclip(p-b0,ba-b0,m.thermal_tau)
    err=float(abs(b[:,~m.zero]-target[:,~m.zero]).max())
    bal=q@m.Z+r['flows_gw']@m.M-m.load[r['hours']]
    if err>1e-6 or abs(bal).max()*1000>1e-4 or (abs(bal*r['prices']).sum(axis=1)*1000).max()>=.05:raise ValueError('Independent spline/balance replay failed')
    return dict(inverse_price_error=err,balance_mw=float(abs(bal).max()*1000))

def trial():
    OUT.mkdir(exist_ok=True);lock=(OUT/'lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'history.json').exists() or (OUT/'failure.json').exists():raise ValueError('Inspect prior run; no automatic restart')
    base,(state,m,network,_)=parent.setup();s,d,A,_,capacity=state
    m.__class__=ConditionalMarket
    # Explicit retrospective annual available-capacity envelope, NOT nameplate.
    m.reference=np.maximum(m.capacity.max(axis=0),.001)
    h=month_hours(1);f=month_hours(2);X,centers=feature_rows(s['groups'],d,h,m.reference);XF,_=feature_rows(s['groups'],d,f,m.reference,centers)
    w=initialize(m.ng)
    initial=w.copy();active=(d['capacity'][h]>0).any(axis=0)&~m.zero
    target=targets(d,h,1);target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,h);design=dict(price_smooth_absolute_epsilon=1,price_scale_eur_mwh=40,generation_floor_twh=.25,generation_smooth_absolute_epsilon=.01,ridge=0)
    provenance=parent.provenance(base)
    for path in [Path(__file__),ROOT/'tools/conditional_monotone_market_2025.py',ROOT/'tools/hour_table_conditioner_2025.py',ROOT/'tools/test_hour_table_conditioner_2025.py']:
        provenance[str(path.relative_to(ROOT))]=digest(path)
    atomic_json(OUT/'provenance.json',provenance);atomic_json(OUT/'network.json',network)
    base.save(OUT/'reference.npz',capacity_reference_gw=m.reference,training_condition_centers=centers)
    atomic_json(OUT/'design.json',dict(rate=RATE,updates=100,local_hour_tables=24,conditions=['January-centered weekend','January-centered available/reference fraction'],reference='annual peak available MW proxy, not nameplate',ridge=.001,cyclic_hour_penalty=.001,init='same neutral60-slope/-30-markup in all rates',network='same fast95-corridor; no original PTDF claim',selection='compare all rates/iterations; no automatic1000 extension; February is development validation'))
    # Validate implicit gradient and condition chain rule on real European hours.
    hh=np.array([15,111,318,567,759,815,900]);xp,_=feature_rows(s['groups'],d,hh,m.reference,centers)
    th=np.einsum('tgf,gfk->tgk',xp,w);r=m.solve(th,hh,tolerance=1e-11)
    rng=np.random.default_rng(73);gq=rng.normal(size=r['quantities_gw'].shape);gp=rng.normal(size=r['prices'].shape);gp[:,~np.isfinite(d['observed_prices']).all(axis=0)]=0
    grad,info=m.backward(th,r,gq,gp);direction=rng.normal(size=w.shape)*active[:,None,None];dt=np.einsum('tgf,gfk->tgk',xp,direction)
    exact=float((grad*dt).sum());vv=[]
    for sign in [1,-1]:
        rr=m.solve(th+sign*1e-6*dt,hh,p0=r['prices'],tolerance=1e-11);vv.append(float((rr['quantities_gw']*gq).sum()+(rr['prices']*gp).sum()))
    finite=(vv[0]-vv[1])/2e-6;error=abs(finite-exact)/max(1,abs(finite),abs(exact))
    if error>.001 or info['unidentified_rhs_max']>1e-8:raise ValueError('Conditional gradient pilot failed '+str((exact,finite,error,info)))
    atomic_json(OUT/'pilot.json',dict(status='passed',exact=exact,finite=finite,scaled_error=error,audit=audit(m,th,r)))
    history=[];mm=np.zeros_like(w);v=mm.copy();p0=fp0=None
    for step in range(101):
        began=time.perf_counter();atomic_json(OUT/'progress.json',dict(iteration=step,updates=100,pid=os.getpid()))
        th=np.einsum('tgf,gfk->tgk',X,w);tf=np.einsum('tgf,gfk->tgk',XF,w)
        r=m.solve(th,h,p0=p0);rr=m.solve(tf,f,p0=fp0)
        values=np.zeros((len(h),A.shape[1]));values[:,:m.ng]=r['quantities_gw']
        loss,gx,gp,_,parts=joint_loss(s,d,capacity,design,np.zeros((1,1)),np.zeros((1,1)),r['prices'],values,h,len(h),target,fixed)
        reg,direct=regularizer(w,initial,active)
        rows=[]
        for raw,res,month in [(th,r,1),(tf,rr,2)]:
            checks=audit(m,raw,res);gen=generation(s,d,capacity,res['quantities_gw']*1000,res['hours']);metrics,monthly=metric(s,d,res['prices'],gen,res['hours'],month)
            rows.append(dict(metrics=metrics,audit=checks,monthly_generation_twh=monthly.tolist()))
        # February loss is scored with February observations only AFTER prediction.
        ft=targets(d,f,2);ft['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
        fv=np.zeros((len(f),A.shape[1]));fv[:,:m.ng]=rr['quantities_gw']
        fl,_,_,_,fparts=joint_loss(s,d,capacity,design,np.zeros((1,1)),np.zeros((1,1)),rr['prices'],fv,f,len(f),ft,fixed_month(s,d,f))
        base.save(OUT/f'state-{step:03d}.npz',weights=w,training_prices=r['prices'],forward_prices=rr['prices'])
        record=dict(iteration=step,training=rows[0],forward=rows[1],training_loss=loss+reg,forward_data_loss=fl,regularizer=reg,**parts,seconds=time.perf_counter()-began)
        history.append(record);atomic_json(OUT/'history.json',history)
        print('FIT',step,'JAN',rows[0]['metrics'],'FEB',rows[1]['metrics'],flush=True)
        report(history,s,d,m,w,X,XF) if step%5==0 or step==100 else None
        if step==100:break
        hourly,info=m.backward(th,r,gx[:,:m.ng],gp)
        if info['unidentified_rhs_max']>1e-8:raise ValueError('Unidentified target gradient '+str(info))
        g=np.einsum('tgf,tgk->gfk',X,hourly)+direct;g[~active]=0
        mm=.9*mm+.1*g;v=.999*v+.001*g*g;t=step+1
        w-=RATE*(mm/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
        p0,fp0=r['prices'],rr['prices']
    if any(digest(ROOT/p)!=sha for p,sha in provenance.items()):raise ValueError('Changed sources during trial')
    atomic_json(OUT/'complete.json',dict(updates=100,points=101,physical_certification='not performed; fast corridor candidate only'))

def report(history,s,d,m,w,X,XF):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4));steps=[r['iteration'] for r in history]
    for key,label in [('training','January fit'),('forward','February forward')]:axes[0].plot(steps,[r[key]['metrics']['price_mae'] for r in history],label=label)
    axes[0].set(xlabel='Update',ylabel='Price MAE EUR/MWh',xlim=(0,100));axes[0].legend()
    axes[1].plot(steps,[r['price_loss']+r['generation_loss'] for r in history],label='January data loss')
    axes[1].plot(steps,[r['forward_data_loss'] for r in history],label='February data loss')
    axes[1].set(xlabel='Update',ylabel='Smooth normalized price + generation loss',xlim=(0,100));axes[1].legend();fig.tight_layout();fig.savefig(OUT/'losses.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5));hour=15;raw=np.einsum('gf,gfk->gk',X[hour],w);u=np.linspace(0,1,201)
    for g,row in enumerate(s['groups']):
        if row['zone']!='DE-LU' or m.zero[g] or m.capacity[hour,g]<=0:continue
        slopes=.05+20*np.logaddexp(0,raw[g,1:]);prices=d['source_cost'][hour,g]+raw[g,0]+basis(u)@slopes
        allowed=u*m.reference[g]<=m.capacity[hour,g]
        line=ax.plot(u*m.reference[g],prices,label=row['technology'],alpha=.3)[0]
        ax.plot(u[allowed]*m.reference[g],prices[allowed],color=line.get_color())
    ax.set(xlabel='Output GW (faint: beyond hourly availability)',ylabel='Marginal bid EUR/MWh',title=f'DE-LU · 2025-01-01 15:00 UTC · update {history[-1]["iteration"]}')
    ax.legend();fig.tight_layout();fig.savefig(OUT/'example-curves.png');plt.close(fig)

def run_all():
    global OUT,RATE
    ROOT_OUT.mkdir(exist_ok=True)
    lock=(ROOT_OUT/'suite.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (ROOT_OUT/'suite-started.json').exists():raise ValueError('Inspect existing suite before any restart')
    atomic_json(ROOT_OUT/'suite-started.json',dict(rates=[.05,.15,.5],updates=100,pid=os.getpid()))
    for RATE in [.05,.15,.5]:
        OUT=ROOT_OUT/f'lr-{RATE:g}'
        try:
            # Repeated original setup would stack process-local provenance wrappers.
            # Each trial therefore runs in an isolated child interpreter.
            import subprocess,sys
            log=(ROOT_OUT/f'lr-{RATE:g}.log').open('ab',buffering=0)
            child=subprocess.Popen([sys.executable,'-u',__file__,'--trial',str(RATE)],stdout=log,stderr=subprocess.STDOUT)
            atomic_json(ROOT_OUT/'live-trial.json',dict(rate=RATE,pid=child.pid))
            code=child.wait()
            if code:print('TRIAL FAILED',RATE,'inspect failure evidence; other rates continue',flush=True)
        except Exception:
            ROOT_OUT.mkdir(exist_ok=True);atomic_json(ROOT_OUT/f'controller-failure-{RATE:g}.json',dict(traceback=traceback.format_exc()))
    atomic_json(ROOT_OUT/'suite-finished.json',dict(completed=[r for r in [.05,.15,.5] if (ROOT_OUT/f'lr-{r:g}/complete.json').exists()],failed=[r for r in [.05,.15,.5] if (ROOT_OUT/f'lr-{r:g}/failure.json').exists()]))

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        RATE=float(sys.argv[2]);OUT=ROOT_OUT/f'lr-{RATE:g}'
        try:trial()
        except Exception:
            OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
    else:run_all()
