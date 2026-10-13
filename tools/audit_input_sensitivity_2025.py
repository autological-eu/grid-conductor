"""Saved-source coefficient/physics replay and paired sensitivity evaluation."""
import argparse,hashlib,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from input_sensitivity_2025 import CASES,WIND,inputs,compile_case,wind_source_check
from nve_hydro_diagnostics import digest
from audit_nve_hydro_diagnostics_2025 import physics
from run_bidding_zone_network_2025 import observed
from compare_daily_dispatch_prices import metrics

BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'


def evaluate(folder):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert digest(folder/'design.json')==s['design_sha256']
    assert s['producer_sha256']==digest(ROOT/'tools/run_input_sensitivity_2025.py')
    assert digest(BASE/'summary.json')==s['baseline_summary_sha256']
    assert digest(BASE/'annual.npz')==s['baseline_witness_sha256']
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert list(s['cases'])==list(CASES)
    n,cost,fixed,mapping,original,old,hp=build();cf=n.get_switchable_as_dense('Generator','p_max_pu').values.copy()
    assert hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()==s['mapping_sha256']
    fuel,assumptions,source=inputs(n);assert source==s['source']
    assert wind_source_check(n,cf)==s['wind_observations']
    with np.load(folder/'control.npz') as a:reference=a['prices'].copy();ref_valid=a['optimal'].copy();ref_obj=a['objectives'].copy()
    with np.load(BASE/'annual.npz') as a:
        base_obj=a['bidding_zone_objectives'];base_prices=a['bidding_zone_prices']
        reproduction=dict(maximum_objective_difference_eur=float(abs(ref_obj[ref_valid]-base_obj[ref_valid]).max()),
                          maximum_price_difference_eur_mwh=float(abs(reference[ref_valid]-base_prices[ref_valid]).max()))
        assert reproduction['maximum_objective_difference_eur']<.05
    comparisons={};checks={};all_prices={};all_valid=ref_valid.copy()
    obsroot=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    for name,deltas in CASES.items():
        record=s['cases'][name];assert record['deltas']==deltas
        assert digest(folder/(name+'.npz'))==record['witness_sha256']
        m,off,nc,na=compile_case(n,cost,cf,fixed,deltas,fuel,assumptions)
        # Independent direct reconstruction of each declared cost/bound difference.
        expected_av=cf.copy();expected_cost=cost.copy();gas,oil,carbon=fuel
        for j,(_,g) in enumerate(n.generators.iterrows()):
            if g.carrier in WIND:expected_av[:,j]=np.minimum(cf[:,j]*(1+deltas.get('wind',0)),1.) if deltas.get('wind',0) else cf[:,j]
            if g.carrier not in ['CCGT','OCGT','coal','lignite','oil']:continue
            input_delta=carbon*assumptions[g.carrier]['emissions_t_mwh_th']*deltas.get('carbon',0)
            if g.carrier in ['CCGT','OCGT']:input_delta=input_delta+gas*deltas.get('gas',0)
            if g.carrier=='oil':input_delta=input_delta+oil*deltas.get('oil',0)
            expected_cost[:,j]+=input_delta/g.efficiency
        np.testing.assert_array_equal(nc,expected_cost);np.testing.assert_array_equal(na,expected_av)
        assert hashlib.sha256(nc.tobytes()).hexdigest()==record['cost_sha256']
        assert hashlib.sha256(na.tobytes()).hexdigest()==record['availability_sha256']
        with np.load(folder/(name+'.npz')) as a:
            valid=a['optimal'];v=a['values'];obj=a['objectives'];prices=a['prices']
            assert int(valid.sum())==record['optimal_hours']
            assert [r['hour'] for r in record['failures']]==np.flatnonzero(~valid).tolist()
            assert np.isfinite(v[valid]).all() and np.isnan(v[~valid]).all()
            worst=0.;ids=np.flatnonzero(valid)
            for group in np.split(ids,np.where(np.diff(ids)!=1)[0]+1):
                if len(group):worst=max(worst,physics(n,m,v[group],m['load'][group],off.iloc[group].reset_index(drop=True).copy(),int(group[0])))
            obj_replay=(v[valid,:m['ng']]*m['cost'][valid]).sum(axis=1)
            objerror=float(abs(obj_replay-obj[valid]).max());assert objerror<.05
            emergency=float(v[valid,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency-record['emergency_mwh'])<1e-6
            observations=observed(m,prices);paired=[]
            for row in observations:
                if row['metrics']['known_hours']==0:continue
                z=row['zone'];j=m['zones'].index(row['model_area']);obs=np.array(json.loads((obsroot/(z+'.json')).read_text()),float)
                common=valid&ref_valid&np.isfinite(obs);obs[~common]=np.nan
                before=metrics(reference[:,j],obs);after=metrics(prices[:,j],obs)
                change=prices[common,j]-reference[common,j]
                paired.append(dict(zone=z,control=before,case=after,
                    delta_mae_eur_mwh=after['mae_eur_mwh']-before['mae_eur_mwh'],
                    delta_correlation=after['correlation']-before['correlation'],
                    mean_absolute_price_response_eur_mwh=float(abs(change).mean()),
                    price_changed_hours=int((abs(change)>1e-4).sum()),
                    maximum_absolute_price_response_eur_mwh=float(abs(change).max())))
            comparisons[name]=dict(zones=paired,equal_zone_control_mae=float(np.mean([r['control']['mae_eur_mwh'] for r in paired])),
                equal_zone_case_mae=float(np.mean([r['case']['mae_eur_mwh'] for r in paired])),
                equal_zone_mean_absolute_price_response=float(np.mean([r['mean_absolute_price_response_eur_mwh'] for r in paired])),
                arithmetic_mean_zonal_correlation=float(np.mean([r['case']['correlation'] for r in paired])))
            checks[name]=dict(optimal_hours=int(valid.sum()),failed_hours=int((~valid).sum()),
                network_maximum_residual_mw=worst,objective_maximum_replay_error_eur=objerror,
                emergency_mwh=emergency,observed_price_areas_reparsed=len(paired))
            all_prices[name]=prices.copy();all_valid&=valid
    interaction=all_prices['all_plus10']-reference
    for name in ['wind_plus10','gas_plus10','oil_plus10','carbon_plus10']:interaction-=all_prices[name]-reference
    known_labels=[r['zone'] for r in comparisons['control']['zones']]
    indices=[s['zones'].index(z) for z in known_labels]
    nonadditivity=dict(common_all_case_hours=int(all_valid.sum()),observed_zones=len(indices),
        mean_absolute_price_response_nonadditivity_eur_mwh=float(abs(interaction[all_valid][:,indices]).mean()),
        maximum_absolute_nonadditivity_eur_mwh=float(abs(interaction[all_valid][:,indices]).max()))
    # Use one common calendar for ranking, rather than comparing unequal cohorts.
    common_comparisons={}
    for name,prices in all_prices.items():
        paired=[]
        for z in known_labels:
            j=s['zones'].index(z);obs=np.array(json.loads((obsroot/(z+'.json')).read_text()),float)
            common=all_valid&np.isfinite(obs);obs[~common]=np.nan
            before=metrics(reference[:,j],obs);after=metrics(prices[:,j],obs)
            response=prices[common,j]-reference[common,j]
            paired.append(dict(zone=z,control=before,case=after,
                delta_mae_eur_mwh=after['mae_eur_mwh']-before['mae_eur_mwh'],
                delta_correlation=after['correlation']-before['correlation'],
                mean_absolute_price_response_eur_mwh=float(abs(response).mean()),
                price_changed_hours=int((abs(response)>1e-4).sum())))
        common_comparisons[name]=dict(zones=paired,
            equal_zone_control_mae=float(np.mean([r['control']['mae_eur_mwh'] for r in paired])),
            equal_zone_case_mae=float(np.mean([r['case']['mae_eur_mwh'] for r in paired])),
            equal_zone_mean_absolute_price_response=float(np.mean([r['mean_absolute_price_response_eur_mwh'] for r in paired])),
            arithmetic_mean_zonal_correlation=float(np.mean([r['case']['correlation'] for r in paired])))
    result=dict(status='saved_coefficient_and_component_replay_passed',summary_sha256=digest(folder/'summary.json'),
        auditor_sha256=digest(__file__),baseline_reproduction=reproduction,cases=checks,comparisons=comparisons,
        common_all_case_comparisons=common_comparisons,
        combined_positive_interaction=nonadditivity,elapsed_seconds=time.perf_counter()-began,
        limits=['Predeclared +/-10% sensitivity, not source correction, causal error shares or held-out acceptance.',
                'Metric differences are paired over common valid hours; failures remain missing.',
                'Correlation mean is the arithmetic mean of zone correlations, not a pooled Europe correlation.',
                'Sources and original water/input replay are protected; no baseline promotion.'])
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{'mae':v['equal_zone_case_mae'],'response':v['equal_zone_mean_absolute_price_response']} for k,v in comparisons.items()},indent=2))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);evaluate(a.folder)
