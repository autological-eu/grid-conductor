import unittest
import numpy as np
from summarize_annual_native_generation import energy


class NativeGenerationAccounting(unittest.TestCase):
    def fixture(self):
        arrays=dict(generation_mw=np.array([[10.],[20.]]),storage_discharge_mw=np.array([[3.,4.],[5.,6.]]),
            storage_charge_mw=np.array([[0.,7.],[0.,8.]]))
        record=dict(generator_ids=['g'],storage_ids=['hydro','phs'],generators=[dict(id='g',country='CH',carrier='nuclear')],
            storage_units=[dict(id='hydro',country='CH',carrier='hydro',p_min_pu=0.,role='Unidirectional reservoir'),
                           dict(id='phs',country='CH',carrier='PHS',p_min_pu=-1.,role='Pumped storage')])
        return arrays,record

    def test_reservoir_primary_and_recycling_separate(self):
        a,r=self.fixture();p,s=energy(a,r)
        self.assertEqual(p,{('CH','nuclear'):30.,('CH','hydro-reservoir'):8.})
        self.assertEqual(s,{('CH','PHS'):dict(discharge_mwh=10.,charge_mwh=15.)})

    def test_unexpected_reservoir_charging_rejected(self):
        a,r=self.fixture();a['storage_charge_mw'][0,0]=1.
        with self.assertRaises(ValueError):energy(a,r)

    def test_changed_identity_rejected(self):
        a,r=self.fixture();r['generator_ids']=['changed']
        with self.assertRaises(ValueError):energy(a,r)

    def test_unclassified_storage_not_primary_generation(self):
        a,r=self.fixture();r['storage_units'][0]['role']='unclassified'
        p,s=energy(a,r);self.assertNotIn(('CH','hydro-reservoir'),p);self.assertIn(('CH','hydro'),s)


if __name__=='__main__':unittest.main()
