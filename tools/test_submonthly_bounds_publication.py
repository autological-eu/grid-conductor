import unittest
from publish_submonthly_economic_bounds import summary


class BoundsPublication(unittest.TestCase):
    def fixture(self):
        return dict(status='independently_replayed_economic_annual_feasible',year=2025,hours=8760,blocks=59,
            input_sha256='source',annual_feasible_cost_eur=100.,cyclic_closure_residual_mwh=0.,
            rows=[dict(index=i,max_equality_residual=1e-10,max_inequality_violation=0.,max_bound_violation=0.) for i in range(59)])

    def test_reports_gap_without_validation_claim(self):
        r=summary(self.fixture(),dict(input_sha256='source'),100.,80.)
        self.assertEqual(r['relative_gap'],.2)
        self.assertFalse(any(r['methods'].values()))

    def test_rejects_partial_or_wrong_source(self):
        a=self.fixture();a['hours']=8759
        with self.assertRaises(ValueError):summary(a,dict(input_sha256='source'),100.,80.)
        with self.assertRaises(ValueError):summary(self.fixture(),dict(input_sha256='changed'),100.,80.)

    def test_rejects_invalid_bound(self):
        for lower in (101.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):summary(self.fixture(),dict(input_sha256='source'),100.,lower)

    def test_rejects_changed_upper_or_calendar(self):
        with self.assertRaises(ValueError):summary(self.fixture(),dict(input_sha256='source'),99.,80.)
        a=self.fixture();a['rows'][0]['index']=1
        with self.assertRaises(ValueError):summary(a,dict(input_sha256='source'),100.,80.)

    def test_rejects_residual_failure(self):
        for value in (1e-6,float('nan'),-1.):
            a=self.fixture();a['rows'][0]['max_equality_residual']=value
            with self.assertRaises(ValueError):summary(a,dict(input_sha256='source'),100.,80.)


if __name__=='__main__':unittest.main()
