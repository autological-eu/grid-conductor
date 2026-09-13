"""Phase A gate: per-record coverage manifest for the FR–CH market pilot.

Reads the cached input + provenance and the experiment validation to emit a
machine-readable manifest and a human coverage report. Offline, standard
library only, no API key.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from carbon_pilot import ROOT
from build_market_pilot import DOMAINS, NEIGHBORS

MARKET=ROOT/'data/carbon-pilot/market'
FLOW=ROOT/'data/carbon-pilot/flow-tracing/raw'
SOURCE='ENTSO-E Transparency Platform'
LICENSE_NOTE='ENTSO-E open data terms; no redistribution guarantee beyond research use. Electricity Maps prices used only as a diagnostic benchmark, not ingested.'


def xml_details(raw):
    root=ET.fromstring(raw)
    for e in root.iter():e.tag=e.tag.split('}')[-1]
    resolution=None;curve=None;unit=None
    for ts in root.findall('TimeSeries'):
        curve=curve or ts.findtext('curveType')
        unit=unit or ts.findtext('quantity_Measure_Unit.name')
        for period in ts.findall('Period'):
            resolution=resolution or period.findtext('resolution')
    return dict(resolution=resolution,curve=curve,unit=unit,publication_time=root.findtext('createdDateTime'))


def key_for(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]


def record(request,directory):
    key=key_for(request);body=Path(directory)/(key+'.xml');meta_path=Path(directory)/(key+'.json')
    if not body.exists() or not meta_path.exists():return None
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    info=dict(request=request,file=str(body.relative_to(ROOT)),retrieved_at=meta.get('retrieved_at'),
        sha256=dict(computed=hashlib.sha256(body.read_bytes()).hexdigest(),recorded=meta.get('sha256')))
    try:
        info.update(xml_details(body.read_bytes()))
    except (ET.ParseError,ValueError):
        info.update(resolution=None,curve=None,unit=None,publication_time=None)
    return info


def main():
    data=json.loads((MARKET/'input.json').read_text(encoding='utf-8'))
    records=[]
    for entry in data['provenance'].get('requests',[]):
        request=entry['request'];key=key_for(request)
        directory=MARKET/'raw' if (MARKET/'raw'/(key+'.json')).exists() else FLOW
        info=record(request,directory)
        if info is not None:records.append(info)
    experiment_path=ROOT/'public/research/market-experiment.json'
    validation=json.loads(experiment_path.read_text(encoding='utf-8')).get('validation',{}) if experiment_path.exists() else {}
    manifest=dict(
        model='linked-dispatch-v1 FR–CH pilot',period=dict(start=data['timestamps'][0],end=data['timestamps'][-1],
            interval_hours=data['interval_hours'],interval_count=len(data['timestamps'])),
        source=SOURCE,license_note=LICENSE_NOTE,
        mapping={z:dict(eic=d,neighbors=NEIGHBORS.get(z)) for z,d in DOMAINS.items() if z in data['zones']},
        records=records,zone_coverage={
            z:dict(generation_types=audit['generation_types'],
                balance_residual_mae_mw=audit['balance_residual_mae_mw'],
                price_benchmark=validation.get(z),
                installed_capacity_available=audit['generator_installed_capacity_available'])
            for z,audit in data['provenance']['audit'].items()},
        missing_status_note='Missing quarters stay missing (never zero-filled); capacity, load and flow gaps raise during assembly.',
        generated_at=datetime.now(timezone.utc).isoformat())
    out=ROOT/'public/research/coverage-manifest.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    lines=['# FR–CH market-pilot coverage manifest','',
        f"Period **{manifest['period']['start']}** through **{manifest['period']['end']}**, "
        f"{manifest['period']['interval_count']} hourly intervals. Source: {SOURCE}.",
        manifest['license_note'],'',
        '| Record | Document type | Domain | Unit | Resolution | Curve | Publication | Retrieved |',
        '|---|---|---|---|---|---|---|---|']
    for r in records:
        req=r['request'];kind=req.get('documentType','A75')
        domain=req.get('in_Domain') or req.get('out_Domain') or req.get('outBiddingZone_Domain') or req.get('inBiddingZone_Domain')
        lines.append(f"| {r['file']} | {kind} | `{domain}` | {r.get('unit')} | {r.get('resolution')} | {r.get('curve')} | {r.get('publication_time')} | {r.get('retrieved_at')} |")
    lines+=['','## Remaining gaps and gates','',
            '- Observed price benchmark and balance residuals are in the machine manifest; no annual rank is attributed.',
            '- Installed capacity and outage-adjusted availability are not used (explicit audit flags).',
            '- Missing quarters or capacity records raise during assembly; they are never zero-filled.','']
    doc=ROOT/'docs/market-model-coverage.md';doc.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(records=len(records),zones=list(manifest['zone_coverage']),report=str(doc)),indent=2))


if __name__=='__main__':main()