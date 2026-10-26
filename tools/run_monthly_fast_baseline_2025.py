"""Sequential monthly fast fits, one annual LP clear, independent audit."""
import json
import traceback

from fit_monthly_fast_splines_2025 import main as fit,OUT as FIT
from clear_monthly_fast_lp_2025 import run as clear,OUT as LP
from audit_monthly_fast_lp_2025 import run as audit
from run_differentiable_spline_2025 import atomic_json


def main():
    FIT.mkdir(exist_ok=True)
    pilot=FIT.parent/'monthly-fast-lp-pilot-v3/summary.json'
    if json.loads(pilot.read_text())['status']!='24_hour_original_offer_lp_passed':
        raise ValueError('The existing-column LP pilot did not pass')
    if (FIT/'complete.json').exists() or (LP/'annual.npz').exists():
        raise ValueError('Inspect prior outputs before starting; no implicit restart')
    try:
        atomic_json(FIT/'pipeline.json',dict(stage='monthly_fast_fits'))
        fit()
        atomic_json(FIT/'pipeline.json',dict(stage='one_annual_physical_lp'))
        clear()
        if not (LP/'summary.json').exists():
            raise RuntimeError('Annual LP failed; inspect failure receipt')
        atomic_json(FIT/'pipeline.json',dict(stage='independent_annual_audit'))
        audit()
        atomic_json(FIT/'pipeline.json',dict(stage='audited_annual_complete',
            annual_summary=str(LP/'summary.json'),annual_audit=str(LP/'audit.json')))
    except Exception:
        atomic_json(FIT/'pipeline-failure.json',dict(traceback=traceback.format_exc()))
        raise


if __name__=='__main__':main()
