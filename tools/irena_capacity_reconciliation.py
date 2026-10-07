"""Audited IRENA PDF capacity inventory and separate renewable capacity variants.

All renewable tables retained separately; parent/child technologies never summed.
Only wind/PV variants reuse existing hourly weather shapes. No source overwritten.
"""
import argparse,json,re,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import pycountry
import xarray as xr
from hourly_renewable_estimates import digest

ALIASES={'BA':'Bosnia Herzg','GB':'UK','MK':'North Macedonia','XK':'Kosovo'}


def number(value):
    match=re.fullmatch(r'(\d{1,3}(?: \d{3})*|\d+)(?:\.(\d+))?(?: ([oue]))?',value.strip())
    if not match: raise ValueError('Unrecognised capacity cell: '+value)
    return dict(mw=float(match[1].replace(' ','') + ('.'+match[2] if match[2] else '')),source_flag=match[3])


def extract(text,names,rejected=None):
    rows=[];seen=set()
    for page in text.split('\f'):
        if not page.strip() or 'CAP (MW)' not in page:continue
        heading=page.strip().splitlines()[0].strip()
        header=next(line for line in page.splitlines() if 'CAP (MW)' in line)
        if re.findall(r'20\d\d',header)!=[str(y) for y in range(2016,2026)]:raise ValueError('Unexpected year columns')
        for line in page.splitlines():
            cells=re.split(r'\s{2,}',line.strip())
            if not cells or cells[0] not in names:continue
            # Only full decade rows are accepted: blanks/shifted extraction remain missing.
            try:
                if len(cells)!=11: raise ValueError('Incomplete or shifted decade row')
                values=[number(v) for v in cells[1:]]
            except ValueError as error:
                if rejected is not None: rejected.append(dict(country=names[cells[0]],technology=heading,reason=str(error)))
                continue
            key=(names[cells[0]],heading)
            if key in seen:raise ValueError('Duplicate country/technology')
            seen.add(key)
            rows.append(dict(country=key[0],provider_area=cells[0],technology=heading,
                capacity_2024=values[-2],capacity_2025=values[-1]))
    if not rows:raise ValueError('No recognised capacity records')
    return rows


def run(pdf,receipt,network,base,output):
    if output.exists():raise ValueError('Preserve existing reconciliation')
    meta=json.loads(receipt.read_text())
    if digest(pdf)!=meta['sha256']:raise ValueError('IRENA source changed')
    text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],stderr=subprocess.DEVNULL).decode()
    original=json.loads((base/'summary.json').read_text())
    if digest(network)!=original['network_sha256'] or digest(base/'hourly.npz')!=original['hourly_sha256']:
        raise ValueError('Original availability identity changed')
    codes=sorted({r['country'] for r in original['countries']})
    names={ALIASES.get(c,pycountry.countries.get(alpha_2=c).name if c!='XK' else 'Kosovo'):c for c in codes}
    rejected=[]
    rows=extract(text,names,rejected)
    bank={(r['country'],r['technology']):r for r in rows}
    mapping={'solar':'Solar photovoltaic','wind':'Wind energy'}
    arrays={};comparison=[]
    with np.load(base/'hourly.npz',allow_pickle=False) as source:
        hours=source['hours_utc'];months=pd.DatetimeIndex(hours).month
        elapsed=np.arange(8760)/8760 # Linear commissioning assumption, not observed dates.
        arrays['hours_utc']=hours
        for r in original['countries']:
            ref=bank.get((r['country'],mapping[r['technology']]))
            if ref is None:continue
            key=r['country']+'_'+r['technology'];shape=source[key+'_available_mw']/r['capacity_mw']
            lo=ref['capacity_2024']['mw'];hi=ref['capacity_2025']['mw']
            variants={ 'hold_2024':np.full(8760,lo), 'linear_2025':lo+(hi-lo)*elapsed, 'hold_2025':np.full(8760,hi)}
            values={}
            for name,capacity in variants.items():
                available=shape*capacity;arrays[key+'_'+name+'_available_mw']=available
                values[name]=dict(annual_available_mwh=float(available.sum()),monthly_available_mwh=[float(available[months==m].sum()) for m in range(1,13)])
            obs=[m['observed_generation_mwh'] for m in r['months']]
            comparison.append(dict(country=r['country'],technology=r['technology'],source_capacity_mw=r['capacity_mw'],
                irena_2024_mw=lo,irena_2025_mw=hi,source_available_mwh=r['available_energy_mwh'],
                observed_generation_mwh=None if any(v is None for v in obs) else float(sum(obs)),variants=values))
    # Separate technology inventory for dispatchable renewable power and storage.
    model={}
    with xr.open_dataset(network) as d:
        countries=dict(zip(d.buses_i.values,d.buses_country.values))
        for prefix in ['generators','storage_units']:
            for bus,carrier,power in zip(d[prefix+'_bus'].values,d[prefix+'_carrier'].values,d[prefix+'_p_nom'].values):
                key=(countries[bus],str(carrier));model[key]=model.get(key,0.)+float(power)
    modelmap={'Renewable hydropower':['ror','hydro'],'Pumped hydro':['PHS'],'Bioenergy':['biomass'],
              'Geothermal energy':['geothermal'],'Marine energy':[], 'Solar photovoltaic':['solar','solar-hsat'],
              'Wind energy':['onwind','offwind-ac','offwind-dc','offwind-float']}
    inventory=[]
    for c in codes:
        for tech,carriers in modelmap.items():
            ref=bank.get((c,tech))
            inventory.append(dict(country=c,technology=tech,model_capacity_mw=sum(model.get((c,k),0.) for k in carriers),
                irena_2024_mw=None if ref is None else ref['capacity_2024']['mw'],
                irena_2025_mw=None if ref is None else ref['capacity_2025']['mw'],
                status='missing_or_unparsed_irena_row' if ref is None else 'scope_unreconciled_capacity_comparison'))
    output.mkdir(parents=True)
    np.savez_compressed(output/'variants.npz',**arrays)
    report=dict(status='capacity_sensitivity_not_accepted_dispatch_input',source_url=meta['url'],irena_pdf_sha256=meta['sha256'],
        network_sha256=digest(network),original_summary_sha256=digest(base/'summary.json'),producer_sha256=digest(__file__),
        variants_sha256=digest(output/'variants.npz'),country_count=len(codes),unparsed_rows=rejected,irena_rows=rows,capacity_inventory=inventory,wind_solar_comparison=comparison,
        limitations=['Official PDF integer-MW rounding; o/u/e flags retained; incomplete decade rows rejected, not zero-filled.',
        'National maximum net year-end capacity; parent/child and off-grid tables retained separately, never added.',
        'Linear commissioning is assumed; held endpoints are sensitivities, not certified capacity bounds.',
        'Wind/PV variants retain old national spatial/technology mix and weather shape; new locations not reconstructed.',
        'Hydro/bioenergy/geothermal/marine are capacity audits only; storage/inflow/fuel constraints not rescaled.',
        'Fossil/nuclear capacities are outside IRENA renewable inventory; no generation-fit calibration or source change.'])
    (output/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('IRENA rows:',len(rows),'capacity comparisons:',len(inventory),'wind/PV variants:',len(comparison))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['pdf','receipt','network','base','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();run(a.pdf,a.receipt,a.network,a.base,a.output)
