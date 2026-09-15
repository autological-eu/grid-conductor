import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import datetime as dt
from monthly_weather import month_window, owned_remove, merge, tree_bytes


class BudgetUtilityTests(unittest.TestCase):
    def test_months_cover_year_without_duplicate_boundary(self):
        windows = [month_window(2025, m) for m in range(1, 13)]
        self.assertEqual(sum((b-a).total_seconds()/3600 for a, b in windows), 8760)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(windows, windows[1:])))
        self.assertEqual((month_window(2024, 2)[1]-month_window(2024, 2)[0]).days, 29)

    def test_cleanup_cannot_escape_owned_directory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)/'owned'; root.mkdir()
            outside = Path(temp)/'keep'; outside.write_text('keep')
            for target in [root, outside]:
                with self.assertRaises(ValueError):
                    owned_remove(target, root)
            batch = root/'batch'; batch.mkdir(); (batch/'raw').write_text('abc')
            self.assertEqual(tree_bytes(root), 3)
            owned_remove(batch, root)
            self.assertTrue(outside.exists())

    def test_deep_merge_preserves_unspecified_resources(self):
        result = merge({'a': {'b': 1, 'c': 2}}, {'a': {'b': 3}})
        self.assertEqual(result, {'a': {'b': 3, 'c': 2}})


try:
    import atlite
except ImportError:
    atlite = None


@unittest.skipIf(atlite is None, 'Requires pinned atlite environment')
class CompactConversionTests(unittest.TestCase):
    def test_cached_wind_preserves_annual_mean_and_layout(self):
        import numpy as np
        import xarray as xr
        from compact_cutout import resource_key, open_cutout
        with TemporaryDirectory() as temp:
            cutout = atlite.Cutout(Path(temp)/'raw.nc', module='era5',
                x=slice(0, .3), y=slice(50, 50.3), dx=.3, dy=.3,
                time=slice('2025-01-01', '2025-01-01 03:00'))
            shape = (4, len(cutout.coords['y']), len(cutout.coords['x']))
            cutout.data['wnd100m'] = (('time', 'y', 'x'), np.broadcast_to(np.array([3, 7, 11, 15])[:,None,None], shape))
            cutout.data['roughness'] = (('time', 'y', 'x'), np.full(shape, .1))
            options = dict(turbine='Vestas_V112_3MW', smooth=False, add_cutout_windspeed=True)
            key = resource_key('wind', options)
            field = cutout.wind(aggregate_time=None, **options)
            packed = xr.Dataset({key: field.astype('float32')}, attrs=dict(cutout.data.attrs))
            packed.attrs['gridfix_compact'] = 1
            path = Path(temp)/'compact.nc'; packed.to_netcdf(path)
            compact = open_cutout(path)
            np.testing.assert_allclose(compact.wind(capacity_factor=True, **options),
                cutout.wind(capacity_factor=True, **options), rtol=1e-6)
            layout = xr.ones_like(field.isel(time=0))
            actual = compact.wind(layout=layout, per_unit=True, **options)
            expected = cutout.wind(layout=layout, per_unit=True, **options)
            np.testing.assert_allclose(actual.transpose(*expected.dims), expected, rtol=1e-6)
            self.assertEqual(set(actual.dims), set(expected.dims))
            with self.assertRaises(ValueError):
                compact.wind(turbine='unknown')
            compact.data.close()


if __name__ == '__main__':
    unittest.main()
