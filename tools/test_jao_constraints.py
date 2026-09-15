import copy
import unittest
from unittest.mock import patch
from carbon_pilot import timestamp
from jao_constraints import normalize, month_summary, collect_day
from market_model import dispatch
from test_market_model import fixture
from audit_jao_sample import check_positions


class JaoTests(unittest.TestCase):
    def test_daily_failure_falls_back_to_bounded_chunks(self):
        start=timestamp('2026-01-01T00:00Z')
        with patch('jao_constraints.collect',side_effect=[ValueError('network')]+[dict(rows=1,timestamps={}) for _ in range(4)]) as mock:
            result=collect_day('nordic',start)
        self.assertEqual(result['rows'],4)
        self.assertEqual(len(result['chunks']),4)
        self.assertEqual(mock.call_count,5)

    def test_nordic_coverage_requires_all_quarters(self):
        start=timestamp('2026-01-01T00:00Z');end=timestamp('2026-01-01T01:00Z')
        report=month_summary('nordic',start,end,[dict(timestamps={'2026-01-01T00:00:00Z':2},rows=2)])
        self.assertEqual(report['published_hour_coverage'],0)
        self.assertEqual(report['published_interval_coverage'],.25)

    def test_published_positions_violation_and_missing_hubs(self):
        restrictions=[dict(ptdf={'A':.5,'B':-.5},ram_mw=50)]
        self.assertTrue(check_positions(restrictions,[dict(dateTimeUtc='t',hub_A=50,hub_B=-50)])[0]['passed'])
        self.assertFalse(check_positions(restrictions,[dict(dateTimeUtc='t',hub_A=51,hub_B=-51)])[0]['passed'])
        with self.assertRaises(ValueError):check_positions(restrictions,[dict(dateTimeUtc='t',hub_A=50)])

    def test_half_open_and_virtual_hubs_preserved(self):
        start=timestamp('2026-01-01T00:00Z');end=timestamp('2026-01-01T01:00Z')
        row=dict(id=1,dateTimeUtc='2026-01-01T00:00Z',ram=-2,ptdf_FR=.5,ptdf_ALBE=-.1,ptdf_CH=None)
        outside=dict(row,id=2,dateTimeUtc='2026-01-01T01:00Z')
        result=normalize([row,row,outside],start,end)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['ptdf'],{'FR':.5,'ALBE':-.1})
        self.assertEqual(result[0]['ram_mw'],-2)

    def test_conflicting_duplicate_rejected(self):
        row=dict(id=1,dateTimeUtc='2026-01-01T00:00Z',ram=2,ptdf_FR=.5)
        with self.assertRaises(ValueError):normalize([row,dict(row,ram=3)],timestamp('2026-01-01T00:00Z'),timestamp('2026-01-01T01:00Z'))

    def model(self):
        data=fixture();data['edges']=[]
        data['flow_based_regions']=[dict(id='test',zones=['A','B'],constraints=[
            dict(id=str(h),interval=h,ptdf={'A':.5,'B':-.5},ram_mw=50) for h in range(2)])]
        return data

    def test_flow_based_dispatch_and_shadow_price(self):
        data=self.model();before=copy.deepcopy(data);baseline=dispatch(data)
        self.assertEqual(data,before)
        self.assertAlmostEqual(baseline['flow_based_net_positions_mw']['A'][0],50)
        self.assertAlmostEqual(baseline['flow_based_net_positions_mw']['B'][0],-50)
        self.assertAlmostEqual(baseline['flow_based_constraints'][0]['marginal_cost_reduction_eur_per_mw'],80)
        for row in data['flow_based_regions'][0]['constraints']:row['ram_mw']+=50
        self.assertAlmostEqual(baseline['total_cost_eur']-dispatch(data)['total_cost_eur'],8000)

    def test_unmapped_hubs_and_missing_intervals_fail(self):
        data=self.model();data['flow_based_regions'][0]['constraints'][0]['ptdf']['virtual']=0
        with self.assertRaisesRegex(ValueError,'PTDF'):dispatch(data)
        data=self.model();data['flow_based_regions'][0]['constraints'].pop()
        with self.assertRaisesRegex(ValueError,'intervals'):dispatch(data)

    def test_no_internal_edge_double_counting(self):
        data=self.model();data['edges']=fixture()['edges']
        with self.assertRaisesRegex(ValueError,'double-count'):dispatch(data)


if __name__=='__main__':unittest.main()
