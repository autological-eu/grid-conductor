"""Supervised variable-constraint message passing on the 2025 transport LP.

Experimental approximation only; the accepted physical LP is unchanged.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import linprog
from torch import nn

from .evaluation import ANNUAL
from .neurodynamic_lp_trial import construction, SCALE_GW
from .source import ROOT, digest

OUT = ROOT / 'data/bidding-zone-network-2025/graph-transport-lp-v1'
NZ = 48


def oracle(data):
    path = OUT / 'oracle.npz'
    if path.exists():
        with np.load(path) as saved:
            return saved['x'], saved['price'], float(saved['seconds'])
    A = data['A'].numpy().astype('float64')
    b = data['b'].numpy()
    c = data['c'].numpy()
    x = np.empty((len(b), data['nx']), np.float32)
    price = np.empty((len(b), NZ), np.float32)
    start = time.perf_counter()
    for i in range(len(b)):
        sol = linprog(c[i].astype('float64'), A_ub=A,
                      b_ub=b[i].astype('float64'),
                      bounds=[(None, None)] * data['nx'], method='highs')
        if not sol.success:
            raise RuntimeError(f'Exact transport hour {i}: {sol.message}')
        x[i] = sol.x
        price[i] = (sol.ineqlin.marginals[:NZ] - sol.ineqlin.marginals[NZ:2*NZ]) * 100
        if (i + 1) % 1000 == 0:
            print(f'exact oracle {i + 1}/8760', flush=True)
    seconds = time.perf_counter() - start
    np.savez_compressed(path, x=x, price=price, seconds=seconds)
    return x, price, seconds


class GraphTransport(nn.Module):
    """Fixed LP-coefficient graph: variable, constraint, objective context.

    Nonzero A_ij are signed variable-constraint edges; every variable also
    connects to the shared objective context through its hourly cost.
    """
    def __init__(self, A, width=64, rounds=3):
        super().__init__()
        self.register_buffer('A', A)
        abs_A = A.abs()
        self.register_buffer('av', A / abs_A.sum(0).clamp_min(1)[None, :])
        self.register_buffer('ac', A / abs_A.sum(1).clamp_min(1)[:, None])
        self.vi = nn.Linear(3, width)
        self.ci = nn.Linear(3, width)
        self.vstep = nn.ModuleList([nn.Sequential(nn.Linear(3*width, width), nn.GELU(),
                                                nn.Linear(width, width)) for _ in range(rounds)])
        self.cstep = nn.ModuleList([nn.Sequential(nn.Linear(2*width, width), nn.GELU(),
                                                nn.Linear(width, width)) for _ in range(rounds)])
        self.vnorm = nn.ModuleList([nn.LayerNorm(width) for _ in range(rounds)])
        self.cnorm = nn.ModuleList([nn.LayerNorm(width) for _ in range(rounds)])
        self.xhead = nn.Linear(width, 1)
        self.phead = nn.Linear(width, 1)
        self.register_buffer('vkind', torch.cat([torch.zeros(NZ), torch.ones(A.shape[1]-NZ)]))
        self.register_buffer('ckind', torch.cat([torch.zeros(2*NZ),
            torch.ones(2*NZ), torch.full((2*(A.shape[1]-NZ),), 2.)]))

    def forward(self, b, c):
        n = len(b)
        vf = torch.stack([c, self.vkind.expand(n,-1),
                          self.A.abs().sum(0).expand(n,-1)/10], dim=-1)
        cf = torch.stack([b, self.ckind.expand(n,-1),
                          self.A.abs().sum(1).expand(n,-1)/10], dim=-1)
        v = self.vi(vf)
        con = self.ci(cf)
        for vc, cc, vn, cn in zip(self.vstep, self.cstep, self.vnorm, self.cnorm):
            con = cn(con + cc(torch.cat([con, torch.einsum('ij,bjd->bid', self.ac, v)], -1)))
            objective = (v * c[...,None]).mean(1, keepdim=True).expand_as(v)
            v = vn(v + vc(torch.cat([v, torch.einsum('ij,bid->bjd', self.av, con),
                                       objective], -1)))
        raw = self.xhead(v).squeeze(-1)
        cap = b[:,2*NZ:3*NZ]
        hi = b[:,4*NZ:4*NZ+(self.A.shape[1]-NZ)]
        lo = -b[:,4*NZ+(self.A.shape[1]-NZ):]
        q = cap * torch.sigmoid(raw[:,:NZ])
        flow = lo + (hi-lo) * torch.sigmoid(raw[:,NZ:])
        # Balance prices are constraint-node outputs, in EUR/MWh.
        price = (self.phead(con[:,:NZ]).squeeze(-1) -
                 self.phead(con[:,NZ:2*NZ]).squeeze(-1)) * 100
        return torch.cat([q,flow], 1), price


def evaluate(model, data, oracle_x, oracle_price, ids):
    model.eval()
    xs, ps = [], []
    start = time.perf_counter()
    with torch.no_grad():
        for block in np.array_split(ids, max(1, (len(ids)+255)//256)):
            x,p = model(data['b'][block], data['c'][block])
            xs.append(x.numpy()); ps.append(p.numpy())
    seconds = time.perf_counter()-start
    x=np.concatenate(xs); p=np.concatenate(ps)
    A=data['A'].numpy(); b=data['b'][ids].numpy(); c=data['c'][ids].numpy()
    residual=x@A.T-b
    balance=x[:,:NZ]+x[:,NZ:]@data['incidence'].astype('float32')-data['load'][ids]/SCALE_GW
    exact_obj=(c*oracle_x[ids]).sum(1)
    pred_obj=(c*x).sum(1)
    return dict(hours=len(ids), inference_seconds=seconds,
        decision_mae_gw=float(np.abs(x-oracle_x[ids]).mean()*SCALE_GW),
        price_mae_to_transport_lp_eur_mwh=float(np.abs(p-oracle_price[ids]).mean()),
        balance_mae_mw=float(np.abs(balance).mean()*SCALE_GW*1000),
        balance_max_mw=float(np.abs(balance).max()*SCALE_GW*1000),
        balance_above_1mw_cells=int((np.abs(balance)>1/(SCALE_GW*1000)).sum()),
        inequality_max_violation_mw=float(np.maximum(residual,0).max()*SCALE_GW*1000),
        mean_objective_gap_normalized=float(np.mean(pred_obj-exact_obj)),
        below_exact_objective_hours=int((pred_obj<exact_obj-1e-5).sum()))


def run(epochs=40, batch_size=128):
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=construction()
        provenance=dict(protocol='graph-transport-lp-supervised-v1',
            source_sha256=digest(Path(__file__)),
            transport_source_sha256=digest(ROOT/'baselines/compact/neurodynamic_lp_trial.py'),
            annual_witness_sha256=digest(ANNUAL/'annual.npz'),
            odd_hours=len(data['odd']), even_hours=len(data['even']), epochs=epochs)
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text()) != provenance:
            raise ValueError('Changed source or protocol; refusing resume')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        ox,op,oracle_seconds=oracle(data)
        tx=torch.from_numpy(ox); tp=torch.from_numpy(op)
        torch.manual_seed(19)
        model=GraphTransport(data['A'])
        optim=torch.optim.AdamW(model.parameters(),lr=.001)
        history=[]; began=time.perf_counter()
        for epoch in range(epochs):
            model.train(); losses=[]
            ids=np.random.default_rng(200+epoch).permutation(data['odd'])
            for block in np.array_split(ids,max(1,(len(ids)+batch_size-1)//batch_size)):
                b=data['b'][block]; c=data['c'][block]
                x,p=model(b,c)
                balance=x@data['A'][:2*NZ].T-b[:,:2*NZ]
                loss=(x-tx[block]).square().mean()+.1*((p-tp[block])/100).square().mean() + 8*balance.square().mean()
                optim.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),10)
                optim.step(); losses.append(float(loss.detach()))
            history.append(dict(epoch=epoch+1,train_loss=float(np.mean(losses))))
            if (epoch+1)%5==0:
                print(f'epoch {epoch+1}/{epochs}: loss={history[-1]["train_loss"]:.6f}',flush=True)
        train_seconds=time.perf_counter()-began
        result=dict(provenance=provenance,oracle_seconds=oracle_seconds,
                    train_seconds=train_seconds,history=history,
                    odd=evaluate(model,data,ox,op,data['odd']),
                    even=evaluate(model,data,ox,op,data['even']))
        torch.save(model.state_dict(),OUT/'model.pt')
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
