"""Publish an explicitly provisional price diagnostic, never an acceptance result."""
import argparse,json,math
from pathlib import Path
from monthly_dispatch import digest,save


def validate(report,source_hash):
    if (report['status']!='provisional_fixed_inventory_price_diagnostic_not_validation'
            or report['year']!=2025 or report['hours']!=8760 or report['input_sha256']!=source_hash):
        raise ValueError('Source-matched full-calendar diagnostic required')
    ids=[r['node'] for r in report['nodes']]
    if len(ids)!=128 or len(set(ids))!=len(ids):raise ValueError('Complete unique model-node inventory required')
    allowed={'native_nodal_price_row_absent','unresolved_geographic_mapping',
        'conditional_nodal_vs_observed_zonal_diagnostic_not_validation'}
    for row in report['nodes']:
        if row['status'] not in allowed:raise ValueError('Unsupported diagnostic status')
        if row['status']!='conditional_nodal_vs_observed_zonal_diagnostic_not_validation':continue
        if [m['month'] for m in row['monthly']]!=list(range(1,13)):raise ValueError('Ordered months required')
        if sum(m['matched_hours'] for m in row['monthly'])!=row['matched_hours']:raise ValueError('Monthly coverage differs')
        for item in [row,*row['monthly']]:
            n=item['matched_hours']
            if type(n) is not int or not 0<=n<=8760:raise ValueError('Invalid matched coverage')
            for key in ('bias_eur_mwh','mae_eur_mwh','rmse_eur_mwh','correlation'):
                v=item[key]
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v)):
                    raise ValueError('Nonfinite diagnostic')
                if not n and v is not None:raise ValueError('Empty sample has a metric')
            if n and any(item[k] is None for k in ('bias_eur_mwh','mae_eur_mwh','rmse_eur_mwh')):
                raise ValueError('Observed sample lacks error metrics')
            if n and (item['mae_eur_mwh']<0 or item['rmse_eur_mwh']+1e-9<item['mae_eur_mwh']
                    or item['mae_eur_mwh']+1e-9<abs(item['bias_eur_mwh'])):
                raise ValueError('Inconsistent error metrics')
            if item['correlation'] is not None and not -1-1e-12<=item['correlation']<=1+1e-12:
                raise ValueError('Invalid correlation')
    return report


def publish(source,bounds,prices,output):
    report=json.loads(source.read_text());reference=json.loads(bounds.read_text());tools=Path(__file__).parent
    if report['producer_sha256']!=digest(tools/'compare_native_price_observations.py'):
        raise ValueError('Diagnostic producer changed')
    if reference['status']!='replayed_economic_annual_bounds_not_validated':raise ValueError('Replayed annual source required')
    if digest(prices/'manifest.json')!=report['price_manifest_sha256']:raise ValueError('Price publication changed')
    for zone,value in report['observed_price_sha256'].items():
        if digest(prices/f'{zone}.json')!=value:raise ValueError('Observed price array changed')
    validate(report,reference['input_sha256'])
    report.update(schema_version=1,diagnostic_sha256=digest(source),publication_tool_sha256=digest(Path(__file__)),
        scope='Candidate 001 fixed-inventory conditional nodal prices, provisional national mapping; no zonal aggregation or validation.',
        acceptance=dict(empirical_validation=False,annual_optimum=False,held_out_acceptance=False,investment_validation=False))
    save(output,report)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','bounds','prices','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();publish(a.source,a.bounds,a.prices,a.output);print('Prepared provisional price metrics with explicit unpassed acceptance gates.')
