"""Record actual 2025 source coverage and explicit rebuild gates."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'data/pypsa-eur/online-source-audit'
def main():
    load=pd.read_csv(CACHE/'demand.csv',index_col=0,parse_dates=True).loc['2025']
    if not load.index.equals(pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')):raise ValueError('Unexpected ENTSO-E time coverage')
    neso=pd.read_csv(CACHE/'neso-demand-2025.csv')
    start=pd.to_datetime(neso.SETTLEMENT_DATE).dt.tz_localize('Europe/London').dt.tz_convert('UTC')
    stamps=pd.DatetimeIndex(start+pd.to_timedelta((neso.SETTLEMENT_PERIOD-1)*30,unit='min'))
    expected=pd.date_range('2025-01-01',periods=17520,freq='30min',tz='UTC')
    if not stamps.equals(expected):raise ValueError('NESO settlement/DST alignment is incomplete')
    if neso[['ND','TSD']].isna().any().any():raise ValueError('Missing NESO demand values')
    weather=json.loads((ROOT/'public/research/2025-weather-source-audit.json').read_text())
    raw=(CACHE/'neso-demand-2025.csv').read_bytes()
    report=dict(status='2025_sources_partly_ready_dispatch_input_not_assembled',year=2025,entsoe_hourly_load=dict(hours=8760,complete_countries=[c for c in load if load[c].notna().all()],missing_hours=load.isna().sum().to_dict()),
      neso=dict(source_url='https://api.neso.energy/dataset/8f2fe0af-871c-488d-8bad-960426f24601/resource/b2bde559-3455-4021-b179-dfe60c0337b0/download/demanddata_2025.csv',source_sha256=hashlib.sha256(raw).hexdigest(),intervals=17520,settlement_timezone='Europe/London',utc_alignment='complete_after_explicit_DST_conversion',fields=['ND','TSD'],units='MW',model_mapping='Unresolved: ND/TSD, embedded generation and Great Britain versus Northern Ireland accounting must match model geography.'),
      weather=dict(source_sha256=weather['source_sha256'],hours_per_node=8760,nodes=len(weather['nodes']),generation_availability_ready=False),
      rebuild=dict(upstream_commit='a5408e9db5402c53345d7339fffb52afe96d6e43',config='config/pypsa-eur/full-year.yaml',clusters=128,hours=8760,memory_limit_gib=8,cpu_quota_cores=2,disk_capacity_gib=32,cloud_native_launcher_supported=True),
      remaining_gates=['Reconcile demand gaps using the explicitly configured research methodology; never silently invent or fill data.','Rebuild full spatial renewable availability and annual hydro inflow from 2025 data; point-centroid weather is insufficient for the original PyPSA-Eur method.','Audit the archived power-plant snapshot, fuel/carbon costs and network version against the 2025 rebuild specification.','Match original local patches and record hashes/environment versions; call a new build a rebuild rather than an exact reproduction until these match.','Measure solve memory/time on the 128-node March case before committing to a full linked annual solve on 8 GiB.'],historical_market_validation='not_performed')
    (ROOT/'public/research/2025-rebuild-status.json').write_text(json.dumps(report,indent=2)+'\n');print('2025 weather and GB load ready; complete ENTSO-E country load:',len(report['entsoe_hourly_load']['complete_countries']))
if __name__=='__main__':main()
