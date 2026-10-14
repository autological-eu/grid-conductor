"""Update the retained report; plots and full audit remain local, not bulk Git."""
import argparse,json,statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nve_hydro_diagnostics import ROOT,digest

def report(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'replay.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/replay_residual_demand_audit_2025.py')
    assert digest(folder/'hourly.npz')==s['witness_sha256']
    rows=s['zones'];priced=[r for r in rows if r['price_association']]
    cor=statistics.mean(r['price_association']['observed_price_correlation'] for r in priced)
    oldcor=statistics.mean(r['price_association']['model_price_correlation'] for r in priced)
    flags=sorted([(r['zone'],k,v,r['generation_scope']) for r in rows for k,v in r['resources'].items() if v['known_hours']],key=lambda r:-r[2]['excess_generation_twh'])
    demand=[r for r in s['national_demand'] if r['relative_difference'] is not None]
    with np.load(folder/'hourly.npz') as arrays:
        zones=arrays['zones'].tolist();j=zones.index('FR')
        fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained')
        wind=sorted([r for r in rows if r['resources']['wind']['known_hours']],key=lambda r:-r['resources']['wind']['excess_generation_twh'])[:8]
        y=np.arange(len(wind));ax[0].barh(y-.18,[r['resources']['wind']['available_on_known_hours_twh'] for r in wind],.35,label='Modeled available',color='#2563eb')
        ax[0].barh(y+.18,[r['resources']['wind']['generated_on_known_hours_twh'] for r in wind],.35,label='Reported generated',color='#ea580c')
        ax[0].set_yticks(y,[f"{r['zone']} ({r['resources']['wind']['known_hours']} h)" for r in wind]);ax[0].invert_yaxis();ax[0].set_xlabel('TWh on matched reported hours');ax[0].set_title('Wind: priority consistency checks');ax[0].legend(fontsize=8)
        selected=sorted(demand,key=lambda r:-abs(r['relative_difference']))[:12]
        ax[1].barh([r['country'] for r in selected],[100*r['relative_difference'] for r in selected],color='#2563eb');ax[1].invert_yaxis();ax[1].axvline(0,color='black',lw=.8)
        ax[1].set_xlabel('Model / Ember demand − 1 (%)');ax[1].set_title('National demand: unreconciled scope')
        hours=np.arange(8760);ax[2].plot(hours/24,arrays['nuclear'][:,j]/1000,label='Available model envelope',color='#2563eb')
        # Daily means are shown only when all 24 reported hours are present.
        source=arrays['reported_nuclear'][:,j].reshape(365,24);known=np.isfinite(source).all(axis=1)
        daily=np.full(365,np.nan);daily[known]=source[known].mean(axis=1)/1000
        ax[2].plot(np.arange(365),daily,label='Reported generation (complete days)',color='#ea580c',lw=1)
        ax[2].set_xlabel('UTC day of 2025');ax[2].set_ylabel('GW');ax[2].set_title('France: flat nuclear availability');ax[2].legend(fontsize=8)
        fig.suptitle('Residual-demand input audit — diagnostics, not calibrated corrections',fontsize=15)
        for ext in ['png','svg']:fig.savefig(folder/('diagnostic.'+ext),dpi=160)
        plt.close(fig)
    text=f'''## Europe-wide residual-demand audit — 14 October 2026

**Main finding: improve supply/demand inputs, but also diagnose price formation.**
The unchanged baseline's demand-minus-wind/solar signal correlates with observed
prices at an arithmetic mean zonal **r = {cor:.3f}**, versus **{oldcor:.3f}** for its
cleared prices. Residual-demand correlation is higher in 31 of 41 eligible areas.
This is a descriptive association, not a price estimator, improvement in MAE,
held-out validation or proof that one bidding/constraint assumption is responsible.

The audit covers **48 modeled clearing areas × 8760 UTC hours**, including all
41 eligible A44 price areas. No coefficients changed and no additional clearing
was run. The annual-v7 baseline, its zero-emergency/feasibility evidence, and the
browser's older two-zone estimator remain unchanged.

### Definitions and source coverage

Residual VRE demand = prepared model demand − available wind − available solar.
The wider envelope additionally subtracts available nuclear, run-of-river and
biomass plus the fixed reservoir schedule. It is a supply envelope, not actual
dispatch: nuclear/biomass can be curtailed, fixed hydro is conditional, and imports,
network deliverability, reserves and strategic/commitment bids are not accounted
for in this subtraction. Negative residuals are retained, not clipped. Local
thermal-envelope deficits do not establish infeasibility because imports matter.

Availability uses the retained prepared network, original hourly profiles and
the inherited IRENA capacity trajectory; generation never replaces availability.
Low-cost families are declared by technology, not an empirically fitted bid cutoff.
Emergency supply and battery/pumped-storage discharge are excluded. Generator
identity is preserved in this input audit even where clearing aggregates equal-cost
wind/solar offers, so their dispatch identities cannot be inferred from saved offers.

Fresh ENTSO-E A75/A16 raw interval replay verifies **{a['verified_generation_area_months']} area-months**.
Missing months/types/hours remain unknown. Technology comparisons sum only the
named reported categories: B18/B19 wind, B16 solar, B14 nuclear, B11 run-of-river,
B01 biomass. Unreported categories are not certified zero. Complete reported
categories do not certify whole-fleet reporting. Germany's generation excludes
Luxembourg although clearing uses DE-LU; other national/reporting-area boundaries
and source zone allocations remain proxies. A44 prices are rehashed/XML-reparsed.

Ember's [monthly national release](https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv)
provides complete 2025 demand totals for {len(demand)} of 34 modeled countries.
Missing national totals are not annualised. Compare country sums, never national
totals with an individual bidding zone. Demand accounting (net/gross, losses,
embedded/self-consumed generation, industrial coverage) is still unreconciled.
Elhub's independently source-replayed Norwegian metered consumption is a separate
hourly check; it is not automatically total system load.

### Supply consistency: largest flags

The predeclared flag is reported generation exceeding available supply by more
than 1 MW. Excess TWh sums positive hourly differences on known hours; it is
**not** annual missing capacity, recoverable energy, curtailment or causal price
error. Available supply above generation can reflect curtailment; it is not an
error by itself. Different resource classifications can invalidate direct comparisons.

| Area / resource | Known hours | Available TWh | Generated TWh | Positive excess TWh | Flagged hours |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for z,k,r,scope in flags[:18]:text+=f"| {z} / {k} | {r['known_hours']} | {r['available_on_known_hours_twh']:.2f} | {r['generated_on_known_hours_twh']:.2f} | {r['excess_generation_twh']:.2f} | {r['hours_generated_above_available_1mw']} |\n"
    text+='''
