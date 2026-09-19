import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from pypsa_border_targets import border_catalog, relax_border, solve, write_json, operational_emissions

try:
    import pypsa
except ImportError:
    pypsa = None


@unittest.skipIf(pypsa is None, 'Run integration cases inside the pinned PyPSA-Eur environment')
class BorderTests(unittest.TestCase):
    def network(self):
        n = pypsa.Network()
        n.set_snapshots(['2026-01-01'])
        n.add('Bus', 'A', country='FR', x=2, y=47)
        n.add('Bus', 'B', country='DE', x=10, y=51)
        n.add('Bus', 'C', country='DE', x=11, y=51)
        n.add('Generator', 'cheap', bus='A', p_nom=200, marginal_cost=10)
        n.add('Generator', 'costly', bus='B', p_nom=200, marginal_cost=50)
        n.add('Load', 'demand', bus='B', p_set=100)
        n.add('Line', 'border', bus0='A', bus1='B', x=.1, r=.01, s_nom=50)
        n.add('Line', 'domestic', bus0='B', bus1='C', x=.1, r=.01, s_nom=50)
        return n

    def test_analytical_border_saving_and_original_unchanged(self):
        original = self.network()
        borders = border_catalog(original)
        self.assertEqual([b['id'] for b in borders], ['DE-FR'])
        base = original.copy()
        self.assertAlmostEqual(solve(base), 3000, places=4)
        scenario = original.copy()
        relax_border(scenario, borders[0], 50)
        self.assertAlmostEqual(solve(scenario), 1000, places=4)
        self.assertEqual(scenario.lines.at['border', 'x'], original.lines.at['border', 'x'])
        self.assertEqual(original.lines.at['border', 's_max_pu'], 1)

    def test_zero_capacity_assets_skipped_only_in_lenient_mode(self):
        original = self.network()
        original.add('Link', 'placeholder', bus0='A', bus1='B', p_nom=0, carrier='DC')
        with self.assertRaises(ValueError):
            border_catalog(original)
        borders = border_catalog(original, allow_zero_capacity=True)
        self.assertEqual([b['id'] for b in borders], ['DE-FR'])
        self.assertEqual(len(borders[0]['assets']), 1)

    def test_parallel_assets_share_increment_and_domestic_unchanged(self):
        n = self.network()
        n.add('Line', 'parallel', bus0='A', bus1='B', x=.1, r=.01, s_nom=150)
        relax_border(n, border_catalog(n)[0], 100)
        added = sum(n.lines.at[i, 's_nom']*(n.lines.at[i, 's_max_pu']-1)
                    for i in ['border', 'parallel'])
        self.assertAlmostEqual(added, 100)
        self.assertEqual(n.lines.at['domestic', 's_max_pu'], 1)

    def test_cheaper_border_relief_can_increase_emissions(self):
        n = self.network()
        n.add('Carrier', 'coal', co2_emissions=.34)
        n.add('Carrier', 'gas', co2_emissions=.2)
        n.generators.loc['cheap', ['carrier', 'efficiency']] = ['coal', .4]
        n.generators.loc['costly', ['carrier', 'efficiency']] = ['gas', .5]
        solve(n)
        before = operational_emissions(n)
        self.assertAlmostEqual(before, 62.5, places=4)
        relax_border(n, border_catalog(n)[0], 50)
        solve(n)
        self.assertAlmostEqual(before-operational_emissions(n), -22.5, places=4)
        n.carriers.loc['coal', 'co2_emissions'] = float('nan')
        with self.assertRaises(ValueError):
            operational_emissions(n)

    def test_dc_dynamic_bounds_and_negative_increment(self):
        n = self.network()
        n.remove('Line', 'border')
        n.add('Link', 'dc', bus0='A', bus1='B', carrier='DC', p_nom=50,
              p_min_pu=-1, p_max_pu=[.8])
        border = border_catalog(n)[0]
        with self.assertRaises(ValueError):
            relax_border(n, border, -1)
        relax_border(n, border, 25)
        self.assertAlmostEqual(n.links_t.p_max_pu['dc'].iloc[0], 1.3)
        self.assertAlmostEqual(n.links.at['dc', 'p_min_pu'], -1.5)


class SerializationTests(unittest.TestCase):
    def test_nonfinite_rejected(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                write_json(Path(folder)/'report.json', {'value': float('nan')})


if __name__ == '__main__':
    unittest.main()
