"""Publish compact, source-hash-checked results from the ten saved 2025 LP replays."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.run_scenario import OUT
from baselines.compact.source import digest

receipt = json.loads((ROOT / 'research/data/compact-scenario-pilot-2025.json').read_text())
plan = json.loads((OUT / 'plan.json').read_text())
if digest(OUT / 'plan.json') != receipt['plan_sha256']:
    raise ValueError('Pilot plan hash changed')
model = physical_lp()
_, baseline = saved_annual()
if digest(ROOT / 'data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1/annual.npz') != receipt['baseline_witness_sha256']:
    raise ValueError('Baseline witness hash changed')
zones = list(map(str, model['zones']))
rows = []
for entry, check in zip(plan['scenarios'], receipt['scenarios'], strict=True):
    name = entry['name']
    if name != check['name']:
        raise ValueError('Pilot order changed')
    folder = OUT / name
    if digest(folder / 'summary.json') != check['summary_sha256'] or digest(folder / 'annual.npz') != check['witness_sha256']:
        raise ValueError(f'{name}: scenario evidence changed')
    summary = json.loads((folder / 'summary.json').read_text())
    if summary['optimal_hours'] != 8760 or summary['emergency_mwh'] != 0 or summary['maximum_primal_residual_mw'] > 1e-4:
        raise ValueError(f'{name}: numerical gate failed')
    with np.load(folder / 'annual.npz') as archive:
        prices = archive['row_duals'][:, :model['nz']]
        objective = archive['objectives']
    delta = prices - baseline['row_duals'][:, :model['nz']]
    focus = 'DE-LU' if entry['kind'] == 'generator' else 'NO2'
    i = zones.index(focus)
    if entry['kind'] == 'generator' and np.any(delta[:, i] > 1e-5):
        raise ValueError(f'{name}: added zero-bid generator raised host-zone price')
    if np.any(objective > baseline['objectives'] + .01):
        raise ValueError(f'{name}: objective increased')
    row = dict(name=name, kind=entry['kind'], focus_zone=focus,
               witness_sha256=check['witness_sha256'],
               model_offer_cost_reduction_meur=check['model_offer_cost_reduction_meur'],
               focus_price_mean_change_eur_mwh=float(delta[:, i].mean()),
               focus_price_up_hours=int(np.sum(delta[:, i] > 1e-5)),
               focus_price_down_hours=int(np.sum(delta[:, i] < -1e-5)),
               generator_income_meur=check['added_generator_income_meur'][0] if check['added_generator_income_meur'] else None,
               link_signed_rent_meur=check['link_signed_rent_meur'][0] if check['link_signed_rent_meur'] else None)
    row.update({key: entry[key] for key in ('zone', 'technology', 'capacity_mw', 'from_zone', 'to_zone', 'factor') if key in entry})
    rows.append(row)
out = dict(status='saved_research_pilot_not_general_scenario_estimator', year=2025,
           baseline='mixed_curve_fitting', zones=48, hours=8760,
           plan_sha256=receipt['plan_sha256'],
           baseline_witness_sha256=receipt['baseline_witness_sha256'],
           source_receipt='research/data/compact-scenario-pilot-2025.json',
           limitations='In-sample fitted offers, fixed hydro, and a proxy released exchange envelope for link cases. No battery case or arbitrary browser solve. Offer-cost reduction is not verified investment value.',
           scenarios=rows)
path = ROOT / 'public/research/network-scenario-pilot-2025.json'
path.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
print(path, path.stat().st_size)
