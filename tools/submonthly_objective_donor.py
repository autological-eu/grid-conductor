"""Explicit singleton objective support from an independently replayed block."""
import json
from pathlib import Path
import numpy as np
from monthly_dispatch import digest

PRODUCER_DEPENDENCIES={'native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py','audit_submonthly_warm_calendar.py'}
REPLAY_DEPENDENCIES={'audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','disk_storage_blocks.py','submonthly_objective_donor.py'}


def load(path,domain):
    tools=Path(__file__).parent;cut=json.loads(path.read_text())
    producer=path.parent/'verified.json';receipt=json.loads(producer.read_text());index=cut['index']
    if (cut['status']!='independently_replayed_submonthly_economic_witness'
            or cut['input_sha256']!=domain['input_sha256'] or not 0<=index<len(domain['blocks'])
            or cut['block_sha256']!=domain['block_sha256'][index]
            or cut['producer_receipt_sha256']!=digest(producer)
            or cut['witness_sha256']!=digest(path.parent/'witness.npz')
            or cut['boundary_state_sha256']!=digest(path.parent/'boundary-state.npz')
            or cut['tool_sha256']!=digest(tools/'replay_submonthly_candidate.py')
            or receipt['producer_sha256']!=digest(tools/'audit_submonthly_candidate.py')):
        raise ValueError('Source-matched independently replayed objective donor required')
    for record in [cut,receipt]:
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Economic donor calculation changed')
    if set(cut['dependencies'])!=REPLAY_DEPENDENCIES or set(receipt['dependencies'])!=PRODUCER_DEPENDENCIES:
        raise ValueError('Complete economic calculation fingerprints required')
    g=np.asarray(cut['gradient_eur_per_mwh'],dtype=float);intercept=float(cut['dual_intercept_eur'])
    size=(len(domain['blocks'])+1)*len(domain['storage_ids'])
    if (g.shape!=(size,) or not np.isfinite(g).all()
            or not np.isfinite([intercept,cut['cost_eur'],cut['dual_support_eur']]).all()
            or cut['dual_support_eur']>cut['cost_eur']+1e-7):
        raise ValueError('Finite correctly sized economic support required')
    return ([index],g,intercept),dict(path=str(path),sha256=digest(path),index=index)
