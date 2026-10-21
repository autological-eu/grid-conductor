"""Concise current-model publication from saved oil/CHP witness and fresh A44 targets.

No fit, source substitution, or optimization. Exactly four report figures.
"""
import csv,gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sdac_prices_2025 import ROOT,OUT,sha

MODEL=ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2'
EXPORT=ROOT/'data/bidding-zone-network-2025/sdac-explorer-v1'
PUBLIC=ROOT/'public/research/dispatch-comparison-2025'
ARTICLE=ROOT/'docs/european-physical-synthetic-clearing-2025.md'

def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def rows(path,records):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
def metrics(p,o):
    valid=np.isfinite(o)
    if not valid.any():return dict(known_hours=0,mae_eur_mwh=None,bias_eur_mwh=None,rmse_eur_mwh=None,correlation=None,within_day_mae_eur_mwh=None)
    assert valid.all();e=p-o;a=p.reshape(365,24);b=o.reshape(365,24)
    return dict(known_hours=8760,mae_eur_mwh=float(abs(e).mean()),bias_eur_mwh=float(e.mean()),rmse_eur_mwh=float(np.sqrt(np.mean(e**2))),correlation=float(np.corrcoef(p,o)[0,1]) if p.std()>1e-8 else None,within_day_mae_eur_mwh=float(abs((a-a.mean(axis=1)[:,None])-(b-b.mean(axis=1)[:,None])).mean()))
