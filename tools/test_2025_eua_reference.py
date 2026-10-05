import copy
import unittest
import tempfile
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape
from prepare_2025_eua_reference import summarize, parse, HEADERS


class EUAReferenceTests(unittest.TestCase):
    def workbook(self, path, wrong_units=False, date1904=False):
        strings = list(HEADERS.values()) + ['EU', 'T3PA', 'successful']
        if wrong_units:
            strings[strings.index('Auction Price €/tCO2')] = 'Auction Price €/MWh'
        header = ''.join(f'<c r="{col}6" t="s"><v>{i}</v></c>' for i, col in enumerate(HEADERS))
        values = {'B': '45664', 'D': '7', 'E': '8', 'F': '9', 'G': '10', 'L': '100', 'Y': '1000'}
        first = ''.join(f'<c r="{col}7"' + (' t="s"' if col in ['D', 'E', 'F'] else '') + f'><v>{v}</v></c>' for col, v in values.items())
        namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('xl/workbook.xml', f'<workbook xmlns="{namespace}"><workbookPr date1904="{str(date1904).lower()}"/><sheets><sheet name="Primary Market Auction"/></sheets></workbook>')
            archive.writestr('xl/sharedStrings.xml', f'<sst xmlns="{namespace}">' + ''.join(f'<si><t>{escape(s)}</t></si>' for s in strings) + '</sst>')
            archive.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{namespace}"><sheetData><row r="2"/><row r="6">{header}</row><row r="7">{first}</row></sheetData></worksheet>')

    def test_first_auction_after_header_is_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'reference.xlsx'
            self.workbook(path)
            rows = parse(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['date'], '2025-01-07')
            self.assertEqual(rows[0]['price_eur_tco2'], '10')
            for options in [dict(wrong_units=True), dict(date1904=True)]:
                self.workbook(path, **options)
                with self.assertRaises(ValueError):
                    parse(path)

    def rows(self):
        return [dict(date=f'2025-{month:02d}-07', auction_name='EU', contract='T3PA', status='successful',
                     volume_tco2='100', price_eur_tco2='10', revenue_eur='1000') for month in range(1, 13)]

    def test_uses_volume_weighted_prices_not_bid_means(self):
        rows = self.rows()
        rows.append(dict(date='2025-01-08', auction_name='DE', contract='T3PA', status='successful',
                         volume_tco2='300', price_eur_tco2='20', revenue_eur='6000'))
        report = summarize(rows)
        self.assertEqual(report['volume_tco2'], 1500)
        self.assertEqual(report['volume_weighted_price_eur_tco2'], 12.)
        self.assertEqual(report['monthly'][0]['volume_weighted_price_eur_tco2'], 17.5)

    def test_partial_year_or_duplicate_auction_fails(self):
        rows = self.rows()
        for invalid in [rows[:-1], rows+[copy.deepcopy(rows[0])]]:
            with self.assertRaises(ValueError):
                summarize(invalid)

    def test_wrong_contract_status_units_or_revenue_fails(self):
        for change in [dict(date='2024-01-07'), dict(contract='EUAA'), dict(status='cancelled'),
                       dict(volume_tco2='0'), dict(volume_tco2='1.5'), dict(price_eur_tco2='NaN'),
                       dict(revenue_eur='1001')]:
            rows = self.rows()
            rows[0].update(change)
            with self.assertRaises(ValueError):
                summarize(rows)


if __name__ == '__main__':
    unittest.main()
