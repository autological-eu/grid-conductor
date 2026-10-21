import unittest
from sdac_prices_2025 import parse,START

def xml(series):return ('<Publication_MarketDocument><type>A44</type>'+series+'</Publication_MarketDocument>').encode()
def series(seq='',contract='A01',points='<Point><position>1</position><price.amount>-4</price.amount></Point>',curve='A01'):
    return f'<TimeSeries><contract_MarketAgreement.type>{contract}</contract_MarketAgreement.type><currency_Unit.name>EUR</currency_Unit.name><price_Measure_Unit.name>MWH</price_Measure_Unit.name><in_Domain.mRID>Z</in_Domain.mRID><out_Domain.mRID>Z</out_Domain.mRID>{seq}<curveType>{curve}</curveType><Period><timeInterval><start>2025-01-01T00:00Z</start><end>2025-01-01T02:00Z</end></timeInterval><resolution>PT60M</resolution>{points}</Period></TimeSeries>'
def seq(n):return f'<classificationSequence_AttributeInstanceComponent.position>{n}</classificationSequence_AttributeInstanceComponent.position>'
class Prices(unittest.TestCase):
    def test_select_sdac_without_auction_fallback(self):
        a=series(seq(1));b=series(seq(2)).replace('-4','900')
        p=parse(xml(a+b),'DE-LU','Z');self.assertEqual(p[START],-4);self.assertIsNone(p[START.replace(hour=1)])
        self.assertEqual(parse(xml(b),'AT','Z'),{})
    def test_intraday_excluded_and_ambiguity_rejected(self):
        self.assertEqual(parse(xml(series()+series(seq(2),'A07')),'ES','Z')[START],-4)
        with self.assertRaises(ValueError):parse(xml(series(seq(1))),'DK1','Z')
    def test_missing_vs_published_block(self):
        self.assertIsNone(parse(xml(series()),'DK1','Z')[START.replace(hour=1)])
        self.assertEqual(parse(xml(series(curve='A03')),'DK1','Z')[START.replace(hour=1)],-4)
    def test_conflicts_units_zone(self):
        for raw in [xml(series()+series().replace('-4','5')),xml(series()).replace(b'EUR',b'USD'),xml(series()).replace(b'>Z<',b'>X<')]:
            with self.assertRaises(ValueError):parse(raw,'DK1','Z')
if __name__=='__main__':unittest.main()
