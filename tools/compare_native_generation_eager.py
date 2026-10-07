"""Versioned observation comparison for eager per-block generation accounting.

Uses the original reported-category comparison equations, preserving unknown
scopes and quantities. Does not alter frozen original publications.

Compare fixed-inventory model generation with reported national quantities.

Unreconciled coverage/geographic scopes remain visible. No validation gate,
calibration, missing-category zero, partial-year annualisation or carbon factor.
"""
import argparse,json
from pathlib import Path
from monthly_dispatch import digest,save

from compare_native_generation_observations import compare


def audit(a):
    native=json.loads(a.native.read_text());observed=json.loads(a.observed.read_text())
    tools=Path(__file__).parent
    if native['producer_sha256']!=digest(tools/'summarize_native_generation_eager.py') or observed['producer_sha256']!=digest(tools/'audit_2025_generation_observations.py'):
        raise ValueError('Observation or native-accounting producer changed')
    for record in (native,observed):
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Observation or accounting implementation changed')
    result=dict(status='fixed_inventory_generation_observation_diagnostic_not_validation',year=2025,
        input_sha256=native['input_sha256'],native_accounting_sha256=digest(a.native),observations_audit_sha256=digest(a.observed),
        producer_sha256=digest(Path(__file__)),
        dependencies={name:digest(tools/name) for name in ['compare_native_generation_observations.py','summarize_native_generation_eager.py','audit_2025_generation_observations.py','monthly_dispatch.py']},
        comparisons=compare(native,observed),
        limitations=['Not a converged annual optimum, calibration or validated market simulation.',
            'Country/model-mainland scopes and reported whole-fleet coverage remain unreconciled.',
            'Fuel mappings are provisional; absent/partial categories are not zero-filled or annualised.',
            'Pumped storage recycling is excluded from primary generation on both sides.',
            'No prices, exchanges, lifecycle factors or investment benefits validated.'])
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('native', 'observed', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Preserve previous empirical diagnostic')
    save(a.output, audit(a))
    print('Prepared fixed-inventory generation diagnostics; no validation inferred.')
