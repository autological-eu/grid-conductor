"""Recompute public error CSVs directly from audited witnesses, without renderer."""
import csv,json
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT,digest
from intraday_offer_bids_2025 import TIMEZONES


def audit_public(folder,receipt,public,article):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'verification-v1/audit.json').read_text());study=receipt['weekly_error_evaluation']
    assert a['summary_sha256']==digest(folder/'summary.json')==study['summary_sha256'];assert study['results']==s['results']
    root=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1';joint=ROOT/'data/bidding-zone-network-2025/joint-network-calibration-v4';js=json.loads((joint/'summary.json').read_text())
    observed=np.concatenate([np.load(root/f)['prices'] for f in ['development-targets.npz','evaluation-targets.npz']]);zones=s['zones'];clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC');models={}
    for key in s['design']['anchors']:
        info=js['annuals'][key];path=ROOT/info['witness'] if info.get('external') else joint/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:models[key]=z['row_duals'][:,:len(zones)]
        info=s['annuals'][key];path=folder/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:models[key+'-weekly']=z['row_duals'][:,:len(zones)]
    def read(name):
        assert b'\r\n' not in (public/name).read_bytes()
        with (public/name).open() as f:return list(csv.DictReader(f))
    def eq(raw,v):assert abs(float(raw)-v)<=1e-8*max(1,abs(v)),(raw,v)
    rows=read('hourly-error-zones.csv');assert len(rows)==192 and len({(r['model'],r['zone']) for r in rows})==192
    for row in rows:
        k=row['model'];j=zones.index(row['zone']);p=models[k][:,j];o=observed[:,j];known=np.isfinite(o)
        assert row['label']==study['labels'][k];eq(row['known_hours'],int(known.sum()))
        if not known.any():
            assert all(v=='' for n,v in row.items() if n not in ['model','label','zone','known_hours']);continue
        er=p-o;local=clock.tz_convert(TIMEZONES[row['zone'][:2]]);we=local.dayofweek>=5
        for n,v in dict(mae=abs(er).mean(),bias=er.mean(),weekday_bias=er[~we].mean(),weekend_bias=er[we].mean(),weekday_mae=abs(er[~we]).mean(),weekend_mae=abs(er[we]).mean(),negative_observed_hours=sum(o<-1e-6),negative_model_hours=sum(p<-1e-6),correlation=np.corrcoef(p,o)[0,1]).items():eq(row[n],v)
    periods=read('hourly-error-periods.csv');assert len(periods)==4*(6+12+15)
    regimes={'negative':(-np.inf,-1e-6),'near-zero':(-1e-6,20),'20–80':(20,80),'80–150':(80,150),'150–250':(150,250),'250+':(250,np.inf)}
    for row in periods:
        p=models[row['model']];e=p-observed
        if row['period_type']=='observed-price-regime':
            lo,hi=regimes[row['period']];mask=(observed>=lo)&(observed<hi)&np.isfinite(observed)
            eq(row['zone_hours'],int(mask.sum()));eq(row['mae'],abs(e[mask]).mean());eq(row['bias'],e[mask].mean());eq(row['absolute_error_share'],np.nansum(abs(e[mask]))/np.nansum(abs(e)))
        elif row['period_type']=='UTC-month':
            er=e[clock.month==int(row['period'])];known=np.isfinite(er);eq(row['zone_hours'],known.sum());eq(row['mae'],abs(er[known]).mean());eq(row['bias'],er[known].mean())
        else:
            day=pd.Timestamp(row['period'],tz='UTC');mask=(clock>=day)&(clock<day+pd.Timedelta(days=1));er=e[mask];eq(row['mae'],np.nanmean(abs(er)));eq(row['bias'],np.nanmean(er))
            daily=np.nanmean(abs(e).reshape(365,24,len(zones)),axis=(1,2));assert row['period'] in {str(clock[t*24].date()) for t in np.argsort(daily)[-15:]}
    assert receipt['article_sha256']==digest(article)
    assert len([k for k in receipt['assets'] if k.endswith('.png')])==4
    for name,sha in receipt['assets'].items():assert digest(public/name)==sha
    return dict(status='all_weekly_zonal_and_event_csv_metrics_replayed_from_hourly_witnesses',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),article_sha256=digest(article),assets_sha256=receipt['assets'],zonal_rows=len(rows),event_rows=len(periods))
