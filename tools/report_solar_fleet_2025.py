"""Render audited country/month/hour solar findings without publishing a new model."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from bs4 import BeautifulSoup
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
REPORT=ROOT/'research/solar-alignment-2025.md'
LABEL=dict(control='Solar-aligned control',system_losses='Overall-loss sensitivity')


def table_export(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    with path.open() as f:
        for saved,expected in zip(csv.DictReader(f),rows,strict=True):
            for k,v in expected.items():
                if v is None:assert saved[k]==''
                elif isinstance(v,(int,float)):assert abs(float(saved[k])-v)<1e-9
                else:assert saved[k]==str(v)


def report():
    a=json.loads((OUT/'audit.json').read_text());s=json.loads((OUT/'summary.json').read_text());p=json.loads((OUT/'inputs.json').read_text())
    assert a['status']=='all_17520_source_native_kkt_and_generation_replays_passed'
    assert a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_solar_fleet_2025.py')
    assert a['quantities_sha256']==digest(OUT/'quantity-diagnostics.npz')
    extra=OUT/'report-sources/receipt.json';receipts=json.loads(extra.read_text());context_hashes={str(extra.relative_to(ROOT)):digest(extra)}
    for row in receipts['sources']:
        if row['status']=='retrieved':
            file=extra.parent/row['file'];assert digest(file)==row['sha256'];context_hashes[str(file.relative_to(ROOT))]=row['sha256']
    bnetza=BeautifulSoup((extra.parent/'bnetza-2025.html').read_text(),'html.parser').get_text(' ',strip=True)
    assert 'solar installations and used by the households themselves is not included' in bnetza
    fraunhofer=BeautifulSoup((extra.parent/'fraunhofer-2025.html').read_text(),'html.parser').get_text(' ',strip=True)
    assert 'east-west' in fraunhofer and '16.9 TWh' in fraunhofer
    folder=ROOT/'research';exports=[]
    for kind,filename in [('quantities','solar-fleet-2025-countries.csv'),('monthly','solar-fleet-2025-monthly.csv')]:
        rows=[dict(case=case,**r) for case,values in a[kind].items() for r in values]
        if kind=='quantities':
            for row in rows:
                if row['hours']==0:
                    for key in ['observed_covered_twh','outside_dispatch_bounds_mwh','source_during_zero_availability_mwh']:row[key]=None
        file=folder/filename;table_export(file,rows);exports.append(file)
    price_rows=[]
    for case,record in s['cases'].items():
        for r in record['metrics']['zones']:
            price_rows.append(dict(case=case,zone=r['zone'],hours=r['known_hours'],mae=r.get('mae_eur_mwh'),bias=r.get('bias_eur_mwh'),correlation=r.get('correlation')))
    file=folder/'solar-fleet-2025-prices.csv';table_export(file,price_rows);exports.append(file)
    indexed={case:{r['country']:r for r in rows} for case,rows in a['quantities'].items()}
    examples=['DE','ES','FR','IT','NL','GB'];pos=np.arange(len(examples));fig,ax=plt.subplots(figsize=(11,5))
    for offset,case,color in [(-.26,'control','#888888'),(-.02,'system_losses','#377eb8')]:
        rows=[indexed[case][c] for c in examples];values=np.array([r['dispatch_twh'] for r in rows])
        errors=np.array([[r['dispatch_twh']-r['dispatch_lower_twh'] for r in rows],[r['dispatch_upper_twh']-r['dispatch_twh'] for r in rows]])
        ax.bar(pos+offset,values,width=.22,label=LABEL[case],color=color,yerr=errors,capsize=2,error_kw=dict(lw=.8))
    ax.bar(pos+.22,[indexed['control'][c]['ember_annual_twh'] for c in examples],width=.22,label='Ember annual Solar',color='#4daf4a')
    for i,c in enumerate(examples):
        r=indexed['control'][c]
        if r['hours']:
            ax.scatter(i,r['observed_covered_twh'],marker='D',facecolors='none',edgecolors='#d73027',zorder=5)
            ax.annotate(f"{r['hours']:,} h",(i,r['observed_covered_twh']),xytext=(0,12 if r['observed_covered_twh']<10 else -14),textcoords='offset points',ha='center',fontsize=8,color='#b2182b')
    ax.scatter([],[],marker='D',facecolors='none',edgecolors='#d73027',label='ENTSO-E covered-hour Solar')
    ax.set_xticks(pos,examples);ax.set_ylabel('2025 generation, TWh');ax.grid(axis='y',alpha=.2)
    ax.legend(fontsize=8,ncol=2);ax.set_title('Solar generation: model allocations and separate reporting scopes\nThin bars: conditional dispatch bounds; hourly coverage does not prove fleet coverage')
    fig.tight_layout();file=folder/'assets/solar-fleet-energy-2025.png';fig.savefig(file,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig);exports.append(file)
    fig,axes=plt.subplots(2,2,figsize=(12,7.5));seasons=[('Winter',[12,1,2],'#377eb8'),('Summer',[6,7,8],'#e66101')]
    for ax,c in zip(axes.flat,['DE','ES','FR','NL'],strict=True):
        for season,months,color in seasons:
            for case,style in [('control',':'),('system_losses','--')]:
                rows=[r for r in a['diurnal'][case] if r['country']==c and r['month'] in months]
                means={};lo={};hi={};obs={}
                for h in range(24):
                    group=[r for r in rows if r['hour']==h and r['samples']>0];count=sum(r['samples'] for r in group)
                    for field,store in [('model_mw',means),('lower_mw',lo),('upper_mw',hi),('observed_mw',obs)]:store[h]=sum(r[field]*r['samples'] for r in group)/count/1000 if count else np.nan
                ax.plot(range(24),list(means.values()),color=color,ls=style,label=f'{season}: {LABEL[case]}')
                if case=='system_losses':
                    ax.fill_between(range(24),list(lo.values()),list(hi.values()),color=color,alpha=.12)
                    ax.plot(range(24),list(obs.values()),color=color,label=f'{season}: ENTSO-E')
        ax.set_title(c+(' — source-scope conflict' if c=='NL' else ''));ax.set_xlabel('Local civil hour, including DST');ax.set_ylabel('Mean covered-hour output, GW');ax.set_xticks([0,6,12,18,23]);ax.grid(alpha=.2)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8)
    fig.suptitle('Winter and summer hourly shape — no replacement of missing observations\nSolid: source; dotted: control; dashed: loss sensitivity; shading: conditional allocation range',fontsize=11)
    fig.tight_layout(rect=(0,.10,1,.93));file=folder/'assets/solar-fleet-shape-2025.png';fig.savefig(file,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig);exports.append(file)
    known=[(x,y) for x,y in zip(s['cases']['control']['metrics']['zones'],s['cases']['system_losses']['metrics']['zones'],strict=True) if x['known_hours']==8760]
    better=sum(y['mae_eur_mwh']<x['mae_eur_mwh'] for x,y in known);worse=sum(y['mae_eur_mwh']>x['mae_eur_mwh'] for x,y in known)
    country=p['countries'];complete=sum(r['hours']==8760 for r in a['quantities']['control']);any_hour=sum(r['hours']>0 for r in a['quantities']['control'])
    lines=['## Solar-fleet magnitude and hourly-shape audit — 22 October 2026','',
        f"**The modeled solar supply is too high relative to several reported generation series, but source scope is a major confounder.** One documented loss sensitivity reduces Europe price MAE **{s['cases']['control']['europe_mae']:.3f} → {s['cases']['system_losses']['europe_mae']:.3f} €/MWh**. It improves {better} price zones and worsens {worse}. This small gain does not establish a corrected national fleet, and the public model remains unchanged.",'',
        '### What is modeled and what changed','',
        'Weather is hourly ERA5 on a **0.3° × 0.3° grid**, roughly21×33km in Germany, with20,567 retained cells. Atlite converts weather to PV power before PyPSA-Eur aggregates it into128 regional profiles for each panel technology. Only **123 fixed-panel source generators have positive nameplate**; every tracker generator has zero nameplate, despite the existence of cached tracking profiles. There are34 source-country fleets, later mapped into48 market zones. This is historical reanalysis, not an operational forecast.','',
        'The fixed-panel model is CSi/Huld, south-facing,35° tilt, with0.90 inverter efficiency. Country capacity follows IRENA end2024→end2025 linear commissioning; within-country source capacity/geographical weights are inherited. Regional profile layouts favor eligible productive land rather than establishing the actual location/orientation of the 2025 fleet. A fine weather grid is therefore not proof of fine installed-fleet geography.','',
        'Control is the verified solar-aligned plus German-stock source comparison. The new case replaces the existing0.90 inverter retention with the [PVGIS generic0.86 overall system retention](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en): multiply only PV by0.86/0.90, a4.44% reduction. Do not multiply a second14% loss. Existing irradiance/temperature effects stay in Huld. This is a generic sensitivity, not measured national loss or calibration to generation. Bids, wind, demand, fixed hydro, grid/GSK and all other inputs stay fixed.','',
        '| Case | Europe price MAE | Emergency MWh | New annual driver seconds |',
        '|---|---:|---:|---:|']
    for case,r in s['cases'].items():lines.append(f"| {LABEL[case]} | {r['europe_mae']:.4f} | {r['emergency_mwh']:.6f} | {0 if r['annual']['reused'] else r['annual']['clearing_seconds']:.2f} |")
    lines += ['', 'Forty-one complete SDAC price zones,48 physical zones; zero seconds means an exact reused witness. These are the same frozen bids, including the inherited earlier-target calibration limitation.','',
        '### National energy and reporting boundaries','',
        '![Generation and source coverage](assets/solar-fleet-energy-2025.png)','',
        '| Country | Control solar TWh | Loss case TWh | ENTSO-E covered TWh | Hourly coverage | Ember Solar TWh |',
        '|---|---:|---:|---:|---:|---:|']
    for c in country:
        r=indexed['control'][c];new=indexed['system_losses'][c]
        observed=f"{r['observed_covered_twh']:.3f}" if r['hours'] else 'unavailable'
        lines.append(f"| {c} | {r['dispatch_twh']:.3f} | {new['dispatch_twh']:.3f} | {observed} | {r['hours']}/8760 | "+(f"{r['ember_annual_twh']:.3f}" if r['ember_annual_twh'] is not None else 'incomplete')+' |')
    de=indexed['system_losses']['DE'];es=indexed['system_losses']['ES'];nl=indexed['control']['NL']
    lines += ['',
        f"**Germany:** modeled PV108.587→{de['dispatch_twh']:.3f}TWh versus Ember89.965 and ENTSO-E73.784. The [BNetzA 2025 report](https://www.bundesnetzagentur.de/SharedDocs/Pressemitteilungen/EN/2026/20260104_SMARD.html) explicitly excludes household self-consumption from its grid generation figures. [Fraunhofer ISE](https://www.ise.fraunhofer.de/en/press-media/press-releases/2026/german-public-electricity-generation-in-2025-wind-and-solar-power-take-the-lead.html) reports16.9TWh self-consumed PV and identifies east/west orientation as a yield factor. This supports a scope/geometry investigation; it does not justify shrinking capacity until the ENTSO-E curve matches. Reconcile demand's grid/gross boundary before splitting self-consumption from market offers, so behind-the-meter energy is not removed twice.",'',
        f"**Netherlands:** the full8760-hour ENTSO-E source totals only{nl['observed_annual_twh']:.3f}TWh versus Ember31.420. This is a major source-scope conflict; hourly completeness is not national fleet coverage. Reducing modeled output improves its error against the tiny hourly source while moving farther from Ember. Neither metric establishes the correct total. A CBS national-release reconciliation remains open: its webpage was inspectable through web research, but direct frontend/OData retrieval failed, so no CBS dataset or replacement target was ingested.",'',
        '**Spain:** B16 is Solar rather than an isolated PV measurement. [REE\'s ENTSO-E comparison definition](https://www.ree.es/en/datos/european-landscape) includes photovoltaic and solar thermal. [REE documents](https://www.sistemaelectrico-ree.es/en/renewable-energies-report/sun/generation/solar-thermal-sun-generation) that stored solar heat extends thermal output to later hours; [its renewable report](https://www.sistemaelectrico-ree.es/en/spanish-electricity-system/generation/renewable-electricity-generation) also distinguishes self-consumption. The retained IRENA2025 parent Solar47206MW exceeds PV44903MW by2303MW (rounded parent-minus-child, not an added measured generator). Our modeled PV does not represent that solar-thermal fleet/storage. Output in the observed Solar series during zero modeled PV cannot automatically be called a PV timing bug. No thermal-storage profile was invented.','',
        f"Hourly source coverage spans{any_hour} countries, with{complete} complete years. Missing constituent regions/types propagate to missing national observations. Italy, UK and Norway have no complete national hourly comparison here. France lacks6 hours, Spain37, Denmark8. Ember is monthly and national; no hourly Ember profile was manufactured. Its all-Solar and national boundaries need independent reconciliation before treating it as a PV target.",'',
        '### Hourly and seasonal shape','',
        '![Winter and summer hourly solar shapes](assets/solar-fleet-shape-2025.png)','',
        'Curves average identical covered UTC intervals grouped by local civil hour and season, including DST. Shaded ranges are conditional resource-allocation bounds inside identical-price offer pools, not confidence intervals; country bounds need not be jointly attainable. Annual modeled generation uses an availability-proportional illustration within those bounds, not identified plant dispatch.','',
        f"Germany\'s hourly correlation changes0.97094→{de['correlation']:.5f}; daily normalized-shape L1 changes0.08440→{de['daily_normalized_shape_l1']:.5f}. Spain\'s shape L1 worsens0.20988→{es['daily_normalized_shape_l1']:.5f}. This diagnostic normalizes each complete UTC day's model/source energy before summing hourly absolute differences (zero-energy days excluded). Loss scaling primarily changes magnitude; it cannot recover different orientations, tracking, cloud errors, reporting boundaries or solar-thermal night generation. France\'s unchanged shape/correlation is an explicit example.",'',
        '[Country energy, dispatch bounds, hourly MAE/correlation, daily-energy and normalized-shape diagnostics](solar-fleet-2025-countries.csv) · [All country/month energy and coverage](solar-fleet-2025-monthly.csv) · [All48 zones: price MAE/bias/correlation and missing targets](solar-fleet-2025-prices.csv). Covered-hour sums are not annual totals where hours are missing. No Europe-wide generation score is presented as comparable across incompatible source scopes.','',
        '### Verification and next correction','',
        f"The independent audit reconstructs original PV coefficients, interval shift, IRENA trajectories, original source-country mapping and all original ENTSO-E B16 observations. It replays **17520 hourly native/KKT certificates**, maximum native residual{max(r['native_residual_mw'] for r in a['cases'].values()):.3g}MW and duality gap{max(r['duality_gap'] for r in a['cases'].values()):.3g}EUR, with zero emergency. Generation allocation inequalities and original-source/export rounding are replayed. Three tests guard loss double counting, constituent missingness and mixed-offer bounds. Audit runtime{a['seconds']:.1f}s; new-driver timings exclude preparation/audit.",'',
        'The next material correction is the **fleet and measurement boundary**, followed by geometry: establish grid feed-in versus total PV and compatible demand; separate PV from solar thermal; reconcile IRENA net capacity with PVGIS DC-STC peak-power normalization; then source country/region-specific tilt, azimuth, tracking and system losses. Do not invent an AC/DC factor or use observed dispatch as available power. Germany\'s and France\'s residual surplus remains after the generic loss change, while the Netherlands gives opposing signals by source.','',
        'The compact weather cache retains converted per-cell fixed/tracking outputs and deletes original raw meteorology only after verification. It correctly rejects changed orientation/panel requests. New orientation physics therefore requires freshly retrieved radiation/temperature or independently supplied coefficients; it cannot be reconstructed by relabeling existing profiles. Existing fixed and horizontal-tracker conversions can be reused if verified fleet shares/geography become available; no shares were guessed here. The precomputation approach remains fast at clearing time. No weather collection or unseen-year validation was performed in this audit, and no model/site promotion follows from this small in-sample price improvement.','',
        'Reproduction: config/solar-fleet-audit-2025.json; tools/solar_fleet_audit_2025.py prepare/run, audit_solar_fleet_2025.py, report_solar_fleet_2025.py using the pinned interpreter and original local source caches. Sealed ignored inputs/components, annual witness, source receipts, audit, quantity arrays and renderer receipt are under data/bidding-zone-network-2025/solar-fleet-audit-v1/. Raw provider data and hourly matrices remain outside Git.','']
    marker='## Solar-fleet magnitude and hourly-shape audit — 22 October 2026';old=REPORT.read_text().split(marker)[0].rstrip()
    section='\n'.join(lines)
    for before,after in [('roughly21×33km','roughly 21 × 33 km'),('with20,567','with 20,567'),('into128','into 128'),('are34','are 34'),('into48','into 48'),('south-facing,35°','south-facing, 35°'),('with0.90','with 0.90'),('end2024→end2025','end-2024 → end-2025'),('existing0.90','existing 0.90'),('generic0.86','generic 0.86'),('by0.86/0.90','by 0.86/0.90'),('a4.44%','a 4.44%'),('second14%','second 14%'),('zones,48','zones, 48'),('full8760-hour','full 8760-hour'),('only8760','only 8760'),('all48','all 48'),('reports16.9TWh','reports 16.9 TWh'),('years, Spain37','years, Spain 37'),('lacks6','lacks 6'),('Spain37','Spain 37'),('Denmark8','Denmark 8')]:section=section.replace(before,after)
    REPORT.write_text(old+'\n\n'+section);exports.append(REPORT)
    result=dict(producer_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),
        context_source_sha256=context_hashes,exports={str(f.relative_to(ROOT)):digest(f) for f in exports})
    (OUT/'report-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Rendered country/month/hour solar audit and two figures',flush=True)


if __name__=='__main__':report()
