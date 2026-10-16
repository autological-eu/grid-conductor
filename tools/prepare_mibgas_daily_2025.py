"""Extract official 2025 Iberian gas-day indices; not a thermal-cost compiler.

Download the public workbook from URL explicitly; raw/derived files stay ignored.
No electricity-price targets, TTF substitution, daily interpolation or conversion
from gas-day dates to electricity UTC snapshots is performed here.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import numpy as np
import pandas as pd
from generation_mix_2025 import digest

URL='https://www.mibgas.es/en/file-access/MIBGAS_Data_2025.xlsx?path=AGNO_2025/XLS'
COLUMNS={f'{hub.lower()}_{kind.lower()}_eur_mwh_gas':f'MIBGAS {hub} {kind} Price Index Day-Ahead\n[EUR/MWh]' for hub in ['PVB','VTP'] for kind in ['Last','Average']}


def extract(workbook,out):
    if out.exists():raise FileExistsError(out)
    table=pd.read_excel(workbook,sheet_name='MIBGAS Indexes')
    days=pd.to_datetime(table['Delivery day'],errors='raise')
    assert not days.duplicated().any() and days.notna().all()
    assert set(days)==set(pd.date_range('2025-01-01','2025-12-31'))
    # Do not include 2026 deliveries from the workbook's separate trading sheets.
    table=table.assign(date=days).sort_values('date');rows=[]
    for _,row in table.iterrows():
        record=dict(delivery_day=row['date'].date().isoformat())
        for name,column in COLUMNS.items():
            v=row[column];record[name]=float(v) if pd.notna(v) else None
            if record[name] is not None:assert np.isfinite(v) and v>=0
        rows.append(record)
    out.mkdir(parents=True)
    csv=out/'daily-indices-2025.csv';pd.DataFrame(rows).to_csv(csv,index=False,lineterminator='\n')
    definitions=pd.read_excel(workbook,sheet_name='Definitions')
    descriptions={}
    for _,row in definitions.iterrows():
        name=str(row.iloc[0])
        if name.startswith(('MIBGAS PVB','MIBGAS VTP')):descriptions[name]=str(row.iloc[2])
    disclaimer=pd.read_excel(workbook,sheet_name='Disclaimer',header=None).to_string(index=False,header=False)
    assert 'utilizada libremente' in disclaimer and 'citar la fuente' in disclaimer
    result=dict(status='source_indices_collected_not_model_inputs',source='MIBGAS',url=URL,
                prepared_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),producer_sha256=digest(__file__),
                raw_workbook_sha256=digest(workbook),output_sha256=digest(csv),delivery_days=len(rows),
                known_days={name:sum(r[name] is not None for r in rows) for name in COLUMNS},
                columns=COLUMNS,definitions=descriptions,
                scope='PVB Spanish and VTP Portuguese delivery-day gas indices. Source indices may estimate values in illiquid periods; not independently observed trades each day.',
                reuse='Workbook disclaimer permits free public-information reuse while preserving original content and citing MIBGAS. Keep originals and mark any model conversions as derived.',
                limitations=['Gas-day start/timezone/DST and heating-value basis still need source reconciliation before converting to UTC electricity input hours.',
                             'No missing quotes filled; no use as TTF/THE or as electricity price targets; baseline unchanged.'])
    (out/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','delivery_days','known_days']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('workbook',type=Path);p.add_argument('out',type=Path);a=p.parse_args();extract(a.workbook,a.out)
