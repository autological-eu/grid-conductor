"""Report chronological source-PHS and explicitly hypothetical battery candidates."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/hourly-storage-bids-v1'
REPORT=ROOT/'research/hourly-storage-bids-2025'
LABELS={'baseline':'Accepted baseline','phs_source':'Source pumped storage','phs_plus_battery_demo':'PHS + hypothetical batteries'}


def export(path,rows):
    with path.open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def report():
    s=json.loads((OUT/'summary.json').read_text());a=json.loads((OUT/'audit.json').read_text());inputs=json.loads((OUT/'inputs.json').read_text());active=json.loads((ROOT/'config/active-research-baseline.json').read_text())
    assert a['status']=='all_17520_hourly_storage_physics_and_lp_certificates_replayed' and a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_hourly_storage_2025.py')
    for f,h in inputs['sources'].items():assert digest(ROOT/f)==h
    for f,h in inputs['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    for f,h in a['sources'].items():assert digest(ROOT/f)==h
    for f,h in a['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    files=[];prices=[]
    for zi,zone in enumerate(inputs['zones']):
        row=dict(zone=zone,observed_hours=a['cases']['baseline']['prices'][zi]['known_hours'])
        for case,r in a['cases'].items():
            z=r['prices'][zi];assert z['zone']==zone
            for k in ['mae_eur_mwh','correlation','bias_eur_mwh','demeaned_mae']:row[case+'_'+k]=z.get(k)
        prices.append(row)
    path=Path(str(REPORT)+'-prices.csv');export(path,prices);files.append(path)
    assets=[]
    for r in inputs['assets']:assets.append({k:r[k] for k in ['id','source_id','zone','technology','charge_mw','discharge_mw','energy_mwh','eta_charge','eta_discharge','standing_loss','source_share','mapping_method']})
    path=Path(str(REPORT)+'-fleet.csv');export(path,assets);files.append(path)
    mix=[]
    for country,fuel in sorted({(r['country'],r['fuel']) for r in a['cases']['baseline']['thermal']}):
        row=dict(country=country,fuel=fuel)
        for case,v in a['cases'].items():
            rows=[r for r in v['thermal'] if r['country']==country and r['fuel']==fuel];known=[r for r in rows if r['observed_twh'] is not None]
            row[case+'_annual_twh']=sum(r['model_twh'] for r in rows);row[case+'_monthly_mae_twh']=float(np.mean([r['absolute_error_twh'] for r in known])) if known else None
            if case=='baseline':row['observed_months']=len(known);row['observed_twh']=sum(r['observed_twh'] for r in known) if len(known)==12 else None
        mix.append(row)
    path=Path(str(REPORT)+'-thermal-generation.csv');export(path,mix);files.append(path)
    known=[r for r in prices if r['observed_hours']==8760];known.sort(key=lambda r:r['phs_source_mae_eur_mwh']-r['baseline_mae_eur_mwh'])
    fig,axes=plt.subplots(2,2,figsize=(15,11));ax=axes[0,0];x=np.arange(len(known));delta=[r['phs_source_mae_eur_mwh']-r['baseline_mae_eur_mwh'] for r in known]
    ax.bar(x,delta,color=['#347ba4' if v<0 else '#bc6b3c' for v in delta]);ax.set_xticks(x,[r['zone'] for r in known],rotation=90,fontsize=7);ax.axhline(0,color='black',lw=.7);ax.set_ylabel('Price MAE change, €/MWh');ax.set_title('Source pumped storage vs baseline · all 41 complete zones');ax.grid(axis='y',alpha=.2)
    ax=axes[0,1];cases=list(a['cases']);ax.bar(range(3),[a['cases'][c]['price_mae'] for c in cases],color=['#929292','#347ba4','#7a5ca5']);ax.set_xticks(range(3),['Baseline','Pumped storage','PHS + test batteries']);ax.set_ylabel('Full-year price MAE, €/MWh');ax.set_title('No observed-price fitting in this experiment');ax.grid(axis='y',alpha=.2)
    with np.load(ROOT/active['witness']['witness']) as z:base_prices=z['row_duals'][:,:len(inputs['zones'])]
    with np.load(ROOT/s['cases']['phs_source']['witness']) as z:phs_prices=z['row_duals'][:,:len(inputs['zones'])]
    with np.load(ROOT/s['cases']['phs_plus_battery_demo']['witness']) as z:energy=z['energy_mwh'];values=z['values']
    target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];start=193*24;end=start+5*24;times=np.arange('2025-01-01T00','2026-01-01T00',dtype='datetime64[h]')[start:end];zi=inputs['zones'].index('DE-LU')
    ax=axes[1,0]
    for series,label,color,style in [(target,'Observed SDAC','#222222','-'),(base_prices,'Accepted baseline','#929292','--'),(phs_prices,'Pumped storage','#347ba4','-')]:ax.plot(times,series[start:end,zi],label=label,color=color,ls=style,lw=1)
    ax.set_ylabel('€/MWh');ax.set_title('DE-LU · July 13–17 · example hourly prices');ax.legend(fontsize=8);ax.grid(alpha=.2)
    assets_demo=s['cases']['phs_plus_battery_demo']['assets'];j=next(i for i,r in enumerate(assets_demo) if r['id']=='demo-battery-DE-LU');S=len(assets_demo);n=values.shape[1]-2*S
    ax=axes[1,1];ax.plot(times,energy[start:end,j]/1000,color='#7a5ca5',label='Stored energy');ax.set_ylabel('Stored energy, GWh');ax.set_ylim(0,4.2);ax.set_title('Hypothetical DE-LU battery · 1 GW / 4 GWh');ax.grid(alpha=.2)
    ax2=ax.twinx();ax2.step(times,(values[start:end,n+S+j]-values[start:end,n+j])/1000,where='post',color='#4e9255',alpha=.65);ax2.set_ylabel('Net discharge, GW (negative = charge)');ax2.set_ylim(-1.15,1.15)
    for ax in axes[1]:ax.xaxis.set_major_locator(mdates.DayLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    fig.suptitle('Chronological storage works quickly; this simple bidding rule does not improve price fit');fig.tight_layout(rect=(0,0,1,.96));path=ROOT/'research/assets/hourly-storage-bids-2025.png';fig.savefig(path,dpi=145);plt.close(fig);files.append(path)
    lines=['# Hourly storage bids on the accepted European baseline','',
        '**Implemented:** batteries and pumped storage can submit hourly charging-demand and discharging-supply offers, with state of charge updated from actual dispatch and carried across days. Two full-year European cases pass independent network, stock and LP-price checks. **Neither improves price fit; keep the accepted baseline.**','',
        '## Fleet and scope','',
        'The first case restores only the retained source model’s **67 pumped-storage units: 58.15 GW**, split conservatively into 68 bidding-zone entries. It preserves original pump/turbine power, energy limits, efficiencies and zero natural inflow; it does not add the fixed reservoir schedule a second time. Source round-trip efficiency is 75%. Mixed-zone parents use dated located pumped-storage plant capacities; pure parents map directly. No parent needed the modeled-bus-count fallback, but the source location/grouping remains a proxy.','',
        'The inherited energy capacity is **9,088 GWh**, with durations from roughly 0.008 to 2,404 hours. This is a conspicuous source-model uncertainty, not a verified 2025 pumped-storage inventory. It was disclosed and preserved rather than silently capped or replaced. Power, pumping limits, shared-reservoir roles and energy capacity need external reconciliation before an empirical fleet or investment claim.','',
        'The cache contains no verified battery fleet. The second case adds exactly three **hypothetical 1 GW / 4 GWh batteries** in DE-LU, FR and ES, each with 95% charge and 95% discharge efficiency. This tests the battery interface; it is not a claim that Europe has only these batteries or that these assets existed in 2025.','',
        'Accepted resource_full supply bids, hourly renewable availability, fixed demand/reservoir hydro, grid/GSK/link limits and all price targets remain unchanged. Storage changes consumption and generation endogenously. Its injection follows the same zonal GSK treatment as baseline supply; this does not validate the actual connection of individual plants.','',
        '## Simple bidding and chronology','',
        'For every hour and zone, take the median of the **next 48 own-baseline modeled hourly prices**, clipped at zero. Call that reference P. Charging willingness-to-pay is `eta_charge × eta_discharge × P − 1 €/MWh`; discharging ask is `P + 1 €/MWh`. No observed SDAC price enters this rule, and no new storage forecast LP is solved. The cached baseline was itself calibrated using 2025 prices, so this is still retrospective reconstruction.','',
        'Both directions are divisible offers in the full network LP. A strictly positive buy/sell spread prevents simultaneous cycling without binaries. Available charge is bounded by pump power and remaining space; discharge is bounded by turbine power and current energy. After clearing, `E_next = (1 − standing_loss) × E + eta_charge × charge − discharge / eta_discharge`. Future hours use that actual E, with no day-boundary reset. This hourly screen has no minimum run time, block acceptance, intrahour switching or simultaneous 24-hour day-ahead auction.','',
        'Initial energy is explicitly zero, since observed initial inventories are not supplied. Final inventory is reported rather than forced cyclic or credited in profit. Both evaluated cases happen to finish empty. Forecast windows shrink at year end; they never wrap into January or look up future observations. Reservoir hydro remains fixed and separate. This is a rolling opportunity-cost heuristic, not globally optimal storage operation or a validated operator equilibrium.','',
        '## Full-year results','',
        '| Case | Price MAE €/MWh | Mean correlation | Case runtime | Charge TWh | Discharge TWh | Closing stock TWh |','|---|---:|---:|---:|---:|---:|---:|']
    for case,r in a['cases'].items():
        st=r['storage'];lines.append(f"| {LABELS[case]} | {r['price_mae']:.3f} | {r['mean_correlation']:.4f} | {r['seconds']:.1f} s | {st['charge_twh']:.3f} | {st['discharge_twh']:.3f} | {st['final_twh']:.6f} |" if st else f"| {LABELS[case]} | {r['price_mae']:.3f} | {r['mean_correlation']:.4f} | {r['seconds']:.1f} s historical | — | — | — |")
    lines += ['',f"All cases cover all 8,760 hours and the same 41 complete SDAC target zones of 48 modeled zones. New case runtimes include stock/bid updates, hourly clearing, certificates and witness saving. Total execution for both candidates plus source/forecast preparation is **{s['total_wall_seconds']:.1f} s**; source preparation is **{inputs['preparation_seconds']:.1f} s**. Independent audit takes **{a['seconds']:.1f} s**. A fresh own-baseline forecast solve is excluded; the pinned historical baseline solve took 51.8 s. The two candidate runtimes are sequential measurements, not a claim that adding batteries inherently speeds the solver. One solver/BLAS thread, 5 GiB address-space cap.",'',
        '![Annual scores and hourly storage example](assets/hourly-storage-bids-2025.png)','',
        'The new bids and stock constraints materially alter dispatch, but push prices away from the observations on average. A storage implementation is not automatically a better market reconstruction: fleet inputs, bidding thresholds, forecasting, calibrated pre-storage bids and market design all matter. The baseline bid calibration may already absorb some observed storage effects; adding explicit storage without refitting can expose that mismatch. Price deviations cannot be causally assigned to any one of those from these two cases.','',
        '## Generation effects','',
        '| Case | Wind/solar offer dispatch TWh | Gas monthly MAE TWh | Coal monthly MAE TWh | Nuclear monthly MAE TWh |','|---|---:|---:|---:|---:|']
    for case,r in a['cases'].items():lines.append(f"| {LABELS[case]} | {r['renewable_dispatch_twh']:.3f} | {r['thermal_monthly_mae']['Gas']:.4f} | {r['thermal_monthly_mae']['Coal']:.4f} | {r['thermal_monthly_mae']['Nuclear']:.4f} |")
    lines += ['',
        'Wind/solar is the exact jointly grouped renewable-offer volume, avoiding a false unique wind-versus-solar allocation. Thermal errors compare original monthly Ember cells for the same modeled country/resource groups across cases; they exclude countries lacking that modeled resource. These are not the broader all-country scores in the preceding comparison report. Generation from storage discharge is reported separately rather than counted as new primary renewable or hydro energy. Charging losses require additional net generation. No carbon savings or storage profit is claimed.','',
        '## Verification and next step','',
        'Six focused tests cover empty/full stocks, efficiency, loss and carry beyond a day, forecast boundaries, invalid states/cycling, positive bid spreads and a small independent LP dispatch/dual certificate. Before the annual run, 26 zero-storage control hours reproduced the accepted objective within 2.24e-8 EUR. The annual independent replay reconstructs each forecast, bid bound and storage balance, checks every cross-day carry, original network constraints and hourly primal/dual optimality.','']
    for case,r in a['cases'].items():
        if r['physical']:
            q=r['physical'];lines.append(f"- **{LABELS[case]}:** maximum physical residual {q['primal_mw']:.3g} MW, stock balance residual {q['maximum_stock_residual_mwh']:.3g} MWh, duality gap {q['duality_gap_eur']:.3g} EUR, annual energy-ledger residual {q['annual_ledger_residual_mwh']:.3g} MWh. Zero emergency dispatch and simultaneous cycling. Maximum recorded numerical stock clip {q['maximum_recorded_clip_mwh']:.3g} MWh.")
    lines += ['',
        'Retain this candidate as a working storage interface, not a replacement baseline. Before promotion, reconcile real battery/PHS MW/MWh and initial inventories, then evaluate a declared alternative bidding rule on unchanged common inputs. The current 48-hour median rule demonstrably fails the observed-price improvement goal. Do not restart reservoir searches, change source availability to dispatch, or relax feasibility gates. Public explorer/browser integration and recurring reviews remain unchanged.','',
        '[All-zone prices](hourly-storage-bids-2025-prices.csv) · [Source-model zonal PHS fleet](hourly-storage-bids-2025-fleet.csv) · [Country/resource thermal generation](hourly-storage-bids-2025-thermal-generation.csv). Full hourly dispatch, prices, charge/discharge and state trajectories stay in the ignored local `data/bidding-zone-network-2025/hourly-storage-bids-v1/`, with inputs, source hashes and audit. No large hourly witnesses are committed.','',
        'Reproduce in a fresh output directory with pinned scientific Python and one BLAS/OMP thread: run `tools/run_hourly_storage_2025.py`, then `tools/audit_hourly_storage_2025.py`, then `tools/report_hourly_storage_2025.py`. Design: `config/hourly-storage-bids-2025.json`. The generic interface supports both technologies with explicit power, energy, efficiency and standing-loss inputs.','']
    path=Path(str(REPORT)+'.md');path.write_text('\n'.join(lines));files.append(path)
    receipt=dict(producer_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),exports={str(f.relative_to(ROOT)):digest(f) for f in files});(OUT/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Storage comparison exports',len(files),flush=True)


if __name__=='__main__':report()
