"""Publish replayed native trade diagnostics; all empirical acceptance stays false."""
import argparse,csv,json
from pathlib import Path
from monthly_dispatch import digest,save
from summarize_native_exchanges import summarize
from compare_native_exchange_reference import compare,reference


def publish(folder,model,comparison,csv_path,bounds,output):
    native=json.loads(model.read_text());secondary=json.loads(comparison.read_text());bound=json.loads(bounds.read_text())
    if native!=summarize(folder):raise ValueError('Complete native accounting no longer reproduces')
    if (secondary['status']!='secondary_national_exchange_reference_not_entsoe_flow_validation'
            or secondary['year']!=2025 or secondary['input_sha256']!=native['input_sha256']
            or secondary['annual_replay_sha256']!=native['annual_replay_sha256']
            or secondary['model_accounting_sha256']!=digest(model) or secondary['reference_csv_sha256']!=digest(csv_path)
            or secondary['producer_sha256']!=digest(Path(__file__).with_name('compare_native_exchange_reference.py'))
            or bound['status']!='replayed_economic_annual_bounds_not_validated' or bound['input_sha256']!=native['input_sha256']):
        raise ValueError('Source-matched diagnostic provenance required')
    with csv_path.open() as f:bank=reference(csv.DictReader(f))
    if secondary['comparisons']!=compare(native,bank):raise ValueError('Secondary reference comparisons differ')
    save(output,dict(schema_version=1,status='native_country_exchange_and_secondary_reference_not_validated',year=2025,
        input_sha256=native['input_sha256'],annual_replay_sha256=native['annual_replay_sha256'],
        publication_tool_sha256=digest(Path(__file__)),model_accounting_sha256=digest(model),secondary_comparison_sha256=digest(comparison),
        acceptance=dict(annual_optimum=False,entsoe_hourly_exchange_validation=False,bidding_zone_validation=False,investment_validation=False),
        native_accounting=native,secondary_reference=secondary,
        limitations=['Fixed-inventory candidate 001 model countries; separate from the newer best feasible annual incumbent.',
            'Secondary Ember annual Net Imports values are not recovered hourly ENTSO-E A11/A09 observations.',
            'Accounting/geographic/coverage conventions remain unreconciled; no missing reference zero-filled.',
            'Only native arithmetic/provenance reproduced; no empirical, convergence or investment acceptance.']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','model','comparison','csv','bounds','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();publish(a.folder,a.model,a.comparison,a.csv,a.bounds,a.output);print('Prepared source-replayed native trade diagnostic; empirical/investment gates remain open.')
