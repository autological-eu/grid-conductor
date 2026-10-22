"""Concise annual source comparison, all-zone CSV and two scientific figures."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
EU=set('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split())
LABEL={'control':'Current model','solar_interval':'Solar alignment only','de_capacity':'German stock only','solar_capacity':'Both corrections'}


def report():
    s=json.loads((OUT/'summary.json').read_text());a=json.loads((OUT/'audit.json').read_text());p=json.loads((OUT/'inputs.json').read_text())
    assert a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['status']=='all_35040_hourly_source_native_and_optimality_replays_passed'
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_annual_solar_alignment_2025.py')
    cases=s['design']['cases'];zones=p['zones'];metrics=a['metrics'];known=sorted([j for j,r in enumerate(metrics['control']) if r['hours']==8760],key=lambda j:zones[j])
    eu=[j for j in known if zones[j][:2] in EU];countries=sorted({zones[j][:2] for j in known})
    report_dir=ROOT/'research';assets=report_dir/'assets';report_dir.mkdir(exist_ok=True);assets.mkdir(exist_ok=True)
    csv_path=report_dir/'solar-alignment-2025-by-zone.csv'
    fields=['zone','country_group','eu','case','hours','mae','bias','rmse','correlation','ramp_mae','tail_mae']+[f'month_{m:02d}_mae' for m in range(1,13)]
    csv_rows=[]
    for case in cases:
        for row in metrics[case]:
            record={k:row.get(k) for k in fields if not k.startswith('month_')}
            record.update(country_group=row['zone'][:2],eu=row['zone'][:2] in EU,case=case)
            record.update({f'month_{m:02d}_mae':row.get('monthly_mae',[None]*12)[m-1] for m in range(1,13)})
            csv_rows.append(record)
    with csv_path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(csv_rows)
    # Verify every written rounded-independent number before binding the export.
    with csv_path.open() as f:
        for actual,expected in zip(csv.DictReader(f),csv_rows,strict=True):
            for k,v in expected.items():
                if isinstance(v,(int,float)) and not isinstance(v,bool):assert abs(float(actual[k])-v)<1e-10
                elif v is None:assert actual[k]==''
                else:assert actual[k]==str(v)
    plt.rcParams.update({'font.size':10})
    width=7;height=int(np.ceil(len(known)/width));fig,axes=plt.subplots(height,width,figsize=(13,1.45*height))
    changes=np.array([metrics['solar_interval'][j]['mae']-metrics['control'][j]['mae'] for j in known]);limit=max(1.,float(abs(changes).max()))
    norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit)
    for ax in axes.flat:ax.set_visible(False)
    for ax,j,change in zip(axes.flat,known,changes):
        ax.set_visible(True);ax.set_facecolor(plt.cm.RdBu_r(norm(change)))
        ink='white' if abs(change)>.65*limit else 'black'
        ax.text(.5,.75,zones[j],ha='center',va='center',weight='bold',color=ink,transform=ax.transAxes)
        ax.text(.5,.42,f"{metrics['control'][j]['mae']:.2f} → {metrics['solar_interval'][j]['mae']:.2f}",ha='center',color=ink,transform=ax.transAxes)
        ax.text(.5,.13,f'Δ {change:+.2f}',ha='center',color=ink,transform=ax.transAxes);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('All 8,760 hours: current → solar-aligned price MAE (€/MWh)\nBlue improves; red worsens. No bid refit. All complete observed-price zones.',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.92));fig.savefig(assets/'annual-solar-alignment-zones.png',dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for case in cases:
        monthly=np.mean([metrics[case][j]['monthly_mae'] for j in eu],axis=0)
        axes[0].plot(range(1,13),monthly,marker='o',ms=3,label=LABEL[case])
        axes[1].bar(LABEL[case],s['cases'][case]['eu_mae'])
    axes[0].set_xticks(range(1,13));axes[0].set_xlabel('2025 UTC calendar month');axes[0].set_ylabel('EU equal-zone price MAE, €/MWh');axes[0].legend(fontsize=8)
    axes[1].set_ylabel('Full-year EU equal-zone MAE, €/MWh');axes[1].tick_params(axis='x',labelrotation=20)
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(assets/'annual-solar-alignment-eu.png',dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    old=s['cases']['control'];solar=s['cases']['solar_interval'];both=s['cases']['solar_capacity'];better=int((changes<0).sum());worse=int((changes>0).sum())
    country_rows=[]
    for code in countries:
        ids=[j for j in known if zones[j][:2]==code];all_ids=[j for j,z in enumerate(zones) if z[:2]==code]
        country_rows.append(dict(code=code,coverage=f'{len(ids)}/{len(all_ids)}',zones=', '.join(zones[j] for j in ids),
            **{case:float(np.mean([metrics[case][j]['mae'] for j in ids])) for case in cases}))
    lines=['# Full-year 2025 solar-alignment comparison','','Verified research comparison, 22 October 2026. Public model and accepted baseline unchanged.','',
        '## Result','',
        f"Solar alignment alone changes full-year **European MAE {old['europe_mae']:.3f} → {solar['europe_mae']:.3f} €/MWh** and **EU MAE {old['eu_mae']:.3f} → {solar['eu_mae']:.3f} €/MWh**. Of {len(known)} complete price zones, {better} improve and {worse} worsen. These are actual 8,760-hour clearing comparisons, not extrapolated January results.",'',
        'The earlier January improvement came from German thermal-stock reconciliation. Solar timing alone slightly worsened that event-week MAE. The fixed four-case design below separates the two effects across the full year. No bids were refitted or case selected by observed price.','',
        '| Case | Europe MAE | EU MAE | Mean Europe r | Emergency MWh | Annual clearing seconds |','|---|---:|---:|---:|---:|---:|']
    for case in cases:
        row=s['cases'][case];corr=np.mean([metrics[case][j]['correlation'] for j in known])
        lines.append(f"| {LABEL[case]} | {row['europe_mae']:.3f} | {row['eu_mae']:.3f} | {corr:.3f} | {row['emergency_mwh']:.6f} | {row['annual']['clearing_seconds']:.2f} |")
    lines+=['','MAE is €/MWh. Control reuses the independently audited current oil/CHP25 witness; zero seconds means no repeated solve. Other timings include the clearing driver and witness save, excluding source preparation and independent audit. Cases with any emergency use fail supply-model acceptance even if price errors improve.','',
        '![EU monthly and annual price errors](assets/annual-solar-alignment-eu.png)','','## What changes','',
        '**All countries:** original ERA5/atlite PV coefficients label the preceding hour. Move the coefficient at t+1 to market interval [t,t+1), for both fixed and tracked solar. Keep destination-hour IRENA 2024→2025 linear commissioning, source-country/plant geography, offer tranches and original arrays. Solar and wind may share a bid group; only its reconstructed solar contribution changes. Wind timing, bids, observed demand, fixed hydro, network/GSK, links, branch ratings and offsets remain unchanged.','',
        '**German stock sensitivity only:** use the separately audited SMARD annual net stock factors: hard coal 20.352→15.951 GW, lignite 19.457→15.178 GW, gas 36.896→36.614 GW. These annual totals are not hourly available/offered fleet or proof of outages on a particular date. No other country gets an unverified capacity correction.','',
        f"**Year endpoint:** the cache ends at 2025-12-31 23:00 UTC, so the shifted last hour requires a 2026-01-01 00:00 UTC coefficient. That coefficient is explicitly model-derived zero, not a retrieved ERA5 observation. Atlite solar elevation across every weather cell and minute of the full 23–24 UTC interval is at most {p['endpoint']['maximum_sampled_altitude_degrees']:.2f}°; an independent NOAA geometry calculation gives {a['endpoint']['independent_solar_maximum_degrees']:.2f}°. A conservative 2° margin stays below the converter's 1° irradiation cutoff. Zero irradiation produces exactly zero in the retained CSi panel model. This proves the endpoint identity without weather interpolation, circular wrapping or observed-generation substitution. Daylight missing endpoints are rejected.",'',
        '## Per-zone price errors','',
        '![All-zone annual MAE comparison](assets/annual-solar-alignment-zones.png)','',
        '[All 48 zones × four cases: annual/monthly MAE, bias, RMSE, correlation, hourly-ramp MAE and top-5%-observed-price MAE](solar-alignment-2025-by-zone.csv). Unknown targets remain missing, not zero errors.','',
        '## Country overview','',
        'These are equal averages over the listed complete price zones, not demand-weighted national prices. European/EU aggregates weight each unique zone once. DE-LU is shared with Luxembourg and not duplicated; country grouping lists it under DE. Italy and France have incomplete modeled-zone coverage. Shared IE-SEM and other unavailable targets are excluded.','',
        '| Country group | Covered/model zones | Current MAE | Solar only | DE stock only | Both |','|---|---:|---:|---:|---:|---:|']
    for row in country_rows:lines.append(f"| {row['code']} | {row['coverage']} | {row['control']:.2f} | {row['solar_interval']:.2f} | {row['de_capacity']:.2f} | {row['solar_capacity']:.2f} |")
    missing=[z for j,z in enumerate(zones) if j not in known];eu_groups=sorted({zones[j][:2] for j in eu})
    lines+=['',f"Coverage: {len(zones)} modeled zones, {len(known)} complete price zones; EU subtotal uses {len(eu)} zones grouped under {len(eu_groups)} country codes ({', '.join(eu_groups)}), with Luxembourg sharing DE-LU. This is the covered EU network, not complete coverage of all 27 member states. No complete targets for: {', '.join(missing)}.",'',
        '## Verification and interpretation','',
        f"Independent audit replays **35,040 hourly LP witnesses**, including the reused control: original source profiles, full-year clock/capacity/geographic pooling, native component balances/AC branch limits, offer/link bounds, objectives and full primal/dual optimality. Maximum native residual {max(c['native_residual_mw'] for c in a['cases'].values()):.3g} MW; maximum duality gap €{max(c['duality_gap'] for c in a['cases'].values()):.3g}. Original feasibility and optimality gates are unchanged. Three boundary tests verify the nighttime identity, reject missing daylight coefficients and check zero-output panel behavior.",'',
        'All prices are original corrected ENTSO-E main day-ahead hourly targets; published quarter-hour prices are averaged only when all four observations exist. DE-LU/AT use SDAC sequence 1. SMARD provides the German capacity sensitivity, not price targets. Original bids retain non-oil calibration to earlier incorrectly selected targets: this remains an in-sample reconstruction with inherited calibration limitations, not forecast accuracy or recovered auction bids. Timing semantics must follow the source contract even where price MAE worsens. An hourly energy-mix improvement, asset-value validation or annual model promotion cannot be inferred from price error alone.','',
        'The solar input issue affects the shared historical network-dispatch pipeline and its downstream witnesses, including the current public country explorer. This study preserves those historical files and evaluates corrected copies. It does not establish an effect on the separate observed-price/flow congestion-rent computation or automatically replace the two-node browser scenario engine.','',
        '## Conclusion','',
        'The timing correction fixes a shared input contract, but does not by itself improve annual price recovery with the inherited bids. Keep that distinction explicit: prices may have been calibrated around other input errors, while weather magnitude, available/offered fleet and network constraints retain separate uncertainties. This comparison does not identify which uncertainty explains the remaining error. Further source reconciliation and any corrected-input bid recalibration require fresh provenance; do not choose a physically incorrect clock simply because its MAE is lower.','',
        'Source/case plan: `config/annual-solar-alignment-2025.json`. Ignored authoritative evidence: `data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.json`, `summary.json`, `audit.json`, raw annual witnesses and `report-receipt.json`. Source URLs and original hashes remain chained to the January source audit, corrected-price audit and frozen oil/CHP checkpoint. Six historical explorer validation-file hashes are checked against their exact archived bytes at Git commit 5e1fe632861f402029047e3d1ca0c384a2b6212f, because the user later replaced those public exports; no old hash is waived and no obsolete public data is restored. The previous [January investigation](january-scarcity-2025.md) remains separate.','']
    path=report_dir/'solar-alignment-2025.md';path.write_text('\n'.join(lines))
    receipt=dict(producer_sha256=digest(__file__),audit_sha256=digest(OUT/'audit.json'),summary_sha256=digest(OUT/'summary.json'),
        report_sha256=digest(path),csv_sha256=digest(csv_path),figures_sha256={n:digest(assets/n) for n in ['annual-solar-alignment-zones.png','annual-solar-alignment-eu.png']})
    (OUT/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))


if __name__=='__main__':report()
