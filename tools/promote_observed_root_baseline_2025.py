"""Adopt the audited 20-update monthly bids as the research baseline.

The prior manifest is preserved byte-for-byte. This is a research-pointer
change, not a static-app integration or an independent forecast validation.
"""
import json
from pathlib import Path

from generation_mix_2025 import ROOT, digest
from solar_country_fit_2025 import write


ACTIVE = ROOT / 'config/active-research-baseline.json'
ARCHIVE = ROOT / 'config/research-baseline-solar-anchor-2025.json'
FIT = ROOT / 'data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1'
LP = ROOT / 'data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1'


def main():
    old = json.loads(ACTIVE.read_text())
    if (old['model'], old['annual_case']) != ('solar-anchor-bids-v1', 'resource_full'):
        raise ValueError('Active research baseline has changed')
    if ARCHIVE.exists() and ARCHIVE.read_bytes() != ACTIVE.read_bytes():
        raise ValueError('Historical baseline archive differs')
    fa = json.loads((FIT / 'audit.json').read_text())
    la = json.loads((LP / 'audit.json').read_text())
    ls = json.loads((LP / 'summary.json').read_text())
    inputs = json.loads((LP / 'inputs.json').read_text())
    if fa['status'] != 'replayed' or fa['months'] != 12 or fa['price_cells'] != 359160:
        raise ValueError('Incomplete independent monthly replay')
    if la['status'] != 'full_8760_original_lp_replay_passed':
        raise ValueError('Independent LP audit incomplete')
    if ls['status'] != 'annual_lp_completed_pending_independent_audit':
        raise ValueError('Annual LP summary incomplete')
    if la['fit_audit_sha256'] != digest(FIT / 'audit.json') or \
            la['inputs_sha256'] != digest(LP / 'inputs.json') or \
            la['witness_sha256'] != digest(LP / 'annual.npz') or \
            ls['witness_sha256'] != digest(LP / 'annual.npz'):
        raise ValueError('Changed audit inputs or annual witness')
    if inputs['solar_availability_mismatch']['annual_absolute_twh'] != 0:
        raise ValueError('Solar fitting/LP mismatch')
    if ls['market']['hours'] != 8760 or ls['market']['optimal_hours'] != 8760 or \
            not ls['market']['complete_year'] or ls['market']['failures']:
        raise ValueError('Annual chronology/optimality gate failed')
    if la['emergency_mwh'] != 0 or any(la['numerical'][k] >= 1e-4 for k in
            ('primal_mw', 'duality_gap_maximum_eur', 'complementarity_maximum_eur')):
        raise ValueError('Annual feasibility/numerical gate failed')
    if not la['price_mae'] < la['baseline_price_mae'] or \
            not la['hourly_generation']['generation_mae_gw'] < la['baseline_hourly_generation']['generation_mae_gw'] or \
            not la['hourly_generation']['mix_share_mae'] < la['baseline_hourly_generation']['mix_share_mae']:
        raise ValueError('Matched price or generation comparison failed')
    if abs(la['baseline_price_mae'] - old['prices']['equal_zone_mae']) > 1e-9:
        raise ValueError('Historical comparison changed')
    expected = []
    for month in range(1, 13):
        folder = FIT / f'month-{month:02d}'
        summary = json.loads((folder / 'summary.json').read_text())
        history = json.loads((folder / 'history.json').read_text())
        if summary['updates'] != 20 or summary['rate'] != 1. or len(history) != 21 or \
                summary['curves_sha256'] != digest(folder / 'curves.npz') or \
                summary['final']['all_price_cells'] != fa['records'][month - 1]['price_cells']:
            raise ValueError(f'Changed or incomplete fit month {month}')
        if any(row['certificate']['emergency_mwh'] != 0 or
               row.get('gradient_identification', {}).get('unidentified_rhs_max', 0) > 1e-8
               for row in history):
            raise ValueError(f'Uncertified fit month {month}')
        expected += [folder / 'curves.npz', folder / 'summary.json']
    expected += [FIT / 'inputs.json', FIT / 'audit.json', FIT / 'flow-metadata.json',
                 LP / 'inputs.json', LP / 'costs.npz', LP / 'annual.npz',
                 LP / 'summary.json', LP / 'audit.json',
                 ROOT / 'data/price-trace/sdac-hourly-2025-v1/prices.npz']
    artifacts = {str(path.relative_to(ROOT)): digest(path) for path in expected}
    manifest = dict(model='monthly-fitted-bids-v1', annual_case='observed-root-fast-joint-lp',
        decision_date='2026-10-29', role='user-accepted in-sample research baseline',
        evaluation='2025 full-year same-year reconstruction against corrected hourly ENTSO-E SDAC; no independent forecast validation',
        fit_root=str(FIT.relative_to(ROOT)), summary_path=str((LP / 'summary.json').relative_to(ROOT)),
        audit_path=str((LP / 'audit.json').relative_to(ROOT)),
        inputs_path=str((LP / 'inputs.json').relative_to(ROOT)),
        witness=dict(witness=str((LP / 'annual.npz').relative_to(ROOT)),
            witness_sha256=digest(LP / 'annual.npz'), hours=8760,
            optimal_hours=8760, complete_year=True, failures=[],
            clearing_seconds=ls['market']['clearing_seconds'], reused=False),
        prices=dict(equal_zone_mae=la['price_mae'], complete_zones=41,
            modeled_zones=48, hours=8760, baseline_mae=la['baseline_price_mae'],
            zones_improved=la['zones_improved']),
        generation=la['hourly_generation'] | dict(
            baseline_hourly_mae_gw=la['baseline_hourly_generation']['generation_mae_gw'],
            monthly_mae_twh=la['generation_monthly_mae_twh'],
            baseline_monthly_mae_twh=la['baseline_generation_monthly_mae_twh'],
            mixed_offer_dispatch_twh=la['mixed_offer_dispatch_twh'],
            mixed_zero_member_fallback_twh=la['mixed_zero_member_fallback_twh']),
        decision=dict(user_requested_replacement=True,
            same_month_price_conditioned_roots=True,
            training_excluded_price_cells=3,
            independent_annual_lp_replay_passed=True,
            out_of_sample_validation=False,
            note='Accepted as a retrospective research baseline on matched annual price/generation and physical LP evidence. No forecast or investment-response claim.'),
        artifacts=artifacts,
        historical_baseline_manifest=str(ARCHIVE.relative_to(ROOT)),
        public_explorer_updated=False, browser_integration=False,
        recurring_reviews_enabled=False)
    if not ARCHIVE.exists():
        ARCHIVE.write_bytes(ACTIVE.read_bytes())
    write(ACTIVE, manifest)
    print('PROMOTED', manifest['model'], manifest['prices']['equal_zone_mae'])


if __name__ == '__main__':
    main()
