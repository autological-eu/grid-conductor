"""Compare sealed Swedish hydro geography control with independently audited observations."""
import json
from pathlib import Path

import numpy as np

import run_independent_hourly_transport_2025 as parent
from run_network_stock_retiming_2025 import read
from sigmoid_month_pairs_2025 import ROOT, digest
from run_differentiable_spline_2025 import atomic_json

OBS = ROOT / 'data/bidding-zone-source-audit-2025/nordic-zonal-hydro-comparison-v1'
CASE = ROOT / 'data/bidding-zone-network-2025/sweden-static-hydro-allocation-v2'


def run():
    observation = json.loads((OBS / 'summary.json').read_text())
    for relative, expected in observation['sources'].items():
        assert digest(ROOT / relative) == expected, relative
    market_audit = json.loads((CASE / 'audit.json').read_text())
    assert market_audit['status'] == 'completed_independent_replay_including_failed_cases'
    assert digest(CASE / 'summary.json') == market_audit['summary_sha256']
    observed = np.load(OBS / 'hourly.npz')
    base, (state, _, _, _) = parent.setup()
    schema = state[0]
    inputs = read(CASE / 'inputs.npz')
    water = read(CASE / 'maxBorderFlow-water.npz')
    fixed = np.einsum('tzc,tc->tz', inputs['shares'], water['power'])
    rows = []
    for month in (1, 2):
        dispatch = read(CASE / f'maxBorderFlow-{month:02d}.npz')
        hours = dispatch['hours']
        quantities = dispatch['quantities_gw'] * 1000
        for zone in ('SE1', 'SE2', 'NO4'):
            obs_zone = list(observed['zones']).index(zone)
            model_zone = schema['zones'].index(zone)
            ror = [i for i, group in enumerate(schema['groups'])
                   if group['zone'] == zone and group['technology'] == 'ror']
            model = fixed[hours, model_zone] + quantities[:, ror].sum(axis=1)
            reported = observed['reported_hydro_mwh'][hours, obs_zone]
            known = np.isfinite(reported)
            model, reported = model[known], reported[known]
            assert len(model) == len(hours)
            rows.append(dict(month=month, zone=zone,
                             model_twh=float(model.sum()/1e6),
                             reported_twh=float(reported.sum()/1e6),
                             hourly_mae_mw=float(np.mean(abs(model-reported))),
                             shape_correlation=float(np.corrcoef(model,reported)[0,1])))
    atomic_json(CASE / 'observed-hydro-audit.json', dict(
        status='saved_control_compared_to_source_audited_observations', rows=rows,
        source_sha256={str(path.relative_to(ROOT)): digest(path) for path in
                       (OBS/'summary.json', OBS/'hourly.npz', CASE/'audit.json',
                        CASE/'inputs.npz', CASE/'maxBorderFlow-water.npz',
                        CASE/'maxBorderFlow-01.npz', CASE/'maxBorderFlow-02.npz')},
        limitations=['Reported generation validates the control; it is never availability.',
                     'Reported SE hydro category and model reservoir/ROR split are not identical.']))
    print(json.dumps(rows))


if __name__ == '__main__':
    run()
