"""Independent replay: filter auction XML, then use frozen interval decoder.

Separately cross-check full-year hourly DE/AT/DK against Energy-Charts. Those
reference observations never enter the target matrix.
"""
import datetime as dt
import json
import xml.etree.ElementTree as ET
import numpy as np
from sdac_prices_2025 import ROOT,OUT,START,END,sha
from flow_tracing import parse_day_ahead_prices,hourly

def audit():
    s=json.loads((OUT/'summary.json').read_text());assert s['producer_sha256']==sha(ROOT/'tools'/s['producer_file'])
    for name,digest in s['source_hashes'].items():assert sha(ROOT/name)==digest
    assert sha(OUT/'prices.npz')==s['prices_sha256']
    with np.load(OUT/'prices.npz') as z:expected=z['prices']
    result=np.full_like(expected,np.nan)
    for area in s['areas']:
        zone=area['zone'];quarters={}
        for receipt in area['receipts']:
            root=ET.fromstring((ROOT/receipt['path']).read_bytes())
            for e in root.iter():e.tag=e.tag.split('}')[-1]
            for ts in list(root.findall('TimeSeries')):
                seq=ts.findtext('classificationSequence_AttributeInstanceComponent.position')
                keep=ts.findtext('contract_MarketAgreement.type')=='A01' and (seq=='1' if zone in ['DE-LU','AT'] else seq is None)
                if not keep:root.remove(ts)
            samples=parse_day_ahead_prices(ET.tostring(root));req=receipt['request']
            a=dt.datetime.strptime(req['periodStart'],'%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc);b=dt.datetime.strptime(req['periodEnd'],'%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc)
            for t,v in samples.items():
                if max(START,a)<=t<min(END,b):
                    assert t not in quarters or quarters[t]==v;quarters[t]=v
        for h in range(8760):
            v=hourly(quarters,START+dt.timedelta(hours=h))
            if v is not None:result[h,s['zones'].index(zone)]=v
    np.testing.assert_array_equal(result,expected)
    accepted=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1'
    with np.load(accepted/'development-targets.npz') as z:first=z['prices']
    with np.load(accepted/'evaluation-targets.npz') as z:old=np.r_[first,z['prices']]
    np.testing.assert_array_equal(np.isfinite(old),np.isfinite(expected))
    changes=[];references=[]
    for j,zone in enumerate(s['zones']):
        good=np.isfinite(expected[:,j]);delta=abs(old[good,j]-expected[good,j]);changes.append(dict(zone=zone,known_hours=int(good.sum()),changed_hours=int((delta>1e-9).sum()),maximum_change_eur_mwh=float(delta.max()) if good.any() else None))
    refroot=ROOT/'data/price-trace/sdac-reference-2025-v1';receipts=json.loads((refroot/'receipts.json').read_text())
    for zone in ['DE-LU','AT','DK1','DK2']:
        path=refroot/(zone+'.json');assert sha(path)==receipts[zone]['sha256'];doc=json.loads(path.read_text());assert doc['unit']=='EUR / MWh'
        t=doc['unix_seconds'];values=doc['price'];quarters={}
        for i in range(len(t)-1):
            a=dt.datetime.fromtimestamp(t[i],dt.timezone.utc);b=dt.datetime.fromtimestamp(t[i+1],dt.timezone.utc)
            if not START<=a<END:continue
            minutes=int((b-a).total_seconds()/60);assert minutes in [15,30,60] and values[i] is not None
            for q in range(minutes//15):quarters[a+dt.timedelta(minutes=q*15)]=float(values[i])
        ref=np.array([hourly(quarters,START+dt.timedelta(hours=h)) for h in range(8760)],float);assert np.isfinite(ref).all()
        target=expected[:,s['zones'].index(zone)];difference=abs(ref-target)
        # Independent providers can differ at rounding precision; report, never replace.
        assert difference.max()<.011,(zone,difference.max())
        references.append(dict(zone=zone,hours=8760,maximum_difference_eur_mwh=float(difference.max()),mean_absolute_difference_eur_mwh=float(difference.mean()),reference=receipts[zone]))
    map_checks=[]
    for j,zone in enumerate(s['zones']):
        path=ROOT/'public/research/zone-prices-2025'/(zone+'.json')
        if not path.exists():continue
        archived=np.array(json.loads(path.read_text()),float);good=np.isfinite(archived);assert np.isfinite(expected[good,j]).all()
        np.testing.assert_allclose(archived[good],expected[good,j],rtol=0,atol=1e-10)
        map_checks.append(dict(zone=zone,known_hours=int(good.sum()),maximum_difference_eur_mwh=float(abs(archived[good]-expected[good,j]).max()) if good.any() else None,path=str(path.relative_to(ROOT)),sha256=sha(path)))
    out=dict(map_price_checks=map_checks,status='all_raw_A44_auction_hourly_targets_replayed',hours=8760,eligible_zones=int(np.isfinite(expected).all(axis=0).sum()),summary_sha256=sha(OUT/'summary.json'),producer_sha256=s['producer_sha256'],auditor_file=__file__.split('/')[-1],auditor_sha256=sha(__file__),changes=changes,independent_full_year_references=references)
    (OUT/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':audit()
