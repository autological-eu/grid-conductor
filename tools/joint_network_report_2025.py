"""Four-figure retained report for the joint supply/network inverse experiment."""
import csv, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generation_mix_2025 import ROOT, digest

FUELS=['Wind','Solar','Nuclear','Gas','Coal']


def render(folder,public,prefix):
    s=json.loads((folder/'summary.json').read_text()); audit=json.loads((folder/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(folder/'summary.json')
    assert audit['auditor_sha256']==digest(ROOT/'tools/audit_joint_network_calibration_2025.py')
    assert audit['winner']==s['winner'] and len(audit['certificates'])+len(audit['rejected'])==16
    assert s['producer_sha256']==digest(ROOT/'tools/run_joint_network_calibration_2025.py')
    for p,h in s['source_hashes'].items(): assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items(): assert digest(ROOT/'tools'/p)==h
    records={r['id']:r for r in s['records']}; baseline='accepted-unchanged-w100'; bidonly='inverse_joint-unchanged-w100'; winner=s['winner']
    changed=[r for r in s['records'] if r['eligible'] and (r['parameters']['network']!='unchanged' or r['parameters']['wind']!=1)]
    physical=min(changed,key=lambda r:(r['score'],r['penalty'],r['ordinal']))['id'] if changed else None
    leader=min((k for k in records if records[k]['metrics'] is not None),key=lambda k:records[k]['metrics']['price'])
    shown=list(dict.fromkeys([baseline,bidonly,winner]+([physical] if physical and winner in [baseline,bidonly] else [])+[leader]))[:4]
    labels={baseline:'Accepted baseline',bidonly:'Bid-only fit'}
    if winner not in labels: labels[winner]='Joint-score winner'
    if physical and physical not in labels: labels[physical]='Best changed-input fit'
    if leader not in labels: labels[leader]='Price leader'
    root=ROOT/s['accepted_folder']
    with np.load(root/'development-targets.npz') as z: first={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z: target={k:np.concatenate([v,z[k]]) for k,v in first.items()}
    predictions={}
    for k in shown:
        info=s['annuals'][k]; path=ROOT/info['witness'] if info.get('external') else folder/info['witness']; assert digest(path)==info['witness_sha256']
        with np.load(path) as z: predictions[k]=z['row_duals'][:,:len(s['zones'])]
    def write_csv(name,rows):
        with (public/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(key for r in rows for key in r)),lineterminator='\n'); w.writeheader(); w.writerows(rows)
    cases=[]
    for r in s['records']:
        p=r['parameters']; cases.append(dict(case=r['id'],number=r['ordinal']+1,bid=p['bid'],network=p['network'],wind_factor=p['wind'],**(r['metrics'] or {key:None for key in s['reference']}),score=r['score'],penalty=r['penalty'],eligible=r['eligible'],joint_winner=r['id']==winner,emergency_mwh=s['annuals'][r['id']]['emergency_mwh'],binding_branch_hours=s['outcomes'][r['id']].get('network_diagnostics',{}).get('binding_branch_hours'),completed_hours=s['annuals'][r['id']]['optimal_hours'],status=s['annuals'][r['id']].get('rejection','complete_year'),rejected_hour=s['annuals'][r['id']].get('failed_hour')))
    write_csv('joint-search-cases.csv',cases)
    price_rows=[dict(model=k,label=labels[k],**{key:v for key,v in r.items() if not isinstance(v,(list,dict))}) for k in shown for r in s['outcomes'][k]['prices']['zones']]
    write_csv('joint-prices-by-zone.csv',price_rows)
    generation=[]
    for k in shown:
        o=s['outcomes'][k]; point=np.array(o['monthly_fuel_point_twh']).sum(axis=0); lo=np.array([r['generation_lower_twh'] for r in o['monthly_quantities']]).sum(axis=0); hi=np.array([r['generation_upper_twh'] for r in o['monthly_quantities']]).sum(axis=0)
        for ci,c in enumerate(s['countries']):
            for fi,fuel in enumerate(FUELS):
                ref=target['generation'][:,ci,fi]; known=np.isfinite(ref); total=float(ref.sum()) if known.all() else None
                generation.append(dict(model=k,country=c,fuel=fuel,illustrative_model_twh=float(point[ci,fi]),conditional_lower_twh=float(lo[ci,fi]),conditional_upper_twh=float(hi[ci,fi]),known_reference_months=int(known.sum()),observed_twh=total,difference_twh=None if total is None else float(point[ci,fi]-total)))
    write_csv('joint-generation-by-country.csv',generation)
    def save(fig,name): fig.savefig(public/name,dpi=160,bbox_inches='tight'); plt.close(fig)
    # Every declared state, including ineligible/adverse outcomes.
    fig,ax=plt.subplots(figsize=(11,6)); colors={'accepted':'#74899d','inverse_joint':'#087f79'}
    for k,r in records.items():
        if r['metrics'] is None:continue
        p=r['parameters']; ax.scatter(r['metrics']['price'],r['metrics']['generation'],marker='v' if p['wind']==.9 else 'o',s=75,color=colors[p['bid']],edgecolors='black' if r['eligible'] else '#e96940',linewidths=1.2)
        ax.annotate(str(r['ordinal']+1),(r['metrics']['price'],r['metrics']['generation']),xytext=((5,6) if r['ordinal']%2==0 else (-22,-12)),textcoords='offset points',fontsize=8)
    r=records[winner];ax.scatter(r['metrics']['price'],r['metrics']['generation'],s=230,facecolors='none',edgecolors='#162e40',lw=1.5)
    ax.set(xlabel='Full-year equal-zone price MAE (EUR/MWh)',ylabel='Monthly generation interval mismatch (lower is better)',title='Joint bid, wind-availability and AC-limit calibration\nGray: accepted bids; teal: fitted bids; triangle: wind ×0.9; outline: winner')
    fig.text(.10,.015,'Numbers match the complete case table. Orange edge = research filter failed.\nPlotted points have all 8,760 hours / 41 price zones; rejected states remain in the table.',fontsize=8);ax.grid(alpha=.2);fig.tight_layout(rect=(0,.10,1,1));save(fig,'overview.png')
    fig,ax=plt.subplots(figsize=(max(7,len(shown)*2.5),14)); grid=np.array([[r['mae_eur_mwh'] if r['known_hours'] else np.nan for r in s['outcomes'][k]['prices']['zones']] for k in shown]).T
    ceiling=max(45,float(np.nanpercentile(grid,90))); cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#e5e8ec');im=ax.imshow(grid,aspect='auto',vmin=0,vmax=ceiling,cmap=cmap)
    ax.set_xticks(range(len(shown)),[labels[k] for k in shown],rotation=20,ha='right');ax.set_yticks(range(len(s['zones'])),s['zones']);ax.set_title('Every modeled zone: full-year price MAE\nGray cells: no complete observed-price series')
    for j in range(len(s['zones'])):
        for i in range(len(shown)):
            if np.isfinite(grid[j,i]):ax.text(i,j,f'{grid[j,i]:.1f}',ha='center',va='center',fontsize=7,color='white' if grid[j,i]>.65*ceiling else '#172635')
    fig.colorbar(im,ax=ax,shrink=.65,label=f'EUR/MWh; colors capped at {ceiling:.1f}; values remain uncapped');fig.tight_layout();save(fig,'zone-mae-grid.png')
    stamps=np.arange('2025-01-01T00','2026-01-01T00',dtype='datetime64[h]');mask=(stamps>=np.datetime64('2025-07-01'))&(stamps<np.datetime64('2025-07-08'))
    fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True);palette=['#97a2ad','#cf914d','#087f79','#a94c7d']
    for ax,z in zip(axes,['NO5','DE-LU','ES','FR']):
        j=s['zones'].index(z);ax.plot(stamps[mask],target['prices'][mask,j],label='Observed A44',color='#172635',lw=1.2)
        for k,color in zip(shown,palette):ax.plot(stamps[mask],predictions[k][mask,j],label=labels[k],color=color,lw=.85)
        ax.set_ylabel(z+'\nEUR/MWh');ax.grid(alpha=.2)
    axes[0].set_title('Fixed example: 1–7 July 2025 UTC; headline metrics use the whole year');axes[0].legend(fontsize=7,ncol=3);fig.autofmt_xdate();fig.tight_layout();save(fig,'daily-prices.png')
    gen={(r['model'],r['country'],r['fuel']):r for r in generation}; mixshown=list(dict.fromkeys([baseline,bidonly,winner]));width=.8/(len(mixshown)+1)
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for ax,c in zip(axes.flat,['NO','DE','ES','FR']):
        x=np.arange(5)
        for i,k in enumerate(mixshown):
            vals=np.array([gen[k,c,f]['illustrative_model_twh'] for f in FUELS]);pos=x+(i-len(mixshown)/2)*width
            ax.bar(pos,vals,width=width,color=palette[i],label=labels[k])
            if k==winner:
                lo=np.array([gen[k,c,f]['conditional_lower_twh'] for f in FUELS]);hi=np.array([gen[k,c,f]['conditional_upper_twh'] for f in FUELS]);ax.errorbar(pos,vals,yerr=[np.maximum(vals-lo,0),np.maximum(hi-vals,0)],fmt='none',color='#172635',capsize=2,lw=.8)
        ref=[gen[winner,c,f]['observed_twh'] for f in FUELS];ax.bar(x+len(mixshown)/2*width,[np.nan if v is None else v for v in ref],width=width,color='#172635',label='Ember reference')
        ax.set_title(c);ax.set_xticks(x,FUELS,rotation=20);ax.set_ylabel('2025 national generation (TWh)');ax.grid(axis='y',alpha=.15)
    axes.flat[0].legend(fontsize=7);fig.suptitle('National five-fuel mix: observed generation is a target, not availability\nWinner whiskers are conditional allocation bounds, not uncertainty intervals');fig.tight_layout();save(fig,'national-mix.png')
    b=records[baseline]['metrics']; w=records[winner]['metrics']; ib=records[bidonly]['metrics']; bestprice=records[leader]['metrics']['price']
    fmt=lambda v,n: '—' if v is None else f'{v:.{n}f}'
    table='\n'.join(f"| {r['number']} | `{r['case']}` | {fmt(r['price'],3)} | {fmt(r['generation'],4)} | {fmt(r['trade'],4)} | {fmt(r['score'],4)} | {'yes' if r['eligible'] else 'no'} |" for r in cases)
    byzone={k:{r['zone']:r for r in s['outcomes'][k]['prices']['zones']} for k in shown}
    example='\n'.join(f"| {z} | {byzone[baseline][z]['mae_eur_mwh']:.2f} | {byzone[bidonly][z]['mae_eur_mwh']:.2f} | {byzone[winner][z]['mae_eur_mwh']:.2f} | {fmt(byzone[winner][z]['correlation'],3)} |" for z in ['NO1','NO2','NO3','NO4','NO5','DE-LU','ES','FR'])
    effects=[]
    for bid in ['accepted','inverse_joint']:
        control=records[bid+'-unchanged-w100']['metrics']
        for mode in ['all_lower','all_higher','nordic_lower','nordic_higher']:
            r=records[f'{bid}-{mode}-w100']
            if r['metrics'] is None:effects.append(f'| {bid} | {mode} | rejected: infeasible hour | — | no |')
            else:effects.append(f"| {bid} | {mode} | {r['metrics']['price']-control['price']:+.3f} | {r['metrics']['generation']-control['generation']:+.4f} | {'yes' if r['eligible'] else 'no'} |")
    catalogue=json.loads((folder/'branches.json').read_text()); nordic=sum(r['nordic'] for r in catalogue)
    native=max(c['native_modified_physics_residual_mw'] for c in audit['certificates']);gap=max(c['duality_gap_maximum_eur'] for c in audit['certificates']);fresh=s.get('verified_fresh_loop_seconds',sum(v['clearing_seconds'] for v in s['annuals'].values() if not v.get('external')))
    rejection_rows='\n'.join(f"| `{r['case']}` | {r['rejected_hour']} | {r['certificate']['separation_gap_mw']:.6f} |" for r in audit['rejected'])
    first_support=audit['rejected'][0]['active_branch_rows'] if audit['rejected'] else []
    support_countries=sorted({b[c] for b in first_support for c in ['country0','country1']})
    backend_controls=audit.get('matched_backend_controls',[])
    backend_difference=max((r['observed_price_mean_absolute_difference_eur_mwh'] for r in backend_controls),default=0.)
    parameters=records[winner]['parameters']; change='The joint winner changes physical inputs.' if parameters['network']!='unchanged' or parameters['wind']!=1 else 'The tested physical changes do not beat the best unchanged-input control on the declared joint score.'
    network_description={'unchanged':'unchanged AC headroom','all_lower':'15% less AC headroom across Europe','all_higher':'15% more AC headroom across Europe','nordic_lower':'15% less headroom on Nordic-incident AC branches','nordic_higher':'15% more headroom on Nordic-incident AC branches'}[parameters['network']]
    bid_description='the accepted baseline bids' if parameters['bid']=='accepted' else 'the previous fitted bids'
    report=f'''# Inverse market modelling: fitting supply and network constraints

## Summary

We now allow **network limits and generation availability to change alongside supply bids**, rather than fitting bids against a fixed grid. A finite 2025 experiment tests **16 combinations**, using two existing bid anchors and **14 new parameter states**. **{len(audit['certificates'])} cases have complete annual witnesses; {len(audit['rejected'])} are rejected by independently replayed infeasibility certificates**. The best joint-score case is **`{winner}`**: price MAE **{w['price']:.3f} EUR/MWh**, versus **{b['price']:.3f}** for the accepted baseline and **{ib['price']:.3f}** for the previous bid-only winner. Generation mismatch is **{w['generation']:.4f}**, versus **{b['generation']:.4f}** baseline; implied-trade mismatch **{w['trade']:.4f}**, versus **{b['trade']:.4f}**. {change}

The winner uses **{bid_description}**, **{network_description}**, and **wind availability ×{parameters['wind']:.1f}**. These are fitted effective assumptions, **not a recovered real grid**. The lowest price MAE across all tested cases is **{bestprice:.3f} EUR/MWh**; price-only leadership and joint eligibility are distinct. The target below10 EUR/MWh remains unmet. All targets also inform selection: this is **in-sample reconstruction, not independent forecasting**. Neither the accepted baseline nor the browser scenario engine is replaced.

![Every joint supply/network state, price and generation performance]({prefix}overview.png)

## 1. What is being estimated?

Each forward hourly LP chooses dispatch $x_t$ to minimize submitted offer cost $c_t(\\theta)^T x_t$, subject to generation bounds and the physical network equations. Its zonal balance duals give cleared prices $p_t(\\theta)$. In this experiment, $\\theta$ selects a bid anchor, a wind-availability factor and an AC rating factor; **prices are always produced by clearing, never replaced by observations**.

Inverse modelling selects parameters whose forward prices and generation resemble observations. Price alone cannot distinguish expensive bids from unavailable cheap supply or limited imports. Generation and exchanges add information, but do not make the parameters uniquely identified. Fixed GSKs, aggregated offers and nonunique LP duals add ambiguity. The experiment is a small finite search, not an exact globally solved bilevel problem, exhaustive model distribution or proof of actual market offers.

The method follows the inverse-optimisation framing in [Chan, Mahmood and Zhu](https://arxiv.org/abs/2109.03920). [Liang and Dvorkin](https://arxiv.org/html/2302.05498v2) study electricity offer recovery; their identification assumptions do not automatically hold for our aggregated synthetic market. [Birge, Hortaçsu and Pavlin](https://doi.org/10.1287/opre.2017.1606) study constraint recovery from prices. Those results motivate constraint calibration; they do not validate arbitrary European capacity changes or guarantee our fitted parameters are true.

## 2. Baseline model and source data

The accepted `seasonal-calendar-v1/refit` has **48 modeled areas, 145 physical buses, 41 complete observed-price zones and all8,760 UTC hours of2025**. Country-to-zone/source allocation proxies remain. Each hour is an independent sparse LP; daily grouping adds no commitment, ramps or storage optimization. This is EUPHEMIA-inspired synthetic clearing, not reconstruction of actual order books or nonconvex allocation rules.

| Component | Data and treatment |
| --- | --- |
| Grid and fleet | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0; existing PTDF/GSK, AC islands, original HVDC bounds and losses. Static AC headroom starts at0.7 of source nominal ratings; N-0 model limits, not certified commercial JAO domains. |
| Wind/solar | Original2025 [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)/[atlite](https://atlite.readthedocs.io/) weather profiles and [IRENA](https://www.irena.org/Data) end-2024/end-2025 linear capacity trajectory. Commissioning dates, fleet siting and generic resource conversion are proxies. |
| Demand | Prepared2025 [ENTSO-E](https://transparency.entsoe.eu/) demand, fixed in every case; regional allocation and gross/net scope limitations remain. |
| Hydro/nuclear | Fixed hourly water schedules, with retained Norwegian NVE inflow/stock evidence; unchanged nuclear availability proxy. Capacity does not create water. No hydro or storage search restarted. |
| Offers | Monthly World Bank TTF/Brent and ECB FX anchors, plant efficiency/VOM,80 EUR/t carbon assumption, accepted smooth seasonal/hourly bids. The second anchor is the independently verified prior inverse joint winner `r2-s6`; no new bid coefficients are fitted here. |
| Targets | Source-hashed ENTSO-E A44 hourly prices; [Ember](https://ember-energy.org/data/) monthly national Wind/Solar/Nuclear/Gas/Coal generation and signed net exports. Missing values stay unknown. |

Generation scores measure distance outside **conditional saved-group allocation bounds**, divided by max(reference,0.25 TWh), averaged over known country/fuel/month observations. Proportional point allocations are illustrative; bounds are not jointly attainable ranges over all optimal dispatches or statistical confidence intervals. Hydro, biomass and other generation are outside the five-fuel score. New-fit hourly zonal A75 generation validation remains outstanding.

The trade score compares implied generation minus demand with national net exports, normalized by max(model demand,1 TWh). It is **not observed physical border flow**. JAO domains and original-request-classified ENTSO-E flows are not fitted here. Generation/price consistency cannot by itself certify every border constraint.

## 3. Exact adjustable parameters and search

**AC constraints:** preserve $|Hq_t+o_t|\\leq r(\\theta)$, with unchanged PTDF $H$, injection variables $q_t$, offsets $o_t$, topology, impedance, GSK, islands and HVDC physics. Multiply existing symmetric MW limits by **0.85,1 or1.15**. The inherited nominal-rating factor becomes0.595/0.7/0.805. Nothing exceeds source nominal ratings. This changes permitted headroom, not impedance or physical construction, and includes internal AC constraints rather than treating every branch as a commercial border.

Global controls adjust all **{len(catalogue)}** passive branches. Nordic controls adjust the **{nordic}** branches with either endpoint in NO/SE/FI/DK, including incident cross-region AC lines. HVDC links remain unchanged. These static bounds are **experimental calibration assumptions**, not values verified from JAO, outage records or N-1 studies. Their narrow range is deliberately interpretable; it does not encompass every plausible constraint error.

**Wind availability:** multiply original source wind available MW by **1 or0.9**, before aggregation. Preserve chronological weather shape, source country, capacity/nameplate and all solar/other availability. Recompute the available MW used in both clearing and conditional generation allocation. The0.9 hypothesis can represent a coarse conversion/derating bias; it is not a measured correction or capacity estimate, and no observed hourly dispatch becomes available supply. A spatially uniform annual factor cannot repair wrong site geography or within-year timing.

**Bids:** compare two frozen anchors: accepted seasonal bids and prior inverse joint bids. The latter contains bounded smooth gas/coal/nuclear adjustments, Ember mix signals and monotone thermal premiums. Those coefficients are not refitted when the physical parameters change. Therefore this tests joint combinations and interactions, not unrestricted simultaneous continuous estimation.

The main factorial has2 bid anchors ×3 global AC choices ×2 wind choices =12 cases; four extra Nordic lower/higher controls use original wind. Exactly16 states are retained, including adverse and infeasible outcomes. There is no adaptive widening after seeing results. The all-year objective is0.55 normalized price MAE +0.20 within-day demeaned MAE +0.20 generation mismatch +0.05 trade mismatch, plus0.01 times bid/physical departure regularization. Physical regularization averages squared normalized departures in wind, Nordic-incident AC and other AC limits. Bid regularization uses the previous source-availability-weighted offer deviation.

Eligibility requires price MAE no higher than accepted baseline; demeaned-price, generation and trade scores no more than2% worse; all8,760 optimal hours and emergency supply at most1e-6 MWh. These are declared research filters, **not product acceptance gates**. Selection minimizes the regularized score among eligible states, then penalty and ordinal. No automatic baseline promotion follows.

| # | Case | Price MAE | Generation score | Trade score | Joint score | Eligible |
| --- | --- | ---: | ---: | ---: | ---: | --- |
{table}

**Rejected physical combinations.** The first tightened case was initially allowed to continue after HiGHS reported infeasible hours. That diagnostic run was stopped; its completed wind-control witness is reused with original code provenance. Before the remaining search, the failure policy was amended to reject a year at its first numerically certified infeasible hour. Parameter bounds, objective and acceptance filters were unchanged. No partial-year price/mix metric is reported or eligible.

| Rejected case | First rejected UTC hour index | Numerical Farkas separation (MW) |
| --- | ---: | ---: |
{rejection_rows}

The first rejected case's independently replayed certificate uses **{len(first_support)} AC branch rows** with endpoint countries **{', '.join(support_countries)}**. These are participating constraints in one proof, not a unique causal attribution to individual real lines. The certificate therefore localizes a model-consistency issue; it does not establish a real-world shortage.

Hour index0 means1 January2025 at00:00 UTC. A Farkas row ray combines the model's row bounds into a requirement larger than any value allowed by its generation/link bounds, with zero free-injection coefficients to numerical tolerance. The positive separation certifies that hour's constraint set is empty within numerical tolerance. Rays are normalized by their largest absolute row coefficient; the separation magnitude depends on that normalization and is not a physical shortage volume or measured line-capacity deficit. This may expose restricted fixed injection/GSK assumptions, not a real European electricity shortage. Later hours need not be solved to reject a full-year-feasible claim. Changing bid prices cannot repair an empty physical feasible set; reducing only an upper availability bound cannot restore feasibility either. A source-backed constraint or injection/GSK correction would be a different model change, requiring fresh verification.

`accepted` and `inverse_joint` identify bid anchors; `w100`/`w90` identify original/90% wind availability. All-zone, monthly quantity and tail evidence remain separate from aggregate ranking. See [every case]({prefix}joint-search-cases.csv), [shown-model zonal metrics]({prefix}joint-prices-by-zone.csv), and [national fuel volumes/differences]({prefix}joint-generation-by-country.csv).

## 4. Does changing the network help?

The following comparisons hold both bids and original wind availability fixed. Deltas are relative to the unchanged-network case with the **same** bid anchor; negative values improve the error. This isolates effective network-limit changes from bid-fitting gains.

| Bid anchor | Network change | Price MAE delta | Generation-score delta | Eligible |
| --- | --- | ---: | ---: | --- |
{chr(10).join(effects)}

![Full-year price MAE for every modeled zone]({prefix}zone-mae-grid.png)

The grid shows every modeled area, retaining unknown-price cells and regional regressions. NO5 improves from **{byzone[baseline]['NO5']['mae_eur_mwh']:.2f} to {byzone[winner]['NO5']['mae_eur_mwh']:.2f} EUR/MWh**, with correlation **{fmt(byzone[baseline]['NO5']['correlation'],3)}→{fmt(byzone[winner]['NO5']['correlation'],3)}**. But NO2/NO4 and all four Swedish zones have higher MAE than the accepted baseline; France also worsens under the joint winner. The globally relaxed price leader offers a different country trade-off; its near-identical aggregate MAE does not identify which grid is true. National generation agreement is not evidence of correctly located zonal injections. Norway's fixed hydro remains an important structural restriction: AC-limit changes can reroute its fixed production, but cannot create a water-value offer or reschedule water.

| Zone | Accepted MAE | Bid-only MAE | Joint winner MAE | Winner r |
| --- | ---: | ---: | ---: | ---: |
{example}

![Observed and simulated hourly prices in a fixed July week]({prefix}daily-prices.png)

Examples always use1–7 July2025 UTC. All headline scores use the full year, not that week. NO5 is a price illustration; it does not establish complete NO5 generation validation. The five Norwegian price zones remain separate.

![National generation for Norway, Germany, Spain and France]({prefix}national-mix.png)

The mix comparison shows five fuels for NO/DE/ES/FR. Hydro, biomass and other resources are excluded, so this is not a complete national energy-mix validation. Winner whiskers represent conditional allocation bounds; they are not probabilistic uncertainty. Downloads retain missing reference months and signed model-minus-observed TWh. Lower generation mismatch can accompany worse prices in an individual zone, so neither outcome is hidden by the joint score.

## 5. Interpretation, limitations and next steps

**Joint calibration is implementable at this scale.** This trial changes real forward-model bounds, rather than applying a statistical price correction after solving. It exposes whether coarse source/grid assumptions have more leverage than bids alone. The selected Nordic headroom is at the upper tested bound; that is neither a measured transfer capacity nor justification to widen it without new evidence. Its result is a comparison within a deliberately small parameter family; it cannot rule out better seasonal/regional availability, commercial-domain or operating models.

A fitted network can compensate for incorrect bids, demand scope, fixed hydro or GSKs. A lower in-sample error therefore supports a hypothesis, not a verified source correction. The next useful refinement should depend on the observed frontier: independently check the constraints/availability that need adjustment, add verified commercial flow/net-position evidence where available, and expand regional/seasonal parameters only with explicit bounds and identifiability checks. The current model still lacks commitment/ramping, adaptive water offers and a fully represented negative-bid mechanism. Do not assign all residual error to transmission.

For investment analysis, compare each credible fitted model with itself plus the asset, preserving common inputs. Freeze its calibrated parameters within each pair; refitting an intervention to historical baseline prices would suppress the investment effect being estimated. Capacity addition and effective-limit calibration are different interventions; new AC impedance or GSK effects require a faithful network recompile. Effective calibrated bid costs are not verified physical production costs or welfare. Revalue dispatch with independent resource-cost/emission inputs, separating system impacts from revenues/rent. **No investment scenario or posterior distribution is verified by this trial.** Fixed hydro may bias investment effects in either direction. The live browser remains the older two-node line/battery screen.

## 6. Verification and reproduction

Independent replay checks **{len(audit['certificates'])} full-year witnesses and {len(audit['rejected'])} rejected-state certificates**, source hashes, exactly declared states, altered source wind MW and group allocation, native component flows against **altered branch limits**, unchanged source physics elsewhere, primal bounds, objective/dual/complementarity, all price/mix/trade metrics, regularization, eligibility and winner selection. Maximum component residual **{native:.3g} MW**; maximum duality gap **EUR {gap:.6f}**.

Three complete witnesses are reused intact: two prior anchors and the wind control from the interrupted driver. Fresh verified-driver clearing/rejection/retry loops total **{fresh:.2f}s**; source preparation **{s['preparation_seconds']:.2f}s**, retry preparation **{s.get('stage_timings',{}).get('retry_preparation_seconds',0.):.2f}s**, sum of verified source/retry driver commands **{s['end_to_end_seconds']:.2f}s**, peak RSS **{s['peak_rss_mib']:.0f} MiB**. Independent replay is additional time. An initial restart also stopped at a source-versus-normalized-JSON provenance check before any new clears; that check was corrected and moved before model building. That preparation and the earlier interrupted diagnostic are additional, excluded from this current-driver total; the reused wind-control clearing took 141.11s. This is not a claim of combined end-to-end wall-clock experiment runtime.

Two global-relaxation states initially returned Not Set, not Infeasible. Their unchanged-network solutions are checked as feasible controls, and the same state parameters are retried with a reset HiGHS scheduler and presolve off, preserving the 1e-8 primal tolerance. Every successful retry receives the same independent primal/dual and native-physics audit; unresolved numerical cases are never treated as evidence of infeasibility. The auditor also re-clears **{len(backend_controls)} complete unchanged-network years** with the retry backend as matched numerical controls, not new fitted states. Their largest observed-hour mean absolute price departure from the saved controls is **{backend_difference:.6g} EUR/MWh**; LP dual nonuniqueness remains an identification caveat.

With existing verified source caches, restore immutable metadata with `python3 tools/pack_model_metadata.py --restore`. Use pinned Python `data/pypsa-eur/upstream/.pixi/envs/default/bin/python` with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; run `tools/run_joint_network_calibration_2025.py` into a **fresh ignored output directory**, then audit the final directory with `tools/audit_joint_network_calibration_2025.py`. When the declared driver records unresolved numerical states, use `tools/repair_joint_network_calibration_2025.py SOURCE FRESH_RETRY_DIRECTORY` before that audit; it retries only the identical failed states and binds both stages. The retained interrupted wind-control/code/config caches are also prerequisites for current replay. The runner enforces5 GiB address space, a50-minute alarm and a per-output process lock. Existing directories are never implicitly resumed. Public compact assets alone cannot reproduce numerical runs without the omitted large provider/source caches.

Sources/method: [joint parameterization](tools/joint_network_calibration_2025.py), [driver](tools/run_joint_network_calibration_2025.py), [independent replay](tools/audit_joint_network_calibration_2025.py), and [provenance receipt]({prefix}summary.json). Prior [bid-only cases]({prefix}inverse-search-cases.csv), [zonal metrics]({prefix}inverse-prices-by-zone.csv) and [mix comparison]({prefix}inverse-generation-by-country.csv) remain supporting evidence, not a new accepted baseline. Raw observations, hourly arrays and witnesses stay locally ignored. This report does not claim deployment, market certification or independent forecasting.
'''
    for a,b in [('below10','below 10'),('all8,760','all 8,760'),('of2025','of 2025'),('at0.7','at 0.7'),('Original2025','Original 2025'),('original2025','original 2025'),('Prepared2025','Prepared 2025'),('prepared2025','prepared 2025'),('VOM,80','VOM, 80'),('factor becomes0.595','factor becomes 0.595'),('The0.9','The 0.9'),('**0.85,1 or1.15**','**0.85, 1 or 1.15**'),('becomes0.595','becomes 0.595'),('**1 or0.9**','**1 or 0.9**'),('The0.9','The 0.9'),('has2 bid','has 2 bid'),('×3 global','× 3 global'),('×2 wind','× 2 wind'),('=12 cases','= 12 cases'),('Exactly16','Exactly 16'),('is0.55','is 0.55'),('+0.20','+ 0.20'),('+0.05','+ 0.05'),('plus0.01','plus 0.01'),('than2%','than 2%'),('most1e-6','most 1e-6'),('use1–7 July2025','use 1–7 July 2025'),('EUR{','EUR {'),('Hour index0 means1 January2025 at00:00 UTC.','Hour index 0 means 1 January 2025 at 00:00 UTC.'),('enforces5','enforces 5'),('a50-minute','a 50-minute')]: report=report.replace(a,b)
    report='\n'.join(line.rstrip() for line in report.splitlines())+'\n'
    receipt=dict(repair_producer_sha256=s.get('repair_producer_sha256'),retry_protocol=s.get('retry_protocol'),stage_timings=s.get('stage_timings'),summary_sha256=digest(folder/'summary.json'),audit=audit,design=s['design'],producer_sha256=s['producer_sha256'],helper_sha256=s['dependencies']['joint_network_calibration_2025.py'],clearer_sha256=s['dependencies']['joint_network_clear_2025.py'],renderer_sha256=digest(__file__),winner=winner,price_leader=leader,best_changed_inputs=physical,shown=shown,labels={k:labels[k] for k in shown},records=s['records'],annuals=s['annuals'],branch_count=len(catalogue),nordic_branch_count=nordic,preparation_seconds=s['preparation_seconds'],end_to_end_seconds=s['end_to_end_seconds'],peak_rss_mib=s['peak_rss_mib'])
    return report,receipt
