"""Minimum slack diagnostic, never artificial supply in accepted dispatch."""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import hstack,csc_matrix,eye
import highspy
import run_independent_hourly_transport_2025 as parent
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
BORDERS=ROOT/'data/bidding-zone-network-2025/nordic-border-envelopes-v2'
WATER=ROOT/'data/bidding-zone-network-2025/sweden-stock-window-v2'
OUT=ROOT/'data/bidding-zone-network-2025/nordic-border-slack-v1'

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Already complete')
 _,(state,m,_,_)=parent.setup();s,d,_,_,_=state
 with np.load(WATER/'water.npz') as z:delta=z['zonal_delta_mw']
 load=m.load[:1416]-delta/1000;matrix=hstack([csc_matrix(m.Z.T),csc_matrix(m.M.T),eye(m.nz),-eye(m.nz)],format='csc');cols=np.arange(matrix.shape[1],dtype=np.int32);rows=np.arange(m.nz,dtype=np.int32);ng=m.ng;nf=len(m.edges);cases=[]
 for endpoint in ['maxBorderFlow','maxExchanges']:
  parentcase=json.loads((BORDERS/(endpoint+'.json')).read_text());hours=[x['hour'] for x in parentcase['feasibility']['infeasible']]
  with np.load(BORDERS/(endpoint+'-bounds.npz')) as z:lower=z['lower_gw'];upper=z['upper_gw']
  solver=highspy.Highs();solver.setOptionValue('threads',1);solver.setOptionValue('output_flag',False);solver.setOptionValue('primal_feasibility_tolerance',1e-9)
  h=hours[0];lo=np.r_[np.zeros(ng),lower[h],np.zeros(2*m.nz)];hi=np.r_[m.capacity[h],upper[h],np.full(2*m.nz,np.inf)]
  lp=highspy.HighsLp();lp.num_col_=len(cols);lp.num_row_=m.nz;lp.col_cost_=np.r_[np.zeros(ng+nf),np.ones(2*m.nz)];lp.col_lower_=lo;lp.col_upper_=hi;lp.row_lower_=lp.row_upper_=load[h];lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=matrix.indptr;lp.a_matrix_.index_=matrix.indices;lp.a_matrix_.value_=matrix.data;solver.passModel(lp)
  deficit=np.zeros((len(hours),m.nz));surplus=deficit.copy();residual=0.
  for t,h in enumerate(hours):
   lo=np.r_[np.zeros(ng),lower[h],np.zeros(2*m.nz)];hi=np.r_[m.capacity[h],upper[h],np.full(2*m.nz,np.inf)]
   solver.changeColsBounds(len(cols),cols,lo,hi);solver.changeRowsBounds(m.nz,rows,load[h],load[h]);solver.run();assert solver.getModelStatus()==highspy.HighsModelStatus.kOptimal
   x=np.array(solver.getSolution().col_value);residual=max(residual,float(abs(matrix@x-load[h]).max()*1000));deficit[t]=x[ng+nf:ng+nf+m.nz]*1000;surplus[t]=x[ng+nf+m.nz:]*1000
  assert residual<=1e-4;np.savez_compressed(OUT/(endpoint+'.npz'),hours=hours,deficit_mw=deficit,surplus_mw=surplus)
  byzone=[dict(zone=z,deficit_mwh=float(deficit[:,j].sum()),surplus_mwh=float(surplus[:,j].sum()),maximum_deficit_mw=float(deficit[:,j].max()),maximum_surplus_mw=float(surplus[:,j].max())) for j,z in enumerate(m.zones) if deficit[:,j].max()>1e-4 or surplus[:,j].max()>1e-4]
  case=dict(endpoint=endpoint,infeasible_hours=len(hours),minimum_deficit_twh=float(deficit.sum()/1e6),minimum_surplus_twh=float(surplus.sum()/1e6),max_primal_mw=residual,zones=byzone);cases.append(case);print(json.dumps(case),flush=True)
 atomic_json(OUT/'summary.json',dict(status='minimum_slack_diagnostic_only_not_dispatch',cases=cases,limitations=['Slack placement may be nonunique; not causal shares.','No new emergency supply or score from this LP is used in the model.'],source_sha256=digest(__file__),source_envelope_summary_sha256=digest(BORDERS/'summary.json')))
if __name__=='__main__':run()
