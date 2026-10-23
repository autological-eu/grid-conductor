"""Show sealed learned technology curves in a held-out hour; no fit or solve."""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.special import expit, logit
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sigmoid_month_pairs_2025 import ROOT, OUT, load, neutral, offer_costs, digest, write

NAME = 'learned-supply-curve-example-2025'
HOUR = '2025-06-15T12'
ZONE = 'DE-LU'
NAMES = dict(onshore_wind='Onshore wind', offshore_wind='Offshore wind', solar='Solar', nuclear='Nuclear',
             ror='Run-of-river hydro', gas='Gas', hard_coal='Hard coal', lignite='Lignite', oil='Oil / CHP',
             biomass='Biomass', waste='Waste', geothermal='Geothermal')


def export(path, rows):
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)


def report():
    sealed, data, _ = load(); summary = json.loads((OUT/'summary.json').read_text()); audit = json.loads((OUT/'audit.json').read_text())
    assert audit['summary_sha256'] == digest(OUT/'summary.json')
    assert audit['status'] == 'all_six_folds_17520_retained_LP_hours_and_target_isolation_passed'
    row = next(r for r in summary['pairs'] if r['train_month'] == 5 and r['test_month'] == 6)
    proposal = ROOT/row['proposal']['path']; assert digest(proposal) == row['proposal']['sha256']
    theta = np.array(json.loads(proposal.read_text())['theta']); base = neutral(sealed)
    t = int((np.datetime64(HOUR)-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int)); zi = sealed['zones'].index(ZONE)
    K = sealed['design']['segments']; groups = sealed['groups']; exact = offer_costs(theta, groups, data['source_cost'][t:t+1], data['features'][t:t+1], K)[0]
    prices = {}; dispatch = None
    for case in ['selected', 'control']:
        r = row['witnesses']['test_'+case]; assert digest(ROOT/r['path']) == r['sha256']
        with np.load(ROOT/r['path']) as z:
            local = int(np.flatnonzero(z['hours'] == t)[0]); prices[case] = float(z['row_duals'][local, zi])
            if case == 'selected':
                dispatch = z['values'][local, :len(groups)*K].reshape(len(groups), K).sum(axis=1)
    observed = float(data['observed_prices'][t, zi])
    fig, axes = plt.subplots(4, 3, figsize=(14, 12)); summaries = []; offers = []
    for ax, (tech, title) in zip(axes.ravel(), NAMES.items(), strict=True):
        ids = [j for j,g in enumerate(groups) if g['zone'] == ZONE and g['technology'] == tech]
        ids = [j for j in ids if data['capacity'][t,j] > 1e-7]
        cap = data['capacity'][t,ids]; total = float(cap.sum())
        ax.set_title(f'{title} · {total/1000:.2f} GW available', loc='left', fontsize=10, fontweight='bold')
        record = dict(technology=tech, available_gw=total/1000, actual_dispatch_gw=float(dispatch[ids].sum()/1000),
                      control_p10=None, control_p50=None, control_p90=None, learned_p10=None, learned_p50=None, learned_p90=None,
                      minimum_hourly_shift=None, maximum_hourly_shift=None, minimum_spread=None, maximum_spread=None)
        if not ids:
            ax.text(.5,.5,'No available supply',ha='center',va='center',transform=ax.transAxes,color='#777777')
        else:
            curves = {}
            for case, params in [('control',base),('learned',theta)]:
                pi = [groups[j]['parameter'] for j in ids]
                shift = np.clip(params[pi,:5]@data['features'][t,zi],-80,80)
                centers = data['source_cost'][t,ids]+shift; spread = np.exp(params[pi,5])
                def quantity(p): return float((cap*expit((p-centers)/spread)).sum())
                left = float((centers+spread*logit(.001)).min()); right = float((centers+spread*logit(.999)).max())
                p = np.linspace(left,right,1200)
                q = (cap[None,:]*expit((p[:,None]-centers)/spread)).sum(axis=1)
                curves[case]=(q,p)
                for quantile in [.1,.5,.9]:
                    record[case+'_p'+str(int(quantile*100))]=float(brentq(lambda p:quantity(p)-total*quantile,left,right))
                if case == 'learned':
                    record.update(minimum_hourly_shift=float(shift.min()), maximum_hourly_shift=float(shift.max()), minimum_spread=float(spread.min()), maximum_spread=float(spread.max()))
            for case,color,style in [('control','#929292','--'),('learned','#267f91','-')]:
                q,p=curves[case];ax.plot(q/1000,p,color=color,ls=style,lw=1.6)
            segments=[]
            for j in ids:
                for k in range(K):
                    r=dict(zone=ZONE,hour_utc=HOUR+':00Z',technology=tech,country=groups[j]['country'],source_group=j,segment=k,
                           offered_mw=float(data['capacity'][t,j]/K),bid_eur_mwh=float(exact[j*K+k]))
                    offers.append(r);segments.append((r['bid_eur_mwh'],r['offered_mw']))
            segments.sort(); ends=np.cumsum([v[1] for v in segments])/1000; y=np.array([v[0] for v in segments])
            ax.step(np.r_[0,ends],np.r_[y,y[-1]],where='post',color='#c47a2a',lw=1,alpha=.85)
            lo=min(record['control_p10'],record['learned_p10'],float(y.min()));hi=max(record['control_p90'],record['learned_p90'],float(y.max()));span=max(hi-lo,10)
            ax.set_ylim(lo-.15*span,hi+.15*span);ax.set_xlim(0,total/1000*1.03)
            ax.text(.03,.94,f"Learned median: {record['learned_p50']:.1f} €/MWh",transform=ax.transAxes,fontsize=8,va='top')
        ax.set_xlabel('Cumulative offered supply, GW',fontsize=8);ax.set_ylabel('Bid price, €/MWh',fontsize=8);ax.grid(alpha=.2);summaries.append(record)
    fig.suptitle('Learned technology supply curves · DE-LU\n15 June 2025, 12:00–13:00 UTC (14:00–15:00 CEST) · fitted on May only',fontsize=15)
    fig.legend(handles=[Line2D([0],[0],color='#929292',ls='--',label='Unfitted sigmoid'),Line2D([0],[0],color='#267f91',label='Learned smooth curve'),Line2D([0],[0],color='#c47a2a',label='Actual LP offer segments')],loc='lower center',ncol=3,bbox_to_anchor=(.5,.025),fontsize=10)
    fig.text(.5,.008,'Each panel has its own axes. Offered availability is unchanged; actual dispatch is selected by the European network.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.065,1,.94));image=ROOT/'research/assets'/f'{NAME}.png';fig.savefig(image,dpi=150);plt.close(fig)
    table=ROOT/'research'/f'{NAME}.csv';export(table,summaries)
    segments=ROOT/'research'/f'{NAME}-offers.csv';export(segments,offers)
    lines=['# An example of learned technology supply curves','',
      '**DE-LU, 15 June 2025, 12:00–13:00 UTC / 14:00–15:00 CEST.** Curves were fitted on May only, then used unchanged for June. This is an extraction of the completed held-out run: no new fitting or clearing.','',
      f'![Learned supply curves by technology](assets/{NAME}.png)','',
      'Grey dashed: the unfitted sigmoid control. Blue: the learned continuous supply function. Orange: the finite divisible offers actually used by the LP. Both versions have identical source availability; learning changes their bid prices and distribution across price levels. Each panel has its own axes.','',
      'The underlying rule is `quantity = available_MW × sigmoid((price − source_cost − hourly_shift)/spread)`. The shift uses learned intercept and local-clock daily harmonics; spread controls steepness. Both are shared country/resource-family parameters, while original technology/efficiency costs and source groups remain distinct. A technology curve adds up the curves of its source groups, so it need not be one perfect sigmoid.','',
      'A shift upward means that the same volume requires a higher price; a wider price range spreads offered volumes across more prices. The sigmoid expresses **volume as a function of price**. These charts put price on the vertical axis and volume on the horizontal axis, so they show its **inverse**. Here eight equal-volume segments per source group approximate the smooth curve. Their prices are sampled at inverse-sigmoid quantile midpoints. The orange steps are independently divisible, not block bids.','',
      '| Technology | Available GW | Unfitted median bid €/MWh | Learned median bid €/MWh | Learned 10–90% bid range €/MWh | Actual dispatch GW |','|---|---:|---:|---:|---:|---:|']
    for r in summaries:
        if r['available_gw']:
            lines.append(f"| {NAMES[r['technology']]} | {r['available_gw']:.3f} | {r['control_p50']:.2f} | {r['learned_p50']:.2f} | {r['learned_p10']:.2f} to {r['learned_p90']:.2f} | {r['actual_dispatch_gw']:.3f} |")
        else:lines.append(f"| {NAMES[r['technology']]} | 0 | — | — | — | 0 |")
    lines += ['',f"European network clearing gives DE-LU **{prices['selected']:.2f} €/MWh** with learned curves, versus **{prices['control']:.2f} €/MWh** with the unfitted control and **{observed:.2f} €/MWh** observed ENTSO-E SDAC. These prices are not an isolated intersection of the displayed domestic curves: imports, exports, fixed injections and physical network constraints participate.",'',
      'The median and 10–90% range describe prices along the smooth offered-volume curve, not confidence intervals or predicted market-price ranges. Prices beyond those quantiles still exist; graph tails are clipped for readability. Available MW is not dispatched MW, and negative offers are permitted. Germany has no nuclear supply in the retained fleet. Reservoir hydro remains a separate fixed hourly injection. Flexible battery/PHS curves were not part of this fitted experiment; their separate earlier candidate must not be spliced into this witness.','',
      'The gas median changes only from 109.35 to 105.03 €/MWh, but its 10–90% range widens from 80.30–143.22 to −9.46–219.84 €/MWh. The fit is learning a much wider distribution of willingness to supply, not simply shifting every gas offer downward. German wind/solar reach the declared −80 €/MWh effective hourly-shift bound in this example, and a biomass spread reaches the 100 €/MWh upper bound. These binding limits are important calibration diagnostics, not established physical properties.','',
      'These are learned effective offers, not observed order books or recovered operating costs. The broad negative/positive tails can compensate for excessive modeled availability, missing constraints or missing market mechanisms. They do not establish actual renewable or thermal bidding behaviour. The six-pair experiment improved aggregate prices/generation but worsened solar generation and seven Nordic price zones; the accepted baseline remains unchanged.','',
      f'[Technology summary and parameters]({NAME}.csv) · [Exact LP offer segments]({NAME}-offers.csv) · [Six-pair validation report](sigmoid-month-pairs-2025.md). The local receipt pins the proposal, witnesses, original inputs and exports.','']
    doc=ROOT/'research'/f'{NAME}.md';doc.write_text('\n'.join(lines))
    files=[OUT/'inputs.json',OUT/'inputs.npz',OUT/'summary.json',OUT/'audit.json',proposal,*[ROOT/row['witnesses'][key]['path'] for key in ['test_selected','test_control']]]
    receipt=ROOT/'data/bidding-zone-network-2025/learned-supply-curve-example-v1';receipt.mkdir(exist_ok=True)
    write(receipt/'summary.json',dict(producer_sha256=digest(__file__),zone=ZONE,hour_utc=HOUR+':00Z',train_month=5,test_month=6,
          prices=prices,observed_price=observed,sources={str(p.relative_to(ROOT)):digest(p) for p in files},exports={str(p.relative_to(ROOT)):digest(p) for p in [image,table,segments,doc]}))
    print(json.dumps(dict(prices=prices,observed=observed,technology_summary=summaries),indent=2))


if __name__=='__main__':report()
