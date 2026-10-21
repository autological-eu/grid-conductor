"""Standalone verified oil trial report; no website or model promotion."""
import argparse, csv, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from generation_mix_2025 import digest

LABELS={'control':'Current merchant bids','source_costs':'Dated source-cost proxy','chp25':'CHP tranche: 25%','chp50':'CHP tranche: 50%'}
COLORS={'control':'#94a3b8','source_costs':'#f59e0b','chp25':'#2563eb','chp50':'#16a34a'}


def report(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'verification-v2/audit.json').read_text())
    assert a['status']=='passed' and a['summary_sha256']==digest(folder/'summary.json')
    assert a['auditor_sha256']==digest(Path(__file__).with_name('audit_oil_chp_bids_2025.py'))
    cases=s['design']['cases'];outcomes=s['outcomes'];countries=[r['country']for r in outcomes['control']['oil']]
    rows=[]
    for key in cases:
        rows += [dict(case=key,**{k:v for k,v in r.items()if k!='monthly'})for r in outcomes[key]['oil']]
    csv_path=folder/'country-oil-comparison.csv'
    with csv_path.open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    annual=[];files=[csv_path]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    with PdfPages(folder/'oil-chp-bids-2025.pdf')as pdf:
        fig,ax=plt.subplots(figsize=(10.5,6.7));fig.subplots_adjust(top=.82,bottom=.22,left=.10,right=.97)
        x=np.arange(len(countries));width=.16
        observed=[r['observed_twh']for r in outcomes['control']['oil']]
        ax.bar(x-2*width,observed,width,label='ENTSO-E observed oil',color='#111827')
        for i,key in enumerate(cases):ax.bar(x+(i-1)*width,[r['model_known_hours_twh']for r in outcomes[key]['oil']],width,label=LABELS[key],color=COLORS[key])
        ax.set_xticks(x,countries);ax.set_ylabel('Oil generation over known hours (TWh)');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        ax.legend(fontsize=9,ncol=2,loc='upper right')
        fig.suptitle('Does a simple heat-led oil bid recover observed generation?',fontsize=16,y=.96)
        fig.text(.10,.86,'2025 full-year European clearing · five country comparisons · source and structure controls')
        fig.text(.10,.08,'DE/BE/PL: 8,760 known hours; SK/SI: 8,758. Observations are physical ENTSO-E B06 output,\nnot certified day-ahead accepted generation. New oil bids are not fitted to electricity prices or oil generation.',fontsize=9)
        file=folder/'annual-oil-generation.png';fig.savefig(file,dpi=160);files.append(file);pdf.savefig(fig);plt.close(fig)

        fig,axes=plt.subplots(2,1,figsize=(10.5,8.1));fig.subplots_adjust(top=.88,bottom=.19,hspace=.48,left=.10,right=.97)
        germany={key:next(r for r in outcomes[key]['oil']if r['country']=='DE')for key in cases}
        month=np.arange(1,13);axes[0].plot(month,[r['observed_twh']for r in germany['control']['monthly']],color='#111827',label='Observed oil',lw=2)
        for key in cases:axes[0].plot(month,[r['model_twh']for r in germany[key]['monthly']],label=LABELS[key],color=COLORS[key])
        axes[0].set_ylabel('German oil generation (TWh/month)');axes[0].set_xticks(month);axes[0].grid(alpha=.15);axes[0].legend(fontsize=8,ncol=3)
        x=np.arange(4);axes[1].bar(x,[germany[k]['hourly_mae_mw']for k in cases],color=[COLORS[k]for k in cases]);axes[1].set_xticks(x,[LABELS[k].replace(': ','\n').replace(' proxy','')for k in cases],fontsize=8);axes[1].set_ylabel('German hourly oil error (MW MAE)');axes[1].grid(axis='y',alpha=.15);axes[1].set_axisbelow(True)
        fig.suptitle('Germany: annual energy alone is not enough',fontsize=17,y=.96)
        fig.text(.10,.07,'Hourly correlation, active hours, negative-price hours and matched-month quantities accompany totals.\nCheap volumes are optional offers: there is no forced heat schedule, startup state or new energy.\n25%/50% of source-labelled CHP capacity are declared sensitivities, not measured operating minima.',fontsize=9)
        file=folder/'germany-oil-timing.png';fig.savefig(file,dpi=160);files.append(file);pdf.savefig(fig);plt.close(fig)

        baseline=outcomes['control']['prices'];eligible=[r['zone']for r in baseline['zones']if r['known_hours']]
        fig,ax=plt.subplots(figsize=(10.5,7.7));fig.subplots_adjust(top=.88,bottom=.21,left=.10,right=.97)
        for key in cases[1:]:
            index={r['zone']:r for r in outcomes[key]['prices']['zones']}
            original={r['zone']:r for r in baseline['zones']}
            error=[index[z]['mae_eur_mwh']-original[z]['mae_eur_mwh']for z in eligible]
            ax.plot(np.arange(len(eligible)),error,'o-',label=LABELS[key],color=COLORS[key],lw=.7,ms=3)
        ax.axhline(0,color='#111827',lw=.8);ax.set_xticks(np.arange(len(eligible)),eligible,rotation=90,fontsize=7);ax.set_ylabel('Change in price MAE (EUR/MWh); negative = improvement');ax.grid(axis='y',alpha=.15);ax.legend(fontsize=9)
        fig.suptitle('Effect on all 41 complete observed-price areas',fontsize=17,y=.96)
        fig.text(.10,.06,'All 8,760 hours, including negative and extreme prices. Non-oil bids, demand, fixed hydro and\nphysical constraints are frozen. Changed prices are model responses, not evidence of recovered real bids.',fontsize=9)
        file=folder/'price-mae-change.png';fig.savefig(file,dpi=160);files.append(file);pdf.savefig(fig);plt.close(fig)
    files.append(folder/'oil-chp-bids-2025.pdf')
    text=['# Oil bid structure: verified annual experiment','',
          'Full 2025, 8,760-hour European clearing. No baseline/explorer/website promotion.','',
          '## Result','',
          f"The structure partially improves German oil dispatch, while the source-cost correction alone still gives zero oil generation. The 25% CHP case produces {germany['chp25']['model_known_hours_twh']:.3f} TWh against {germany['control']['observed_twh']:.3f} observed and reduces hourly oil MAE from {germany['control']['hourly_mae_mw']:.1f} to {germany['chp25']['hourly_mae_mw']:.1f} MW. The 50% case produces {germany['chp50']['model_known_hours_twh']:.3f} TWh, only {100*abs(germany['chp50']['annual_bias_twh'])/germany['chp50']['observed_twh']:.2f}% below observed, but hourly MAE is worse than CHP25 ({germany['chp50']['hourly_mae_mw']:.1f} MW).",'',
          f"Both have weak German hourly correlation (about {germany['chp50']['hourly_correlation']:.2f}) and zero modeled oil in observed-negative-price hours. BE/PL/SK/SI still have zero oil dispatch. Europe price MAE changes from {baseline['equal_zone_mae']:.3f} to {outcomes['chp25']['prices']['equal_zone_mae']:.3f}/{outcomes['chp50']['prices']['equal_zone_mae']:.3f} EUR/MWh. Thus annual energy matching does not establish recovered dispatch timing or an overall better price model. Neither case is promoted.",'',
          '## What changed','',
          'The control reuses the independently audited capacity+daily-Brent witness. Source-cost control replaces only eligible EU/EEA oil carbon costs with a carried EEX primary-auction proxy; daily EIA Brent/ECB, existing electrical efficiencies and VOM remain. Non-EU/EEA carbon stays inherited. This is not a complete delivered-fuel or carbon-regime correction.','',
          'Two further cases split 25% or 50% of geographically matched, catalogue-labelled CHP capacity into a cheaper offer; remaining capacity bids merchant marginal cost. Total hourly available MW is conserved. Assumed useful-heat efficiency is 0.5 and alternative gas-boiler efficiency 0.9. Heat credit per electrical MWh is (0.5/electrical efficiency) × (monthly gas price + carbon × 0.198)/0.9. Physical oil emissions are not erased; the credit represents hypothetical displaced boiler cost.','',
          'These are fixed, predeclared structural sensitivities. No observed oil volume or electricity price selects the new oil quantities, credits or a winning case. The existing non-oil bids retain their all-year calibrated terms; this remains retrospective reconstruction rather than independent forecasting. No observed hourly heat, startup state, heat balance or forced output is claimed. Unknown/PP roles and source-missing PL/SK/SI CHP capacity receive no heat credit. Reserve market eligibility, crude versus delivered fuel, electrical heat rates and other carbon regimes remain unresolved.','',
          'EEX auction values are carried over UTC days: six initial days retain EUR80/t, and the last quote is carried sixteen days to year end. They are not complete daily secondary-market observations or an operational information set. The model remains independent hourly LPs orchestrated daily, with unchanged fixed hydro and network/GSK.','',
          '## Oil generation against observed B06 output','',
          '| Country | Observed TWh | Control | Source costs | CHP25 | CHP50 |','|---|---:|---:|---:|---:|---:|']
    for i,country in enumerate(countries):text.append('| '+country+' | '+f'{observed[i]:.6f}'+' | '+' | '.join(f"{outcomes[k]['oil'][i]['model_known_hours_twh']:.6f}"for k in cases)+' |')
    text += ['', 'Matched known hours only: DE/BE/PL 8,760; SK/SI 8,758. Physical national generation can include heat-led, industrial, reserve or redispatch operation; it does not identify accepted day-ahead bids. Shared/multizone national-price pooling is excluded from these five comparisons. Full Europe oil generation is a separate modeled quantity, not compared to this five-country observed sum.','',
             '| Case | Europe modeled oil TWh | Equal-zone price MAE | Mean zonal r |','|---|---:|---:|---:|']
    for key in cases:text.append(f"| {LABELS[key]} | {outcomes[key]['oil_generation_twh']:.6f} | {outcomes[key]['prices']['equal_zone_mae']:.6f} | {outcomes[key]['prices']['mean_correlation']:.6f} |")
    text += ['', '## Germany: timing and operating hours','', '| Case | Oil MW MAE | Oil r | Modeled active hours | Oil during observed-negative-price hours (TWh) |','|---|---:|---:|---:|---:|']
    for key in cases:
        row=germany[key];r='undefined'if row['hourly_correlation']is None else f"{row['hourly_correlation']:.4f}"
        text.append(f"| {LABELS[key]} | {row['hourly_mae_mw']:.3f} | {r} | {row['model_active_hours']} | {row['model_oil_at_negative_observed_price_twh']:.6f} |")
    text += ['', '## Interpretation and limitations','',
             'A smaller annual deficit is not sufficient for acceptance. Check hourly/monthly errors and correlations, country effects and price accuracy together. Two heat-tranche sizes expose sensitivity rather than identifying a unique heat schedule. A catalogue CHP label gives a capacity bound, not evidence that this particular fraction runs every day or produces the observed national oil output. An improvement under an assumed heat credit requires dated plant/heat evidence before promotion. The next useful source work is hourly or seasonal heat/industrial operating obligations and the identities/roles of BE/PL/SK oil units; further increasing one universal heat credit is not justified by these results.','',
             'Merit-order price differences can displace other fuels and alter imports. Offer objectives include hypothetical avoided-heat credits and must not be called electricity-only fuel expenditure, complete heat-system cost or validated investment welfare. Generation differences do not resolve reservoir adaptation, reserve eligibility or forecast uncertainty.','',
             '## Verification','',
             'Independent auditor reparses auction, raw plant geography/roles and source observations; reconstructs changed costs/matrix/capacity conservation without importing the new compiler; replays all saved primals, native network components, quantities, prices and KKT/duality. Every case has all 8,760 optimal hours and zero emergency. Existing 1e-4 MW and EUR0.05 gates remain.','',
             f"Maximum native residual: {max(r['native_residual_mw']for r in a['certificates']):.3g} MW. Maximum duality gap: EUR{max(r['duality_gap_maximum_eur']for r in a['certificates']):.3g}.", '',
             f"Source/model preparation: {s['preparation_seconds']:.2f}s; producer total: {s['end_to_end_seconds']:.2f}s. New annual solve/witness times: "+', '.join(f"{key} {s['annuals'][key]['clearing_seconds']:.2f}s"for key in cases if not s['annuals'][key]['reused'])+'. Timings include witness export and are not browser latency.', '',
             'A first attempt stopped before clearing on a read-only pandas input array; its failure/source snapshot is retained. The fresh retry uses an explicit mutable copy, with a passed carbon/calendar preflight and no changed numerical or physical gate. An initial verifier stopped while comparing NumPy monthly arrays with JSON lists; the completed verification-v2 uses a lossless type conversion with unchanged checks/tolerances. No annual solve was repeated for that reporting correction.','',
             'Primary implementation references: [ASSUME flexable](https://github.com/assume-framework/assume/blob/eb3782193bcb176afccd1fbc878113aa41778a3b/assume/strategies/flexable.py), [EEX primary auctions](https://public.eex-group.com/eex/eua-auction-report/index.html). Exact formulas, bounds and source pins are in config/oil-chp-bids-2025.json and summary.json. The full earlier source audit is in thermal-bid-audit-v2/report.md.','']
    md=folder/'report.md';md.write_text('\n'.join(text));files.append(md)
    receipt=dict(producer_sha256=digest(__file__),summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(folder/'verification-v2/audit.json'),files={p.name:digest(p)for p in files})
    (folder/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(md)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);report(p.parse_args().folder.resolve())
