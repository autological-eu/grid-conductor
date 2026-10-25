"""Offline reservoir retiming under zonal transport feasibility, no price targets.

Flexible generation is eliminated exactly into zonal0..sum(available MW) bounds.
Hydro energy, stock boundaries and power limits stay explicit. A tiny declared
interior generation margin avoids otherwise arbitrary boundary-only prices; it
uses existing available generation, not emergency supply or extra capacity.
"""
import numpy as np
from scipy.sparse import csc_matrix,coo_matrix,hstack,vstack,kron,eye
import highspy

def project(M,available,load_without_hydro,shares,flow_lower,flow_upper,inflow,spill,initial,terminal,stock_capacity,power_lower,power_upper,target_stock,reference_power,anchors=None,margin_mw=.01):
 T,nz=available.shape;ne=M.shape[0];nc=inflow.shape[1];width=ne+4*nc
 p0=ne;s0=p0+nc;e0=s0+nc;d0=e0+nc
 base=hstack([csc_matrix(M.T),csc_matrix((nz,4*nc))],format='csc');grid=kron(eye(T,format='csc'),base,format='csc')
 t,z,c=np.nonzero(shares);grid+=coo_matrix((shares[t,z,c],(t*nz+z,t*width+p0+c)),shape=grid.shape).tocsc()
 tt=np.repeat(np.arange(T),nc);cc=np.tile(np.arange(nc),T);rr=np.arange(T*nc);valid=tt>0
 water=coo_matrix((np.r_[np.ones(2*T*nc),-np.ones(valid.sum())],(np.r_[rr,rr,rr[valid]],np.r_[tt*width+p0+cc,tt*width+s0+cc,(tt[valid]-1)*width+s0+cc[valid]])),shape=(T*nc,T*width)).tocsc()
 small=np.zeros((4*nc,width))
 for c in range(nc):
  small[c,s0+c]=1;small[c,e0+c]=-1;small[nc+c,s0+c]=-1;small[nc+c,e0+c]=-1
  small[2*nc+c,p0+c]=1;small[2*nc+c,d0+c]=-1;small[3*nc+c,p0+c]=-1;small[3*nc+c,d0+c]=-1
 absolute=kron(eye(T,format='csc'),csc_matrix(small),format='csc');matrix=vstack([grid,water,absolute],format='csc')
 margin=np.minimum(margin_mw,available/4)
 water_rhs=(inflow-spill).copy();water_rhs[0]+=initial
 rowlo=np.r_[(load_without_hydro-available+margin).ravel(),water_rhs.ravel(),np.full(T*4*nc,-np.inf)]
 rowhi=np.r_[(load_without_hydro-margin).ravel(),water_rhs.ravel(),np.c_[target_stock,-target_stock,reference_power,-reference_power].ravel()]
 lower=np.zeros((T,width));upper=np.full((T,width),np.inf);lower[:,:ne]=flow_lower;upper[:,:ne]=flow_upper
 lower[:,p0:s0]=power_lower;upper[:,p0:s0]=power_upper;upper[:,s0:e0]=stock_capacity
 lower[-1,s0:e0]=upper[-1,s0:e0]=terminal
 if anchors:
  for hour,stock in anchors.items():lower[hour,s0:e0]=upper[hour,s0:e0]=stock
 cost=np.zeros((T,width));cost[:,e0:d0]=1;cost[:,d0:]=1e-6
 solver=highspy.Highs()
 for k,v in [('threads',1),('output_flag',False),('time_limit',300),('primal_feasibility_tolerance',1e-9),('dual_feasibility_tolerance',1e-9),('solver','ipm')]:solver.setOptionValue(k,v)
 lp=highspy.HighsLp();lp.num_col_=T*width;lp.num_row_=matrix.shape[0];lp.col_cost_=cost.ravel();lp.col_lower_=lower.ravel();lp.col_upper_=upper.ravel();lp.row_lower_=rowlo;lp.row_upper_=rowhi;lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=matrix.indptr;lp.a_matrix_.index_=matrix.indices;lp.a_matrix_.value_=matrix.data;solver.passModel(lp);solver.run()
 if solver.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise ValueError('Network-water projection failed: '+solver.modelStatusToString(solver.getModelStatus()))
 flat=np.array(solver.getSolution().col_value);x=flat.reshape(T,width);ax=matrix@flat
 residual=max(float(np.maximum(rowlo-ax,0).max()),float(np.maximum(ax-rowhi,0).max()),float(np.maximum(lower-x,0).max()),float(np.maximum(x-upper,0).max()))
 if residual>1e-4:raise ValueError('Original projection gate failed '+str(residual))
 power=x[:,p0:s0];stock=x[:,s0:e0];previous=np.vstack([initial,stock[:-1]]);water_res=float(abs(stock-previous-inflow+power+spill).max())
 if water_res>1e-4:raise ValueError('Water replay failed')
 generation=load_without_hydro-x[:,:ne]@M-np.einsum('tzg,tg->tz',shares,power)
 return dict(power=power,stock=stock,flows_mw=x[:,:ne],feasible_generation_mw=generation),dict(seconds=solver.getRunTime(),max_primal_mw_mwh=residual,water_residual_mwh=water_res,interior_existing_generation_margin_mw=margin_mw,objective='sum absolute stock discrepancy +1e-6 absolute pattern change; no price target',stock_max_discrepancy_mwh=float(abs(stock-target_stock).max()),window_generation_difference_mwh=(power-reference_power).sum(axis=0).tolist())
