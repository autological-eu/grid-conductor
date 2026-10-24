"""Compact results only after independent best-epoch witness replay."""
import csv
import html
import json
import numpy as np
from run_forward_hourly_splines_2025 import OUT, ROOT
from supply_knot_network_2025 import load
from sigmoid_month_pairs_2025 import FAMILIES


def run():
    audit=json.loads((OUT/'audit.json').read_text())
    if audit['status']!='passed': raise ValueError('Audit required')
    history=json.loads((OUT/'history.json').read_text())
    row=history[audit['selected_iteration']]
    sealed,data,_,_,_=load()
    target=ROOT/'research/forward-hourly-splines-2025.md'
    assets=ROOT/'research/assets'
    assets.mkdir(exist_ok=True)
    columns=['month','fit_price_mae','averaged_within_price_mae','forward_price_mae','fit_mix_mae_twh','forward_mix_mae_twh']
    csvpath=assets/'forward-hourly-splines-months-2025.csv'
    with csvpath.open('w') as f:
        writer=csv.writer(f);writer.writerow(columns)
        for r in row['months']:
            forward=r.get('forward',{}).get('metrics',{})
            writer.writerow([r['month'],r['within']['metrics']['price_mae'],r['within_averaged']['metrics']['price_mae'],forward.get('price_mae',''),r['within']['metrics']['generation_mae_twh'],forward.get('generation_mae_twh','')])
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="370" viewBox="0 0 920 370"><rect width="920" height="370" fill="white"/><g font-family="sans-serif" fill="#172033">']
    maxval=max(r['within_averaged']['metrics']['price_mae'] for r in row['months'])
    maxval=max(maxval,max(r.get('forward',{'metrics':{'price_mae':0}})['metrics']['price_mae'] for r in row['months']))*1.12
    for y in range(5):
        py=290-y*55
        svg.append(f'<path d="M70 {py}H880" stroke="#e5e7eb"/><text x="15" y="{py+5}">{maxval*y/4:.0f}</text>')
    for key,color,label,dy in [('within','#2563eb','Independent hourly fit',0),('within_averaged','#9b59b6','Averaged curves, same month',20),('forward','#e87524','Forward prediction',40)]:
        points=[]
        for r in row['months']:
            if key not in r:continue
            month=r['month']+(1 if key=='forward' else 0)
            x=70+(month-1)*810/11
            y=290-r[key]['metrics']['price_mae']/maxval*220
            points.append(f'{x:.2f},{y:.2f}')
        svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/><text x="70" y="{320+dy}" fill="{color}">{label}</text>')
    for m in range(1,13):svg.append(f'<text x="{70+(m-1)*810/11:.1f}" y="309">{m}</text>')
    svg.append('<text x="70" y="25">Hourly price MAE (EUR/MWh), by evaluation month</text></g></svg>')
    (assets/'forward-hourly-splines-months-2025.svg').write_text(''.join(svg))
    complete=np.isfinite(data['observed_prices']).all(axis=0)
    abs_error=[]
    with (assets/'forward-hourly-splines-zones-2025.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['zone','hours','forward_mae_eur_mwh'])
        for m in range(1,12):
            with np.load(OUT/f'best/month-{m:02d}/forward.npz') as z:
                abs_error.append(abs(z['row_duals'][:,:sealed['nz']]-data['observed_prices'][z['hours']]))
        error=np.concatenate(abs_error)
        for j in np.flatnonzero(complete):writer.writerow([sealed['zones'][j],len(error),float(error[:,j].mean())])
    with (assets/'forward-hourly-splines-generation-2025.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['month','country','technology_family','observed_twh','within_twh','averaged_within_twh','forward_twh'])
        for month in range(1,13):
            fitted=row['months'][month-1]
            predicted=row['months'][month-2].get('forward') if month>1 else None
            for c,country in enumerate(sealed['countries']):
                for k,family in enumerate(FAMILIES):
                    observed=data['ember'][month-1,c,k]
                    if np.isfinite(observed):writer.writerow([month,country,family,observed,fitted['within']['monthly_generation_twh'][c][k],fitted['within_averaged']['monthly_generation_twh'][c][k],predicted['monthly_generation_twh'][c][k] if predicted else ''])
    table=[]
    for label,key in [('Hourly fits, all12 months','within'),('Hourly fits, matched Feb–Dec','within_matched'),('Averaged curves, matched Feb–Dec','within_averaged_matched'),('Next-month predictions, Feb–Dec','forward')]:
        r=row[key];table.append(f"| {label} | {r['hours']:,} | {r['price_mae']:.3f} | {r['generation_mae_twh']:.4f} | {r['generation_normalized_mae']:.4f} |")
    text=f'''# Hourly spline fits and next-month validation —2025

Twelve separate monthly models fit every chronological hour; eleven adjacent
forward predictions cover February–December. The selected common iteration is
**{audit['selected_iteration']}**, chosen by next-month original-LP price MAE.
The loop evaluated{len(history)} epochs and stopped after three consecutive
nonimprovements of at least0.000001 EUR/MWh. January has no preceding2025 fit;
December's fit requires January2026 data for its own forward evaluation.

| Evaluation | Hours | Price MAE EUR/MWh | Monthly mix MAE TWh | Normalized mix MAE |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

![Within and forward monthly errors](assets/forward-hourly-splines-months-2025.svg)

Each hour/technology/zone has its own midpoint and five positive increments at
0/20/40/60/80/100% available output. Monotone cubic bids are fitted by full-month
smooth-clearing price/dispatch adjoints, using hourly ENTSO-E price error and
actual monthly Ember generation totals. Every month starts from the same neutral
source-cost-anchored curve. Shrinkage and adjacent-hour departure penalties both
have weight0.01; Adam learning rate0.5. Wind/solar/run-of-river bid zero.

For prediction, average the economic **functions** at each local hour of week,
only over training hours with available output. The average of cubic coefficients
is the exact pointwise curve mean, not a new fit of averaged raw parameters.
Unsupported slots use that resource's training-month mean; entirely absent
resources use the neutral prior. Target-month prices and generation do not enter
this transfer. Actual target-hour demand, MW, source/fuel-cost anchors, original
network constraints and fixed hydro injections remain exogenous inputs.

All reported scores use the original20-tranche LP with exact average bid prices,
not the regularized smooth training prices. Prices use the same41 complete
ENTSO-E zones. Generation is compared only with known monthly country/family
Ember targets; national totals are not hourly bidding-zone observations.
Equal-price renewable dispatch allocations can be nonunique.

The independent audit rebuilt cubic costs with SciPy PCHIP and replayed
{audit['hours']:,} selected-epoch witness hours across the three evaluations.
Original feasibility1e-4 MW, objective/complementarity0.05 EUR and free reduced
cost1e-5 EUR/MWh gates remain unchanged. Full witness files and source hashes are
local ignored artifacts; see `forward-hourly-splines-v1/provenance.json` and
`audit.json`. Intermediate interior states are pruned; all epoch scores and
archived coefficients remain retained, together with initial/best/last LP evidence.

These are retrospective **perfect-input model-selection validation** results.
Next-month errors determine stopping, so they are not an untouched test set.
The full2025 inputs were previously investigated. Fixed observed hydro and actual
future weather/demand mean this is not an operational forecasting experiment.
No accepted baseline or public explorer is changed.

Compare matched February–December hourly fits with averaged within-month curves
to quantify averaging loss, then compare those with forward predictions to assess
transfer. A lower within-month error alone does not establish predictive gain.

[Monthly scores](assets/forward-hourly-splines-months-2025.csv) ·
[Per-zone forward errors](assets/forward-hourly-splines-zones-2025.csv) ·
[Country/technology monthly generation](assets/forward-hourly-splines-generation-2025.csv)
'''
    target.write_text(text)
    print(str(target.relative_to(ROOT)))


if __name__=='__main__':run()
