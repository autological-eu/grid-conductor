"""Preserve original member IDs for future zone mapping; do not assign zones."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
import xarray as xr
from hourly_renewable_estimates import digest


def run(network, expected, busmap, output):
    if output.exists():raise ValueError('Use a fresh diagnostic path')
    if digest(network)!=expected:raise ValueError('Source network hash mismatch')
    rows=list(csv.DictReader(busmap.open()))
    if not rows or len({r['name'] for r in rows})!=len(rows) or any(not r['name'] or not r['busmap'] for r in rows):
        raise ValueError('Complete unique member identities required')
    counts=Counter(r['busmap'] for r in rows)
    with xr.open_dataset(network) as d:
        if set(counts)!=set(d.buses_i.values):raise ValueError('Complete known cluster coverage required')
    report=dict(status='cluster_membership_diagnostic_not_zonal_mapping',network_sha256=expected,
                busmap_sha256=digest(busmap),producer_sha256=digest(__file__),
                original_members=len(rows),clusters=len(counts),members=rows,
                limitations=['All original member IDs retained; no geographic positions or accepted zones inferred.',
                             'Original member and asset positions plus period-specific polygons remain required.',
                             'No pooling, input changes or solve performed.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Preserved {len(rows)} members across {len(counts)} known clusters.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['network','busmap','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    a=p.parse_args();run(a.network,a.expected_sha256,a.busmap,a.output)
