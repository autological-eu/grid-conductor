"""Compare native country trade with secondary annual Ember net-import records."""
import argparse,csv,json,math
from pathlib import Path
from monthly_dispatch import digest,save
from compare_2025_generation_reference import ISO3
CODES={**ISO3,'DE':'DEU','DK':'DNK','IT':'ITA','NO':'NOR','SE':'SWE','BA':'BIH','ME':'MNE','GB':'GBR','LU':'LUX','XK':'XKX'}


def reference(rows):
    result={}
    for r in rows:
        if (r['Year']!='2025' or r['Area type'] not in ('Country','Country or economy')
                or r['Category']!='Electricity imports' or r['Variable']!='Net Imports' or r['Unit']!='TWh'):continue
        value=float(r['Value'])
        if not math.isfinite(value) or r['ISO 3 code'] in result:raise ValueError('Unique finite 2025 net-import record required')
        result[r['ISO 3 code']]=dict(area=r['Area'],net_import_twh=value)
    if not result:raise ValueError('No supported reference schema/records')
    return result


def compare(model,bank):
    if model['status']!='fixed_inventory_native_country_exchange_diagnostic_not_validation' or model['year']!=2025 or model['hours']!=8760:
        raise ValueError('Complete 2025 model country diagnostic required')
    rows=[]
    for row in model['countries']:
        if row['hours']!=8760:raise ValueError('No partial country annualisation')
        c=row['country'];ref=bank.get(CODES.get(c));e=row['net_export_mwh']/1e6
        if not math.isfinite(e):raise ValueError('Finite model exports required')
        rows.append(dict(country=c,status='unreconciled_secondary_national_trade_diagnostic' if ref else 'national_trade_reference_unavailable',
            model_net_export_twh=e,reference_area=ref['area'] if ref else None,
            reference_net_import_twh=ref['net_import_twh'] if ref else None,
            reference_net_export_twh=-ref['net_import_twh'] if ref else None,
            difference_net_export_twh=e+ref['net_import_twh'] if ref else None))
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','reference','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous diagnostic')
    model=json.loads(a.model.read_text())
    if model['producer_sha256']!=digest(Path(__file__).with_name('summarize_native_exchanges.py')):raise ValueError('Accounting producer changed')
    with a.reference.open() as f:bank=reference(csv.DictReader(f))
    save(a.output,dict(status='secondary_national_exchange_reference_not_entsoe_flow_validation',year=2025,
        input_sha256=model['input_sha256'],annual_replay_sha256=model['annual_replay_sha256'],model_accounting_sha256=digest(a.model),
        reference_csv_sha256=digest(a.reference),producer_sha256=digest(Path(__file__)),
        reference_source_url='https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/yearly_full_release_long_format.csv',
        comparisons=compare(model,bank),limitations=['Secondary country-year Net Imports records; not audited hourly ENTSO-E A11/A09 flows.',
            'Positive reference Net Imports means imports; displayed reference net exports negate that signed value.',
            'Model candidate 001 fixed inventories and country/mainland accounting boundaries remain unreconciled.',
            'Shared upstream observations, national coverage and balance conventions require audit.',
            'No bidding-zone, annual optimum, empirical acceptance or investment validity inferred.']))
    print('Compared secondary national trade references; no hourly-flow validation inferred.')
