"""Reject unused/public intermediate data returning to the static publication."""
from pathlib import Path
import fnmatch
import gzip
import hashlib
import json
from pack_model_metadata import FILES

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = [
    'dispatch-comparison-2025/overview.png',
    'dispatch-comparison-2025/national-mix.png',
    'dispatch-comparison-2025/daily-prices.png',
    'dispatch-comparison-2025/zone-mae-grid.png',
    'dispatch-comparison-2025/prices-by-zone.csv',
    'dispatch-comparison-2025/daily-fuel-prices-by-zone.csv',
    'dispatch-comparison-2025/renewable-source-prices-by-zone.csv',
    'dispatch-comparison-2025/renewable-capacity-audit.csv',
    'dispatch-comparison-2025/nuclear-availability-prices-by-zone.csv',
    'dispatch-comparison-2025/nuclear-availability-by-month.csv',
    'dispatch-comparison-2025/joint-search-cases.csv',
    'dispatch-comparison-2025/joint-prices-by-zone.csv',
    'dispatch-comparison-2025/joint-generation-by-country.csv',
    'dispatch-comparison-2025/inverse-search-cases.csv',
    'dispatch-comparison-2025/inverse-prices-by-zone.csv',
    'dispatch-comparison-2025/inverse-generation-by-country.csv',
    'dispatch-comparison-2025/generation-by-area.csv',
    'dispatch-comparison-2025/generation-by-fuel.csv',
    'dispatch-comparison-2025/national-generation.csv',
    'dispatch-comparison-2025/summary.json',
    'entsoe-fast-targets.json', 'carbon-spreads-2025.json',
    'zone-prices-2025/*.json', 'irena-capacity-2025/summary.json.gz',
    'european-reservoir-clearing-2025/summary.json.gz',
    'european-reservoir-clearing-2025/replay.json',
    'fixed-reservoir-screening-2025/summary.json.gz',
    'fixed-reservoir-screening-2025/resource-bids.json',
    'fixed-reservoir-screening-2025/resource-bids-curves.png',
    'fixed-reservoir-screening-2025/resource-bids-errors.png',
    'fixed-reservoir-screening-2025/nve-water-update.json',
    'fixed-reservoir-screening-2025/nve-water-update.png',
    'fixed-reservoir-screening-2025/nve-hydro-diagnostics.json',
    'fixed-reservoir-screening-2025/nve-geography-errors.png',
    'fixed-reservoir-screening-2025/nve-bounded-hydro.png',
    'fixed-reservoir-screening-2025/bidding-zone-model.json',
    'fixed-reservoir-screening-2025/bidding-zone-errors.png',
    'daily-fuel-annual-2025/compact-zonal.json', 'daily-fuel-annual-2025/compact-zonal.png',
    'daily-fuel-annual-2025/performance.json',
    'daily-fuel-annual-2025/replay.json', 'daily-fuel-annual-2025/price-comparison.json',
    'daily-fuel-annual-2025/summary.json.gz', 'daily-fuel-annual-2025/germany-prices.png',
    'daily-fuel-annual-2025/monthly-errors.png', 'daily-fuel-annual-2025/zone-errors.png',
    'daily-fuel-annual-2025/zone-errors.csv',
    'daily-fuel-annual-2025/border-errors.csv',
    'daily-fuel-annual-2025/germany-hourly.csv.gz',
]


