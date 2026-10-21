"""Append a compact, independently verified oil trial to the retained report.

Preserves the original report bytes/receipts and all four original figures.
"""
import argparse, csv, gzip, hashlib, json
from pathlib import Path
from generation_mix_2025 import ROOT, digest

MARKER='\n<!-- oil-supply-2025 -->\n'
PUBLIC=ROOT/'public/research/oil-supply-2025'
ARTICLE=ROOT/'docs/european-physical-synthetic-clearing-2025.md'
LABELS=dict(control='Unchanged joint + weekly control',daily_oil='Daily oil prices only',
            missing_capacity='Missing oil capacity only',capacity_and_daily_oil='Capacity + daily oil prices')


def csv_file(name,rows):
    with (PUBLIC/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader();w.writerows(rows)


def publish(folder):
    import numpy as np
    s=json.loads((folder/'summary.json').read_text()); a=json.loads((folder/'verification-v1/audit.json').read_text())
    assert a['status']=='passed' and a['summary_sha256']==digest(folder/'summary.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_oil_supply_2025.py')
    assert len(a['certificates'])==4 and all(c['hours']==8760 and c['emergency_mwh']<=1e-6 for c in a['certificates'])
    diagnostic=json.loads((folder/'price-witness-comparison.json').read_text())
    assert diagnostic['summary_sha256']==digest(folder/'summary.json') and diagnostic['producer_sha256']==digest(ROOT/'tools/diagnose_oil_duals_2025.py')
    changes=diagnostic['changes']['capacity_and_daily_oil']; changed=changes['changed_price_cells']
    PUBLIC.mkdir(parents=True,exist_ok=True)
    cap=json.loads((ROOT/'data/oil-market-2025/capacity.json').read_text())
    capacities=[dict(country=r['country'],year=2025,inherited_oil_mw=a['existing_oil_capacity_mw'].get(r['country'],0),
                     entsoe_a68_oil_mw=r['mw'],added_oil_mw=a['capacity_fill_mw'].get(r['country'],0),domain=r['domain'],
                     source_xml_sha256=r['sha256']) for r in cap['countries']]
    csv_file('capacity.csv',capacities)
    prices=[]; generation=[]; sources={}; explorer=ROOT/'public/research/country-explorer-2025'
    manifest=json.loads((explorer/'manifest.json').read_text()); ti=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='oil')
    observations={}
    for entry in manifest['countries']:
        path=explorer/entry['file']; assert digest(path)==entry['sha256']; sources[str(path.relative_to(ROOT))]=digest(path)
        data=json.loads(gzip.decompress(path.read_bytes())); area=next(r for r in data['generation'] if r['id']=='country:'+entry['code'])
        observations[entry['code']]=np.array([np.nan if v is None else v/manifest['generation_scale'] for v in data['series'][area['observed'][ti]]])
    for name in s['design']['cases']:
        outcome=s['outcomes'][name]
        for row in outcome['prices']['zones']:
            prices.append(dict(case=name,zone=row['zone'],known_hours=row['known_hours'],mae_eur_mwh=row.get('mae_eur_mwh'),bias_eur_mwh=row.get('bias_eur_mwh'),correlation=row.get('correlation')))
        with np.load(folder/(name+'-oil.npz')) as z: q=z['generation_mwh']
        assert digest(folder/(name+'-oil.npz'))==outcome['oil_arrays_sha256']
        for ci,country in enumerate(s['countries']):
            o=observations[country]; good=np.isfinite(o)
            generation.append(dict(case=name,country=country,model_annual_twh=float(q[:,ci].sum()/1e6),
                observed_known_hours=int(good.sum()),observed_twh=float(o[good].sum()/1e6) if good.any() else None,
                model_matched_hours_twh=float(q[good,ci].sum()/1e6) if good.any() else None))
    csv_file('prices-by-zone.csv',prices); csv_file('oil-generation.csv',generation)
    metrics=[dict(case=k,label=LABELS[k],mae_eur_mwh=v['prices']['equal_zone_mae'],mean_correlation=v['prices']['mean_correlation'],
                  oil_twh=sum(v['oil_generation_twh']),generation_score=v['quantity_errors']['generation'],trade_score=v['quantity_errors']['trade'],
                  clearing_seconds=s['annuals'][k]['clearing_seconds']) for k,v in s['outcomes'].items()]
    tables='\n'.join(f"| {r['label']} | {r['mae_eur_mwh']:.6f} | {r['mean_correlation']:.6f} | {r['oil_twh']:.6f} |" for r in metrics)
    cap_table='\n'.join(f"| {r['country']} | {r['inherited_oil_mw']:.3f} | {r['entsoe_a68_oil_mw']:.3f} | {r['added_oil_mw']:.3f} |" for r in capacities)
    selected=[]
    for country in ['DE','BE','PL','SK','SI']:
        r=next(r for r in generation if r['case']=='capacity_and_daily_oil' and r['country']==country)
        observed='Unknown' if r['observed_twh'] is None else f"{r['observed_twh']:.4f}"
        matched='Unknown' if r['model_matched_hours_twh'] is None else f"{r['model_matched_hours_twh']:.4f}"
        selected.append(f"| {country} | {observed} | {matched} | {r['observed_known_hours']} |")
    result_note=('All four cases still dispatch zero oil. Daily prices alone reproduce the control; '
                 'the capacity cases change aggregate price MAE by less than €0.000004/MWh. '
                 'There is no material price or oil-generation improvement.'
                 if all(abs(r['oil_twh'])<1e-12 for r in metrics) and max(abs(r['mae_eur_mwh']-metrics[0]['mae_eur_mwh']) for r in metrics)<.000004
                 else 'Read the full controlled results above; no automatic promotion follows.')
    section=f'''
## Oil supply: capacity and fuel-price check

Oil was already a modeled fuel, but the displayed joint + weekly checkpoint
dispatches **zero oil generation** from **{sum(a['existing_oil_capacity_mw'].values())/1000:.3f} GW** of inherited oil capacity.
The explorer's annual Ember chart grouped oil with waste as “Other fossil”; it now
also shows oil separately against ENTSO-E **B06**, including matched-hour totals.
Oil shale, peat and waste are not liquid oil. IRENA's renewable statistics cannot
supply missing oil-fired capacity.

A fresh ENTSO-E **A68/A33** annual capacity check identifies three missing fleets.
The trial adds **{sum(a['capacity_fill_mw'].values()):.3f} MW** across PL, SK and SI.
Existing fleets are retained: the other discrepancies below require broader
fleet/scope reconciliation, rather than silently replacing them all.

| Country | Inherited oil MW | ENTSO-E 2025 oil MW | Added MW |
| --- | ---: | ---: | ---: |
{cap_table}

New capacity uses each country's existing zonal balance and unchanged physical
GSK. This is a location proxy, not a plant-level reconstruction. Installed
nameplate is assumed fully available, as in the inherited thermal model; annual
capacity cells do not prove hourly availability or oil/gas fuel-switching capability.
The source reporting year runs 31 December 23:00 UTC to the next year's same
boundary; applying its capacity scalar to all 8,760 UTC model hours is explicit.

Oil offers use fuel + carbon + variable O&M: **(oil EUR/MWh thermal + CO₂ EUR/t ×
emissions t/MWh thermal) / electrical efficiency + VOM**. The control retains
monthly World Bank Brent and ECB conversion. Daily cases use retained original
2025 EIA Brent quotes and ECB daily FX, preserving the **1.7 MWh thermal/barrel**
conversion, original emissions/VOM and **0.35** default oil efficiency. Non-trading
dates carry the most recent quote for at most five days; {a['daily_oil_fallback_hours']} hours retain the
monthly anchor before both daily series begin. These are ex-post crude proxies,
not delivered diesel/fuel-oil prices or day-ahead-known quotes.

Four predeclared full-year controls keep non-oil bids and coefficients, demand,
weather, fixed hydro chronology and joint-grid constraints unchanged. No electricity
prices were fitted for this trial; the anchor remains an in-sample reconstruction.

| Full 2025 case | Equal-zone price MAE €/MWh | Mean zonal r | Modeled oil TWh |
| --- | ---: | ---: | ---: |
{tables}

| Country | ENTSO-E oil TWh on known hours | Combined trial, same hours TWh | Known hours |
| --- | ---: | ---: | ---: |
{chr(10).join(selected)}

ENTSO-E generation above uses the independently audited country exports rounded
to 0.1 MWh per hour; partial coverage is not annualised. Ember “Other fossil”
is not an oil-only validation target. All country/zone results, including missing
observations, are downloadable below. Full-year price metrics retain all 41 complete
areas and every hour, including negative and extreme prices.

**Result:** {result_note}

Adding columns also selects different dual prices in {len(changed)} zone-hours:
{sum(not r['eligible_observed_price'] for r in changed)} without complete observed-price coverage,
{sum(r['eligible_observed_price'] for r in changed)} within the evaluated areas. The largest differences are
€{changes['maximum_all_area_change']:.2f}/MWh overall and €{changes['maximum_eligible_change']:.2f}/MWh in eligible areas.
With zero oil output and objective differences below €{changes['maximum_objective_change_eur']:.5f},
these differences between optimal witnesses are not evidence of oil-driven price
improvement. Every evaluated hour remains in the annual metrics.

**Interpretation:** missing oil capacity is a real source gap, but adding nameplate
does not require oil to dispatch. Relative bids, network delivery and omitted
cogeneration/operating commitments still determine its use. This controlled test
does not establish that oil explains Europe's price errors. Do not lower bids or
turn observed generation into available supply just to force agreement. Broader
dated conventional-fleet/outage and CHP/fuel-product reconciliation remain open.
The accepted baseline and displayed country checkpoint are unchanged.

All four years have complete optimal witnesses and zero emergency. Independent
XML/quote/FX reconstruction, modified source-capacity bounds, native network
equations, primal/dual optimality, price metrics and country quantities pass the
original 1e-4 MW / €0.05 gates. Preparation {s['preparation_seconds']:.1f}s; clearing
{min(r['clearing_seconds'] for r in metrics):.1f}–{max(r['clearing_seconds'] for r in metrics):.1f}s per full year.
Audit/export time is separate from clearing time.

[Oil capacity CSV](/research/oil-supply-2025/capacity.csv) ·
[All-zone price CSV](/research/oil-supply-2025/prices-by-zone.csv) ·
[All-country oil generation CSV](/research/oil-supply-2025/oil-generation.csv) ·
[Provenance and replay receipt](/research/oil-supply-2025/summary.json).
Sources: [ENTSO-E](https://transparency.entsoe.eu/),
[EIA Brent](https://www.eia.gov/dnav/pet/hist/RBRTED.htm),
[ECB FX](https://data.ecb.europa.eu/data/datasets/EXR),
[World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets).
'''
    original=ARTICLE.read_text().split(MARKER)[0]
    comparison=json.loads((ROOT/'public/research/dispatch-comparison-2025/summary.json').read_text())
    assert hashlib.sha256(original.encode()).hexdigest()==comparison['article_sha256']
    ARTICLE.write_text(original+MARKER+section)
    result=dict(status='audited_research_trial_not_promoted',year=2025,design=s['design'],metrics=metrics,capacity=capacities,generation=generation,
                sources=s['source_hashes']|sources,source_summary_sha256=digest(folder/'summary.json'),audit=a,
                price_witness_comparison=diagnostic,
                producer_sha256=s['producer_sha256'],helper_sha256=s['helper_sha256'],renderer_sha256=digest(__file__),
                base_article_sha256=comparison['article_sha256'],article_sha256=digest(ARTICLE),section_sha256=hashlib.sha256(section.encode()).hexdigest(),
                assets={p.name:digest(p) for p in PUBLIC.glob('*.csv')})
    (PUBLIC/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);publish(p.parse_args().folder.resolve())
