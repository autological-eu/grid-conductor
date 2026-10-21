"""CI verification for the oil extension; retain the original report's hash chain."""
import csv, gzip, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MARKER=b'\n<!-- oil-supply-2025 -->\n'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    article=ROOT/'docs/european-physical-synthetic-clearing-2025.md'; raw=article.read_bytes()
    public=ROOT/'public/research/oil-supply-2025'; receipt=public/'summary.json'
    if not receipt.exists():
        assert MARKER not in raw
        return raw
    r=json.loads(receipt.read_text()); assert raw.count(MARKER)==1
    base,section=raw.split(MARKER); assert sha(article)==r['article_sha256']
    assert hashlib.sha256(base).hexdigest()==r['base_article_sha256']
    assert hashlib.sha256(section).hexdigest()==r['section_sha256']
    assert r['design']==json.loads((ROOT/'config/oil-supply-2025.json').read_text())
    assert r['status']=='audited_research_trial_not_promoted' and r['year']==2025
    for file,key in [('run_oil_supply_2025.py','producer_sha256'),('oil_supply_2025.py','helper_sha256'),('report_oil_supply_2025.py','renderer_sha256')]:
        assert sha(ROOT/'tools'/file)==r[key]
    a=r['audit']; assert a['status']=='passed' and a['summary_sha256']==r['source_summary_sha256']
    assert sha(ROOT/'tools/audit_oil_supply_2025.py')==a['auditor_sha256']
    diagnostic=r['price_witness_comparison']
    assert diagnostic['summary_sha256']==r['source_summary_sha256']
    assert sha(ROOT/'tools/diagnose_oil_duals_2025.py')==diagnostic['producer_sha256']
    assert len(a['certificates'])==4 and [c['case'] for c in a['certificates']]==r['design']['cases']
    for c in a['certificates']:
        assert c['hours']==8760 and c['emergency_mwh']<=1e-6
        assert c['native_residual_mw']<=1e-4 and c['offer_bound_mw']<=1e-4
        assert c['objective_error_eur']<.05 and c['duality_gap_maximum_eur']<.05 and c['complementarity_maximum_eur']<.05
        assert c['stationarity_maximum_eur_mwh']<1e-5
    assert r['assets'].keys()=={'capacity.csv','prices-by-zone.csv','oil-generation.csv'}
    for name,h in r['assets'].items(): assert sha(public/name)==h
    assert set(p.name for p in public.iterdir())==set(r['assets'])|{'summary.json'}
    with (public/'capacity.csv').open() as f: capacities=list(csv.DictReader(f))
    assert len(capacities)==len(r['capacity'])==7
    for row,saved in zip(capacities,r['capacity'],strict=True):
        for key,value in saved.items(): assert row[key]==str(value)
    added={row['country']:float(row['added_oil_mw']) for row in capacities if float(row['added_oil_mw'])>0}
    assert added==a['capacity_fill_mw'] and set(added)=={'PL','SK','SI'}
    with (public/'prices-by-zone.csv').open() as f: prices=list(csv.DictReader(f))
    assert len(prices)==192 and len({(p['case'],p['zone']) for p in prices})==192
    with (public/'oil-generation.csv').open() as f: generation=list(csv.DictReader(f))
    assert len(generation)==len(r['generation'])==136
    explorer=ROOT/'public/research/country-explorer-2025'; manifest=json.loads((explorer/'manifest.json').read_text())
    ti=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='oil'); observed={}
    for entry in manifest['countries']:
        path=explorer/entry['file']; assert r['sources'][str(path.relative_to(ROOT))]==sha(path)==entry['sha256']
        d=json.loads(gzip.decompress(path.read_bytes())); area=next(a for a in d['generation'] if a['id']=='country:'+entry['code'])
        o=[v for v in d['series'][area['observed'][ti]] if v is not None]
        observed[entry['code']]=(len(o),sum(o)/manifest['generation_scale']/1e6 if o else None)
    for row,saved in zip(generation,r['generation'],strict=True):
        for key,value in saved.items(): assert row[key]==('' if value is None else str(value))
        hours,total=observed[row['country']]; assert int(row['observed_known_hours'])==hours
        if total is None: assert row['observed_twh']==row['model_matched_hours_twh']==''
        else: assert abs(float(row['observed_twh'])-total)<1e-10
    for metric in r['metrics']:
        case=metric['case']; rows=[p for p in prices if p['case']==case]; eligible=[p for p in rows if int(p['known_hours'])==8760]
        assert len(rows)==48 and len(eligible)==41
        assert abs(sum(float(p['mae_eur_mwh']) for p in eligible)/41-metric['mae_eur_mwh'])<1e-9
        assert abs(sum(float(p['correlation']) for p in eligible)/41-metric['mean_correlation'])<1e-9
        assert abs(sum(float(g['model_annual_twh']) for g in generation if g['case']==case)-metric['oil_twh'])<1e-9
        assert f"{metric['mae_eur_mwh']:.6f}".encode() in section
    return base


if __name__=='__main__': check(); print('Oil extension and original report provenance verified')
