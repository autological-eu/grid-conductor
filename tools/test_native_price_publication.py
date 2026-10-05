import copy,unittest
from publish_native_price_diagnostic import validate

class PricePublication(unittest.TestCase):
    def report(self):
        return dict(status='provisional_fixed_inventory_price_diagnostic_not_validation',year=2025,hours=8760,
            input_sha256='source',nodes=[dict(node=str(i),status='native_nodal_price_row_absent') for i in range(128)])
    def test_changed_source_partial_year_duplicate_nodes(self):
        for change in [lambda r:r.update(input_sha256='other'),lambda r:r.update(hours=168),
                lambda r:r['nodes'][1].update(node='0')]:
            r=self.report();change(r)
            with self.assertRaises(ValueError):validate(r,'source')
    def test_no_promoted_acceptance(self):
        r=self.report();r['nodes'][0]['status']='validated'
        with self.assertRaises(ValueError):validate(r,'source')
    def test_error_and_coverage_consistency(self):
        r=self.report();row=r['nodes'][0]
        row.update(status='conditional_nodal_vs_observed_zonal_diagnostic_not_validation',matched_hours=12,
            bias_eur_mwh=-2,mae_eur_mwh=2,rmse_eur_mwh=2,correlation=None,
            monthly=[dict(month=m,matched_hours=1,bias_eur_mwh=-2,mae_eur_mwh=2,rmse_eur_mwh=2,correlation=None) for m in range(1,13)])
        validate(r,'source')
        for key,value in [('mae_eur_mwh',1),('correlation',2),('matched_hours',11)]:
            bad=copy.deepcopy(r);bad['nodes'][0][key]=value
            with self.assertRaises(ValueError):validate(bad,'source')
