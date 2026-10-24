"""Real-European physical transfer probe before patience training starts."""
import json
from pathlib import Path
import numpy as np
import run_fast_fit_physical_transfer_2025 as study
from transport_curve_physical_transfer_2025 import clear
from sigmoid_month_pairs_2025 import ROOT, digest
from run_differentiable_spline_2025 import atomic_json


def run():
    study.OUT.mkdir(exist_ok=True)
    base = study.setup_controller()
    state, market, _, _ = base.setup()
    theta = np.load(study.PARENT/'iteration-003/shared-parameters.npy')
    hours = np.array([15,111,318,567,759,815,900])
    records = []
    for bins in [20,100]:
        witness, info = clear(state, market, theta, hours, bins=bins)
        path = study.OUT/f'physical-pilot-{bins}.npz'
        base.save(path, **witness)
        records.append(dict(bins=bins, info=info, witness_sha256=digest(path)))
    paths = [Path(__file__), ROOT/'tools/transport_curve_physical_transfer_2025.py',
             ROOT/'tools/run_fast_fit_physical_transfer_2025.py',
             ROOT/'tools/test_transport_curve_transfer_2025.py', study.PLAN]
    result = dict(status='passed', hours=hours.tolist(), zones=48, cases=records,
                  parameter_sha256=digest(study.PARENT/'iteration-003/shared-parameters.npy'),
                  sources={str(p.relative_to(ROOT)):digest(p) for p in paths})
    atomic_json(study.OUT/'physical-pilot.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    run()
