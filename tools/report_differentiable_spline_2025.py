"""Compact research snapshot; never infer completion from missing checkpoints."""
import csv
import json
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sigmoid_month_pairs_2025 import ROOT,OUT as SOURCE,FAMILIES,digest
from differentiable_spline_clearing import initial_parameters,BidCost
from run_differentiable_spline_2025 import OUT,PLAN


def run():
    research=ROOT/'research';pilot=ROOT/'data/bidding-zone-network-2025/differentiable-spline-pilot-v1/summary.json'
    checked=json.loads(pilot.read_text());gradient_path=ROOT/'data/bidding-zone-network-2025/differentiable-spline-gradient-v1/summary.json'
    extra=json.loads(gradient_path.read_text()) if gradient_path.exists() else None
    histories={int(p.stem.split('-')[1]):json.loads(p.read_text()) for p in sorted(OUT.glob('history-*.json'))}
    plt.rcParams.update({'svg.fonttype':'none','font.size':10})
    fig,ax=plt.subplots(figsize=(7,3.5))
    for month,rows in histories.items():ax.plot([r['step'] for r in rows],[r['loss'] for r in rows],marker='o',label=f'Month {month:02d}')
    ax.set(xlabel='Completed gradient updates',ylabel='Sampled joint training loss',title='Training only — not held-out performance')
    if histories:ax.legend()
    ax.grid(alpha=.2);fig.tight_layout();fig.savefig(research/'differentiable-spline-2025-training.svg');plt.close(fig)
    rows=[dict(train=month,**{k:r[k] for k in ['step','loss','price_loss','generation_loss','ridge','elapsed_seconds']}) for month,rr in histories.items() for r in rr]
    if rows:
        with (research/'differentiable-spline-2025-training.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    proposal=OUT/'proposal-01.json';curve_text='The January proposal has not yet completed; no learned-curve figure is claimed.'
    if proposal.exists():
        sealed=json.loads((SOURCE/'inputs.json').read_text());theta=np.array(json.loads(proposal.read_text())['theta']);neutral=initial_parameters(len(theta));hour=348
        with np.load(SOURCE/'inputs.npz') as z:cap=z['capacity'][hour];cost=z['source_cost'][hour];features=z['features'][hour]
        fig,axes=plt.subplots(2,2,figsize=(9,6));curve_rows=[]
        for ax,family in zip(axes.flat,['Gas','Coal','Other fossil','Solar']):
            ids=[j for j,g in enumerate(sealed['groups']) if g['country']=='DE' and g['family']==family and cap[j]>0]
            if not ids:ax.set_title(family+' — no available source group');continue
            j=max(ids,key=lambda j:cap[j]);g=sealed['groups'][j];zero=g['technology']=='solar';q=np.linspace(0,cap[j]/1000,101)
            for label,pars in [('Neutral',neutral),('Learned',theta)]:
                c=BidCost(np.array([cap[j]/1000]),np.array([0. if zero else cost[j]]),np.array([g['parameter']]),features[[g['zone_id']]],np.array([zero]),pars,0)
                prices=np.array([c.evaluate(np.array([v]))[1][0] for v in q]);ax.plot(q,prices,label=label)
                curve_rows.extend(dict(technology=g['technology'],zone=g['zone'],source_group=j,curve=label,gw=float(v),bid_eur_mwh=float(p)) for v,p in zip(q,prices))
            ax.set(title=f"{g['zone']} · {g['technology']}",xlabel='Available output (GW)',ylabel='Bid (EUR/MWh)');ax.grid(alpha=.2);ax.legend()
        fig.suptitle('15 January 2025 12:00 UTC — fitted on January sample only');fig.tight_layout();fig.savefig(research/'differentiable-spline-2025-curves.svg');plt.close(fig)
        with (research/'differentiable-spline-2025-curves.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(curve_rows[0]));writer.writeheader();writer.writerows(curve_rows)
        curve_text='![Exact smooth source-group bids](differentiable-spline-2025-curves.svg)\n\nEach panel shows the largest available German source group in that resource family, not the entire national stack. Solar’s zero economic curve includes the disclosed numerical tie-break of at most €0.01/MWh. [Curve data](differentiable-spline-2025-curves.csv).'
    summary_path=OUT/'summary.json';summary=json.loads(summary_path.read_text()) if summary_path.exists() else None
    failure=OUT/'failure.json';progress=json.loads((OUT/'progress.json').read_text()) if (OUT/'progress.json').exists() else {}
    status='Execution stopped; inspect the retained failure checkpoint.' if failure.exists() else 'Month-pair fitting/evaluation is still in progress; no completed validation score is available.'
    if summary:status=f"Evaluation status: {summary['status']}; {len(summary['pairs'])}/6 complete month pairs."
    evaluation='No complete even-month comparison is available in this snapshot.'
    if summary and summary['pairs']:
        lines=['| Test month | Neutral price MAE (EUR/MWh) | Learned price MAE | Neutral generation MAE (TWh) | Learned generation MAE |',
               '|---|---:|---:|---:|---:|']
        for pair in summary['pairs']:
            c=pair['control'];l=pair['learned'];lines.append(f"| {pair['test']:02d} | {c['price_mae']:.3f} | {l['price_mae']:.3f} | {c['generation_mae_twh']:.4f} | {l['generation_mae_twh']:.4f} |")
        evaluation='\n'.join(lines)+'\n\nThese are complete-month errors; independent saved-witness replay remains required before verified acceptance.'
    sensitivity='Additional directional and regularization checks are pending.'
    if extra:
        maxp=max(r['max_price_difference_eur_mwh'] for r in extra['regularizer_sensitivity']);maxq=max(r['max_source_group_dispatch_difference_mw'] for r in extra['regularizer_sensitivity'])
        maxg=max(r['absolute_error'] for r in extra['gradient_checks'])
        sensitivity=f"Three additional full-European directional checks (midpoints, shapes and joint) pass, with maximum absolute directional-derivative discrepancy {maxg:.2g}. Reducing the generation regularizer from €0.01 to €0.001/MWh changes prices by at most €{maxp:.6f}/MWh and individual source-group output by at most {maxq:.3f} MW over the three pilot hours. This is a small sample, not annual robustness evidence."
    text=f'''# Differentiable spline supply bids — research prototype

Snapshot: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.

**Implemented:** smooth monotone technology bids and gradient descent through constrained European clearing, fitting both prices and generation. **{status}** The accepted model, country explorer and disabled recurring reviews are unchanged.

## Model and data

The physical inputs are the sealed, unfitted month-pair experiment: 48 bidding zones, 474 technology/source-cost groups, original hourly demand and renewable availability, interconnector bounds and model-derived physical grid constraints. Reservoir output stays fixed. No battery/pumped-storage fleet or new water scheduling is introduced. Artificial emergency generation is fixed absent; infeasible cases must fail rather than invent supply.

Wind, solar and run-of-river offer at zero economic price, with curtailment allowed. Other groups use their hourly source-cost anchor plus a learned local-clock midpoint and six positive cubic I-spline coefficients. Positive weights enforce a nondecreasing marginal bid. Integrating this bid gives the exact convex offer-cost objective; the experiment does not clear an LP approximation of the spline.

Parameters are shared across country/resource families (216 sets, 11 coefficients each); source technology and efficiency cost differences remain separate. They are not independent parameters for 8760 hours. The midpoint uses the first two daily sine/cosine harmonics and a bounded shift; availability and source costs also change hourly. Country generation targets do not identify unique zonal or plant bids.

Prices are negative zonal balance multipliers in EUR/MWh. Supply and network variables use GW and objective values use kEUR/hour. The solver retains balance, branch and link constraints. A technical generation regularizer changes marginal costs by at most €0.01/MWh inside capacities; a 1e-6 quadratic tie-break applies to network variables. These provide curvature, including for economically zero-bid resources; they are not observed bid costs.

Price observations are corrected hourly ENTSO-E SDAC prices. Generation is evaluated against original Ember monthly national technology totals; hourly ENTSO-E generation remains available but is not silently substituted for monthly targets. Capacity/availability and source-cost provenance is inherited unchanged from the [sealed source experiment](sigmoid-month-pairs-2025.md). Full-year-fitted bid offsets and empirical country PV factors stay removed. Historical grid, fixed-hydro and perfect-input assumptions still make this conditional retrospective research.

## Actual gradient fitting

Each clearing solves the smooth convex dispatch problem. An implicit adjoint of its primal-dual KKT system differentiates **both generator dispatch and cleared price multipliers** with respect to spline parameters. Adam follows those gradients on a joint loss: smooth price MAE divided by €40/MWh, normalized monthly generation error and a small parameter ridge. This differs from the earlier inverse least-squares/heuristic sigmoid fit.

Each odd month initializes independently. A fixed uniformly sampled 16 hours from that month supplies four gradient updates; monthly dispatch is estimated by expanding the sampled hours, while fixed reservoir generation uses its exact monthly total. This is a deliberately small, approximate training budget, not a claim of parameter convergence. Missing generation remains unknown. Even-month observations do not enter the fit or clearing. Proposals freeze before scoring February, April, June, August, October and December at **all 4344 hours**, with identical-input neutral-spline controls.

The even months have already been inspected in prior research, so this is not untouched prospective forecast validation. A completed six-month score would also not be an 8760-hour out-of-fold annual score. The zero-renewable-bid assumption changes alongside curve family relative to the earlier sigmoid experiment; only the neutral-versus-learned spline comparison isolates fitting in this design.

![Observed training progress](differentiable-spline-2025-training.svg)

[Training data](differentiable-spline-2025-training.csv). Loss is sample-based and smoothed; it must not be reported as ordinary all-hour price or generation MAE. Current checkpoint stage: `{progress.get('stage','not recorded')}`. No test result is inferred from this plot.

## Example supply curves

{curve_text}

## Complete-month evaluation

{evaluation}

## Numerical verification

Six focused tests pass: monotonicity, integrated-cost derivatives, congested toy dispatch, joint price/dispatch finite differences, zero-bid parameter isolation, and training-loss/target-slice derivatives and isolation. Three European January hours satisfy balance/network feasibility and nonlinear KKT checks. One European joint adjoint agrees with finite differences to absolute error 9.38e-9.

{sensitivity}

Initial exact European smooth solves take 1.51–3.40 seconds/hour, 18–40 Newton iterations. These are measured pilot timings, not annual runtime. Saved primal/dual witnesses support an independent replay with physical residual≤1e-4 MW, stationarity≤2e-7 EUR/MWh and complementarity≤€0.05. Complementarity is a nonlinear KKT statistic, not the earlier LP objective-gap measure. Full replay remains a separate acceptance step.

Smooth spline bids do not make hard capacity/network active-set changes universally differentiable. The adjoint uses the converged, very small perturbed KKT system; gradient checks are local. Numerical conditioning, parameter non-identification and broader smoothing sensitivity require continued checks.

## Conclusion and next check

The differentiable constrained prototype works on toy and European pilot cases. It has **not yet established better held-out accuracy or fast annual inference**. Complete all six month pairs, independently replay the saved certificates, then compare ordinary price MAE and actual monthly generation errors against neutral controls before considering larger fitting budgets or model adoption.

Reproduce with the scientific environment and `PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`: `run_differentiable_spline_2025.py`, then `audit_differentiable_spline_2025.py`, then `report_differentiable_spline_2025.py`. The runner checks sealed dependency hashes on resume; inspect live jobs/failure checkpoints first and never start a duplicate. Large witnesses remain ignored local data, not Git.
'''
    (research/'differentiable-spline-2025.md').write_text(text)
    sources=[PLAN,pilot,OUT/'provenance.json']+([proposal] if proposal.exists() else [])+list(OUT.glob('history-*.json'))+([gradient_path] if extra else [])
    (research/'differentiable-spline-2025-receipt.json').write_text(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in sources},indent=2)+'\n')


if __name__=='__main__':run()
