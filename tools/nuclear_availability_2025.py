"""RTE national daily availability proxies, distinct from generation and unit outages."""
import csv,datetime as dt,io,json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import xarray as xr
from generation_mix_2025 import ROOT,digest
from synthetic_bids_2025 import SOURCE

PAGE='https://analysesetdonnees.rte-france.com/production/nucleaire'
CSV='https://analysesetdonnees.rte-france.com/system/files/graphDownloads/RTE_PAD_disponibilite_nucleaire.csv'
CASES=['annual_mean','daily_utc','daily_paris']
DESIGN=dict(cases=['baseline']+CASES,
    source='RTE daily French nuclear available GW from REMIT. Never use generation as available supply. Annual mean control uses only the 365 source dates of 2025.',
    daily='Daily reported values are repeated within a day as an hourly approximation, not certified hourly maxima or plant-level outage schedules. Date labels lack timezone: UTC and Europe/Paris mappings are explicit alignment controls, not a verified clock correction. Paris mapping needs the adjacent 2026-01-01 boundary record.',
    allocation='Replace FR source-country nuclear available MW, distributing national values by retained source nameplate weights. Preserve original geographical/GSK allocation, grouping and nominal capacities; this is a national proxy, not unit outage reconstruction. Reject values above retained national nameplate; no clipping or capacity creation.',
    frozen='Accepted annual seasonal refit coefficients, monthly fuel anchors, all renewable availability, demand, fixed hydro chronology, grid/GSK and all other countries/resources unchanged. No generation/price fitting and no auto-promotion.',
    evaluation='All 8760 2025 UTC hours and all41 observed price areas. Baseline uses the intact accepted annual witness. Annual-mean versus daily controls distinguish level and shape approximately; timezone mapping also changes boundary hours. Retrospective source-based reconstruction, not a day-ahead-information forecast or investment validation.')


def collect(out):
    import requests
    out.mkdir(parents=True,exist_ok=False)
    sources={}
    for name,url in [('availability.csv',CSV),('methodology.html',PAGE)]:
        r=requests.get(url,timeout=60);r.raise_for_status();(out/name).write_bytes(r.content)
        sources[name]=dict(url=url,sha256=digest(out/name),bytes=len(r.content))
    days=parse((out/'availability.csv').read_bytes());values=hourly(days,'daily_utc')
    receipt=dict(provider='RTE',retrieved_utc=dt.datetime.now(dt.timezone.utc).isoformat(),sources=sources,producer_sha256=digest(__file__),days_2025=365,minimum_mw=float(values.min()),mean_mw=float(values.mean()),maximum_mw=float(values.max()),scope='French national reported nuclear availability; original small multi-year CSV retained for exact source replay, only2025 plus Paris boundary used.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def parse(raw):
    rows=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';');assert rows.fieldnames==['Date','Filière','Valeur (GW)']
    days={}
    for row in rows:
        if row['Filière']!='Disponibilité du parc nucléaire':continue
        day=dt.datetime.strptime(row['Date'],'%Y/%m/%d').date()
        if not (dt.date(2025,1,1)<=day<=dt.date(2026,1,1)):continue
        assert day not in days,'Duplicate national source date'
        value=1000*float(row['Valeur (GW)'].replace(',','.'));assert np.isfinite(value) and value>=0
        days[day]=value
    assert set(days)>={dt.date(2025,1,1)+dt.timedelta(days=i) for i in range(365)},'Incomplete source year'
    return days


def hourly(days,case):
    assert case in CASES
    if case=='annual_mean':return np.full(8760,np.mean([days[dt.date(2025,1,1)+dt.timedelta(days=i)] for i in range(365)]))
    zone=dt.timezone.utc if case=='daily_utc' else ZoneInfo('Europe/Paris')
    start=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)
    return np.array([days[(start+dt.timedelta(hours=h)).astimezone(zone).date()] for h in range(8760)])


def membership(n):
    with xr.open_dataset(SOURCE) as d:
        country=dict(zip(d.buses_i.values,d.buses_country.values))
        names={str(k) for k,b,c in zip(d.generators_i.values,d.generators_bus.values,d.generators_carrier.values) if country[b]=='FR' and c=='nuclear'}
        original=sum(float(p) for k,p in zip(d.generators_i.values,d.generators_p_nom.values) if str(k) in names)
    mask=np.array([str(name).split('::',1)[0] in names for name in n.generators.index]);p=n.generators.p_nom.values
    assert abs(p[mask].sum()-original)<1e-6
    assert (n.generators.carrier[mask]=='nuclear').all()
    return mask,original


def replace(source,n,mask,series):
    nominal=n.generators.p_nom.values[mask];assert series.shape==(8760,) and np.isfinite(series).all() and series.min()>=0 and series.max()<=nominal.sum()
    result=source.copy();result[:,mask]=series[:,None]*(nominal/nominal.sum())[None,:]
    np.testing.assert_allclose(result[:,mask].sum(axis=1),series,atol=1e-7,rtol=1e-12)
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();print(collect(a.out)['days_2025'])
