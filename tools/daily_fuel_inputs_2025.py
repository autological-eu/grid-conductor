"""Daily fuel inputs for controlled retrospective 2025 research, not live forecasts."""
import argparse,datetime as dt,io,json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT,digest

EIA_URL='https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls'
RULES_URL='https://www.mibgas.es/sites/default/files/2023%20Reglas%20del%20Mercado%20Organizado%20de%20Gas_EN.pdf'
FUEL=ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json'
GAS=ROOT/'data/fuel-prices/mibgas-daily-source-v1'
FX=ROOT/'data/fuel-prices/ecb-2025-api.csv'


def gas_day(instant):
    local=instant.astimezone(ZoneInfo('Europe/Madrid'))
    return local.date()-dt.timedelta(days=local.hour<6)


def latest(bank,date):
    available=[d for d in bank if d<=date]
    if not available:return None,None
    previous=max(available)
    if (date-previous).days>5:raise ValueError('Unexpected quote gap; do not silently bridge missing data')
    return bank[previous],previous


def prepare(workbook,rules,out):
    if out.exists():raise FileExistsError(out)
    old=json.loads(FUEL.read_text());heat=old['assumptions']['oil_mwh_th_per_barrel']
    prices=pd.read_excel(workbook,sheet_name='Data 1',header=2)
    assert prices.columns[0]=='Date' and 'Europe Brent Spot Price FOB' in prices.columns[1]
    quotes={}
    for date,value in prices.itertuples(index=False,name=None):
        date=pd.Timestamp(date).date()
        if date.year!=2025 or pd.isna(value):continue
        assert date not in quotes and np.isfinite(value) and value>0;quotes[date]=float(value)
    assert len(quotes)>240 and max(quotes)==dt.date(2025,12,31)
    fx=pd.read_csv(FX);assert (fx.KEY=='EXR.D.USD.EUR.SP00.A').all()
    exchange={dt.date.fromisoformat(row.TIME_PERIOD):float(row.OBS_VALUE) for row in fx.itertuples()}
    assert len(exchange)==len(fx) and all(v>0 and np.isfinite(v) for v in exchange.values())
    gr=json.loads((GAS/'receipt.json').read_text());ga=json.loads((GAS/'audit.json').read_text())
    assert ga['receipt_sha256']==digest(GAS/'receipt.json') and gr['output_sha256']==digest(GAS/'daily-indices-2025.csv')
    table=pd.read_csv(GAS/'daily-indices-2025.csv');banks={z:{dt.date.fromisoformat(r.delivery_day):getattr(r,hub+'_last_eur_mwh_gas') for r in table.itertuples()} for z,hub in [('ES','pvb'),('PT','vtp')]}
    arrays={k:np.array([r['oil_eur_mwh_th' if k=='oil' else 'gas_eur_mwh_th'] for r in old['hours']],float) for k in ['oil','gas_ES','gas_PT']}
    arrays.update(oil_quote_date=np.full(8760,'',dtype='U10'),fx_quote_date=np.full(8760,'',dtype='U10'),gas_delivery_day=np.full(8760,'',dtype='U10'))
    for t in range(8760):
        instant=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(hours=t);date=instant.date();gasdate=gas_day(instant)
        quote,qd=latest(quotes,date);rate,fd=latest(exchange,date)
        if quote is not None and rate is not None:
            arrays['oil'][t]=quote/rate/heat;arrays['oil_quote_date'][t]=qd.isoformat();arrays['fx_quote_date'][t]=fd.isoformat()
        if gasdate.year==2025:
            for zone,bank in banks.items():
                assert np.isfinite(bank[gasdate]) and bank[gasdate]>=0
                arrays['gas_'+zone][t]=bank[gasdate]*old['assumptions']['gas_basis_multiplier']
            arrays['gas_delivery_day'][t]=gasdate.isoformat()
    out.mkdir(parents=True)
    # Only the used 2025 observations are cached, not the entire historical EIA workbook.
    pd.DataFrame([dict(date=d.isoformat(),brent_usd_barrel=v) for d,v in sorted(quotes.items())]).to_csv(out/'brent-quotes-2025.csv',index=False,lineterminator='\n')
    np.savez_compressed(out/'inputs.npz',**arrays)
    sources={str(p.relative_to(ROOT)):digest(p) for p in [FUEL,FX,GAS/'receipt.json',GAS/'audit.json',GAS/'daily-indices-2025.csv']}
    result=dict(status='daily_oil_and_iberian_gas_inputs_prepared',producer_sha256=digest(__file__),sources=sources,
                eia=dict(url=EIA_URL,workbook_sha256=digest(workbook),quote_count=len(quotes),quote_csv_sha256=digest(out/'brent-quotes-2025.csv')),
                gas_rules=dict(url=RULES_URL,pdf_sha256=digest(rules)),inputs_sha256=digest(out/'inputs.npz'),
                oil_daily_hours=int((arrays['oil_quote_date']!='').sum()),oil_monthly_fallback_hours=int((arrays['oil_quote_date']=='').sum()),
                gas_daily_hours_per_zone=int((arrays['gas_delivery_day']!='').sum()),gas_monthly_fallback_hours_per_zone=int((arrays['gas_delivery_day']=='').sum()),
                rules=dict(gas='MIBGAS last day-ahead PVB in ES, VTP in PT only; delivery gas-day starts 06:00 Europe/Madrid (05:00 UTC winter / 04:00 UTC summer), common European gas day. Before first 2025 gas day retain monthly benchmark. Provider index estimates remain explicit.',
                    oil='EIA daily Brent USD/barrel / most recent same-or-earlier daily ECB USD/EUR / inherited 1.7 MWh thermal/barrel. Same-day ex-post observations; not an operational bid forecast. Carry last known quotes across nontrading days, at most 5 days. Retain baseline monthly oil until both 2025 series begin.',
                    basis='Keep inherited gas_basis_multiplier=1.0 and oil heat content=1.7. Gas MWh retains the baseline gross/efficiency-basis equivalence assumption; this is not a newly audited plant HHV/LHV correction.',
                    fixed='Monthly gas elsewhere, coal, carbon EUR80/t, seasonal coefficients, capacities, availability, demand, fixed hydro and grid unchanged.',
                    scope='Daily oil across modeled oil offers; daily gas only ES/PT, not Europe-wide daily TTF. Test direct quotes and a separate monthly-mean-preserving daily-shape control; no price fitting.'),
                limitations=['Brent crude is not a delivered generating-fuel price. Country gas hubs and source indices are proxies for plant fuel acquisition costs.',
                              'Gas-day convention and source values are reconciled, but inherited heating-value and efficiency assumptions remain model limitations.',
                              'No electricity-price targets used in source preparation; accuracy remains retrospective annual reconstruction.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k.endswith('hours') or k.endswith('zone')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workbook',type=Path);p.add_argument('rules',type=Path);p.add_argument('out',type=Path);a=p.parse_args();prepare(a.workbook,a.rules,a.out)
