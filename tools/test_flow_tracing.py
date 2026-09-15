import unittest
import datetime as dt
from flow_tracing import trace, solve, parse_quantity, charging, parse_day_ahead_prices, hourly
from test_carbon_pilot import document, point


def price_doc(points, resolution='PT60M', zone='10YZZ', curve='A01', intervals=None):
    import xml.etree.ElementTree as ET
    ns = 'http://iec.ch/TC57/2013/schema/message'
    doc = ET.Element(f'{{{ns}}}Publication_MarketDocument')
    for tag in ['mRID', 'type', 'process.processType']:
        ET.SubElement(doc, f'{{{ns}}}{tag}').text = tag.title()
    ts = ET.SubElement(doc, f'{{{ns}}}TimeSeries')
    for tag, value in [('businessType', 'B07'), ('in_Domain.mRID', zone), ('out_Domain.mRID', zone),
                       ('currency_Unit.name', 'EUR'), ('price_Measure_Unit.name', 'MWH'), ('curveType',curve)]:
        ET.SubElement(ts, f'{{{ns}}}{tag}').text = value
    period = ET.SubElement(ts, f'{{{ns}}}Period')
    ET.SubElement(period, f'{{{ns}}}resolution').text = resolution
    start = '2026-08-10T00:00Z'
    minutes = {'PT15M': 15, 'PT60M': 60}[resolution]
    total = (intervals or len(points)) * minutes
    end = f'2026-08-10T{total//60:02d}:{total%60:02d}Z'
    ti = ET.SubElement(period, f'{{{ns}}}timeInterval')
    ET.SubElement(ti, f'{{{ns}}}start').text = start
    ET.SubElement(ti, f'{{{ns}}}end').text = end
    for position, amount in points:
        p = ET.SubElement(period, f'{{{ns}}}Point')
        ET.SubElement(p, f'{{{ns}}}position').text = str(position)
        ET.SubElement(p, f'{{{ns}}}price.amount').text = str(amount)
    return ET.tostring(doc, encoding='unicode')


def node(generation, intensity, load, unknown=0, charging=0):
    return dict(generation=generation, emissions=(generation-unknown)*intensity,
                unknown=unknown, load=load, charging=charging)


class FlowTests(unittest.TestCase):
    def test_transit_import_carbon(self):
        result = trace({'FR':node(40,50,0),'DE':node(60,500,80),
                        'DK':node(0,0,20)}, {('FR','DE'):40,('DE','DK'):20})
        self.assertAlmostEqual(result['DE']['carbon_intensity'],320)
        self.assertAlmostEqual(result['DK']['carbon_intensity'],320)
        self.assertAlmostEqual(sum(result[z]['carbon_intensity']*load for z,load in [('FR',0),('DE',80),('DK',20)]),32000)

    def test_loop_is_solved_together(self):
        result = trace({'A':node(100,100,100),'B':node(100,500,100)},
                       {('A','B'):50,('B','A'):50})
        self.assertAlmostEqual(result['A']['carbon_intensity'],200)
        self.assertAlmostEqual(result['B']['carbon_intensity'],400)

    def test_boundary_and_storage_uncertainty_propagate(self):
        result = trace({'A':node(50,100,50,unknown=10),'B':node(0,0,50)},
                       {('EXTERNAL','A'):50,('A','B'):50})
        self.assertAlmostEqual(result['B']['unresolved_supply_share'],.6)
        self.assertIsNone(result['B']['carbon_intensity'])
        self.assertAlmostEqual(result['B']['sensitivity_low'],40)
        self.assertAlmostEqual(result['B']['sensitivity_high'],940)

    def test_deficit_is_unknown_not_clean(self):
        r = trace({'A':node(50,100,100)}, {})['A']
        self.assertEqual(r['unresolved_supply_share'],.5)
        self.assertEqual(r['balance_residual_mwh'],-50)
        self.assertEqual(r['quality'],'large_balance_residual')

    def test_charging_is_a_sink_and_surplus_is_reported(self):
        r = trace({'A':node(100,100,70,charging=20)}, {})['A']
        self.assertEqual(r['balance_residual_mwh'],10)
        self.assertEqual(r['carbon_intensity'],100)

    def test_unanchored_loop_rejected(self):
        with self.assertRaises(ValueError):
            trace({'A':node(0,0,0),'B':node(0,0,0)}, {('A','B'):10,('B','A'):10})

    def test_metadata_checked_before_period_parsing(self):
        xml = document(point(1,20))
        self.assertEqual(len(parse_quantity(xml,{'inBiddingZone_Domain.mRID':'TEST'})),4)
        with self.assertRaises(ValueError):
            parse_quantity(xml,{'inBiddingZone_Domain.mRID':'WRONG'})

    def test_only_storage_consumption_is_charging(self):
        self.assertEqual(charging(document(point(1,10),direction='out',kind='B18'),'TEST'),{})
        self.assertEqual(len(charging(document(point(1,10),direction='out',kind='B10'),'TEST')['B10']),4)

    def test_flow_module_does_not_change_production_pilot_geography(self):
        from carbon_pilot import AREAS
        self.assertEqual(set(AREAS),{'FR','DE','DK-DK1','DK-DK2'})

    def test_invalid_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            trace({'A':node(10,0,10,unknown=11)}, {})