Spain's wind has shape correlation 0.880 and Portugal's 0.862; their large volume
shortfalls justify auditing dated capacity and site-weighted conversion/coverage
before a bid uplift. Spain has 37 missing generation hours, which are excluded.
Its solar available energy exceeds reported generation on matched hours, yet
there are hourly above-availability flags: annual totals alone cannot validate
weather timing, geography or technology scope.

Run-of-river flags are especially sensitive to source classification: B11/B12
reservoir routing may differ from PyPSA's ROR/fixed-reservoir split. They do not
justify adding turbines or water. Reconcile combined hydro accounting and regional
routing before interpreting the Austria/Finland/Norway differences as shortages.
France's nuclear available envelope is flat through 2025, while generation varies.
Its total envelope is above reported generation but lacks outage timing. Observed
generation is not a replacement availability series; obtain capacity/outage inputs.

### National demand checks

Absolute differences above 5% flag investigation, not an acceptance threshold or
an instruction to scale loads. Totals below show complete 12-month references.

| Country | Prepared model TWh | Ember demand TWh | Difference % |
| --- | ---: | ---: | ---: |
'''
    for r in sorted(demand,key=lambda r:-abs(r['relative_difference'])):text+=f"| {r['country']} | {r['model_twh']:.2f} | {r['ember_twh']:.2f} | {100*r['relative_difference']:+.1f} |\n"
    text+='''
Sixteen of 33 complete national comparisons exceed 5%. Countries with near-equal
annual totals still need hourly and zonal validation. No certified independent
whole-Europe hourly zonal demand observation was reconstructed here. Norwegian
Elhub comparisons preserve their metered-consumption scope:

| Zone | Known hours | Model TWh | Metered TWh | Hourly shape r |
| --- | ---: | ---: | ---: | ---: |
'''
    for r in a['norway_metered_demand']:text+=f"| {r['zone']} | {r['known_hours']} | {r['model_on_known_hours_twh']:.2f} | {r['elhub_metered_twh']:.2f} | {r['shape_correlation']:.3f} |\n"
    text+='''
