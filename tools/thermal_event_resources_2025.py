"""Recover wind/solar available MW before equal-price pooling; never use dispatch."""
import json,gzip
from pathlib import Path
import numpy as np
import xarray as xr
from prepare_thermal_event_2025 import ROOT,OUT
from generation_mix_2025 import digest

def prepare():
    dest=OUT/'resource-components.npz';assert not dest.exists();meta=json.loads((OUT/'inputs-protocol-v2.json').read_text());a=meta['start_hour'];b=meta['stop_hour']
    network=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc';mapping=ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json';layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json';irena=ROOT/'public/research/irena-capacity-2025/summary.json.gz'
    records=json.loads(gzip.decompress(irena.read_bytes()))['irena_rows'];layout=json.loads(layout_path.read_text());allocation=json.loads(mapping.read_text())['allocation'];families=[{'solar','solar-hsat'},{'onwind','offwind-ac','offwind-dc','offwind-float'}];labels=['Solar photovoltaic','Wind energy']
    with xr.open_dataset(network) as ds:
        names=ds.generators_i.values.tolist();fuel=ds.generators_carrier.values;nom=ds.generators_p_nom.values;bus=ds.generators_bus.values;country=dict(zip(ds.buses_i.values,ds.buses_country.values));countries=np.array([country[x] for x in bus]);columns=ds.generators_t_p_max_pu_i.values.tolist();raw=ds.generators_t_p_max_pu.isel(snapshots=slice(a,b)).values
        native=np.zeros((b-a,len(names)))
        for j,f in enumerate(fuel):
            if f not in families[0]|families[1]:continue
            native[:,j]=raw[:,columns.index(names[j])]*nom[j]
        for c in sorted(set(countries)):
            for carriers,label in zip(families,labels,strict=True):
                ids=np.flatnonzero((countries==c)&np.isin(fuel,list(carriers)));total=nom[ids].sum();r=next((r for r in records if r['country']==c and r['technology']==label),None)
                if total>0 and r:
                    lo=r['capacity_2024']['mw'];hi=r['capacity_2025']['mw'];native[:,ids]*=((lo+(hi-lo)*np.arange(a,b)/8760)/total)[:,None]
        refined=[];refined_fuel=[]
        for record in allocation:
            if record['component']!='Generator':continue
            name=record['name'];j=names.index(name) if name in names else None
            for _,weight in record['shares'].items():
                if weight<=0:continue
                refined.append(np.zeros(b-a) if j is None else native[:,j]*weight);refined_fuel.append('emergency' if j is None else fuel[j])
    solar=np.zeros((b-a,meta['ng']));wind=solar.copy();refined=np.array(refined).T
    for j,(ids,fraction) in enumerate(zip(layout['members'],layout['fractions'],strict=True)):
        ids=[i for i in ids if i<len(refined_fuel)]
        solar[:,j]=refined[:,[i for i in ids if refined_fuel[i] in families[0]]].sum(axis=1)*fraction
        wind[:,j]=refined[:,[i for i in ids if refined_fuel[i] in families[1]]].sum(axis=1)*fraction
    with np.load(OUT/'inputs.npz') as z:original=z['availability']
    renewable=[c['column'] for c in meta['columns'] if set(c['carriers'])<=families[0]|families[1]]
    np.testing.assert_allclose((solar+wind)[:,renewable],original[:,renewable],rtol=1e-10,atol=1e-7)
    assert np.all((solar+wind)[:,[j for j in range(meta['ng']) if j not in renewable]]==0)
    np.savez_compressed(dest,solar=solar,wind=wind)
    result=dict(status='original_weather_capacity_and_geographic_shares_replayed_before_offer_pooling',producer_sha256=digest(__file__),input_summary_sha256=digest(OUT/'inputs-protocol-v2.json'),components_sha256=digest(dest),source_hashes={str(p.relative_to(ROOT)):digest(p) for p in [network,mapping,layout_path,irena]},maximum_reconstruction_error_mw=float(abs((solar+wind)[:,renewable]-original[:,renewable]).max()))
    (OUT/'resource-components.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['maximum_reconstruction_error_mw'],flush=True)
if __name__=='__main__':prepare()
