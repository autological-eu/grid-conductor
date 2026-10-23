"""Observed LP evaluation and explicit normalized-node curve figures."""
import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse import load_npz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sigmoid_month_pairs_2025 import ROOT,OUT as SOURCE,FAMILIES,EMBER,digest,split
from supply_knot_splines_2025 import KNOTS,spline,initial_parameters
from run_supply_knots_lp_2025 import OUT,PLAN


def csvfile(path,rows):
    if not rows:return
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def run():
    dest=ROOT/'research';summary=json.loads((OUT/'summary.json').read_text());layout=json.loads((OUT/'layout.json').read_text());design=json.loads(PLAN.read_text())
    audit_path=OUT/'audit.json';audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
    with np.load(SOURCE/'inputs.npz') as z:observed=z['observed_prices'];ember=z['ember'];accepted=z['accepted_prices'];capacity=z['capacity'];source_cost=z['source_cost'];features=z['features'];fixed_generation=z['fixed_generation']
    source=json.loads((SOURCE/'inputs.json').read_text());complete=np.isfinite(observed).all(axis=0);allhours=[];pred={k:[] for k in ['control','learned']};monthly_rows=[];fold_rows=[]
    mapping=np.array(layout['mapping']);nsource=len(mapping);ncurve=layout['count'];ntech=len(source['technologies']);ncountry=len(source['countries'])
    membership=csr_matrix((np.ones(nsource),(np.arange(nsource),mapping)),shape=(nsource,ncurve))
    destinations=[g['country_id']*ntech+source['technologies'].index(g['technology']) for g in source['groups']]
    attribution=csr_matrix((np.ones(nsource),(np.arange(nsource),destinations)),shape=(nsource,ncountry*ntech));allocation_error=0.;allocation_hours=0
    zero_groups=[];native_matrix=load_npz(SOURCE/'network.npz')
    for zone in source['zones']:
        ids=[j for j,g in enumerate(layout['groups']) if g['zone']==zone and g['technology'] in design['zero_economic_bid']]
        if len(ids)<2:continue
        columns=[int(np.flatnonzero(mapping==j)[0])*source['design']['segments'] for j in ids]
        if any((native_matrix[:,c]-native_matrix[:,columns[0]]).nnz for c in columns):raise ValueError('Zero-price offers differ physically; cannot assume interchangeable')
        zero_groups.append(ids)
    sensitivity_rows=[]
    family_error={k:{f:[] for f in FAMILIES} for k in pred};family_normal={k:{f:[] for f in FAMILIES} for k in pred};mixshares={k:[] for k in pred}
    for pair in summary['pairs']:
        _,hours=split(pair['train'],pair['test']);allhours.extend(hours)
        fold=dict(train=pair['train'],test=pair['test'],hours=len(hours))
        for kind in pred:
            record=pair['cases'][kind];metrics=record['metrics'];fold.update({kind+'_'+key:value for key,value in metrics.items()})
            with np.load(OUT/f"test-{pair['test']:02d}-{kind}.npz") as z:
                pred[kind].append(z['row_duals'][:,:source['nz']])
                # Independent sparse attribution, not the producer's group loop.
                pooled=capacity[hours]@membership;denom=pooled[:,mapping]
                shares=np.divide(capacity[hours],denom,out=np.zeros_like(denom),where=denom>0)
                reconstructed=((z['quantities'][:,mapping]*shares)@attribution).reshape(len(hours),ncountry,ntech)+fixed_generation[hours]
                error=float(abs(reconstructed-z['generation']).max());allocation_error=max(allocation_error,error);allocation_hours+=len(hours)
                if error>1e-7:raise ValueError('Independent country/technology allocation mismatch')
                # A second, equally optimal zero-bid allocation. Do not alter
                # saved witnesses or select the better-looking observed score.
                alternative=z['quantities'].copy();curtailed=0
                for ids in zero_groups:
                    available=pooled[:,ids];total=available.sum(axis=1);output=alternative[:,ids].sum(axis=1)
                    replacement=np.divide(output[:,None]*available,total[:,None],out=np.zeros_like(available),where=total[:,None]>0)
                    if abs(replacement.sum(axis=1)-output).max()>1e-7 or np.maximum(replacement-available,0).max()>1e-4:raise ValueError('Invalid proportional zero-bid allocation')
                    curtailed+=int(((output<total-1e-4)&(output>1e-4)).sum());alternative[:,ids]=replacement
                altgen=((alternative[:,mapping]*shares)@attribution).reshape(len(hours),ncountry,ntech)+fixed_generation[hours]
                altmonthly=np.column_stack([altgen[:,:,[source['technologies'].index(t) for t in EMBER[f]]].sum(axis=(0,2))/1e6 for f in FAMILIES])
                ref=ember[pair['test']-1];known=np.isfinite(ref)
                sensitivity_rows.append(dict(case=kind,month=pair['test'],known_cells=int(known.sum()),raw_generation_mae_twh=metrics['generation_mae_twh'],
                    proportional_generation_mae_twh=float(abs(altmonthly[known]-ref[known]).mean()),max_hourly_country_technology_difference_mw=float(abs(altgen-reconstructed).max()),
                    nonunique_zero_bid_zone_hours=curtailed))
            monthly=np.array(record['monthly_generation_twh']);obs=ember[pair['test']-1]
            full=np.isfinite(obs).all(axis=1)&(obs.sum(axis=1)>0)&(monthly.sum(axis=1)>0)
            for ci in np.flatnonzero(full):mixshares[kind].extend((100*abs(monthly[ci]/monthly[ci].sum()-obs[ci]/obs[ci].sum())).tolist())
            for ci,country in enumerate(source['countries']):
                for f,family in enumerate(FAMILIES):
                    if np.isfinite(obs[ci,f]):
                        err=abs(monthly[ci,f]-obs[ci,f]);family_error[kind][family].append(err);family_normal[kind][family].append(err/max(obs[ci,f],.25))
                        monthly_rows.append(dict(case=kind,month=pair['test'],country=country,family=family,observed_twh=float(obs[ci,f]),modeled_twh=float(monthly[ci,f]),absolute_error_twh=float(err)))
        fold_rows.append(fold)
    hours=np.array(allhours);target=observed[hours];scores={k:float(abs(np.concatenate(pred[k])[:,complete]-target[:,complete]).mean()) for k in pred}
    gen_scores={k:float(np.mean([x for ff in family_error[k].values() for x in ff])) for k in pred};norm_scores={k:float(np.mean([x for ff in family_normal[k].values() for x in ff])) for k in pred}
    zone_rows=[]
    for zi,zone in enumerate(source['zones']):
        valid=np.isfinite(target[:,zi]);row=dict(zone=zone,observed_hours=int(valid.sum()),eligible_all_year=bool(complete[zi]))
        for kind in pred:
            pp=np.concatenate(pred[kind])[:,zi];row[kind+'_mae_eur_mwh']=float(abs(pp[valid]-target[valid,zi]).mean()) if valid.any() else ''
            row[kind+'_bias_eur_mwh']=float((pp[valid]-target[valid,zi]).mean()) if valid.any() else ''
            row[kind+'_correlation']=float(np.corrcoef(pp[valid],target[valid,zi])[0,1]) if valid.sum()>1 and np.std(pp[valid])>0 else ''
        row['learned_minus_control_mae']=row['learned_mae_eur_mwh']-row['control_mae_eur_mwh'] if valid.any() else '';zone_rows.append(row)
    wide={}
    for row in monthly_rows:
        key=(row['month'],row['country'],row['family'])
        item=wide.setdefault(key,{k:row[k] for k in ['month','country','family','observed_twh']})
        for field in ['modeled_twh','absolute_error_twh']:item[row['case']+'_'+field]=row[field]
    csvfile(dest/'supply-knots-lp-2025-folds.csv',fold_rows);csvfile(dest/'supply-knots-lp-2025-zones.csv',zone_rows);csvfile(dest/'supply-knots-lp-2025-generation.csv',list(wide.values()))
    band_rows=[]
    bands=[('negative',-np.inf,0),('0_to_50',0,50),('50_to_100',50,100),('100_to_200',100,200),('200_to_500',200,500),('500_plus',500,np.inf)]
    for label,low,high in bands:
        tt=target[:,complete];mask=(tt>=low)&(tt<high)
        if not mask.any():continue
        row=dict(observed_price_band=label,zone_hours=int(mask.sum()),observed_mean_eur_mwh=float(tt[mask].mean()))
        for kind in pred:
            pp=np.concatenate(pred[kind])[:,complete];row[kind+'_mae_eur_mwh']=float(abs(pp[mask]-tt[mask]).mean())
        band_rows.append(row)
    csvfile(dest/'supply-knots-lp-2025-price-bands.csv',band_rows)
    spike=next((r for r in band_rows if r['observed_price_band']=='500_plus'),None)
    tails_text=f"Price-spike recovery remains poor: the {spike['zone_hours']} zone-hours above €500/MWh have fitted MAE €{spike['learned_mae_eur_mwh']:.2f}/MWh, versus €{spike['control_mae_eur_mwh']:.2f}/MWh neutral." if spike else 'No observed price above €500/MWh occurs in this evaluation scope.'
    csvfile(dest/'supply-knots-lp-2025-allocation-sensitivity.csv',sensitivity_rows)
    proportional={kind:sum(r['known_cells']*r['proportional_generation_mae_twh'] for r in sensitivity_rows if r['case']==kind)/sum(r['known_cells'] for r in sensitivity_rows if r['case']==kind) for kind in pred}
    plt.rcParams.update({'svg.fonttype':'none','font.size':9})
    eligible=[r for r in zone_rows if r['eligible_all_year']];grid=np.full((6,7),np.nan);labels={}
    for i,row in enumerate(eligible):
        r,c=divmod(i,7);grid[r,c]=row['learned_mae_eur_mwh'];labels[(r,c)]=f"{row['zone']}\n€{row['learned_mae_eur_mwh']:.1f}\nΔ{row['learned_minus_control_mae']:+.1f}"
    fig,ax=plt.subplots(figsize=(9,6));im=ax.imshow(grid,cmap='YlOrRd');ax.set_xticks([]);ax.set_yticks([])
    threshold=np.nanmin(grid)+.6*(np.nanmax(grid)-np.nanmin(grid))
    for (r,c),label in labels.items():ax.text(c,r,label,ha='center',va='center',fontsize=9,color='white' if grid[r,c]>threshold else 'black')
    ax.set_title(f"LP price MAE · {len(hours)} evaluation hours\nΔ is learned minus same-input neutral control; negative is better")
    fig.colorbar(im,ax=ax,label='EUR/MWh',shrink=.7);fig.tight_layout();fig.savefig(dest/'supply-knots-lp-2025-zone-mae.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4));x=np.arange(len(FAMILIES));family_rows=[]
    for kind,offset,color in [('control',-.18,'#7c8ca2'),('learned',.18,'#146b84')]:
        vals=[np.mean(family_error[kind][f]) for f in FAMILIES];ax.bar(x+offset,vals,.35,label=kind,color=color)
        for f,v in zip(FAMILIES,vals):family_rows.append(dict(case=kind,family=f,monthly_generation_mae_twh=float(v),known_cells=len(family_error[kind][f])))
    ax.set_xticks(x,FAMILIES,rotation=25,ha='right');ax.set(ylabel='Mean absolute monthly error (TWh)',title='Generation errors against original Ember monthly national cells');ax.legend();fig.tight_layout();fig.savefig(dest/'supply-knots-lp-2025-generation.svg');plt.close(fig);csvfile(dest/'supply-knots-lp-2025-families.csv',family_rows)
    # January fit, February physical example; no February target enters curve construction.
    theta=np.array(json.loads((OUT/'proposal-01.json').read_text())['theta']);neutral=initial_parameters(len(theta));hour=1092
    fig,axes=plt.subplots(2,3,figsize=(11,6));curve_rows=[]
    u=np.linspace(0,1,301)
    for ax,tech in zip(axes.flat,['gas','hard_coal','lignite','oil','biomass','solar']):
        c=next((j for j,g in enumerate(layout['groups']) if g['zone']=='DE-LU' and g['technology']==tech),None)
        if c is None:ax.set_title(tech+' — absent');continue
        ids=np.flatnonzero(np.array(layout['mapping'])==c);av=capacity[hour,ids].sum();anchor=float(capacity[hour,ids]@source_cost[hour,ids]/av) if av>0 else 0.;g=layout['groups'][c];zero=tech in design['zero_economic_bid']
        for name,state in [('Neutral',neutral),('Learned',theta)]:
            par=state[c];inc=.001+20*np.logaddexp(0,par[5:]);shift=80*np.tanh(features[hour,g['zone_id']]@par[:5]/4)
            pp=np.zeros(len(u)) if zero else anchor+shift+spline(u,np.repeat(inc[None,:],len(u),axis=0))[0]
            ax.plot(u*100,pp,label=name,color='#146b84' if name=='Learned' else '#7c8ca2')
            nodal=np.zeros(6) if zero else anchor+shift+spline(KNOTS,np.repeat(inc[None,:],6,axis=0))[0]
            ax.scatter(KNOTS*100,nodal,s=17,zorder=3)
            if name=='Learned':
                edges=np.linspace(0,1,design['lp_tranches_per_curve']+1)
                interval=np.zeros(len(edges)-1) if zero else anchor+shift+np.diff(spline(edges,np.repeat(inc[None,:],len(edges),axis=0))[1])*design['lp_tranches_per_curve']
                ax.stairs(interval,edges*100,color='#39a7b2',linewidth=.7,alpha=.7,label='LP offers',baseline=None)
            for fraction,price in zip(KNOTS,nodal):curve_rows.append(dict(zone='DE-LU',technology=tech,curve=name,hour=hour,supply_fraction=float(round(fraction,2)),available_mw=float(av),offered_mw=float(fraction*av),bid_eur_mwh=float(price)))
        ax.set(title=f'{tech} · {av/1000:.2f} GW available',xlabel='Available supply (%)',ylabel='Economic bid (EUR/MWh)');ax.set_xticks(KNOTS*100);ax.grid(alpha=.15)
    axes.flat[0].legend();fig.suptitle('DE-LU · 15 February 2025 12:00 UTC · January-only fitted knots');fig.tight_layout();fig.savefig(dest/'supply-knots-lp-2025-curves.svg');fig.savefig('/tmp/grid-supply-knots-curves.png',dpi=130);plt.close(fig);csvfile(dest/'supply-knots-lp-2025-curves.csv',curve_rows)
    improved=sum(r['learned_minus_control_mae']<0 for r in eligible);worse=[r for r in eligible if r['learned_minus_control_mae']>=0]
    rows=['| Test month | Neutral price MAE | Fitted price MAE | Neutral generation MAE | Fitted generation MAE |','|---|---:|---:|---:|---:|']
    for pair in summary['pairs']:
        c=pair['cases']['control']['metrics'];l=pair['cases']['learned']['metrics'];rows.append(f"| {pair['test']:02d} | {c['price_mae']:.2f} | {l['price_mae']:.2f} | {c['generation_mae_twh']:.4f} | {l['generation_mae_twh']:.4f} |")
    pilot=json.loads((ROOT/'data/bidding-zone-network-2025/supply-knots-lp-pilot-v1/summary.json').read_text())
    lp_seconds=sum(case['info']['seconds'] for pair in summary['pairs'] for case in pair['cases'].values());fit_seconds=sum(json.loads((OUT/f"proposal-{pair['train']:02d}.json").read_text())['history'][-1]['seconds'] for pair in summary['pairs'])
    baseline=float(abs(accepted[hours][:,complete]-target[:,complete]).mean());status='Complete and independently audited.' if audit and summary['status']=='complete' else 'Partial or audit pending; do not treat these results as fully verified.'
    prior_summary=json.loads((SOURCE/'summary.json').read_text());tested={p['test'] for p in summary['pairs']};prior_pairs=[p for p in prior_summary['pairs'] if p['test_month'] in tested]
    prior_score=sum(p['test_hours']*p['test_selected']['price_mae'] for p in prior_pairs)/sum(p['test_hours'] for p in prior_pairs)
    prior_gen=sum(p['test_selected']['generation_cells']*p['test_selected']['generation_mae_twh'] for p in prior_pairs)/sum(p['test_selected']['generation_cells'] for p in prior_pairs)
    known_cells=sum(p['cases']['learned']['metrics']['generation_cells'] for p in summary['pairs']);countries=len({r['country'] for r in monthly_rows})
    now=datetime.now(ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M %Z')
    transfer_path=OUT/'transfer.json';transfer=json.loads(transfer_path.read_text()) if transfer_path.exists() else None
    transfer_text='Full smooth-to-LP transfer checks and selected-training-loss replays are pending.'
    if transfer:
        mean_difference=np.mean([r['mean_price_difference_eur_mwh'] for r in transfer['pairs']]);maximum=max(r['max_price_difference_eur_mwh'] for r in transfer['pairs'])
        transfer_text=f"Across all96 selected training hours, smooth-to-LP price differences average €{mean_difference:.3f}/MWh and reach €{maximum:.2f}/MWh. All six selected training losses replay; poisoning all other months' observation targets leaves the loss and derivatives identical. These checks do not establish annual approximation convergence."
    orchestration_path=OUT/'orchestration.json';orchestration=json.loads(orchestration_path.read_text()) if orchestration_path.exists() else None
    runtime_text=f"Sum of per-fold final fitting-session timers: **{fit_seconds:.1f}s** (resumed prefixes may be recorded separately). LP compilation/clearing/certificate time for both cases across completed pairs: **{lp_seconds:.1f}s**."
    if orchestration and orchestration.get('status')=='all_original_LP_pairs_complete':
        runtime_text=f"Measured active job wall time, including the checkpointed first phase and two-worker continuation: **{orchestration['total_active_job_wall_seconds']:.1f}s**. The continuation's parallel fitting phase took **{orchestration['parallel_stage_seconds']:.1f}s**. Summed LP compilation/clearing/certificate time for both cases: **{lp_seconds:.1f}s**. Fitting, independent audits and transfer checks overlapped; these timings are not additive."
    text=f'''# Six supply-level spline knots in the original LP model

{now}. **{status}** Research candidate; accepted model and public explorer unchanged.

## Summary

The model fits marginal prices at **0%,20%,40%,60%,80% and100%** of available technology output in each bidding zone. It then clears those bids in the original linear-programming model. Over **{len(hours)} even-month hours/{int(complete.sum())} complete price zones**, fitted LP price MAE is **€{scores['learned']:.3f}/MWh**, versus **€{scores['control']:.3f}/MWh** for the same-input unfitted control. Monthly generation MAE is **{gen_scores['learned']:.4f} TWh**, versus **{gen_scores['control']:.4f} TWh**; normalized errors are **{norm_scores['learned']:.4f}** and **{norm_scores['control']:.4f}**. Generation coverage: {known_cells} known Ember cells/{countries} countries.

These are actual LP cleared-price and generated-energy scores, not spline regression error or sampled training loss. The comparison evaluates fitting under one common pooling/control design; it does not isolate the benefit of six-node splines over the old sigmoid family. Six even months are not an8760-hour out-of-fold year, and2025 has been inspected before.

## Model: what changes and what stays

There are **326 technology/bidding-zone curves**. Five positive price increments set the six nodes, and monotone cubic Hermite interpolation (PCHIP) connects them. Unequal increments permit several changes in curvature, while keeping higher cumulative output no cheaper than lower output. Five additional local-clock coefficients move the midpoint through the day. Hourly availability scales the horizontal axis, and hourly source costs anchor the vertical axis. Parameters are shared within a month, not independently fitted for every hour.

The earlier I-spline also allowed curvature. Six explicit interpolation nodes make the requested supply levels direct parameters; this change alone does not establish greater expressiveness or accuracy. Zone-specific parameter sharing also differs from the earlier national sharing.

Wind, solar and run-of-river keep zero economic bids. Reservoir hydro keeps its original fixed hourly injections; this experiment adds no storage fleet or water rescheduling. The original fixed demand, branch constraints, GSK/ratings, link bounds and all physical MW are retained. Only technology columns with identical network coefficients are pooled; pooling error is {layout['capacity_partition_error_mw']:.2g} MW.

Pooling produces a genuine technology-zone supply curve. Its source-cost anchor is the hourly availability-weighted mean of its original source groups. This replaces their separate cost anchors and is a substantive modelling assumption. National generation from a mixed-country curve is attributed in original available-capacity proportions. This is an illustrative allocation, not independently identified plant/country dispatch. Both fitted and neutral controls use the same pooling and allocation, so their difference does not reward a change in bookkeeping.

## Fitting and original-LP inference

Each odd month initializes from only its own earlier saved smooth-spline fit, resampled at the six nodes. Eight additional Adam updates use implicit gradients of constrained **smooth** clearing on a fixed16-hour sample. The joint loss includes prices, sample-expanded monthly generation and a small ridge; normalized generation errors divide by max(observed,0.25 TWh), not an unqualified percentage error. The minimum training-loss proposal freezes before the following even month's observations are scored. This is a bounded exploratory fit, not a converged full-month optimization. More parameters with only16 sampled hours can remain underidentified.

The monotone cubic curve is continuously differentiable in supply volume. Local gradients in its node parameters use the explicit cubic formulas; PCHIP's endpoint-slope clipping is only piecewise differentiable in parameters. Local gradient tests cover the evaluated cases, not every clipping/active-constraint transition.

The original HiGHS **LP** represents each smooth bid with20 divisible equal-volume tranches. Each tranche price is the exact average of the economic spline over its volume interval. Total offered MW equals available MW; the economic LP has no quadratic tie-break. The smooth training solver's small curvature regularizer is not included in LP bids. Gradient descent therefore trains a smooth surrogate; the reported scores measure its actual transfer to LP clearing. Hard LP prices/allocations are not globally differentiable, and discrete offer transitions can change them.

{transfer_text}

![Learned nodes scaled to hourly technology availability](supply-knots-lp-2025-curves.svg)

Dots mark the six actual nodal prices; available GW is shown separately. [Nodal data](supply-knots-lp-2025-curves.csv). More knots allow curvature but do not require visually wiggly curves: technologies that are always out of merit or fully dispatched may leave parts of the bid curve weakly identified. The figure uses February physical inputs with January-only fitted parameters; no February prices construct these offers.

## LP price and generation results

Price units are EUR/MWh; generation units are mean absolute monthly TWh per known national/resource cell.

{chr(10).join(rows)}

![Per-zone fitted LP price MAE](supply-knots-lp-2025-zone-mae.svg)

{improved}/{len(eligible)} complete price zones improve against the neutral control. Zones without an improvement: {', '.join(r['zone'] for r in worse) or 'none'}. [All48 zones, observed-hour coverage, MAE, bias and correlation](supply-knots-lp-2025-zones.csv). The accepted full-year-fitted model scores €{baseline:.3f}/MWh on these hours, as **in-sample context**, not a held-out competitor.

Headline price MAE weights every covered zone/hour equally; it is not demand-weighted. The seven zones without complete annual observed-price coverage remain in the network and are reported separately with their actual coverage.

[Errors by observed-price band, including negative prices and price spikes](supply-knots-lp-2025-price-bands.csv) retain the price-variance cases that an overall MAE can hide.

{tails_text} Overall improvement does not establish adequate capture of extreme variability. Solar monthly generation MAE also worsens slightly against neutral; the resource plot retains that adverse result.

The earlier odd/even-month sigmoid candidate scores €{prior_score:.3f}/MWh and {prior_gen:.4f} TWh monthly generation MAE on these same test months. That is another retrospective held-out result, but it used full odd-month fitting, shared national parameters, separate source-cost groups and different renewable bids. The new study changes all these assumptions together; it is not a controlled curve-family superiority test.

![Monthly national technology generation errors](supply-knots-lp-2025-generation.svg)

[All observed/model monthly generation cells](supply-knots-lp-2025-generation.csv), [resource summary](supply-knots-lp-2025-families.csv), [fold scores](supply-knots-lp-2025-folds.csv). Missing observations remain unknown. Generation-share MAE, restricted to complete nine-family country/months, is {np.mean(mixshares['learned']):.2f} percentage points fitted versus {np.mean(mixshares['control']):.2f} neutral; this narrower score does not cover all national scopes.

**Generation allocation is not always unique.** Zero-priced wind, solar and run-of-river offers with identical physical columns can exchange curtailed output without changing cost, zonal supply, prices or network feasibility. The headline generation errors describe the saved LP allocation. An equally optimal allocation that curtails these zero-bid resources proportionally to availability gives monthly generation MAE **{proportional['learned']:.4f} TWh fitted/{proportional['control']:.4f} TWh neutral**. This is a sensitivity check, not a selected improvement or a change to saved dispatch. [Per-fold ambiguity and allocation differences](supply-knots-lp-2025-allocation-sensitivity.csv). Source-column interchangeability, unchanged zonal totals and capacity bounds are explicitly verified.

## Sources and verification

The sealed [source experiment](sigmoid-month-pairs-2025.md) supplies original hourly ENTSO-E SDAC prices/demand, original Ember monthly national generation, capacities/availability and source costs. No new external data or annual target-fitted PV/bid coefficients are introduced. Fixed reservoir, historical grid and perfect-input assumptions remain conditional retrospective limitations. Generation and day-ahead auction data describe different source/market scopes; IRENA capacity is not hourly generated energy.

Five focused tests pass, including nodal interpolation against SciPy, monotonicity/integrated costs, joint clearing gradients, exact zero-renewable LP bids and mixed-country generation-loss derivatives. A European knot-shape adjoint check differs from finite differences by {pilot['gradient']['absolute_error']:.3g}. All72 January pilot LP hours pass original feasibility/economic gates.20vs40 tranches differ by a mean €{pilot['lp_resolution'][-1]['mean_price_difference_from_previous']:.3f}/MWh in that pilot; annual discretization convergence is not established.

Independent auditing reconstructs economic costs with SciPy PCHIP, rather than the producer's interpolation implementation, then replays saved primal/dual LP certificates, quantities, source allocations, source observations, fold boundaries and scores. Audit status: **{audit['status'] if audit else 'pending'}**. Original gates remain1e-4 MW physical residual and€0.05 objective/complementarity error, with zero artificial emergency dispatch.

The report also independently reconstructs national technology allocation using sparse source-membership/attribution matrices, rather than the producer's allocation loop: {allocation_hours} witness hours checked, maximum discrepancy {allocation_error:.3g} MW.

{runtime_text} These cover the listed month pairs, not measured annual runtime. Source loading/reporting and any pre-existing warm-initializer fit should not be mistaken for fresh inference time. Full hourly witnesses stay ignored locally; only compact reports, figures and score CSVs enter Git.

## Conclusion

The requested six-node curves work as ordinary LP offers. Fitting improves price and generation errors against the matching neutral control in every test month. However, the **€{scores['learned']:.3f}/MWh** price MAE remains above the earlier sigmoid fit's **€{prior_score:.3f}/MWh** on these months; this experiment supplies no basis for replacing that stronger fit. It changes pooling, parameter sharing, renewable bids and training budget together, so the outcome does not show that spline interpolation itself is inferior. A larger declared training budget, a controlled curve-family comparison and full-period discretization checks are the next tests; no baseline promotion follows from this prototype.

Reproduce: `run_supply_knots_lp_2025.py`, `audit_supply_knots_lp_2025.py`, then `report_supply_knots_lp_2025.py` with the pinned scientific Python and `PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. Inspect live jobs first; resumes require unchanged sealed dependencies.
'''
    (dest/'supply-knots-lp-2025.md').write_text(text)
    for path in dest.glob('supply-knots-lp-2025-*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    inputs=[PLAN,OUT/'summary.json',OUT/'layout.json',OUT/'provenance.json',SOURCE/'summary.json',ROOT/'tools/report_supply_knots_lp_2025.py']+([audit_path] if audit else [])+([transfer_path] if transfer else [])+([orchestration_path] if orchestration else [])
    (dest/'supply-knots-lp-2025-receipt.json').write_text(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in inputs},indent=2)+'\n')
    print(json.dumps(dict(price_mae=scores,generation_mae_twh=gen_scores,normalized_generation_error=norm_scores,hours=len(hours),audited=bool(audit)),indent=2))


if __name__=='__main__':run()
