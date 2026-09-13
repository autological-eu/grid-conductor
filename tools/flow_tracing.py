"""Independent ENTSO-E flow-tracing research pilot; no Electricity Maps inputs."""
import argparse
from collections import Counter
from contextlib import closing
import datetime as dt
import hashlib
import json
import math
import os
import sqlite3
import statistics
from pathlib import Path
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

from carbon_pilot import (AREAS as GENERATION_AREAS, FACTORS, FACTOR_VERSION, IPCC, ROOT, UTC, iso, STORAGE,
                          parse_generation, calculate)

# Explicit pilot geography, not a claim to cover the whole European grid.
AREAS = dict(GENERATION_AREAS, GB="10YGB----------A")
AREAS.update({"NO-NO2": "10YNO-2--------T", "SE-SE4": "10Y1001A1001A47J"})
del AREAS['DE']
AREAS['DE-LU'] = '10Y1001A1001A82H'
EXTERNAL = {"BE": "10YBE----------2", "NL": "10YNL----------L",
            "CH": "10YCH-SWISSGRIDZ", "ES": "10YES-REE------0",
            "IT-NO": "10Y1001A1001A73I", "AT": "10YAT-APG------L",
            "CZ": "10YCZ-CEPS-----N", "PL": "10YPL-AREA-----S",
            "LU": "10YLU-CEGEDEL-NQ", "IE": "10Y1001A1001A59C",
            "NO-NO1": "10YNO-1--------2", "NO-NO5": "10Y1001A1001A48H",
            "SE-SE3": "10Y1001A1001A46L"}
# Domain coverage failures stay missing rather than becoming zero flows.
NEIGHBORS = {
    "FR": "BE DE GB CH ES IT-NO".split(),
    "DE": "FR NL BE CH AT CZ PL LU DK-DK1 DK-DK2 NO-NO2 SE-SE4".split(),
    "DK-DK1": "DE DK-DK2 NL GB NO-NO2 SE-SE3".split(),
    "DK-DK2": "DE DK-DK1 SE-SE4".split(),
    "GB": "FR BE NL DK-DK1 NO-NO2 IE".split(),
    "NO-NO2": "DE DK-DK1 GB NL NO-NO1 NO-NO5".split(),
    "SE-SE4": "DE DK-DK2 PL LT SE-SE3".split(),
}
EXTERNAL["LT"] = "10YLT-1001A0008Q"
NEIGHBORS = {('DE-LU' if z == 'DE' else z):
             [('DE-LU' if b == 'DE' else b) for b in neighbors if b != 'LU']
             for z,neighbors in NEIGHBORS.items()}
del EXTERNAL['LU']