def report():
    s=json.loads((MODEL/'summary.json').read_text());a=json.loads((MODEL/'verification-v2/audit.json').read_text());assert a['status']=='passed' and a['summary_sha256']==sha(MODEL/'summary.json')
    pa=json.loads((OUT/'audit.json').read_text());assert pa['summary_sha256']==sha(OUT/'summary.json')
    ea=json.loads((EXPORT/'audit.json').read_text());assert ea['price_source_audit_sha256']==sha(OUT/'audit.json')
    manifest=json.loads((ROOT/'public/research/country-explorer-2025/manifest.json').read_text());zones=s['zones'];countries=s['countries']
    with np.load(OUT/'prices.npz') as z:observed=z['prices']
    with np.load(MODEL/'chp25.npz') as z:price=z['row_duals'][:,:len(zones)]
    info=s['annuals']['control'];controlfile=ROOT/info['witness'];assert sha(controlfile)==info['witness_sha256']
    with np.load(controlfile) as z:control=z['row_duals'][:,:len(zones)]
    comparison=[dict(zone=zone,**metrics(price[:,j],observed[:,j]),control_mae_eur_mwh=metrics(control[:,j],observed[:,j])['mae_eur_mwh']) for j,zone in enumerate(zones)]
    eligible=[r for r in comparison if r['known_hours']==8760];mae=float(np.mean([r['mae_eur_mwh'] for r in eligible]));control_mae=float(np.mean([r['control_mae_eur_mwh'] for r in eligible]));correlation=float(np.mean([r['correlation'] for r in eligible]));assert abs(mae-manifest['model']['mae_eur_mwh'])<1e-10
    with np.load(EXPORT/'aggregation.npz') as z:mix=z['model']
    es=json.loads((EXPORT/'summary.json').read_text());tech=es['technologies'];oil=[];monthrows=[]
    for c in ['DE','BE','PL','SK','SI']:
        doc=json.loads(gzip.decompress((ROOT/'public/research/country-explorer-2025'/(c+'.json.gz')).read_bytes()));area=next(r for r in doc['generation'] if r['id']=='country:'+c)
        obs=np.array([np.nan if v is None else v/10 for v in doc['series'][area['observed'][tech.index('oil')]]]);q=mix[:,es['domains'].index('country:'+c),tech.index('oil')];valid=np.isfinite(obs)
        oil.append(dict(country=c,known_hours=int(valid.sum()),observed_twh=float(obs[valid].sum()/1e6),model_matched_twh=float(q[valid].sum()/1e6),model_annual_twh=float(q.sum()/1e6),hourly_mae_mw=float(abs(q[valid]-obs[valid]).mean()),hourly_correlation=float(np.corrcoef(q[valid],obs[valid])[0,1]) if q[valid].std()>1e-8 else None,model_at_negative_observed_price_twh=float(q[valid&(observed[:,zones.index('DE-LU' if c=='DE' else c)]<0)].sum()/1e6)))
    for entry in manifest['countries']:
        d=json.loads(gzip.decompress((ROOT/'public/research/country-explorer-2025'/entry['file']).read_bytes()))
        monthrows.extend([dict(country=entry['code'],**r) for r in d['monthly']])
    PUBLIC.mkdir(exist_ok=True);rows(PUBLIC/'prices-by-zone.csv',comparison);rows(PUBLIC/'oil-generation.csv',oil);rows(PUBLIC/'national-generation.csv',monthrows)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    def save(fig,name):fig.savefig(PUBLIC/name,dpi=160,bbox_inches='tight');plt.close(fig)
    de=next(r for r in oil if r['country']=='DE');oldde=next(r for r in s['outcomes']['control']['oil'] if r['country']=='DE')
    fig,ax=plt.subplots(1,3,figsize=(12,3.6));fig.subplots_adjust(wspace=.45,top=.78,bottom=.23)
    for axis,labels,vals,title,unit in [(ax[0],['Merchant control','CHP 25%'],[control_mae,mae],'European price error','EUR/MWh MAE'),(ax[1],['Observed','Merchant','CHP 25%'],[de['observed_twh'],oldde['model_all_hours_twh'],de['model_annual_twh']],'German oil generation','TWh/year'),(ax[2],['Merchant','CHP 25%'],[oldde['hourly_mae_mw'],de['hourly_mae_mw']],'German hourly oil error','MW MAE')]:
        axis.bar(labels,vals,color=['#64748b','#2563eb','#0891b2'][:len(vals)]);axis.set_title(title);axis.set_ylabel(unit);axis.tick_params(axis='x',labelsize=8);axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
        for i,v in enumerate(vals):axis.text(i,v+max(vals)*.025,f'{v:.2f}',ha='center',fontsize=9)
        axis.set_ylim(0,max(vals)*1.18)
    fig.suptitle('Oil CHP improves dispatch quantities; European price accuracy barely changes',fontsize=13);save(fig,'overview.png')
    fuels=['Wind','Solar','Nuclear','Hydro','Gas','Coal','Other fossil','Bioenergy']
    fig,axs=plt.subplots(2,2,figsize=(12,7.3));fig.subplots_adjust(hspace=.65,top=.9,bottom=.13)
    for axis,c in zip(axs.flat,['DE','FR','ES','NO']):
        labels=[];obs=[];model=[]
        for f in fuels:
            rr=[r for r in monthrows if r['country']==c and r['fuel']==f];valid=[r for r in rr if r['observed_twh'] is not None]
            if not valid:continue
            labels.append(f+(' *' if len(valid)<12 else ''));obs.append(sum(r['observed_twh'] for r in valid));model.append(sum(r['model_twh'] for r in valid))
        x=np.arange(len(labels));axis.bar(x-.2,obs,.4,label='Ember observed',color='#334155');axis.bar(x+.2,model,.4,label='Model allocation',color='#2563eb');axis.set_xticks(x,labels,rotation=35,ha='right',fontsize=8);axis.set_ylabel('TWh (matched months)');axis.set_title(c);axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
    axs.flat[0].legend(fontsize=8);fig.suptitle('Generation mix: national Ember observations versus model allocation',fontsize=13);fig.text(.12,.015,'Country-level fuel totals, not hourly generation targets. * Partial monthly coverage. Other fossil is not oil alone.',fontsize=9);save(fig,'national-mix.png')
    fig,axs=plt.subplots(4,1,figsize=(12,9),sharex=True);fig.subplots_adjust(hspace=.45,top=.92,bottom=.10)
    # Shared January window directly answers the source/spike question; metrics use all year.
    first=14*24;last=21*24;t=np.arange(first,last)/24+1
    for axis,zone in zip(axs,['DE-LU','FR','ES','NO2']):
        j=zones.index(zone);axis.plot(t,observed[first:last,j],color='#0f172a',label='ENTSO-E day-ahead (hourly)',lw=1);axis.plot(t,price[first:last,j],color='#2563eb',label='Oil CHP 25% model',lw=1);axis.set_ylabel('EUR/MWh');axis.set_title(zone,loc='left',fontsize=10);axis.grid(alpha=.15)
    axs[0].legend(fontsize=8,ncol=2);axs[-1].set_xlabel('January 2025 day (UTC); 15–21 January shown');fig.suptitle('Corrected observed prices and remaining hourly spike errors',fontsize=13);save(fig,'daily-prices.png')
    fig,axis=plt.subplots(figsize=(12,8));axis.set_axis_off();cols=6
    for i,row in enumerate(comparison):
        x=i%cols;y=i//cols;v=row['mae_eur_mwh'];color='#e2e8f0' if v is None else plt.cm.YlOrRd(min(v/60,1)*.8+.05)
        axis.add_patch(plt.Rectangle((x,y),.94,.88,facecolor=color,edgecolor='white'));axis.text(x+.47,y+.23,row['zone'],ha='center',va='center',fontsize=10);axis.text(x+.47,y+.58,'No target' if v is None else f'€{v:.2f}',ha='center',va='center',fontsize=11,fontweight='bold')
    axis.set_xlim(0,6);axis.set_ylim(8,0);axis.set_title('Full-year hourly price MAE by modeled zone (EUR/MWh)\nAll 41 complete targets retained; seven areas stay unknown',pad=20);save(fig,'zone-mae-grid.png')
    specific='\n'.join(f"| {r['zone']} | {r['mae_eur_mwh']:.2f} | {r['bias_eur_mwh']:.2f} | {r['correlation']:.3f} |" for r in comparison if r['zone'] in ['DE-LU','AT','DK1','DK2','FR','ES','NO1','NO2','NO3','NO4','NO5'])
    oiltable='\n'.join(f"| {r['country']} | {r['known_hours']:,} | {r['observed_twh']:.4f} | {r['model_matched_twh']:.4f} | {r['hourly_mae_mw']:.2f} |" for r in oil)
    cert=next(r for r in a['certificates'] if r['case']=='chp25');improve=(1-de['hourly_mae_mw']/oldde['hourly_mae_mw'])*100
    text=f'''# European hourly clearing: current oil/CHP model

Updated 22 October 2026. **The current displayed model includes daily oil costs and a simple CHP heat credit. Germany's hourly oil-generation error falls by {improve:.1f}%, but European price accuracy remains far from the below-€10/MWh goal.** The full-year comparison now uses audited ENTSO-E main day-ahead prices, averaged to UTC hours.

[Explore any country, its generation sources and hourly prices](/countries/) · [Denmark, 1–20 January (hourly)](/countries?country=DK&start=2025-01-01&end=2025-01-20&resolution=hourly)

## 1. What the model clears

Fixed hourly demand meets synthetic generator offers in **48 modeled market areas**, through a **145-bus PyPSA-Eur-derived physical backbone**. All **8,760 hours of 2025** are cleared under model transmission constraints. Daily grouping runs independent hourly LPs: it does not add commitment, battery arbitrage or adaptive reservoir optimisation.

- **Demand and geography:** retained ENTSO-E/PyPSA-Eur input and geographical allocation; source-country labels and bidding zones are distinct. Coverage and allocation proxies remain.
- **Wind and solar:** original processed weather profiles and IRENA end-2024/end-2025 capacity trajectories, with assumed linear commissioning. Availability is never replaced by observed generation or dispatch.
- **Hydro:** the retained, water-audited fixed hourly reservoir schedule, including NVE-backed Norwegian reconciliation; run-of-river remains a supply resource. Reservoir output cannot adapt to a new investment.
- **Thermal and nuclear bids:** fuel, efficiency, carbon and variable-cost anchors plus saved monotone gas/coal blocks and calibrated seasonal/local-clock/weekly adjustments. The retained joint checkpoint also includes an inverse gas/coal/nuclear bid correction. Those non-oil coefficients are frozen. Non-oil fuel anchors remain inherited monthly World Bank/ECB inputs and coal/lignite/carbon assumptions; daily gas prices were not adopted.
- **Network:** model PTDFs, static generation-shift keys and bounded/lossy controllable links. The retained joint fit uses 15% higher effective Nordic-incident AC ratings. This is a calibration assumption, not measured extra capacity or a certified JAO commercial domain.

This is a transparent zonal-dispatch approximation inspired by market clearing, **not EUPHEMIA or a reconstruction of actual order books**. The workbench's two-zone scenario engine and formally accepted research baseline are unchanged; this report and the country explorer show the newer verified oil/CHP checkpoint.

## 2. What changed in oil supply

The audited annual ENTSO-E A68/A33 B06 inventory fills only three missing oil fleets: **PL 392.535 MW, SK 259 MW and SI 58 MW**. Existing fleets remain. Installed nameplate is treated as available supply, not proof of hourly operational readiness. IRENA covers renewable capacity and does not supply these fossil-oil figures.

Oil's merchant offer is `(fuel + carbon × emissions factor) / electrical efficiency + variable O&M`. Fuel uses daily **EIA Brent and ECB exchange rates**; Brent is a crude-price proxy, not the delivered plant fuel product. The inherited efficiency (typically 35%), thermal emissions factor (0.2571 t/MWh) and operating cost (€8.0148/MWh electrical) remain assumptions.

EU/EEA oil carbon uses dated **EEX T3PA primary-auction prices**, carried forward: the first 144 hours use €80/t, and the longest carry is 16 days. Outside that jurisdiction the retained €80/t remains unresolved. Primary auctions are not a complete daily spot series.

For **25% of source-labelled, geographically matched oil CHP capacity**, an optional cheaper tranche subtracts an avoided-heat credit: `(0.5 / electrical efficiency) × (monthly gas + carbon × 0.198) / 0.9`. Useful-heat efficiency 0.5 and alternative-boiler efficiency 0.9 are explicit proxies. The remaining capacity keeps the merchant bid. Total hourly MW is conserved; there is no forced heat generation, measured heat-demand schedule or new energy. This tranche is not fitted to electricity prices or oil generation. All non-oil bids, weather, fixed hydro, demand and physical constraints stay frozen.

## 3. Full-year results

**European price MAE is €{mae:.2f}/MWh**, the equal-weight mean of 41 complete zonal MAEs over all 8,760 hours; mean zonal correlation is **{correlation:.3f}**. The same frozen model with merchant oil bids, missing-capacity additions and daily oil costs scores **€{control_mae:.2f}/MWh** against these same corrected observations. Oil CHP improves generation, not aggregate price accuracy.

![European price error and German oil-generation improvement](/research/dispatch-comparison-2025/overview.png)

| Zone | Price MAE €/MWh | Bias €/MWh | Correlation |
| --- | ---: | ---: | ---: |
{specific}

The hourly error is $e_t = p_t^{{model}} - p_t^{{ENTSO-E}}$; zonal $MAE = (1/8760) \\sum_t |e_t|$. Positive bias means model overpricing. All zones and adverse results are in the CSV and explorer. Seven modeled areas lack complete observed targets; none is assigned a zero error.

![Full-year price MAE for every modeled zone](/research/dispatch-comparison-2025/zone-mae-grid.png)

Germany produces **{de['model_annual_twh']:.3f} TWh oil** against **{de['observed_twh']:.3f} TWh observed**; hourly oil MAE falls from **{oldde['hourly_mae_mw']:.2f} to {de['hourly_mae_mw']:.2f} MW**. Its hourly oil correlation is only **{de['hourly_correlation']:.3f}**. This is partial recovery, not a solved timing model. The other four comparable countries still dispatch no oil, despite observed output. Physical B06 output is not necessarily day-ahead market-accepted generation.

| Country | Matched hours | Observed oil TWh | Model oil TWh | Hourly MAE MW |
| --- | ---: | ---: | ---: | ---: |
{oiltable}

![National generation by fuel compared with original monthly Ember observations](/research/dispatch-comparison-2025/national-mix.png)

Generation totals are **availability-proportional allocations within aggregated equal-offer groups**, not independently identified plant dispatch. The country explorer supplies conditional lower/upper allocation bounds and original source rows. Ember is monthly and national; IRENA is capacity, not hourly generation. Hourly ENTSO-E generation is shown only where original PSR/geographical coverage exists. Missing NO5 prevents a complete Norwegian national hourly source total; its available zonal observations remain visible. Ember's “Other fossil” is broader than oil.

![Hourly prices in Germany, France, Spain and Norway during 15–21 January](/research/dispatch-comparison-2025/daily-prices.png)

The January plot answers the spike question with the corrected auction. On 20 January at 16:00 UTC (17:00 CET), DE-LU's actual day-ahead price is **€583.40/MWh**; on 15 January at the same hour it is **€377.99/MWh**. Missing scarcity premiums, operational constraints, hydro response and imperfect supply/network inputs remain possible contributors. These plots do not establish causal error shares. All headline metrics use the entire year, including negative and extreme prices.

## 4. Observed prices, provenance and verification

**Every observed comparison price comes from ENTSO-E A44**, in EUR/MWh, for the requested zone. Main day-ahead contract A01 is required; A07 intraday is excluded. Germany and Austria explicitly use **auction sequence 1 (SDAC)**, with no fallback to sequence 2. Other cached markets use their sole unclassified A01 series; non-coupled markets are not labelled SDAC. Four published quarter-hour samples are required for each UTC-hour mean; published block curves are expanded, while missing points remain missing.

The earlier research importer incorrectly preferred the highest auction sequence in DE-LU and Austria. This publication rebuilds the targets from original XML and independently replays all hourly cells. A separate Energy-Charts/SMARD check agrees **exactly for all 8,760 hours in DE-LU, AT, DK1 and DK2**; that reference never substitutes for ENTSO-E observations. Denmark's targets do not change. The map's archived prices also agree wherever covered; its existing coverage is preserved.

**No model was refitted or re-solved for this source correction.** We re-evaluate the saved verified annual oil/CHP solution. Its non-oil calibration used the earlier auction targets, so the updated MAE is a corrected-target evaluation of that frozen model—not evidence of a new correctly targeted fit, forecasting validation or recovered real bids. Earlier research MAEs are historical retained-target scores and should not be compared directly with the corrected scores here.

The displayed witness has 8,760 optimal hours and zero emergency supply. Its independent native-equation residual is **{cert['native_residual_mw']:.3g} MW**, maximum duality gap **€{cert['duality_gap_maximum_eur']:.3g}**, and objective replay error **€{cert['objective_error_eur']:.3g}**, within the original gates. The original annual clearing loop took **{s['annuals']['chp25']['clearing_seconds']:.2f}s**; input preparation and independent audit are separate costs. Numerical feasibility does not certify empirical accuracy.

The new export independently replays all countries' saved dispatch allocations, source generation, prices, original IRENA cells and Ember rows before publication. Hourly downloads round generation to 0.1 MW and prices to €0.001/MWh; summary scores use unrounded arrays. Country source coverage, shared DE-LU/IE-SEM areas and conditional bounds remain explicit.

## Conclusion

The heat-credit oil bid recovers meaningful German oil generation without forcing output or relaxing the network. It leaves large price and generation gaps. **Correct auction identity is now verified for the published comparisons; the next modeling step is to re-establish calibration against these corrected targets before interpreting further price improvements.** This checkpoint does not validate investment returns, adaptive storage or future-year forecasts.

- [All-zone full-year price metrics](/research/dispatch-comparison-2025/prices-by-zone.csv)
- [Matched-hour oil generation](/research/dispatch-comparison-2025/oil-generation.csv) · [Monthly country/fuel generation](/research/dispatch-comparison-2025/national-generation.csv)
- [Compact source and verification receipt](/research/dispatch-comparison-2025/summary.json) · [Country data and downloads](/countries/) · [Workbench methodology](/docs/workbench-methodology/)

Original bulk sources, calibration receipts and hourly solver witnesses remain outside Git. Data providers: [ENTSO-E](https://transparency.entsoe.eu/), [IRENA](https://www.irena.org/Publications), [Ember](https://ember-energy.org/data/), [NVE](https://www.nve.no/), [EIA](https://www.eia.gov/), [ECB](https://www.ecb.europa.eu/), [EEX](https://www.eex.com/), and the retained [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) source lineage. Independent price check: [Energy-Charts API](https://api.energy-charts.info/), CC BY 4.0 Bundesnetzagentur/SMARD.
'''
    ARTICLE.write_text(text)
    # Replace obsolete report-only tables; original research receipts/witnesses remain untouched.
    names={'overview.png','national-mix.png','daily-prices.png','zone-mae-grid.png','prices-by-zone.csv','oil-generation.csv','national-generation.csv','summary.json'}
    for p in PUBLIC.iterdir():
        if p.is_file() and p.name not in names:p.unlink()
    summary=dict(schema_version=2,status='verified_saved_oil_chp25_re_evaluated_against_corrected_entsoe',hours=8760,days=365,modeled_zones=48,observed_price_zones=41,model_case='chp25',model_id=manifest['model']['id'],mae_eur_mwh=mae,control_mae_eur_mwh=control_mae,mean_zonal_correlation=correlation,model_summary_sha256=sha(MODEL/'summary.json'),witness_sha256=sha(MODEL/'chp25.npz'),model_audit=a,price_source_audit=pa,price_summary_sha256=sha(OUT/'summary.json'),price_audit_sha256=sha(OUT/'audit.json'),country_export_audit=ea,country_manifest_sha256=sha(ROOT/'public/research/country-explorer-2025/manifest.json'),renderer_file=Path(__file__).name,renderer_sha256=sha(__file__),article_sha256=sha(ARTICLE),oil=oil,zones=comparison,assets={p.name:sha(p) for p in PUBLIC.iterdir() if p.name!='summary.json'},limitations=manifest['limitations'])
    write(PUBLIC/'summary.json',summary);print('Publication prepared',mae,control_mae,correlation,flush=True)

if __name__=='__main__':report()
