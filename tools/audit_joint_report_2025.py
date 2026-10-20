"""Independent compact CSV and selection checks against audited annual results."""
import csv, json
import numpy as np
from generation_mix_2025 import ROOT, digest


def audit_public(folder,receipt,public,article):
    s=json.loads((folder/'summary.json').read_text()); a=json.loads((folder/'verification-v1/audit.json').read_text()); study=receipt['joint_network_evaluation']
    assert a['summary_sha256']==digest(folder/'summary.json')==study['summary_sha256']
    assert a['winner']==study['winner']==s['winner']; assert study['records']==s['records']
    root=ROOT/s['accepted_folder']
    with np.load(root/'development-targets.npz') as z: first={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z: target={k:np.concatenate([v,z[k]]) for k,v in first.items()}
    def read(name):
        assert b'\r\n' not in (public/name).read_bytes(), 'Publication CSV must use portable LF bytes'
        with (public/name).open() as f:return list(csv.DictReader(f))
    def eq(raw,value):
        if isinstance(value,(str,bool)):assert raw==str(value),(raw,value)
        elif value is None:assert raw==''
        else:assert abs(float(raw)-value)<=1e-8*max(1,abs(value)),(raw,value)
    records={r['id']:r for r in s['records']}; rows=read('joint-search-cases.csv')
    assert len(rows)==16 and len({r['case'] for r in rows})==16
    for row in rows:
        r=records[row['case']]; p=r['parameters']
        expected=dict(number=r['ordinal']+1,bid=p['bid'],network=p['network'],wind_factor=p['wind'],**(r['metrics'] or {key:None for key in s['reference']}),score=r['score'],penalty=r['penalty'],eligible=r['eligible'],joint_winner=r['id']==s['winner'],emergency_mwh=s['annuals'][r['id']]['emergency_mwh'],binding_branch_hours=s['outcomes'][r['id']].get('network_diagnostics',{}).get('binding_branch_hours'),completed_hours=s['annuals'][r['id']]['optimal_hours'],status=s['annuals'][r['id']].get('rejection','complete_year'),rejected_hour=s['annuals'][r['id']].get('failed_hour'))
        for key,value in expected.items():eq(row[key],value)
    rows=read('joint-prices-by-zone.csv'); assert len(rows)==len(study['shown'])*48 and len({(r['model'],r['zone']) for r in rows})==len(rows)
    for row in rows:
        k=row['model']; assert k in study['shown']; r=next(v for v in s['outcomes'][k]['prices']['zones'] if v['zone']==row['zone']); assert row['label']==study['labels'][k]
        for key,v in r.items():
            if not isinstance(v,(list,dict)):eq(row[key],v)
    price_count=len(rows); rows=read('joint-generation-by-country.csv'); assert len(rows)==len(study['shown'])*len(s['countries'])*5 and len({(r['model'],r['country'],r['fuel']) for r in rows})==len(rows)
    for row in rows:
        k=row['model']; assert k in study['shown']; ci=s['countries'].index(row['country']); fi=['Wind','Solar','Nuclear','Gas','Coal'].index(row['fuel']); outcome=s['outcomes'][k]
        point=sum(m[ci][fi] for m in outcome['monthly_fuel_point_twh']); lo=sum(m['generation_lower_twh'][ci][fi] for m in outcome['monthly_quantities']); hi=sum(m['generation_upper_twh'][ci][fi] for m in outcome['monthly_quantities']); ref=target['generation'][:,ci,fi]; known=np.isfinite(ref); total=float(ref.sum()) if known.all() else None
        for key,value in [('illustrative_model_twh',point),('conditional_lower_twh',lo),('conditional_upper_twh',hi),('known_reference_months',int(known.sum())),('observed_twh',total),('difference_twh',None if total is None else point-total)]:eq(row[key],value)
    assert receipt['article_sha256']==digest(article)
    assert len([name for name in receipt['assets'] if name.endswith('.png')])==4
    for name,sha in receipt['assets'].items():assert digest(public/name)==sha
    return dict(status='joint_report_cases_zonal_prices_national_mix_and_selection_replayed',auditor_sha256=digest(__file__),source_summary_sha256=digest(folder/'summary.json'),article_sha256=digest(article),assets_sha256=receipt['assets'],cases=16,zone_rows=price_count,generation_rows=len(rows))
