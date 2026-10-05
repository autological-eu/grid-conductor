"""Adopt a replayed necessary cut in the explicit shorter-block state layout."""
import json
from pathlib import Path
import numpy as np
from monthly_dispatch import digest


def load(path, domain, anchor):
    tools=Path(__file__).parent
    cut=json.loads(path.read_text())
    producer=path.parent/'verified.json'
    receipt=json.loads(producer.read_text())
    index=cut['index']
    if (cut['status']!='independently_replayed_submonthly_feasibility_cut'
            or cut['input_sha256']!=domain['input_sha256']
            or cut['anchor_audit_sha256']!=domain['annual_primal_audit_sha256']
            or not 0<=index<len(domain['blocks'])
            or cut['block_sha256']!=domain['block_sha256'][index]
            or cut['producer_receipt_sha256']!=digest(producer)
            or cut['witness_sha256']!=digest(path.parent/'witness.npz')
            or cut['tool_sha256']!=digest(tools/'replay_submonthly_feasibility.py')
            or receipt['producer_sha256']!=digest(tools/'audit_submonthly_feasibility.py')):
        raise ValueError('Source-matched replayed submonthly feasibility donor required')
    for record in [cut,receipt]:
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:
                raise ValueError('Submonthly feasibility calculation changed')
    g=np.asarray(cut['gradient'],dtype=float)
    limit=float(cut['feasibility_limit']);intercept=float(cut['intercept'])
    if (g.shape!=anchor.shape or not np.isfinite(g).all()
            or not np.isfinite([limit,intercept,cut['dual_support'],cut['anchor_support']]).all()
            or cut['dual_support']<=1e-7 or cut['anchor_support']>1e-7
            or limit!=1e-7-intercept
            or abs(float(intercept+g@anchor)-cut['anchor_support'])>1e-7
            or float(g@anchor)>limit):
        raise ValueError('Necessary cut layout, separation or verified anchor differs')
    return g,limit,dict(path=str(path),sha256=digest(path),index=index,
                       scope='Replayed necessary inventory feasibility cut; not an economic objective')
