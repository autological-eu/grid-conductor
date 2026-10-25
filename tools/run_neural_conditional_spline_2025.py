"""Fresh matched-input neural conditioner experiment; January→February100."""
import json,os,time,fcntl,traceback,csv
from pathlib import Path
import numpy as np
import run_independent_hourly_transport_2025 as parent
from conditional_monotone_market_2025 import ConditionalMarket,basis
from neural_spline_conditioner_2025 import Conditioner
from run_conditional_monotone_2025 import features,audit
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from run_supply_knots_lp_2025 import joint_loss
from supply_knot_network_2025 import generation
OUT=ROOT/'data/bidding-zone-network-2025/neural-conditional-spline-v1'
REFERENCE=ROOT/'data/bidding-zone-network-2025/conditional-monotone-v1'

def pilot(m,model,state,active):
 s,d,_,_,_=state;h=np.array([15,111,318,567,759,815,900]);X=features(s,d,h,m.reference)
 raw,cache=model.forward(X,active,True);r=m.solve(raw,h,tolerance=1e-11);rng=np.random.default_rng(73)
 gq=rng.normal(size=r['quantities_gw'].shape);gp=rng.normal(size=r['prices'].shape);gp[:,~np.isfinite(d['observed_prices']).all(axis=0)]=0
 g,info=m.backward(raw,r,gq,gp);grad=model.backward(g,cache);checks=[]
 for seed in [31,73,91]:
  rng=np.random.default_rng(seed);direction={k:rng.normal(size=v.shape) for k,v in model.p.items()};exact=sum(float((grad[k]*direction[k]).sum()) for k in grad);values=[];eps=1e-6
  saved={k:v.copy() for k,v in model.p.items()}
  for sign in [1,-1]:
   for k in model.p:model.p[k]=saved[k]+sign*eps*direction[k]
   rr=m.solve(model.forward(X,active),h,p0=r['prices'],tolerance=1e-11);values.append(float((rr['quantities_gw']*gq).sum()+(rr['prices']*gp).sum()))
  model.p=saved;finite=(values[0]-values[1])/(2*eps);err=abs(finite-exact)/max(1,abs(finite),abs(exact));checks.append(dict(seed=seed,exact=exact,finite=finite,scaled_error=err))
  if err>.001:raise ValueError('Neural-dispatch gradient pilot failed '+str(checks[-1]))
 if info['unidentified_rhs_max']>1e-8:raise ValueError('Unidentified pilot target')
 return dict(status='passed',checks=checks,audit=audit(m,raw,r))

def plots(history,s,d,m,raw):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(12,4));steps=[r['iteration'] for r in history]
 old=json.loads((REFERENCE/'history.json').read_text())
 for key,label,color in [('training','January','#2563eb'),('forward','February','#ea580c')]:
  axes[0].plot(steps,[r[key]['metrics']['price_mae'] for r in history],label='Neural '+label,color=color)
  axes[0].plot([r['iteration'] for r in old],[r[key]['metrics']['price_mae'] for r in old],label='Linear '+label,color=color,ls='--',alpha=.6)
 axes[0].set(xlabel='Update',ylabel='Price MAE EUR/MWh',xlim=(0,100));axes[0].legend(fontsize=8)
 axes[1].plot(steps,[r['price_loss']+r['generation_loss'] for r in history],label='January data loss');axes[1].plot(steps,[r['forward_data_loss'] for r in history],label='February data loss');axes[1].set(xlabel='Update',ylabel='Smooth price + generation data loss',xlim=(0,100));axes[1].legend()
 fig.tight_layout();fig.savefig(OUT/'losses.png');plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5));u=np.linspace(0,1,201);h=15
 for g,row in enumerate(s['groups']):
  if row['zone']!='DE-LU' or m.zero[g] or m.capacity[h,g]<=0:continue
  slopes=.05+20*np.logaddexp(0,raw[h,g,1:]);prices=m.source[h,g]+raw[h,g,0]+basis(u)@slopes;allowed=u*m.reference[g]<=m.capacity[h,g]
  line=ax.plot(u*m.reference[g],prices,alpha=.25)[0];ax.plot(u[allowed]*m.reference[g],prices[allowed],color=line.get_color(),label=row['technology'])
 ax.set(title=f'DE-LU · 1 January15:00 UTC · update{history[-1]["iteration"]}',xlabel='Output GW; faint beyond available output',ylabel='Marginal bid EUR/MWh');ax.legend();fig.tight_layout();fig.savefig(OUT/'example-curves.png');plt.close(fig)

