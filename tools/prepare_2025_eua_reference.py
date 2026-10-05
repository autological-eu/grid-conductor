"""Audit a public EEX 2025 EUA auction reference; never reprice dispatch implicitly."""
import argparse
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from monthly_dispatch import digest, save

SOURCE = 'https://www.eex.com/fileadmin/EEX/Downloads/Markets/Environmentals/EUA_Emission_Spot_Primary_Market_Auction_Report/Archive_Reports/emission-spot-primary-market-auction-report-2012-2025-data.zip'
MEMBER = 'emission-spot-primary-market-auction-report-2025-data.xlsx'
NS = {'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
HEADERS = {'B':'Date', 'D':'Auction Name', 'E':'Contract', 'F':'Status',
           'G':'Auction Price €/tCO2', 'L':'Auction Volume tCO2', 'Y':'Total Revenue €'}


def number(value):
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Malformed auction quantity') from None
    if not result.is_finite():
        raise ValueError('Nonfinite auction quantity')
    return result


def summarize(records):
    seen = set()
    months = defaultdict(list)
    total_volume = Decimal(0)
    total_revenue = Decimal(0)
    for row in records:
        day = date.fromisoformat(row['date'])
        identity = (day, row['auction_name'], row['contract'])
        if day.year != 2025 or identity in seen:
            raise ValueError('Wrong-year or duplicate auction')
        seen.add(identity)
        if row['contract'] != 'T3PA' or row['status'] != 'successful':
            raise ValueError('Unexpected contract or auction status; review scope')
        volume, price, revenue = [number(row[key]) for key in ['volume_tco2', 'price_eur_tco2', 'revenue_eur']]
        if volume <= 0 or volume != volume.to_integral_value() or price <= 0 or abs(volume*price-revenue) > Decimal('.01'):
            raise ValueError('Price, volume or reported euro revenue does not reconcile')
        total_volume += volume
        total_revenue += volume*price
        months[day.month].append((volume, price))
    if set(months) != set(range(1, 13)):
        raise ValueError('All twelve auction months required; no annualisation')
    monthly = []
    for month, rows in sorted(months.items()):
        volume = sum((v for v, _ in rows), Decimal(0))
        revenue = sum((v*p for v, p in rows), Decimal(0))
        monthly.append(dict(month=month, auctions=len(rows), volume_tco2=int(volume),
                            volume_weighted_price_eur_tco2=float(revenue/volume)))
    return dict(auctions=len(records), volume_tco2=int(total_volume),
                auction_revenue_eur=float(total_revenue),
                volume_weighted_price_eur_tco2=float(total_revenue/total_volume),
                first_auction=min(row['date'] for row in records), last_auction=max(row['date'] for row in records),
                monthly=monthly)


def parse(workbook):
    with zipfile.ZipFile(workbook) as archive:
        for name in ['xl/workbook.xml', 'xl/sharedStrings.xml', 'xl/worksheets/sheet1.xml']:
            if archive.getinfo(name).file_size > 8*2**20:
                raise ValueError('Workbook XML exceeds bounded reference size')
        book = ET.fromstring(archive.read('xl/workbook.xml'))
        properties = book.find('x:workbookPr', NS)
        if properties is not None and properties.get('date1904', 'false') not in ['false', '0']:
            raise ValueError('Unexpected Excel date system')
        sheets = book.findall('x:sheets/x:sheet', NS)
        if len(sheets) != 1 or sheets[0].get('name') != 'Primary Market Auction':
            raise ValueError('Unexpected EEX reference sheet')
        strings = [''.join(item.text or '' for item in node.findall('.//x:t', NS))
                   for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('x:si', NS)]
        table = []
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('x:sheetData/x:row', NS):
            cells = {}
            for cell in row.findall('x:c', NS):
                value = cell.find('x:v', NS)
                if value is None:
                    continue
                column = re.fullmatch(r'([A-Z]+)[0-9]+', cell.attrib['r'])
                if not column:
                    raise ValueError('Malformed Excel cell reference')
                cells[column[1]] = strings[int(value.text)] if cell.get('t') == 's' else value.text
            table.append(cells)
    header = next((index for index, row in enumerate(table) if all(row.get(k) == v for k,v in HEADERS.items())), None)
    if header is None:
        raise ValueError('Expected EEX headers and explicit units required')
    records = []
    for row in table[header+1:]:
        if not row.get('B'):
            continue
        serial = number(row['B'])
        if serial != serial.to_integral_value():
            raise ValueError('Auction calendar date must have no time fraction')
        day = date(1899, 12, 30)+timedelta(days=int(serial))
        records.append(dict(date=day.isoformat(), auction_name=row['D'], contract=row['E'], status=row['F'],
                            price_eur_tco2=row['G'], volume_tco2=row['L'], revenue_eur=row['Y']))
    return records


def audit(args):
    source = json.loads(args.manifest.read_text())
    if source['source'] != SOURCE or source['sha256'] != digest(args.archive):
        raise ValueError('Original official EEX archive and receipt required')
    with zipfile.ZipFile(args.archive) as archive:
        members = [name for name in archive.namelist() if Path(name).name == MEMBER]
        if len(members) != 1 or archive.getinfo(members[0]).file_size > 8*2**20:
            raise ValueError('Unique bounded 2025 source workbook required')
        if archive.read(members[0]) != args.workbook.read_bytes():
            raise ValueError('Extracted workbook differs from original archive')
    result = summarize(parse(args.workbook))
    result.update(status='observed_2025_eua_auction_reference_not_dispatch_validation', year=2025,
                  source_url=SOURCE, archive_sha256=digest(args.archive), workbook_member=members[0],
                  workbook_sha256=digest(args.workbook), producer_sha256=digest(Path(__file__)),
                  scope='EEX successful EUA primary auctions; auction-volume-weighted clearing price, not hourly spot/futures prices or a fitted power-price parameter.',
                  limitations=['No baseline cost or dispatch is changed by this reference.',
                      'EU ETS operational CO2 cost differs from lifecycle carbon-intensity accounting.',
                      'Any dispatch sensitivity needs explicit jurisdiction/asset coverage and independent re-solves.',
                      'UK/Swiss/non-EU policy coverage must not be silently treated as identical.',
                      'No annual market validation, avoided emissions or investment benefit inferred.'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['archive', 'manifest', 'workbook', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous reference evidence')
    result = audit(args)
    save(args.output, result)
    print(f"Audited {result['auctions']} successful 2025 EUA auctions; weighted price {result['volume_weighted_price_eur_tco2']:.4f} EUR/tCO2. Model unchanged.")
