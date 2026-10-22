"""Render the audited eligibility extension, compact CSV and one figure."""
import csv
import gzip
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/thermal-eligibility-v1'
LABEL=dict(solar_control='Solar-corrected control',eligibility='Reserve exclusions',
           stock_control='National-stock control',reconciled='Exclusions + reconciled stock')


def report():
    s=json.loads((OUT/'summary.json').read_text());a=json.loads((OUT/'audit.json').read_text())
    assert a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['status']=='all_35040_source_native_and_kkt_replays_passed'
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_thermal_eligibility_2025.py')
    p=json.loads((ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.json').read_text())
    # Validate the changed technology against original hourly provider records,
    # with the independently verified public export as a second rounded check.
    export=ROOT/'public/research/country-explorer-2025/DE.json.gz'
    country=json.loads(gzip.decompress(export.read_bytes()))
    area=next(r for r in country['source_generation'] if r['area']=='DE-LU')
    observed_coal=np.full(8760,np.nan);generation_sources={str(export.relative_to(ROOT)):digest(export)}
    for month in area['provenance']:
        path=ROOT/f"data/carbon-pilot/map-2025/DE-LU/{month['month']:02d}.json"
        assert digest(path)==month['processed_sha256'];generation_sources[str(path.relative_to(ROOT))]=digest(path)
        for row in json.loads(path.read_text()):
            t=int((np.datetime64(row['start'].removesuffix('Z'))-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
            assert np.isnan(observed_coal[t]);observed_coal[t]=row['generation_mwh_by_type'].get('B05',np.nan)
    assert np.isfinite(observed_coal).all()
    rounded=np.array(country['series'][area['psr']['B05']])/10
    assert abs(observed_coal-rounded).max()<=.05+1e-8
    observed_coal_twh=float(observed_coal.sum()/1e6)
    with np.load(ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.npz') as z:
        gas=z['thermal'][2];gas_ids=gas>0;event=19*24+16
        gas_mw=gas[gas_ids]*p['capacity'][2]['factor']
        gas_max_bid=float(z['cost'][event,gas_ids].max())
    with np.load(ROOT/s['cases']['reconciled']['annual']['witness']) as z:
        gas_unused=float((gas_mw-z['values'][event,:p['ng']][gas_ids]).sum())
    folder=ROOT/'research';csv_path=folder/'thermal-eligibility-2025-by-zone.csv'
    rows=[dict(case=case,**r) for case,data in a['metrics'].items() for r in data]
    with csv_path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    zi=p['zones'].index('DE-LU');sl=slice(14*24,21*24)
    observed=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices']
    fig,ax=plt.subplots(1,2,figsize=(12,4));dates=pd.date_range('2025-01-01',periods=8760,freq='h')[sl]
    ax[0].plot(dates,observed[sl,zi],color='black',label='Observed SDAC',lw=1.5)
    for case,r in s['cases'].items():
        path=ROOT/r['annual']['witness'];assert digest(path)==r['annual']['witness_sha256']
        with np.load(path) as z:prices=z['row_duals'][sl,zi]
        ax[0].plot(dates,prices,label=LABEL[case],lw=.9)
    ax[0].set_ylabel('German price, €/MWh');ax[0].set_xlabel('January 2025, UTC');ax[0].tick_params(axis='x',rotation=30)
    ax[0].legend(fontsize=7)
    keys=list(s['cases']);values=[s['cases'][k]['german_coal_dispatch_twh'] for k in keys]
    ax[1].barh([LABEL[k] for k in keys],values)
    ax[1].axvline(observed_coal_twh,color='black',ls='--',label=f'ENTSO-E B05: {observed_coal_twh:.2f} TWh')
    ax[1].set_xlabel('Full-year German hard-coal generation, TWh');ax[1].set_xlim(0,max(values)*1.14);ax[1].legend(fontsize=8)
    for i,k in enumerate(keys):ax[1].text(values[i]+.2,i,f'{values[i]:.2f}',va='center',fontsize=8)
    for axis in ax:axis.grid(axis='y',alpha=.2)
    fig.suptitle('Dated German reserve eligibility — source correction, no bid fit');fig.tight_layout()
    image=folder/'assets/thermal-eligibility-2025.png';fig.savefig(image,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig)
    lines=['## Implemented reserve-eligibility test — 22 October 2026','',
        'The first source correction is now implemented and independently checked for all 8,760 hours. It removes Bexbach, Weiher and Bergkamen from ordinary market supply: **2,101.6 MW on the retained source-unit basis**. It does not reproduce the January spike or establish that all remaining gas capacity is market-eligible. No new scarcity markup was fitted and no public model was replaced.','',
        '| Case | Europe MAE | DE-LU MAE | Jan 20 price | DE coal TWh | Coal offered GW | New solve seconds |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for case,r in s['cases'].items():
        seconds=0 if r['annual']['reused'] else r['annual']['clearing_seconds']
        lines.append(f"| {LABEL[case]} | {r['europe_mae']:.3f} | {r['german_mae']:.3f} | {r['event_price']:.2f} | {r['german_coal_dispatch_twh']:.3f} | {r['german_coal_available_mw']/1000:.3f} | {seconds:.2f} |")
    lines += ['','Prices/MAE are €/MWh; event is January 20, 16 UTC, observed **583.40**. Coal TWh is modeled dispatch, not an observed-generation validation. MAE weights 41 complete European price zones equally. The 48-zone physical model includes seven zones without complete price targets; no zero-fill. Controls reuse exact audited annual witnesses; timings exclude preparation and independent replay.','',
        f"**Spike check:** every case still misses all 40 observed German hours above €300/MWh and generates no false German exceedances. The reconciled case leaves **{gas_unused/1000:.2f} GW** unused in the unchanged German gas offer inventory at the event, all bid at or below **€{gas_max_bid:.2f}/MWh**. These are model quantities, not measured real-world availability. The reserve correction therefore has not resolved the cheap-gas discrepancy.",'',
        f"**Generation check:** the original complete ENTSO-E B05 hourly source sums to **{observed_coal_twh:.3f} TWh** for Germany. Reserve exclusion changes modeled coal from {s['cases']['solar_control']['german_coal_dispatch_twh']:.3f} to {s['cases']['eligibility']['german_coal_dispatch_twh']:.3f} TWh; stock reconciliation changes {s['cases']['stock_control']['german_coal_dispatch_twh']:.3f} to {s['cases']['reconciled']['german_coal_dispatch_twh']:.3f}. This checks the affected technology, not the entire generation mix. Germany's source is a national proxy under the DE-LU area code, excluding Luxembourg. Pure coal offer columns are independently established by the annual audit. Original processed hourly observations are hashed and checked against the separately audited rounded public export (≤0.05 MW per hour); none enter availability or bids.",'',
        '![Eligibility event and annual generation comparison](assets/thermal-eligibility-2025.png)','',
        '[All 41 price zones × four cases: MAE, bias, correlation, >€300 observed-price error, missed spikes and false spikes](thermal-eligibility-2025-by-zone.csv).','',
        '### Identification and evidence','',
        'The [28 February 2024 BNetzA decision for Bexbach/Weiher](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Erzeugungskapazitaeten/Systemrelevante_KW/_DL/AmprionGmbH_II_28022024.pdf?__blob=publicationFile&v=2), p2, documents their existing grid-reserve binding through March 2025 and renewal through March 2031. The [Bergkamen decision](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Erzeugungskapazitaeten/Systemrelevante_KW/_DL/AmprionGmbH_III_28022024.pdf?__blob=publicationFile&v=2), p2, covers November 2024–March 2026. The [April 2024 regulator announcement](https://www.bundesnetzagentur.de/SharedDocs/Pressemitteilungen/EN/2024/20240430_Netzreserve_Pb.html) confirms temporary market returns had ended and reserve plants cannot operate in the market. This establishes role coverage for all modeled 2025 hours; dates outside 2025 are not an hourly outage reconstruction.','',
        '| Source row | Source plant | Regulator identity | Source MW removed |',
        '|---|---|---|---:|',
        '| 2574 | Weiher | Weiher 3 / SEE906326984744 | 655.6 |',
        '| 2594 | Bexbach | Bexbach A / SEE954971534470 | 726.0 |',
        '| 2581 | Bergkamen | Bergkamen A / SEE930673793902 | 720.0 |','',
        'These are manually reviewed aliases, enforced by exact source row/name/country/fuel/bus/MW assertions; the original source rows do not contain the regulator SEE identifiers. Group nameplate totals are replayed against the original native network before mapping through original offer shares. Source MW are retained consistently: the current regulator list rounds Weiher to 656 and reports Bergkamen at 717 MW; neither is silently substituted. The reserve-analysis dispatch table\'s lower requested MW are not unit nameplate. This is a bounded, partial ledger rather than a complete German fleet reconciliation.','',
        '### Avoiding double-counting','',
        'The eligibility-only case removes these source units from the solar-corrected, unscaled hard-coal fleet. The reconciled case first removes them, then scales the remaining source coal to the same **15.951 GW** national-stock total used by the stock control: 15,951 / (20,351.945 − 2,101.6). It retains that control\'s gas/lignite stock factors. Thus the comparison tests offer composition at a common total instead of subtracting the reserves twice. Whether the SMARD annual-stock series already excludes every reserve unit is not independently certified; this is explicitly an overlap sensitivity. Retained identical-price pools do not uniquely identify individual unit dispatch.','',
        '### Verification, limits and next action','',
        f"Two new annual solves and two reused controls pass independent source/volume replay, all 35,040 hourly KKT checks and native component/network bounds. Maximum native residual **{max(r['native_residual_mw'] for r in a['cases'].values()):.3g} MW**; maximum duality gap **{max(r['duality_gap'] for r in a['cases'].values()):.3g} EUR**. Every case uses zero emergency energy. Three contract tests cover identity mismatches/duplicate rows, German-local effective dates and stock/reserve overlap. Original files, PV/wind/IRENA, demand, fixed hydro, grid/GSK and bids are preserved.",'',
        'The three exclusions improve source realism but do not explain the expensive observed marginal bid. Do not introduce a €500 tail while large cheap modeled gas volumes remain usable. Next reconcile gas market roles, source stock/efficiency and dated outages, then test a simple online/startable gas bid structure with finite resource-backed volumes. Scholven/Mannheim overlapping source aggregates, multi-block Karlsruhe/Altbach/Heilbronn and Staudinger remain unresolved; no whole-site removal or synthetic outage was applied. This test does not validate national generation mix, investment value or exact EUPHEMIA block pricing. Existing non-oil bids retain calibration to the earlier auction targets; all 2025 has been inspected, so this is retrospective reconstruction.','']
    article=folder/'scarcity-bidding-2025.md';old=article.read_text();marker='## Implemented reserve-eligibility test — 22 October 2026'
    old=old.split(marker)[0].rstrip()
    old=old.replace('22 October 2026. Literature review and read-only replay of the verified annual\nsource-corrected book. No new market solve, fitted bid, baseline promotion or\nwebsite replacement.',
        '22 October 2026. Literature review, saved-book diagnosis and an implemented,\nindependently verified annual reserve-eligibility test. The implementation/results\nare at the end. No fitted scarcity bid, baseline promotion or website replacement.')
    old=old.replace('are concrete follow-up sources. No unit mapping has been completed here.',
        'are concrete follow-up sources. The implemented extension below matches three\nwhole plants; the remaining fleet and block-level mappings are unresolved.')
    article.write_text(old+'\n\n'+'\n'.join(lines))
    write=dict(producer_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),
        generation_source_sha256=generation_sources,observed_german_coal_twh=observed_coal_twh,
        reconciled_event_unused_gas_mw=gas_unused,reconciled_event_max_gas_bid=gas_max_bid,
        exports={str(f.relative_to(ROOT)):digest(f) for f in [article,csv_path,image]})
    (OUT/'report-receipt.json').write_text(json.dumps(write,indent=2)+'\n')


if __name__=='__main__':report()
