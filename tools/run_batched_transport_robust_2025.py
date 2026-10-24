"""Fresh provenance for cold-retry numerical policy; original market retained."""
import argparse,json,traceback
from pathlib import Path
import numpy as np
import run_batched_transport_recovery_2025 as recovery
from batched_transport_cold_retry_2025 import RobustTransportMarket
from sigmoid_month_pairs_2025 import ROOT,digest
from supply_knot_splines_2025 import initial_parameters
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/batched-transport-robust-v1'
PLAN=ROOT/'config/batched-transport-robust-2025.json'


def configure():
    recovery.PARENT=recovery.OUT;recovery.OUT=OUT;recovery.PLAN=PLAN
    recovery.RecoveredTransportMarket=RobustTransportMarket;recovery.configure()
    previous=recovery.parent.provenance
    def provenance():
        result=previous()
        for path in [Path(__file__),ROOT/'tools/batched_transport_cold_retry_2025.py',PLAN]:result[str(path.relative_to(ROOT))]=digest(path)
        return result
    recovery.parent.provenance=provenance


def main(pilot=False):
    configure()
    if pilot:
        recovery.pilot()
        state,m,_,_=recovery.setup();theta=initial_parameters(m.ng)[:,[0,5,6,7,8,9]]
        r=m.solve(theta,np.array([1928]))
        record=json.loads((OUT/'pilot.json').read_text());record['second_failure_cold_replay']=dict(hour=1928,seconds=r['seconds'],certificate=r['certificate'])
        for path in [Path(__file__),ROOT/'tools/batched_transport_cold_retry_2025.py',PLAN]:record['sources'][str(path.relative_to(ROOT))]=digest(path)
        atomic_json(OUT/'pilot.json',record)
    else:
        recovery.parent.run()
        import report_batched_transport_2025 as report
        report.OUT=OUT;report.setup=recovery.setup;report.provenance=recovery.parent.provenance;report.run()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');args=parser.parse_args();OUT.mkdir(exist_ok=True)
    try:main(args.pilot)
    except Exception:
        atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
