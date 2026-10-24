"""File-saving plumbing recovery, reusing the immutable completed annual solve."""
import json
import shutil
import traceback
from pathlib import Path
import run_batched_transport_robust_2025 as controller
from sigmoid_month_pairs_2025 import ROOT, digest
from run_differentiable_spline_2025 import atomic_json

PARENT = controller.OUT
OUT = ROOT / 'data/bidding-zone-network-2025/batched-transport-fit-v1'


def configure():
    controller.configure()
    base = controller.recovery.parent
    base.OUT = OUT
    # Correct the helper namespace without modifying a sealed producer.
    base.old.save_array = base.old.base.save_array
    previous = base.provenance
    def provenance():
        result = previous()
        for path in [Path(__file__), PARENT / 'annual.json', PARENT / 'annual.npz',
                     PARENT / 'failure.json', PARENT / 'provenance.json']:
            result[str(path.relative_to(ROOT))] = digest(path)
        return result
    base.provenance = provenance
    return base


def prepare():
    OUT.mkdir(exist_ok=True)
    annual = json.loads((PARENT / 'annual.json').read_text())
    assert annual['hours'] == 8760 and annual['zones'] == 48
    assert digest(PARENT / 'annual.npz') == annual['witness_sha256']
    assert 'save_array' in json.loads((PARENT / 'failure.json').read_text())['traceback']
    for name in ['annual.json', 'annual.npz', 'pilot.json']:
        target = OUT / name
        if target.exists():
            if digest(target) != digest(PARENT / name) and name != 'pilot.json':
                raise ValueError('Changed inherited annual witness')
        else:
            shutil.copy2(PARENT / name, target)
    pilot = json.loads((OUT / 'pilot.json').read_text())
    pilot['sources'][str(Path(__file__).relative_to(ROOT))] = digest(__file__)
    atomic_json(OUT / 'pilot.json', pilot)
    atomic_json(OUT / 'annual-reuse.json', dict(
        source=str(PARENT.relative_to(ROOT)), annual_witness_sha256=annual['witness_sha256'],
        scope='Exact completed neutral annual inference reuse; no repeated annual solve.'))


def run():
    prepare()
    base = configure()
    base.run()
    import report_batched_transport_2025 as report
    report.OUT = OUT
    report.setup = controller.recovery.setup
    report.provenance = base.provenance
    report.run()


if __name__ == '__main__':
    try:
        run()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT / 'failure.json', dict(traceback=traceback.format_exc()))
        raise
