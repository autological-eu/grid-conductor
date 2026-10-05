"""Stream complete native country exchanges; not observed bidding-zone validation."""
import argparse,json,math
from pathlib import Path
from collections import defaultdict
from importlib.metadata import version
import numpy as np
from monthly_dispatch import digest,save
from map_submonthly_exchange_calendar import verify


def totals(values):
    a=np.asarray(values,dtype=float)
    if a.ndim!=1 or not np.isfinite(a).all():raise ValueError('Finite hourly signed exchange required')
    return dict(net_export_mwh=float(np.sum(a)),positive_net_export_mwh=float(np.sum(np.maximum(a,0))),
        negative_net_import_mwh=float(np.sum(np.maximum(-a,0))),positive_net_export_hours=int(np.count_nonzero(a>0)),hours=len(a))


def summarize(folder):
    path=folder/'verified-calendar.json';r=json.loads(path.read_text());mp=folder/'manifest.json';m=json.loads(mp.read_text());tools=Path(__file__).parent
    if (r['status']!='annual_native_branch_mapping_complete_not_exchange_validation' or r['year']!=2025
            or r['hours']!=8760 or len(r['rows'])!=59 or r['manifest_sha256']!=digest(mp)
            or r['input_sha256']!=m['input_sha256'] or r['annual_replay_sha256']!=m['annual_replay_sha256']):
        raise ValueError('Complete source-matched exchange mapping required')
    if m['producer_sha256']!=digest(tools/'map_submonthly_exchange_calendar.py'):raise ValueError('Supervisor changed')
    for name,v in m['dependencies'].items():
        if digest(tools/name)!=v:raise ValueError('Mapper changed')
    for name,v in m['packages'].items():
        if version(name)!=v:raise ValueError('Environment changed')
    accum=defaultdict(list);position=0;identity=None;max_residual=0.
    for index,row in enumerate(r['rows']):
        target=folder/f'{index:02d}'
        if row['index']!=index or row['start_hour']!=position or row['receipt_sha256']!=digest(target/'verified.json') or row['quantities_sha256']!=digest(target/'quantities.npz'):
            raise ValueError('Mapping receipt/chronology changed')
        expected={k:row[k] for k in ('index','month','start_hour','end_hour_exclusive','hours')}
        record=verify(target,expected,r['input_sha256'],r['annual_replay_sha256'],m['dependencies']['map_submonthly_exchanges.py'])
        current=(record['assets'],record['countries'])
        if identity is None:identity=current
        if identity!=current:raise ValueError('Country/branch identities change within calendar')
        with np.load(target/'quantities.npz',allow_pickle=False) as q:export=q['country_net_export_mw']
        residual=float(np.max(abs(np.sum(export,axis=1)),initial=0.));max_residual=max(max_residual,residual)
        if all(a['efficiency']==1 for a in record['assets']) and residual>1e-7:raise ValueError('Lossless cross-country accounting does not close')
        for i,country in enumerate(record['countries']):accum[(country,row['month'])].append(totals(export[:,i]))
        position=row['end_hour_exclusive']
    if position!=8760:raise ValueError('No partial-year annualisation')
    countries=[]
    for country in identity[1]:
        months=[]
        for month in range(1,13):
            blocks=accum[(country,month)]
            months.append(dict(month=month,**{k:math.fsum(b[k] for b in blocks) if k.endswith('_mwh') else sum(b[k] for b in blocks)
                for k in ('net_export_mwh','positive_net_export_mwh','negative_net_import_mwh','positive_net_export_hours','hours')}))
        countries.append(dict(country=country,monthly=months,**{k:math.fsum(x[k] for x in months) if k.endswith('_mwh') else sum(x[k] for x in months)
            for k in ('net_export_mwh','positive_net_export_mwh','negative_net_import_mwh','positive_net_export_hours','hours')}))
    return dict(status='fixed_inventory_native_country_exchange_diagnostic_not_validation',year=2025,hours=8760,
        input_sha256=r['input_sha256'],annual_replay_sha256=r['annual_replay_sha256'],mapping_calendar_sha256=digest(path),
        producer_sha256=digest(Path(__file__)),countries=countries,max_country_sum_terminal_residual_mw=max_residual,
        scope='Candidate 001 model-country terminal accounting; not observed or accepted bidding-zone exchange.',
        limitations=['Country net export aggregates simultaneous native border flows before positive/negative totals; not gross bilateral allocation.',
            'Fixed-inventory candidate 001, not converged annual optimum.',
            'No A11/A09 receipt recovery, observation agreement, price calibration, carbon or investment validity inferred.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous exchange diagnostic')
    save(a.output,summarize(a.folder));print('Summarised complete native exchanges; no empirical acceptance inferred.')
