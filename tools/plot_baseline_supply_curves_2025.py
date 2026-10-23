"""Show current baseline technology offer curves, preserving pooled source MW.

A reporting extraction only: no fit, solve, change of bids or baseline promotion.
"""
import csv
import json
import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pypsa
from generation_mix_2025 import ROOT,CARRIER,FAMILIES,digest
from europe_linked_clearing_2025 import load

ZONE='DE-LU'
HOUR='2025-07-15T12'
NAME='de-lu-baseline-supply-curves-2025'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
FLEET=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
SOLAR=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
TECH=[f for f in FAMILIES if f not in ['reservoir','emergency']]
NAMES=dict(onshore_wind='Onshore wind',offshore_wind='Offshore wind',solar='Solar',nuclear='Nuclear',ror='Run-of-river hydro',gas='Gas',hard_coal='Hard coal',lignite='Lignite',oil='Oil / CHP',biomass='Biomass',waste='Waste',geothermal='Geothermal')
COLORS=dict(zip(TECH,['#16817a','#37a8a1','#e2ad16','#8856a7','#327db4','#d86b35','#555555','#96754d','#ad456c','#6b9e38','#8b8c35','#ae817b'],strict=True))


def steps(rows):
    rows=sorted(rows,key=lambda r:(r['bid_eur_mwh'],r['offer_column'],r['technology']))
    prices=np.array([r['bid_eur_mwh'] for r in rows]);ends=np.cumsum([r['available_mw'] for r in rows])/1000
    return rows,np.r_[0,ends],np.r_[prices,prices[-1]]