def check():
    folder = ROOT / 'public/research'
    comparison = json.loads((folder / 'dispatch-comparison-2025/summary.json').read_text())
    assert comparison['generation_reporting_areas'] == 38 and comparison['observed_price_zones'] == 41
    assert comparison['report_audit']['summary_sha256'] == comparison['derived_summary_sha256']
    assert comparison['report_audit']['maximum_hourly_allocation_difference_mw'] < 1e-6
    model = comparison.get('legacy_out_of_fold_model_verification') or comparison['model_verification']
    assert model['optimal_hours'] == 8760 and model['maximum_physical_residual_mw'] <= 1e-4
    assert model['maximum_duality_gap_eur'] < .05 and model['complete_lp_certificates'] == 11
    for role in ['producer', 'helper', 'auditor']:
        assert hashlib.sha256((ROOT / 'tools' / model[role + '_file']).read_bytes()).hexdigest() == model[role + '_sha256']
    assert comparison['article_sha256'] == hashlib.sha256((ROOT / 'docs/european-physical-synthetic-clearing-2025.md').read_bytes()).hexdigest()
    for file, sha in [('write_concise_dispatch_report_2025.py', comparison['renderer_sha256']),
                      (comparison.get('derived_producer_file', 'prepare_concise_dispatch_report_2025.py'), comparison['derived_producer_sha256']),
                      (comparison['report_audit'].get('auditor_file', 'audit_concise_dispatch_report_2025.py'), comparison['report_audit']['auditor_sha256'])]:
        assert hashlib.sha256((ROOT / 'tools' / file).read_bytes()).hexdigest() == sha
    direction = comparison['research_direction']
    assert direction['audit']['diagnosis_sha256'] == direction['diagnosis_sha256']
    assert direction['audit']['price_zones'] == 41 and direction['audit']['hours'] == 8760
    assert direction['mix_audit']['maximum_hourly_allocation_difference_mw'] < 1e-6
    for name, sha in [('diagnose_accepted_baseline_2025.py', direction['producer_sha256']),
                      ('audit_accepted_baseline_diagnosis_2025.py', direction['audit']['auditor_sha256']),
                      ('prepare_accepted_baseline_mix_2025.py', direction['mix_producer_sha256']),
                      ('audit_accepted_baseline_mix_2025.py', direction['mix_auditor_sha256'])]:
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha
    assert direction['plan_sha256'] == hashlib.sha256((ROOT / 'config/research-improvement-plan.json').read_bytes()).hexdigest()
    expected = {'overview.png', 'national-mix.png', 'daily-prices.png', 'zone-mae-grid.png', 'prices-by-zone.csv',
                'generation-by-area.csv', 'generation-by-fuel.csv', 'national-generation.csv'}
    if comparison.get('daily_fuel_evaluation'):
        daily = comparison['daily_fuel_evaluation']
        assert daily['audit']['summary_sha256'] == daily['summary_sha256']
        assert len(daily['audit']['certificates']) == 5
        assert all(c['hours']==8760 and c['original_physical_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in daily['audit']['certificates'])
        for file,sha in [('run_daily_fuel_dispatch_2025.py',daily['producer_sha256']),('audit_daily_fuel_dispatch_2025.py',daily['audit']['auditor_sha256']),('daily_fuel_inputs_2025.py',daily['inputs_producer_sha256'])]:
            assert hashlib.sha256((ROOT/'tools'/file).read_bytes()).hexdigest()==sha
        expected.add('daily-fuel-prices-by-zone.csv')
    if comparison.get('renewable_source_evaluation'):
        study=comparison['renewable_source_evaluation']
        assert study['audit']['summary_sha256']==study['summary_sha256']
        assert len(study['audit']['certificates'])==7
        assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in study['audit']['certificates'])
        for file,sha in [('run_renewable_source_bids_2025.py',study['producer_sha256']),('renewable_source_bids_2025.py',study['helper_sha256']),('audit_renewable_source_bids_2025.py',study['audit']['auditor_sha256'])]:
            assert hashlib.sha256((ROOT/'tools'/file).read_bytes()).hexdigest()==sha
        expected.update({'renewable-source-prices-by-zone.csv','renewable-capacity-audit.csv'})
    if comparison.get('nuclear_availability_evaluation'):
        study=comparison['nuclear_availability_evaluation']
        assert study['audit']['summary_sha256']==study['summary_sha256']
        assert len(study['audit']['certificates'])==4 and study['audit']['source_days']==365
        assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in study['audit']['certificates'])
        assert all(c['optimal_hours']==8760 and c['emergency_mwh']==0 for c in study['annuals'].values())
        for file,sha in [('run_nuclear_availability_2025.py',study['producer_sha256']),('nuclear_availability_2025.py',study['helper_sha256']),('audit_nuclear_availability_2025.py',study['audit']['auditor_sha256'])]:
            assert hashlib.sha256((ROOT/'tools'/file).read_bytes()).hexdigest()==sha
        expected.update({'nuclear-availability-prices-by-zone.csv','nuclear-availability-by-month.csv'})
    if comparison.get('inverse_bid_ensemble_evaluation'):
        study=comparison['inverse_bid_ensemble_evaluation']
        assert study['audit']['summary_sha256']==study['summary_sha256']
        assert study['audit']['members']==study['members'] and study['audit']['attempts']==12
        assert 1<=len(study['members'])<=5 and len(study['audit']['certificates'])==len(study['records'])<=13
        assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in study['audit']['certificates'])
        assert all(c['optimal_hours']==8760 and c['emergency_mwh']==0 for c in study['annuals'].values())
        for file,sha in [('run_inverse_bid_ensemble_2025.py',study['producer_sha256']),('inverse_bid_ensemble_2025.py',study['helper_sha256']),('audit_inverse_bid_ensemble_2025.py',study['audit']['auditor_sha256']),('bid_ensemble_report_2025.py',study['renderer_sha256'])]:
            assert hashlib.sha256((ROOT/'tools'/file).read_bytes()).hexdigest()==sha
        assert study['design']==json.loads((ROOT/'config/inverse-bid-ensemble-2025.json').read_text())
        report_audit=study['report_audit']
        assert report_audit['source_summary_sha256']==study['summary_sha256'] and report_audit['article_sha256']==comparison['article_sha256']
        assert report_audit['assets_sha256']==comparison['assets'] and report_audit['primary_members']==len(study['members'])
        assert hashlib.sha256((ROOT/'tools/audit_inverse_report_2025.py').read_bytes()).hexdigest()==report_audit['auditor_sha256']
        records={r['id']:r for r in study['records']};winner=records[study['winner']]
        assert study['winner']==study['audit']['winning_state']==study['members'][0]
        assert all(records[k]['eligible'] for k in study['members'])
        for row in study['cutoff_sensitivity']:
            count=sum(r['eligible'] and r['score']<=winner['score']+row['score_tolerance']+1e-12 and r['metrics']['price']<=winner['metrics']['price']+1+1e-12 for r in records.values())
            assert row['qualifying_states']==count and row['retained_cap']==min(5,count)

        expected.update({'inverse-search-cases.csv','inverse-prices-by-zone.csv','inverse-generation-by-country.csv'})
    if comparison.get('joint_network_evaluation'):
        study=comparison['joint_network_evaluation']
        assert study['audit']['summary_sha256']==study['summary_sha256']
        assert study['winner']==study['audit']['winner']
        assert len(study['records'])==len(study['audit']['certificates'])+len(study['audit']['rejected'])==16
        assert study['audit']['new_case_states']==14 and study['audit']['external_witnesses']==3
        assert all(c['hours']==8760 and c['native_modified_physics_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in study['audit']['certificates'])
        assert all(c['certificate']['separation_gap_mw']>1e-4 and c['certificate']['free_column_residual']<=1e-7 for c in study['audit']['rejected'])
        for file,sha in [('run_joint_network_calibration_2025.py',study['producer_sha256']),('joint_network_calibration_2025.py',study['helper_sha256']),('joint_network_clear_2025.py',study['clearer_sha256']),('audit_joint_network_calibration_2025.py',study['audit']['auditor_sha256']),('joint_network_report_2025.py',study['renderer_sha256'])]:
            assert hashlib.sha256((ROOT/'tools'/file).read_bytes()).hexdigest()==sha
        if study.get('repair_producer_sha256'):
            assert hashlib.sha256((ROOT/'tools/repair_joint_network_calibration_2025.py').read_bytes()).hexdigest()==study['repair_producer_sha256']
        assert study['design']==json.loads((ROOT/'config/joint-network-calibration-2025.json').read_text())
        r=study['report_audit']
        assert r['source_summary_sha256']==study['summary_sha256'] and r['article_sha256']==comparison['article_sha256'] and r['assets_sha256']==comparison['assets']
        assert hashlib.sha256((ROOT/'tools/audit_joint_report_2025.py').read_bytes()).hexdigest()==r['auditor_sha256']
        assert r['cases']==16 and r['zone_rows']==len(study['shown'])*48
        expected.update({'joint-search-cases.csv','joint-prices-by-zone.csv','joint-generation-by-country.csv'})
    assert set(comparison['assets']) == expected
    for file, sha in comparison['assets'].items():
        assert hashlib.sha256((folder / 'dispatch-comparison-2025' / file).read_bytes()).hexdigest() == sha
    files = [p for p in folder.rglob('*') if p.is_file()]
    hydrated = [p for p in files if str(p.relative_to(folder)) in FILES]
    for p in hydrated:
        assert p.read_bytes() == gzip.decompress(p.with_name(p.name + '.gz').read_bytes()), 'Changed hydrated metadata'
    files = [p for p in files if p not in hydrated]
    archived = {name: gzip.decompress((folder / (name + '.gz')).read_bytes()) for name in FILES}
    for raw in archived.values():
        assert isinstance(json.loads(raw), dict), 'Invalid archived JSON'
    daily = json.loads((folder / 'daily-fuel-annual-2025/replay.json').read_text())
    assert hashlib.sha256(archived['daily-fuel-annual-2025/summary.json']).hexdigest() == daily['summary_sha256'], 'Detached daily replay'
    performance = json.loads((folder / 'daily-fuel-annual-2025/performance.json').read_text())
    assert performance['reference_summary_sha256'] == daily['summary_sha256'], 'Detached performance baseline'
    assert performance['execution_driver_sha256'] == hashlib.sha256((ROOT / 'tools/fast_daily_market.py').read_bytes()).hexdigest(), 'Changed performance adapter'
    assert performance['coefficient_days_checked'] == 365 and len(performance['selected_days']) == 18
    for engine in performance['records']:
        assert all(row['attempts'][-1]['status'] == 'HighsModelStatus.kOptimal' for row in engine['days'])
    annual = performance['annual_validation']
    assert annual['hours'] == 8760 and annual['days'] == 365 and annual['preparation_arrays_identical']
    assert annual['execution_driver_sha256'] == performance['execution_driver_sha256']
    assert annual['replay']['closure_residual_mwh'] == 0 and annual['replay']['maximum_join_residual_mwh'] == 0
    assert annual['replay']['maximum_primal_residual'] <= 1e-4 and annual['simultaneous_storage_hours'] == 0
    compact = json.loads((folder / 'daily-fuel-annual-2025/compact-zonal.json').read_text())
    assert compact['hours'] == 8760 and compact['days'] == 365 and compact['window_statistics']['optimal_days'] == 365
    assert compact['source_summary_sha256'] == compact['replay']['summary_sha256'], 'Detached compact replay'
    assert compact['physics'] == compact['replay']['physics']
    assert compact['physics']['maximum_residual'] <= 1e-4 and compact['physics']['closure_mwh'] == 0
    assert compact['physics']['simultaneous_storage_hours'] == 0
    for name, sha in compact['provenance']['dependencies'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha, 'Changed compact calculation source'
    assert compact['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/report_compact_zonal_2025.py').read_bytes()).hexdigest()
    assert compact['image_sha256'] == hashlib.sha256((folder / 'daily-fuel-annual-2025/compact-zonal.png').read_bytes()).hexdigest()
    assert len(compact['native_checks']) == 3
    assert all(abs(row['objective_difference_eur']) <= max(.05, abs(row['native_objective_eur'])*1e-8) for row in compact['native_checks'])
    fixed = json.loads(archived['fixed-reservoir-screening-2025/summary.json'])['provenance']
    assert hashlib.sha256(archived['european-reservoir-clearing-2025/summary.json']).hexdigest() == fixed['annual_summary_sha256'], 'Detached hydro source'
    assert hashlib.sha256((folder / 'european-reservoir-clearing-2025/replay.json').read_bytes()).hexdigest() == fixed['water_replay_sha256'], 'Detached water replay'
    combined = json.loads((folder / 'fixed-reservoir-screening-2025/resource-bids.json').read_text())
    assert combined['hours'] == 8760 and set(combined['cases']) == {'resource_bids'}
    assert combined['source_summary_sha256'] == combined['replay']['summary_sha256'], 'Detached combined replay'
    assert combined['provenance']['reference_summary_sha256'] == hashlib.sha256(archived['fixed-reservoir-screening-2025/summary.json']).hexdigest(), 'Detached fixed reference'
    assert combined['water_residual_mwh'] <= 1e-4
    for variant, record in combined['cases'].items():
        assert record['optimal_hours'] == 8760 and record['physics'] == combined['replay']['cases'][variant]
        assert record['maximum_live_residual_mw'] <= 1e-4 and record['physics']['maximum_residual_mw'] <= 1e-4
        assert len(record['native_checks']) == 3
        assert all(abs(row['difference_eur']) <= max(.05, abs(row['native_objective_eur'])*1e-8) for row in record['native_checks'])
    for name, sha in combined['provenance']['dependencies'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha, 'Changed combined calculation source'
    assert combined['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/evaluate_fixed_hydro_bids_2025.py').read_bytes()).hexdigest()
    for name, sha in combined['images'].items():
        assert hashlib.sha256((folder / 'fixed-reservoir-screening-2025' / name).read_bytes()).hexdigest() == sha, 'Changed combined figure'
    assert len(combined['diagnostics']['ranked_errors']) == 39 and len(combined['german_offer_examples']) == 3
    diagnosis = combined['diagnostics']
    assert diagnosis['annual_summary_sha256'] == combined['source_summary_sha256']
    assert diagnosis['producer_sha256'] == hashlib.sha256((ROOT / 'tools/diagnose_fixed_hydro_errors_2025.py').read_bytes()).hexdigest()
    assert diagnosis['annual_witness_sha256'] == combined['cases']['resource_bids']['witness_sha256']
    assert len(diagnosis['norway']['price_interval_probes']) == diagnosis['norway']['high_price_hours']
    for row in diagnosis['capacity_and_energy']:
        assert row['ember_month_counts']['Hydro'] == 12 and row['ember_month_counts']['Demand'] == 12
        assert row['model_total_hydro_bounds_twh'][0] <= row['model_total_hydro_bounds_twh'][1]+1e-6
    update_path = folder / 'fixed-reservoir-screening-2025/nve-water-update.json'
    if update_path.exists():
        update = json.loads(update_path.read_text()); s = update['summary']; a = update['audit']
        assert update['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/report_nve_hydro_update_2025.py').read_bytes()).hexdigest()
        assert update['image_sha256'] == hashlib.sha256(update_path.with_suffix('.png').read_bytes()).hexdigest()
        assert a['audit_producer_sha256'] == hashlib.sha256((ROOT / 'tools/audit_nve_hydro_model_2025.py').read_bytes()).hexdigest()
        for name, sha in s['new_sources'].items():
            assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha
        assert s['optimal_hours'] == 8760 and a['physics'] == s['physics']
        assert a['water_maximum_residual_mwh'] <= 1e-4 and a['physics']['maximum_residual_mw'] <= 1e-4
        assert s['water_native']['status'] == 'optimal' and s['water_native']['hours'] == 48
        assert len(s['native_checks']) == 3
        assert all(abs(v['difference_eur']) <= max(.05, abs(v['native_objective_eur'])*1e-8) for v in s['native_checks'])
        assert sum(v['updated']['known_hours'] > 0 for v in a['observed_price_comparisons']) == 39
    diagnostic_path = folder / 'fixed-reservoir-screening-2025/nve-hydro-diagnostics.json'
    if diagnostic_path.exists():
        d = json.loads(diagnostic_path.read_text())
        assert d['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/report_nve_hydro_diagnostics_2025.py').read_bytes()).hexdigest()
        assert d['audit']['audit_producer_sha256'] == hashlib.sha256((ROOT / 'tools/audit_nve_hydro_diagnostics_2025.py').read_bytes()).hexdigest()
        for key, producer in [('annual', 'run_nve_bus_geography_2025.py'), ('windows', 'run_nve_hydro_windows_2025.py'), ('points', 'diagnose_nve_hydro_prices_2025.py')]:
            assert d[key]['producer_sha256'] == hashlib.sha256((ROOT / 'tools' / producer).read_bytes()).hexdigest()
            assert d[key]['helper_sha256'] == hashlib.sha256((ROOT / 'tools/nve_hydro_diagnostics.py').read_bytes()).hexdigest()
        assert d['windows']['flexibility_sha256'] == hashlib.sha256((ROOT / 'tools/nve_hydro_flexibility.py').read_bytes()).hexdigest()
        assert d['annual']['optimal_hours'] == 8760 and d['annual']['physics']['emergency_mwh'] == 0
        assert d['audit']['annual_network_residual_mw'] <= 1e-4
        assert d['audit']['annual_water_residual_mwh'] <= 1e-4
        assert len(d['audit']['windows']) == 6
        assert all(r['network_residual_mw'] <= 1e-4 and r['water_bounds_energy_residual_mwh'] <= 1e-4 for r in d['audit']['windows'])
        for name, sha in d['images'].items():
            assert hashlib.sha256((diagnostic_path.parent / name).read_bytes()).hexdigest() == sha
    zonal_path = folder / 'fixed-reservoir-screening-2025/bidding-zone-model.json'
    if zonal_path.exists():
        z = json.loads(zonal_path.read_text()); s = z['summary']; a = z['audit']
        assert z['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/report_bidding_zone_network_2025.py').read_bytes()).hexdigest()
        assert z['image_sha256'] == hashlib.sha256(zonal_path.with_name('bidding-zone-errors.png').read_bytes()).hexdigest()
        assert a['audit_producer_sha256'] == hashlib.sha256((ROOT / 'tools/audit_bidding_zone_network_2025.py').read_bytes()).hexdigest()
        assert s['producer_sha256'] == hashlib.sha256((ROOT / 'tools/run_bidding_zone_network_2025.py').read_bytes()).hexdigest()
        assert s['compiler_sha256'] == hashlib.sha256((ROOT / 'tools/bidding_zone_network_2025.py').read_bytes()).hexdigest()
        assert z['source_collection_producer_sha256'] == hashlib.sha256((ROOT / 'tools/collect_bidding_zone_sources_2025.py').read_bytes()).hexdigest()
        for name, sha in s['dependencies'].items():
            assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha
        assert a['maximum_parent_available_supply_change_mw'] < 1e-6
        assert a['maximum_hourly_demand_change_mw'] < 1e-6 and a['maximum_fixed_hydro_change_mw'] < 1e-6
        for key, r in a['cases'].items():
            assert r['optimal_hours'] == s['cases'][key]['optimal_hours']
            assert r['maximum_component_residual_mw'] <= 1e-4
            assert r['optimal_hours'] + len(s['cases'][key]['failures']) == 8760
            assert len(s['cases'][key]['native_checks']) == 3
            assert all(abs(v['objective_difference_eur']) <= max(.05,abs(v['native_objective_eur'])*1e-8) for v in s['cases'][key]['native_checks'])
    carbon = json.loads((folder / 'carbon-spreads-2025.json').read_text())
    assert carbon['year'] == 2025 and len(carbon['borders']) == 68
    assert carbon['metric_sha256'] == hashlib.sha256((ROOT / 'src/lib/carbon-spread.ts').read_bytes()).hexdigest(), 'Changed carbon metric'
    for zone, digest in carbon['price_sha256'].items():
        assert hashlib.sha256((folder / 'zone-prices-2025' / (zone + '.json')).read_bytes()).hexdigest() == digest, 'Changed carbon price selection'
    unexpected = [str(p.relative_to(folder)) for p in files
                  if not any(fnmatch.fnmatch(str(p.relative_to(folder)), pattern) for pattern in ALLOWED)]
    if unexpected:
        raise ValueError('Unapproved public intermediate assets: ' + ', '.join(unexpected))
    print(f'Public assets: {len(files)} files; {sum(p.stat().st_size for p in files)/1024**2:.2f} MiB; allowlist passed')


if __name__ == '__main__':
    check()
