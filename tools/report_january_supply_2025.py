"""Update the January investigation with audited source findings; no publication."""
import csv
import datetime as dt
import gzip
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from zoneinfo import ZoneInfo
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1'
BASE=ROOT/'data/bidding-zone-network-2025/thermal-event-v1'
RUN=OUT/'clearing-v1'
LABELS={'control':'Current book','solar_interval':'Solar interval alignment','de_capacity':'DE thermal capacity','solar_capacity':'Both source corrections'}


def report():
    summary=json.loads((RUN/'summary.json').read_text());audit=json.loads((RUN/'audit.json').read_text());assert audit['summary_sha256']==digest(RUN/'summary.json') and audit['status']=='sources_and_all_four_network_cases_replayed'
    for name,h in audit['normalized_sha256'].items():assert digest(OUT/(name+'.json'))==h
    assert audit['collection_sha256']==digest(OUT/'collection.json') and audit['diagnostics_sha256']==digest(RUN/'source-diagnostics.npz')
    meta=json.loads((BASE/'inputs-protocol-v2.json').read_text());source=dict(np.load(BASE/'inputs.npz'));rec=dict(np.load(OUT/'reconciliation-inputs.npz'));prepared=json.loads((OUT/'reconciliation-inputs.json').read_text());a,b=meta['start_hour'],meta['stop_hour'];t=184;de=meta['zones'].index('DE-LU');cases=summary['design']['cases'];witness={name:dict(np.load(RUN/(name+'.npz'))) for name in cases};stamp=int(dt.datetime(2025,1,20,16,tzinfo=dt.timezone.utc).timestamp()*1000)
    def smard(name):
        rows=dict(json.loads((OUT/(name+'.json')).read_text())['samples'])
        return np.array([rows[stamp+(i-t)*3600000] for i in range(240)])
    records=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))['irena_rows']
    with xr.open_dataset(ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc') as ds:
        fuel=ds.generators_carrier.values.astype(str);country_map=dict(zip(ds.buses_i.values,ds.buses_country.values));country=np.array([country_map[x] for x in ds.generators_bus.values]);names=ds.generators_i.values.astype(str).tolist();cols=list(ds.generators_t_p_max_pu_i.values);nom=ds.generators_p_nom.values;raw=ds.generators_t_p_max_pu.isel(snapshots=slice(a,b)).values;wind={}
        ids=np.flatnonzero((country=='DE')&np.isin(fuel,['onwind','offwind-ac','offwind-dc','offwind-float']));row=next(r for r in records if r['country']=='DE' and r['technology']=='Wind energy');wind_total=row['capacity_2024']['mw']+(row['capacity_2025']['mw']-row['capacity_2024']['mw'])*np.arange(a,b)/8760;factor=wind_total/nom[ids].sum()
        for key,carriers in [('onshore',['onwind']),('offshore',['offwind-ac','offwind-dc','offwind-float'])]:
            selected=np.flatnonzero((country=='DE')&np.isin(fuel,carriers));wind[key]=np.sum(raw[:,[cols.index(names[j]) for j in selected]]*nom[selected],axis=1)*factor
        load_ids=[i for i,bus in enumerate(ds.loads_bus.values) if country_map[bus]=='DE'];model_load=ds.loads_t_p_set.isel(snapshots=slice(a,b)).values[:,load_ids].sum(axis=1)
    with np.load(RUN/'source-diagnostics.npz') as z:
        np.testing.assert_allclose(model_load,z['model_load'],rtol=0,atol=1e-7)
        for key in wind:np.testing.assert_allclose(wind[key],z[key],rtol=0,atol=1e-7)
    forecast_total=smard('forecast_wind_solar');forecast_load=smard('forecast_load');actual_load=smard('actual_load');forecast_residual=forecast_load-forecast_total;model_residual=model_load-wind['onshore']-wind['offshore']-rec['de_solar'];aligned_residual=model_load-wind['onshore']-wind['offshore']-rec['de_solar_aligned']
    rows=[dict(name=LABELS[name],jan20_eur_mwh=summary['cases'][name]['january20_16utc_eur_mwh'],eu_mae_eur_mwh=summary['cases'][name]['mae_eur_mwh'],de_mae_eur_mwh=summary['cases'][name]['german_mae_eur_mwh'],emergency_mwh=summary['cases'][name]['emergency_mwh'],solver_seconds=summary['cases'][name]['solver_seconds']) for name in cases]
    with (RUN/'comparison.csv').open('w') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report_path=ROOT/'research/january-scarcity-2025.md';assets=ROOT/'research/assets';prior=OUT/'previous-report';prior.mkdir(exist_ok=True)
    if not (prior/'january-scarcity-2025.md').exists():
        old=json.loads((BASE/'runs-v7/report-receipt.json').read_text());assert old['report_sha256']==digest(report_path)
        shutil.copyfile(report_path,prior/report_path.name)
        for filename,h in old['figures_sha256'].items():assert digest(assets/filename)==h;shutil.copyfile(assets/filename,prior/filename)
        (prior/'receipt.json').write_text(json.dumps(old,indent=2)+'\n')
    colors=['#333333','#287faf','#bd7733','#267955'];plt.rcParams.update({'font.size':10})
    fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True);hours=np.arange(24);sl=slice(168,192)
    axes[0].plot(hours,source['observed'][sl,de],color='black',lw=2,label='ENTSO-E SDAC')
    for name,color in zip(cases,colors):axes[0].plot(hours,witness[name]['row_duals'][sl,de],color=color,label=LABELS[name],lw=1.3)
    axes[0].set_ylabel('DE-LU price\nEUR/MWh');axes[0].legend(ncol=2,fontsize=8)
    axes[1].plot(hours,rec['de_solar'][sl]/1000,label='Original modeled availability');axes[1].plot(hours,rec['de_solar_aligned'][sl]/1000,label='Aligned modeled availability');axes[1].plot(hours,smard('actual_solar')[sl]/1000,label='SMARD actual generation',color='black');axes[1].plot(hours,smard('forecast_solar')[sl]/1000,label='SMARD forecast generation',ls='--');axes[1].set_ylabel('German solar\nGW');axes[1].legend(ncol=2,fontsize=8)
    axes[2].plot(hours,(wind['onshore'][sl]+wind['offshore'][sl])/1000,label='Modeled wind availability');axes[2].plot(hours,(smard('actual_onshore')[sl]+smard('actual_offshore')[sl])/1000,label='SMARD actual generation',color='black');axes[2].plot(hours,(smard('forecast_onshore')[sl]+smard('forecast_offshore')[sl])/1000,label='SMARD forecast generation',ls='--');axes[2].set_ylabel('German wind\nGW');axes[2].legend(ncol=2,fontsize=8);axes[2].set_xlabel('January 20, 2025 — UTC interval start')
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Source reconciliation: clocks, forecast supply and the missed price spike');fig.tight_layout();fig.savefig(assets/'january-scarcity-prices.png',dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,3.5));y=np.arange(4);axes[0].barh(y,[r['jan20_eur_mwh'] for r in rows],color=colors);axes[0].set_yticks(y,[r['name'] for r in rows]);axes[0].axvline(583.4,color='black',ls='--',label='Observed 583.40');axes[0].legend(fontsize=8);axes[0].set_xlabel('Jan 20 16 UTC, EUR/MWh');axes[1].barh(y,[r['eu_mae_eur_mwh'] for r in rows],color=colors);axes[1].set_yticks(y,['']*4);axes[1].set_xlabel('Event-week European MAE, EUR/MWh')
    for ax in axes:ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(assets/'january-scarcity-comparison.png',dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    lines=['# January 2025 price-spike investigation','','Source follow-up, 22 October 2026. Research evidence; current public model and accepted baseline remain unchanged.','','## Findings','',
        '**Two input problems are substantiated:** ERA5 solar intervals were carried into hour-start market snapshots one hour late, and the inherited German coal fleet exceeds reported 2025 net installed capacity. Correcting these inputs still leaves the January 20 price spike largely unexplained.','',
        f"The combined case gives **€{rows[3]['jan20_eur_mwh']:.2f}/MWh** at January 20, 16:00 UTC, versus **€583.40 observed**. Reported-capacity reconciliation alone improves German event-week MAE **€{rows[0]['de_mae_eur_mwh']:.2f}→€{rows[2]['de_mae_eur_mwh']:.2f}/MWh**. Solar timing alignment alone slightly worsens price MAE: retain that adverse outcome. No price-selected shift, bid fit, model selection or promotion was performed.",'',
        '## Forecast supply balance','',
        'SMARD is the Bundesnetzagentur public source, with TSO/ENTSO-E data and explicit series IDs. Forecast generation, actual generation, modeled available supply and demand have different meanings. Values below refer to Germany; price comparisons use DE-LU. All prices remain corrected original ENTSO-E A44 SDAC targets.','',
        '| January 20, 16 UTC | Original model MW | Aligned model MW | SMARD forecast MW | SMARD actual MW |','|---|---:|---:|---:|---:|',
        f"| Solar | {rec['de_solar'][t]:.2f} | {rec['de_solar_aligned'][t]:.2f} | {smard('forecast_solar')[t]:.2f} | {smard('actual_solar')[t]:.2f} |",
        f"| Onshore wind | {wind['onshore'][t]:.2f} | unchanged | {smard('forecast_onshore')[t]:.2f} | {smard('actual_onshore')[t]:.2f} |",
        f"| Offshore wind | {wind['offshore'][t]:.2f} | unchanged | {smard('forecast_offshore')[t]:.2f} | {smard('actual_offshore')[t]:.2f} |",
        f"| Grid load | {model_load[t]:.2f} | unchanged | {forecast_load[t]:.2f} | {actual_load[t]:.2f} |",'',
        f"Residual load here means **grid load minus wind and solar**. It is {model_residual[t]/1000:.2f} GW in the original inputs and {aligned_residual[t]/1000:.2f} GW after solar alignment, versus {forecast_residual[t]/1000:.2f} GW in the forecast archive. This is a tightness diagnostic, not a newly fitted bid feature. Realized demand is higher than forecast at this hour; an underestimated German demand input is not the apparent problem.",'',
        '**Forecast-vintage limit:** these are current archived forecast series, not verified pre-auction snapshots. SMARD distinguishes day-ahead and intraday forecasts; its guidance describes renewable forecast publication by 18:00 for the following day, after the midday auction. File creation metadata does not establish the original forecast issue time. We therefore use these forecasts only as retrospective diagnostics, not recovered auction offers or physical resource bounds. Actual generation is never substituted for availability.','',
        '![Price, solar and wind evidence for January 20](assets/january-scarcity-prices.png)','','## Solar timing correction','',
        'ECMWF defines ERA5 accumulated radiation as covering the preceding hour. The installed atlite adapter explicitly says 13:01–14:00 is labeled 14:00 and computes solar position at the interval midpoint. Our compact converter retains the source clock; the renewable loader copies profiles directly to market snapshots. Every original solar/PV-tracker generator profile matches the network coefficient exactly in the source replay. The market demand/price clock labels interval starts.','',
        'The correction uses **PV coefficient at t+1 for market interval [t,t+1)**. Wind coefficients are unchanged. Destination-hour IRENA commissioning, source-country membership, plant geography and tranche shares are preserved. Original files remain intact; corrected coefficients are separate arrays. No circular roll, correlation-selected lag, weather rescaling or generation replacement is used.','',
        'This fixes interval semantics, not the size of the midday solar resource estimate. A full-year corrected profile still needs the right-edge 2026-01-01 00:00 coefficient; this study neither wraps nor fills that endpoint. No annual corrected-profile or price-accuracy claim follows from this ten-day test.','','## German thermal-capacity reconciliation','',
        'SMARD reports net installed capacity in MW, with an annual reporting calendar. The 2025 label is resolved in Europe/Berlin, including a UTC timestamp on December 31, 2024. These are revised annual stock figures, **not dated hourly outages, market-eligible offered capacity, or proof of January 20 availability**.','',
        '| Technology | Inherited model MW | SMARD reported 2025 MW | Applied factor |','|---|---:|---:|---:|']
    for row in prepared['capacity']:lines.append(f"| {row['technology']} | {row['model_mw']:.2f} | {row['reported_2025_mw']:.2f} | {row['factor']:.4f} |")
    lines+=['', 'The capacity case proportionally reconciles only existing German coal/lignite/gas offer upper bounds, keeping spatial membership, relative offer tranches and bids unchanged. German/Luxembourg membership is checked against original source-country labels; no Luxembourg thermal fleet is folded into the German totals. Gas nameplate is already close to the reported stock. Hourly outages and commercial availability remain unresolved, so this is a reported-stock sensitivity, not a reconstructed available fleet.','','## Clearing results','',
        '| Case | Jan 20 German price | European MAE | German MAE | Emergency MWh | Solver seconds |','|---|---:|---:|---:|---:|---:|']
    for row in rows:lines.append(f"| {row['name']} | {row['jan20_eur_mwh']:.2f} | {row['eu_mae_eur_mwh']:.2f} | {row['de_mae_eur_mwh']:.2f} | {row['emergency_mwh']:.6f} | {row['solver_seconds']:.3f} |")
    lines+=['','Prices/MAE are EUR/MWh. Evaluate every hour January 15–21 (168 hours), with equal weight across all 41 complete observed-price zones; German MAE is separate. All cases retain the entire European network, fixed hydro, original demand, calibrated bids, GSK, links and ratings/flow offsets. There is no startup/commitment optimization in these fast source tests. All four cases use zero emergency supply over all 240 checked hours.','',
        'The control reuses the saved annual witness and has no new solve time. The three new cases each make 240 chronological hourly solves; recorded solver time excludes collection, source reconstruction and verification. These timings are not an 8,760-hour benchmark. Existing non-oil bids retain calibration to earlier incorrectly selected auction targets; no corrected-target refit was performed.','',
        '![Fixed source cases and event-week price errors](assets/january-scarcity-comparison.png)','','## Verification and prior evidence','',
        f"Independent replay covers the original raw source responses, configuration units, all four **960 hourly LP witnesses** (240 reused control,720 new), every native network equation, bounds, unchanged costs and full primal/dual optimality. Maximum native residual is {audit['maximum_native_residual_mw']:.3g} MW and duality gap €{audit['maximum_duality_gap_eur']:.3g}. Quarter-hour energy sums match hourly energy; forecast components match their combined series. Four source-contract tests cover interval alignment across midnight, missing year endpoints and source-year selection.",'',
        'Authoritative ignored receipts: `data/bidding-zone-network-2025/january-supply-balance-v1/reconciliation-inputs.json`, `clearing-v1/summary.json`, `clearing-v1/audit.json` and `report-receipt.json`. URLs, original response bytes, retrieval timestamps and SHA256 hashes are retained. Source/case producers are `january_supply_sources_2025.py`, `january_supply_balance_2025.py` and `audit_january_supply_2025.py`.','',
        'The [prior ramp/startup investigation](https://github.com/autological-eu/grid-conductor/blob/3516be8/research/january-scarcity-2025.md) remains archived with all original witnesses: running-unit ramps left the event price at159.10; continuous startup states raised it to165.04. Its stronger stress failed the emergency-supply gate and peaked two hours late. The prior report/figures are also copied into this source checkpoint with their original hashes; no old numerical helper or receipt is rewritten.','','## Conclusion and next checks','',
        'These input corrections improve physical consistency and modestly improve the German price comparison, but they do not recover the scarcity event. Solar alignment alone slightly worsens price errors, consistent with inherited bid parameters already compensating for imperfect inputs; that possibility is not proof of its cause. Keep the source correction distinct from refitting bids.','',
        'The remaining forecast gap is chiefly wind. Gas installed capacity broadly agrees with the public stock, so the next decisive evidence is **hourly available/offered thermal capacity and bids**, along with the true regional import constraints and neighboring hydro opportunity costs. We have not identified which of these caused the observed spike.','',
        'A usable ENTSO-E API credential is not configured in this runtime, so authenticated outage queries are unavailable. Dated plant outages remain unverified; other public sources may provide evidence. This does not prevent the public SMARD audit or network solves. Obtain dated source evidence before asserting that a particular plant was unavailable; do not infer outages from low generation or from this price gap. The public model, accepted annual baseline and disabled recurring reviews remain unchanged.','','## Sources','',
        '- [ECMWF ERA5 time/accumulation convention](https://confluence.ecmwf.int/pages/viewpage.action?pageId=85415489).',
        '- [Atlite solar-interval discussion](https://github.com/PyPSA/atlite/issues/158); the locally installed adapter and exact loader/converter source bytes are hash-bound.',
        '- [SMARD forecasts](https://www.smard.de/page/en/wiki-article/5884/206318) and [net installed capacity](https://www.smard.de/page/en/wiki-article/5884/6038/installed-generation-capacity).',
        '- [SMARD API chart configuration](https://www.smard.de/app/chart_configuration/market_data_configuration.json): forecasts125/123/3791/5097/411; actual4068/4067/1225/410; installed4075/4072/198. Public SMARD data attribution: Bundesnetzagentur/SMARD, CC BY4.0.','']
    report_path.write_text('\n'.join(lines))
    receipt=dict(producer_sha256=digest(Path(__file__)),summary_sha256=digest(RUN/'summary.json'),audit_sha256=digest(RUN/'audit.json'),report_sha256=digest(report_path),previous_report_sha256=digest(prior/'january-scarcity-2025.md'),figures_sha256={name:digest(assets/name) for name in ['january-scarcity-prices.png','january-scarcity-comparison.png']},comparison_sha256=digest(RUN/'comparison.csv'),model_de_load_at_event_mw=float(model_load[t]),forecast_residual_at_event_mw=float(forecast_residual[t]),model_residual_at_event_mw=float(model_residual[t]),aligned_residual_at_event_mw=float(aligned_residual[t]),scope='Source diagnostics and fixed four-case event experiment; no publication or baseline promotion')
    (OUT/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':report()
