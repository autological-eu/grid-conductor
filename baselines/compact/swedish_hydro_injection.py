"""Water-infeasible Swedish hydro injection sensitivity, never a baseline candidate.

Reported B12 reservoir generation replaces the retained national fixed schedule,
clipped at the raw model turbine fleet. National changes are distributed across
the five existing source units in proportion to nameplate power. This is an
explicit price response diagnostic; it does not reconstruct unit water stocks.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .evaluation import physical_lp, saved_annual
from .lp import clear_hour, solver
from .nordic_storage import ORIGINAL, physical_basis, sha, sources
from .source import ROOT, grouped_fit_inputs

OUTPUT = ROOT / 'data/bidding-zone-network-2025/swedish-hydro-injection-v1'


def run(output=OUTPUT):
    output = Path(output)
    if (output / 'summary.json').exists() or (output / 'prices.npz').exists():
        raise FileExistsError('Existing Swedish injection diagnostic; use a fresh output path')
    schema, data, _ = grouped_fit_inputs()
    model = physical_lp()
    costs, baseline = saved_annual()
    native, original, _, _, allocation = sources()
    hydro = original.storage_units.query("carrier == 'hydro'")
    swedish = hydro.loc[hydro.bus.map(original.buses.country) == 'SE']
    if len(swedish) != 5 or not swedish.cyclic_state_of_charge.all():
        raise ValueError('Swedish source hydro fleet changed')
    country = next(group['country_id'] for group in schema['groups'] if group['country'] == 'SE')
    tech = schema['technologies'].index('reservoir')
    observed = data['observed_generation'][:, country, tech]
    fixed = data['fixed_generation'][:, country, tech]
    if not np.isfinite(observed).all() or not np.isfinite(fixed).all():
        raise ValueError('Swedish hourly generation is incomplete')
    nameplate = swedish.p_nom.to_numpy()
    shares = nameplate / nameplate.sum()
    capped = np.minimum(observed, nameplate.sum())
    delta = (capped - fixed)[:, None] * shares[None, :]
    zone_share, branch = physical_basis(native, swedish, allocation, model['zones'])
    if branch.shape != (5, 255) or abs(zone_share.sum(axis=1) - 1).max() > 1e-10:
        raise ValueError('Swedish injection basis changed')
    changed = model | dict(load=model['load'] - delta @ zone_share,
                           flow=model['flow'] + delta @ branch)
    highs = solver(changed, costs)
    price = np.full((8760, model['nz']), np.nan)
    shortage = np.full(8760, np.nan)
    residual = np.full(8760, np.nan)
    infeasible = []
    for hour in range(8760):
        try:
            values, duals, _, error = clear_hour(highs, changed, costs, hour)
        except RuntimeError as exc:
            if 'Infeasible' not in str(exc):
                raise
            infeasible.append(hour)
            continue
        price[hour] = duals[:model['nz']]
        shortage[hour] = values[:model['ng']][model['emergency_mask']].sum()
        residual[hour] = error
        if hour % 2000 == 0:
            print(f'Cleared through hour {hour}', flush=True)
    valid = np.isfinite(price).all(axis=1)
    observed_price = data['observed_prices']
    baseline_price = baseline['row_duals'][:, :model['nz']]
    zones = model['zones']
    zone_metrics = {}
    for zone in ['NO1', 'NO2', 'NO3', 'NO4', 'NO5', 'SE1', 'SE2', 'SE3', 'SE4']:
        index = zones.index(zone)
        covered = valid & np.isfinite(observed_price[:, index])
        zone_metrics[zone] = dict(covered_hours=int(covered.sum()),
            baseline_mae_eur_mwh=float(abs(baseline_price[covered, index] - observed_price[covered, index]).mean()) if covered.any() else None,
            injection_mae_eur_mwh=float(abs(price[covered, index] - observed_price[covered, index]).mean()) if covered.any() else None,
            baseline_bias_eur_mwh=float((baseline_price[covered, index] - observed_price[covered, index]).mean()) if covered.any() else None,
            injection_bias_eur_mwh=float((price[covered, index] - observed_price[covered, index]).mean()) if covered.any() else None)
    efficiency = swedish.efficiency_dispatch.to_numpy()
    inflow = original.storage_units_t.inflow[swedish.index].to_numpy()
    annual_sustainable_mwh = float((inflow * efficiency[None, :]).sum())
    result = dict(status='water_infeasible_price_sensitivity_only',
        model='retained_mixed_curve_fitting_799_offer_lp_frozen_bids',
        source='ENTSO-E B12 national generation target from retained grouped fit inputs',
        allocation='Swedish national delta to five source units by p_nom; physical bus shares retained',
        observed_reservoir_twh=float(observed.sum() / 1e6),
        fixed_reservoir_twh=float(fixed.sum() / 1e6),
        capped_target_twh=float(capped.sum() / 1e6),
        cap_exceedance_hours=int((observed > nameplate.sum() + 1e-6).sum()),
        clipped_energy_twh=float((observed - capped).sum() / 1e6),
        turbine_capacity_gw=float(nameplate.sum() / 1000),
        original_annual_inflow_twh=float(inflow.sum() / 1e6),
        cyclic_annual_sustainable_upper_twh=annual_sustainable_mwh / 1e6,
        capped_target_excess_over_sustainable_twh=float((capped.sum() - annual_sustainable_mwh) / 1e6),
        lp_feasible_hours=int(valid.sum()), lp_infeasible_hours=len(infeasible),
        infeasible_hour_indices=infeasible,
        emergency_hours=int(np.count_nonzero(shortage[valid] > 1e-5)),
        emergency_mwh=float(np.nansum(shortage)),
        maximum_primal_residual_mw=float(np.nanmax(residual)) if valid.any() else None,
        zone_metrics_on_feasible_hours_only=zone_metrics,
        limitations=['Observed country B12 category is not a verified per-unit dispatch schedule',
                     'Reported target is clipped at source fleet power and still violates annual cyclic water budget',
                     'No Swedish unit-level stock or spill chronology is reconstructed',
                     'Feasible-hour price scores are selected subsets, not annual benchmark scores'],
        source_sha256={'raw_pypsa_grid': sha(ORIGINAL),
                       'grouped_fit_inputs': sha(ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz')})
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / 'prices.npz', prices=price, shortage=shortage,
                        feasible=valid, capped_generation=capped)
    result['price_witness_sha256'] = sha(output / 'prices.npz')
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
