import numpy as np
import pytest
from bid_calibration_2025 import bids,score,choose,targets,NTRAIN


def test_only_declared_resource_bids_change():
    base=np.array([[100.,110.,27.,0.,10000.]])
    result=bids(base,['gas','coal','nuclear',None,None],[30.,-30.,15.])
    np.testing.assert_array_equal(result,[[130.,80.,42.,0.,10000.]])
    np.testing.assert_array_equal(base,[[100.,110.,27.,0.,10000.]])
    with pytest.raises(ValueError):bids(base,['gas']*5,[31.,0.,0.])


def test_evaluation_prices_and_generation_cannot_change_training_targets():
    prices=np.ones((8760,1));bank={('FRA','Gas',1):2.,('FRA','Gas',7):1e9}
    first=targets(prices,['FR'],list(range(1,7)),bank)
    prices[NTRAIN:]=1e9;bank[('FRA','Gas',7)]=-1e9
    second=targets(prices,['FR'],list(range(1,7)),bank)
    for key in first:np.testing.assert_array_equal(first[key],second[key])
    assert first['prices'].shape==(4344,1)


def test_price_gain_cannot_hide_large_quantity_regression_in_joint_score():
    baseline=dict(price=10.,generation=.2,trade=.1)
    bad=dict(price=5.,generation=.8,trade=.1)
    assert score(bad,baseline,[0.,0.,0.])>score(baseline,baseline,[0.,0.,0.])


def test_selection_ties_prefer_smaller_adjustments_and_ignore_failed_trials():
    records=[dict(params=[30.,0.,0.],score=1.),dict(params=[0.,0.,0.],score=1.),dict(params=[-30.,0.,0.],score=None)]
    assert choose(records)['params']==[0.,0.,0.]
