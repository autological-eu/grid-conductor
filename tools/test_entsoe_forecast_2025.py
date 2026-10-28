import unittest
import numpy as np

from compile_entsoe_forecasts_2025 import decode,hourly


def document(points,curve='A03'):
    body=''.join(f'<Point><position>{p}</position><quantity>{v}</quantity></Point>'
                 for p,v in points)
    return (f'<GL_MarketDocument><type>A65</type><TimeSeries>'
            f'<businessType>A04</businessType><quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>'
            f'<curveType>{curve}</curveType><Period><timeInterval>'
            f'<start>2025-01-01T00:00Z</start><end>2025-01-01T02:00Z</end>'
            f'</timeInterval><resolution>PT30M</resolution>{body}</Period>'
            f'</TimeSeries></GL_MarketDocument>').encode()


class ForecastParserTest(unittest.TestCase):
    def test_stepwise_expansion_and_missing_hour(self):
        value=hourly(decode(document([(1,100),(2,120)]),'A65')[('A04','load')])
        self.assertEqual(value[0],110)
        self.assertEqual(value[1],120)
        self.assertTrue(np.isnan(value[2]))

    def test_point_curve_preserves_gap(self):
        value=hourly(decode(document([(1,100),(3,130)],'A01'),'A65')[('A04','load')])
        self.assertTrue(np.isnan(value[0]))
        self.assertTrue(np.isnan(value[1]))


if __name__=='__main__':unittest.main()
