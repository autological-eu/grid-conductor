"""EU-27 day-ahead zone registry (E0 gate).

Canonical EIC-code map for the bidding zones modelled in the EU market
experiment, the internal border set, the CORE flow-based membership and the
fixed-exterior neighbours. Codes marked `verified` came from successful cached
Aug-2026 ENTSO-E requests (`data/carbon-pilot/flow-tracing/raw`); the rest are
candidates that `--normalize-eic` confirms against a live A44 spot query (needs
ENTSOE_API_KEY) before the topology is pinned to `data/eu-market/eic.json`.

Convention: `price` = bidding-zone code for A44/A65, `gen` = control-area code
for A75 where it differs (Germany: 83F country domain vs 82H DE-LU price zone).
Regenerate (and re-verify) only through this module; do not hand-edit the dump.
"""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DUMP=ROOT/'data/eu-market'

# (label, price_eic, gen_eic_or_None, verified)
ZONES=[
    ('AT','10YAT-APG------L',None,True),('BE','10YBE----------2',None,True),
    ('BG','10YCA-BULGARIA-R',None,False),
    ('CZ','10YCZ-CEPS-----N',None,True),
    ('DE-LU','10Y1001A1001A82H','10Y1001A1001A83F',True),
    ('DK1','10YDK-1--------W',None,True),('DK2','10YDK-2--------M',None,True),
    ('EE','10Y1001A1001A39I',None,False),('ES','10YES-REE------0',None,True),
    ('FI','10YFI-1--------U',None,False),('FR','10YFR-RTE------C',None,True),
    ('GR','10YGR-HTSO-----Y',None,False),('HR','10YHR-HEP------M',None,False),
    ('HU','10YHU-MAVIR----U',None,False),('IE','10YIE-1001A00010',None,True),
    ('IT-North','10Y1001A1001A73I',None,True),
    ('IT-CNOR','10Y1001A1001A70O',None,False),('IT-CSUD','10Y1001A1001A71M',None,False),
    ('IT-SARD','10Y1001A1001A74G',None,False),('IT-SUD','10Y1001A1001A788',None,False),
    ('IT-SICI','10Y1001A1001A75E',None,False),
    ('LT','10YLT-1001A0008Q',None,True),('LV','10YLV-1001A00074',None,False),
    ('NL','10YNL----------L',None,True),('PL','10YPL-AREA-----S',None,True),
    ('PT','10YPT-REN------W',None,False),('RO','10YRO-TEL------P',None,False),
    ('SE1','10Y1001A1001A44P',None,False),('SE2','10Y1001A1001A45N',None,False),('SE3','10Y1001A1001A46L',None,False),('SE4','10Y1001A1001A47J',None,False),('SI','10YSI-ELES-----O',None,False),
    ('SK','10YSK-SEPS-----K',None,False),
]
# Swedish bidding zones remain separate in prices, demand, generation and borders.
SE_AREA={'SE1':'10Y1001A1001A44P','SE2':'10Y1001A1001A45N','SE3':'10Y1001A1001A46L','SE4':'10Y1001A1001A47J'}
IE_AREA={'IE-N':'10Y1001A1001A59C'}

# (label, eic, optional: drop silently if unretrievable, verified)
EXTERIORS=[
    ('GB','10YGB----------A',True,True),('CH','10YCH-SWISSGRIDZ',True,True),
    ('NO1','10YNO-1--------2',True,True),('NO2','10YNO-2--------T',True,True),
    ('NO5','10Y1001A1001A48H',True,True),
    ('NO3','10YNO-3--------J',True,False),('NO4','10YNO-4--------9',True,False),
    ('RS','10YCS-SERBIATSOV',True,False),('BA','10YBA-JPCC------D',True,False),
    ('ME','10YME-CG-TSO---S',True,False),('AL','10YAL-KESH-----5',True,False),
    ('MK','10YMK-MEPSO----8',True,False),
]
EXTRA_EDGE=['UA','MD','RU','BY','TR','MA']

CORE={'AT','BE','CZ','DE-LU','FR','HR','HU','NL','PL','RO','SI','SK'}

INTERNAL_BORDERS=[
    ('FR','BE'),('FR','DE-LU'),('FR','ES'),('FR','IT-North'),
    ('BE','NL'),('BE','DE-LU'),
    ('NL','DE-LU'),('NL','DK1'),
    ('DE-LU','DK1'),('DE-LU','DK2'),('DE-LU','CZ'),('DE-LU','AT'),('DE-LU','PL'),
    ('DE-LU','SE4'),
    ('AT','CZ'),('AT','HU'),('AT','SI'),('AT','IT-North'),
    ('CZ','PL'),('CZ','SK'),
    ('PL','SK'),('PL','LT'),('PL','SE4'),
    ('SK','HU'),
    ('HU','SI'),('HU','HR'),('HU','RO'),
    ('SI','HR'),('SI','IT-North'),
    ('IT-North','IT-CNOR'),('IT-CNOR','IT-CSUD'),('IT-CSUD','IT-SUD'),
    ('IT-CSUD','IT-SARD'),
    ('IT-SUD','IT-SICI'),('IT-SICI','IT-SARD'),
    ('GR','BG'),('GR','IT-SUD'),
    ('BG','RO'),
    ('ES','PT'),
    ('DK1','DK2'),('DK1','SE3'),('DK2','SE4'),
    ('SE1','FI'),('SE3','FI'),('SE1','SE2'),('SE2','SE3'),('SE3','SE4'),('FI','EE'),('EE','LV'),('LV','LT'),('LT','SE4'),
]
EXTERIOR_BORDERS=[
    ('FR','CH'),('DE-LU','CH'),('AT','CH'),('IT-North','CH'),
    ('FR','GB'),('BE','GB'),('NL','GB'),('DK1','GB'),('IE','GB'),
    ('NL','NO2'),('DE-LU','NO2'),('DK1','NO2'),
    ('SE3','NO1'),('SE2','NO3'),('SE1','NO4'),('SE2','NO4'),('FI','NO4'),
    ('HU','RS'),('HR','BA'),('HR','RS'),('RO','RS'),('BG','RS'),
    ('BG','MK'),('GR','MK'),('HR','ME'),('GR','AL'),
]

