"""Standard-library CI check for the country explorer's public files and receipts."""
import gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def check():
    public=ROOT/'public/research/country-explorer-2025';manifest=json.loads((public/'manifest.json').read_text());audit=json.loads((public/'verification.json').read_text())
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    assert audit['status']=='all_country_hourly_source_dispatch_prices_and_original_provider_rows_replayed'
    assert audit['producer_sha256']==sha(ROOT/'tools'/audit.get('producer_file','export_country_explorer_2025.py')) and audit['auditor_sha256']==sha(ROOT/'tools'/audit.get('auditor_file','audit_country_explorer_2025.py'))
    transport=audit['transport'];assert transport['producer_sha256']==sha(ROOT/'tools/prepare_country_explorer_transport.py')
    assert transport['manifest_sha256']==sha(public/'manifest.json') and transport['original_manifest_sha256']==audit['manifest_sha256']
    original_audit={k:v for k,v in audit.items() if k!='transport'}
    assert hashlib.sha256((json.dumps(original_audit,indent=2)+'\n').encode()).hexdigest()==transport['source_audit_sha256']
    original_manifest=json.loads(json.dumps(manifest))
    for entry in original_manifest['countries']:entry.pop('json_sha256')
    assert hashlib.sha256((json.dumps(original_manifest,indent=2)+'\n').encode()).hexdigest()==audit['manifest_sha256']
    assert manifest['schema_version']==1 and manifest['hours']==audit['hours']==8760 and manifest['year']==2025
    assert len(manifest['countries'])==audit['countries']==34 and len(manifest['technologies'])==13
    assert len({e['code'] for e in manifest['countries']})==34 and manifest['model']['accepted_baseline'] is False
    assert audit['maximum_allocation_difference_mw']<1e-6 and audit['maximum_generation_rounding_mw']<=.05000001 and audit['maximum_price_rounding_eur_mwh']<=.00050001
    expected={'manifest.json','verification.json'};total=0
    for entry in manifest['countries']:
        name=entry['file'];assert name==entry['code']+'.json.gz';expected.add(name);path=public/name
        assert sha(path)==entry['sha256']==audit['files'][name]['sha256'];assert path.stat().st_size==entry['bytes']==audit['files'][name]['bytes'];total+=path.stat().st_size
        raw=gzip.decompress(path.read_bytes());assert hashlib.sha256(raw).hexdigest()==entry['json_sha256']==transport['json_sha256'][name]
        data=json.loads(raw);assert data['country']==entry['code'] and data['model_id']==manifest['model']['id'] and data['hours']==8760
        assert [r['zone'] for r in data['prices']]==entry['price_zones']
        for values in data['series'].values():assert len(values)==8760 and all(v is None or type(v) is int for v in values)
        for area in data['generation']:
            for key in ['model','lower','upper','observed']:assert len(area[key])==13 and all(ref in data['series'] for ref in area[key])
            for ref,count in zip(area['observed'],area['observed_hours'],strict=True):assert sum(v is not None for v in data['series'][ref])==count
        for price in data['prices']:assert price['model'] in data['series'] and price['observed'] in data['series'] and sum(v is not None for v in data['series'][price['observed']])==price['known_hours']
    assert {p.name for p in public.iterdir() if p.is_file()}==expected and total==audit['bytes'] and total<=24*1024**2
    print(f'Country explorer:34 countries,8760 hours, audited references/coverage/hashes; {total/1024**2:.2f} MiB lazy country data')


if __name__=='__main__':check()
