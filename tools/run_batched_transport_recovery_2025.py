"""Fresh-provenance controller for unchanged transport economics, robust Newton."""
import argparse,json,traceback
from pathlib import Path
import numpy as np
import run_batched_transport_2025 as parent
from batched_transport_newton_recovery_2025 import RecoveredTransportMarket
from supply_knot_splines_2025 import initial_parameters
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT,digest

PARENT=parent.OUT
OUT=ROOT/'data/bidding-zone-network-2025/batched-transport-recovery-v1'
PLAN=ROOT/'config/batched-transport-recovery-2025.json'
ORIGINAL_SETUP=parent.setup
ORIGINAL_PROVENANCE=parent.provenance


def setup():
    state,m,network,design=ORIGINAL_SETUP()
    market=RecoveredTransportMarket(m.zones,m.groups,m.lower,m.upper,m.edges,m.capacity,m.source,m.load,
        cost=m.cost,thermal_tau=m.thermal_tau,renewable_tau=m.renewable_tau,flow_tau=m.flow_tau)
    return state,market,network,design


def configure():
    parent.OUT=OUT;parent.PLAN=PLAN;parent.setup=setup
    before=json.loads((ROOT/'config/batched-transport-dispatch-2025.json').read_text());after=json.loads(PLAN.read_text())
    for key,value in before.items():
        if key!='name' and after[key]!=value:raise ValueError('Numerical recovery changed specification: '+key)
    def provenance():
        paths=[Path(__file__),ROOT/'tools/batched_transport_newton_recovery_2025.py',PARENT/'failure.json',PARENT/'provenance.json',ROOT/'config/batched-transport-dispatch-2025.json']
        result=ORIGINAL_PROVENANCE();result.update({str(p.relative_to(ROOT)):digest(p) for p in paths});return result
    parent.provenance=provenance


def pilot():
    import pilot_batched_transport_2025 as p
    p.OUT=OUT;p.setup=setup;p.run()
    state,m,_,_=setup();theta=initial_parameters(m.ng)[:,[0,5,6,7,8,9]]
    r=m.solve(theta,np.array([318]))
    record=json.loads((OUT/'pilot.json').read_text());record['recovered_original_failure']=dict(hour=318,certificate=r['certificate'],seconds=r['seconds'],coordinate_recoveries=r['coordinate_recoveries'])
    for path in [Path(__file__),ROOT/'tools/batched_transport_newton_recovery_2025.py',PLAN]:record['sources'][str(path.relative_to(ROOT))]=digest(path)
    atomic_json(OUT/'pilot.json',record)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');args=parser.parse_args();OUT.mkdir(exist_ok=True)
    configure()
    try:
        if args.pilot:pilot()
        else:
            parent.run()
            import report_batched_transport_2025 as report
            report.OUT=OUT;report.setup=setup;report.provenance=parent.provenance;report.run()
    except Exception:
        atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
