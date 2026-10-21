"""Source-only spike/auction-selection diagnosis; preserves frozen price pipeline.

Reference: Energy-Charts price API, sourced from Bundesnetzagentur/SMARD.
No target replacement, price fit, market solve or production parser mutation.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from flow_tracing import parse_day_ahead_prices, hourly

ROOT=Path(__file__).resolve().parents[1]
REFERENCE_URL='https://api.energy-charts.info/price?bzn=DE-LU&start=2025-01-15&end=2025-01-21'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(reference, out):
    manifest_path=ROOT/'data/price-trace/dispatch-validation-2025-v2/manifest.json'
    manifest=json.loads(manifest_path.read_text());zone=manifest['zones']['DE-LU']
    receipt=next(r for r in zone['receipts']if r['month']==1)
    key=hashlib.sha256(json.dumps(receipt['request'],sort_keys=True).encode()).hexdigest()[:24]
    xml=ROOT/'data/price-trace/entsoe/DE-LU'/(key+'.xml')
    assert digest(xml)==receipt['sha256']
    root=ET.fromstring(xml.read_bytes())
    for e in root.iter():e.tag=e.tag.split('}')[-1]
    by_sequence={}
    for sequence in [1,2]:
        doc=ET.Element('Publication_MarketDocument')
        for ts in root.findall('TimeSeries'):
            assert ts.findtext('in_Domain.mRID')==zone['price_eic']==ts.findtext('out_Domain.mRID')
            if ts.findtext('classificationSequence_AttributeInstanceComponent.position')==str(sequence):doc.append(ts)
        assert len(doc)>0
        by_sequence[sequence]=parse_day_ahead_prices(ET.tostring(doc))
    ref=json.loads(reference.read_text());assert ref['unit'].replace(' ','')=='EUR/MWh'
    differences=[]
    for seconds,price in zip(ref['unix_seconds'],ref['price']):
        time=dt.datetime.fromtimestamp(seconds,dt.timezone.utc)
        reconstructed=hourly(by_sequence[1],time)
        assert reconstructed is not None and price is not None
        differences.append(abs(reconstructed-price))
    assert len(differences)==168 and max(differences)<1e-9
    folder=ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2'
    summary=json.loads((folder/'summary.json').read_text());audit=json.loads((folder/'audit.json').read_text())
    assert audit['status']=='passed' and audit['summary_sha256']==digest(folder/'summary.json')
    for filename,sha in summary['files'].items():assert digest(folder/filename)==sha
    meta=json.loads((folder/'offers.json').read_text());zi=summary['zones'].index('DE-LU')
    with np.load(folder/'offers.npz')as z:
        arrays={k:z[k]for k in ['availability','dispatch','prices','net_load','fixed_hydro','observed_prices']}
    clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC');local=clock.tz_convert('Europe/Berlin')
    explorer=ROOT/'public/research/country-explorer-2025';mf=json.loads((explorer/'manifest.json').read_text())
    country=next(r for r in mf['countries']if r['code']=='DE');path=explorer/country['file'];assert digest(path)==country['sha256']
    data=json.loads(gzip.decompress(path.read_bytes()));area=next(r for r in data['generation']if r['id']=='country:DE')
    def generation(name,t):
        index=next(i for i,r in enumerate(mf['technologies'])if r['id']==name)
        value=data['series'][area['observed'][index]][t]
        assert value is not None
        return value/mf['generation_scale']
    wind=[r['column']for r in meta if r['zone']=='DE-LU'and r['category']=='Wind/solar']
    gas=[r['column']for r in meta if r['zone']=='DE-LU'and r['category']=='Gas']
    days=[]
    for date in ['2025-01-15','2025-01-20']:
        times=np.flatnonzero(local.strftime('%Y-%m-%d')==date)
        prices=[hourly(by_sequence[1],clock[t].to_pydatetime())for t in times]
        assert all(p is not None for p in prices)
        t=int(times[np.argmax(prices)]);stamp=clock[t].to_pydatetime()
        selected=hourly(by_sequence[2],stamp)
        assert abs(arrays['observed_prices'][t,zi]-selected)<1e-9
        days.append(dict(date=date,peak_local=local[t].isoformat(),sdac_peak_eur_mwh=float(max(prices)),
            retained_target_at_peak_eur_mwh=float(arrays['observed_prices'][t,zi]),
            model_at_peak_eur_mwh=float(arrays['prices'][t,zi]),
            prepared_load_gw=float((arrays['net_load'][t,zi]+arrays['fixed_hydro'][t,zi])/1000),
            model_available_wind_solar_gw=float(arrays['availability'][t,wind].sum()/1000),
            german_observed_wind_solar_gw=sum(generation(k,t)for k in ['onshore_wind','offshore_wind','solar'])/1000,
            model_gas_available_gw=float(arrays['availability'][t,gas].sum()/1000),
            model_gas_dispatch_gw=float(arrays['dispatch'][t,gas].sum()/1000)))
    sources=[manifest_path,xml,folder/'summary.json',folder/'audit.json',folder/'offers.npz',folder/'offers.json',explorer/'manifest.json',path,ROOT/'tools/flow_tracing.py']
    result=dict(status='confirmed_DE_January_auction_selection_mismatch',producer_sha256=digest(Path(__file__)),
        source_hashes={str(p.relative_to(ROOT)):digest(p)for p in sources},reference_url=REFERENCE_URL,
        reference_sha256=digest(reference),reference_license=ref['license_info'],matched_reference_hours=168,
        sequence1_reference_max_difference=max(differences),days=days,new_solves=0,
        limitations=['Only DE January 15–21 independently cross-checked here; other zones/year need fresh explicit auction audit.',
          'Preserved old pipeline prefers the highest sequence. Reproducing that parser is not validation of SDAC market identity.',
          'Available wind/solar differs in meaning from observed generation; no generation-as-availability substitution.',
          'Unused model gas capacity is not necessarily deliverable; this is a diagnostic, not a causal error decomposition.',
          'Frozen benchmark data/fits are unchanged; prior price-accuracy claims require corrected-auction re-evaluation.'])
    out.mkdir(parents=True,exist_ok=False)
    (out/'reference.json').write_bytes(reference.read_bytes())
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','matched_reference_hours','sequence1_reference_max_difference','days']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.reference,a.output)
