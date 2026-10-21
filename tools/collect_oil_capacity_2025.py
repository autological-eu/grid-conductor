"""Collect credential-free receipts and A68 oil capacity; raw XML stays ignored."""
import argparse, json, os, xml.etree.ElementTree as ET
from pathlib import Path
from flow_tracing import fetch
from eu_zones import ROOT, ZONES

COUNTRIES = ['PL', 'SK', 'CZ', 'SI', 'DE-LU', 'BE', 'FR']


def parse(raw, domain):
    root = ET.fromstring(raw)
    for e in root.iter():
        e.tag = e.tag.split('}')[-1]
    if root.tag != 'GL_MarketDocument':
        raise ValueError('No installed-capacity document')
    rows = []
    for series in root.findall('TimeSeries'):
        if series.findtext('MktPSRType/psrType') != 'B06':
            continue
        if series.findtext('inBiddingZone_Domain.mRID') != domain:
            raise ValueError('Capacity reporting domain mismatch')
        if series.findtext('quantity_Measure_Unit.name') != 'MAW':
            raise ValueError('Capacity must be MW')
        for period in series.findall('Period'):
            points = period.findall('Point')
            if period.findtext('resolution') != 'P1Y' or len(points) != 1:
                raise ValueError('Expected one annual capacity point')
            start, end = period.findtext('timeInterval/start'), period.findtext('timeInterval/end')
            if (start, end) != ('2024-12-31T23:00Z', '2025-12-31T23:00Z'):
                raise ValueError('Unexpected 2025 reporting-year boundary')
            value = float(points[0].findtext('quantity'))
            if not 0 <= value < 100000:
                raise ValueError('Invalid oil MW')
            rows.append(dict(mw=value, start=start, end=end, resolution='P1Y'))
    if len(rows) != 1:
        raise ValueError('Missing or ambiguous oil capacity; never zero-fill')
    return rows[0]


def collect(out):
    if not os.environ.get('ENTSOE_API_KEY'):
        credential = ROOT / 'data/price-trace/.entsoe-key'
        if credential.exists():
            os.environ['ENTSOE_API_KEY'] = credential.read_text().strip()
    from generation_mix_2025 import digest
    rows = []
    for country in COUNTRIES:
        domain = next(g or p for z, p, g, _ in ZONES if z == country)
        request = dict(documentType='A68', processType='A33', in_Domain=domain,
                       periodStart='202501010000', periodEnd='202601010000')
        folder = out / 'entsoe-capacity' / country
        raw = fetch(request, folder)
        row = parse(raw, domain)
        # fetch receipts contain request parameters without the security token.
        raw_path = next(p for p in folder.glob('*.xml') if p.read_bytes() == raw)
        rows.append(dict(country='DE' if country == 'DE-LU' else country,
                         domain=domain, request=request, **row,
                         raw_path=str(raw_path.relative_to(ROOT)), sha256=digest(raw_path)))
    result = dict(year=2025, source='ENTSO-E A68 installed generation capacity by type; A33 annual',
                  producer_sha256=digest(__file__), countries=rows,
                  boundary_note='Annual Central-European reporting-year cells; applying a scalar to all 8760 UTC hours is an explicit model assumption, not hourly availability.')
    (out / 'capacity.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('out', type=Path)
    collect(p.parse_args().out.resolve())
