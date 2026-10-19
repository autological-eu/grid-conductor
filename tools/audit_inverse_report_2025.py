"""Replay published inverse-report CSVs and primary/broad price envelopes.

Uses immutable forward witnesses and the independently audited numerical summary;
no import of the presentation or inverse-calibration implementation.
"""
import csv,json
import numpy as np
from generation_mix_2025 import ROOT,digest


def audit_public(folder,receipt,public,article):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'verification-v1/audit.json').read_text());study=receipt['inverse_bid_ensemble_evaluation']
    assert digest(folder/'summary.json')==a['summary_sha256']==study['summary_sha256']
    assert study['members']==a['members']==s['members'];root=ROOT/s['accepted_folder']
    for name in ['development-targets.npz','evaluation-targets.npz']:
        assert digest(root/name)==s['source_hashes'][str((root/name).relative_to(ROOT))]
    with np.load(root/'development-targets.npz') as z:first={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in first.items()}
    records={r['id']:r for r in s['records']};eligible=[k for k in records if records[k]['eligible']];assert eligible==study['all_eligible_ids']
    bounds={name:[np.full_like(target['prices'],np.inf),np.full_like(target['prices'],-np.inf)] for name in ['primary','broad']}
    for k in set(eligible+s['members']):
        info=s['annuals'][k];p=ROOT/info['witness'] if info.get('external') else folder/info['witness'];assert digest(p)==info['witness_sha256']
        with np.load(p) as z:prices=z['row_duals'][:,:len(s['zones'])]
        for name,yes in [('primary',k in s['members']),('broad',k in eligible)]:
            if yes:bounds[name][0]=np.minimum(bounds[name][0],prices);bounds[name][1]=np.maximum(bounds[name][1],prices)
    coverage={}
    for name,(lo,hi) in bounds.items():
        rows=[]
        for j,zone in enumerate(s['zones']):
            known=np.isfinite(target['prices'][:,j]);o=target['prices'][:,j];v=dict(zone=zone,known_hours=int(known.sum()),observed_in_minmax_fraction=float(np.count_nonzero((o[known]>=lo[known,j]-1e-8)&(o[known]<=hi[known,j]+1e-8))/known.sum()) if known.any() else None,mean_width_eur_mwh=float(np.mean(hi[:,j]-lo[:,j])));rows.append(v)
        published=study['coverage'] if name=='primary' else study['all_eligible_coverage'];assert len(rows)==len(published)
        for expected,actual in zip(rows,published):
            assert expected['zone']==actual['zone'] and expected['known_hours']==actual['known_hours']
            for key in ['observed_in_minmax_fraction','mean_width_eur_mwh']:
                if expected[key] is None:assert actual[key] is None
                else:assert abs(expected[key]-actual[key])<1e-10
        coverage[name]={r['zone']:r for r in rows}
    for name,key in [('primary','equal_zone_envelope_coverage'),('broad','equal_zone_all_eligible_coverage')]:
        mean=np.mean([r['observed_in_minmax_fraction'] for r in coverage[name].values() if r['known_hours']]);assert abs(mean-study[key])<1e-12
    assert abs(np.mean([r['mean_width_eur_mwh'] for r in coverage['broad'].values() if r['known_hours']])-study['mean_all_eligible_width_eur_mwh'])<1e-10
    def read(name):
        with (public/name).open() as f:return list(csv.DictReader(f))
    def eq(raw,value):
        if isinstance(value,(str,bool)):assert raw==str(value)
        elif value is None:assert raw==''
        else:assert abs(float(raw)-value)<=1e-8*max(1,abs(value)),(raw,value)
    rows=read('inverse-search-cases.csv');assert len(rows)==len(records) and len({r['model'] for r in rows})==len(records)
    for row in rows:
        r=records[row['model']]
        for k in ['score','penalty']:eq(row[k],r[k])
        for k,v in r['metrics'].items():eq(row[k],v)
        assert row['eligible']==str(r['eligible']) and row['retained']==str(r['id'] in study['members']) and row['bid_sha256']==r['bid_sha256']
    rows=read('inverse-prices-by-zone.csv');assert len(rows)==len(study['shown'])*len(s['zones']) and len({(r['model'],r['zone']) for r in rows})==len(rows)
    pr={k:{r['zone']:r for r in v['prices']['zones']} for k,v in s['outcomes'].items()}
    support=json.loads((folder/'round-2-proposal.json').read_text())['support_hours'];assert digest(folder/'round-2-proposal.json')==s['proposals'][1]['sha256']
    for row in rows:
        assert row['model'] in study['shown'];z=row['zone'];r=pr[row['model']][z]
        for k,v in r.items():
            if not isinstance(v,(list,dict)):eq(row[k],v)
        for name,field in [('primary','ensemble_observed_minmax_fraction'),('broad','all_eligible_minmax_fraction')]:eq(row[field],coverage[name][z]['observed_in_minmax_fraction'])
        for name,field in [('primary','ensemble_mean_width_eur_mwh'),('broad','all_eligible_mean_width_eur_mwh')]:eq(row[field],coverage[name][z]['mean_width_eur_mwh'])
        assert row['last_proposal_parent']==s['proposals'][1]['parent']
        for fi,f in enumerate(['gas','coal','nuclear']):eq(row[f+'_supporting_interior_hours'],support[s['zones'].index(z)][fi])
    rows=read('inverse-generation-by-country.csv');assert len(rows)==len(study['shown'])*len(s['countries'])*5 and len({(r['model'],r['country'],r['fuel']) for r in rows})==len(rows)
    for row in rows:
        k=row['model'];assert k in study['shown'];ci=s['countries'].index(row['country']);fi=['Wind','Solar','Nuclear','Gas','Coal'].index(row['fuel']);outcome=s['outcomes'][k]
        point=sum(m[ci][fi] for m in outcome['monthly_fuel_point_twh']);low=sum(m['generation_lower_twh'][ci][fi] for m in outcome['monthly_quantities']);high=sum(m['generation_upper_twh'][ci][fi] for m in outcome['monthly_quantities'])
        ref=target['generation'][:,ci,fi];known=np.isfinite(ref);total=float(ref.sum()) if known.all() else None
        for field,value in [('illustrative_model_twh',point),('conditional_lower_twh',low),('conditional_upper_twh',high),('known_reference_months',int(known.sum())),('observed_twh',total),('difference_twh',None if total is None else point-total)]:eq(row[field],value)
    assert receipt['article_sha256']==digest(article)
    for name,sha in receipt['assets'].items():assert digest(public/name)==sha
    assert len([k for k in receipt['assets'] if k.endswith('.png')])==4
    return dict(status='inverse_report_csvs_and_primary_and_broad_envelopes_replayed',auditor_file='audit_inverse_report_2025.py',auditor_sha256=digest(__file__),source_summary_sha256=digest(folder/'summary.json'),article_sha256=digest(article),assets_sha256=receipt['assets'],search_rows=len(records),zone_rows=len(study['shown'])*len(s['zones']),generation_rows=len(rows),primary_members=len(s['members']),broad_members=len(eligible))
