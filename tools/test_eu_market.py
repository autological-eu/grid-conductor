import copy
import datetime as dt
import unittest
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import build_eu_market
from assemble_eu_market import assemble, to_hourly
from audit_eu_market import audit_bank
from build_eu_market import Bank, prefix_candidates
from validate_market_model import rel_mad, passes, group_error, price_pairs


def fixture():
    def series(v): return [v]*2976
    return dict(schema_version=2, month='2026-08', zones=['A','B'],
        zone_domains={z:dict(price=z,gen=None) for z in ['A','B']},
        interior_borders=[['A','B']], exterior_borders=[], caps_synthetic=[],
        load_mw={'A':series(100),'B':series(100)}, prices={'A':series(20),'B':series(30)},
        generation_mw={'A':{'B04':series(110),'B10':series(20)},'B':{'B04':series(80)}},
        storage_charge_mw={'A':{'B10':series(10)}},
        flows_mw={'A>B':series(30),'B>A':series(10)},
        caps_mw={'A>B':series(50),'B>A':series(25)})


class EuropeanInputTests(unittest.TestCase):
    def test_incomplete_hour_and_real_zero(self):
        self.assertEqual(to_hourly([100,None,None,None],1,'x'),[None])
        self.assertEqual(to_hourly([0]*4,1,'x'),[0])
        self.assertEqual(to_hourly([100,200,300,400],1,'x'),[250])

    def test_no_interpolation(self):
        self.assertEqual(to_hourly([100]*4+[None]*4+[200]*4,3,'x'),[100,None,200])

    def test_conservation_and_asymmetric_capacity(self):
        bank=fixture()
        self.assertTrue(audit_bank(bank)['input_gate_passed'])
        model=assemble(bank)
        self.assertEqual(model['external_net_import_mw']['A'][0],10)
        self.assertEqual(model['edges'][0]['ab_mw'][0],50)
        self.assertEqual(model['edges'][0]['ba_mw'][0],25)
        self.assertEqual(model['provenance']['audit']['A']['balance_residual_mae_mw'],0)
        self.assertFalse(any(g['id'].startswith('A-B10') for g in model['generators']))

    def test_missing_reverse_blocks_not_mirrored(self):
        bank=fixture();del bank['caps_mw']['B>A']
        with self.assertRaisesRegex(ValueError,'input gate'):assemble(bank)

    def test_unknown_flow_and_generation_block(self):
        for field,key in [('flows_mw','B>A'),('load_mw','A')]:
            bank=fixture();bank[field][key][1]=None
            self.assertFalse(audit_bank(bank)['input_gate_passed'])
        bank=fixture();bank['generation_mw']['A']['B04'][1]=None
        self.assertFalse(audit_bank(bank)['input_gate_passed'])

    def test_geography_and_synthetic_block(self):
        bank=fixture();bank['zone_domains']['A']['gen']='different-area'
        self.assertFalse(audit_bank(bank)['input_gate_passed'])
        bank=fixture();bank['caps_synthetic']=['A>B']
        self.assertFalse(audit_bank(bank)['input_gate_passed'])

    def test_price_not_supply_or_truncation(self):
        bank=fixture();bank['prices']['A']=[None]*2976
        self.assertTrue(audit_bank(bank)['input_gate_passed'])
        self.assertEqual(len(assemble(bank)['timestamps']),744)

    def test_domains_do_not_fallback(self):
        zones={'A':{'price':'bidding','gen':'country'}}
        self.assertEqual(prefix_candidates(zones,{}, {}, {},'A'),['bidding'])
        self.assertEqual(prefix_candidates(zones,{}, {}, {},'A','gen'),['country'])

    def test_bank_preserves_observation_and_checks_alignment(self):
        start=dt.datetime(2026,8,1,tzinfo=dt.timezone.utc);bank=Bank(start,4)
        bank.put('x',start,0);bank.put('x',start,None)
        self.assertEqual(bank.load('x')[0],0)
        with self.assertRaises(ValueError):bank.put('x',start+dt.timedelta(minutes=1),2)

    def test_validation_missing_fails_and_blocks_are_summed(self):
        self.assertFalse(passes(None));self.assertFalse(passes(float('nan')))
        self.assertIsNone(group_error({'B12':None},{'B12'}))
        self.assertEqual(rel_mad([{'generation_mw':{'a':40,'b':60}}],[100],['a','b']),0)

    def test_price_exclusion_does_not_shift_dates(self):
        rows=[dict(price_eur_mwh={'A':v},unserved_mwh=u) for v,u in [(10,0),(9999,1),(30,0)]]
        self.assertEqual(price_pairs(rows,[10,20,30],'A'),[(10,10),(30,30)])

    def test_collector_exports_both_directions_without_capacity_fallback(self):
        stamp=dt.datetime(2026,8,1,tzinfo=dt.timezone.utc)
        registry=({'A':{'price':'A'},'B':{'price':'B'}},{},[('A','B')],[],{}, {})
        def fetch(request, directory):
            if request['documentType']=='A61':raise ValueError('No capacity data')
            return ('<Document><type>'+request['documentType']+'</type></Document>').encode()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'bank.json'
            with patch.object(build_eu_market,'DUMP',Path(directory)), patch.object(build_eu_market,'read_registry',return_value=registry), patch.object(build_eu_market,'fetch',side_effect=fetch), patch.object(build_eu_market,'parse_day_ahead_prices',return_value={stamp:20}), patch.object(build_eu_market,'parse_generation',return_value={'B04':{stamp:100}}), patch.object(build_eu_market,'charging',return_value={}), patch.object(build_eu_market,'parse_quantity',return_value={stamp:10}), patch('time.sleep'), contextlib.redirect_stdout(io.StringIO()):
                build_eu_market.collect(output=output)
            bank=json.loads(output.read_text())
            self.assertEqual(set(bank['flows_mw']),{'A>B','B>A'})
            self.assertEqual(bank['caps_mw'],{})
            self.assertEqual(bank['caps_synthetic'],[])


if __name__=='__main__':unittest.main()
