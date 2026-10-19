"""Complete source dates, explicit calendar alignment and conserved national MW."""
import datetime as dt,unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from nuclear_availability_2025 import parse,hourly,replace


class AvailabilityTests(unittest.TestCase):
    def days(self):return {dt.date(2025,1,1)+dt.timedelta(days=i):float(i+1) for i in range(366)}
    def test_daily_alignment_and_boundaries(self):
        days=self.days();utc=hourly(days,'daily_utc');local=hourly(days,'daily_paris')
        self.assertEqual(utc[-1],365);self.assertEqual(local[-1],366)
        # Both DST boundaries map hours directly, without missing/repeated UTC hours.
        for day in [dt.date(2025,3,30),dt.date(2025,10,26)]:
            value=days[day];self.assertEqual(np.count_nonzero(local==value),23 if day.month==3 else 25)
        self.assertEqual(len(utc),8760);self.assertEqual(hourly(days,'annual_mean')[0],183.)
        del days[dt.date(2026,1,1)]
        with self.assertRaises(KeyError):hourly(days,'daily_paris')
    def test_parser_rejects_missing_or_duplicate_and_ignores_envelope(self):
        lines=['Date;Filière;Valeur (GW)']+[f'{d:%Y/%m/%d};Disponibilité du parc nucléaire;1,25' for d in self.days()]
        lines+=['2025/01/01;Enveloppe 2015-2019;999']
        self.assertEqual(parse(('\ufeff'+'\n'.join(lines)).encode())[dt.date(2025,1,1)],1250)
        with self.assertRaises(AssertionError):parse('\n'.join(lines+[lines[1]]).encode())
        with self.assertRaises(AssertionError):parse('\n'.join(lines[:4]).encode())
    def test_only_target_members_change_no_capacity_creation(self):
        n=SimpleNamespace(generators=pd.DataFrame(dict(p_nom=[10.,30.,20.])))
        original=np.tile([7.,21.,12.],(8760,1));mask=np.array([True,True,False]);q=np.full(8760,36.)
        out=replace(original,n,mask,q);np.testing.assert_array_equal(out[:,2],original[:,2]);np.testing.assert_allclose(out[:,:2].sum(axis=1),q)
        np.testing.assert_array_equal(original[0],[7.,21.,12.])
        with self.assertRaises(AssertionError):replace(original,n,mask,np.full(8760,41.))


if __name__=='__main__':unittest.main()
