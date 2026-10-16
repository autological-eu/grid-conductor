"""Independent replay of accepted-baseline diagnosis, using sealed mix evidence."""
import argparse
import json
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT, MONTH, digest


def audit(folder):
    report=json.loads((folder/'diagnosis.json').read_text())
    summary=json.loads((folder/'summary.json').read_text())
    assert report['producer_sha256']==digest(ROOT/'tools/diagnose_accepted_baseline_2025.py')
    assert report['derivation_summary_sha256']==digest(folder/'summary.json')
    assert report['derivation_audit_sha256']==digest(folder/'verification-v1/audit.json')
    assert report['baseline_config_sha256']==digest(ROOT/'config/research-baseline.json')
    baseline=json.loads((ROOT/'config/research-baseline.json').read_text())
    model=ROOT/Path(baseline['summary_path']).parent
    with np.load(model/'development-targets.npz') as z: first=z['prices']
    with np.load(model/'evaluation-targets.npz') as z: obs=np.concatenate([first,z['prices']])
    with np.load(folder/'comparison.npz') as z: arrays={k:z[k] for k in z.files}
    assert [r['zone'] for r in report['zones']]==summary['zones']
    maes=[];daily=[];shape=[]
    for j,row in enumerate(report['zones']):
        ref=obs[:,j];pred=arrays['combined_prices'][:,j];good=np.isfinite(ref)
        assert row['known_price_hours']==int(good.sum())
        if not good.any():continue
        assert good.all()
        err=pred-ref;blocks=[err[t:t+24] for t in range(0,8760,24)]
        values=dict(mae_eur_mwh=float(np.sum(np.abs(err))/8760),bias_eur_mwh=float(np.sum(err)/8760),
                    daily_mean_error_mae=float(np.mean([abs(b.mean()) for b in blocks])),
                    within_day_error_mae=float(np.mean([np.mean(abs(b-b.mean())) for b in blocks])))
        for k,v in values.items():assert abs(row[k]-v)<1e-9
        maes.append(values['mae_eur_mwh']);daily.append(values['daily_mean_error_mae']);shape.append(values['within_day_error_mae'])
        assert row['observed_negative_hours']==np.count_nonzero(ref < -1e-6)
        assert row['modeled_negative_hours']==np.count_nonzero(pred < -1e-6)
        if (ref < -1e-6).any():assert abs(row['negative_hour_mae']-float(np.mean(abs(err[ref < -1e-6]))))<1e-9
        else:assert row['negative_hour_mae'] is None
        assert abs(row['correlation']-float(np.corrcoef(pred,ref)[0,1]))<1e-10
        for r in row['monthly']:
            e=err[MONTH==r['month']];assert abs(r['mae']-np.mean(abs(e)))<1e-9 and abs(r['bias']-np.mean(e))<1e-9
        assert len(row['generation'])==int(np.isfinite(arrays['observed'][:,j,:]).any(axis=0).sum())
        for fuel in row['generation']:
            k=summary['technologies'].index(fuel['technology']);refg=arrays['observed'][:,j,k];known=np.isfinite(refg)
            gen=arrays['combined_point'][:,j,k];lo=arrays['combined_lower'][:,j,k];hi=arrays['combined_upper'][:,j,k]
            assert fuel['known_hours']==known.sum()
            for key,aa,bb in [('generation_shape_correlation',gen[known],refg[known]),('hourly_mix_error_price_error_correlation',(gen-refg)[known],err[known])]:
                if len(aa)>2 and np.std(aa)>1e-8 and np.std(bb)>1e-8:assert abs(fuel[key]-float(np.corrcoef(aa,bb)[0,1]))<1e-9
                else:assert fuel[key] is None
            for key,v in [('model_twh',gen),('observed_twh',refg),('difference_twh',gen-refg)]:assert abs(fuel[key]-float(v[known].sum()/1e6))<1e-8
            for month in fuel['monthly']:
                mask=known&(MONTH==month['month']);assert month['known_hours']==mask.sum()
                for key,v in [('model_twh',gen),('observed_twh',refg)]:assert abs(month[key]-float(v[mask].sum()/1e6))<1e-8
                assert abs(month['difference_twh']-float((gen-refg)[mask].sum()/1e6))<1e-8
                outside=max(float((lo-refg)[mask].sum()/1e6),float((refg-hi)[mask].sum()/1e6),0.)
                assert abs(month['outside_interval_twh']-outside)<1e-8
    assert len(maes)==report['observed_zones']==41 and report['hours']==8760
    for key,v in [('equal_zone_mae',np.mean(maes)),('mean_daily_level_error_mae',np.mean(daily)),('mean_within_day_error_mae',np.mean(shape))]:assert abs(report[key]-v)<1e-9
    assert abs(report['equal_zone_mae']-baseline['prices']['equal_zone_mae'])<1e-9
    assert abs(report['remaining_reduction_percent']-100*(1-10/np.mean(maes)))<1e-9
    order=sorted([r for r in report['zones'] if r['known_price_hours']],key=lambda r:-r['mae_eur_mwh'])
    assert report['top_ten_zones']==[r['zone'] for r in order[:10]]
    assert abs(report['top_ten_share_absolute_error']-sum(r['mae_eur_mwh'] for r in order[:10])/sum(maes))<1e-10
    result=dict(status='accepted_refit_price_monthly_mix_and_target_metrics_replayed',diagnosis_sha256=digest(folder/'diagnosis.json'),auditor_sha256=digest(__file__),zones=48,price_zones=41,hours=8760)
    path=folder/'diagnosis-audit.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);audit(p.parse_args().folder)
