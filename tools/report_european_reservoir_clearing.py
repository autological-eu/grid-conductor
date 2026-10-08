"""Generate compact report figures only after independent annual primal replay."""
import csv,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/research/european-reservoir-clearing-2025'
CACHE=ROOT/'data/synthetic-europe-physical-2025-irena-linear/hydro-warm-v1'

def run():
    s=json.loads((OUT/'summary.json').read_text());r=json.loads((OUT/'replay.json').read_text())
    if r['status']!='all_59_saved_primals_replayed' or r['hours']!=8760 or r['source_signature']!=s['signature']:raise ValueError('Annual replay not verified')
    if abs(s['total_operating_cost_eur']-r['total_operating_cost_eur'])>max(.05,s['total_operating_cost_eur']*1e-9):raise ValueError('Annual cost mismatch')
    before=json.loads((ROOT/'public/research/european-physical-bids-2025-irena-linear/summary.json').read_text())
    areas=pd.DataFrame(s['area_summary']);old=pd.read_csv(ROOT/'public/research/european-physical-bids-2025-irena-linear/area-summary.csv').set_index('area')
    prices=[];receipts=[]
    for i in range(59):
        p=CACHE/f'{i:02d}.npz';receipt=json.loads((CACHE/f'{i:02d}.json').read_text());receipts.append(receipt)
        if digest(p)!=receipt['witness_sha256']:raise ValueError('Witness changed')
        with np.load(p,allow_pickle=False) as a:prices.append(a['prices'])
    prices=np.concatenate(prices);de=prices[:,list(areas.area).index('0:DE')]
    observed=np.array([np.nan if v is None else v for v in json.loads((ROOT/'public/research/zone-prices-2025/DE-LU.json').read_text())]);valid=np.isfinite(observed);error=de[valid]-observed[valid]
    if prices.shape!=(8760,len(areas)) or abs(np.abs(error).mean()-s['germany']['mae_eur_mwh'])>1e-8:raise ValueError('Price replay failed')
    dates=pd.date_range('2025-01-01',periods=8760,freq='h');frame=pd.DataFrame({'utc':dates,'simulated_eur_mwh':de,'observed_de_lu_eur_mwh':observed})
    frame.to_csv(OUT/'hourly-de.csv',index=False)
    fig,axes=plt.subplots(3,1,figsize=(12,11),layout='constrained')
    weekly=frame.set_index('utc').resample('7D').mean();axes[0].plot(weekly.index,weekly.observed_de_lu_eur_mwh,label='Observed DE-LU');axes[0].plot(weekly.index,weekly.simulated_eur_mwh,label='Reservoir-enabled mainland DE');axes[0].set(title='Germany price proxy — seven-day means of hourly results',ylabel='EUR/MWh');axes[0].legend()
    axes[1].scatter(observed[valid],de[valid],s=3,alpha=.2);low=min(observed[valid].min(),de[valid].min());high=max(observed[valid].max(),de[valid].max());axes[1].plot([low,high],[low,high],color='black',linewidth=1);axes[1].set(xlabel='Observed DE-LU EUR/MWh',ylabel='Simulated DE EUR/MWh',title=f'All {valid.sum():,} jointly observed hours; no fitting')
    axes[2].hist(error,bins=70,color='#2563eb');axes[2].axvline(0,color='black',linewidth=1);axes[2].set(xlabel='Simulated minus observed EUR/MWh',ylabel='Hours',title=f"Hourly error: MAE {abs(error).mean():.2f}, bias {error.mean():+.2f}, RMSE {np.sqrt((error**2).mean()):.2f} EUR/MWh")
    fig.savefig(OUT/'price-comparison.svg');plt.close(fig)
    comparison=areas.set_index('area')[['emergency_supply_twh']].rename(columns={'emergency_supply_twh':'reservoir_emergency_twh'}).join(old[['emergency_supply_twh']].rename(columns={'emergency_supply_twh':'no_hydro_emergency_twh'}));comparison.to_csv(OUT/'shortage-comparison.csv')
    shown=comparison.assign(rank=comparison.max(axis=1)).sort_values('rank',ascending=False).head(12).iloc[::-1];ys=np.arange(len(shown));fig,ax=plt.subplots(figsize=(12,7),layout='constrained');ax.barh(ys+.2,shown.no_hydro_emergency_twh,height=.4,label='IRENA wind/PV, reservoirs omitted');ax.barh(ys-.2,shown.reservoir_emergency_twh,height=.4,label='With chronological reservoirs');ax.set_yticks(ys,shown.index);ax.set(xlabel='Emergency supply TWh',title='Largest area shortages — same IRENA capacity inputs');ax.legend();fig.savefig(OUT/'area-shortages.svg');plt.close(fig)
    hydro=pd.read_csv(OUT/'norway-hourly.csv',parse_dates=['utc']).set_index('utc')
    if len(hydro)!=8760 or abs(hydro.hydro_mw.sum()/1e6-s['norway']['hydro_generation_twh'])>1e-8:raise ValueError('Norway hourly export mismatch')
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained');axes[0].plot(hydro.index,hydro.end_inventory_mwh/1e6);axes[0].set(ylabel='Reservoir inventory TWh',title='Norway — chronological inventory, fixed reference boundaries');axes[1].plot(hydro.index,hydro.hydro_mw/1000,label='Turbine output');axes[1].plot(hydro.index,hydro.inflow_mw/1000,label='Water-energy inflow',alpha=.5);axes[1].legend();axes[1].set(ylabel='GW');fig.savefig(OUT/'norway-hydro.svg');plt.close(fig)
    monthly=hydro.resample('MS').agg({'hydro_mw':'sum','inflow_mw':'sum','spill_mw':'sum','end_inventory_mwh':'last'})/1e6;monthly.columns=['hydro_twh','water_inflow_twh','spill_twh','end_inventory_twh'];monthly.to_csv(OUT/'norway-monthly.csv')
    no=areas[areas.area.str.endswith(':NO')];no_old=old[old.index.str.endswith(':NO')];gen=areas.assign(country=areas.area.str.split(':').str[-1]).groupby('country').hydro_generation_twh.sum().sort_values();fig,ax=plt.subplots(figsize=(12,9),layout='constrained');ax.barh(gen.index,gen.values);ax.set(xlabel='Reservoir turbine generation TWh',title='All 34 country labels — reservoir output only');fig.savefig(OUT/'country-hydro.svg');plt.close(fig)
    metrics=dict(joint_observed_hours=int(valid.sum()),norway_emergency_twh=float(no.emergency_supply_twh.sum()),prior_norway_emergency_twh=float(no_old.emergency_supply_twh.sum()),reservoir_generation_twh=float(areas.hydro_generation_twh.sum()),solver_seconds=s['solver_seconds'],preparation_seconds=s['preparation_seconds'],cold_retry_blocks=sum(v['cold_retry'] for v in receipts),report_producer_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),replay_sha256=digest(OUT/'replay.json'))
    (OUT/'report-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n');print(json.dumps(metrics,indent=2))

if __name__=='__main__':run()
