"""Physics, rolling chronology and transport geography of the compact trial."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from compact_zonal_market import Window, replay, transport_network
from daily_market_clearing import reachable_bounds


def fixture(hydro=False):
    H=48;initial=np.array([0.]);cap=np.array([10.]);charge=np.array([0. if hydro else 2.]);discharge=np.array([2.])
    eta_c=np.array([0. if hydro else .9]);eta_d=np.array([.9]);phi=np.array([.999])
    inflow=np.full((H,1),.2 if hydro else 0.)
    lo,hi=reachable_bounds(inflow,np.broadcast_to(charge,inflow.shape),np.broadcast_to(discharge,inflow.shape),cap,eta_c,eta_d,phi,initial)
    s=dict(ids=['store'],area=np.array([0]),initial=initial,terminal=initial,cap=cap,charge=charge,discharge=discharge,
           eta_c=eta_c,eta_d=eta_d,phi=phi,inflow=inflow,reachable_lower=lo,reachable_upper=hi,
           target=np.zeros((H+1,1)),hydro=np.array([0],dtype=int) if hydro else np.array([],dtype=int),discharge_cost=np.array([.001]))
    m=dict(zones=['0:A'],links=[],offer_zones=np.array(['0:A']),emergency_mask=np.array([False]),
           availability=np.full((H,1),20.),load=np.full((H,1),5.),cost=np.r_[np.full(24,10.),np.full(24,100.)][:,None],
           link_min=np.zeros((H,0)),link_max=np.zeros((H,0)))
    return m,s


class CompactTests(unittest.TestCase):
    def test_battery_carries_energy_and_closes_without_gifts(self):
        m,s=fixture();first=Window(m,s,48).clear(0,s['initial'])[0]
        w=Window(m,s,48);a=w.unpack(first['values'][:24]);current=a['inventory'][-1]
        self.assertGreater(current[0],1.)
        last=Window(m,s,24);b=last.unpack(last.clear(24,current)[0]['values'])
        data={k:np.concatenate([a[k],b[k]]) for k in a}
        checked=replay(m,s,data)
        self.assertEqual(checked['simultaneous_storage_hours'],0)
        self.assertLess(checked['maximum_water_residual'],1e-8)
        self.assertGreater(data['charge'].sum(),data['discharge'].sum())

    def test_reservoir_has_no_pump_and_conserves_original_inflow(self):
        m,s=fixture(True);w=Window(m,s,48);r=w.clear(0,s['initial'])[0];data=w.unpack(r['values'])
        self.assertEqual(len(w.charge_ids),0)
        self.assertEqual(float(data['charge'].sum()),0.)
        self.assertLess(replay(m,s,data)['closure_mwh'],1e-8)
        self.assertLessEqual(float((data['discharge']/s['eta_d']).sum()+data['spill'].sum()),float(s['inflow'].sum())+1e-8)
        corrupted={k:v.copy() for k,v in data.items()};corrupted['inventory'][24,0]+=1
        with self.assertRaisesRegex(ValueError,'physics failed'):replay(m,s,corrupted)

    def test_native_links_keep_losses_and_island_areas(self):
        m,_=fixture();m.update(zones=['0:A','0:B','1:A'],buszone={'a':'0:A','b':'0:B','c':'1:A'},
                              link_min=np.array([[-3.]]*48),link_max=np.array([[4.]]*48))
        native=pd.DataFrame([dict(bus0='a',bus1='c',efficiency=.9)],index=['dc'])
        branches=pd.DataFrame([dict(bus0='a',bus1='b',s_nom=10.,s_max_pu=.8),dict(bus0='a',bus1='b',s_nom=5.,s_max_pu=1.)])
        n=SimpleNamespace(links=native,df=lambda c:branches if c=='Line' else pd.DataFrame())
        out=transport_network(n,m)
        self.assertEqual(out['zones'],m['zones'])
        self.assertEqual(out['links'][0]['efficiency'],.9)
        np.testing.assert_array_equal(out['link_min'][:,0],m['link_min'][:,0])
        self.assertEqual(out['links'][1]['limit'],13.)
        self.assertEqual(out['links'][0]['b'],2)

    def test_cached_solver_updates_demand_cost_and_stock(self):
        m,s=fixture();w=Window(m,s,24)
        a=w.clear(0,s['initial'])[0]
        m['load'][24:]=6.
        b=w.clear(24,s['initial'])[0]
        cold=Window(m,s,24).clear(24,s['initial'])[0]
        self.assertAlmostEqual(b['objective_eur'],cold['objective_eur'],places=7)
        self.assertGreater(b['objective_eur'],a['objective_eur'])
        np.testing.assert_allclose(b['prices'],cold['prices'],atol=1e-9)


if __name__=='__main__':unittest.main()
