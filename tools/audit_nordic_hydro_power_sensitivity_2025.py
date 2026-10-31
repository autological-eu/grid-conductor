"""Independent all-hour LP replay for the Nordic RoR profile sensitivity."""
from __future__ import annotations

import json

import numpy as np

from baselines.compact.source import ROOT, digest
from tools.price_mechanism_2025 import dual_replay
from tools.run_nordic_hydro_power_sensitivity_2025 import OUT, SUMMARY, candidate

AUDIT=ROOT/'research/data/nordic-ror-power-sensitivity-audit-2025.json'


def audit():
    summary=json.loads(SUMMARY.read_text());results={}
    for network in ('original','a11'):
        model,cost,rows=candidate(network)
        path=OUT/f'{network}.npz'
        if digest(path)!=summary['outcomes'][network]['witness_sha256']:
            raise ValueError('Changed annual RoR witness')
        with np.load(path) as archive:
            x=archive['values'];y=archive['row_duals'];objective=archive['objectives']
            if not archive['optimal'].all() or not np.array_equal(archive['hours'],np.arange(8760)):
                raise ValueError('Incomplete chronology')
        ng,nl,nz=(model[k] for k in ('ng','nl','nz'))
        maximum=dict(primal_residual_mw=0.,objective_residual_eur=0.)
        for start in range(0,8760,168):
            stop=min(start+168,8760);sl=slice(start,stop)
            rating=model['ratings'][sl] if model['ratings'].ndim==2 else model['ratings']
            case={k:model[k] for k in ('A','ng','nl','nz','islands')}
            case.update(cost=cost[sl],availability=model['availability'][sl],
                        link_min=model['link_min'][sl],link_max=model['link_max'][sl],
                        load=model['load'][sl],island_rhs=model['island_rhs'][sl],ratings=rating)
            reduced=np.c_[cost[sl],np.zeros((stop-start,nl+nz))]-(model['A'].T@y[sl].T).T
            values=dual_replay(case,x[sl],y[sl],reduced,objective[sl],model['flow'][sl])
            for key,value in values.items():maximum[key]=max(maximum.get(key,0.),value)
            actual=(model['A']@x[sl].T).T
            lower=np.c_[model['load'][sl],model['island_rhs'][sl],-rating-model['flow'][sl]]
            upper=np.c_[model['load'][sl],model['island_rhs'][sl],rating-model['flow'][sl]]
            maximum['primal_residual_mw']=max(maximum['primal_residual_mw'],
                float(np.maximum(lower-actual,0).max()),float(np.maximum(actual-upper,0).max()))
            maximum['objective_residual_eur']=max(maximum['objective_residual_eur'],
                float(abs((x[sl,:ng]*cost[sl]).sum(axis=1)-objective[sl]).max()))
        if maximum['primal_residual_mw']>=1e-4 or maximum['objective_residual_eur']>=.05:
            raise ValueError('Primal/objective replay failed')
        results[network]=dict(hours=8760,new_offer_columns=len(rows),
                              witness_sha256=digest(path),numerical=maximum)
    receipt=dict(status='both_full_year_primal_dual_replays_passed',outcomes=results)
    AUDIT.write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':print(json.dumps(audit(),indent=2))
