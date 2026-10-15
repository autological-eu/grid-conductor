"""Append verified quantity comparisons to the existing maintained article."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from generation_mix_2025 import ROOT,EMBER,digest


def show(value,digits=2):
    return 'Unknown' if value is None else f'{value:.{digits}f}'


def report(folder):
    presentation=folder/'presentation-v2'
    presentation.mkdir(parents=True,exist_ok=False)
    audit_path=folder/'verification-v2/audit.json'
    s=json.loads((folder/'summary.json').read_text());a=json.loads(audit_path.read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and a['auditor_sha256']==digest(ROOT/'tools/audit_dispatch_mix_2025.py')
    assert digest(folder/'quantities.npz')==s['witness_sha256']
    core=['Wind','Solar','Hydro','Nuclear','Gas','Coal'];countries=s['countries']
    bank={(r['country'],r['technology']):r for r in s['annual']}
    with np.load(folder/'quantities.npz') as q:
        available=q['available'];families=q['families'].tolist()
        available_twh={(c,f):float(available[:,j,[families.index(v) for v in EMBER[f]]].sum()/1e6) for j,c in enumerate(countries) for f in core if f!='Hydro'}
    matrix=np.array([[bank[c,f]['difference_twh'] if bank[c,f]['difference_twh'] is not None else np.nan for f in core] for c in countries])
    fig=plt.figure(figsize=(15,11),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[1.1,1.])
    ax=fig.add_subplot(gs[:,0]);bound=float(np.nanmax(abs(matrix)))
    cmap=plt.get_cmap('coolwarm').copy();cmap.set_bad('#dddddd')
    im=ax.imshow(np.ma.masked_invalid(matrix),aspect='auto',vmin=-bound,vmax=bound,cmap=cmap)
    ax.set_xticks(range(len(core)),core,rotation=35,ha='right');ax.set_yticks(range(len(countries)),countries,fontsize=8)
    ax.set_title('Annual model − Ember (TWh)\nIllustrative allocation; grey = incomplete reference')
    fig.colorbar(im,ax=ax,label='TWh difference',shrink=.7)
    for ax,c,f in [(fig.add_subplot(gs[0,1]),'FR','Nuclear'),(fig.add_subplot(gs[1,1]),'ES','Wind')]:
        row=bank[c,f];months=row['monthly'];x=np.arange(1,13)
        ax.fill_between(x,[m['lower_twh'] for m in months],[m['upper_twh'] for m in months],alpha=.2,color='#ea580c',label='Within-group allocation range')
        ax.plot(x,[m['model_twh'] for m in months],'o-',color='#ea580c',label='Illustrative model allocation')
        ax.plot(x,[np.nan if m['ember_twh'] is None else m['ember_twh'] for m in months],'o-',color='#2563eb',label='Ember observed')
        ax.set_title(c+' '+f);ax.set_ylabel('Monthly generation (TWh)');ax.set_xticks(x);ax.set_xlabel('2025 month');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('2025 generation quantities — retained dispatch, not available supply\nCountry scope and hydro/storage accounting remain explicit limitations')
    for ext in ['png','svg']:fig.savefig(presentation/('generation-mix.'+ext),dpi=140)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,6),layout='constrained');labels=[];bars=[]
    for c in ['DE','FR','ES','NO']:
        for model in [True,False]:
            row=[bank[c,f]['model_share_pct' if model else 'ember_share_pct'] for f in EMBER]
            labels.append(c+(' model*' if model else ' Ember')+('†' if any(v is None for v in row) else ''))
            bars.append(row)
    values=np.array(bars,float);bottom=np.zeros(len(labels));colors=plt.get_cmap('tab10').colors
    # Omit individual unknown components, then show the unallocated total separately.
    # This is a visual residual of the known total, never zero-filled source data.
    known=np.where(np.isfinite(values),values,0.)
    for k,f in enumerate(EMBER):ax.bar(np.arange(len(labels)),known[:,k],bottom=bottom,label=f,color=colors[k]);bottom+=known[:,k]
    remainder=np.maximum(100-bottom,0.)
    ax.bar(np.arange(len(labels)),remainder,bottom=bottom,color='#cccccc',hatch='//',label='Unallocated total / missing split')
    ax.set_xticks(np.arange(len(labels)),labels,rotation=20,ha='right');ax.set_ylabel('Share of total generation (%)');ax.set_title('Generation shares: absolute TWh differences are reported separately')
    ax.legend(ncol=3,fontsize=8);fig.supxlabel('*Illustrative tie allocation; hydro/waste scope unreconciled.\n† Missing component data remain unknown; known shares are shown with any residual total in grey.',fontsize=9)
    for ext in ['png','svg']:fig.savefig(presentation/('generation-shares.'+ext),dpi=140)
    plt.close(fig)
    total_rows=[];mix_rows=[];timing=[]
    for row in s['country_totals']:
        c=row['country'];e=next(r for r in s['energy'] if r['country']==c)
        dg=None if e['ember_demand_twh'] is None else e['model_demand_twh']-e['ember_demand_twh']
        dx=None if e['ember_net_export_twh'] is None else e['model_implied_net_export_twh']-e['ember_net_export_twh']
        total_rows.append(f"| {c} | {row['model_total_twh']:.2f} [{row['lower_twh']:.2f}, {row['upper_twh']:.2f}] | {show(row['ember_total_twh'])} | {show(row['difference_twh'])} | {show(dg)} | {show(dx)} |")
        mix_rows.append('| '+c+' | '+' | '.join(show(bank[c,f]['difference_twh']) for f in core)+' |')
    full_hourly=[r for r in s['hourly'] if r['technology']!='reported_primary_total' and r['year']['known_hours']==8760]
    known_hourly=[r for r in s['hourly'] if r['technology']!='reported_primary_total' and r['year']['known_hours']>0]
    ranked=sorted([r for r in s['annual'] if r['technology'] in ['Wind','Solar','Nuclear','Gas','Coal'] and r['outside_range_twh'] is not None],key=lambda r:-r['outside_range_twh'])
    worst=[]
    for r in ranked[:12]:
        worst.append(f"| {r['country']} | {r['technology']} | {available_twh[r['country'],r['technology']]:.2f} | {r['model_twh']:.2f} [{r['lower_twh']:.2f}, {r['upper_twh']:.2f}] | {r['ember_twh']:.2f} | {r['difference_twh']:.2f} | {r['outside_range_twh']:.2f} |")
    for c,f in [('FR','nuclear'),('DE','gas'),('ES','onshore_wind'),('PT','onshore_wind'),('SE','reservoir')]:
        r=next(r for r in s['hourly'] if r['country']==c and r['technology']==f)['year']
        timing.append(f"| {c} | {f} | {r['known_hours']} | {show(r.get('model_twh'))} | {show(r.get('observed_twh'))} | {show(r.get('mae_mw'))} | {show(r.get('correlation'),3)} |")
    incomplete=[r for r in s['observation_coverage'] if r['missing_areas'] or not r['expected_areas']]
    shortages='; '.join(r['country']+': '+(', '.join(r['missing_areas']) if r['missing_areas'] else 'no matching national domain') for r in incomplete)
    complete_ref=sum(r['ember_total_twh'] is not None for r in s['country_totals'])
    biggest=ranked[0]
    totals={r['country']:r for r in s['country_totals']};energy={r['country']:r for r in s['energy']}
    def demand_gap(c):return energy[c]['model_demand_twh']-energy[c]['ember_demand_twh']
    text=f'''## Dispatch generation mix, demand and trade — 15 October 2026

**This compares actual saved dispatch quantities with observations**, rather than
comparing available supply with generated energy. The retained annual-v7 baseline
is unchanged. All {len(countries)} source countries are included; {complete_ref}
have twelve-month Ember total-generation references. ENTSO-E provides
{len(known_hourly)} country/technology comparisons with some known hours, of which
{len(full_hourly)} have all 8760 hours. Coverage does not certify whole-fleet scope.

The largest ranked core-fuel discrepancy that cannot be removed by changing only
the within-group allocation is **{biggest['country']} {biggest['technology']}**:
model {biggest['model_twh']:.2f} TWh, conditional range
[{biggest['lower_twh']:.2f}, {biggest['upper_twh']:.2f}], versus
Ember {biggest['ember_twh']:.2f} TWh. This flags a quantity mismatch, not an estimate
of missing installed capacity or a causal share of price error.

**What this changes in the diagnosis:** Germany's total generation differs by
only {totals['DE']['difference_twh']:.2f} TWh, but wind is
{bank['DE','Wind']['difference_twh']:+.2f} and gas
{bank['DE','Gas']['difference_twh']:+.2f} TWh. Matching total generation is not
matching the supply mix. Germany and the UK comparison also have demand differences
of {demand_gap('DE'):+.2f} and {demand_gap('GB'):+.2f} TWh: reconcile national
load boundaries before interpreting all generation errors as supply problems.
Italy's generation difference {totals['IT']['difference_twh']:+.2f} TWh nearly
matches its demand difference {demand_gap('IT'):+.2f} TWh, while implied net exports
differ by only {energy['IT']['model_implied_net_export_twh']-energy['IT']['ember_net_export_twh']:+.2f} TWh.

In Poland, demand is much closer ({demand_gap('PL'):+.2f} TWh), but model implied
net imports are {-energy['PL']['model_implied_net_export_twh']:.2f} TWh versus
{-energy['PL']['ember_net_export_twh']:.2f} reported, alongside coal generation
{bank['PL','Coal']['difference_twh']:+.2f} TWh below the reference. This motivates
separate supply-cost, commitment and network/trade tests; it does not identify
which mechanism caused the error. DE/GB wind excess and ES/PT wind deficits also
argue against a uniform European wind multiplier.

Spain's modeled wind availability integrates to {available_twh['ES','Wind']:.2f}
TWh, versus {bank['ES','Wind']['ember_twh']:.2f} TWh reported generation;
Portugal's figures are {available_twh['PT','Wind']:.2f} versus
{bank['PT','Wind']['ember_twh']:.2f} TWh. Even the available envelope is below
reported generation, so dispatch/bid changes alone cannot close those gaps with
the current inputs and boundaries. Audit fleet/capacity, weather normalization and
reporting scope first; do not substitute observed generation for availability.

### Equal-price dispatch is not a unique technology mix

The solver combines offers with identical annual bid sequences and balance columns.
Wind, solar and run-of-river can consequently share a zero-price offer. Its saved
output does not uniquely identify which of those technologies generated it.

For every retained group with output q, total available MW A and a selected
technology/country subset with available MW a, feasible subset generation lies
between max(0, q − (A − a)) and min(q, a). The illustrative point q × a/A preserves
the group's dispatch, cost and caps. Country and Ember-fuel bounds are computed
after aggregating source capacities to those labels, **not** by summing individual
technology bounds. Bounds for different labels need not be jointly attainable.
Fixed reservoir output is added exactly and remains separate from available MW.

These ranges are conditional on the retained aggregate offer outputs. They do not
explore other primal optima or rerun dispatch. Source-country placements within
shared zones, especially DE/LU and IE/GB, remain conditional under the zonal GSK
formulation. A point mix is not a uniquely predicted physical plant dispatch.

### Sources, calendar and accounting

- **Model:** annual-v7, all 8760 optimal UTC hours; source fleet, fixed hydro,
  original availability and bid profiles reconstructed; saved network physics replayed.
- **ENTSO-E:** cached A75/A16 production by PSR type, freshly replayed from raw
  intervals and integrated to hourly MWh. B19 is onshore wind; B18 offshore.
  Missing types and hours remain unknown. Country aggregates require every
  constituent zone. Germany's generation domain excludes Luxembourg and is compared
  with source-country DE; it is not treated as DE-LU or Luxembourg production.
- **Ember:** cached current-release national 2025 monthly generation, total demand
  and Net imports, with source receipt/hash. Annual references require all twelve
  months; explicit reported zeros remain zeros. Ember may share ENTSO-E upstream
  observations and is not necessarily an independent measurement.
- **Storage:** model battery/PHS dispatch is absent. Observed B10 pumped discharge
  and B25 storage discharge are kept separately, never added to primary generation.
  Ember Hydro/storage, gross/net generation, own use, charging and demand scope
  remain unreconciled. Bioenergy uses modeled biomass; all modeled waste is grouped
  with Other fossil as an explicit accounting proxy, not a verified biogenic split.
  Other renewables includes modeled geothermal but lacks some reported categories.

Incomplete national hourly geography: {shortages}. Italy's missing IT-CALA/IT-SICI
and Norway's missing NO5 are not replaced by zero or partial-country annual totals.
ENTSO-E reported-primary totals cover only source-reported types; they are not
certified complete national generation. Ember country totals provide broader
comparisons where complete, with their accounting limitations retained.
For example, German gas generation is {next(r for r in s['hourly'] if r['country']=='DE' and r['technology']=='gas')['year']['observed_twh']:.2f}
TWh in the 8760-hour ENTSO-E PSR series but {bank['DE','Gas']['ember_twh']:.2f} TWh
in Ember. The model is below both, but their difference needs reporting-scope,
CHP/autoproduction and gross/net reconciliation; complete hours alone do not prove
complete fleet coverage. Reservoir versus run-of-river classification also needs
reconciliation before interpreting a PSR-subtype difference as missing water.

### Annual production, demand and implied trade

All values are TWh; differences are model minus Ember. The model generation point
uses the illustrative tie split, with its conditional allocation range in brackets.
Implied model net exports = primary generation − prepared demand. Ember exports
negate its signed Net imports. This is **not** independently validated hourly
branch flow or bilateral trade; storage/loss/demand conventions can differ.
Generation differences must be read alongside demand and trade differences.

| Country | Model generation [range] | Ember generation | Generation difference | Demand difference | Implied net-export difference |
| --- | ---: | ---: | ---: | ---: | ---: |
'''+'\n'.join(total_rows)+'''

### Annual generation differences by technology

TWh, model illustrative allocation minus Ember. Unknown means incomplete reference,
not zero. Hydro comparisons retain the pumped-storage boundary caveat. The local
`generation-mix` PNG/SVG includes a full-country heatmap and monthly FR nuclear /
ES wind examples; `generation-shares` shows DE/FR/ES/NO composition. Share errors
and absolute TWh errors are distinct: normalization can hide a wrong total.
Figures are in the fresh `presentation-v2/` subdirectory. Missing component shares
remain unknown; charts show known shares and any unallocated total separately,
rather than treating an unreported fuel as verified zero.

| Country | Wind | Solar | Hydro | Nuclear | Gas | Coal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+'\n'.join(mix_rows)+'''

### Largest core-fuel gaps beyond within-group allocation

Sorted by distance of the twelve-month reference from the conditional allocation
range; hydro and waste/bioenergy proxies are excluded from this ranking. All other
countries/fuels remain in the data. “Outside range” means the mismatch cannot be
removed solely by redistributing the saved group outputs between equal-price
members. It does not distinguish fleet/weather, bid, demand, trade or reporting error.
Available energy is original available MW integrated over the year, **not dispatch**;
it ignores delivery and commitment. Where available energy exceeds reported
generation but dispatch is low, an annual capacity shortage alone is not an
explanation. Hourly timing, bids, imports, demand or other constraints may still matter.

| Country | Technology | Available TWh | Model TWh [range] | Ember TWh | Point difference | Outside range TWh |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''+'\n'.join(worst)+'''

### Hourly timing and monthly quantities

The full local comparison contains monthly totals and matched-hour bias, MAE, RMSE,
correlation and allocation-range exceedances for every available country/type.
Monthly and annual ENTSO-E sums use only their known hours; a partial sum is not
annualized. The examples below show matched-hour TWh and MW MAE. Correlation may
be unknown for constant or unavailable series. Point timing metrics inherit the
declared allocation rule; interval exceedances help identify robust discrepancies.

| Country | PSR technology | Known hours | Model matched TWh | Observed matched TWh | MAE MW | Correlation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''+'\n'.join(timing)+f'''

### Verification and next action

Four fixtures verify sharp marginal bounds and regrouping, zero availability,
emergency exclusion, missing hours and missing constituent zones, and B18/B19
identity. Independent `audit_dispatch_mix_2025.py` rebuilds source columns and
saved dispatch, checks proportional allocations and conditional bounds, rereads
PSR observations and Ember records, and replays monthly/annual quantities,
hourly metrics, shares, demand and implied trade. All {a['countries']} countries /
{a['annual_country_fuel_rows']} annual fuel rows pass. Maximum allocation
difference {a['maximum_allocation_error_mw']:.3g} MW; native-component residual
{a['maximum_network_residual_mw']:.3g} MW; global generation-demand-link-loss
closure {a['maximum_global_energy_closure_mw']:.3g} MW, below 1e-4 MW.

Fresh ignored root `data/bidding-zone-network-2025/generation-mix-v1/` contains
the declared design, raw-observation replay, source/code hashes, full monthly /
hourly metrics, quantities and figures. Producer `compare_dispatch_mix_2025.py`
plus helper `generation_mix_2025.py` takes {s['elapsed_seconds']:.2f}s including
source reconstruction and raw observation replay; independent audit
{a['elapsed_seconds']:.2f}s. No new clearing was run; these are audit timings.

Prioritize national demand-scope reconciliation, regional wind fleet/weather inputs,
then source-backed outage timing and separate bid/network/trade controls. In
particular, cheap supply and imports displacing thermal generation warrant a joint
quantity/price check before adding generic bid steps or raising fuel prices.
A reference outside
modeled availability flags input/scope issues; sufficient availability but different
dispatch motivates bid/constraint investigation, without establishing causality.
Do not fit generation into renewable availability. Hydro remains fixed, price and
mix accuracy gates remain open, and no investment or browser integration is accepted.
This report update is local; no CI/Pages or live-publication claim follows.

'''
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md';content=path.read_text()
    heading='## Dispatch generation mix, demand and trade — 15 October 2026\n'
    if heading in content:
        begin=content.index(heading);end=content.index('\n## ',begin+len(heading));content=content[:begin]+text+content[end+1:]
    else:
        anchor='## Residual-demand response and fleet-stack diagnosis — 15 October 2026';position=content.index(anchor);content=content[:position]+text+content[position:]
    path.write_text(content)
    (presentation/'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(audit_path),producer_sha256=digest(__file__),figures={name:digest(presentation/name) for name in ['generation-mix.png','generation-mix.svg','generation-shares.png','generation-shares.svg']}),indent=2)+'\n')
    print('Updated retained generation-mix article; figures remain ignored',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);report(p.parse_args().folder)
