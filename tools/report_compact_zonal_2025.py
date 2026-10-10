"""Append compact trial evidence to the maintained daily report, no third model page."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
from compare_daily_dispatch_prices import metrics, model_area, audit_observations

ROOT=Path(__file__).resolve().parents[1]
HEADER='## Compact zonal rolling-storage trial'


def publish(folder):
    s=json.loads((folder/'summary.json').read_text());replay=json.loads((folder/'replay.json').read_text())
    if s['hours']!=8760 or s['days']!=365 or replay['summary_sha256']!=digest(folder/'summary.json'):
        raise ValueError('Verified complete annual trial required')
    with np.load(folder/'annual.npz',allow_pickle=False) as a:prices=a['prices'].copy()
    network=json.loads((folder/'network.json').read_text());areas=network['zones']
    if prices.shape!=(8760,len(areas)) or not np.isfinite(prices).all():
        raise ValueError('Invalid annual price witness')
    if any(r['day']!=d or r['start_hour']!=d*24 or r['status']!='optimal' for d,r in enumerate(s['records'])):
        raise ValueError('Incomplete chronology/termination')
    root=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((root/'manifest.json').read_text())
    rows=[];excluded=[];observations={}
    for zone,meta in sorted(manifest['zones'].items()):
        area,scope=model_area(zone)
        if area not in areas:
            excluded.append(dict(zone=zone,reason=scope));continue
        path=root/(zone+'.json')
        if digest(path)!=meta['hourly_sha256']:raise ValueError('Observation changed')
        observed=np.array([np.nan if v is None else v for v in json.loads(path.read_text())])
        audit_observations(zone,meta,observed)
        if not np.isfinite(observed).any():
            excluded.append(dict(zone=zone,reason='No observed A44 prices; no price error can be computed'))
            continue
        rows.append(dict(zone=zone,area=area,mapping_scope=scope,observation_sha256=digest(path),**metrics(prices[:,areas.index(area)],observed)))
        observations[zone]=observed
    de=prices[:,areas.index('0:DE')];observed=observations['DE-LU'];dates=pd.date_range('2025-01-01',periods=8760,freq='h')
    out=ROOT/'public/research/daily-fuel-annual-2025';image=out/'compact-zonal.png'
    fig,axes=plt.subplots(3,1,figsize=(12,11),layout='constrained')
    axes[0].plot(dates[:168],de[:168],label='Compact zonal DE proxy');axes[0].plot(dates[:168],observed[:168],label='Observed ENTSO-E DE-LU',alpha=.8)
    axes[0].set(ylabel='EUR/MWh',title='First week: untuned hourly clearing versus observations');axes[0].legend()
    months=[metrics(de[dates.month==month],observed[dates.month==month]) for month in range(1,13)]
    axes[1].bar(range(1,13),[r['mae_eur_mwh'] for r in months]);axes[1].set(xticks=range(1,13),xlabel='Month',ylabel='EUR/MWh',title='German proxy: monthly mean absolute price error')
    axes[2].bar([r['zone'] for r in rows],[r['mae_eur_mwh'] for r in rows]);axes[2].tick_params(axis='x',rotation=90)
    axes[2].set(ylabel='EUR/MWh',title='All mapped observed zones: mean absolute price error (country proxies reused)')
    fig.savefig(image,dpi=120);plt.close(fig)
    g=next(r for r in rows if r['zone']=='DE-LU').copy()
    g['pairs']=g['known_hours']
    compact={k:v for k,v in s.items() if k!='records'}
    compact['workbench_series_germany_diagnostic']=compact['germany']
    compact['germany']=g
    compact.update(source_summary_sha256=digest(folder/'summary.json'),replay=replay,
                   publication_producer_sha256=digest(__file__),observed_manifest_sha256=digest(root/'manifest.json'),
                   mapped_zone_errors=rows,excluded=excluded,germany_monthly=months,image_sha256=digest(image),
                   window_statistics=dict(variables=s['records'][0]['variables'],rows=s['records'][0]['rows'],nonzeros=s['records'][0]['nonzeros'],
                       optimal_days=sum(r['status']=='optimal' for r in s['records']),
                       maximum_live_lp_residual=max(r['maximum_residual'] for r in s['records']),
                       median_solver_seconds=float(np.median([r['solver_seconds'] for r in s['records']])),
                       maximum_solver_seconds=max(r['solver_seconds'] for r in s['records'])))
    (out/'compact-zonal.json').write_text(json.dumps(compact,separators=(',',':'),allow_nan=False)+'\n')
    p=s['physics'];r=s['records'][0]
    norway_errors=[row['mae_eur_mwh'] for row in rows if row['zone'].startswith('NO')]
    norway_range=f'{min(norway_errors):.2f}–{max(norway_errors):.2f}' if norway_errors else 'unavailable'
    checks='\n'.join(f"| {i['start_hour']//24+1} | {i['hours']} | {i['objective_difference_eur']:.6g} | {i['maximum_price_difference_eur_mwh']:.6g} |" for i in s['native_checks'])
    text=f'''{HEADER}

This fresh Europe-wide experiment simplifies the current daily engine rather than
changing the observed bottleneck baseline or browser simulator. It clears **365
UTC days / 8,760 hours** across **{s['areas']} country/AC-island areas**, with
{s['offers']} equivalent offers, {s['links']} transport links and all {s['storage_units']}
original storage inventories. No observed electricity price is an optimisation input.

### What changed

Cross-area passive AC lines become lossless transport corridors bounded by the
**sum of their original N-0 ratings**. Original controllable links retain their
hourly signed bounds and efficiencies. Internal passive constraints, Kirchhoff
relations and GSK/PTDF rows are omitted. These are optimistic **model-derived
transport envelopes**, not commercial NTC, JAO constraints or a physical grid
feasibility certificate; country/island geography is still not audited bidding zones.

A sparse persistent LP optimises today plus tomorrow and implements today only.
The final window is shortened to 24 hours: no missing 31 December and no fabricated
2026 tail. Generator offers and original 2025 availability/demand are unchanged,
including IRENA linear wind/solar commissioning and the same monthly TTF/Brent,
EUR80/t carbon and prepared thermal efficiencies/costs. Reservoirs keep original
inflow, spill, losses, turbine limits and actual carried water stocks. PHS/batteries
keep charge/discharge efficiency and power/energy bounds. Only identically zero
charging/spill modes are removed from the sparse matrix; storage units are not merged.

The separate expected-price forecast and threshold-bid stage is replaced here by
**central short-horizon dispatch**, not independently strategic operator bidding.
Natural reservoirs receive a soft end-window seasonal-stock target: initial stock
plus cumulative inflow minus a uniform annual release budget, clipped to capacity.
Absolute deviation costs **EUR40 per stored MWh**, a declared untuned heuristic
using the existing inventory-adjustment scale, not an observed or forecast water
price. Short storage has no soft seasonal target. Backward per-unit reachability
protects the same year-end stocks; future network feasibility is not guaranteed
by these bounds alone. Charge/discharge friction is EUR0.001/MWh; battery wear
remains EUR2/MWh discharged. No daily water budgets or stock resets are used.

### Measured runtime and verification

| Measurement | Compact trial |
| --- | ---: |
| Actual daily/window solver time | {s['solver_seconds']:.2f} s |
| Hourly vectors/solver updates | {s['daily_vector_preparation_seconds']:.2f} s |
| Input compilation and source checks | {s['input_preparation_seconds']:.2f} s |
| Three native checks, including native construction | {s['native_seconds']:.2f} s |
| Full command including native checks and witness export | {s['elapsed_seconds']:.2f} s |
| Full command minus native-check time | {s['elapsed_seconds']-s['native_seconds']:.2f} s |
| Peak process RSS | {s['peak_rss_mib']:.0f} MiB |
| Typical 48-hour LP | {r['variables']:,} variables / {r['rows']:,} rows / {r['nonzeros']:,} nonzeros |
| Independently replayed component residual | {p['maximum_residual']:.3g} |
| Closing-stock residual | {p['closure_mwh']:.3g} MWh |
| Simultaneous charge/discharge | {p['simultaneous_storage_hours']} unit-hours |
| Emergency supply | {p['emergency_supply_twh']:.6f} TWh |
| Implemented-hour variable operating cost | EUR {p['operating_cost_eur']/1e9:.3f} billion |

All 365 windows terminate optimal and pass live LP residual checks. A separate
process reconstructs the source case and replays saved **implemented** generation,
transfers, power/energy bounds, hourly water balances, carried stocks and closure
using component equations rather than the producer's matrix. Lookahead objectives
and seasonal penalties are not summed into annual operating cost: overlapping
forecast hours would double-count energy. Replay/native timings are separate;
these checks do not certify an annual optimum or empirical agreement.

| UTC starting day | Window hours | Native minus custom objective, EUR | Maximum dual-price difference, EUR/MWh |
| --- | ---: | ---: | ---: |
{checks}

Native PyPSA independently formulates the same zonal links, storage equations,
reachability and soft targets. Equal objectives can coexist with different dual
prices under degeneracy; native agreement verifies this simplified formulation,
not the original physical grid or actual market prices.

### Observed-price diagnostics and conclusion

German country-proxy MAE is **EUR{g['mae_eur_mwh']:.2f}/MWh**, bias
EUR{g['bias_eur_mwh']:.2f}/MWh, RMSE EUR{g['rmse_eur_mwh']:.2f}/MWh and correlation
{g['correlation']:.3f} over {g['pairs']:,} observed pairs. The model has
{g['model_negative_hours']} negative-price hours versus {g['observed_negative_hours']}
observed. The retained physical/bidding reference has German MAE EUR22.22/MWh and
0.852118 TWh emergency supply; these policy/network changes are **not an exact
acceleration of that reference**. All {len(rows)} eligible mapped observed zones
are reported, without clipping errors, fitting parameters or filling missing prices.
The primary comparison uses the same direct A44 validation series as the retained
reference, rather than the older workbench price series; both are labelled in the
compact evidence. Raw A44 requests/hashes/hourly aggregation are rechecked; Norway, Sweden and mainland
Italy still reuse country proxies. This is descriptive evidence, not held-out acceptance.

Norwegian country-proxy price MAE remains EUR{norway_range}/MWh across mapped Norwegian zones;
less shortage has not resolved hydro valuation or internal-zone geography.

![Compact zonal trial: observed prices and all mapped zone errors](/research/daily-fuel-annual-2025/compact-zonal.png)

[Compact trial timings, assumptions, native checks, replay and zone diagnostics](/research/daily-fuel-annual-2025/compact-zonal.json)

The simplified formulation establishes a measured European baseline for further
work. It has not replaced the retained model or browser screen. Commercial transfer
limits, geographic reconciliation, hydro-target/lookahead sensitivity and paired
investment/native tests remain necessary before using it to value investments.
'''
    document=ROOT/'docs/daily-fuel-dispatch-2025.md';old=document.read_text().split(HEADER)[0].rstrip()
    document.write_text(old+'\n\n'+text)
    print(json.dumps(dict(mapped_zones=len(rows),germany=g,elapsed_seconds=s['elapsed_seconds'],solver_seconds=s['solver_seconds'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args();publish(args.run)