ZONE_LABELS={z[0] for z in ZONES}


def load_prior():
    prior_path=DUMP/'eic.json'
    if prior_path.exists():
        try:
            return json.loads(prior_path.read_text())
        except Exception:
            return None
    return None


def seed_from_prior(registry, ext_registry, prior):
    if not prior:
        return
    for label,item in registry.items():
        p=(prior.get('zones') or {}).get(label)
        if not p:
            continue
        item.update(price=p.get('price',item['price']),gen=p.get('gen'),verified=p.get('verified',item['verified']))
    for e in ext_registry:
        p=(prior.get('exteriors') or {}).get(e['label'])
        if p:
            e.update(eic=p.get('eic',e['eic']),verified=p.get('verified',e['verified']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--normalize-eic',action='store_true',help='live A44 spot-check every zone/candidate (needs ENTSOE_API_KEY)')
    args=p.parse_args()
    registry={label:dict(price=price,gen=gen,verified=verified) for label,price,gen,verified in ZONES}
    ext_registry=[dict(label=label,eic=eic,optional=optional,verified=verified) for label,eic,optional,verified in EXTERIORS]
    # Regenerate from the reviewed registry, never inherit old alias substitutions.
    if args.normalize_eic:
        normalize_eic(registry, ext_registry)
    status={label:item['verified'] for label,item in registry.items()}
    status.update({item['label']:item['verified'] for item in ext_registry})
    topology=dict(zones=registry,
        exteriors=ext_registry,
        interiors={f'{a}-{b}':dict(a=a,b=b,core=a in CORE and b in CORE) for a,b in INTERNAL_BORDERS},
        exteriors_exchange=[dict(zone=z,neighbor=n) for z,n in EXTERIOR_BORDERS],
        core=sorted(CORE),se_area=SE_AREA,ie_area=IE_AREA,extra_edge=EXTRA_EDGE,
        status=status,
        note='First-pass adjacency statement; flows/capacity per border verified in E1 via A11/A61 fetch.')
    DUMP.mkdir(parents=True,exist_ok=True)
    (DUMP/'topology.json').write_text(json.dumps(topology,indent=2),encoding='utf-8')
    (DUMP/'eic.json').write_text(json.dumps(dict(
        zones=registry,
        exteriors={item['label']:dict(eic=item['eic'],optional=item['optional'],verified=item['verified']) for item in ext_registry},
        se_area=SE_AREA,ie_area=IE_AREA,
        note='eic.json is the pinned input to E1 fetches; regenerate only via eu_zones.py'),indent=2))
    print(f'zones={len(ZONE_LABELS)} interior_edges={len(INTERNAL_BORDERS)} '
        f'exterior_edges={len(EXTERIOR_BORDERS)} core_zones={len(CORE)} '
        f'confirmed={sum(status.values())} pending={sum(1 for v in status.values() if not v)}')


def normalize_eic(registry, ext_registry):
    import os
    if not os.environ.get('ENTSOE_API_KEY'):
        print('ENTSOE_API_KEY not set; export it, then re-run.')
        return
    from flow_tracing import fetch, parse_day_ahead_prices
    print('normalizing via live A44 spot-check (2026-08-01 00:00) ...')
    period=dict(periodStart='202608010000',periodEnd='202608020215',documentType='A44',processType='A01')
    cache=DUMP/'raw';cache.mkdir(parents=True,exist_ok=True)
    for label,z in [*((z[0],z[1]) for z in ZONES),*((x[0],x[1]) for x in EXTERIORS)]:
        holder=registry[label] if label in registry else next((e for e in ext_registry if e['label']==label),None)
        if holder is None or holder['verified']:
            continue
        ok=False
        try:
            raw=fetch(dict(period,in_Domain=z,out_Domain=z),cache)
            ok=any(v is not None for v in parse_day_ahead_prices(raw).values())
        except ValueError as error:
            print(f'  {label}: {z} -> {error}')
        if ok:
            holder['verified']=True
            print(f'  {label}: {z} -> confirmed')
        else:
            print(f'  {label}: {z} -> NOT confirmed (stays candidate)')
    print('normalize done; unverified codes stay candidates until a later pass.')


if __name__=='__main__':main()