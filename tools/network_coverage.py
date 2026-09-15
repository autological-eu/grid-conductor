"""Separate published network evidence coverage from readiness for dispatch."""
import argparse
import json
from pathlib import Path
from carbon_pilot import ROOT

CORE={'AT','BE','CZ','DE-LU','FR','HR','HU','NL','PL','RO','SI','SK'}
NORDIC={'DK1','DK2','FI','SE1','SE2','SE3','SE4','NO1','NO2','NO3','NO4','NO5'}


def summarize(bank, quality, publications):
    regions={r['region']:r for p in publications for r in p['regions']}
    rows=[]
    for a,b in bank['interior_borders']:
        region='core' if {a,b}<=CORE else 'nordic' if {a,b}<=NORDIC else None
        for source,target in [(a,b),(b,a)]:
            key=source+'>'+target
            ntc=quality['coverage']['capacity/'+key]['coverage']
            publication=regions.get(region,{}) if region else {}
            regional=publication.get('month')==bank['month'] and publication.get('published_hour_coverage')==1
            rows.append(dict(direction=key,region=region,ntc_hour_coverage=ntc,
                evidence='JAO regional domain' if regional else 'ENTSO-E estimated NTC' if ntc==1 else 'unresolved',
                dispatch_ready=False,
                note='Region-wide constraints cannot be replaced by independent border limits' if regional else 'Requires market-horizon and topology reconciliation'))
    return dict(month=bank['month'],expected_directions=len(rows),
        directions_with_published_network_evidence=sum(r['evidence']!='unresolved' for r in rows),
        market_baseline_validated=False,annual_opportunity_meur=None,directions=rows,
        interpretation='Publication availability only: region membership plus complete monthly timestamps does not validate hybrid hub mappings, LTA inclusion or supply and demand.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank',type=Path,default=ROOT/'data/eu-market/bank-2026-01-v2.json')
    p.add_argument('--quality',type=Path,default=ROOT/'public/research/january-2026/eu-input-quality.json')
    p.add_argument('--jao',type=Path,nargs='+',default=[ROOT/'public/research/jao-january-coverage.json',ROOT/'public/research/jao-nordic-january-coverage.json'])
    args=p.parse_args()
    result=summarize(json.loads(args.bank.read_text()),json.loads(args.quality.read_text()),[json.loads(p.read_text()) for p in args.jao])
    out=ROOT/'public/research/network-evidence-coverage.json'
    out.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(result['directions_with_published_network_evidence'],'/',result['expected_directions'],'directions with published network evidence; dispatch not yet validated')


if __name__=='__main__':main()
