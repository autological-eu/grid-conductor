"""Learning-rate-only control for the zone graph, with the same odd-month split."""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .graph_transport_lp_trial import evaluate
from .neurodynamic_lp_trial import construction
from .odd_even_transformer_trial import MONTH
from .source import ROOT, digest
from .zone_graph_transport_trial import NZ, ORACLE, ZoneGraph

OUT=ROOT/'data/bidding-zone-network-2025/zone-graph-rate-control-v1'


def run():
    torch.set_num_threads(2)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=construction()
        with np.load(ORACLE) as z:
            ox=z['x']; op=z['price']
        train=np.flatnonzero((MONTH%2==1)&(MONTH!=11))
        val=np.flatnonzero(MONTH==11)
        provenance=dict(protocol='zone-graph-rate-control-v1',source_sha256=digest(Path(__file__)),
            oracle_sha256=digest(ORACLE),model_source_sha256=digest(ROOT/'baselines/compact/zone_graph_transport_trial.py'),
            train_hours=len(train),validation_hours=len(val),epochs=80,lr=.001,balance_weight=8.)
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=provenance:
            raise ValueError('Changed protocol')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        torch.manual_seed(29)
        model=ZoneGraph(data['edges'])
        opt=torch.optim.AdamW(model.parameters(),lr=.001)
        tx=torch.from_numpy(ox); tp=torch.from_numpy(op)
        history=[]; best=None
        began=time.perf_counter()
        for epoch in range(80):
            model.train(); losses=[]
            ids=np.random.default_rng(300+epoch).permutation(train)
            for block in np.array_split(ids,max(1,(len(ids)+127)//128)):
                b=data['b'][block];c=data['c'][block]
                x,p=model(b,c)
                balance=x@data['A'][:2*NZ].T-b[:,:2*NZ]
                loss=(x-tx[block]).square().mean()+.1*((p-tp[block])/100).square().mean()+8*balance.square().mean()
                opt.zero_grad();loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),10)
                opt.step();losses.append(float(loss.detach()))
            row=dict(epoch=epoch+1,train_loss=float(np.mean(losses)))
            if (epoch+1)%10==0:
                v=evaluate(model,data,ox,op,val)
                row['validation']=v
                row['selection_score']=v['price_mae_to_transport_lp_eur_mwh']+v['balance_mae_mw']/100
                if best is None or row['selection_score']<best['selection_score']:
                    best=row
                    torch.save(model.state_dict(),OUT/'best.pt')
                print(f'control epoch {epoch+1}/80: val price={v["price_mae_to_transport_lp_eur_mwh"]:.3f}, balance={v["balance_mae_mw"]:.1f} MW',flush=True)
            history.append(row)
        train_seconds=time.perf_counter()-began
        model.load_state_dict(torch.load(OUT/'best.pt',map_location='cpu',weights_only=True))
        result=dict(provenance=provenance,train_seconds=train_seconds,history=history,
            selected_epoch=best['epoch'],selection_score=best['selection_score'],
            even=evaluate(model,data,ox,op,data['even']))
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