def solve(matrix, rhs):
    """Partial-pivot Gaussian elimination, rejecting unanchored flow loops."""
    n = len(rhs)
    a = [list(row) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for k in range(n):
        pivot = max(range(k, n), key=lambda i: abs(a[i][k]))
        if abs(a[pivot][k]) < 1e-10:
            raise ValueError("Singular flow network")
        a[k], a[pivot] = a[pivot], a[k]
        v = a[k][k]
        a[k] = [x / v for x in a[k]]
        for i in range(n):
            if i != k:
                v = a[i][k]
                a[i] = [x - v*y for x, y in zip(a[i], a[k])]
    return [row[-1] for row in a]


def trace(nodes, edges, upper=1500):
    """Nodes: generation, known emissions (kg), unknown MWh, load, charging.

    Edges are directed MWh. Boundary imports and storage discharge are tagged
    unknown, not assigned a neighboring production average. Residual deficits
    become unknown supply; surpluses are unallocated sinks, never called losses.
    """
    names = sorted(nodes)
    if not math.isfinite(upper) or upper < 0:
        raise ValueError('Invalid sensitivity assumption')
    index = {z: i for i, z in enumerate(names)}
    n = len(names)
    matrix = [[0.0]*n for _ in names]
    known, unknown, residuals = [], [], {}
    for z in names:
        item = nodes[z]
        if any(not math.isfinite(v) or v < 0 for v in item.values()):
            raise ValueError("Invalid node input")
        if item['unknown'] > item['generation']:
            raise ValueError('Unknown supply exceeds generation')
        imports = sum(v for (a,b),v in edges.items() if b == z)
        exports = sum(v for (a,b),v in edges.items() if a == z)
        supply = item['generation'] + imports
        demand = item['load'] + item['charging'] + exports
        deficit = max(0, demand-supply)
        total = supply + deficit
        if total <= 0:
            raise ValueError("Empty node")
        matrix[index[z]][index[z]] = total
        boundary = sum(v for (a,b),v in edges.items() if b == z and a not in index)
        unknown.append(item['unknown'] + boundary + deficit)
        known.append(item['emissions'])
        residuals[z] = (supply-demand, total)
    for (a,b),value in edges.items():
        if not math.isfinite(value) or value < 0 or a == b:
            raise ValueError("Invalid flow")
        if a in index and b in index:
            matrix[index[b]][index[a]] -= value
    low, share = solve(matrix, known), solve(matrix, unknown)
    result = {}
    for z,i in index.items():
        residual,total = residuals[z]
        u = min(1.0, max(0.0, share[i]))
        result[z] = dict(sensitivity_low=low[i], sensitivity_high=low[i]+upper*u,
            unresolved_supply_share=u, carbon_intensity=low[i] if u < 1e-10 else None,
            balance_residual_mwh=residual, balance_residual_share=abs(residual)/total,
            quality="provisional" if abs(residual)/total <= .05 else "large_balance_residual")
    return result


def benchmark(rows, archive):
    """Read the comparison archive only AFTER solving; never feeds the solver."""
    with closing(sqlite3.connect(archive.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        lookup = {(z,t):(v,e) for z,t,v,e in db.execute(
            "SELECT zone,start,value,estimated FROM observations WHERE metric='carbon' AND start>=? AND start<=?",
            (min(r['start'] for r in rows),max(r['start'] for r in rows)))}
    report = {}
    for z in sorted({r['zone'] for r in rows}):
        if z == 'DE-LU':
            report[z] = dict(status='not_compared: archive DE geography differs from DE-LU')
            continue
        pairs = [(r,lookup[z,r['start']]) for r in rows if r['zone']==z
                 and r.get('quality') == 'provisional' and (z,r['start']) in lookup
                 and lookup[z,r['start']][0] is not None]
        report[z] = dict(matched_hours=len(pairs),estimated_benchmark_hours=sum(bool(v[1]) for _,v in pairs))
        if pairs:
            report[z].update(pilot_low_mean=statistics.mean(r['sensitivity_low'] for r,_ in pairs),
                pilot_high_mean=statistics.mean(r['sensitivity_high'] for r,_ in pairs),
                benchmark_mean=statistics.mean(v[0] for _,v in pairs),
                unresolved_share_mean=statistics.mean(r['unresolved_supply_share'] for r,_ in pairs))
    return report


def fetch(params, directory):
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:24]
    path = directory / (key + '.xml')
    meta = path.with_suffix('.json')
    if path.exists() and meta.exists():
        raw = path.read_bytes()
        metadata = json.loads(meta.read_text())
        if metadata['sha256'] != hashlib.sha256(raw).hexdigest() or metadata['request'] != params:
            raise ValueError('Cache mismatch')
        return raw
    token = os.environ.get('ENTSOE_API_KEY')
    if not token:
        raise ValueError('Missing ENTSOE_API_KEY and no cached response')
    url = 'https://web-api.tp.entsoe.eu/api?' + urllib.parse.urlencode(dict(params, securityToken=token))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise ValueError(f'ENTSO-E HTTP {error.code}') from None
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('ENTSO-E network failure') from None
    directory.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    meta.write_text(json.dumps(dict(request=params, retrieved_at=iso(dt.datetime.now(UTC)),
        sha256=hashlib.sha256(raw).hexdigest()), indent=2))
    return raw


def parse_quantity(raw, expected):
    root = ET.fromstring(raw)
    for e in root.iter():
        e.tag = e.tag.split('}')[-1]
    if root.tag == 'Acknowledgement_MarketDocument':
        raise ValueError('No quantity data returned')
    # Reuse the strict period/curve parser after validating quantity metadata.
    out = ET.Element('GL_MarketDocument')
    for ts in root.findall('TimeSeries'):
        for field,value in expected.items():
            if ts.findtext(field) != value:
                raise ValueError(f'Unexpected quantity domain: {field}')
        if ts.findtext('quantity_Measure_Unit.name') != 'MAW':
            raise ValueError('Expected MW')
        clean = ET.SubElement(out, 'TimeSeries')
        for tag,value in [('businessType','A01'), ('objectAggregation','A08'),
                          ('inBiddingZone_Domain.mRID','quantity'),
                          ('quantity_Measure_Unit.name','MAW'), ('curveType',ts.findtext('curveType'))]:
            ET.SubElement(clean,tag).text = value
        ET.SubElement(ET.SubElement(clean,'MktPSRType'),'psrType').text = 'quantity'
        for period in ts.findall('Period'):
            clean.append(period)
    return parse_generation(ET.tostring(out), 'quantity')['quantity']


def hourly(samples, hour):
    values = [samples.get(hour+dt.timedelta(minutes=15*i)) for i in range(4)]
    return None if any(v is None for v in values) else sum(values)/4


def charging(raw, area):
    root = ET.fromstring(raw)
    for e in root.iter():
        e.tag = e.tag.split('}')[-1]
    out = ET.Element('GL_MarketDocument')
    for ts in root.findall('TimeSeries'):
        e = ts.find('outBiddingZone_Domain.mRID')
        if e is not None and ts.findtext('MktPSRType/psrType') in STORAGE:
            if e.text != area:
                raise ValueError('Unexpected charging area')
            e.tag = 'inBiddingZone_Domain.mRID'
            out.append(ts)
    return parse_generation(ET.tostring(out),area) if len(out) else {}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--month', default='2026-08')
    p.add_argument('--output', type=Path, default=ROOT/'data/carbon-pilot/flow-tracing')
    p.add_argument('--archive',type=Path,help='Optional Electricity Maps benchmark, read after solving')
    args = p.parse_args()
    start = dt.datetime.strptime(args.month,'%Y-%m').replace(tzinfo=UTC)
    end = (start.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
    period = dict(periodStart=start.strftime('%Y%m%d%H%M'),periodEnd=end.strftime('%Y%m%d%H%M'))
    generation, charges, loads, flows, errors = {}, {}, {}, {}, {}
    domains = dict(EXTERNAL, **AREAS)
    for z in AREAS:
        try:
            raw = fetch(dict(period,documentType='A75',processType='A16',in_Domain=AREAS[z]),args.output/'raw')
            generation[z] = {r['start']:r for r in calculate(parse_generation(raw,AREAS[z]),z,start,end)}
            charges[z] = charging(raw,AREAS[z])
            raw = fetch(dict(period, documentType='A65',processType='A16',outBiddingZone_Domain=AREAS[z]),args.output/'raw')
            loads[z] = parse_quantity(raw,{'outBiddingZone_Domain.mRID':AREAS[z]})
        except (ValueError, RuntimeError) as error:
            errors[z] = str(error)
        print('Node',z,errors.get(z,'downloaded'),flush=True)
    borders = sorted({tuple(sorted((z,b))) for z,neighbors in NEIGHBORS.items() for b in neighbors})
    for a,b in borders:
        for source,target in [(a,b),(b,a)]:
            try:
                raw = fetch(dict(period,documentType='A11',out_Domain=domains[source],in_Domain=domains[target]),args.output/'raw')
                flows[source,target] = parse_quantity(raw,{'out_Domain.mRID':domains[source],'in_Domain.mRID':domains[target]})
            except (ValueError,RuntimeError) as error:
                errors[source+'>'+target] = str(error)
        print('Border',a,b,flush=True)
    rows, snapshots = [], []
    t = start
    while t < end:
        nodes, edge_hour, missing, unavailable = {}, {}, [], []
        for z in AREAS:
            r = generation.get(z,{}).get(iso(t))
            load = hourly(loads.get(z,{}),t)
            cs = [hourly(s,t) for s in charges.get(z,{}).values()]
            if r is None or r['sensitivity_low'] is None or not r['storage_data_complete'] or load is None or any(v is None for v in cs):
                unavailable.append(z)
                continue
            energy = r['generation_mwh_by_type']
            nodes[z] = dict(generation=sum(energy.values()), load=load, charging=sum(cs),
                emissions=sum(v*FACTORS[k][0] for k,v in energy.items() if k in FACTORS),
                unknown=sum(v for k,v in energy.items() if k not in FACTORS))
        for a,b in borders:
            if a not in nodes and b not in nodes:
                continue
            for source,target in [(a,b),(b,a)]:
                v = hourly(flows.get((source,target),{}),t)
                if v is None:
                    missing.append(source+'>'+target)
                else:
                    edge_hour[source,target] = v
        if missing:
            results = {z:dict(quality='missing_inputs',carbon_intensity=None,missing=missing) for z in nodes}
        else:
            try:
                results = trace(nodes,edge_hour)
            except ValueError as error:
                results = {z:dict(quality='unsolved',carbon_intensity=None,reason=str(error)) for z in nodes}
        for z in unavailable:
            results[z] = dict(quality='missing_node_inputs',carbon_intensity=None)
        for r in results.values():
            r['unresolved_neighbor_nodes'] = unavailable
        rows.extend(dict(zone=z,start=iso(t),basis='consumption_lifecycle_flow_traced',
                         unit='gCO2e/kWh',factor_version=FACTOR_VERSION,**r) for z,r in results.items())
        snapshots.append(dict(start=iso(t),nodes=nodes,
            edges=[dict(source=a,target=b,energy_mwh=v) for (a,b),v in edge_hour.items()],
            missing_flows=missing,unavailable_nodes=unavailable))
        t += dt.timedelta(hours=1)
    out = args.output/args.month
    out.mkdir(parents=True,exist_ok=True)
    (out/'hourly.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows))
    (out/'network.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in snapshots))
    summary = dict(period=period,zones=list(AREAS),external_domains=EXTERNAL,borders=borders,errors=errors,
        quality_counts=dict(Counter(r['quality'] for r in rows)),factor_version=FACTOR_VERSION,factor_source=IPCC,
        factor_mapping=FACTORS,unknown_factor_scenarios=[0,1500],
        per_zone={z:dict(Counter(r['quality'] for r in rows if r['zone']==z)) for z in AREAS},
        limitations=['Pilot boundary topology requires completeness audit',
        'External imports, storage discharge, unsupported fuels and balance deficits carry unknown carbon',
        'Sensitivity 0/1500 gCO2e/kWh is an assumption, not a confidence interval',
        'Absent charging categories are unreported; balance residual exposes but cannot identify missing charging',
        'No Electricity Maps inputs; no live app changes'])
    if args.archive:
        summary['benchmark'] = benchmark(rows,args.archive)
        summary['benchmark_note'] = 'Consumption-basis diagnostic; unresolved supply and different factors prevent accuracy claims'
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
