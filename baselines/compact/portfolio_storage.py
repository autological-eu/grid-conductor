"""Reusable chronological joint LP for several batteries and scenario offers.

Research candidate. The original hourly network rows and accepted 2025 input
arrays are preserved; this module is separate from source-hashed one-battery
receipts. Use clear() with explicit starting stock for each battery.
"""
from __future__ import annotations

import time

import highspy
import numpy as np
from scipy.sparse import block_diag, coo_matrix, hstack, vstack

from .lp import ratings_at
from .storage import Battery


class PortfolioWindow:
    def __init__(self, model, costs, batteries: tuple[Battery, ...], hours: int):
        if hours < 24 or hours % 24:
            raise ValueError('Expected a positive whole-day look-ahead')
        if not batteries:
            raise ValueError('At least one battery required')
        zones=list(map(str,model['zones']))
        if len({b.zone for b in batteries}) != len(batteries):
            raise ValueError('One candidate battery per zone in this research runner')
        for b in batteries:
            if (b.zone not in zones or b.power_mw<=0 or b.energy_mwh<=0 or
                    not 0<b.charge_efficiency<=1 or not 0<b.discharge_efficiency<=1 or
                    not 0<=b.initial_mwh<=b.energy_mwh or not 0<=b.terminal_mwh<=b.energy_mwh or
                    b.throughput_eur_mwh<0):
                raise ValueError(f'Invalid battery: {b}')
        self.model=model;self.costs=costs;self.batteries=batteries;self.hours=hours
        self.nb=len(batteries)
        self.ng,self.nl,self.nz=(int(model[k]) for k in ('ng','nl','nz'))
        self.nr,self.nc=model['A'].shape
        if self.nc!=self.ng+self.nl+self.nz or costs.shape!=(8760,self.ng):
            raise ValueError('Scenario LP column or bid-cost mismatch')
        self.nbase=hours*self.nc
        self.ncols=self.nbase+3*self.nb*hours
        self.nrows=hours*self.nr+self.nb*hours
        self.zone_indices=[zones.index(b.zone) for b in batteries]
        began=time.perf_counter()
        source=block_diag([model['A'].tocsc()]*hours,format='csc')
        rows=[];cols=[];vals=[]
        for bi,zi in enumerate(self.zone_indices):
            for t in range(hours):
                rows.extend((t*self.nr+zi,)*2)
                cols.extend((self._col(bi,t,0)-self.nbase,self._col(bi,t,1)-self.nbase))
                vals.extend((-1.,1.))
        injection=coo_matrix((vals,(rows,cols)),shape=(hours*self.nr,3*self.nb*hours)).tocsc()
        network=hstack([source,injection],format='csc')
        rows=[];cols=[];vals=[]
        for bi,b in enumerate(batteries):
            for t in range(hours):
                row=bi*hours+t
                rows.extend((row,row,row))
                cols.extend((self._col(bi,t,0),self._col(bi,t,1),self._col(bi,t,2)))
                vals.extend((-b.charge_efficiency,1/b.discharge_efficiency,1.))
                if t:
                    rows.append(row);cols.append(self._col(bi,t-1,2));vals.append(-1.)
        stock=coo_matrix((vals,(rows,cols)),shape=(self.nb*hours,self.ncols)).tocsc()
        self.matrix=vstack([network,stock],format='csc')
        self.assembly_seconds=time.perf_counter()-began
        highs=highspy.Highs()
        highs.setOptionValue('output_flag',False)
        highs.setOptionValue('threads',1)
        highs.setOptionValue('solver','simplex')
        highs.setOptionValue('primal_feasibility_tolerance',1e-8)
        highs.setOptionValue('dual_feasibility_tolerance',1e-8)
        self.highs=highs;self._initialized=False

    def _col(self,bi,t,k):
        return self.nbase+3*(bi*self.hours+t)+k

    def _arrays(self,start,initial):
        if (start<0 or start+self.hours>8760 or len(initial)!=self.nb or
                any(not 0<=v<=b.energy_mwh for v,b in zip(initial,self.batteries))):
            raise ValueError('Invalid start or stock vector')
        c=np.zeros(self.ncols)
        lower=np.full(self.ncols,-np.inf)
        upper=np.full(self.ncols,np.inf)
        row_lower=np.zeros(self.nrows)
        row_upper=np.zeros(self.nrows)
        model=self.model
        for t in range(self.hours):
            h=start+t;col=t*self.nc;row=t*self.nr
            c[col:col+self.ng]=self.costs[h]
            lower[col:col+self.ng]=0.
            upper[col:col+self.ng]=model['availability'][h]
            lower[col+self.ng:col+self.ng+self.nl]=model['link_min'][h]
            upper[col+self.ng:col+self.ng+self.nl]=model['link_max'][h]
            k=self.nz+len(model['islands'])
            rhs=np.r_[model['load'][h],model['island_rhs'][h]]
            row_lower[row:row+k]=rhs;row_upper[row:row+k]=rhs
            rating=ratings_at(model,h)
            row_lower[row+k:row+self.nr]=-rating-model['flow'][h]
            row_upper[row+k:row+self.nr]=rating-model['flow'][h]
        for bi,b in enumerate(self.batteries):
            for t in range(self.hours):
                col=self._col(bi,t,0)
                c[col:col+2]=b.throughput_eur_mwh
                lower[col:col+3]=0.
                upper[col:col+3]=[b.power_mw,b.power_mw,b.energy_mwh]
            terminal=self._col(bi,self.hours-1,2)
            lower[terminal]=upper[terminal]=b.terminal_mwh
            row_lower[self.hours*self.nr+bi*self.hours]=initial[bi]
            row_upper[self.hours*self.nr+bi*self.hours]=initial[bi]
        return c,lower,upper,row_lower,row_upper

    def clear(self,start:int,initial:tuple[float,...]):
        began=time.perf_counter()
        c,lower,upper,row_lower,row_upper=self._arrays(start,initial)
        highs=self.highs
        if not self._initialized:
            lp=highspy.HighsLp()
            lp.num_col_,lp.num_row_=self.ncols,self.nrows
            lp.col_cost_,lp.col_lower_,lp.col_upper_=c,lower,upper
            lp.row_lower_,lp.row_upper_=row_lower,row_upper
            lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
            lp.a_matrix_.start_=self.matrix.indptr
            lp.a_matrix_.index_=self.matrix.indices
            lp.a_matrix_.value_=self.matrix.data
            highs.passModel(lp);self._initialized=True
        else:
            cols=np.arange(self.ncols,dtype=np.int32)
            rows=np.arange(self.nrows,dtype=np.int32)
            highs.changeColsCost(self.ncols,cols,c)
            highs.changeColsBounds(self.ncols,cols,lower,upper)
            highs.changeRowsBounds(self.nrows,rows,row_lower,row_upper)
        update_seconds=time.perf_counter()-began
        began=time.perf_counter()
        highs.setOptionValue('time_limit',highs.getRunTime()+120.)
        highs.run()
        if highs.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            highs.clearSolver();highs.setOptionValue('time_limit',highs.getRunTime()+120.)
            highs.run()
        if highs.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            raise RuntimeError(f'Window {start}: {highs.modelStatusToString(highs.getModelStatus())}')
        solve_seconds=time.perf_counter()-began
        result=highs.getSolution();x=np.asarray(result.col_value)
        actual=self.matrix@x
        residual=max(float(np.maximum(row_lower-actual,0).max(initial=0)),
                     float(np.maximum(actual-row_upper,0).max(initial=0)),
                     float(np.maximum(lower-x,0).max(initial=0)),
                     float(np.maximum(x-upper,0).max(initial=0)))
        if residual>1e-4:
            raise ValueError(f'Window {start}: primal residual {residual}')
        values=x[:self.nbase].reshape(self.hours,self.nc)
        if np.any(values[:,:self.ng][:,self.model['emergency_mask']].sum(axis=1)>1e-6):
            raise ValueError(f'Window {start}: emergency dispatch')
        storage=x[self.nbase:].reshape(self.nb,self.hours,3)
        if np.any(np.minimum(storage[:,:,0],storage[:,:,1])>1e-5):
            raise ValueError(f'Window {start}: simultaneous battery cycling')
        prices=np.asarray(result.row_dual)[:self.hours*self.nr].reshape(self.hours,self.nr)[:,:self.nz]
        return dict(objective_eur=float(highs.getObjectiveValue()),values=values,
                    zonal_prices=prices,storage=storage,maximum_primal_residual=residual,
                    update_seconds=update_seconds,solve_seconds=solve_seconds)
