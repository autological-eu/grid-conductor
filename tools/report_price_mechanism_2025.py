"""Explain verified LP price mechanisms in the retained report; local plots only."""
import argparse,collections,json,statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nve_hydro_diagnostics import ROOT,digest

def buckets(row):
    c=row['local_interior_offer_hours'];mixed=sum(v for k,v in c.items() if k.startswith(('mixed:','tied:')))
    result={'Gas':c.get('gas',0),'Nuclear':c.get('nuclear',0),'Coal/lignite':c.get('coal_lignite',0),
        'Mixed/tied':mixed,'No local interior':c.get('no_local_interior_offer',0)}
    result['Other local']=8760-sum(result.values());return result

def report(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'audit.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_price_mechanism_2025.py')
    for name,sha in a['auditor_dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert digest(folder/'analysis.npz')==a['analysis_witness_sha256']
    rows=a['zones'];priced=[r for r in rows if 'observed_metrics' in r];counts=collections.Counter()
    for r in priced:counts.update(buckets(r))
    denominator=len(priced)*8760
    shares={k:100*v/denominator for k,v in counts.items()}
    gas_r=statistics.mean(r['observed_price_gas_input_r'] for r in priced)
    oil_r=statistics.mean(r['observed_price_oil_input_r'] for r in priced)
    fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    axes[0].barh(list(shares),list(shares.values()),color=['#2563eb','#0284c7','#475569','#16a34a','#ea580c','#a855f7'])
    axes[0].invert_yaxis();axes[0].set_xlabel('Share of 41 observed-zone hours (%)');axes[0].set_title('Local price-matched interior offer evidence')
    with np.load(folder/'analysis.npz') as v,np.load(folder/'annual.npz') as annual:
        j=s['zones'].index('NO5');months=(np.datetime64('2025-01-01')+np.arange(8760).astype('timedelta64[h]')).astype('datetime64[M]')
        obs=np.array(json.loads((ROOT/'data/price-trace/dispatch-validation-2025-v2/NO5.json').read_text()),float)
        series={'Island-balance term':v['island_term'][:,j],'Passive constraint term':v['passive_term'][:,j],
            'Model price':annual['row_duals'][:,j],'Observed NO5 price':obs}
        for label,x in series.items():
            values=[float(np.mean(x[(months==np.datetime64(f'2025-{m:02d}'))&np.isfinite(x)])) for m in range(1,13)]
            axes[1].plot(range(1,13),values,label=label,marker='o',ms=3)
        axes[1].axhline(0,color='black',lw=.7);axes[1].set_xlabel('UTC month, 2025');axes[1].set_ylabel('EUR/MWh');axes[1].set_title('NO5: witness-specific price decomposition');axes[1].legend(fontsize=8)
    fig.suptitle('Price mechanism diagnostic — unchanged baseline, not real order-book attribution')
    for ext in ['png','svg']:fig.savefig(folder/('price-mechanisms.'+ext),dpi=160)
    plt.close(fig)
    text=f'''## Hourly marginal-bid and constraint investigation — 14 October 2026

**What was investigated:** which local offers are consistent with marginality,
how model constraints enter zonal prices, and how observed electricity prices
associate with the retained monthly gas/oil inputs. This reruns the **unchanged**
annual-v7 coefficients to save primal and dual witnesses; it is not a new candidate.
All 8760 hours solve, with original demand, availability, fixed hydro, network,
GSK and fuel bids. All 264 predeclared calendar demand probes are feasible.

**Main result:** monthly gas/oil associations with observed prices are modest
(mean zonal r {gas_r:.3f}/{oil_r:.3f}, versus the residual-demand audit's 0.644).
This does not make fuel bids irrelevant, but fuel prices alone do not explain
the hourly price signal. In the Nordic zones, local-interior offer evidence is
mostly absent; reservoir hydro cannot bid in this fixed-injection formulation.
Model island coupling and passive constraints therefore need investigation
alongside hydro water value, rather than an arbitrary fuel-price uplift.

### Gas, oil and the remaining supply stack

An interior aggregate offer has both positive dispatch and remaining headroom
greater than 0.001 MW, and its bid matches the local price within 1e-5 EUR/MWh.
This is local marginal-offer evidence in this LP, not identification of a unique
real market generator. Equal-cost wind/solar/run-of-river offers are merged;
mixed and tied identities remain ambiguous. A zone can have an import- or
constraint-dependent price with **no local interior offer**. These categories
partition all 41 observed-zone × 8760 hours, with equal area weighting.
Carrier sets retain full-year aggregate membership, including constituents that
may be unavailable in a particular hour; this conservative classification does
not infer an hourly dispatch split. "No local interior" is witness-specific,
not evidence that the real market had no marginal generator.

| Local offer evidence | Share of observed-zone hours |
| --- | ---: |
'''
    for k,v in shares.items():text+=f'| {k} | {v:.2f}% |\n'
    text+=f'''
Monthly gas-input/observed-price correlation has mean zonal **r = {gas_r:.3f}**;
the analogous oil association is **{oil_r:.3f}**. These use the source-verified
World Bank/ECB thermal-input series, not a new daily fuel dataset. Monthly inputs
cannot explain intraday variation by themselves, and seasonal/common drivers can
produce correlation without causal price setting. The assumed EUR80/t carbon
price is constant, so its correlation is undefined, not zero. Observed electricity
prices never enter bid construction. The earlier +/-10% gas diagnostic showed
price influence; oil perturbations did not materially affect this baseline.
Fuel-price correlation and residual-demand correlation measure different relationships.

### How network shadows enter the recorded price

Free zonal net-injection stationarity gives:

**Zonal price = island-balance contribution + passive-network contribution.**

Each contribution is the relevant row shadow prices multiplied by that area's
injection column. This is an exact algebraic identity for the saved dual witness.
Island contributions include cross-island HVDC coupling, losses and cable scarcity;
they are not a single unconstrained European energy price. Passive contributions
reflect the model's PTDF, GSK and line limits, not verified JAO commercial constraints,
physical congestion rent or an independent share of market price error. Degeneracy
can change the decomposition without changing costs; do not treat it as unique
causal attribution. Nonzero shadow prices are distinct from merely binding limits.

Passive rows have nonzero shadow prices in **{a['hours_any_passive_shadow']} of 8760 hours**
somewhere in the network. The table keeps all 48 clearing areas, including areas
without an observed-price target. "Passive >1" counts a zonal contribution whose
absolute value exceeds EUR1/MWh. Shares refer to local interior offers, not all
upstream price influence. All means retain signed contributions and negative prices.

| Area | Local gas % | Local nuclear % | No local interior % | Mean island term | Mean passive term | Passive >1 hours | Negative-price hours |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for r in rows:
        b=buckets(r);text+=f"| {r['zone']} | {100*b['Gas']/8760:.1f} | {100*b['Nuclear']/8760:.1f} | {100*b['No local interior']/8760:.1f} | {r['mean_island_balance_term_eur_mwh']:.2f} | {r['mean_passive_constraint_term_eur_mwh']:.2f} | {r['passive_term_above_1_eur_hours']} | {r['material_negative_price_hours']} |\n"
    text+='''
Contribution units are EUR/MWh. Passive adjustments may raise or lower a zone's
price; a negative contribution is not negative congestion rent. Exact offer
carrier sets, every area's full category counts, top passive-row/link-bound
shadow diagnostics and all observed/fuel associations remain in the ignored audit.

### Hydro's structural limitation

Reservoir hydro is **fixed injection**, subtracted from load before clearing.
It has no variable offer or marginal water value in this LP. Changing the cost
of a fixed quantity adds a constant to the objective; it cannot repair prices.
A hydro-bidding correction therefore requires bounded dispatch flexibility with
explicit inflow, efficiency, turbine/stock constraints and common stock boundaries,
not simply a hydro-price multiplier. This audit does not implement or validate
that correction or identify when hydro actually set the observed market price.

### Verification and demand probes

Independent native-component replay verifies the annual saved primal. Dual replay
checks stationarity, bound/row complementary slackness, strong duality and the
price identity; it verifies that recorded prices are legitimate LP sensitivities,
not that the market model is empirically correct. Interior offer columns are
independently checked to contain only their zonal balance, and interior bid/price
agreement is tested. All 41 eligible observed prices are rehashed/XML-reparsed.

| Check | Maximum difference |
| --- | ---: |
'''
    checks={'Baseline price reproduction EUR/MWh':a['baseline_reproduction']['maximum_price_difference_eur_mwh'],
        'Baseline objective reproduction EUR':a['baseline_reproduction']['maximum_objective_difference_eur'],
        'Native-component residual MW':a['network_maximum_residual_mw'],
        'Dual stationarity EUR/MWh':a['dual_checks']['stationarity_maximum_eur_mwh'],
        'Strong-duality gap EUR':a['dual_checks']['duality_gap_maximum_eur'],
        'Complementarity EUR':a['dual_checks']['complementarity_maximum_eur'],
        'Price-decomposition EUR/MWh':a['dual_checks']['price_decomposition_maximum_eur_mwh']}
    for k,v in checks.items():text+=f'| {k} | {v:.3g} |\n'
    text+=f'''
Demand probes use each month's fifteenth day at noon UTC for DE-LU, FR, NO1-NO5,
SE1-SE4, with +/-1 MW along the unchanged GSK. They preserve all supply/water
inputs and physical limits. This tests the model's assumed marginal withdrawal
pattern, not independently observed demand locations. The supporting-price slope
must lie between downward/upward objective secants; kinked prices need not equal
both secants. All 264 saved feasible primals and objective differences replay.
Four targeted identity/constraint-sign/mixed-offer/boundary fixtures pass.

Annual clearing/dual capture: **{s['loop_seconds']:.2f}s**; source/grid preparation
**{s['preparation_seconds']:.2f}s**; producer including probes/export
**{s['end_to_end_seconds']:.2f}s**, peak RSS **{s['peak_rss_mib']:.0f} MiB**.
Independent physics/dual/probe/source replay adds **{a['elapsed_seconds']:.2f}s**.
These timings do not change the retained baseline's benchmark receipt.

Reproduce with pinned Python: `tools/run_price_mechanism_2025.py <fresh-root>`,
`tools/audit_price_mechanism_2025.py <root>`, then
`tools/report_price_mechanism_2025.py <root>`. Ignored root:
`data/bidding-zone-network-2025/price-mechanism-v1/`. Primal/dual/probe witnesses,
all-area evidence and PNG/SVG charts remain outside Git. The local plot shows
offer evidence and NO5's monthly decomposition. This report update is local;
no new live-publication or baseline/browser-integration claim follows.

**Next:** interpret the verified Nordic constraint contributions alongside the
residual-demand signal; reconcile commercial GSKs and test bounded hydro flexibility
with preserved water/stock boundaries. Keep wind, demand and nuclear source
corrections separate. Fuel influence is established within this model, but neither
monthly fuel correlation nor constraint shadows identify causal observed-price errors.
No price fitting, arbitrary network relaxation, annual-optimum claim or retired
search restart is authorized by these diagnostic results.

'''
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md';old=path.read_text();marker='## Europe-wide residual-demand audit — 14 October 2026'
    if '## Hourly marginal-bid and constraint investigation — 14 October 2026' in old:raise ValueError('Preserve existing report')
    assert marker in old;path.write_text(old.replace(marker,text+marker,1))
    (folder/'report-receipt.json').write_text(json.dumps(dict(producer_sha256=digest(__file__),audit_sha256=digest(folder/'audit.json'),
        images={ext:digest(folder/('price-mechanisms.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated existing report; local plots retained',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();report(a.folder)
