"""Full annual witness, or early rejected year with a numerical Farkas certificate."""
import time
import highspy
import numpy as np
from generation_mix_2025 import digest
from nve_hydro_diagnostics import solver
from run_regional_water_candidate_2025 import guarded_hour


def clear_or_reject(m,flow,cost,path):
    start=time.perf_counter(); case=m|dict(cost=cost); h=solver(case); h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x=np.full((8760,m['A'].shape[1]),np.nan); y=np.full((8760,m['A'].shape[0]),np.nan); obj=np.full(8760,np.nan)
    for t in range(8760):
        r,v=guarded_hour(h,case,t,flow[t])
        if v is None:
            h=solver(case); h.setOptionValue('primal_feasibility_tolerance',1e-8); r,v=guarded_hour(h,case,t,flow[t])
        if v is None:
            ray=np.zeros(m['A'].shape[0]); certificate=None
            if h.getModelStatus()==highspy.HighsModelStatus.kInfeasible:
                _,exists,raw=h.getDualRay()
                if exists:
                    raw=np.array(raw);raw/=max(abs(raw).max(),1e-30)
                    lo=np.r_[m['load'][t],m['island_rhs'][t],-m['ratings']-flow[t]]; hi=np.r_[m['load'][t],m['island_rhs'][t],m['ratings']-flow[t]]
                    lower=np.r_[np.zeros(m['ng']),m['link_min'][t]]; upper=np.r_[m['availability'][t],m['link_max'][t]]
                    for candidate in [raw,-raw]:
                        a=m['A'].T@candidate; finite=m['ng']+m['nl']; free=float(abs(a[finite:]).max(initial=0))
                        row=float(np.maximum(candidate,0)@lo+np.minimum(candidate,0)@hi)
                        col=float(np.maximum(a[:finite],0)@upper+np.minimum(a[:finite],0)@lower); gap=row-col
                        if free<=1e-7 and gap>1e-4:
                            ray=candidate; certificate=dict(row_bound_mw=row,column_maximum_mw=col,separation_gap_mw=gap,free_column_residual=free); break
            np.savez_compressed(path,values=x[:t],row_duals=y[:t],objectives=obj[:t],optimal=np.ones(t,bool),hours=np.arange(t),rejected_hour=np.array(t),farkas_row_ray=ray)
            info=dict(witness=path.name,witness_sha256=digest(path),hours=t,optimal_hours=t,complete_year=False,failed_hour=t,solver_status=r['status'],rejection='numerically_certified_infeasible_hour' if certificate else 'unresolved_solver_failure',farkas_certificate=certificate,clearing_seconds=time.perf_counter()-start)
            return None,None,None,info
        x[t]=v;y[t]=h.getSolution().row_dual;obj[t]=r['objective_eur']
    np.savez_compressed(path,values=x,row_duals=y,objectives=obj,optimal=np.ones(8760,bool),hours=np.arange(8760))
    return x,y,obj,dict(witness=path.name,witness_sha256=digest(path),hours=8760,optimal_hours=8760,complete_year=True,failures=[],clearing_seconds=time.perf_counter()-start)
