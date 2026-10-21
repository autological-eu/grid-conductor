"""Bind both gzip and decoded JSON hashes without changing audited country data.

Some static hosts transparently decode .gz responses. This appends transport
metadata, preserving the source audit and its original manifest hash verbatim.
"""
import gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def prepare():
    folder=ROOT/'public/research/country-explorer-2025';manifest=json.loads((folder/'manifest.json').read_text());audit=json.loads((folder/'verification.json').read_text())
    assert 'transport' not in audit,'Transport metadata already prepared; preserve its receipt'
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert sha((folder/'manifest.json').read_bytes())==audit['manifest_sha256']
    original_audit=sha((folder/'verification.json').read_bytes());hashes={}
    for entry in manifest['countries']:
        data=(folder/entry['file']).read_bytes();assert sha(data)==entry['sha256']==audit['files'][entry['file']]['sha256']
        entry['json_sha256']=sha(gzip.decompress(data));hashes[entry['file']]=entry['json_sha256']
    final=(json.dumps(manifest,indent=2,allow_nan=False)+'\n').encode();(folder/'manifest.json').write_bytes(final)
    audit['transport']=dict(producer_sha256=sha(Path(__file__).read_bytes()),source_audit_sha256=original_audit,original_manifest_sha256=audit['manifest_sha256'],manifest_sha256=sha(final),json_sha256=hashes)
    (folder/'verification.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('Gzip/decoded-JSON integrity metadata prepared; all34 audited payloads unchanged')


if __name__=='__main__':prepare()
