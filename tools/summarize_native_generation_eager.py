"""Versioned eager-per-block accounting for mapped annual generation.

Separate producer preserves the frozen original accounting provenance. Each
compressed quantity array is loaded once per block rather than per asset.
Memory is bounded by one at-most-168-hour block; equations are unchanged.

Stream mapped annual witness generation by native country and carrier.

Accounting diagnostic only: country grouping is not a verified bidding-zone
mapping. Hydro reservoir discharge is separate from pumped storage recycling.
"""
import argparse,json,math
from pathlib import Path
from collections import defaultdict
from importlib.metadata import version
import numpy as np
from monthly_dispatch import digest,save
from map_submonthly_calendar import verify
from summarize_annual_native_generation import energy as original_energy


def energy(arrays,record):
    names = ('generation_mw', 'storage_discharge_mw', 'storage_charge_mw')
    arrays = {name: np.asarray(arrays[name]) for name in names}
    hours = arrays['generation_mw'].shape[0]
    if not 1 <= hours <= 168:
        raise ValueError('Bounded nonempty hourly block required')
    for name in names:
        count = len(record['generators'] if name == 'generation_mw' else record['storage_units'])
        if arrays[name].shape != (hours, count) or not np.isfinite(arrays[name]).all():
            raise ValueError('Invalid generation/storage accounting grid')
    return original_energy(arrays, record)


def summarize(folder):
    calendar_path=folder/'verified-calendar.json';calendar=json.loads(calendar_path.read_text())
    manifest_path=folder/'manifest.json';manifest=json.loads(manifest_path.read_text())
    if (calendar['status']!='annual_native_witness_mapping_complete_not_validation' or calendar['year']!=2025
            or calendar['hours']!=8760 or len(calendar['rows'])!=59 or calendar['manifest_sha256']!=digest(manifest_path)
            or calendar['input_sha256']!=manifest['input_sha256']
            or calendar['annual_replay_sha256']!=manifest['annual_replay_sha256']):raise ValueError('Complete source-matched native annual mapping required')
    tools=Path(__file__).parent
    if manifest['producer_sha256']!=digest(tools/'map_submonthly_calendar.py'):raise ValueError('Mapping supervisor changed')
    for name,value in manifest['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Mapping implementation changed')
    for name,value in manifest['packages'].items():
        if version(name)!=value:raise ValueError('Mapping environment changed')
    primary=defaultdict(list);storage=defaultdict(lambda:defaultdict(list));position=0;rows=[]
    for index,row in enumerate(calendar['rows']):
        if row['index']!=index or row['start_hour']!=position:raise ValueError('Incomplete annual chronology')
        target=folder/f'{index:02d}';path=target/'verified.json'
        if digest(path)!=row['receipt_sha256'] or digest(target/'quantities.npz')!=row['quantities_sha256']:raise ValueError('Mapped annual evidence changed')
        keys=('index','month','start_hour','end_hour_exclusive','hours');expected={k:row[k] for k in keys}
        record=verify(target,expected,calendar['input_sha256'],calendar['annual_replay_sha256'],manifest['dependencies']['map_submonthly_witness.py'])
        with np.load(target/'quantities.npz',allow_pickle=False) as data:p,s=energy(data,record)
        for (country,carrier),value in p.items():primary[(row['month'],country,carrier)].append(value)
        for (country,carrier),data in s.items():
            for name,value in data.items():storage[(row['month'],country,carrier)][name].append(value)
        rows.append(dict(index=index,receipt_sha256=row['receipt_sha256'],quantities_sha256=row['quantities_sha256']))
        position=row['end_hour_exclusive']
    if position!=8760:raise ValueError('Complete year required; never annualise a partial pass')
    countries=sorted({country for _,country,_ in set(primary)|set(storage)})
    result=[]
    for country in countries:
        months=[];annual=defaultdict(list);annual_storage=defaultdict(lambda:defaultdict(list))
        for month in range(1,13):
            mix={carrier:math.fsum(v) for (m,c,carrier),v in primary.items() if (m,c)==(month,country)}
            stored={carrier:{name:math.fsum(v) for name,v in data.items()} for (m,c,carrier),data in storage.items() if (m,c)==(month,country)}
            for carrier,value in mix.items():annual[carrier].append(value)
            for carrier,data in stored.items():
                for name,value in data.items():annual_storage[carrier][name].append(value)
            months.append(dict(month=month,primary_generation_mwh_by_model_carrier=mix,storage_energy_mwh_by_model_carrier=stored))
        mix={carrier:math.fsum(v) for carrier,v in annual.items()}
        result.append(dict(country=country,primary_generation_mwh=math.fsum(mix.values()),primary_generation_mwh_by_model_carrier=mix,
            storage_energy_mwh_by_model_carrier={carrier:{name:math.fsum(v) for name,v in data.items()} for carrier,data in annual_storage.items()},monthly=months))
    return dict(status='annual_fixed_inventory_generation_accounting_diagnostic_not_validation',year=2025,hours=8760,unit='MWh',
        input_sha256=calendar['input_sha256'],annual_replay_sha256=calendar['annual_replay_sha256'],mapping_calendar_sha256=digest(calendar_path),
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['summarize_annual_native_generation.py','map_submonthly_calendar.py','map_submonthly_witness.py','monthly_dispatch.py']},
        countries=result,rows=rows,limitations=['Native model-country grouping; mainland coverage and bidding-zone boundaries remain to be reconciled.',
        'Primary generation includes unidirectional hydro reservoirs; pumped-storage recycling remains separate.',
        'Fixed-inventory feasible annual trajectory, not converged annual optimum or observed generation agreement.',
        'No emission factors, carbon intensity, price fitting, availability substitution or investment benefits inferred.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous native annual accounting diagnostic')
    r=summarize(a.folder);save(a.output,r);print(f"Summarised {len(r['countries'])} native model countries; no empirical validation inferred.")
