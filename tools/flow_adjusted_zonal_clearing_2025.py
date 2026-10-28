"""Retrospective supply-bid clearing at observed A09 net import, with strict coverage.

This diagnoses bids conditional on observed exchanges. It is not a network or
investment scenario solver: changed assets need newly cleared flows.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import numpy as np

from collect_entsoe_flows_2025 import OUT as FLOWS, PERIOD, plan
from flow_tracing import ROOT, parse_quantity
from run_batched_transport_2025 import setup
from supply_knot_splines_2025 import initial_parameters

DEST=ROOT/'data/eu-market/flow-adjusted-clearing-2025'
START=datetime(2025,1,1,tzinfo=timezone.utc)


def observed_exchanges(zones,edges):
    """Hourly net imports, only when every incident directed series is covered."""
    codes={z:eic for a,b,ca,cb in plan() for z,eic in ((a,ca),(b,cb))}
    allowed={(a,b) for a,b,_,_ in plan()} | {(b,a) for a,b,_,_ in plan()}
    directional={}
    for i,j in edges:
        a,b=zones[i],zones[j]
        if (a,b) not in allowed:continue
        for source,sink in ((a,b),(b,a)):
            request=dict(PERIOD,documentType='A09',out_Domain=codes[source],
                         in_Domain=codes[sink],**{'contract_MarketAgreement.Type':'A01'})
            key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]
            path=FLOWS/'raw'/(key+'.xml')
            if not path.exists():continue
            raw=path.read_bytes();meta=json.loads(path.with_suffix('.json').read_text())
            if meta['request']!=request or meta['sha256']!=hashlib.sha256(raw).hexdigest():
                raise ValueError('Exchange source/receipt mismatch')
            try:samples=parse_quantity(raw,{'out_Domain.mRID':codes[source],
                                            'in_Domain.mRID':codes[sink]})
            except ValueError:continue  # Acknowledgement means missing, not zero.
            quarters=np.full(8760*4,np.nan)
            for stamp,mw in samples.items():
                idx=(stamp-START)/timedelta(minutes=15)
                if int(idx)!=idx or not 0<=idx<len(quarters):raise ValueError('Invalid exchange time')
                quarters[int(idx)]=mw
            blocks=quarters.reshape(8760,4)
            directional[source,sink]=np.where(np.isfinite(blocks).all(axis=1),
                                              blocks.mean(axis=1)/1000,np.nan)
    net=np.zeros((8760,len(zones)));covered=np.ones((8760,len(zones)),bool)
    for i,j in edges:
        a,b=zones[i],zones[j]
        outgoing=directional.get((a,b));incoming=directional.get((b,a))
        if outgoing is None or incoming is None:
            covered[:,[i,j]]=False;continue
        good=np.isfinite(outgoing)&np.isfinite(incoming)
        covered[:,i]&=good;covered[:,j]&=good
        balance=incoming-outgoing
        net[:,i]+=np.where(good,balance,0)
        net[:,j]-=np.where(good,balance,0)
    return net,covered,len(directional)


def clear_independent(market,theta,net,covered,hours):
    offers=market.offers(theta,hours)
    target=market.load[hours]-net[hours]
    valid=covered[hours].copy()
    zone_cap=offers['capacity']@market.Z
    valid &= (target>=-1e-8)&(target<=zone_cap+1e-8)
    lo=np.full(target.shape,-1000.);hi=np.full(target.shape,3000.)
    for _ in range(48):
        mid=(lo+hi)/2
        q,_=market.supply(mid,offers)
        generated=q@market.Z
        lo=np.where(generated<target,mid,lo)
        hi=np.where(generated>=target,mid,hi)
    price=(lo+hi)/2
    q,_=market.supply(price,offers)
    residual=q@market.Z-target
    valid &= abs(residual)<1e-6
    return price,q,valid,residual


def main():
    state,market,_,_=setup();s,d,*_=state
    net,covered,directions=observed_exchanges(s['zones'],market.edges)
    theta=initial_parameters(len(s['groups']))[:,[0,5,6,7,8,9]]
    prices=[];valid=[];residual=[]
    for hours in np.array_split(np.arange(8760),12):
        p,q,v,r=clear_independent(market,theta,net,covered,hours)
        prices.append(p);valid.append(v);residual.append(r)
    prices=np.concatenate(prices);valid=np.concatenate(valid);residual=np.concatenate(residual)
    observed=d['observed_prices'];matched=valid&np.isfinite(observed)
    per_zone=[]
    for j,z in enumerate(s['zones']):
        mask=matched[:,j]
        per_zone.append(dict(zone=z,covered_hours=int(covered[:,j].sum()),
            cleared_hours=int(valid[:,j].sum()),matched_price_hours=int(mask.sum()),
            price_mae_eur_mwh=float(abs(prices[mask,j]-observed[mask,j]).mean()) if mask.any() else None))
    summary=dict(status='retrospective_observed_flow_diagnostic',zones=len(s['zones']),hours=8760,
        source_directions=directions,covered_zone_hours=int(covered.sum()),
        cleared_zone_hours=int(valid.sum()),matched_price_cells=int(matched.sum()),
        price_mae_eur_mwh=float(abs(prices[matched]-observed[matched]).mean()) if matched.any() else None,
        maximum_cleared_balance_mw=float(abs(residual[valid]).max()*1000) if valid.any() else None,
        per_zone=per_zone,
        limitation='Only full incident A09/A01 coverage; fixed historical exchanges; neutral technology bids; no scenario flow response.')
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    np.savez_compressed(DEST/'witness.npz',prices=prices,valid=valid,net_import_gw=net,covered=covered)
    print(json.dumps({k:v for k,v in summary.items() if k!='per_zone'},indent=2))


if __name__=='__main__':main()