### All-area hourly residual and price associations

Demand/wind/solar totals below are model-input TWh over 8760 hours. VRE-negative
counts retain surplus envelope hours; they are not measured curtailment. Both r
columns compare with the same observed price series. A dash means unavailable
price comparison, not zero. Raw MW residuals are not prices, and their correlations
cannot be compared as MAE or interpreted as a calibrated substitute model.

| Area | Demand TWh | Available wind TWh | Available solar TWh | VRE-negative hours | Residual/price r | Cleared/price r |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for r in rows:
        v=r['annual_twh'];p=r['price_association'];rc=f"{p['observed_price_correlation']:.3f}" if p else '—';pc=f"{p['model_price_correlation']:.3f}" if p else '—'
        text+=f"| {r['zone']} | {v['demand']:.2f} | {v['wind']:.2f} | {v['solar']:.2f} | {r['negative_vre_residual_hours']} | {rc} | {pc} |\n"
    text+=f'''
NO5 residual-demand correlation is +0.618 while cleared-price correlation is
−0.133; NO3 is +0.582 versus +0.016 and SE4 +0.631 versus +0.263. Existing
demand/weather contain a meaningful market-related signal that the current
clearing output does not reproduce. This supports controlled hydro opportunity-
cost/fixed-injection and GSK/commercial-constraint diagnostics alongside input
corrections. It does not identify their causal contribution or certify a bidding rule.

### Verification, reproducibility and next action

Independent source-input replay reconstructs every zonal demand and technology
availability sum from the unchanged network, fixed hydro, reported quantities,
missingness and both residual identities. Maximum aggregation difference is
**{a['maximum_input_sum_difference_mw']:.3g} MW**. National monthly demand sums and
references replay; Norwegian source responses are rehashed against their retained
raw replay. Four targeted coverage/threshold tests pass. This validates the input
audit, not a new market solution or price accuracy. Producer/replay/code/source
hashes and failed/unavailable source coverage remain local.

Producer/source replay takes **{s['elapsed_seconds']:.2f}s**, peak RSS
**{s['peak_rss_mib']:.0f} MiB**; independent reconstruction adds **{a['elapsed_seconds']:.2f}s**.
These are audit timings, not annual clearing-loop timings. Reproduce with pinned
Python: `tools/residual_demand_audit_2025.py <fresh-root>`, then
`tools/replay_residual_demand_audit_2025.py <root>` and
`tools/report_residual_demand_audit_2025.py <root>`. Current ignored root is
`data/residual-demand-audit-2025/v1/`. Its PNG/SVG diagnostic shows matched wind
quantities, national demand differences and French nuclear timing; full hourly
matrices, all resource coverage/flags and raw replay manifests stay outside Git.
This report update is local until CI/Pages and public URLs are verified.

**Next priorities:**

1. Reconcile Spain/Portugal wind capacity and site-weather conversion with dated
   external sources; preserve IRENA normalization and validate against generation
   without fitting availability to it. Extend the same audit to Finland/Austria
   and relevant Italian zones, retaining scope limits.
2. Resolve demand definitions for the largest discrepancies, then obtain/replay
   actual hourly zonal load. Do not silently scale demand to Ember.
3. Replace flat/proxy nuclear availability with dated fleet/outage evidence.
4. Diagnose Nordic binding constraints, fixed hydro marginal water value and GSK
   price responses on predeclared hours/common inputs. The residual signal is
   stronger than current cleared prices, so data corrections alone are insufficient
   evidence for a fix. Keep chronology/water, adverse outcomes and independent
   physics gates; do not restart retired adaptive-water searches.

Predeclare validation splits/acceptance thresholds before tuning. No blanket
fuel uplift, renewable-generation substitution, baseline promotion or browser
replacement follows from this audit. Automatic hourly reviews remain disabled.

'''
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md';old=path.read_text();marker='## Dated Norwegian wind-geography test — 13 October 2026'
    if '## Europe-wide residual-demand audit — 14 October 2026' in old:raise ValueError('Preserve existing report; do not append twice')
    assert marker in old;path.write_text(old.replace(marker,text+marker,1))
    (folder/'report-receipt.json').write_text(json.dumps(dict(producer_sha256=digest(__file__),summary_sha256=digest(folder/'summary.json'),
        replay_sha256=digest(folder/'replay.json'),images={ext:digest(folder/('diagnostic.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated retained report; plots/full audit remain local',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();report(a.folder)
