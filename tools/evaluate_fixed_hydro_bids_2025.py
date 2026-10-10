"""Publish the single selected fixed-hydro model and independently sourced diagnostics."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hybrid_fixed_hydro_2025 import ROOT,HOURS,load,compiled,resource_costs,verified_fuel,FUEL
from simple_resource_bids import cost_assumptions
from hourly_renewable_estimates import digest
OUT=ROOT/'public/research/fixed-reservoir-screening-2025'


def publish(folder,diagnostics):
    s=json.loads((folder/'summary.json').read_text());r=json.loads((folder/'replay.json').read_text());d=json.loads(diagnostics.read_text())
    if set(s['cases'])!={'resource_bids'} or r['summary_sha256']!=digest(folder/'summary.json') or d['annual_summary_sha256']!=digest(folder/'summary.json'):raise ValueError('Detached selected evidence')
    if d['producer_sha256']!=digest(ROOT/'tools/diagnose_fixed_hydro_errors_2025.py'):raise ValueError('Changed diagnostic producer')
    for name,sha in s['provenance']['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Changed selected producer')
    c=s['cases']['resource_bids'];witness=folder/'resource_bids.npz'
    if digest(witness)!=c['witness_sha256']:raise ValueError('Changed primal')
    with np.load(witness,allow_pickle=False) as a:prices=a['prices'].copy()
    n,b,common=load();fuel=verified_fuel(FUEL);m=compiled(n,b,resource_costs(n,b['cost'],fuel,cost_assumptions()[0],'resource_bids'))
    dates=n.snapshots;curves=[];de=s['zones'].index('0:DE')
    observation_root=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    if digest(observation_root/'manifest.json')!=d['observed_manifest_sha256']:raise ValueError('Changed observed manifest')
    meta=json.loads((observation_root/'manifest.json').read_text())['zones']['DE-LU']
    if digest(observation_root/'DE-LU.json')!=meta['hourly_sha256']:raise ValueError('Changed DE observations')
    obs=np.array([np.nan if x is None else x for x in json.load(open(ROOT/'data/price-trace/dispatch-validation-2025-v2/DE-LU.json'))])
    fig,axes=plt.subplots(3,1,figsize=(11,9),layout='constrained')
    for ax,t in zip(axes,HOURS):
        mask=(m['offer_zones']=='0:DE')&~m['emergency_mask'];cost=m['cost'][t,mask];vol=m['availability'][t,mask];order=np.argsort(cost)
        cost=cost[order];vol=vol[order];ax.step(np.r_[0,np.cumsum(vol)]/1000,np.r_[cost[0],cost],where='pre',label='Selected domestic offers')
        ax.axhline(prices[t,de],color='black',ls='--',label='Coupled clearing');ax.axhline(obs[t],color='gray',ls=':',label='Observed DE-LU');ax.axvline(m['load'][t,de]/1000,color='gray',alpha=.4)
        ax.set(title=str(dates[t])+' UTC',xlabel='Cumulative domestic offered GW',ylabel='EUR/MWh');ax.legend(fontsize=8)
        curves.append(dict(utc=str(dates[t]),cost_eur_mwh=cost.tolist(),volume_mw=vol.tolist(),modeled_price_eur_mwh=float(prices[t,de]),observed_price_eur_mwh=float(obs[t])))
    curves_path=OUT/'resource-bids-curves.png';fig.savefig(curves_path,dpi=120);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(11,10),layout='constrained');top=d['ranked_errors'][:12];x=np.arange(len(top))
    axes[0].bar(x-.17,[v['annual']['mae_eur_mwh'] for v in top],width=.34,label='All hours');axes[0].bar(x+.17,[v['non_spike']['mae_eur_mwh'] for v in top],width=.34,label='Excluding modeled >1000 EUR/MWh')
    axes[0].set(xticks=x,xticklabels=[v['zone'] for v in top],ylabel='MAE EUR/MWh',title='Largest observed-price errors; excluded spikes remain in official annual metrics');axes[0].legend(fontsize=8)
    no=d['norway'];p=no['price_interval_probes'];axes[1].plot([v['saved_price'] for v in p],label='Saved Norwegian price');axes[1].plot([v['downward_incremental_cost_eur_mwh'] for v in p],label='One-MW downward demand probe');axes[1].plot([v['price_eur_mwh'] for v in no['hydro_capacity_gsk_probe']],label='Hydro-inclusive injection-weight probe')
    axes[1].set(xlabel='Index of 168 high-price hours, chronological',ylabel='EUR/MWh',title='Diagnostic probes only: water/capacity unchanged');axes[1].legend(fontsize=8)
    areas=d['capacity_and_energy'];x=np.arange(len(areas));axes[2].bar(x-.18,[v['model_total_hydro_bounds_twh'][0] for v in areas],width=.36,label='Model hydro lower allocation bound');axes[2].bar(x+.18,[v['ember_2025_twh']['Hydro'] for v in areas],width=.36,label='Ember observed national hydro')
    axes[2].errorbar(x-.18,[v['model_total_hydro_bounds_twh'][0] for v in areas],yerr=np.array([[0]*len(areas),[max(0.,v['model_total_hydro_bounds_twh'][1]-v['model_total_hydro_bounds_twh'][0]) for v in areas]]),fmt='none',color='black',capsize=3)
    axes[2].set(xticks=x,xticklabels=[v['country'] for v in areas],ylabel='TWh',title='Hydro energy comparison; allocation bounds retain merged-offer ambiguity');axes[2].legend(fontsize=8)
    errors_path=OUT/'resource-bids-errors.png';fig.savefig(errors_path,dpi=120);plt.close(fig)
    provenance=s['provenance'].copy();audit=provenance.pop('capacity_audit');provenance['capacity_audit_canonical_sha256']=__import__('hashlib').sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    public=dict(status=s['status'],hours=8760,cases=s['cases'],provenance=provenance,replay=r,water_residual_mwh=s['water_residual_mwh'],source_summary_sha256=digest(folder/'summary.json'),
        diagnostics=d,fuel_monthly_inputs=fuel['monthly'],raw_fuel_provenance=fuel['provenance'],german_offer_examples=curves,common_preparation_seconds=s['common_preparation_seconds'],elapsed_seconds=s['elapsed_seconds'],peak_rss_mib=s['peak_rss_mib'],
        publication_producer_sha256=digest(__file__),images={p.name:digest(p) for p in [curves_path,errors_path]})
    (OUT/'resource-bids.json').write_text(json.dumps(public,separators=(',',':'),allow_nan=False)+'\n')
    de_error=next(v for v in d['ranked_errors'] if v['zone']=='DE-LU')['annual'];nr=next(v for v in areas if v['country']=='NO')
    lower=np.median([v['downward_incremental_cost_eur_mwh'] for v in no['price_interval_probes']]);gsk_med=np.median([v['price_eur_mwh'] for v in no['hydro_capacity_gsk_probe']]);remaining=sum(v['price_eur_mwh']>1000 for v in no['hydro_capacity_gsk_probe'])
    errors='\n'.join(f"| {v['zone']} | {v['annual']['mae_eur_mwh']:.2f} | {v['non_spike']['mae_eur_mwh']:.2f} | {100*v['above_1000_error_fraction']:.1f}% |" for v in top)
    fleet='\n'.join(f"| {v['country']} | {v['source_hydro_including_ror_gw']:.2f} | {v['irena_hydropower_2025_gw']:.2f} | {v['model_total_hydro_bounds_twh'][0]:.2f}–{v['model_total_hydro_bounds_twh'][1]:.2f} | {v['ember_2025_twh']['Hydro']:.2f} | {v['source_demand_twh']:.2f} | {v['ember_2025_twh']['Demand']:.2f} |" for v in areas)
    native='\n'.join(f"| {v['utc']} | {v['difference_eur']:.8g} |" for v in c['native_checks'])
    (ROOT/'docs/european-physical-synthetic-clearing-2025.md').write_text(f'''# European hourly dispatch — selected model and error diagnosis

## Summary and conclusion

We retain **one model: fixed hourly hydro injections, simple resource bids and
physical-network clearing** over all 8,760 UTC hours of 2025. The legacy and
fuel-only comparison variants have been removed from code, publication and local
checkpoints. Their small bid differences did not justify maintaining three versions.
The paused daily-storage reference remains separate; the browser still uses its
two-zone screen.

The selected model clears the year in **{c['loop_with_live_replay_seconds']:.2f}s**
including updates and live checks, plus {s['common_preparation_seconds']:.2f}s common
preparation. German price MAE is **EUR{de_error['mae_eur_mwh']:.2f}/MWh**.
Norway dominates the errors. Its turbine capacity is relatively close to IRENA,
but modeled hydro energy is low and the assumed grid injection pattern creates
large price sensitivity. **Changing a fixed hydro price cannot fix this model:
hydro output is injected directly, with no price-setting hydro offer.**

## Model and data

- Wind/PV offer original weather-limited volumes at EUR0/MWh. IRENA end-2024/end-2025
  linear commissioning scales fleet availability; observed commissioning is unknown.
- Gas/oil bids use hashed World Bank monthly TTF/Brent and ECB FX, efficiency,
  operational emissions and variable O&M. Coal/lignite use prepared fuel constants.
  Carbon remains an assumed EUR80/t; heating-value and delivered-oil proxies are explicit.
- Nuclear, biomass, waste, geothermal and run-of-river use prepared cost/availability
  proxies. Commitment, ramps and historical outages are unresolved; nuclear profiles
  ending in 2024 are declared proxies. Observed electricity prices do not enter bids.
- Reservoir output comes from the retained, independently replayed chronological
  water schedule. Capacity does not supply extra water. No battery/PHS dispatch is
  included. Weather availability is never replaced with realized generation.
- Forty country/AC-island areas, 256 passive branches and 74 controllable links use
  native bounds/efficiencies and PTDF/GSK constraints. These are N-0 approximations,
  not commercial zones or accepted JAO capacities. Prepared demand is still a proxy.

Identical offers merge exactly; a persistent one-thread HiGHS basis is reused for
hourly updates. There is no forecast or reservoir optimization stage. Full command,
including three native checks, component replay and witness export: {s['elapsed_seconds']:.2f}s;
peak RSS {s['peak_rss_mib']:.0f} MiB. Historical hydro preparation, independent audit
and diagnosis/report generation are additional; loop timing is not end-to-end timing.

## Supply-curve examples

![Selected German offers and coupled prices](/research/fixed-reservoir-screening-2025/resource-bids-curves.png)

Domestic curves are illustrative: their intersection with domestic demand is not
the coupled European solution. Imports, exports and physical constraints determine
clearing. Observed DE-LU prices are comparison data, not inputs.

## Where the errors are largest

![Largest errors, Norwegian price probes and national hydro energy](/research/fixed-reservoir-screening-2025/resource-bids-errors.png)

All 39 eligible A44 observations are rehashed and independently reparsed, preserving
UTC aggregation and missingness. Four unavailable series and unresolved Italian
islands remain excluded. Norway's five observed zones share one model price, as do
other declared country proxies. Full metrics for every eligible zone are in the download.

| Observed zone | Annual MAE EUR/MWh | MAE outside modeled >1000 spikes | Absolute error from spikes |
| --- | ---: | ---: | ---: |
{errors}

Removing spikes here is a **diagnostic only**; official annual errors retain them.
This is untuned descriptive evidence, not held-out empirical acceptance.

## Capacity gap or hydro energy gap?

IRENA country hydropower is compared with reservoir turbines plus run-of-river,
using parent totals once. Prepared fleet and IRENA year-end capacity have different
scopes/dates. [IRENA source capacity and provenance](/research/irena-capacity-2025/summary.json.gz)
and [Ember monthly source](https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv)
are independently hashed. Ember supplies all twelve 2025 months per country. It reports national
hydro generation, including categories that are not perfectly identical to the model.

| Country | Model hydro GW | IRENA end-2025 GW | Model hydro TWh bounds | Ember hydro TWh | Model demand TWh | Ember demand TWh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{fleet}

Zero-cost run-of-river can merge with wind/PV. Its dispatched share is not uniquely
identified, so the table reports rigorous bounds from total merged dispatch and
individual availability; it does not invent a proportional allocation.

Norway has {nr['source_hydro_including_ror_gw']:.2f} GW versus
{nr['irena_hydropower_2025_gw']:.2f} GW in IRENA—a modest capacity difference.
Fixed reservoir output is {nr['fixed_reservoir_output_twh']:.2f} TWh; source reservoir
inflow is {no['source_reservoir_inflow_water_twh']:.2f} TWh of stored water-equivalent
energy, or {no['source_reservoir_inflow_electrical_equivalent_twh']:.2f} TWh after turbine
efficiency. Those reservoir quantities exclude run-of-river. Modeled total hydro
bounds above remain below observed generation. Extra turbine MW alone would not
close an inflow/schedule energy gap; it must be reconciled with stocks and spill.

During the 168 Norwegian price spikes, unused turbine headroom averages
{no['turbine_headroom_mean_on_spikes_mw']/1000:.2f} GW and is never below
{no['turbine_headroom_min_on_spikes_mw']/1000:.2f} GW. This is power headroom, **not
proof that additional water is available**. It argues against turbine scarcity as
the sole cause. Retained model inventories are not observed NVE stocks.

## Fixed-volume and network effects

There are 168 Norwegian hours above EUR1000/MWh, {no['high_price_hours_without_emergency']}
without emergency generation. A one-MW demand increase at these hours costs roughly
EUR10000/MWh, while the median cost saved by a one-MW demand decrease is
EUR{lower:.2f}/MWh. The asymmetric response exposes a tight volume/network boundary:
a dual price can jump despite negligible actual shortage.

The compiler's injection weights use ordinary-generator capacity and **omit reservoir
turbines**. In hydro-dominated Norway this is a material geographic approximation.
We tested the same 168 hours with Norwegian reservoir capacity included in the
injection weights, leaving turbine capacity, water, fixed output, demand, bids and
line ratings unchanged. Median Norwegian probe price is EUR{gsk_med:.2f}/MWh;
only {remaining} of these hours remain above EUR1000/MWh. A sampled native PyPSA
check agrees within EUR{abs(no['hydro_gsk_native_check']['difference_eur']):.8g}.

This isolates sensitivity to injection geometry; **it is not an accepted replacement
GSK, annual improvement claim or relaxation of physical limits**. Those weights still
aggregate a country and do not reproduce actual nodal demand, hydro injections or
commercial NO1–NO5 geography. Lower probe prices alone do not validate them.

**Would bidding-zone resolution help?** Likely, because it separates northern and
southern hydro, loads and interconnectors that a single Norwegian country price
collapses. Zone labels alone are insufficient: fixed hydro must enter at its
physical buses, demand needs a verified spatial allocation, and flexible generator
injections need defensible within-zone distribution. More zones with the same
incorrect weights can retain artificial spikes. Test audited NO1–NO5 mapping and
nodal injection placement together, then repeat native and sensitivity checks.

## Other high-error areas and next improvements

- **Eastern Denmark:** its large spikes partly accompany the Norwegian island-price
  distortion. Reconcile injection geometry and DK1/DK2 commercial boundaries first;
  national fleet totals do not establish DK2 supply.
- **Estonia/Baltics:** inspect fossil technology classification and interconnection
  assumptions. Ember records about 1.983 TWh of Estonian other-fossil generation;
  the prepared fleet has a 0.251 GW oil category priced as Brent fuel and no explicit
  oil-shale strategy. That is a classification/cost concern, not proof of missing
  capacity. Baltic topology/outages and demand need independent reconciliation.
- **Finland/Sweden:** hydro energy and country-versus-zone aggregation remain relevant;
  their fleet/energy comparisons above identify input priorities without price fitting.

Priority: correct nodal/zonal demand and hydro injection representation, then audit
Norwegian water energy against monthly Ember and observed NVE stock changes. Keep
original chronology, efficiency, stocks and spill; do not simply scale fixed output
to observed generation. If hydro offers are introduced, use explicit water-value
bids and available turbine/water volumes with carried stocks. Price tuning alone
cannot change an injection-only schedule. The daily-storage reference remains paused.

## Numerical checks and provenance

All 8760 selected hours terminate optimal. Saved-primal replay independently checks
bounds, area/island balances and passive flows outside the producer matrix. Water
residual {s['water_residual_mwh']:.3g} MWh and network residual
{c['physics']['maximum_residual_mw']:.3g} MW pass 1e-4; closure remains unchanged.
Emergency supply is {c['physics']['emergency_supply_twh']:.7f} TWh in four hours.

| UTC hour | Native PyPSA minus fast objective EUR |
| --- | ---: |
{native}

Native parity verifies the formulation. Empirical thresholds/held-out periods,
paired investments, adaptive storage and supported browser integration remain open.

[Selected results, all-zone errors, capacity/energy sources, price probes and replay](/research/fixed-reservoir-screening-2025/resource-bids.json)

[Retained hydro source metadata](/research/fixed-reservoir-screening-2025/summary.json.gz)
· [water replay](/research/european-reservoir-clearing-2025/replay.json).

Reproduce with tools/hybrid_fixed_hydro_2025.py in a fresh output root, then --audit;
run tools/diagnose_fixed_hydro_errors_2025.py --run ROOT --out ROOT/diagnostics.json,
and tools/evaluate_fixed_hydro_bids_2025.py --run ROOT --diagnostics ROOT/diagnostics.json.
Use pinned Python and verified ignored provider/source/water caches. Raw observations
and annual witnesses stay outside Git. Only this model is maintained for this report.
''')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--diagnostics',type=Path,required=True);a=p.parse_args();publish(a.run,a.diagnostics)
