"""Export original prepared-network demand; national diagnostic, not zonal acceptance."""
import argparse
import json
from pathlib import Path
import numpy as np
import xarray as xr
from hourly_renewable_estimates import digest


def aggregate(dataset):
    expected=np.datetime64('2025-01-01T00','ns')+np.arange(8760).astype('timedelta64[h]')
    hours=dataset.snapshots_snapshot.values
    if not np.array_equal(hours,expected):raise ValueError('Exact 8760 UTC hours required')
    for key in ['snapshots_objective','snapshots_generators','snapshots_stores']:
        if not np.array_equal(dataset[key].values,np.ones(8760)):raise ValueError('Hourly weights required')
    buses=list(dataset.buses_i.values);countries=list(dataset.buses_country.values)
    if len(set(buses))!=len(buses):raise ValueError('Duplicate bus identity')
    country=dict(zip(buses,countries))
    ids=list(dataset.loads_i.values);varying=list(dataset.loads_t_p_set_i.values)
    if len(set(ids))!=len(ids) or len(set(varying))!=len(varying) or set(ids)!=set(varying):
        raise ValueError('Complete unique hourly load identities required')
    values=dataset.loads_t_p_set.sel(loads_t_p_set_i=ids).values
    if values.shape!=(8760,len(ids)) or not np.isfinite(values).all() or np.any(values<0):
        raise ValueError('Finite nonnegative hourly demand required')
    load_buses=list(dataset.loads_bus.values)
    if len(load_buses)!=len(ids) or any(bus not in country for bus in load_buses):raise ValueError('Unknown load bus')
    supported=sorted(set(countries))
    if any(not isinstance(c,str) or len(c)!=2 for c in supported):raise ValueError('National country identities required')
    result=np.zeros((8760,len(supported)))
    for j,c in enumerate(supported):
        indices=[i for i,bus in enumerate(load_buses) if country[bus]==c]
        result[:,j]=values[:,indices].sum(axis=1)
    if not np.allclose(result.sum(axis=1),values.sum(axis=1),rtol=1e-12,atol=1e-7):raise ValueError('Aggregation changes hourly demand')
    month=hours.astype('datetime64[M]')
    rows=[]
    for j,c in enumerate(supported):
        monthly=[dict(month=m,demand_mwh=float(result[month==np.datetime64(f'2025-{m:02d}'),j].sum())) for m in range(1,13)]
        rows.append(dict(country=c,annual_demand_mwh=float(result[:,j].sum()),peak_demand_mw=float(result[:,j].max()),monthly=monthly))
    return hours,supported,result,rows


def run(network,expected_hash,output):
    if output.exists():raise ValueError('Preserve existing diagnostic')
    if digest(network)!=expected_hash:raise ValueError('Source network changed')
    with xr.open_dataset(network) as dataset:hours,countries,values,rows=aggregate(dataset)
    output.mkdir(parents=True)
    path=output/'hourly.npz'
    np.savez_compressed(path,hours_utc=hours,countries=np.array(countries),demand_mw=values)
    summary=dict(status='national_prepared_network_demand_diagnostic_not_zonal_validation',year=2025,hours=8760,unit='MW',
        network_sha256=expected_hash,producer_sha256=digest(__file__),hourly_sha256=digest(path),countries=rows,
        limitations=['Prepared-network demand is not independently validated ENTSO-E demand.',
        'National aggregation does not establish bidding-zone allocation or whole-country accounting scope.',
        'No interpolation, gap filling, dispatch substitution or annual optimisation performed.'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(f'Exported original hourly demand for {len(countries)} national model areas; zonal gate remains open.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--network',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.network,a.expected_sha256,a.output)
