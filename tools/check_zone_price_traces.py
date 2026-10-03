"""Require a real static hourly plot for every eligible workbench corridor."""
import json,hashlib,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'public/research/zone-prices-2025';raw=(out/'manifest.json').read_bytes();manifest=json.loads(raw)
rows=json.loads((root/'public/research/entsoe-fast-targets.json').read_text())['targets'];pairs=sorted({tuple(sorted(r['border'].split('>'))) for r in rows if (r.get('deadweight_loss_meur_year') or 0)>0})
values={}
for zone in sorted({z for pair in pairs for z in pair}):
 item=manifest[zone]
 if item['status']!='published':raise ValueError(f'Missing published trace: {zone}')
 if item.get('source')!='ENTSO-E A44 day-ahead prices' and 'CC BY 4.0' not in item.get('license',''):raise ValueError(f'Public source rights not established: {zone}')
 data=json.loads((out/(zone+'.json')).read_text())
 assert len(data)==8760 and all(v is None or isinstance(v,(int,float)) and math.isfinite(v) for v in data)
 assert sum(v is not None for v in data)==item['known_hours']
 values[zone]=data
coverage=[]
for a,b in pairs:
 known=sum(x is not None and y is not None for x,y in zip(values[a],values[b]))
 if not known:raise ValueError(f'No jointly observed prices: {a}–{b}')
 coverage.append(dict(zone_a=a,zone_b=b,known_hours=known,total_hours=8760))
report=dict(year=2025,manifest_sha256=hashlib.sha256(raw).hexdigest(),zones=len(values),corridors=len(pairs),minimum_joint_hours=min(r['known_hours'] for r in coverage),coverage=coverage,limitations=['Hourly means require all four quarter-hour prices.','Known-hour coverage is not validation of network congestion or investment benefit.'])
(out/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Verified {len(values)} zones and {len(pairs)} corridors; minimum joint coverage {report["minimum_joint_hours"]}/8760 hours')
