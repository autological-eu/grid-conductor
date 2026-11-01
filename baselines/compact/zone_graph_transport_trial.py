"""Physical zone-edge message-passing candidate for the same transport LP oracle."""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .evaluation import ANNUAL
from .graph_transport_lp_trial import NZ, evaluate
from .neurodynamic_lp_trial import construction
from .source import ROOT, digest

OUT = ROOT / 'data/bidding-zone-network-2025/zone-graph-transport-v1'
ORACLE = ROOT / 'data/bidding-zone-network-2025/graph-transport-lp-v1/oracle.npz'


class ZoneGraph(nn.Module):
    """GNN on physical interconnectors, with zone and corridor output heads."""
    def __init__(self, edges, width=64, rounds=3):
        super().__init__()
        self.register_buffer('src', torch.as_tensor(edges[:, 0], dtype=torch.long))
        self.register_buffer('dst', torch.as_tensor(edges[:, 1], dtype=torch.long))
        degree = torch.bincount(torch.cat([self.src,self.dst]), minlength=NZ).clamp_min(1)
        self.register_buffer('degree', degree.float())
        self.node_in=nn.Linear(3,width)
        self.edge_in=nn.Linear(2,width)
        self.node_step=nn.ModuleList([nn.Sequential(nn.Linear(3*width,width),nn.GELU(),
                                                   nn.Linear(width,width)) for _ in range(rounds)])
        self.edge_step=nn.ModuleList([nn.Sequential(nn.Linear(3*width,width),nn.GELU(),
                                                   nn.Linear(width,width)) for _ in range(rounds)])
        self.node_norm=nn.ModuleList([nn.LayerNorm(width) for _ in range(rounds)])
        self.edge_norm=nn.ModuleList([nn.LayerNorm(width) for _ in range(rounds)])
        self.qhead=nn.Linear(width,1)
        self.fhead=nn.Linear(width,1)
        self.phead=nn.Linear(width,1)

    def forward(self,b,c):
        ne=len(self.src)
        load=b[:,:NZ]
        cap=b[:,2*NZ:3*NZ]
        hi=b[:,4*NZ:4*NZ+ne]
        lo=-b[:,4*NZ+ne:]
        node=self.node_in(torch.stack([load,cap,c[:,:NZ]],-1))
        edge=self.edge_in(torch.stack([lo,hi],-1))
        for ns,es,nnorm,enorm in zip(self.node_step,self.edge_step,
                                     self.node_norm,self.edge_norm):
            a=node[:,self.src]
            z=node[:,self.dst]
            edge=enorm(edge+es(torch.cat([edge,a,z],-1)))
            msg=edge+z
            rev=edge+a
            agg=torch.zeros_like(node)
            # Learned edge-to-node messages, summed over actual incident links.
            agg.index_add_(1,self.src,msg)
            agg.index_add_(1,self.dst,rev)
            agg=agg/self.degree[None,:,None]
            context=node.mean(1,keepdim=True).expand_as(node)
            node=nnorm(node+ns(torch.cat([node,agg,context],-1)))
        q=cap*torch.sigmoid(self.qhead(node).squeeze(-1))
        f=lo+(hi-lo)*torch.sigmoid(self.fhead(edge).squeeze(-1))
        price=self.phead(node).squeeze(-1)*100
        return torch.cat([q,f],1),price


def run(epochs=40,batch_size=128):
    torch.set_num_threads(2)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not ORACLE.exists():
            raise FileNotFoundError('Matched exact transport oracle must be present')
        data=construction()
        with np.load(ORACLE) as npz:
            ox=npz['x']; op=npz['price']
        provenance=dict(protocol='physical-zone-graph-transport-v1',
            source_sha256=digest(Path(__file__)),
            oracle_sha256=digest(ORACLE),
            annual_witness_sha256=digest(ANNUAL/'annual.npz'),
            odd_hours=len(data['odd']),even_hours=len(data['even']),epochs=epochs)
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=provenance:
            raise ValueError('Changed source or oracle; refusing duplicate trial')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        torch.manual_seed(19)
        model=ZoneGraph(data['edges'])
        optim=torch.optim.AdamW(model.parameters(),lr=.001)
        target_x=torch.from_numpy(ox); target_p=torch.from_numpy(op)
        history=[]; began=time.perf_counter()
        for epoch in range(epochs):
            model.train(); losses=[]
            ids=np.random.default_rng(200+epoch).permutation(data['odd'])
            for block in np.array_split(ids,max(1,(len(ids)+batch_size-1)//batch_size)):
                b=data['b'][block]; c=data['c'][block]
                x,p=model(b,c)
                balance=x@data['A'][:2*NZ].T-b[:,:2*NZ]
                loss=(x-target_x[block]).square().mean()+.1*((p-target_p[block])/100).square().mean()+8*balance.square().mean()
                optim.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(),10)
                optim.step(); losses.append(float(loss.detach()))
            history.append(dict(epoch=epoch+1,train_loss=float(np.mean(losses))))
            if (epoch+1)%5==0:
                print(f'epoch {epoch+1}/{epochs}: loss={history[-1]["train_loss"]:.6f}',flush=True)
        result=dict(provenance=provenance,train_seconds=time.perf_counter()-began,
            history=history,odd=evaluate(model,data,ox,op,data['odd']),
            even=evaluate(model,data,ox,op,data['even']))
        torch.save(model.state_dict(),OUT/'model.pt')
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
