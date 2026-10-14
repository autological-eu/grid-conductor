"""Check training-only isotonic optimality and temporal evaluation independently."""
import argparse,json
from pathlib import Path
import numpy as np
from nve_hydro_diagnostics import ROOT,digest

def replay(folder):
    s=json.loads((folder/'benchmark.json').read_text())
    assert digest(ROOT/'tools/residual_price_benchmark_2025.py')==s['producer_sha256']
    assert digest(folder/'benchmark.npz')==s['witness_sha256']
    assert digest(folder/'benchmark-design.json')==s['design_sha256']
    source=ROOT/'data/residual-demand-audit-2025/v1';assert digest(source/'summary.json')==s['residual_summary_sha256']
    assert digest(source/'replay.json')==s['residual_replay_sha256']
    assert digest(folder/'summary.json')==s['transport_summary_sha256']
    base=ROOT/'data/bidding-zone-network-2025/annual-v7';assert digest(base/'summary.json')==s['baseline_summary_sha256']
    obsroot=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((obsroot/'manifest.json').read_text())
    assert digest(obsroot/'manifest.json')==s['observation_manifest_sha256']
    source_summary=json.loads((source/'summary.json').read_text());assert digest(source/'hourly.npz')==source_summary['witness_sha256']
    bs=json.loads((base/'summary.json').read_text());assert digest(base/'annual.npz')==bs['witness_sha256']
    ts=json.loads((folder/'summary.json').read_text());assert digest(folder/'coupled.npz')==ts['witnesses']['coupled.npz']
    checked=[];worst=0.
    with np.load(folder/'benchmark.npz') as b,np.load(source/'hourly.npz') as r,np.load(base/'annual.npz') as p,np.load(folder/'coupled.npz') as c:
        for row in s['zones']:
            z=row['zone'];target_path=obsroot/(z+'.json');assert digest(target_path)==manifest['zones'][z]['hourly_sha256']
            if row['status']!='retrospective_temporal_evaluation':continue
            o=np.array(json.loads(target_path.read_text()),float);area='IE-SEM' if z=='IE' else z
            feature=r['residual_vre'][:,r['zones'].tolist().index(area)]
            # Fixed 4344-hour boundary; no evaluated target participates in these conditions.
            known=np.flatnonzero(np.isfinite(o[:4344]));x=feature[known];y=o[known]
            order=np.argsort(x,kind='stable');x=x[order];y=y[order];u,first,count=np.unique(x,return_index=True,return_counts=True)
            means=np.add.reduceat(y,first)/count;cx=b[z+'_curve_x'];cy=b[z+'_curve_y']
            np.testing.assert_array_equal(cx,u);assert np.diff(cy).min(initial=0)>-1e-8
            prefix=np.cumsum(count*(cy-means));lambda_= -prefix[:-1]
            assert abs(prefix[-1])<1e-5 and lambda_.min(initial=0)>-1e-5
            slack=cy[:-1]-cy[1:];complement=float(abs(lambda_*slack).max(initial=0));assert complement<1e-5
            worst=max(worst,complement,abs(float(prefix[-1])))
            pred=np.interp(feature,cx,cy);np.testing.assert_array_equal(pred,b[z+'_prediction'])
            old=p['bidding_zone_prices'][:,bs['cases']['bidding_zone']['zones'].index(area)];transport=c['prices'][:,ts['metadata']['primary'][area]]
            keep=np.arange(8760)>=4344;keep&=np.isfinite(o)&np.isfinite(old)&np.isfinite(transport)&np.isfinite(pred)
            assert int(keep.sum())==row['evaluation_hours']
            for name,values in [('physical',old),('coupled',transport),('benchmark',pred),('train_mean_reference',np.full(8760,o[known].mean()))]:
                error=values[keep]-o[keep];record=row[name]
                assert abs(float(abs(error).mean())-record['mae_eur_mwh'])<1e-8
                assert abs(float(error.mean())-record['bias_eur_mwh'])<1e-8
                assert abs(float(np.sqrt(np.mean(error**2)))-record['rmse_eur_mwh'])<1e-8
            checked.append(z)
    result=dict(status='training_only_isotonic_KKT_and_temporal_metrics_replayed',areas=len(checked),zones=checked,
        maximum_training_optimality_residual=worst,benchmark_sha256=digest(folder/'benchmark.json'),auditor_sha256=digest(__file__),
        limit='Retrospective temporal separation, not untouched 2025 validation or counterfactual investment acceptance.')
    (folder/'benchmark-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();replay(a.folder)
