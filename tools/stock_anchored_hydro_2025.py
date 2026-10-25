"""Lexicographic reservoir schedule: observed-stock proximity, then pattern change.

Inflow, initial/terminal stock, spill, stock capacity and turbine/deliverability
bounds are fixed inputs. Observed stocks are retrospective physical observations,
not generation targets or bid-price labels.
"""
import numpy as np
from scipy.sparse import eye,diags,hstack,vstack,csr_matrix
from scipy.optimize import linprog

def schedule(inflow,initial,terminal,capacity,lower,upper,spill,target_stock,reference):
 T=len(inflow);I=eye(T,format='csr');Z=I*0;delta=I-diags(np.ones(T-1),-1,shape=(T,T),format='csr')
 rhs=np.asarray(inflow)-spill;rhs=rhs.copy();rhs[0]+=initial
 E=hstack([I,delta,Z,Z],format='csr')
 # p, end-of-hour stock, absolute stock discrepancy, absolute power discrepancy.
 A=vstack([hstack([Z,I,-I,Z]),hstack([Z,-I,-I,Z]),hstack([I,Z,Z,-I]),hstack([-I,Z,Z,-I])],format='csr')
 b=np.r_[target_stock,-target_stock,reference,-reference]
 lo=np.r_[lower,np.zeros(3*T)];hi=np.r_[upper,np.full(T,capacity),np.full(2*T,np.inf)]
 lo[2*T-1]=hi[2*T-1]=terminal
 opts=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9,time_limit=180)
 objective=np.r_[np.zeros(2*T),np.ones(T),np.zeros(T)]
 first=linprog(objective,A_ub=A,b_ub=b,A_eq=E,b_eq=rhs,bounds=list(zip(lo,hi)),method='highs-ds',options=opts)
 if not first.success:raise ValueError('Stock projection failed: '+first.message)
 second=linprog(np.r_[np.zeros(3*T),np.ones(T)],A_ub=vstack([A,csr_matrix(objective[None])]),b_ub=np.r_[b,first.fun+1e-4],A_eq=E,b_eq=rhs,bounds=list(zip(lo,hi)),method='highs-ds',options=opts)
 if not second.success:raise ValueError('Pattern tie-break failed: '+second.message)
 x=second.x;power=x[:T];stock=x[T:2*T]
 previous=np.r_[initial,stock[:-1]]
 residual=max(float(abs(stock-previous-inflow+power+spill).max()),float(np.maximum(-stock,0).max()),float(np.maximum(stock-capacity,0).max()),float(np.maximum(lower-power,0).max()),float(np.maximum(power-upper,0).max()),float(abs(stock[-1]-terminal)))
 if residual>1e-4:raise ValueError('Unchanged water feasibility gate failed: '+str(residual))
 return power,stock,dict(water_residual_mwh=residual,stock_l1_minimum_mwh_hours=float(first.fun),stock_l1_realized_mwh_hours=float(abs(stock-target_stock).sum()),pattern_l1_mwh=float(abs(power-reference).sum()),annual_generation_difference_mwh=float(power.sum()-reference.sum()),stock_max_discrepancy_mwh=float(abs(stock-target_stock).max()))
