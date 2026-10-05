"""Provisional per-node fixed-inventory price diagnostics; never zonal validation."""
import argparse, json, math
from pathlib import Path
import numpy as np
from monthly_dispatch import digest, save
from map_submonthly_calendar import verify
from importlib.metadata import version
from audit_2025_price_observations import audit
from audit_2025_price_mapping import audit as mapping_audit


def metrics(model, observed):
    if len(model)!=len(observed): raise ValueError('Matched chronological lengths required')
    if any(not math.isfinite(float(x)) for x in model): raise ValueError('Nonfinite model price')
    if any(x is not None and (type(x) not in (float,int) or not math.isfinite(x)) for x in observed):
        raise ValueError('Malformed observed price')
    pairs=[(float(a),float(b)) for a,b in zip(model,observed) if b is not None]
    if not pairs: return dict(matched_hours=0,bias_eur_mwh=None,mae_eur_mwh=None,rmse_eur_mwh=None,correlation=None)
    a,b=np.array(pairs).T;d=a-b
    return dict(matched_hours=len(pairs),bias_eur_mwh=float(np.mean(d)),mae_eur_mwh=float(np.mean(abs(d))),
        rmse_eur_mwh=float(np.sqrt(np.mean(d*d))),
        correlation=float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else None)


def compare(folder, network, prices):
    # Replays mapping hash, package, quantity and complete-calendar gates before interpretation.
    calendar_path=folder/'verified-calendar.json';manifest_path=folder/'manifest.json'
    native=json.loads(calendar_path.read_text());manifest=json.loads(manifest_path.read_text())
    if (native['status']!='annual_native_witness_mapping_complete_not_validation'
            or native['year']!=2025 or native['hours']!=8760 or len(native['rows'])!=59
            or native['manifest_sha256']!=digest(manifest_path)
            or native['input_sha256']!=manifest['input_sha256']
            or native['annual_replay_sha256']!=manifest['annual_replay_sha256']):
        raise ValueError('Complete source-matched mapping required')
    tools=Path(__file__).parent
    if manifest['producer_sha256']!=digest(tools/'map_submonthly_calendar.py'):raise ValueError('Mapping supervisor changed')
    for name,value in manifest['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Mapping implementation changed')
    for name,value in manifest['packages'].items():
        if version(name)!=value:raise ValueError('Mapping environment changed')
    mapping=mapping_audit(network,prices);observations=audit(prices)
    if native['input_sha256']!=mapping['input_sha256']: raise ValueError('Different native network')
    node_map={r['node']:r for r in mapping['nodes']};bank={r['zone']:r for r in observations['zones']}
    series={};position=0;calendar=json.loads((folder/'verified-calendar.json').read_text())
    for index,row in enumerate(calendar['rows']):
        if row['index']!=index:raise ValueError('Changed block order')
        target=folder/f"{row['index']:02d}"
        if digest(target/'verified.json')!=row['receipt_sha256']:raise ValueError('Mapping receipt changed')
        expected={k:row[k] for k in ('index','month','start_hour','end_hour_exclusive','hours')}
        receipt=verify(target,expected,native['input_sha256'],native['annual_replay_sha256'],manifest['dependencies']['map_submonthly_witness.py'])
        if row['start_hour']!=position or digest(target/'quantities.npz')!=row['quantities_sha256']:
            raise ValueError('Calendar or mapped quantities changed')
        with np.load(target/'quantities.npz',allow_pickle=False) as q:
            values=q['nodal_price_eur_per_mwh']
            if values.shape!=(row['hours'],len(receipt['bus_ids'])): raise ValueError('Price identity shape differs')
            if position and set(series)!=set(receipt['bus_ids']): raise ValueError('Node identity changes')
            for i,node in enumerate(receipt['bus_ids']): series.setdefault(node,[]).extend(values[:,i].tolist())
        position=row['end_hour_exclusive']
    if position!=8760: raise ValueError('Complete annual chronology required')
    rows=[dict(node=node,status='native_nodal_price_row_absent') for node in sorted(set(node_map)-set(series))]
    for node,values in sorted(series.items()):
        identity=node_map[node];zone=identity['candidate_zone']
        if zone is None:
            rows.append(dict(node=node,status='unresolved_geographic_mapping',reason=identity['reason']));continue
        path=prices/f'{zone}.json'
        if digest(path)!=bank[zone]['hourly_sha256']: raise ValueError('Observations changed')
        observed=json.loads(path.read_text());offset=0;months=[]
        import calendar as cal
        for month in range(1,13):
            end=offset+cal.monthrange(2025,month)[1]*24
            months.append(dict(month=month,**metrics(values[offset:end],observed[offset:end])));offset=end
        rows.append(dict(node=node,country=identity['country'],provisional_observed_zone=zone,
            status='conditional_nodal_vs_observed_zonal_diagnostic_not_validation',**metrics(values,observed),monthly=months))
    return dict(status='provisional_fixed_inventory_price_diagnostic_not_validation',year=2025,hours=8760,
        input_sha256=native['input_sha256'],mapping_calendar_sha256=digest(calendar_path),
        annual_replay_sha256=native['annual_replay_sha256'],price_manifest_sha256=observations['manifest_sha256'],
        observed_price_sha256={r['zone']:r['hourly_sha256'] for r in observations['zones']},
        producer_sha256=digest(Path(__file__)),nodes=rows,
        limitations=['Candidate 001 fixed-inventory conditional dual prices; not annual optimum market prices.',
            'Provisional national mapping; no load-weighted aggregation or accepted bidding-zone mapping.',
            'Missing nodal rows/observations and split-zone countries not replaced with zero.',
            'No calibration, held-out acceptance, investment or emissions validity inferred.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('folder','network','prices','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous diagnostic')
    save(a.output,compare(a.folder,a.network,a.prices));print('Prepared provisional per-node price diagnostic; no validation inferred.')
