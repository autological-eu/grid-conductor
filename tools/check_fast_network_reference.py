"""Generate analytical browser parity cases using the existing SciPy reference.

Fixtures are test-only, never published as European research data.
Run explicitly after changing the formulation; inspect diffs before accepting.
"""
import copy
import json
from pathlib import Path
import scipy
from market_model import dispatch

root = Path(__file__).resolve().parents[1]
base = json.loads((root / 'tests/fixtures/network.json').read_text())
cases = [base]
coupled = copy.deepcopy(base)
coupled['generators'][0].update(energy_budget_mwh=20, ramp_mw_per_hour=5, max_mw=[0, 200])
cases.append(coupled)
storage = copy.deepcopy(base)
storage.update(edges=[], load_mw={'A': [0, 100], 'B': [0, 0]},
    generators=[dict(id='g', zone='A', max_mw=[200, 200], cost_eur_mwh=10, co2_t_per_mwh=1)],
    storage=[dict(id='s', zone='A', power_mw=100, energy_mwh=100, initial_mwh=20,
        terminal_mwh=20, charge_efficiency=.9, discharge_efficiency=.9, throughput_cost_eur_mwh=1)])
cases.append(storage)
regional = copy.deepcopy(base)
regional.update(edges=[], flow_based_regions=[dict(id='r', zones=['A', 'B'], constraints=[
    dict(id=f'r{t}', interval=t, ptdf={'A': 1, 'B': 0}, ram_mw=20) for t in range(2)])])
cases.append(regional)
result = dict(reference='tools/market_model.py linked-dispatch-v1', scipy_version=scipy.__version__,
    cases=[dict(input=d, expected=dispatch(d)) for d in cases])
(root / 'tests/fixtures/network-reference.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
print(f'Generated {len(cases)} analytical cases with SciPy {scipy.__version__}')
