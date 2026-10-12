"""Restore pinned geographic sources; reject changed mutable provider releases."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[{'path': 'data/bidding-zone-network-2025/sources/IT_CALA.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_CALA.geojson', 'sha256': 'baecd930118c8226f6e2d37bd2386472c6de8d170ee554733d7dbe88a2d2980b'}, {'path': 'data/bidding-zone-network-2025/sources/IT_CNOR.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_CNOR.geojson', 'sha256': 'dd052d17fa70d163528bb3bdf260e330740f0c1a89155eff1bc36114f291f70d'}, {'path': 'data/bidding-zone-network-2025/sources/IT_CSUD.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_CSUD.geojson', 'sha256': '482bcaef8dcd81addeb969a8ade1abc1a1c1c953ac2952db58a1e641044b87ac'}, {'path': 'data/bidding-zone-network-2025/sources/IT_SARD.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_SARD.geojson', 'sha256': 'a7753ee6db6ef875c5413138d4c4c0755372070faa958d6ba0115c63a4025a3a'}, {'path': 'data/bidding-zone-network-2025/sources/IT_SICI.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_SICI.geojson', 'sha256': '077a0f5e06fd5e3b065f84aa06376cfec720a5627f1b8fe437180b1de9816c46'}, {'path': 'data/bidding-zone-network-2025/sources/IT_SUD.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_SUD.geojson', 'sha256': '07d54be4cf7b32f773baf7a63290c17ce71d330db9040a2605e7c01fa670044e'}, {'path': 'data/bidding-zone-network-2025/sources/electricitymaps-world.geojson', 'url': 'https://raw.githubusercontent.com/electricitymaps/electricitymaps-contrib/f2c444841ba8ea8ad1e04f6e3a1acf2688aeac6a/geo/world.geojson', 'sha256': '4dca24f24de0c0cae8ae99cef3b196d064776b8f9a3f366ab7c4de63adcd3594'}, {'path': 'data/bidding-zone-network-2025/sources/italian-zones.geojson', 'url': 'https://raw.githubusercontent.com/EnergieID/entsoe-py/0cae4006c5fc81952c4717323417a3dbe94a8222/entsoe/geo/geojson/IT_NORD.geojson', 'sha256': '36eb1ee7c6941d48234e2ceb0c7ff58f15b6ff2cf4801c6abd687e353cd6fc3d'}, {'path': 'data/bidding-zone-source-audit-2025/nve-zones.json', 'url': 'https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson', 'sha256': '07c5af7b596c066cbbd42df1ffa4eb7e58bd81c9f429037d66c7df9733e71c92'}]

def collect():
    for source in SOURCES:
        path=ROOT/source['path']
        raw=path.read_bytes() if path.exists() else urllib.request.urlopen(source['url'],timeout=60).read()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise ValueError('Provider release changed; use fresh provenance and rerun: '+source['path'])
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(raw)
        receipt=path.with_name(path.name+'.receipt.json') if path.name in ['electricitymaps-world.geojson','italian-zones.geojson'] else path.with_suffix('.receipt.json')
        if path.name=='nve-zones.json':receipt=path.with_suffix('.meta.json')
        if not receipt.exists():receipt.write_text(json.dumps(dict(url=source['url'],sha256=source['sha256'],recovery='Pinned bytes; original retrieval time not reconstructed'),indent=2)+'\n')
        print(path.name+': pinned source verified')

if __name__=='__main__':collect()
