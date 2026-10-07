"""Publish a German reported-gas consistency diagnostic, never acceptance."""
import argparse
import json
import math
from pathlib import Path
from audit_smard_2025_gas import audit
from summarize_native_generation_eager import summarize
from monthly_dispatch import digest, save


def compare(reference, observed, native):
    if reference['year'] != 2025 or reference['observed_hours'] != 8760 or native['hours'] != 8760:
        raise ValueError('Complete exact-year reference required')
    zone = next(z for z in observed['zones'] if z['zone'] == 'DE-LU')
    country = next(c for c in native['countries'] if c['country'] == 'DE')
    if any([m['month'] for m in rows] != list(range(1, 13)) for rows in [reference['monthly'], zone['monthly'], country['monthly']]):
        raise ValueError('Ordered UTC months required')
    rows = []
    for ref, obs, model in zip(reference['monthly'], zone['monthly'], country['monthly']):
        gas = obs['by_reported_type']['B04']
        if (obs['status'] != 'raw_interval_energy_replayed' or gas['observed_hours'] != obs['expected_hours']
                or ref['observed_hours'] != ref['expected_hours'] or obs['expected_hours'] != ref['expected_hours']):
            raise ValueError('Complete reported gas hours required; no extrapolation')
        mix = model['primary_generation_mwh_by_model_carrier']
        if not all(k in mix for k in ['CCGT', 'OCGT']):
            raise ValueError('Explicit native gas-carrier quantities required')
        values = [ref['complete_reported_energy_mwh'], gas['reported_energy_mwh'], math.fsum(mix[k] for k in ['CCGT', 'OCGT'])]
        if any(type(v) not in [int, float] or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('Finite nonnegative gas quantities required')
        rows.append(dict(month=ref['month'], hours=ref['expected_hours'], smard_mwh=values[0], entsoe_reported_mwh=values[1],
                         native_ccgt_ocgt_mwh=values[2], smard_minus_entsoe_mwh=values[0]-values[1]))
    annual = {k: math.fsum(row[k] for row in rows) for k in ['smard_mwh', 'entsoe_reported_mwh', 'native_ccgt_ocgt_mwh']}
    annual['smard_minus_entsoe_mwh'] = annual['smard_mwh']-annual['entsoe_reported_mwh']
    return dict(monthly=rows, annual=annual)


def run(args):
    ref = audit(args.cache)
    observed = json.loads(args.observed.read_text())
    tools = Path(__file__).parent
    if (observed['status'] != 'raw_generation_observations_replayed_not_model_validation' or observed['year'] != 2025
            or observed['producer_sha256'] != digest(tools/'audit_2025_generation_observations.py')):
        raise ValueError('Audited original observed-generation producer required')
    for name, value in observed['dependencies'].items():
        if digest(tools/name) != value:
            raise ValueError('Observed-generation audit changed')
    native = summarize(args.mapping)
    result = compare(ref, observed, native)
    result.update(status='german_gas_reported_consistency_and_conditional_dispatch_diagnostic_not_validation', year=2025,
                  hours=8760, unit='MWh', input_sha256=native['input_sha256'], annual_replay_sha256=native['annual_replay_sha256'],
                  mapping_calendar_sha256=native['mapping_calendar_sha256'], observations_audit_sha256=digest(args.observed),
                  smard_reference=ref, producer_sha256=digest(Path(__file__)),
                  dependencies={name:digest(tools/name) for name in ['audit_smard_2025_gas.py','summarize_native_generation_eager.py','audit_2025_generation_observations.py','monthly_dispatch.py']},
                  acceptance=dict(annual_optimum=False, empirical_validation=False, investment_validation=False),
                  limitations=['Feasible candidate 006 fixed-inventory dispatch, not converged annual optimum.',
                               'Reported German feed-in is not whole-fleet gross generation or verified mainland model scope.',
                               'ENTSO-E DE-LU generation artifact uses German national proxy excluding Luxembourg.',
                               'SMARD and ENTSO-E may share TSO observations; agreement is consistency, not independent measurement.',
                               'SMARD hourly source-label/energy interpretation follows documented filter; full provider-method audit remains open.',
                               'Native gas covers CCGT/OCGT; fleet taxonomy, CHP, outages, fuel and policy costs remain unreconciled.',
                               'No price fitting, generation-as-availability, lifecycle intensity, avoided emissions or investment benefit inferred.'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['cache', 'observed', 'mapping', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve prior diagnostic')
    save(args.output, run(args))
    print('Replayed UTC German gas diagnostic; all acceptance gates remain false.')
