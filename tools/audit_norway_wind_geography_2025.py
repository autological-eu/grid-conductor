"""Independent dated-share, conserved-input and saved physical witness replay."""
import argparse,datetime as dt,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from norway_wind_geography_2025 import apply
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import digest
from audit_nve_hydro_diagnostics_2025 import physics
from run_bidding_zone_network_2025 import observed
from compare_daily_dispatch_prices import metrics
BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def audit(folder):
    start=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert digest(folder/'annual.npz')==s['witness_sha256']
    assert digest(folder/'design.json')==s['design_sha256']
    assert digest(BASE/'annual.npz')==s['baseline_witness_sha256']
    assert digest(BASE/'summary.json')==s['baseline_summary_sha256']
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    n,cost,fixed,mapping,original,old,hp=build()
    before_av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    before_gen=n.generators.copy();before_load=n.get_switchable_as_dense('Load','p_set').copy()
    before_cost=cost.copy();before_fixed=fixed.copy();before_lines=n.lines.copy();before_links=n.links.copy()
    mask=(n.generators.carrier=='onwind')&n.generators.bus.map(n.buses.country).eq('NO')
    zone=n.generators.bus.map(n.buses.bidding_zone)
    before_z={z:float(before_av[:,mask&zone.eq(z)].sum()/1e6) for z in ['NO1','NO2','NO3','NO4','NO5']}
    source=apply(n);assert source==s['source']
    assert n.generators.drop(columns='p_nom').equals(before_gen.drop(columns='p_nom'))
    assert n.lines.equals(before_lines) and n.links.equals(before_links)
    np.testing.assert_array_equal(cost,before_cost);assert fixed.equals(before_fixed)
    # Separate date parser and zone accumulator: replay every hourly fleet share.
    capacity=np.zeros((8760,5));ids=set()
    path=ROOT/'data/bidding-zone-source-audit-2025/nve-wind.json'
    assert digest(path)==source['source']['sha256']
    dates=[dt.datetime(2025,1,1)+dt.timedelta(hours=t) for t in range(8760)]
    for farm in json.loads(path.read_text()):
        j=int(farm['ElspotomraadeNummer'])-1;assert 0<=j<5
        for batch in farm['Turbiner']:
            assert batch['TurbinID'] not in ids;ids.add(batch['TurbinID'])
            begin=dt.datetime.fromisoformat(batch['DatoIdriftsatt'])
            finish=dt.datetime.fromisoformat(batch['DatoUtavdrift']) if batch.get('DatoUtavdrift') else dt.datetime.max
            assert begin<=finish
            power=float(batch['AntallTurbiner'])*float(batch['TurbinStorrelse_kW'])/1000
            capacity[:,j]+=np.array([begin<=stamp<finish for stamp in dates])*power
    share=capacity/capacity.sum(axis=1)[:,None]
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    np.testing.assert_array_equal(av[:,~mask],before_av[:,~mask])
    np.testing.assert_array_equal(n.generators.loc[~mask,'p_nom'],before_gen.loc[~mask,'p_nom'])
    np.testing.assert_array_equal(n.get_switchable_as_dense('Load','p_set').values,before_load.values)
    national=before_av[:,mask].sum(axis=1)
    np.testing.assert_allclose(av[:,mask].sum(axis=1),national,rtol=1e-12,atol=1e-7)
    nominal=float(before_gen.loc[mask,'p_nom'].sum());fleet=[]
    np.testing.assert_allclose(n.get_switchable_as_dense('Generator','p_max_pu').values[:,mask],
        np.repeat((national/nominal)[:,None],int(mask.sum()),axis=1),rtol=1e-12,atol=1e-12)
    for j,z in enumerate(['NO1','NO2','NO3','NO4','NO5']):
        columns=mask&zone.eq(z);expected=share[:,j]*national
        np.testing.assert_allclose(av[:,columns].sum(axis=1),expected,rtol=1e-12,atol=1e-7)
        oldnom=before_gen.loc[columns,'p_nom'];newnom=n.generators.loc[columns,'p_nom']
        np.testing.assert_allclose(newnom,nominal*share[0,j]*oldnom/oldnom.sum(),atol=1e-8)
        fleet.append(dict(zone=z,dated_registry_mw=float(capacity[0,j]),
            source_normalisation_before_mw=float(oldnom.sum()),source_normalisation_after_mw=float(newnom.sum()),
            available_before_twh=before_z[z],available_after_twh=float(expected.sum()/1e6)))
    m,off=compile_global(n,cost,fixed,'bidding_zone');assert m['zones']==s['zones']
    with np.load(folder/'annual.npz') as a:
        v=a['values'];valid=a['optimal'];prices=a['prices'];obj=a['objectives']
        assert int(valid.sum())==s['optimal_hours']
        assert np.flatnonzero(~valid).tolist()==[r['hour'] for r in s['failures']]
        assert np.isnan(v[~valid]).all() and np.isfinite(v[valid]).all()
        worst=0.;hours=np.flatnonzero(valid)
        for block in np.split(hours,np.where(np.diff(hours)!=1)[0]+1):
            if len(block):worst=max(worst,physics(n,m,v[block],m['load'][block],off.iloc[block].reset_index(drop=True).copy(),int(block[0])))
        error=float(abs((v[valid,:m['ng']]*m['cost'][valid]).sum(axis=1)-obj[valid]).max());assert error<.05
        emergency=float(v[valid,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency-s['emergency_mwh'])<1e-6
        observations=observed(m,prices)
        with np.load(BASE/'annual.npz') as ref:reference=ref['bidding_zone_prices'].copy()
        results=[];obsroot=ROOT/'data/price-trace/dispatch-validation-2025-v2'
        months=n.snapshots.month.values
        for row in observations:
            if not row['metrics']['known_hours']:continue
            z=row['zone'];j=m['zones'].index(row['model_area']);obs=np.array(json.loads((obsroot/(z+'.json')).read_text()),float)
            obs[~valid]=np.nan
            before=metrics(reference[:,j],obs);after=metrics(prices[:,j],obs)
            seasonal=[]
            for label,selection in [('winter',np.isin(months,[12,1,2])),('spring',np.isin(months,[3,4,5])),('summer',np.isin(months,[6,7,8])),('autumn',np.isin(months,[9,10,11]))]:
                seasonal.append(dict(season=label,baseline=metrics(reference[selection,j],obs[selection]),candidate=metrics(prices[selection,j],obs[selection])))
            results.append(dict(zone=z,baseline=before,candidate=after,seasonal=seasonal))
    result=dict(status='dated_shares_and_saved_component_replay_passed_not_acceptance',
        summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
        optimal_hours=int(valid.sum()),failed_hours=int((~valid).sum()),network_maximum_residual_mw=worst,
        objective_maximum_replay_error_eur=error,emergency_mwh=emergency,fleet=fleet,zones=results,
        national_hourly_available_maximum_change_mw=float(abs(av[:,mask].sum(axis=1)-national).max()),
        equal_zone_baseline_mae=float(np.mean([r['baseline']['mae_eur_mwh'] for r in results])),
        equal_zone_candidate_mae=float(np.mean([r['candidate']['mae_eur_mwh'] for r in results])),
        mean_baseline_zonal_correlation=float(np.mean([r['baseline']['correlation'] for r in results])),
        mean_candidate_zonal_correlation=float(np.mean([r['candidate']['correlation'] for r in results])),
        elapsed_seconds=time.perf_counter()-start)
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['optimal_hours','network_maximum_residual_mw','equal_zone_baseline_mae','equal_zone_candidate_mae','mean_candidate_zonal_correlation','elapsed_seconds']},indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);audit(a.folder)
