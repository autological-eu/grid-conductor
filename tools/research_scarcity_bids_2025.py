"""Read-only January offer-headroom diagnostic; no optimization or bid changes."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest

SOURCE=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
TARGET=ROOT/'data/price-trace/sdac-hourly-2025-v1'
OUT=ROOT/'data/bidding-zone-network-2025/scarcity-bid-research-v1'


def run():
    OUT.mkdir(parents=True,exist_ok=False)
    p=json.loads((SOURCE/'inputs.json').read_text());s=json.loads((SOURCE/'summary.json').read_text())
    audit=json.loads((SOURCE/'audit.json').read_text());case='solar_capacity';t=19*24+16
    assert audit['status']=='all_35040_hourly_source_native_and_optimality_replays_passed'
    assert audit['summary_sha256']==digest(SOURCE/'summary.json') and audit['inputs_sha256']==digest(SOURCE/'inputs.json')
    assert audit['auditor_sha256']==digest(ROOT/'tools/audit_annual_solar_alignment_2025.py')
    for file,sha in p['source_hashes'].items():assert digest(ROOT/file)==sha
    for file,sha in p['files'].items():assert digest(SOURCE/file)==sha
    path=ROOT/s['cases'][case]['annual']['witness'];assert digest(path)==s['cases'][case]['annual']['witness_sha256']
    with np.load(path) as z:x=z['values'][t];y=z['row_duals'][t]
    with np.load(SOURCE/'inputs.npz') as z:
        av=z['availability'][t]+z['solar_aligned'][t]-z['solar_original'][t]
        cost=z['cost'][t];thermal=z['thermal'];offer_zones=z['offer_zones'];emergency=z['emergency_mask']
        flow=z['flow'][t];ratings=z['ratings'];load=z['load'][t];island=z['island_rhs'][t]
        link_lo=z['link_min'][t];link_hi=z['link_max'][t]
    for row,vector in zip(p['capacity'],thermal,strict=True):av+=(row['factor']-1)*vector
    ng,nl,nz=p['ng'],p['nl'],p['nz'];zi=p['zones'].index('DE-LU');price=float(y[zi])
    A=load_npz(SOURCE/'network.npz');axis=np.zeros(A.shape[0]);axis[zi]=1
    spare=np.maximum(av-x[:ng],0);de=(offer_zones=='DE-LU')&~emergency
    rows=[]
    for row,vector in zip(p['capacity'],thermal,strict=True):
        ids=np.flatnonzero(vector>0)
        np.testing.assert_allclose(av[ids],vector[ids]*row['factor'],rtol=0,atol=1e-7)
        assert de[ids].all()
        for j in ids:np.testing.assert_array_equal(A[:,j].toarray().ravel(),axis)
        rows.append(dict(technology=row['technology'],available_mw=float(av[ids].sum()),
            dispatch_mw=float(x[ids].sum()),unused_mw=float(spare[ids].sum()),
            unused_below_300_mw=float(spare[ids][cost[ids]<300].sum()),
            bid_min_eur_mwh=float(cost[ids].min()),bid_max_eur_mwh=float(cost[ids].max())))
        # Second aggregation by scalar offer records, not the vector totals.
        assert abs(sum(float(av[j]-x[j]) for j in ids)-rows[-1]['unused_mw'])<1e-7
    candidates=np.flatnonzero(de&(spare>=1.)&(cost<300))
    j=int(min(candidates,key=lambda k:cost[k]));assert price<=cost[j]+1e-5
    np.testing.assert_array_equal(A[:,j].toarray().ravel(),axis)
    # Explicit feasible +1 MW demand witness: the selected offer's column is
    # exactly the DE balance row. Net injection/flows remain unchanged.
    v=x.copy();v[j]+=1.;row_lo=np.r_[load,island,-ratings-flow];row_hi=np.r_[load,island,ratings-flow]
    row_lo[zi]+=1.;row_hi[zi]+=1.;ax=A@v
    lo=np.r_[np.zeros(ng),link_lo];hi=np.r_[av,link_hi]
    residual=max(np.maximum(row_lo-ax,0).max(),np.maximum(ax-row_hi,0).max(),
                 np.maximum(lo-v[:ng+nl],0).max(),np.maximum(v[:ng+nl]-hi,0).max())
    assert residual<=1e-4
    target=json.loads((TARGET/'summary.json').read_text())
    assert target['prices_sha256']==digest(TARGET/'prices.npz') and target['zones']==p['zones']
    with np.load(TARGET/'prices.npz') as z:observed=float(z['prices'][t,zi])
    assert abs(observed-583.4)<1e-9
    # The certificate gives an upper bound for a +1 MW objective increment, not
    # a newly solved derivative or a real-world plant-availability estimate.
    result=dict(status='saved_offer_book_and_feasible_one_mw_certificate_replayed',
        producer_sha256=digest(__file__),hour=t,utc='2025-01-20T16:00Z',case=case,
        observed_eur_mwh=observed,model_eur_mwh=price,thermal=rows,
        unused_de_nonemergency_below_500_mw=float(spare[de&(cost<500)].sum()),
        one_mw_certificate=dict(offer_column=j,offer_bid_eur_mwh=float(cost[j]),
            objective_increment_upper_bound_eur=float(cost[j]),maximum_primal_residual_mw=float(residual),
            scope='Hypothetical extra load along this zonal representation; algebraic feasible witness, no new optimization'),
        source_hashes={str(f.relative_to(ROOT)):digest(f) for f in [SOURCE/'inputs.json',SOURCE/'inputs.npz',SOURCE/'network.npz',SOURCE/'summary.json',SOURCE/'audit.json',path,TARGET/'summary.json',TARGET/'prices.npz']})
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    ids=np.flatnonzero(thermal.sum(axis=0)>0);order=ids[np.argsort(cost[ids])]
    cumulative=np.r_[0,np.cumsum(av[order])/1000];prices=np.r_[cost[order],cost[order][-1]]
    fig,axes=plt.subplots(1,2,figsize=(11,4.3));pos=np.arange(3)
    axes[0].bar(pos,[r['available_mw']/1000 for r in rows],label='Modeled available')
    axes[0].bar(pos,[r['dispatch_mw']/1000 for r in rows],label='Saved dispatch')
    axes[0].set_xticks(pos,['Hard coal','Lignite','Gas']);axes[0].set_ylabel('German thermal power, GW');axes[0].legend(fontsize=8)
    axes[1].step(cumulative,prices,where='post',label='Local thermal offers')
    axes[1].axhline(price,color='green',ls='--',label=f'Coupled model price {price:.2f}')
    axes[1].axhline(observed,color='black',ls='--',label=f'Observed price {observed:.2f}')
    axes[1].set_xlabel('Cumulative local thermal offered capacity, GW');axes[1].set_ylabel('Bid / price, €/MWh');axes[1].set_ylim(0,630);axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.suptitle('January 20, 2025, 16 UTC — saved source-corrected model\nLocal offer inventory; not an isolated German market-clearing curve',fontsize=11)
    fig.tight_layout();image=ROOT/'research/assets/scarcity-bid-headroom-2025.png';fig.savefig(image,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    (OUT/'figure-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(OUT/'summary.json'),figure_sha256=digest(image)),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_hashes'},indent=2))


if __name__=='__main__':run()
