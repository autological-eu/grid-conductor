"""Add source-updated Norwegian water evidence to the existing selected-model report."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
from nve_hydro_inputs_2025 import ROOT

def publish(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'audit.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json')
    assert a['audit_producer_sha256']==digest(ROOT/'tools/audit_nve_hydro_model_2025.py')
    assert a['water_maximum_residual_mwh']<=1e-4 and s['optimal_hours']==8760
    for name,sha in s['new_sources'].items():assert digest(ROOT/'tools'/name)==sha
    old=json.loads((ROOT/'public/research/fixed-reservoir-screening-2025/resource-bids.json').read_text())
    no=next(v for v in old['diagnostics']['capacity_and_energy'] if v['country']=='NO')
    rows=[v for v in a['observed_price_comparisons'] if v['updated']['known_hours']];rows=sorted(rows,key=lambda v:v['updated']['mae_eur_mwh'],reverse=True)
    elhub=ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1/summary.json'
    # Independently audited national comparison; no observations feed input compilation.
    e=json.loads(elhub.read_text());ea=json.loads(elhub.with_name('audit.json').read_text())
    assert ea['summary_sha256']==digest(elhub)
    measured=ea['national_comparison']['Hydro']['elhub_covered_twh']
    ember=no['ember_2025_twh']['Hydro'];lo,hi=s['total_hydro_bounds_twh']
    out=ROOT/'public/research/fixed-reservoir-screening-2025'
    fig,axes=plt.subplots(2,1,figsize=(12,10),layout='constrained')
    axes[0].bar(['Frozen model','NVE-input model','Ember observed','Elhub observed'],[no['model_total_hydro_bounds_twh'][0],lo,ember,measured],color=['#8290a4','#2563eb','#15803d','#65a30d'])
    axes[0].set(ylabel='Norwegian hydro TWh',title='2025 energy: source-backed update, not generation fitting')
    for i,value in enumerate([no['model_total_hydro_bounds_twh'][0],lo,ember,measured]):axes[0].text(i,value+1,f'{value:.2f}',ha='center')
    x=np.arange(len(rows));axes[1].bar(x-.18,[v['previous']['mae_eur_mwh'] for v in rows],width=.36,label='Frozen inputs');axes[1].bar(x+.18,[v['updated']['mae_eur_mwh'] for v in rows],width=.36,label='NVE-input update')
    axes[1].set(xticks=x,xticklabels=[v['zone'] for v in rows],ylabel='Price MAE EUR/MWh',title='All eligible price areas; Norwegian zones still share one country price')
    axes[1].tick_params(axis='x',labelrotation=90);axes[1].legend()
    image=out/'nve-water-update.png';fig.savefig(image,dpi=110);plt.close(fig)
    public=dict(summary=s,audit=a,previous_hydro_bounds_twh=no['model_total_hydro_bounds_twh'],ember_hydro_twh=ember,elhub_hydro_twh=measured,elhub_summary_sha256=digest(elhub),elhub_audit_sha256=digest(elhub.with_name('audit.json')),publication_producer_sha256=digest(__file__),image_sha256=digest(image))
    (out/'nve-water-update.json').write_text(json.dumps(public,separators=(',',':'),allow_nan=False)+'\n')
    norway=[v for v in rows if v['zone'].startswith('NO')]
    price_outcome=('Norwegian price MAE improves in every observed zone, but this is still an untuned country-proxy comparison.'
        if all(v['updated']['mae_eur_mwh']<v['previous']['mae_eur_mwh'] for v in norway)
        else 'Norwegian price accuracy regresses in at least one observed zone. Keep this as an input diagnostic; do not promote it as an accepted baseline.')
    source=s['hydro_source'];native='\n'.join(f"| {v['utc']} | {v['difference_eur']:.8g} |" for v in s['native_checks'])
    errors='\n'.join(f"| {v['zone']} | {v['previous']['mae_eur_mwh']:.2f} | {v['updated']['mae_eur_mwh']:.2f} | {v['updated']['bias_eur_mwh']:.2f} |" for v in rows)
    updated=f'''## Norway: source-backed water update

The updated model keeps the same resource-bid formulation and physical network,
with corrected **2025 Norwegian water inputs**. Hydro generation changes from
**{no['model_total_hydro_bounds_twh'][0]:.2f} to {lo:.2f}–{hi:.2f} TWh**. Against Ember,
the signed model-minus-observed difference is now **{lo-ember:+.2f} to {hi-ember:+.2f} TWh**;
against Elhub it is **{lo-measured:+.2f} to {hi-measured:+.2f} TWh**. These datasets differ in scope and
must not be treated as interchangeable targets. The update is untuned evidence,
not empirical acceptance or a certified commercial-zone model. **{price_outcome}**

![Norwegian hydro update and all eligible price-area errors](/research/fixed-reservoir-screening-2025/nve-water-update.png)

### What changed, and why

1. The original ERA5 Norwegian hydro profile totals **119.519 TWh** because the
   pinned PyPSA-Eur compiler substitutes the historical EIA median when its
   generation series has no 2025 entry. This is a normalization problem, not
   evidence that turbine capacity alone is inadequate.
2. Replace that normalization with [NVE's weather-driven HBV usable-inflow series]({source['method_url']}):
   **{source['iso_2025_inflow_twh']:.3f} TWh** over ISO-2025 weeks, or
   **{source['calendar_inflow_twh']:.3f} TWh** after alignment to 8,760 UTC hours.
   The separate production/stock-derived inflow column is deliberately excluded.
   Full weeks retain the original ERA5 hourly shape; partial calendar-boundary
   weeks use uniform rates over the entire source week. DST weeks have 167/169 hours.
3. Use NVE reservoir boundary stocks, linearly interpolated from adjacent weekly
   measurements: **{source['initial_electrical_stock_twh']:.3f} →
   {source['final_electrical_stock_twh']:.3f} TWh** electrical-equivalent energy.
   Observed stock drawdown is explicit; no daily resets or additional water.
   Reported storage-energy capacity is **{source['storage_electrical_capacity_twh']:.3f} TWh**.
4. Divide electrical-equivalent reservoir inflow, capacity and stocks by original
   turbine efficiency **0.9** to obtain PyPSA's pre-dispatch stored-energy units.
   Apply that efficiency once at discharge. Run-of-river availability is electrical
   output and receives no additional efficiency conversion.
5. Retain original turbine MW and split reservoir/run-of-river water by their
   capacity shares. Country-pooled stocks and reservoir output are distributed
   over the original turbines by MW share. This is a declared allocation proxy.
6. Compute each hour's physically feasible hydro-delivery interval, holding other
   countries' schedules fixed, excluding levels that cause avoidable emergency
   production elsewhere. The envelope permits only the minimum emergency volume
   feasible that hour, with a 0.001 MW numerical allowance and an inward
   schedule margin up to 0.0001 MW. Final physics tolerances are unchanged.
   An offline linear programme penalizes spill at ten times
   the per-MWh absolute deviation from the retained seasonal pattern. Its target is scaled
   by the new water budget, not observed generation. It is **not an annual economic optimum**.
   The resulting fixed schedule then enters the same fast hourly clearing.

NVE revised its HBV history in June 2026. This is a retrospective release, not a
forecast available to operators in 2025. Gross reservoir stock and net usable
inflow are assumed to share an electrical-equivalent basis; catchment routing,
losses, cascade interactions and price-area water allocation remain unresolved.
NVE capacity is reservoir energy; original turbine MW remains unchanged. Observed
Elhub/Ember generation and ENTSO-E prices never enter the schedule or bids.

### Verification and runtime

All **8,760 clearings terminate optimal**. Separate saved-witness replay rebuilds
source coefficients and checks hourly water balance, capacity/turbine bounds,
spill, prescribed closing stocks, area/island balances, passive limits, link bounds
and objectives. Maximum water residual is **{a['water_maximum_residual_mwh']:.3g} MWh**;
network residual is **{a['physics']['maximum_residual_mw']:.3g} MW**.
Native PyPSA independently checks 48 chronological water hours and three physical
market hours. Native objective differences below are formulation checks, not
price-error percentages.

| UTC hour | Objective difference EUR |
| --- | ---: |
{native}

The hourly clearing loop takes **{s['loop_with_live_replay_seconds']:.2f}s**.
One-time source/schedule preparation takes **{s['offline_schedule_and_bounds_seconds']:.2f}s**,
including {s['delivery_bounds_seconds']:.2f}s for network envelopes.
The producer takes **{s['end_to_end_seconds']:.2f}s** end to end; independent audit
and report generation are additional. Spill is **{s['spill_electrical_twh']:.4f} TWh**.
Norway still has **{s['no_hours_above_1000']}** modeled hours above EUR1,000/MWh.
Europe-wide emergency supply is **{s['physics']['emergency_supply_twh']*1e6:.4f} MWh**
over **{s['physics']['shortage_hours']} hours**, versus 0.02982 TWh over four hours
in the frozen reference. The minimum emergency volume allowed by preparation is
{s['minimum_emergency_envelope_twh']:.5f} TWh; clearing costs can trade off a small
shortage against costly production. Improved Norwegian energy matching does not
establish adequacy or price accuracy elsewhere.
No seconds-scale end-to-end claim is made for regenerating this schedule.

### Observed-price comparison

All {len(rows)} eligible areas with observations use the same independently replayed
ENTSO-E A44 data; four mapped areas with no price observations remain explicitly
missing in the downloadable audit.
No price fitting, held-out accuracy claim or exclusion of difficult hours. The
country-price proxy is repeated across NO1–NO5; finer geography remains necessary.

| Price area | Frozen MAE EUR/MWh | Updated MAE EUR/MWh | Updated bias EUR/MWh |
| --- | ---: | ---: | ---: |
{errors}

### Conclusion and reproduction

{price_outcome}

The historical normalization and energy-basis treatment can materially distort
Norwegian hydro. This update addresses those inputs using independent hydrology
and observed stock boundaries. Remaining energy/price discrepancies need zonal
asset mapping, metering/demand-scope reconciliation and a defensible GSK; do not
remove them by fitting generation or prices. Fixed schedules still cannot respond
to hydro investments. Paired-investment and browser-integration gates remain open.

Use the pinned interpreter for `tools/update_norway_hydro_2025.py --out <fresh-root>`,
then `tools/audit_nve_hydro_model_2025.py <fresh-root>` and
`tools/report_nve_hydro_update_2025.py <fresh-root>`. Collect the public NVE table
with `tools/collect_nve_hydrology.ts`; raw source bytes and witnesses stay ignored.

[Source hashes, numerical checks and all price metrics](/research/fixed-reservoir-screening-2025/nve-water-update.json)

## Frozen reference diagnostics

The following figures and results describe the preserved **pre-update input reference**.
They are retained for the controlled comparison above, not the updated water model.

'''
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md';text=path.read_text()
    if '## Frozen reference diagnostics' in text:text=text.split('## Frozen reference diagnostics',1)[1].split('## Summary and conclusion',1)[1];text='## Summary and conclusion'+text
    else:text=text.split('\n',1)[1].lstrip()
    path.write_text('# European hourly dispatch — selected model and error diagnosis\n\n'+updated+text)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);publish(parser.parse_args().folder)
