"""Preserve original reservoir inflows; preprocessing diagnostic, not zonal acceptance."""
import argparse,json
from pathlib import Path
import numpy as np
import xarray as xr
from hourly_renewable_estimates import digest


def extract(d):
    hours=d.snapshots_snapshot.values
    expected=np.datetime64('2025-01-01T00','ns')+np.arange(8760).astype('timedelta64[h]')
    if not np.array_equal(hours,expected):raise ValueError('Exact 8760 UTC hours required')
    if not np.array_equal(d.snapshots_stores.values,np.ones(8760)):raise ValueError('Hourly storage weights required')
    ids=list(d.storage_units_i.values);profiles=list(d.storage_units_t_inflow_i.values)
    if len(set(ids))!=len(ids) or len(set(profiles))!=len(profiles) or not set(profiles).issubset(ids):raise ValueError('Unique known reservoir identities required')
    hydro=[i for i in ids if d.storage_units_carrier.sel(storage_units_i=i).item()=='hydro']
    if not hydro or set(profiles)!=set(hydro):raise ValueError('Complete reservoir-only inflow profiles required')
    inflow=d.storage_units_t_inflow.sel(storage_units_t_inflow_i=hydro).values
    if inflow.shape!=(8760,len(hydro)) or not np.isfinite(inflow).all() or np.any(inflow<0):raise ValueError('Finite nonnegative original inflows required')
    buses=list(d.buses_i.values)
    if len(set(buses))!=len(buses):raise ValueError('Duplicate bus identity')
    country=dict(zip(buses,d.buses_country.values));rows=[]
    for j,i in enumerate(hydro):
        fields={key.removeprefix('storage_units_'):d[key].sel(storage_units_i=i).item() for key in d.variables if key.startswith('storage_units_') and d[key].dims==('storage_units_i',) and key!='storage_units_i'}
        if fields['bus'] not in country:raise ValueError('Unknown reservoir bus')
        for key in ['p_nom','max_hours','p_min_pu','efficiency_dispatch','efficiency_store']:
            if not np.isfinite(fields[key]):raise ValueError('Nonfinite source storage parameter')
        if fields['p_nom']<=0 or fields['max_hours']<0 or fields['p_min_pu']!=0:raise ValueError('Unidirectional reservoir physics required')
        if not 0<fields['efficiency_dispatch']<=1 or not 0<=fields['efficiency_store']<=1:raise ValueError('Invalid source storage efficiency')
        months=hours.astype('datetime64[M]')
        rows.append(dict(id=i,country=country[fields['bus']],source_parameters=fields,
            annual_storage_inflow_mwh=float(inflow[:,j].sum()),monthly=[dict(month=m,storage_inflow_mwh=float(inflow[months==np.datetime64(f'2025-{m:02d}'),j].sum())) for m in range(1,13)]))
    return hours,hydro,inflow,rows


def run(network,expected,output):
    if output.exists():raise ValueError('Preserve existing diagnostic')
    if digest(network)!=expected:raise ValueError('Source network changed')
    with xr.open_dataset(network) as d:hours,ids,inflow,rows=extract(d)
    output.mkdir(parents=True);path=output/'hourly.npz'
    np.savez_compressed(path,hours_utc=hours,reservoir_ids=np.array(ids),inflow_mw=inflow)
    summary=dict(status='original_reservoir_inflow_diagnostic_not_zonal_validation',year=2025,hours=8760,network_sha256=expected,
        producer_sha256=digest(__file__),hourly_sha256=digest(path),reservoirs=rows,
        limitations=['Original prepared-network storage-energy inflow, not observed generation or post-turbine electrical output.',
        'Reservoir identities remain separate; no pooling of water or boundary inventories.',
        'Not a complete storage compiler: omitted/default fields, boundary conditions and bidding-zone assignment require separate audit.',
        'Pumped storage excluded from primary reservoir inflows; charging and recycling remain separate.',
        'No fitting, interpolation, new weather conversion or optimisation performed.'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(f'Preserved 8760 original hours for {len(ids)} reservoirs; zonal acceptance remains open.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--network',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.network,a.expected_sha256,a.output)
