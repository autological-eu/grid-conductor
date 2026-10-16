"""Rank accepted annual reconstruction errors; no fitting or market clearing.

Generation associations are descriptive, not causal input/bid error attribution.
The combined array name belongs to the derivation format and means refit here.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT, MONTH, digest


def correlation(a, b):
    good = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[good], b[good])[0, 1]) if good.sum() > 2 and np.std(a[good]) > 1e-8 and np.std(b[good]) > 1e-8 else None


def diagnose(folder, output):
    baseline = json.loads((ROOT/'config/research-baseline.json').read_text())
    model = ROOT/Path(baseline['summary_path']).parent
    assert digest(ROOT/baseline['summary_path']) == baseline['summary_sha256']
    s = json.loads((folder/'summary.json').read_text())
    a = json.loads((folder/'verification-v1/audit.json').read_text())
    assert a['summary_sha256'] == digest(folder/'summary.json')
    assert 'accepted single annual refit' in s['period']
    assert digest(folder/'comparison.npz') == s['witness_sha256']
    with np.load(model/'development-targets.npz') as z: first = z['prices']
    with np.load(model/'evaluation-targets.npz') as z: observed = np.concatenate([first, z['prices']])
    with np.load(folder/'comparison.npz') as z: arrays = {k:z[k] for k in z.files}
    with np.load(model/baseline['witness']['witness']) as z:
        np.testing.assert_array_equal(arrays['combined_prices'], z['row_duals'][:, :len(s['zones'])])
    rows = []
    for j, zone in enumerate(s['zones']):
        p = arrays['combined_prices'][:, j]; o = observed[:, j]; good = np.isfinite(o)
        row = dict(zone=zone, known_price_hours=int(good.sum()))
        if not good.any():
            rows.append(row); continue
        assert good.all(), 'Partial price years must not silently enter the complete-year headline'
        error = p-o; daily = error.reshape(365, 24).mean(axis=1)
        row.update(mae_eur_mwh=float(abs(error).mean()), bias_eur_mwh=float(error.mean()),
                   correlation=correlation(p,o), daily_mean_error_mae=float(abs(daily).mean()),
                   within_day_error_mae=float(abs(error.reshape(365,24)-daily[:,None]).mean()),
                   observed_negative_hours=int((o < -1e-6).sum()), modeled_negative_hours=int((p < -1e-6).sum()),
                   negative_hour_mae=float(abs(error[o < -1e-6]).mean()) if (o < -1e-6).any() else None,
                   monthly=[dict(month=m, mae=float(abs(error[MONTH==m]).mean()),bias=float(error[MONTH==m].mean())) for m in range(1,13)])
        fuels = []
        for k, fuel in enumerate(s['technologies']):
            gen = arrays['combined_point'][:,j,k]; ref = arrays['observed'][:,j,k]; known = np.isfinite(ref)
            if not known.any(): continue
            lo = arrays['combined_lower'][:,j,k]; hi = arrays['combined_upper'][:,j,k]
            outside = gen-ref
            monthly = []
            for m in range(1,13):
                mask = known & (MONTH==m)
                if not mask.any(): continue
                q,r,l,u = [float(v[mask].sum()/1e6) for v in (gen,ref,lo,hi)]
                monthly.append(dict(month=m,known_hours=int(mask.sum()),model_twh=q,observed_twh=r,
                                    difference_twh=q-r,outside_interval_twh=max(l-r,r-u,0.)))
            fuels.append(dict(technology=fuel,known_hours=int(known.sum()),model_twh=float(gen[known].sum()/1e6),
                              observed_twh=float(ref[known].sum()/1e6),difference_twh=float(outside[known].sum()/1e6),
                              hourly_mix_error_price_error_correlation=correlation(outside[known],error[known]),
                              generation_shape_correlation=correlation(gen[known],ref[known]),monthly=monthly))
        row['generation'] = fuels
        rows.append(row)
    eligible = [r for r in rows if r['known_price_hours']]
    mae = float(np.mean([r['mae_eur_mwh'] for r in eligible]))
    assert len(eligible)==41 and abs(mae-baseline['prices']['equal_zone_mae'])<1e-9
    ranked = sorted(eligible,key=lambda r:-r['mae_eur_mwh'])
    result = dict(status='accepted_refit_price_and_mix_diagnosis',year=2025,annual_case='refit',
                  baseline_config_sha256=digest(ROOT/'config/research-baseline.json'),
                  derivation_summary_sha256=digest(folder/'summary.json'),derivation_audit_sha256=digest(folder/'verification-v1/audit.json'),
                  producer_sha256=digest(__file__),hours=8760,observed_zones=len(eligible),equal_zone_mae=mae,
                  target_mae=10.,remaining_reduction_percent=100*(1-10/mae),
                  mean_daily_level_error_mae=float(np.mean([r['daily_mean_error_mae'] for r in eligible])),
                  mean_within_day_error_mae=float(np.mean([r['within_day_error_mae'] for r in eligible])),
                  top_ten_zones=[r['zone'] for r in ranked[:10]],
                  top_ten_share_absolute_error=float(sum(r['mae_eur_mwh'] for r in ranked[:10])/sum(r['mae_eur_mwh'] for r in ranked)),
                  zones=rows,limitations=[
                      'All-year price-calibrated reconstruction; no independent prediction accuracy or causal error shares.',
                      'Daily means and within-day diagnostics use observed errors and are not deployable price corrections; MAEs do not add.',
                      'Generation uses saved-group proportional illustrations and conditional bounds; missing A75 and national/zonal scope caveats persist.',
                      'Generation and price associations can reflect shared demand/weather/network effects; no fitted input corrections follow.',
                      'Partial generation months retain known hours only; unknown prices/generation are not zero-filled.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['zones','limitations']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();diagnose(a.folder,a.output)
