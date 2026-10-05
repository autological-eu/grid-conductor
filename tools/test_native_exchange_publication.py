import csv,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from monthly_dispatch import digest
from compare_native_exchange_reference import compare,reference
from publish_native_exchange_diagnostic import publish

class ExchangePublication(unittest.TestCase):
    def fixture(self,p):
        source=p/'reference.csv';row={'Year':'2025','Area type':'Country','Category':'Electricity imports','Variable':'Net Imports','Unit':'TWh','Value':'19.54','ISO 3 code':'DEU','Area':'Germany'}
        with source.open('w') as f:w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
        model=dict(status='fixed_inventory_native_country_exchange_diagnostic_not_validation',year=2025,hours=8760,input_sha256='source',annual_replay_sha256='annual',
            countries=[dict(country='DE',hours=8760,net_export_mwh=156e6)])
        mp=p/'model.json';mp.write_text(json.dumps(model))
        cp=p/'comparison.json';comparison=dict(status='secondary_national_exchange_reference_not_entsoe_flow_validation',year=2025,input_sha256='source',annual_replay_sha256='annual',
            model_accounting_sha256=digest(mp),reference_csv_sha256=digest(source),producer_sha256=digest(Path(__file__).with_name('compare_native_exchange_reference.py')),
            comparisons=compare(model,reference([row])))
        cp.write_text(json.dumps(comparison));bp=p/'bounds.json';bp.write_text(json.dumps(dict(status='replayed_economic_annual_bounds_not_validated',input_sha256='source')))
        return model,(p,mp,cp,source,bp,p/'public.json')
    def test_explicit_unpassed_gates(self):
        with tempfile.TemporaryDirectory() as d:
            model,args=self.fixture(Path(d))
            with patch('publish_native_exchange_diagnostic.summarize',return_value=model):publish(*args)
            self.assertFalse(any(json.loads(args[-1].read_text())['acceptance'].values()))
    def test_reject_changed_reference_or_source(self):
        for which in ('reference','source'):
            with tempfile.TemporaryDirectory() as d:
                model,args=self.fixture(Path(d))
                if which=='reference':args[3].write_text(args[3].read_text().replace('19.54','20.54'))
                else:args[4].write_text(json.dumps(dict(status='replayed_economic_annual_bounds_not_validated',input_sha256='other')))
                with patch('publish_native_exchange_diagnostic.summarize',return_value=model),self.assertRaises(ValueError):publish(*args)
    def test_reject_nonreproducing_native_or_comparison(self):
        for which in ('native','comparison'):
            with tempfile.TemporaryDirectory() as d:
                model,args=self.fixture(Path(d))
                if which=='native':replayed={**model,'hours':744}
                else:
                    replayed=model;r=json.loads(args[2].read_text());r['comparisons'][0]['reference_net_export_twh']=19.54;args[2].write_text(json.dumps(r))
                with patch('publish_native_exchange_diagnostic.summarize',return_value=replayed),self.assertRaises(ValueError):publish(*args)