class PriceDocTests(unittest.TestCase):
    def test_intraday_price_is_not_a_day_ahead_price(self):
        import xml.etree.ElementTree as ET
        root=ET.fromstring(price_doc([(1,'10')]))
        series=next(e for e in root.iter() if e.tag.endswith('TimeSeries'))
        ET.SubElement(series,'contract_MarketAgreement.type').text='A07'
        with self.assertRaises(ValueError):parse_day_ahead_prices(ET.tostring(root))

    def test_a03_price_blocks_are_observations(self):
        xml=price_doc([(1,'10'),(4,'-2')],resolution='PT15M',curve='A03',intervals=8)
        values=parse_day_ahead_prices(xml)
        start=dt.datetime(2026,8,10,tzinfo=dt.timezone.utc)
        self.assertEqual(hourly(values,start),7)
        self.assertEqual(hourly(values,start+dt.timedelta(hours=1)),-2)

    def test_a01_price_gap_stays_unknown(self):
        values=parse_day_ahead_prices(price_doc([(1,'10'),(4,'-2')],resolution='PT15M',intervals=8))
        self.assertIsNone(hourly(values,dt.datetime(2026,8,10,tzinfo=dt.timezone.utc)))

    def test_hourly_prices_parsed_with_negatives(self):
        prices = parse_day_ahead_prices(price_doc([(1, '50.0'), (2, '-5.5')]))
        hour = dt.datetime(2026, 8, 10, 0, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(prices[hour], 50.0)
        self.assertEqual(prices[hour + dt.timedelta(minutes=15)], 50.0)
        self.assertEqual(prices[hour + dt.timedelta(hours=1)], -5.5)
        self.assertAlmostEqual(hourly(prices, hour), 50.0)
        self.assertAlmostEqual(hourly(prices, hour + dt.timedelta(hours=1)), -5.5)

    def test_quarterly_prices_aggregate_via_hourly(self):
        prices = parse_day_ahead_prices(price_doc([(1, '60'), (2, '40'), (3, '40'), (4, '20')], resolution='PT15M'))
        hour = dt.datetime(2026, 8, 10, 0, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(len(prices), 4)
        self.assertAlmostEqual(hourly(prices, hour), 40.0)

    def test_hourly_missing_quarter(self):
        self.assertIsNone(hourly({}, dt.datetime(2026, 8, 10, 0, 0, tzinfo=dt.timezone.utc)))

    def test_rejects_non_price_document(self):
        with self.assertRaises(ValueError):
            parse_day_ahead_prices(document(point(1, 10)))

    def test_rejects_non_eur_and_cross_zone(self):
        bad = price_doc([(1, '1')], zone='10YZ')
        bad = bad.replace('EUR', 'USD')
        with self.assertRaises(ValueError):
            parse_day_ahead_prices(bad)
        with self.assertRaises(ValueError):
            parse_day_ahead_prices('<Publication_MarketDocument/>')

    def test_price_survives_entsoe_shaping(self):
        xml = price_doc([(1, '40.00')])
        self.assertEqual(parse_day_ahead_prices(xml)[dt.datetime(2026, 8, 10, 0, 0, tzinfo=dt.timezone.utc)], 40.0)


if __name__ == '__main__':
    unittest.main()
