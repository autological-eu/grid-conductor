"""Recompute publication CSV metrics from unrounded saved duals and fresh targets."""
import csv,json
from pathlib import Path
import numpy as np
from sdac_prices_2025 import ROOT,OUT,sha

def audit():
    pub=ROOT/'public/research/dispatch-comparison-2025';s=json.loads((pub/'summary.json').read_text());model=ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2';ms=json.loads((model/'summary.json').read_text());export=ROOT/'data/bidding-zone-network-2025/sdac-explorer-v1';es=json.loads((export/'summary.json').read_text())
    assert s['witness_sha256']==sha(model/'chp25.npz')==ms['annuals']['chp25']['witness_sha256']
    assert s['price_audit_sha256']==sha(OUT/'audit.json') and s['country_export_audit']==json.loads((export/'audit.json').read_text())
    with np.load(model/'chp25.npz') as z:p=z['row_duals'][:,:48];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
    with np.load(ROOT/ms['annuals']['control']['witness']) as z:control=z['row_duals'][:,:48]
    with np.load(OUT/'prices.npz') as z:o=z['prices']
    with (pub/'prices-by-zone.csv').open() as f:table=list(csv.DictReader(f))
    assert len(table)==48;maes=[];controls=[];rs=[]
    for j,row in enumerate(table):
        assert row['zone']==ms['zones'][j];good=np.isfinite(o[:,j]);assert int(row['known_hours'])==good.sum()
        if not good.any():assert row['mae_eur_mwh']=='';continue
        assert good.all();error=p[:,j]-o[:,j];mae=float(np.mean(np.abs(error)));bias=float(error.sum()/8760);rmse=float(np.sqrt(np.dot(error,error)/8760));r=float(np.corrcoef(p[:,j],o[:,j])[0,1]);ctrl=float(np.mean(np.abs(control[:,j]-o[:,j])))
        within=[]
        for day in range(365):
            a=p[day*24:(day+1)*24,j];b=o[day*24:(day+1)*24,j];within.extend(abs(a-a.mean()-b+b.mean()))
        for field,value in [('mae_eur_mwh',mae),('bias_eur_mwh',bias),('rmse_eur_mwh',rmse),('correlation',r),('control_mae_eur_mwh',ctrl),('within_day_mae_eur_mwh',float(np.mean(within)))]:assert abs(float(row[field])-value)<1e-9,(row['zone'],field)
        maes.append(mae);controls.append(ctrl);rs.append(r)
    assert len(maes)==41 and abs(np.mean(maes)-s['mae_eur_mwh'])<1e-10 and abs(np.mean(controls)-s['control_mae_eur_mwh'])<1e-10 and abs(np.mean(rs)-s['mean_zonal_correlation'])<1e-10
    with np.load(export/'aggregation.npz') as z:allocation=z['model']
    with np.load(model/'chp25-oil.npz') as z:oil=z['generation_mwh']
    for j,c in enumerate(es['countries']):np.testing.assert_allclose(allocation[:,es['domains'].index('country:'+c),es['technologies'].index('oil')],oil[:,j],rtol=0,atol=1e-6)
    with (pub/'national-generation.csv').open() as f:table=list(csv.DictReader(f))
    from generation_mix_2025 import EMBER,MONTH
    import gzip
    manifest=json.loads((ROOT/'public/research/country-explorer-2025/manifest.json').read_text());expected=[]
    with (pub/'oil-generation.csv').open() as f:oilrows=list(csv.DictReader(f))
    assert [row['country'] for row in oilrows]==['DE','BE','PL','SK','SI']
    for row,reported in zip(oilrows,s['oil'],strict=True):
        c=row['country'];payload=json.loads(gzip.decompress((ROOT/'public/research/country-explorer-2025'/(c+'.json.gz')).read_bytes()));area=next(a for a in payload['generation'] if a['id']=='country:'+c)
        obs=np.array([np.nan if v is None else v/10 for v in payload['series'][area['observed'][es['technologies'].index('oil')]]]);q=oil[:,es['countries'].index(c)];valid=np.isfinite(obs)
        expected_oil=dict(known_hours=int(valid.sum()),observed_twh=float(np.nansum(obs)/1e6),model_matched_twh=float(q[valid].sum()/1e6),model_annual_twh=float(q.sum()/1e6),hourly_mae_mw=float(np.mean(abs(q[valid]-obs[valid]))),hourly_correlation=float(np.corrcoef(q[valid],obs[valid])[0,1]) if q[valid].std()>1e-8 else None,model_at_negative_observed_price_twh=float(q[valid&(o[:,ms['zones'].index('DE-LU' if c=='DE' else c)]<0)].sum()/1e6))
        for key,value in expected_oil.items():
            if value is None:assert row[key]=='' and reported[key] is None
            else:assert abs(float(row[key])-value)<1e-6 and abs(reported[key]-value)<1e-6
    for entry in manifest['countries']:
        country=json.loads(gzip.decompress((ROOT/'public/research/country-explorer-2025'/entry['file']).read_bytes()));expected.extend([dict(country=entry['code'],**row) for row in country['monthly']])
    assert len(table)==len(expected)
    for row,ref in zip(table,expected,strict=True):
        assert row['country']==ref['country'] and row['fuel']==ref['fuel'] and int(row['month'])==ref['month']
        if ref['observed_twh'] is None:assert row['observed_twh']==''
        else:assert abs(float(row['observed_twh'])-ref['observed_twh'])<1e-10
        fields=[es['technologies'].index(f) for f in EMBER[row['fuel']]];value=allocation[MONTH==int(row['month']),es['domains'].index('country:'+row['country'])][:,fields].sum()/1e6
        assert abs(float(row['model_twh'])-value)<1e-9
    for name,digest in s['assets'].items():assert sha(pub/name)==digest
    assert sha(ROOT/'docs/european-physical-synthetic-clearing-2025.md')==s['article_sha256']
    result=dict(status='unrounded_all_year_price_and_country_fuel_tables_replayed',publication_summary_before_audit_sha256=sha(pub/'summary.json'),auditor_file=Path(__file__).name,auditor_sha256=sha(__file__),hours=8760,observed_zones=41,countries=34,all_country_oil_quantities_match=True,monthly_rows=len(table))
    (export/'report-audit.json').write_text(json.dumps(result,indent=2)+'\n');s['report_audit']=result;(pub/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(result['status'])
if __name__=='__main__':audit()
