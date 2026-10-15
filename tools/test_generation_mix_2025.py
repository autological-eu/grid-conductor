import json
import numpy as np
import pytest
import generation_mix_2025 as mix


def test_equal_bid_mix_is_not_unique_and_joint_bounds_require_regrouping():
    av=np.array([[40.,60.]]);dispatch=np.array([[50.]])
    p,lo,hi,cap=mix.allocate(av,dispatch,[[0,1]],['solar','wind'],['solar','wind'])
    np.testing.assert_allclose(p,[[20.,30.]])
    np.testing.assert_array_equal(lo,[[0.,10.]])
    np.testing.assert_array_equal(hi,[[40.,50.]])
    # Combined output is exactly 50, not the sum of individual marginal bounds.
    p,lo,hi,_=mix.allocate(av,dispatch,[[0,1]],['renewable','renewable'],['renewable'])
    np.testing.assert_array_equal(lo,[[50.]])
    np.testing.assert_array_equal(hi,[[50.]])


def test_zero_availability_and_explicit_emergency_exclusion():
    p,lo,hi,cap=mix.allocate(np.array([[0.,10.]]),np.array([[0.,5.]]),[[0],[1]],['wind',None],['wind'])
    assert p[0,0]==lo[0,0]==hi[0,0]==0
    with pytest.raises(ValueError):
        mix.allocate(np.array([[0.]]),np.array([[1.]]),[[0]],['wind'],['wind'])


def test_partial_generation_is_not_zero_filled_or_annualised():
    m=np.array([10.,20.,30.]);o=np.array([10.,np.nan,40.])
    result=mix.quantity_metrics(m,o,np.zeros(3),m)
    assert result['known_hours']==2
    assert result['status']=='matched_hours_only_not_annualised'
    assert result['model_twh']==40/1e6 and result['observed_twh']==50/1e6
    assert result['outside_allocation_range_hours']==1


def test_missing_constituent_and_unreported_psr_remain_unknown(tmp_path,monkeypatch):
    monkeypatch.setattr(mix,'ROOT',tmp_path)
    p=tmp_path/'data/carbon-pilot/map-2025/NO1/01.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps([dict(start='2025-01-01T00:00:00Z',generation_mwh_by_type={'B19':4.,'B18':2.},primary_generation_mwh=6.)]))
    replay=dict(zones=[dict(zone='NO1',monthly=[dict(status='raw_interval_energy_replayed',month=1,processed_sha256=mix.digest(p))])])
    data,coverage=mix.observations(replay,{'NO':['NO1','NO5'],'example':['NO1']},{})
    assert np.isnan(data[:,0]).all() and coverage[0]['missing_areas']==['NO5']
    assert data[0,1,mix.FAMILIES.index('onshore_wind')]==4.
    assert data[0,1,mix.FAMILIES.index('offshore_wind')]==2.
    assert np.isnan(data[0,1,mix.FAMILIES.index('nuclear')])
