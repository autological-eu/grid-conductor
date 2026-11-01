"""Declared longer-training search for the experimental zone-edge transport GNN."""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .evaluation import ANNUAL
from .graph_transport_lp_trial import evaluate
from .neurodynamic_lp_trial import construction
from .odd_even_transformer_trial import MONTH
from .source import ROOT, digest
from .zone_graph_transport_trial import NZ, ORACLE, ZoneGraph

OUT = ROOT / 'data/bidding-zone-network-2025/zone-graph-tuning-v1'
EPOCHS = 80
CONFIGS = (
    dict(name='higher_rate', lr=.002, balance_weight=8.),
    dict(name='higher_balance', lr=.001, balance_weight=16.),
)


def run():
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=construction()
        with np.load(ORACLE) as saved:
            ox=saved['x']; op=saved['price']
        train=np.flatnonzero((MONTH%2==1)&(MONTH!=11))
        val=np.flatnonzero(MONTH==11)
        even=data['even']
        provenance=dict(protocol='zone-graph-odd-validation-search-v1',
            source_sha256=digest(Path(__file__)),
            model_source_sha256=digest(ROOT/'baselines/compact/zone_graph_transport_trial.py'),
            oracle_sha256=digest(ORACLE), annual_witness_sha256=digest(ANNUAL/'annual.npz'),
            configs=list(CONFIGS), epochs=EPOCHS,
            train_hours=len(train), validation_hours=len(val), even_hours=len(even),
            selection='minimum November price MAE + balance MAE MW / 100, every 10 epochs')
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=provenance:
            raise ValueError('Changed protocol; refusing resume')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        tx=torch.from_numpy(ox); tp=torch.from_numpy(op)
        rows=[]; start=time.perf_counter()
        for ci, cfg in enumerate(CONFIGS):
            torch.manual_seed(29)
            model=ZoneGraph(data['edges'])
            opt=torch.optim.AdamW(model.parameters(),lr=cfg['lr'])
            history=[]; best=None; best_state=None
            began=time.perf_counter()
            for epoch in range(EPOCHS):
                model.train(); losses=[]
                ids=np.random.default_rng(300+epoch).permutation(train)
                for block in np.array_split(ids,max(1,(len(ids)+127)//128)):
                    b=data['b'][block]; c=data['c'][block]
                    x,p=model(b,c)
                    balance=x@data['A'][:2*NZ].T-b[:,:2*NZ]
                    loss=(x-tx[block]).square().mean()+.1*((p-tp[block])/100).square().mean()+cfg['balance_weight']*balance.square().mean()
                    opt.zero_grad(); loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(),10)
                    opt.step(); losses.append(float(loss.detach()))
                row=dict(epoch=epoch+1,train_loss=float(np.mean(losses)))
                if (epoch+1)%10==0:
                    v=evaluate(model,data,ox,op,val)
                    row['validation']=v
                    score=v['price_mae_to_transport_lp_eur_mwh']+v['balance_mae_mw']/100
                    row['selection_score']=score
                    if best is None or score<best['selection_score']:
                        best=row
                        best_state={k:t.detach().cpu().clone() for k,t in model.state_dict().items()}
                        torch.save(best_state,OUT/f'{cfg["name"]}-best.pt')
                    print(f'{cfg["name"]} epoch {epoch+1}/{EPOCHS}: val price={v["price_mae_to_transport_lp_eur_mwh"]:.3f}, balance={v["balance_mae_mw"]:.1f} MW',flush=True)
                history.append(row)
            rows.append(dict(config=cfg,train_seconds=time.perf_counter()-began,
                             best_epoch=best['epoch'],selection_score=best['selection_score'],
                             validation=best['validation'],history=history))
            (OUT/f'{cfg["name"]}-history.json').write_text(json.dumps(rows[-1],indent=2)+'\n')
        winner=min(rows,key=lambda r:r['selection_score'])
        model=ZoneGraph(data['edges'])
        model.load_state_dict(torch.load(OUT/f'{winner["config"]["name"]}-best.pt',map_location='cpu',weights_only=True))
        result=dict(provenance=provenance,total_seconds=time.perf_counter()-start,
                    candidates=[{k:v for k,v in row.items() if k!='history'} for row in rows],
                    selected=winner['config']['name'],selected_epoch=winner['best_epoch'],
                    even=evaluate(model,data,ox,op,even),
                    odd_train=evaluate(model,data,ox,op,train))
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
