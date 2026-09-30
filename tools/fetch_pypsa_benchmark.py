"""Fetch one pinned public network using HTTP ranges, not the 2.2 GB ZIP.

Source: Zenodo 7646728 (CC BY 4.0), networks/elec_s_37.nc.
Large source files stay in ignored data/pypsa-eur/.
"""
import hashlib
import io
import json
from pathlib import Path
import struct
import urllib.request
import zlib

URL = 'https://zenodo.org/records/7646728/files/networks.zip?download=1'
MEMBER = 'networks/elec_s_37.nc'
SHA256 = 'a535836b22ed0259ee95ca90867016eedf2b26cc88c1129bf3730420d51dcde8'
DESTINATION = Path(__file__).resolve().parents[1]/'data/pypsa-eur/online-source-audit/elec_s_37.nc'

def ranged(start, end=None):
    value=f'bytes={start}-{end}' if end is not None else f'bytes=-{start}'
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'Range': value}), timeout=60) as response:
        if response.status != 206:
            raise ValueError('Server must support ranges; refusing entire archive download')
        data=response.read()
    return data

def fetch():
    if DESTINATION.exists() and hashlib.sha256(DESTINATION.read_bytes()).hexdigest()==SHA256:
        return DESTINATION
    tail=ranged(131072)
    position=tail.find(b'PK\x01\x02')
    found=None
    while position>=0 and tail[position:position+4]==b'PK\x01\x02':
        header=struct.unpack('<4s6H3L5H2L',tail[position:position+46])
        name_length,extra_length,comment_length=header[10:13]
        name=tail[position+46:position+46+name_length].decode()
        if name==MEMBER:found=header;break
        position+=46+name_length+extra_length+comment_length
    if found is None or found[4]!=8 or found[9]>64*1024*1024:
        raise ValueError('Expected compact deflated member missing')
    offset=found[-1]
    raw=ranged(offset, offset+found[8]+4096)
    local=struct.unpack('<4s5H3L2H',raw[:30])
    start=30+local[-2]+local[-1]
    payload=zlib.decompress(raw[start:start+found[8]],-15)
    if len(payload)!=found[9] or zlib.crc32(payload)!=found[7] or hashlib.sha256(payload).hexdigest()!=SHA256:
        raise ValueError('Archive member checksum failed')
    DESTINATION.parent.mkdir(parents=True,exist_ok=True)
    DESTINATION.write_bytes(payload)
    return DESTINATION

if __name__=='__main__':
    print(json.dumps({'file':str(fetch()),'source':URL,'member':MEMBER,'sha256':SHA256}))
