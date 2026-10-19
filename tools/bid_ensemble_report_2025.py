"""Concise current inverse-modelling report; four figures and compact CSV evidence."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generation_mix_2025 import ROOT,digest

FUELS=['Wind','Solar','Nuclear','Gas','Coal']


def render(folder,public,prefix):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'verification-v1/audit.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and a['members']==s['members']
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_inverse_bid_ensemble_2025.py')
    assert s['producer_sha256']==digest(ROOT/'tools/run_inverse_bid_ensemble_2025.py')
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    assert len(a['certificates'])==len(s['records'])
    assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in a['certificates'])
    records={r['id']:r for r in s['records']};winner=a['winning_state'];leader=min(records,key=lambda k:records[k]['metrics']['price']);members=s['members']
    shown=list(dict.fromkeys(['baseline']+members+[leader]));root=ROOT/s['accepted_folder']
    eligible_ids=[k for k in records if records[k]['eligible']]
    with np.load(root/'development-targets.npz') as z:first={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in first.items()}
    predictions={}
    for k in list(dict.fromkeys(shown+eligible_ids)):
        info=s['annuals'][k];path=ROOT/info['witness'] if info.get('external') else folder/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:predictions[k]=z['row_duals'][:,:len(s['zones'])]
    def write_csv(name,rows):
        fields=list(dict.fromkeys(k for r in rows for k in r))
        with (public/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
    def save(fig,name):fig.savefig(public/name,dpi=150,bbox_inches='tight',facecolor='white');plt.close(fig)
    rows=[]
    for k,r in records.items():rows.append(dict(model=k,parent=r['parent'],round=r['round'],price_step=r['step'][0],mix_step=r['step'][1],curve_step=r['step'][2],**r['metrics'],penalty=r['penalty'],score=r['score'],eligible=r['eligible'],retained=k in members,bid_sha256=r['bid_sha256']))
    write_csv('inverse-search-cases.csv',rows)
    prop_path=folder/'round-2-proposal.json';assert digest(prop_path)==s['proposals'][1]['sha256']
    support=np.array(json.loads(prop_path.read_text())['support_hours'])
    broad_stack=np.array([predictions[k] for k in eligible_ids]);broad_low=broad_stack.min(axis=0);broad_high=broad_stack.max(axis=0)
    broad=[]
    for zi,zone in enumerate(s['zones']):
        good=np.isfinite(target['prices'][:,zi]);observed=target['prices'][:,zi]
        broad.append(dict(zone=zone,known_hours=int(good.sum()),observed_in_minmax_fraction=float(((observed[good]>=broad_low[good,zi]-1e-8)&(observed[good]<=broad_high[good,zi]+1e-8)).mean()) if good.any() else None,mean_width_eur_mwh=float((broad_high[:,zi]-broad_low[:,zi]).mean())))
    broad_coverage={r['zone']:r for r in broad}
    coverage={r['zone']:r for r in s['coverage']};price_rows=[]
    for k in shown:
        for r in s['outcomes'][k]['prices']['zones']:price_rows.append(dict(model=k,role='baseline' if k=='baseline' else 'retained' if k in members else 'price leader outside primary set',**r,ensemble_observed_minmax_fraction=coverage[r['zone']]['observed_in_minmax_fraction'],ensemble_mean_width_eur_mwh=coverage[r['zone']]['mean_width_eur_mwh']))
    # Keep numeric scalar summaries, not repeated24-hour profiles/arrays.
    price_rows=[{k:v for k,v in r.items() if not isinstance(v,(list,dict))} for r in price_rows]
    for row in price_rows:
        zi=s['zones'].index(row['zone']);row['last_proposal_parent']=s['proposals'][1]['parent'];row['all_eligible_minmax_fraction']=broad_coverage[row['zone']]['observed_in_minmax_fraction'];row['all_eligible_mean_width_eur_mwh']=broad_coverage[row['zone']]['mean_width_eur_mwh']
        for fi,family in enumerate(['gas','coal','nuclear']):row[family+'_supporting_interior_hours']=int(support[zi,fi])
    write_csv('inverse-prices-by-zone.csv',price_rows)
    generation=[]
    for k in shown:
        point=np.array(s['outcomes'][k]['monthly_fuel_point_twh']).sum(axis=0);low=np.array([r['generation_lower_twh'] for r in s['outcomes'][k]['monthly_quantities']]).sum(axis=0);high=np.array([r['generation_upper_twh'] for r in s['outcomes'][k]['monthly_quantities']]).sum(axis=0)
        for ci,c in enumerate(s['countries']):
            for fi,fuel in enumerate(FUELS):
                ref=target['generation'][:,ci,fi];known=np.isfinite(ref);annual=float(ref.sum()) if known.all() else None
                generation.append(dict(model=k,country=c,fuel=fuel,known_reference_months=int(known.sum()),observed_twh=annual,illustrative_model_twh=float(point[ci,fi]),conditional_lower_twh=float(low[ci,fi]),conditional_upper_twh=float(high[ci,fi]),difference_twh=float(point[ci,fi]-annual) if annual is not None else None))
    write_csv('inverse-generation-by-country.csv',generation)
    # Price-vs-quantity trade-off: all attempted unique states, including rejects.
    fig,ax=plt.subplots(figsize=(10,5));baseline=records['baseline']
    for k,r in records.items():
        color='#177a70' if r['eligible'] else '#bd652d';mark='*' if k=='baseline' else 'o';ax.scatter(r['metrics']['price'],r['metrics']['generation'],color=color,marker=mark,s=160 if k=='baseline' else 55,edgecolor='#182a3b' if k in members else 'none',linewidth=1.5)
        ax.annotate(k,(r['metrics']['price'],r['metrics']['generation']),xytext=(4,5 if r['ordinal']%2==0 else -11),textcoords='offset points',fontsize=8)
    ax.set(xlabel='Full-year equal-zone hourly price MAE (EUR/MWh)',ylabel='Monthly generation-interval mismatch score',title='Inverse calibration: price improvements and generation trade-offs\nGreen passes research filters; orange fails; outlined states form the retained set')
    ax.grid(alpha=.2);fig.tight_layout();save(fig,'overview.png')
    # Every model area retained; gray means no complete price observations.
    pr={k:{r['zone']:r for r in s['outcomes'][k]['prices']['zones']} for k in shown};grid=np.full((len(s['zones']),len(shown)),np.nan)
    for j,z in enumerate(s['zones']):
        for i,k in enumerate(shown):
            if pr[k][z]['known_hours']:grid[j,i]=pr[k][z]['mae_eur_mwh']
    fig,ax=plt.subplots(figsize=(max(7,len(shown)*1.35),14));cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#e8edf2');ceiling=max(40,float(np.nanquantile(grid,.95)))
    im=ax.imshow(np.ma.masked_invalid(grid),cmap=cmap,vmin=0,vmax=ceiling,aspect='auto')
    ax.set_xticks(range(len(shown)),[k+('\nnot retained' if k not in members and k!='baseline' else '') for k in shown],rotation=25,ha='right');ax.set_yticks(range(len(s['zones'])),s['zones']);ax.set_title('All modeled zones: full 2025 hourly price MAE\nEUR/MWh; gray = no complete observed price series')
    for j in range(len(s['zones'])):
        for i in range(len(shown)):
            if np.isfinite(grid[j,i]):ax.text(i,j,f'{grid[j,i]:.1f}',ha='center',va='center',fontsize=7,color='white' if grid[j,i]>ceiling*.65 else '#172635')
    fig.colorbar(im,ax=ax,shrink=.65,label=f'MAE; colors capped at {ceiling:.1f}, numbers retain full values');fig.tight_layout();save(fig,'zone-mae-grid.png')
    # Fixed illustrative UTC week, not selected for fit; annual metrics use every hour.
    stamps=np.arange('2025-01-01T00','2026-01-01T00',dtype='datetime64[h]');mask=(stamps>=np.datetime64('2025-07-01'))&(stamps<np.datetime64('2025-07-08'));stack=np.array([predictions[k] for k in members]);lower=stack.min(axis=0);upper=stack.max(axis=0)
    fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True)
    for ax,z in zip(axes,['NO5','DE-LU','ES','FR']):
        zi=s['zones'].index(z);ax.fill_between(stamps[mask],broad_low[mask,zi],broad_high[mask,zi],color='#e8a75d',alpha=.3,label='All eligible fits: diagnostic min/max')
        ax.fill_between(stamps[mask],lower[mask,zi],upper[mask,zi],color='#1e9a9b',alpha=.25,label='Primary near-best min/max (not confidence)')
        ax.plot(stamps[mask],target['prices'][mask,zi],color='#172635',lw=1.1,label='Observed A44');ax.plot(stamps[mask],predictions['baseline'][mask,zi],color='#949da7',lw=.8,label='Accepted baseline')
        ax.plot(stamps[mask],predictions[winner][mask,zi],color='#087c78',lw=.9,label='Score-winning fit')
        if leader not in members:ax.plot(stamps[mask],predictions[leader][mask,zi],color='#bd652d',lw=.7,ls='--',label='Price leader outside primary set')
        ax.set_ylabel(z+'\nEUR/MWh');ax.grid(alpha=.2)
    axes[0].set_title('A fixed example week: 1–7 July 2025 (UTC)\nThin/narrow fit spread can coexist with large observed-price errors');axes[0].legend(fontsize=7,ncol=2);fig.autofmt_xdate();fig.tight_layout();save(fig,'daily-prices.png')
    # Match each national fuel reference, show conditional group-allocation bounds.
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    grows={(r['model'],r['country'],r['fuel']):r for r in generation}
    for ax,c in zip(axes.flat,['NO','DE','ES','FR']):
        x=np.arange(5);b=[grows['baseline',c,f]['illustrative_model_twh'] for f in FUELS];w=[grows[winner,c,f]['illustrative_model_twh'] for f in FUELS];o=[grows[winner,c,f]['observed_twh'] for f in FUELS]
        ax.bar(x-.25,b,width=.25,label='Accepted baseline',color='#8c99a6');ax.bar(x,w,width=.25,label='Score-winning fit',color='#138a84');ax.bar(x+.25,[np.nan if v is None else v for v in o],width=.25,label='Ember reference',color='#203349')
        lo=np.array([grows[winner,c,f]['conditional_lower_twh'] for f in FUELS]);hi=np.array([grows[winner,c,f]['conditional_upper_twh'] for f in FUELS]);ax.errorbar(x,w,yerr=[np.maximum(np.array(w)-lo,0),np.maximum(hi-np.array(w),0)],fmt='none',color='#172635',lw=.8,capsize=2)
        ax.set_title(c);ax.set_xticks(x,FUELS,rotation=20);ax.set_ylabel('2025 national generation (TWh)');ax.grid(axis='y',alpha=.15)
    axes[0,0].legend(fontsize=8);fig.suptitle('Five comparable fuel families; hydro and other generation excluded\nBars illustrate saved-group allocations; whiskers are conditional bounds, not uncertainty intervals');fig.tight_layout();save(fig,'national-mix.png')
    elig=[r for r in records.values() if r['eligible']];base=records['baseline']['metrics'];win=records[winner]['metrics'];bestprice=records[leader]['metrics']['price'];mean_cover=float(np.mean([r['observed_in_minmax_fraction'] for r in s['coverage'] if r['known_hours']]))
    sensitivity=[]
    for tolerance in [.005,.01,.02,.03]:
        pool=[r for r in records.values() if r['eligible'] and r['score']<=records[winner]['score']+tolerance+1e-12 and r['metrics']['price']<=records[winner]['metrics']['price']+1+1e-12]
        sensitivity.append(dict(score_tolerance=tolerance,qualifying_states=len(pool),retained_cap=min(5,len(pool))))
    sensitivity_table='\n'.join(f"| {r['score_tolerance']:.3f} | {r['qualifying_states']} | {r['retained_cap']} |" for r in sensitivity)
    broad_cover=float(np.mean([r['observed_in_minmax_fraction'] for r in broad if r['known_hours']]))
    broad_width=float(np.mean([r['mean_width_eur_mwh'] for r in broad if r['known_hours']]))
    headline='The bounded search found eligible alternative bid fits.' if len(members)>1 else 'The predeclared near-best ensemble contains only one member; other research-eligible fits exist but are outside that narrow score cutoff.'
    names={'baseline':'Accepted baseline',winner:'Joint-score fit ('+winner+')'}
    if leader!=winner:names[leader]='Price-focused fit ('+leader+')'
    state_values={}
    for k in [winner,leader]:
        p=folder/(k+'-parameters.json');assert digest(p)==s['parameter_hashes'][k];state_values[k]=json.loads(p.read_text())
    winner_tops=np.array(state_values[winner]['curve'])*[60,40];leader_tops=np.array(state_values[leader]['curve'])*[60,40]
    table='\n'.join(f"| {names.get(k,k)} | {records[k]['metrics']['price']:.3f} | {s['outcomes'][k]['prices']['mean_correlation']:.3f} | {records[k]['metrics']['daily_demeaned_price']:.3f} | {records[k]['metrics']['generation']:.4f} | {records[k]['metrics']['trade']:.4f} | {'yes' if records[k]['eligible'] else 'no'} |" for k in list(dict.fromkeys(['baseline']+members+[leader])))
    examples='\n'.join(f"| {z} | {pr['baseline'][z]['mae_eur_mwh']:.2f} | {pr[winner][z]['mae_eur_mwh']:.2f} | {pr['baseline'][z]['correlation']:.3f} | {pr[winner][z]['correlation']:.3f} |" for z in ['NO1','NO2','NO3','NO4','NO5','DE-LU','ES','FR'])
    support_table='\n'.join(f"| {z} | {support[s['zones'].index(z),0]} | {support[s['zones'].index(z),1]} | {support[s['zones'].index(z),2]} |" for z in ['NO1','NO2','NO3','NO4','NO5','DE-LU','ES','FR'])
    physical=max(c['original_component_residual_mw'] for c in a['certificates']);gap=max(c['duality_gap_maximum_eur'] for c in a['certificates']);seconds=sum(v['clearing_seconds'] for v in s['annuals'].values() if not v.get('external'))
    report=f'''# Inverse market modelling: European2025 bid calibration

## Summary

**{headline}** The accepted seasonal-bid baseline has full-year price MAE **{base['price']:.3f} EUR/MWh**. The score-winning eligible state, **{winner}**, gives **{win['price']:.3f} EUR/MWh** ({100*(1-win['price']/base['price']):.2f}% lower), with generation-interval mismatch **{base['generation']:.4f}→{win['generation']:.4f}** and trade mismatch **{base['trade']:.4f}→{win['trade']:.4f}**. The unrestricted price leader gives **{bestprice:.3f} EUR/MWh**; eligibility is reported below rather than hidden. The <10 EUR/MWh research target remains {'unmet' if win['price']>=10 else 'met for this in-sample reconstruction only'}.

This is **2025 in-sample reconstruction**, using all 2025 prices and generation to fit and select bids. Generation/trade agreement and independently checked physics are complementary evidence, **not independent forecast validation**. The primary rule retained **{len(members)}** bid state(s): **{', '.join(members)}**. Their min/max price envelope contains observed prices in **{100*mean_cover:.2f}%** of eligible zone-hours. This is descriptive coverage of a finite tested family, not a confidence interval or a posterior probability. The accepted baseline and browser scenario engine remain unchanged; these are experimental fits.

##1. What inverse market modelling means

Our forward problem takes supply bids, available generation, demand and network constraints, clears the system, and produces dispatch and balance-dual prices. The inverse problem asks which plausible bid parameters could explain observed outcomes while retaining that clearing mechanism.

In compact form, each hour solves $x_t(\\theta)\\in\\arg\\min_x c_t(\\theta)^T x$ under the same physical constraints; $p_t(\\theta)$ is its zonal balance-dual vector. Calibration compares $p_t(\\theta)$ and the resulting generation/trade quantities with observations. Observed prices never overwrite the cleared prices.

**Identification is the central difficulty.** A 100 EUR/MWh price might reflect a higher gas offer, less available cheap generation, or constrained imports. The same price can arise from different mechanisms with different investment responses. A resource that never influences prices is poorly identified by price data. Equal-price aggregation and LP dual nonuniqueness add ambiguity; national generation totals do not identify actual hourly plant dispatch.

[Chan, Mahmood and Zhu's review](https://arxiv.org/abs/2109.03920) explains inverse optimisation as estimating objectives or constraints that explain decisions. [Bertsimas, Gupta and Paschalidis](https://arxiv.org/abs/1308.3397) develop data-driven estimation from equilibrium observations. These motivate an optimisation-consistent approach, but do not establish that our approximate European market is the true data-generating mechanism.

[Liang and Dvorkin](https://arxiv.org/html/2302.05498v2) study marginal offer recovery from electricity-market clearing information. Their recovery guarantees depend on their assumptions and observable marginal behaviour; non-marginal offers remain unidentified. We have zonal prices and aggregated generation rather than complete plant-level clearing observations, so **we do not inherit their uniqueness or convergence guarantees**. [Birge, Hortaçsu and Pavlin's MISO study](https://doi.org/10.1287/opre.2017.1606) investigates constraint recovery from price outcomes under specified assumptions; it does not authorize freely tuning our physical network until prices match. [Babier et al.](https://doi.org/10.1287/ijoo.2019.0045) fit inverse models from multiple decisions; their ensemble-consensus framework differs from our finite set of near-best parameter fits.

**Implemented here:** a bounded two-round inverse-calibration heuristic, with actual full-year forward solves and an explicit near-best fit selection rule. It is not an exact global bilevel inverse optimisation, proof of actual bids, exhaustive solution distribution or strategic Nash-equilibrium model.

##2. Baseline model, sources and what stays fixed

The single accepted reference is `seasonal-calendar-v1/refit`: **48 modeled areas,145 physical buses,41 complete observed-price zones and all8,760 UTC hours of2025**. Separate Nordic and Italian zones are retained; geographic/source allocation proxies remain. Independent hourly sparse LPs minimize offered supply cost. Daily grouping does not add unit commitment, ramping, storage scheduling or complex block orders. This is EUPHEMIA-inspired synthetic clearing, not EUPHEMIA reproduction.

| Component | Source and treatment |
| --- | --- |
| Physical network and fleet | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0; PTDF/GSK, electrical islands, HVDC bounds/losses and0.7 branch-rating factor. Model-derived N-0 limits, not certified JAO commercial domains or explicit N-1 security. |
| Wind and solar | Original 2025 [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)/[atlite](https://atlite.readthedocs.io/) weather profiles, [IRENA](https://www.irena.org/Data) end2024/end2025 capacity interpolation. Assumed commissioning, generic turbines/panels and potential-based layouts; generation never replaces availability. |
| Demand | Prepared [ENTSO-E](https://transparency.entsoe.eu/)-based 2025 hourly demand, with regional allocation/scope proxies; fixed in every fit. |
| Hydro and nuclear availability | Retained fixed hourly reservoir schedule and source water/stock evidence; Norway uses NVE HBV/stock inputs. Nuclear retains the 2024 national energy-availability-factor proxy. No adaptive hydro or RTE availability change in this trial. |
| Bid anchors | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF/Brent, [ECB](https://data.ecb.europa.eu/) FX, source efficiency/VOM and80 EUR/t carbon assumption; accepted seasonal/local-clock and Ember bid correction. Delivered fuel and operational details remain imperfect. |
| Targets | Source-hashed ENTSO-E A44 hourly price aggregates; [Ember](https://ember-energy.org/data/) monthly national Wind/Solar/Nuclear/Gas/Coal generation and signed net exports. Unknown observations remain unknown. |

The five-fuel mix score excludes hydro, biomass and other generation; trade is **implied generation minus model demand**, not verified physical border flow. National/zone boundaries and gross/net reporting differ. Updated hourly zonal ENTSO-E A75 generation checks have not been derived for these inverse fits; prior baseline/OOF A75 evidence is separate. Passing the five-fuel national screen does not certify every zone or resource. Allocation points are proportional illustrations; conditional fuel/country bounds preserve saved group totals, are not jointly attainable bounds on all primal optima and do not identify real plant dispatch.

Recent source diagnostics remain separate: [wind/PV controls]({prefix}renewable-source-prices-by-zone.csv), [IRENA capacity audit]({prefix}renewable-capacity-audit.csv), [RTE nuclear controls]({prefix}nuclear-availability-prices-by-zone.csv), and [daily-fuel controls]({prefix}daily-fuel-prices-by-zone.csv). None was silently combined with this accepted-baseline comparison.

##3. Implemented search and safeguards

1. Start from the accepted annual witness and its exact offer grouping. Five features—constant, annual sine/cosine and first local-clock daily sine/cosine—propose smooth **zone/resource** gas, coal and nuclear bid corrections. Fit observed-minus-parent-price residuals only when that model has a local interior offer matching its saved zonal dual. Require168 supported hours and ridge336; clip fitting residuals at±100. An interior offer has neither generation bound active, so its marginal bid equals the local price in this formulation. Re-clearing is essential because the marginal offers and binding network constraints can change after a bid adjustment. This labels supporting model evidence, not unique real price setters. Unsupported groups receive zero proposals.
2. Add a national annual fuel-mix proposal only when all12 reference months exist. Underproduction outside the conditional annual allocation interval proposes a lower offer; overproduction proposes a higher offer. Each increment is bounded at±15 EUR/MWh and weighted into groups by original nameplate membership. It changes **bids, never availability**.
3. Accumulate the smooth/mix correction, capped at±45 EUR/MWh for gas/coal and ±15 for nuclear. Thermal block premiums are nonnegative and monotone, capped at 60 gas/40 coal on the upper block; intermediate premium is 35% of that. Nuclear has no peaking block. Final thermal/nuclear bids have a zero floor; renewable and all other bids stay unchanged. Bounds are declared experimental assumptions, not observed market bids or subsidy evidence.
4. Make exactly two rounds of six declared step tuples, at most12 new annual clears. Each round uses the best eligible completed state as parent. Identical bid hashes reuse their witness. There are no per-hour fitted prices, extra adaptive rounds or physical-constraint searches. The replay found supported zone/resource groups **{[r['supported_zone_resources'] for r in a['proposal_support']]}** across the two rounds; each supported group estimates five coefficients, plus bounded national fuel signals.
5. Score every unique state using **55% normalized price MAE +20% normalized daily-demeaned price MAE +20% normalized generation-interval error +5% normalized trade-interval error**, plus0.01 times availability-weighted squared bid departure. Normalization uses the accepted baseline. A research-eligible state must not increase price MAE, may increase each other score by at most2%, and must clear all hours with zero emergency. These are predeclared trial filters, **not empirical product acceptance gates**.
6. Retain at most five distinct eligible bid states within0.01 of the best regularized score and1 EUR/MWh of that score winner's MAE. Keep the score winner first, then choose diverse normalized parameter vectors. Equal weights are descriptive; we do not infer a likelihood or assign posterior probabilities. The baseline can remain a member, and the set can collapse to one if alternatives fail.

The complete [predeclared design](config/inverse-bid-ensemble-2025.json) fixes every step, bound and filter before outcomes. The continuous inverse problem is nonsmooth and nonconvex through changing active constraints. Hourly LP optimality is independently checked; **there is no outer-search global-optimum or convergence certificate**.

##4. Full-year results and model distribution

| State | Price MAE | Mean zonal r | Within-day MAE | Generation score | Trade score | Eligible? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{table}

Price errors are EUR/MWh. Scores for generation/trade are normalized interval discrepancies, not total-fleet percentage errors. Trial IDs describe steps in the same solver: `r2-s6` means round 2, step 6, not a separate network implementation. The joint fit reaches gas/coal upper-block premiums **{winner_tops[0]:.0f}/{winner_tops[1]:.0f} EUR/MWh**; the price-focused fit reaches **{leader_tops[0]:.0f}/{leader_tops[1]:.0f}**. Both also change bounded smooth/mix bid terms; neither changes available generation. **{len(elig)}/{len(records)}** unique states pass the research filters. The table contains the anchor, every retained member and the overall price leader; [all search states]({prefix}inverse-search-cases.csv) include excluded cases and exact parent/step provenance.

![All search states: price and generation trade-offs]({prefix}overview.png)

The retained states are alternative explanations **within one unchanged physical network**, not randomly perturbed networks centered on observations. A narrow envelope can simply mean that the tested bid family misses the same price movements. Coverage of **{100*mean_cover:.2f}%** is reported rather than assuming the observed market lies inside the fit distribution. With one member, the envelope has zero width and coverage becomes an approximate numerical equality count, not useful uncertainty quantification. Envelope width excludes uncertainty from weather, capacity, demand scope, network structure and missing market mechanisms. Averaged ensemble prices are not prices from a single cleared system, and are not the primary model metric.

**Post-run cutoff diagnostic, not a change to primary selection:** applying wider score tolerances to the same completed states gives the counts below, keeping all other filters and the 1 EUR/MWh limit. No additional solve or primary-member substitution is made. This shows dependence on the analyst's tolerance; it does not establish probabilities. A second diagnostic uses **all {len(eligible_ids)} research-eligible states**, without the near-best score cutoff. That wider min/max envelope spans observed prices in **{100*broad_cover:.2f}%** of eligible zone-hours, with mean width **{broad_width:.2f} EUR/MWh**. Even this broader family is far from bracketing the observed market; the orange band below is not the primary retained ensemble or a confidence interval.

| Score tolerance above winner | Qualifying states | Maximum retained after five-member cap |
| --- | ---: | ---: |
{sensitivity_table}

![Per-zone price MAE for baseline, retained members and price leader]({prefix}zone-mae-grid.png)

All48 areas appear; seven lack complete observed-price series and remain gray. Negative and extreme observations remain in all eligible-zone annual metrics. No zone or failed hour is removed to improve a headline.

### Norway, Germany, Spain and France

Improvements are not uniform: the score winner improves Germany and Spain, but worsens France and NO3/NO4. The all-zone table/grid retain those regressions. Better aggregate generation scores likewise do not establish improvement in every country/fuel.

| Zone | Baseline MAE | Score winner MAE | Baseline r | Score winner r |
| --- | ---: | ---: | ---: | ---: |
{examples}

**Where the inverse proposals have leverage.** The last proposal used parent **{s['proposals'][1]['parent']}**. Its local interior supporting-hour counts are below; fewer than 168 hours means no local price proposal for that zone/resource.

| Zone | Gas | Coal | Nuclear |
| --- | ---: | ---: | ---: |
{support_table}

All Norwegian groups are below the threshold. Thermal bids there therefore have no directly fitted local price adjustment in this design; cross-border changes can still affect prices. Fixed hydro is an injection, not an adjustable water offer. Expanding a thermal bid search cannot by itself identify missing local price formation. Germany, Spain and France have much stronger supporting model evidence, without proving which actual generators set observed prices.

![Fixed example week: observed prices, baseline and retained-fit envelope]({prefix}daily-prices.png)

The illustration always uses **1–7 July 2025 UTC**; all headline metrics use the full year. NO5 is a price example, not an assertion of complete NO5 generation observations. The five Norwegian zones remain separate in price comparisons; national generation is checked separately below.

![National five-fuel generation comparison with Ember]({prefix}national-mix.png)

Whiskers show conditional saved-group allocation bounds, not probabilistic confidence. The [national generation download]({prefix}inverse-generation-by-country.csv) preserves every shown model/country/fuel, reporting coverage and signed TWh differences. Missing annual references stay blank; they are not summed as zero. The [per-zone price download]({prefix}inverse-prices-by-zone.csv) includes bias, correlation, tails, negative-hour and daily-shape diagnostics plus envelope coverage.

##5. What this means for investment scenarios

The experiment supports a way to keep several admissible bid explanations when the observations do not uniquely identify one. It does **not** yet estimate investment benefits. For each future ensemble member, compare its own baseline with the same model plus the asset, preserving common exogenous inputs and physical chronology. Report distributions of system-cost change, emissions, congestion rent and asset revenue separately; system savings are not investor income. Calibrated offer costs include effective premiums: their objective is not verified physical production cost or economic welfare. Revalue dispatch with independently sourced resource costs/emissions when estimating economic impacts; keep cleared-price revenues and transfers separate.

A project that looks valuable across credible fits is more robust to this tested bid uncertainty. A project whose sign changes between fits needs further investigation. Neither conclusion establishes robustness to structural model error. Fixed hydro cannot change its water schedule after an investment; this can bias results in either direction. Adaptive hydro/storage would require the separate verified chronology and strategy work. The live browser remains the older two-node line/battery screen.

##6. Conclusion, limitations and reproduction

The useful result is the **joint price/mix trade-off and the retained set**, not a claim that fitting prices recovers the real European order book. The score-winning MAE is **{win['price']:.3f}**, versus the target below10. Capacity/site weather, operational availability, bid constraints, reporting scope and Nordic fixed-injection/network price formation remain possible sources of error. Effective fitted bids can compensate for these errors. The nonnegative thermal floor and unchanged zero renewable offers also restrict negative-price mechanisms; keeping negative observations in the score does not make those mechanisms identifiable. Wind/solar excess cannot automatically be repaired by changing thermal bids. This finite search neither exhausts plausible bids nor rules out better model formulations.

All2025 observations inform this reconstruction and its selection. Independent physics and generation consistency do not turn it into a forecast backtest. Any forecasting claim needs separately designed out-of-sample evaluation; investment claims need paired forward scenarios and their acceptance checks. There is no automatic baseline promotion.

Independent replay verifies **{len(a['certificates'])} complete annual witnesses**, all inverse proposals, bounded costs, physical invariance, original component physics, primal/dual objectives, full price/monthly mix/trade metrics, both round-parent selections, duplicates and diversity-based ensemble membership. Maximum native-component residual is **{physical:.3g} MW** and maximum duality gap **EUR {gap:.6f}**. All unique states have8,760 optimal hours and zero emergency supply. Fresh clearing loops total **{seconds:.2f}s**; preparation **{s['preparation_seconds']:.2f}s**, complete search **{s['end_to_end_seconds']:.2f}s**, peak RSS **{s['peak_rss_mib']:.0f} MiB**. The baseline is reused intact, not counted as a fresh clear.

To reproduce with the pinned local source caches: hydrate the four immutable model-metadata archives with `python3 tools/pack_model_metadata.py --restore`; use the pinned Python at `data/pypsa-eur/upstream/.pixi/envs/default/bin/python` to run the finite driver into a **fresh ignored output directory**, then the independent auditor on that directory. Set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1`. The runner enforces a 5 GiB address-space limit, 40-minute alarm and one process/lock. Existing output directories are never implicitly resumed. A fresh checkout without the authorized large source caches cannot reproduce numerical results from the small public report assets alone.

Implementation: [inverse proposals and selection](tools/inverse_bid_ensemble_2025.py), [finite driver](tools/run_inverse_bid_ensemble_2025.py), [independent replay](tools/audit_inverse_bid_ensemble_2025.py), [report renderer](tools/bid_ensemble_report_2025.py), and [compact provenance receipt]({prefix}summary.json). Large source inputs, hourly witnesses and proposal arrays remain ignored locally. Prior seasonal out-of-fold evidence remains in its downloads and explicitly labelled legacy receipt fields; it is not this all-year fitted ensemble.
'''
    # Readable spacing around numbers in prose; no change to mathematical/data values.
    for old,new in [('European2025','European 2025'),('##1.','## 1.'),('##2.','## 2.'),('##3.','## 3.'),('##4.','## 4.'),('##5.','## 5.'),('##6.','## 6.'),('all 2025','all 2025'),('All2025','All 2025'),('all8,760','all 8,760'),('all48','all 48'),('All48','All 48'),('all12','all 12'),('all 2025','all 2025'),('an100','an 100'),('A100','A 100'),('at±','at ±'),('at60','at 60'),('at168','at 168'),('Require168','Require 168'),('ridge336','ridge 336'),('plus0.01','plus 0.01'),('within0.01','within 0.01'),('and1 EUR','and 1 EUR'),('at most12','at most 12'),('at most2%','at most 2%'),('of2025','of 2025'),('original2025','original 2025'),('end2024/end2025','end-2024/end-2025'),('factor. Nuclear retains the 2024','factor. Nuclear retains the 2024'),('and80 EUR','and 80 EUR'),('and0.7','and 0.7'),('at±100','at ±100'),('on2025','on 2025'),('areas,145','areas, 145'),('buses,41','buses, 41'),('all41','all 41'),('have8,760','have 8,760'),('below10','below 10'),('EUR{','EUR {')]:report=report.replace(old,new)
    receipt=dict(summary_sha256=digest(folder/'summary.json'),audit=a,design=s['design'],producer_sha256=s['producer_sha256'],helper_sha256=s['dependencies']['inverse_bid_ensemble_2025.py'],renderer_sha256=digest(__file__),winner=winner,price_leader=leader,members=members,shown=shown,records=s['records'],cutoff_sensitivity=sensitivity,coverage=s['coverage'],all_eligible_ids=eligible_ids,all_eligible_coverage=broad,equal_zone_all_eligible_coverage=broad_cover,mean_all_eligible_width_eur_mwh=broad_width,equal_zone_envelope_coverage=mean_cover,annuals=s['annuals'],parameter_hashes=s['parameter_hashes'],preparation_seconds=s['preparation_seconds'],end_to_end_seconds=s['end_to_end_seconds'],peak_rss_mib=s['peak_rss_mib'])
    return report,receipt
