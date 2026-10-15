import numpy as np
import pytest
from diagnose_residual_response_2025 import band_edges, band_ids, response_rows


def test_training_edges_do_not_use_extreme_evaluation_values():
    train = np.arange(4344, dtype=float)
    edges = band_edges(train)
    np.testing.assert_array_equal(band_ids(np.array([-1e9, 1e9]), edges), [0, 4])
    np.testing.assert_allclose(edges, [868.6, 1737.2, 2605.8, 3474.4])


def test_tied_edges_preserve_empty_bands_and_training_exclusion():
    x = np.ones(8760); observed = np.zeros(8760); physical = np.ones(8760)
    physical[:4344] = 1e6
    rows, common, ids = response_rows(x, observed, physical, observed, band_edges(x[:4344]))
    assert [r['hours'] for r in rows] == [0, 0, 0, 0, 4416]
    assert rows[-1]['physical_bias'] == 1.
    assert not common[:4344].any()


def test_missing_prices_are_not_zero_and_negative_prices_remain():
    x = np.ones(8760); observed = np.full(8760, -10.); physical = np.zeros(8760)
    observed[4344] = np.nan
    rows, common, ids = response_rows(x, observed, physical, physical, band_edges(x[:4344]))
    assert rows[-1]['hours'] == 4415
    assert rows[-1]['observed_mean'] == -10.
    assert rows[-1]['physical_bias'] == 10.
    with pytest.raises(ValueError):
        band_edges(np.array([1., np.nan]))
