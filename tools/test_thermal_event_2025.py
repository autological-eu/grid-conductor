import unittest
import numpy as np
from scipy.sparse import csc_matrix
from thermal_event_model_2025 import compile_day,solve,seed,options,carry

class Event(unittest.TestCase):
    def setup_book(self):
        T=96;A=csc_matrix([[1,1,-1],[0,0,1.]])
        m=dict(ng=2,nl=0,nz=1,islands=1,groups=[dict(columns=[0],capacity_mw=100,carrier='coal')],columns=[dict(column=0,carriers=['coal']),dict(column=1,carriers=['emergency'])])
        d=dict(parameters={'coal':dict(ramp_fraction_per_hour=.2,minimum_output_fraction=.2,startup_lead_hours=3,minimum_up_hours=2,minimum_down_hours=2,startup_eur_per_mw=100,online_eur_per_mw_hour=1)},weather_stress=dict(solar=.5,wind=.7))
        s=dict(availability=np.tile([100.,1000.],(T,1)),cost=np.tile([20.,500.],(T,1)),link_min=np.empty((T,0)),link_max=np.empty((T,0)),load=np.full((T,1),20.),island_rhs=np.zeros((T,1)),ratings=np.empty(0),flow=np.empty((T,0)),initial=np.array([20.,0.,0.]))
        return A,m,d,s
    def test_ramp_triggers_high_marginal_backup(self):
        A,m,d,s=self.setup_book();s['load'][10]=80
        for name in ['control','ramp']:
            state=seed(m,s,d,options(name));lp=compile_day(A,s,m,d,name,0,state);_,x,y,_,_=solve(lp)
            if name=='control':self.assertAlmostEqual(y[10*2],20)
            else:self.assertAlmostEqual(y[10*2],500);q=x[:48*3].reshape(48,3)[:,0];self.assertLessEqual(np.max(abs(np.diff(q))),20+1e-6)
    def test_start_delay_and_midnight_carry(self):
        A,m,d,s=self.setup_book();s['initial'][0]=0;s['load'][:]=0;s['load'][25:]=80
        state=seed(m,s,d,options('commitment'));lp=compile_day(A,s,m,d,'commitment',0,state);_,x,_,_,_=solve(lp);q=x[:48*3].reshape(48,3)[:,0];self.assertLess(np.max(abs(q[:3])),1e-6)
        carried=carry(x,lp,m,state);self.assertGreater(carried['starts'].sum(),0)
        nxt=compile_day(A,s,m,d,'commitment',24,carried);_,z,_,_,_=solve(nxt);second=z[:48*3].reshape(48,3)[:,0]
        self.assertGreater(second[1],0);self.assertGreater(carried['q'][0]+carried['starts'].sum(),0)
    def test_no_thermal_tranche_can_bypass_group_ramp(self):
        A,m,d,s=self.setup_book();A=csc_matrix([[1,1,1,-1],[0,0,0,1.]])
        m.update(ng=3);m['groups'][0]['columns']=[0,1];m['columns']=[dict(column=0,carriers=['coal']),dict(column=1,carriers=['coal']),dict(column=2,carriers=['emergency'])]
        s['availability']=np.tile([50.,50.,1000.],(96,1));s['cost']=np.tile([20.,30.,500.],(96,1));s['initial']=np.array([20.,0.,0.,0.]);s['load'][10]=100
        lp=compile_day(A,s,m,d,'ramp',0,seed(m,s,d,options('ramp')));_,x,_,_,_=solve(lp);q=x[:48*4].reshape(48,4)[:,:2].sum(axis=1);self.assertLessEqual(np.max(abs(np.diff(q))),20+1e-6)
    def test_pooled_renewable_stress_uses_original_components(self):
        A,m,d,s=self.setup_book();m['columns'][0]['carriers']=['onwind','solar']
        s['solar_components']=np.tile([40.,0.],(96,1));s['wind_components']=np.tile([60.,0.],(96,1))
        lp=compile_day(A,s,m,d,'weather_stress',0,seed(m,s,d,options('weather_stress')))
        self.assertAlmostEqual(lp['chi'][0],62.)
        self.assertEqual(s['availability'][0,0],100.)
if __name__=='__main__':unittest.main()
