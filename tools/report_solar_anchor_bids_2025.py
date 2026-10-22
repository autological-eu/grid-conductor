"""Concise full-year bid recalibration report, with no public-model promotion."""
import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/solar-anchor-bids-v1'


def export(path,rows):
    with path.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def report():
    a=json.loads((OUT/'audit.json').read_text());s=json.loads((OUT/'summary.json').read_text());p=json.loads((OUT/'inputs.json').read_text())
    assert a['status']=='all_35040_source_bid_native_kkt_replays_passed' and a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_solar_anchor_bids_2025.py')
    for f,h in a['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    baseline=a['cases']['control'];selected=a['selected'];winner=min((k for k in a['cases'] if k!='control'),key=lambda k:a['cases'][k]['europe_mae']);candidate=a['cases'][winner];folder=ROOT/'research';files=[]
    target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];complete=np.isfinite(target).all(axis=0);tail={};event={}
    for case in ['control',winner]:
        record=s['cases'][case]['annual'];path=ROOT/record['witness'];assert digest(path)==record['witness_sha256']
        with np.load(path) as z:prices_raw=z['row_duals'][:,:target.shape[1]]
        mask=(target[:,complete]>300);tail[case]=float(abs(prices_raw[:,complete]-target[:,complete])[mask].mean())
        zi=next(i for i,r in enumerate(baseline['prices']) if r['zone']=='DE-LU');hour=19*24+16
        event[case]=float(prices_raw[hour,zi]);event['observed']=float(target[hour,zi])
    prices=[]
    for i,old in enumerate(baseline['prices']):
        row=dict(zone=old['zone'],hours=old['known_hours'])
        for case,r in a['cases'].items():
            z=r['prices'][i];assert z['zone']==old['zone']
            for key in ['mae_eur_mwh','correlation','demeaned_mae','ramp_mae']:row[case+'_'+key]=z.get(key)
        prices.append(row)
    path=folder/'solar-anchor-bids-2025-prices.csv';export(path,prices);files.append(path)
    generation=[]
    for fuel in ['Solar','Gas','Coal','Nuclear']:
        source_key='solar' if fuel=='Solar' else 'thermal'
        cs=sorted(set(r['country'] for r in baseline[source_key] if source_key=='solar' or r['fuel']==fuel))
        for country in cs:
            row=dict(country=country,fuel=fuel)
            for case,r in a['cases'].items():
                rows=[v for v in r[source_key] if v['country']==country and (source_key=='solar' or v['fuel']==fuel)]
                row[case+'_twh']=sum(v['model_twh'] for v in rows)
                row[case+'_monthly_mae_twh']=float(np.mean([abs(v['model_twh']-v['observed_twh']) for v in rows if v['observed_twh'] is not None])) if any(v['observed_twh'] is not None for v in rows) else None
            rows=[v for v in baseline[source_key] if v['country']==country and (source_key=='solar' or v['fuel']==fuel)]
            row['observed_twh']=sum(v['observed_twh'] for v in rows) if len(rows)==12 and all(v['observed_twh'] is not None for v in rows) else None
            row['observed_months']=sum(v['observed_twh'] is not None for v in rows);generation.append(row)
    path=folder/'solar-anchor-bids-2025-generation.csv';export(path,generation);files.append(path)
    fig,axes=plt.subplots(1,2,figsize=(13,9),gridspec_kw={'width_ratios':[1.3,1]});ax=axes[0]
    known=[r for r in prices if r['hours']==8760];known.sort(key=lambda r:r[winner+'_mae_eur_mwh']-r['control_mae_eur_mwh'])
    delta=[r[winner+'_mae_eur_mwh']-r['control_mae_eur_mwh'] for r in known]
    ax.barh(np.arange(len(known)),delta,color=['#377eb8' if v<0 else '#d95f02' for v in delta]);ax.set_yticks(np.arange(len(known)),[r['zone'] for r in known],fontsize=8);ax.axvline(0,color='black',lw=.7);ax.set_xlabel('Change in annual price MAE, €/MWh');ax.set_title('All 41 complete price zones\nBlue improves; orange worsens');ax.grid(axis='x',alpha=.2)
    ax=axes[1];fuels=['Solar','Gas','Coal','Nuclear'];pos=np.arange(4)
    for offset,case,color in [(-.18,'control','#888888'),(.18,winner,'#377eb8')]:
        values=[np.mean([r[case+'_monthly_mae_twh'] for r in generation if r['fuel']==f and r[case+'_monthly_mae_twh'] is not None]) for f in fuels]
        ax.bar(pos+offset,values,width=.35,label=case,color=color)
    ax.set_xticks(pos,fuels);ax.set_ylabel('Equal-country monthly generation MAE, TWh');ax.legend();ax.set_title('Generation checks against Ember\nSolar: 21 fitted countries; thermal: modeled fleets');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Retained country solar factors + bounded supply-bid recalibration');fig.tight_layout(rect=(0,0,1,.96));path=folder/'assets/solar-anchor-bids-2025.png';fig.savefig(path,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig);files.append(path)
    mean=lambda r,k:float(np.mean([z[k] for z in r['prices'] if z['known_hours']==8760 and z.get(k) is not None]))
    improvement=100*(1-candidate['europe_mae']/baseline['europe_mae']);better=sum(v<0 for v in delta);worse=sum(v>0 for v in delta)
    lines=['# Supply bids after the country solar correction','',
        f"**Result:** the lowest-price-error trial `{winner}` changes full-year European price MAE **{baseline['europe_mae']:.3f} → {candidate['europe_mae']:.3f} €/MWh ({improvement:.2f}% lower)** with the retained solar factors. {better} zones improve and {worse} worsen. But thermal generation error increases **{100*(candidate['thermal_monthly_normalized_error']/baseline['thermal_monthly_normalized_error']-1):.2f}%**, failing the predeclared 5% guard. **No new bid trial qualifies; retain the solar-corrected control.** All four 8,760-hour cases pass independent source/bid/native/KKT replay with zero emergency. Website/explorer unchanged.",'',
        '## What changes','',
        'Start from the user-retained solar-country-fit-v1/country_factors: 21 source-country PV factors, the corrected weather interval, generic loss retention and German stock reconciliation. Keep their exclusions and original source files intact. The old non-oil bid calibration used earlier auction targets; this experiment fits a fresh bounded **increment** against corrected ENTSO-E main day-ahead (SDAC) hourly prices.','',
        'The existing gas, coal/lignite and nuclear offers retain their daily fuel, efficiency, carbon, variable-cost and inherited bid components. Add one smooth effective correction per zone/resource. Calendar features are annual sine/cosine, local-hour first/second harmonics, seasonal × daily interactions and a centered local weekend indicator (16 coefficients; DST respected). No residual-demand predictor, observed hourly generation, hourly price lookup in dispatch or post-clearing price correction is used.','',
        'Fit ridge regression (168 I) to observed-minus-anchor price errors, clipped to ±100 €/MWh. The common calendar rule uses all available target hours; the resource rule uses only hours with positive local interior dispatch, more than 0.001 MW from either bound, and offer cost within 1e-5 €/MWh of the local anchor price. Require 168 observations; unsupported fits remain zero. Bound incremental offers to ±30 €/MWh gas/coal and ±7.5 nuclear; the half case uses half these corrections. Floor final thermal bids at zero and apply the same correction to every tranche, preserving their ordering. These are research bounds, not measured markups.','',
        'Oil/CHP, renewable bids, emergency bids, fixed hydro schedules, physical MW, solar factors, demand, network/GSK/PTDF and link limits are unchanged. Hydro remains precomputed; this does not introduce reservoir optimization or a new chronological storage model. Clearing reruns every hour of 2025 under the constrained market model.','',
        '## Fixed experiment and all results','',
        'One reused control and exactly three new annual trials, all from one unchanged-anchor proposal: half/full common calendar and full resource-specific correction. No successive residual fitting or search expansion. Select the lowest all-year equal-zone MAE among independently verified zero-emergency cases whose solar monthly MAE and thermal monthly normalized generation error are each at most 105% of control. That 5% is an experimental selection guard, not a relaxed product acceptance gate.','',
        '| Case | Price MAE €/MWh | Daily-demeaned MAE | Solar monthly MAE TWh | Thermal normalized error | Eligible |',
        '|---|---:|---:|---:|---:|---|']
    for case,r in a['cases'].items():lines.append(f"| {case} | {r['europe_mae']:.3f} | {mean(r,'demeaned_mae'):.3f} | {r['solar_monthly_mae']:.5f} | {r['thermal_monthly_normalized_error']:.4f} | {'yes' if r['eligible'] else 'no'} |")
    lines+=['','Thermal guard: mean absolute monthly Gas/Coal/Nuclear generation error divided by max(source TWh,0.25), over known original Ember targets for modeled resource-country pairs. Each selected thermal offer has a single verified source country, so these national resource totals need no proportional inter-country allocation. Coal includes lignite. Missing targets are unknown. This guard excludes countries without the corresponding modeled fleet; it is not a complete national-mix validation. Oil is not compared to Ember Other fossil, which also contains other fuels.','',
        'Solar uses proportional generation allocation within equal-price pools, with conditional lower/upper bounds retained in the local audit. Its monthly score covers the 21 fitted countries and is distinct from pre-clearing yield fit. The factors and source profiles stay fixed even when market curtailment changes. The generation CSV shows every modeled thermal country/resource and the 21 solar countries, with source coverage and all trial totals.','',
        '![Every-zone price changes and generation checks](assets/solar-anchor-bids-2025.png)','',
        '## Lowest-price-error trial: detail (not adopted)','',
        '| Zone | Anchor MAE | Trial MAE | Anchor correlation | Trial correlation |',
        '|---|---:|---:|---:|---:|']
    for zone in ['DE-LU','FR','ES','NO1','NO2','NO3','NO4','NO5','SE1','SE4']:
        old=next(r for r in baseline['prices'] if r['zone']==zone);new=next(r for r in candidate['prices'] if r['zone']==zone)
        lines.append(f"| {zone} | {old['mae_eur_mwh']:.3f} | {new['mae_eur_mwh']:.3f} | {old['correlation']:.3f} | {new['correlation']:.3f} |")
    lines+=['',f"Equal-zone mean correlation **{mean(baseline,'correlation'):.3f} → {mean(candidate,'correlation'):.3f}**; daily-demeaned MAE **{mean(baseline,'demeaned_mae'):.3f} → {mean(candidate,'demeaned_mae'):.3f} €/MWh**; hourly-ramp MAE **{mean(baseline,'ramp_mae'):.3f} → {mean(candidate,'ramp_mae'):.3f} €/MWh**.",'',
        f"Scarcity remains unresolved: pooled MAE over observed prices above 300 €/MWh in the 41 complete zones is **{tail['control']:.2f} → {tail[winner]:.2f} €/MWh** (a conditional pooled score, not the equal-zone annual metric). At 20 January 16:00 UTC, Germany clears **{event['control']:.2f} → {event[winner]:.2f} €/MWh**, versus **{event['observed']:.2f}** observed.",'',
        'This is an all-8,760-hour solve, scored equally over 41 complete ENTSO-E zones out of 48 modeled zones. Unavailable observations remain missing, with coverage in the CSV. Fitting, trial selection and final scoring all use already-inspected 2025; these are **in-sample reconstruction results**, not cross-validation, unseen-year forecasting accuracy, recovered actual bids or verified investment benefits. Effective corrections can absorb source and grid errors. Smooth calendar corrections cannot by themselves explain exceptional scarcity spikes or establish plant eligibility/startup constraints.','',
        '## Verification and conclusion','',
        f"Independent audit verifies the sealed source/proposal hashes, re-solves each ridge fit through augmented least squares, reconstructs resource-only costs, and replays all **35,040** hourly primal/native/KKT certificates. Maximum native residual **{max(r['native_residual_mw'] for r in a['cases'].values()):.3g} MW**, maximum duality gap **{max(r['duality_gap_maximum_eur'] for r in a['cases'].values()):.3g} EUR**. No emergency in any case; original feasibility/optimality gates remain unchanged. New clearing times: "+', '.join(f"{case} {r['annual']['clearing_seconds']:.1f}s" for case,r in s['cases'].items() if case!='control')+f". Independent audit {a['seconds']:.1f}s. Three focused tests cover unsupported/missing fits, clipping/ridge and unchanged nonthermal/tranche behavior.",'',
        f"The declared selection retains `{selected}`. The `{winner}` price improvement demonstrates sensitivity to supply bids, but its generation trade-off prevents adoption; the two common-calendar trials also fail the thermal guard. Solar monthly MAE changes only {baseline['solar_monthly_mae']:.5f} → {candidate['solar_monthly_mae']:.5f} TWh, so the principal rejection is thermal mix. A useful next experiment would constrain bid fitting jointly by country/resource generation instead of fitting prices first and checking mix afterward. That needs a new declared design, not relaxed guards or an expanded version of this completed search. Public report/explorer/browser solver remain unchanged and recurring reviews stay disabled.",'',
        '[All 48 zones and all trial price/shape scores](solar-anchor-bids-2025-prices.csv) · [Country/resource generation, all trial totals and monthly errors](solar-anchor-bids-2025-generation.csv).','',
        'Reproduce: pinned scientific Python with PYTHONPATH=tools and BLAS/OMP threads1; run solar_anchor_bids_2025.py prepare then run (fresh directory only), audit_solar_anchor_bids_2025.py, report_solar_anchor_bids_2025.py. Design is config/solar-anchor-bids-2025.json. Full hashes, coefficients, source memberships, witnesses, all monthly allocation bounds and certificates are retained in ignored data/bidding-zone-network-2025/solar-anchor-bids-v1/. No hourly matrices or raw-provider data are added to Git.','']
    path=folder/'solar-anchor-bids-2025.md';path.write_text('\n'.join(lines));files.append(path)
    receipt=dict(producer_sha256=digest(__file__),audit_sha256=digest(OUT/'audit.json'),selected=selected,lowest_price_trial=winner,exports={str(f.relative_to(ROOT)):digest(f) for f in files})
    (OUT/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Selected',selected,'lowest-price trial',winner,baseline['europe_mae'],'→',candidate['europe_mae'],flush=True)


if __name__=='__main__':report()
