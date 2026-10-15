"""Update the retained article; full diagnostic arrays and figures stay ignored."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from nve_hydro_diagnostics import ROOT, digest


def report(folder):
    s = json.loads((folder / 'summary.json').read_text())
    audit = json.loads((folder / 'audit.json').read_text())
    assert audit['summary_sha256'] == digest(folder / 'summary.json')
    assert audit['auditor_sha256'] == digest(ROOT / 'tools/audit_residual_response_2025.py')
    assert digest(folder / 'fleet.npz') == s['witness_sha256']
    rows = s['zones']; inventory = s['inventory']
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.3), layout='constrained')
    for ax, z in zip(axes, ['DE-LU', 'FR', 'NO5']):
        row = next(r for r in rows if r['zone'] == z)
        bands = [b for b in row['bands'] if b['hours']]
        x = [b['residual_mean_mw'] / 1000 for b in bands]
        for key, label, color in [('observed_mean', 'Observed', '#2563eb'), ('physical_mean', 'Dispatch', '#ea580c'), ('reference_mean', 'Statistical reference', '#16a34a')]:
            ax.plot(x, [b[key] for b in bands], 'o-', label=label, color=color)
        ax.set_title(z); ax.set_xlabel('Mean residual demand (GW)')
        ax.set_ylabel('Mean price (EUR/MWh)'); ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('July–December 2025: response in January–June-defined residual-demand bands\nDescriptive conditional means; not causal supply curves')
    for suffix in ['png', 'svg']:
        fig.savefig(folder / ('residual-response.' + suffix), dpi=140)
    plt.close(fig)
    carriers = sorted(set(r['carrier'] for r in inventory))
    # Installed MW is the prepared p_nom anchor, not annual-average in-service capacity.
    fleet_table = []
    for c in carriers:
        group = [r for r in inventory if r['carrier'] == c]
        bids = [r for r in group if r['bid_min'] is not None]
        eff = sorted(set(v for r in group for v in r['unique_efficiencies']))
        bid_range = f"{min(r['bid_min'] for r in bids):.2f}–{max(r['bid_max'] for r in bids):.2f}" if bids else 'No available MW'
        fleet_table.append(f"| {c} | {sum(r['installed_mw'] for r in group)/1000:.2f} | {len(group)} | {max(r['unique_annual_bid_profiles'] for r in group)} | {bid_range} | {min(eff):.3f}–{max(eff):.3f} |")
    full = []
    contrast = []
    for r in rows:
        low, high = r['bands'][0], r['bands'][-1]
        if low['hours'] and high['hours']:
            do = high['observed_mean'] - low['observed_mean']
            dm = high['physical_mean'] - low['physical_mean']
            contrast.append((r['zone'], do, dm))
            full.append(f"| {r['zone']} | {low['hours']} / {high['hours']} | {low['physical_bias']:.2f} | {high['physical_bias']:.2f} | {do:.2f} | {dm:.2f} |")
        else:
            full.append(f"| {r['zone']} | {low['hours']} / {high['hours']} | Unknown if empty | Unknown if empty | Unknown | Unknown |")
    worst = []
    for b in s['largest_band_biases'][:10]:
        av = b['available_mean_mw']; thermal = sum(av.get(c, 0.) for c in ['CCGT', 'OCGT', 'coal', 'lignite', 'oil'])
        worst.append(f"| {b['zone']} / {b['band']} | {b['hours']} | {b['observed_mean']:.2f} | {b['physical_mean']:.2f} | {b['physical_bias']:.2f} | {av.get('nuclear',0)/1000:.2f} | {thermal/1000:.2f} | {b['tier_local_surplus_mean_mw'][2]/1000:.2f} |")
    nuclear = [r for r in inventory if r['carrier'] == 'nuclear']
    flat_nuclear = [r for r in nuclear if r['availability_constant']]
    wrong_direction = [z for z, do, dm in contrast if do > 0 and dm < 0]
    gas = [r for r in inventory if r['carrier'] in ['CCGT', 'OCGT']]
    weaker = sum(dm < do for z, do, dm in contrast)
    avg_observed = sum(do for z, do, dm in contrast) / len(contrast)
    avg_dispatch = sum(dm for z, do, dm in contrast) / len(contrast)
    low_bias = sum(r['bands'][0]['physical_bias'] for r in rows) / len(rows)
    high_bias = sum(r['bands'][-1]['physical_bias'] for r in rows) / len(rows)
    de_gas = next(r for r in inventory if r['zone'] == 'DE-LU' and r['carrier'] == 'CCGT')
    fr_nuclear = next(r for r in nuclear if r['zone'] == 'FR')
    text = f'''## Residual-demand response and fleet-stack diagnosis — 15 October 2026

**What this adds:** compare observed and simulated prices at comparable residual
demand, then inspect the unchanged fleet's available quantities and bid structure.
Hydro remains fixed. No new clearing solve, calibrated dispatch bids, candidate,
browser change or empirical acceptance is introduced.

**Main finding: the price response is too weak, not simply too low everywhere.**
Equal-zone mean dispatch bias is EUR{low_bias:.2f}/MWh in the lowest residual band
and EUR{high_bias:.2f}/MWh in the highest. Observed high-minus-low prices average
EUR{avg_observed:.2f}/MWh, versus EUR{avg_dispatch:.2f}/MWh for dispatch; the dispatch
contrast is smaller in {weaker}/{len(contrast)} areas. Each area uses its own bands
and hour counts. These are conditional contrasts, not causal demand derivatives.

### Comparable response bands

For each zone, January–June residual demand defines four quintile boundaries.
Evaluate all five bands on July–December only, using identical known hours for
observed A44 prices, annual-v7 dispatch and the separate statistical reference.
Residual demand is prepared demand minus **available** wind and solar, not actual
renewable generation. All {len(rows)} eligible price areas retain 4416 evaluation
hours; ties and empty bands remain explicit. Training quantiles do not guarantee
equally sized evaluation bands. Negative prices/residuals are preserved.

The local PNG/SVG `residual-response` figure shows DE-LU, FR and NO5; full area
coverage is in the table below. These are conditional means, **not inferred
physical supply curves**: seasonal fuel conditions, outages, hydro and imports
can differ between bands. Already inspected 2025 remains retrospective evidence.

Observed mean prices rise from the lowest to highest band in
{sum(do > 0 for z,do,dm in contrast)}/{len(contrast)} areas with both bands populated.
The dispatch response moves in the opposite direction despite that observed rise
in {len(wrong_direction)} areas ({', '.join(wrong_direction) or 'none'}).
Differences in level and response shape must be investigated separately; a
zone-wide price offset alone cannot correct a wrong direction or slope.

Bias is dispatch minus observed. High-minus-low contrasts describe band means,
not derivatives or causal effects of adding capacity. All prices are EUR/MWh.

| Area | Low / high band hours | Low-band bias | High-band bias | Observed high−low | Dispatch high−low |
| --- | ---: | ---: | ---: | ---: | ---: |
''' + '\n'.join(full) + f'''

### Supply quantities and bid dispersion

Rebuild the frozen source fleet and aggregate original generator columns by area
and carrier, retaining original p_max_pu × p_nom. Emergency supply is excluded.
Reservoir injections stay separate, never converted to flexible available supply.
The prepared p_nom anchor below is **not annual-average 2025 in-service capacity**;
renewable commissioning trajectories remain encoded in the inherited profiles.

Bid range covers the full year and positive available MW. “Profiles” is the maximum
number of distinct annual bid-price sequences within one area/carrier, not the
number of real plants or operators. Efficiency is the prepared conversion factor.
Counts compare exact stored sequences and can distinguish negligible floating-point
differences; interpret them together with actual bid/efficiency ranges.
Zero-capacity source placeholders remain explicit; their profile counts do not
represent active supply and their unavailable bid ranges are not filled with zero.

| Carrier | Prepared p_nom GW | Areas | Max profiles / area | Bid range EUR/MWh | Efficiency range |
| --- | ---: | ---: | ---: | ---: | ---: |
''' + '\n'.join(fleet_table) + f'''

Nuclear availability is constant through the year in {len(flat_nuclear)}/{len(nuclear)}
modeled nuclear areas ({', '.join(r['zone'] for r in flat_nuclear)}). Its inherited
availability is a declared 2024 proxy, not an audited 2025 outage calendar.
Gas has one annual bid profile per area/technology in
{sum(r['unique_annual_bid_profiles']==1 for r in gas)}/{len(gas)} nonempty area/carrier
groups. These are structural simplifications, not proof of missing physical MW.
In France, nuclear available MW stays at {fr_nuclear['hourly_available_min_mw']/1000:.2f} GW,
against a prepared nameplate anchor of {fr_nuclear['installed_mw']/1000:.2f} GW, every hour.
In contrast, German CCGT already has {de_gas['unique_annual_bid_profiles']} stored
profiles and efficiencies {min(de_gas['unique_efficiencies']):.3f}–{max(de_gas['unique_efficiencies']):.3f}:
the present gas stack is not uniformly one bid per technology across Europe.
All {len(gas)} gas area/carrier groups nevertheless have constant available MW
through the year; dated outages/deratings are a separate missing input dimension.
All inventoried generator offers are nonnegative. Negative Norwegian dispatch
prices therefore do not come from a negative gas or renewable bid: the fixed
injections and coupled physical/GSK formulation permit such marginal prices.
The response bands alone cannot attribute the effect to one constraint or prove
that those model constraints represent actual commercial price formation.

Thermal offers inherit monthly World Bank gas/oil and ECB FX inputs, a fixed
EUR80/t carbon assumption and prepared technology costs/efficiencies. Nuclear and
other nonthermal offers retain their source costs. Low-cost renewables remain
weather-limited. Available quantities, operational bids and observed generation
are different objects; generation is not substituted for availability.

### Where to inspect first

The ten largest absolute band-mean price biases below are selected **after**
evaluation, requiring at least 100 hours. They prioritize diagnosis, not validation.
Available nuclear/thermal columns are mean local MW in those hours, not dispatch.
The final column is local generator availability bidding ≤EUR60/MWh plus fixed
reservoir output minus demand. It excludes emergency but ignores imports,
commitment, reserves and network deliverability: positive values are local supply
envelopes, not proof of feasible surplus or erroneous market prices.

| Area / band | Hours | Observed price | Dispatch price | Bias | Nuclear GW | Thermal GW | Local ≤EUR60 envelope−demand GW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
''' + '\n'.join(worst) + f'''

The full witness includes envelopes at EUR0/30/60/100/200, all carrier availability
and per-area bid/efficiency inventory. Network coupling may make a local price
differ from a local offer; unchanged physical/GSK and transport controls remain
separate evidence, not additive causal shares of price error.

### Implications for the next model change

1. **Correct supply timing and scope before fitting bids.** Prioritize dated nuclear
   outages and existing ES/PT wind/demand flags. Constant availability and inherited
   fleet/weather proxies need source verification; do not scale to observed prices
   or replace renewable availability with generated energy.
2. **Test transparent resource-level bid dispersion.** Audit whether technology-wide
   efficiencies/cost profiles collapse genuinely different units into a few steps.
   Use sourced efficiency, variable cost and outage information, with unchanged fuel
   inputs and fixed hydro as controls. More bid steps do not automatically improve
   empirical accuracy; evaluate all areas and adverse outcomes.
   Existing German gas dispersion means a blanket “add more steps” change is not
   supported by this inventory. Prioritize source-backed availability timing first.
3. **Keep network effects explicit.** Wrong local responses can reflect neighboring
   markets or physical/GSK constraints as well as local supply. Neither this
   association nor the statistical reference authorizes replacing dispatch with a
   fitted regional price curve or double-counting imports.
   The Norwegian reversed conditional response remains a network/fixed-injection
   investigation, not evidence that hydro needs a higher bid or more installed MW.

### Provenance and verification

Fresh ignored root: `data/bidding-zone-network-2025/response-diagnostic-v1/`.
Producer `tools/diagnose_residual_response_2025.py` seals source/witness and code
hashes before reading prices. Independent `tools/audit_residual_response_2025.py`
rebuilds original columns, MW tiers, demand/fixed hydro, chronological residual
identities, efficiency/profile inventory, training quantiles, common-hour means
and diagnostic ranking. All {audit['zones']} areas / {audit['inventory_rows']} fleet
rows replay; maximum MW aggregation difference {audit['maximum_source_sum_error_mw']:.3g}.
Three fixtures cover training-only boundaries, tied/empty bands, training exclusion,
missing prices and negative-price retention. Preparation {s['preparation_seconds']:.2f}s;
complete source/price producer {s['end_to_end_seconds']:.2f}s; independent replay
{audit['elapsed_seconds']:.2f}s. These times are diagnostics, not clearing-loop times.
Figures and arrays remain local/ignored. Report updated locally; no CI/Pages or
public-URL publication claim follows.

'''
    path = ROOT / 'docs/european-physical-synthetic-clearing-2025.md'
    content = path.read_text()
    heading = '## Residual-demand response and fleet-stack diagnosis — 15 October 2026\n'
    # Insert before the preceding dated diagnostic, preserving older sections.
    if heading in content:
        a = content.index(heading); b = content.index('\n## ', a + len(heading))
        content = content[:a] + text + content[b+1:]
    else:
        candidates = [line for line in content.splitlines() if line.startswith('## ') and '14 October 2026' in line]
        assert candidates, 'Missing retained report insertion point'
        position = content.index(candidates[0])
        content = content[:position] + text + content[position:]
    path.write_text(content)
    (folder / 'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'), audit_sha256=digest(folder/'audit.json'), producer_sha256=digest(__file__), figures={suffix:digest(folder/('residual-response.'+suffix)) for suffix in ['png','svg']}), indent=2)+'\n')
    print('Updated retained article; figures remain local', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('folder', type=Path)
    report(p.parse_args().folder)
