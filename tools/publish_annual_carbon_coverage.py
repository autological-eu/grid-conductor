"""Publish audited annual collection coverage; never fabricate full intensity."""
import json,hashlib,datetime as dt
from pathlib import Path
from carbon_pilot import ROOT,UTC,iso
from collect_annual_production_carbon import aggregate

def publish():
 folder=ROOT/'data/carbon-pilot/entsoe';source=json.loads((folder/'annual-2025.json').read_text())
 for month,receipt in source['monthly'].items():
  raw=(folder/f'2025-{month}/hourly.jsonl').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=receipt['hourly_sha256']:raise ValueError('Monthly input fingerprint mismatch')
 rows=[json.loads(line) for m in range(1,13) for line in (folder/f'2025-{m:02d}/hourly.jsonl').read_text().splitlines()]
 for zone,item in source['zones'].items():
  group=[r for r in rows if r['zone']==zone]
  expected=[iso(dt.datetime(2025,1,1,tzinfo=UTC)+dt.timedelta(hours=i)) for i in range(8760)]
  if sorted(r['start'] for r in group)!=expected:raise ValueError('Annual chronology mismatch')
  recomputed=aggregate(group,8760)
  if item!=recomputed:raise ValueError('Annual aggregate mismatch')
 source['limitations']=['Complete-hour totals exclude missing generation hours; not full-year generation totals',
  'Reported categories alone do not establish complete fleet coverage','Generic lifecycle factors remain pilot proxies',
  'Positive unsupported fuels block full annual intensity','Production only; not consumption or avoided emissions']
 out=ROOT/'public/research/production-carbon-2025';out.mkdir(exist_ok=True)
 (out/'annual-coverage.json').write_text(json.dumps(source,indent=2,allow_nan=False)+'\n')
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
 for zone in source['zones']:
  ax.plot(range(1,13),[100*source['monthly'][f'{m:02d}']['zones'][zone]['complete_generation_hours']/source['monthly'][f'{m:02d}']['zones'][zone]['expected_hours'] for m in range(1,13)],marker='o',label=zone)
 ax.set_xticks(range(1,13));ax.set_ylim(0,105);ax.set_xlabel('UTC calendar month, 2025');ax.set_ylabel('Complete reported generation hours (%)');ax.set_title('Data coverage, not carbon-factor completeness');ax.grid(alpha=.2);ax.legend()
 fig.savefig(out/'annual-coverage.svg');plt.close(fig)
 print('Published audited annual coverage artifact and chart; full annual intensity remains unavailable')
if __name__=='__main__':publish()