def diagnostics(s,d,prices,step):
 with np.load(REFERENCE/'state-100.npz') as z:old=z['forward_prices']
 train=month_hours(1);future=month_hours(2);complete=np.isfinite(d['observed_prices']).all(axis=0)
 with (OUT/'february-errors.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['zone','cohort','hours','linear100_mae','neural_mae','linear100_bias','neural_bias','neural_update'])
  for j in np.flatnonzero(complete):
   observed=d['observed_prices'][future,j];lo,hi=np.quantile(d['observed_prices'][train,j],[.05,.95])
   for name,mask in [('all',np.ones(len(future),bool)),('above_january_p95',observed>hi),('below_january_p05',observed<lo),('middle', (observed>=lo)&(observed<=hi))]+[(f'UTC_hour_{k:02d}',future%24==k) for k in range(24)]:
    if not mask.any():continue
    a=old[mask,j]-observed[mask];b=prices[mask,j]-observed[mask];w.writerow([s['zones'][j],name,int(mask.sum()),float(abs(a).mean()),float(abs(b).mean()),float(a.mean()),float(b.mean()),step])

def run():
 OUT.mkdir(exist_ok=True);lock=(OUT/'lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if (OUT/'history.json').exists() or (OUT/'failure.json').exists():raise ValueError('Inspect existing study before restart')
 base,(state,m,network,_)=parent.setup();s,d,A,_,capacity=state;m.__class__=ConditionalMarket
 with np.load(REFERENCE/'reference.npz') as z:m.reference=z['capacity_reference_gw']
 techs=sorted({g['technology'] for g in s['groups']});model=Conditioner([g['zone_id'] for g in s['groups']],[techs.index(g['technology']) for g in s['groups']])
 h=month_hours(1);f=month_hours(2);X=features(s,d,h,m.reference);XF=features(s,d,f,m.reference);active=(d['capacity'][h]>0).any(axis=0)&~m.zero
 target=targets(d,h,1);ft=targets(d,f,2);complete=np.isfinite(d['observed_prices']).all(axis=0)
 target['prices'][:,~complete]=np.nan;ft['prices'][:,~complete]=np.nan;fixed=fixed_month(s,d,h);ffixed=fixed_month(s,d,f)
 design=dict(price_smooth_absolute_epsilon=1,price_scale_eur_mwh=40,generation_floor_twh=.25,generation_smooth_absolute_epsilon=.01,ridge=0)
 paths=[Path(__file__),ROOT/'tools/neural_spline_conditioner_2025.py',ROOT/'tools/test_neural_spline_conditioner_2025.py',ROOT/'tools/conditional_monotone_market_2025.py',ROOT/'tools/run_conditional_monotone_2025.py',REFERENCE/'history.json',REFERENCE/'state-100.npz',REFERENCE/'reference.npz',REFERENCE/'provenance.json']
 pinned=parent.provenance(base);pinned.update({str(p.relative_to(ROOT)):digest(p) for p in paths});atomic_json(OUT/'provenance.json',pinned)
 atomic_json(OUT/'design.json',dict(hidden=[32,32],activation='tanh',zone_embedding=8,technology_embedding=4,seed=20261025,learning_rate=.003,updates=100,parameter_count=sum(v.size for v in model.p.values()),features='same six nonconstant physical/calendar inputs as linear model',reference='unchanged annual peak availability proxy, not nameplate',penalty='0.001 mean squared parameter departure from initialization',training='January only; all744h',validation='February all672h; model-selection development period, not untouched forecast',network='unchanged fast95-corridor approximation; no physical adoption claim',comparison='same initial bids and physical inputs; changes nonlinear architecture, cross-zone/technology sharing and optimizer LR'))
 atomic_json(OUT/'pilot.json',pilot(m,model,state,active));initial={k:v.copy() for k,v in model.p.items()};mm={k:np.zeros_like(v) for k,v in model.p.items()};vv={k:np.zeros_like(v) for k,v in model.p.items()};N=sum(v.size for v in model.p.values());history=[];p0=fp0=None
 for step in range(101):
  started=time.perf_counter();atomic_json(OUT/'progress.json',dict(iteration=step,updates=100,pid=os.getpid()))
  th,cache=model.forward(X,active,True);tf=model.forward(XF,active);r=m.solve(th,h,p0=p0);rr=m.solve(tf,f,p0=fp0)
  value=np.zeros((len(h),A.shape[1]));value[:,:m.ng]=r['quantities_gw'];zero=np.zeros((1,1));loss,gx,gp,_,parts=joint_loss(s,d,capacity,design,zero,zero,r['prices'],value,h,len(h),target,fixed)
  fvalue=np.zeros((len(f),A.shape[1]));fvalue[:,:m.ng]=rr['quantities_gw'];fl,*_=joint_loss(s,d,capacity,design,zero,zero,rr['prices'],fvalue,f,len(f),ft,ffixed)
  reg=.001*sum(float(((v-initial[k])**2).sum()) for k,v in model.p.items())/N;rows=[]
  for raw,res,month in [(th,r,1),(tf,rr,2)]:
   checks=audit(m,raw,res);gen=generation(s,d,capacity,res['quantities_gw']*1000,res['hours']);metrics,monthly=metric(s,d,res['prices'],gen,res['hours'],month);rows.append(dict(metrics=metrics,audit=checks,monthly_generation_twh=monthly.tolist()))
  base.save(OUT/f'state-{step:03d}.npz',**model.p,training_prices=r['prices'],forward_prices=rr['prices'])
  row=dict(iteration=step,training=rows[0],forward=rows[1],training_loss=loss+reg,forward_data_loss=fl,regularizer=reg,**parts,seconds=time.perf_counter()-started);history.append(row);atomic_json(OUT/'history.json',history)
  print('FIT',step,'JAN',rows[0]['metrics'],'FEB',rows[1]['metrics'],flush=True)
  if step%5==0 or step==100:plots(history,s,d,m,th);diagnostics(s,d,rr['prices'],step)
  if step==100:break
  hourly,info=m.backward(th,r,gx[:,:m.ng],gp)
  if info['unidentified_rhs_max']>1e-8:raise ValueError('Unidentified target gradient '+str(info))
  grad=model.backward(hourly,cache)
  for key in model.p:
   g=grad[key]+.002*(model.p[key]-initial[key])/N
   if not np.isfinite(g).all():raise ValueError('Nonfinite network gradient')
   mm[key]=.9*mm[key]+.1*g;vv[key]=.999*vv[key]+.001*g*g;t=step+1;model.p[key]-=.003*(mm[key]/(1-.9**t))/(np.sqrt(vv[key]/(1-.999**t))+1e-8)
  p0,fp0=r['prices'],rr['prices']
 if any(digest(ROOT/p)!=sha for p,sha in pinned.items()):raise ValueError('Changed provenance')
 atomic_json(OUT/'complete.json',dict(points=101,updates=100,original_physical_certification='not performed'))

if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
