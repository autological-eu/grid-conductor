"""CI-checkable bindings for the new current-model publication, no legacy claims."""
import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    public=ROOT/'public/research/dispatch-comparison-2025';s=json.loads((public/'summary.json').read_text());assert s['schema_version']==2 and s['model_case']=='chp25' and s['hours']==8760 and s['days']==365 and s['observed_price_zones']==41
    assert s['renderer_sha256']==sha(ROOT/'tools'/s['renderer_file'])
    article=ROOT/'docs/european-physical-synthetic-clearing-2025.md';assert s['article_sha256']==sha(article);assert article.read_text().count('![')==4
    assert s['model_audit']['summary_sha256']==s['model_summary_sha256'] and s['model_audit']['status']=='passed'
    assert s['model_audit']['auditor_sha256']==sha(ROOT/'tools/audit_oil_chp_bids_2025.py')
    assert {r['case'] for r in s['model_audit']['certificates']}=={'control','source_costs','chp25','chp50'}
    for c in s['model_audit']['certificates']:
        assert c['hours']==8760 and c['emergency_mwh']==0 and c['native_residual_mw']<=1e-4 and c['primal_residual_mw']<=1e-4 and c['objective_error_eur']<.05 and c['duality_gap_maximum_eur']<.05
    source=s['price_source_audit'];assert source['status']=='all_raw_A44_auction_hourly_targets_replayed' and source['hours']==8760 and source['eligible_zones']==41 and source['summary_sha256']==s['price_summary_sha256']
    assert hashlib.sha256((json.dumps(source,indent=2)+'\n').encode()).hexdigest()==s['price_audit_sha256']
    assert source['producer_sha256']==sha(ROOT/'tools/sdac_prices_2025.py') and source['auditor_sha256']==sha(ROOT/'tools'/source['auditor_file'])
    assert {r['zone'] for r in source['changes'] if r['changed_hours']}=={'AT','DE-LU'}
    assert {r['zone'] for r in source['independent_full_year_references']}=={'AT','DE-LU','DK1','DK2'}
    for ref in source['independent_full_year_references']:assert ref['hours']==8760 and ref['maximum_difference_eur_mwh']==0
    for ref in source['map_price_checks']:
        assert ref['maximum_difference_eur_mwh']==0 and ref['sha256']==sha(ROOT/ref['path'])
    countries=ROOT/'public/research/country-explorer-2025';ca=s['country_export_audit'];manifest=json.loads((countries/'manifest.json').read_text());liveaudit=json.loads((countries/'verification.json').read_text());assert {k:v for k,v in liveaudit.items() if k!='transport'}==ca
    assert ca['price_source_audit_sha256']==s['price_audit_sha256'] and ca['model_summary_sha256']==s['model_summary_sha256'] and ca['witness_sha256']==s['witness_sha256'] and s['country_manifest_sha256']==sha(countries/'manifest.json')
    assert manifest['model']['id']==s['model_id'] and abs(manifest['model']['mae_eur_mwh']-s['mae_eur_mwh'])<1e-10
    a=s['report_audit'];assert a['status']=='unrounded_all_year_price_and_country_fuel_tables_replayed' and a['auditor_sha256']==sha(ROOT/'tools'/a['auditor_file']) and a['hours']==8760 and a['observed_zones']==41 and a['countries']==34 and a['all_country_oil_quantities_match']
    before={k:v for k,v in s.items() if k!='report_audit'};assert hashlib.sha256((json.dumps(before,indent=2)+'\n').encode()).hexdigest()==a['publication_summary_before_audit_sha256']
    expected={'overview.png','national-mix.png','daily-prices.png','zone-mae-grid.png','prices-by-zone.csv','oil-generation.csv','national-generation.csv'}
    assert set(s['assets'])==expected and {p.name for p in public.iterdir()}==expected|{'summary.json'}
    for name,digest in s['assets'].items():assert sha(public/name)==digest
    with (public/'prices-by-zone.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==48;valid=[r for r in rows if r['mae_eur_mwh']];assert len(valid)==41 and all(int(r['known_hours'])==8760 for r in valid)
    assert math.isclose(sum(float(r['mae_eur_mwh']) for r in valid)/41,s['mae_eur_mwh'],abs_tol=1e-10)
    print('Current report: corrected A44 targets, four full-year reference checks, 8760-hour physical certificate, 34-country export and all figures/tables bound')
if __name__=='__main__':check()