def report():
    _,active,p,s,m,c,_,reference,layout_path=load();t=int((np.datetime64(HOUR)-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int));zi=p['zones'].index(ZONE)
    source_paths=[ROOT/'config/active-research-baseline.json',ROOT/active['inputs_path'],ROOT/active['proposal']['path'],ROOT/active['witness']['witness'],layout_path,ANCHOR/'native.nc',FLEET/'inputs.json',FLEET/'components.npz',SOLAR/'inputs.json',SOLAR/'delta.npz',ROOT/'tools/europe_linked_clearing_2025.py',ROOT/'tools/solar_anchor_bids_2025.py']
    layout=json.loads(layout_path.read_text());n=pypsa.Network(ANCHOR/'native.nc');native=n.get_switchable_as_dense('Generator','p_max_pu').iloc[t].to_numpy()*n.generators.p_nom.to_numpy();labels=[CARRIER[g.carrier] for _,g in n.generators.iterrows()]
    fi=json.loads((FLEET/'inputs.json').read_text());assert digest(FLEET/'components.npz')==fi['components_sha256']
    factors={r['country']:r['factor'] for r in json.loads((SOLAR/'inputs.json').read_text())['factors']}
    with np.load(FLEET/'components.npz') as z:pv=z['pv'][t]*(86/90)*np.array([factors.get(v,1.) for v in fi['native_countries']]);mapping=z['mapping']
    pv_total=pv@mapping;np.testing.assert_allclose(pv_total,s['solar_aligned'][t]*(86/90)+np.load(SOLAR/'delta.npz')['delta'][t],rtol=0,atol=1e-7)
    rows=[];emergency=[];partition_error=0.;mixed=0
    for j in np.flatnonzero(s['offer_zones']==ZONE):
        av=float(m['availability'][t,j]);price=float(c[t,j])
        if s['emergency_mask'][j]:emergency.append(dict(offer_column=int(j),available_mw=av,bid_eur_mwh=price));continue
        if j>=p['original_ng']:
            # Added oil capacity and split oil-CHP offers retain source technology.
            parts={'oil':av};rank='oil CHP / added oil'
        else:
            ids=layout['members'][j];fraction=layout['fractions'][j];rank=str(layout['ranks'][j]);parts={}
            nonpv=[i for i in ids if labels[i]!='solar'];den=float(native[nonpv].sum()*fraction);remaining=max(0.,av-pv_total[j])
            assert den>1e-9 or remaining<1e-5
            for fuel in {labels[i] for i in nonpv}:
                cap=float(native[[i for i in nonpv if labels[i]==fuel]].sum()*fraction)
                parts[fuel]=cap*remaining/den if den>0 else 0.
            if pv_total[j]>0:parts['solar']=float(pv_total[j])
        partition_error=max(partition_error,abs(sum(parts.values())-av));assert partition_error<1e-5
        mixed+=sum(v>1e-7 for v in parts.values())>1
        for fuel,mw in parts.items():
            if mw>1e-7:rows.append(dict(zone=ZONE,hour_utc=HOUR+':00Z',technology=fuel,offer_column=int(j),tranche_rank=rank,available_mw=float(mw),bid_eur_mwh=price,source_pool_has_multiple_technologies=bool(sum(v>1e-7 for v in parts.values())>1)))
    # Sum the extracted labels back into every original offer, independent of plot sorting.
    for j in np.flatnonzero((s['offer_zones']==ZONE)&~s['emergency_mask']):
        assert abs(sum(r['available_mw'] for r in rows if r['offer_column']==j)-m['availability'][t,j])<1e-5
    bus_zone=n.buses.bidding_zone.replace({'ES-IB-MA':'ES'});ids=n.loads.index[n.loads.bus.map(bus_zone)==ZONE]
    demand=float(n.get_switchable_as_dense('Load','p_set').loc[n.snapshots[t],ids].sum());fixed=demand-float(s['load'][t,zi]);domestic=float(reference['values'][t,:p['ng']][s['offer_zones']==ZONE].sum());model_price=float(reference['row_duals'][t,zi])
    assert np.maximum(reference['values'][t,:p['ng']][s['emergency_mask']],0).sum()<=1e-6
    target=ROOT/'data/price-trace/sdac-hourly-2025-v1';ts=json.loads((target/'summary.json').read_text());assert ts['zones']==p['zones'] and ts['prices_sha256']==digest(target/'prices.npz');observed=float(np.load(target/'prices.npz')['prices'][t,zi]);source_paths += [target/'summary.json',target/'prices.npz']
    files=[];path=ROOT/'research'/f'{NAME}.csv'
    with path.open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    files.append(path)
    fig,axes=plt.subplots(4,3,figsize=(14,12));summary=[]
    for ax,fuel in zip(axes.ravel(),TECH,strict=True):
        rr=[r for r in rows if r['technology']==fuel];mw=sum(r['available_mw'] for r in rr)
        row=dict(technology=fuel,name=NAMES[fuel],available_mw=mw,segments=len(rr),minimum_bid=min((r['bid_eur_mwh'] for r in rr),default=None),maximum_bid=max((r['bid_eur_mwh'] for r in rr),default=None));summary.append(row)
        ax.set_title(f'{NAMES[fuel]} · {mw/1000:.2f} GW',loc='left',fontweight='bold',fontsize=11)
        if rr:
            _,x,y=steps(rr);ax.step(x,y,where='post',color=COLORS[fuel],lw=2);ax.set_xlim(0,max(x[-1]*1.04,.001));span=max(np.ptp(y),10.);ax.set_ylim(y.min()-span*.15,y.max()+span*.2)
            ax.text(.03,.9,f"{row['minimum_bid']:.1f} to {row['maximum_bid']:.1f} €/MWh",transform=ax.transAxes,fontsize=9)
        else:
            ax.text(.5,.5,'No available offer volume\nin this hour',ha='center',va='center',transform=ax.transAxes,color='#666666');ax.set_xlim(0,1);ax.set_ylim(0,1)
        ax.set_xlabel('Cumulative available volume, GW',fontsize=9);ax.set_ylabel('Bid, €/MWh',fontsize=9);ax.grid(alpha=.2)
    fig.suptitle('Accepted baseline supply offers by technology · DE-LU\n15 July 2025, 12:00–13:00 UTC (14:00–15:00 CEST)',fontsize=16)
    fig.text(.5,.015,f'Each panel has its own axes. Fixed reservoir hydro: {fixed/1000:.2f} GW, outside these flexible curves. Availability is not dispatch.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.035,1,.94));path=ROOT/'research/assets'/f'{NAME}.png';fig.savefig(path,dpi=155);plt.close(fig);files.append(path)
    ordered,x,y=steps(rows);fig,ax=plt.subplots(figsize=(13,6.5));ax.step(x,y,where='post',color='#444444',lw=.6)
    for k,r in enumerate(ordered):ax.plot([x[k],x[k+1]],[y[k],y[k]],color=COLORS[r['technology']],lw=3,solid_capstyle='butt')
    ax.axhline(model_price,color='#245ac2',ls='--',label=f'Model clearing price {model_price:.2f} €/MWh')
    ax.axhline(observed,color='#222222',ls=':',label=f'Observed SDAC {observed:.2f} €/MWh')
    ax.axvline(s['load'][t,zi]/1000,color='#777777',ls='-.',lw=1,label=f'Demand less fixed hydro {s["load"][t,zi]/1000:.2f} GW')
    ax.set(xlabel='Cumulative domestic available supply, GW',ylabel='Bid, €/MWh',title='Combined DE-LU hourly supply curve · same offers sorted together\n15 July 2025, 12:00 UTC · network imports/exports determine the actual clearing')
    ax.grid(alpha=.2);handles,leglabels=ax.get_legend_handles_labels();handles += [Patch(color=COLORS[f],label=NAMES[f]) for f in TECH if any(r['technology']==f for r in rows)];leglabels += [NAMES[f] for f in TECH if any(r['technology']==f for r in rows)]
    ax.legend(handles,leglabels,loc='upper left',bbox_to_anchor=(1.01,1),fontsize=9)
    fig.text(.01,.015,f'Reservoir hydro {fixed/1000:.2f} GW is fixed, not an offer. Emergency backstop omitted from normal stack; it dispatched zero.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));path=ROOT/'research/assets'/f'{NAME}-combined.png';fig.savefig(path,dpi=150);plt.close(fig);files.append(path)
    lines=['# What the baseline supply curves look like','',f'**DE-LU, 15 July 2025 at 12:00–13:00 UTC (14:00–15:00 CEST).** Exact accepted `resource_full` bid prices and available MW, extracted without a new solve or fit. Curves change each hour as availability and bid inputs change.','',f'Native demand is **{demand/1000:.2f} GW**, fixed reservoir output **{fixed/1000:.2f} GW**, leaving **{s["load"][t,zi]/1000:.2f} GW** after that fixed injection. Network-constrained modeled price is **{model_price:.2f} €/MWh**, versus **{observed:.2f} €/MWh** observed ENTSO-E SDAC. These prices come from the full European clearing, not an isolated intersection of this domestic curve and demand.','',
        '![All technology curves](assets/'+NAME+'.png)','',
        'Each horizontal segment is an available volume offered at one price: width is GW, height is €/MWh. Segments are sorted within each technology. These are independently divisible hourly supply tranches; they are not all-or-nothing block orders. Multiple source groups can give more than three steps in the combined gas or coal curve. Panel axes differ to keep low-price and small-volume resources readable.','',
        '| Technology | Available GW | Lowest bid €/MWh | Highest bid €/MWh |','|---|---:|---:|---:|']
    for r in summary:lines.append(f"| {r['name']} | {r['available_mw']/1000:.3f} | {r['minimum_bid']:.2f} | {r['maximum_bid']:.2f} |" if r['segments'] else f"| {r['name']} | 0 | — | — |")
    lines += ['','![Combined zonal curve](assets/'+NAME+'-combined.png)','',
        'The combined curve sorts the same offers across all technologies. The demand marker excludes fixed reservoir hydro. Imports, exports, link losses and physical constraints participate in the European solve; an isolated supply-demand intersection would be a different calculation. Capacity is offered availability, not accepted dispatch or annual nameplate. The CSV retains source offer IDs, prices, capacities and tranche ranks.','',
        f'{mixed} source offers in this zone contain multiple technologies at identical bid prices. Their volumes are split for this display using current corrected PV components and remaining original member-availability shares, preserving each compiled offer’s total MW to within {partition_error:.3g} MW. This does not infer unique generator dispatch or distinct bidding behavior inside those pools. The plotted pieces remain fungible parts of the same original offer. Equal-price visual ordering is arbitrary.','',
        f'Reservoir hydro has no flexible price curve in this baseline. Batteries/PHS are not modeled as flexible offers. Nuclear has no offered volume in DE-LU in this example. Emergency backstop offers are separate artificial feasibility supply ({sum(r["available_mw"] for r in emergency)/1000:.2f} GW at '+', '.join(f'{v:.0f}' for v in sorted({r['bid_eur_mwh'] for r in emergency}))+' €/MWh); they are excluded from the normal curve scale and dispatch zero.','',
        '[Download the exact offer segments]('+NAME+'.csv). Source identity, hashes, plot exports and summary are retained in the local ignored `data/bidding-zone-network-2025/baseline-supply-curve-example-v1/` receipt. Baseline and public explorer unchanged.','']
    path=ROOT/'research'/f'{NAME}.md';path.write_text('\n'.join(lines));files.append(path)
    out=ROOT/'data/bidding-zone-network-2025/baseline-supply-curve-example-v1';out.mkdir(exist_ok=True)
    result=dict(producer_sha256=digest(__file__),zone=ZONE,hour_utc=HOUR+':00Z',model=active['model'],case=active['annual_case'],demand_mw=demand,fixed_reservoir_mw=fixed,model_price_eur_mwh=model_price,observed_price_eur_mwh=observed,domestic_flexible_dispatch_mw=domestic,technology_summary=summary,emergency=emergency,mixed_source_offers=int(mixed),maximum_partition_error_mw=float(partition_error),sources={str(f.relative_to(ROOT)):digest(f) for f in source_paths},exports={str(f.relative_to(ROOT)):digest(f) for f in files})
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['demand_mw','fixed_reservoir_mw','model_price_eur_mwh','observed_price_eur_mwh','technology_summary']},indent=2),flush=True)


if __name__=='__main__':logging.getLogger('pypsa').setLevel(logging.ERROR);report()
