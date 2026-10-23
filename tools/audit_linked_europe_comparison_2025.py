"""Independent saved-array/source metric replay; no solve or parameter changes."""
import json
import time
import numpy as np
from generation_mix_2025 import ROOT,digest,EMBER

OUT=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-robust-v1/observed-comparison-v1'


def audit():
    started=time.perf_counter();s=json.loads((OUT/'summary.json').read_text())
    assert s['producer_sha256']==digest(ROOT/'tools/evaluate_linked_europe_2025.py')
    for f,h in s['sources'].items():assert digest(ROOT/f)==h,f
    for f,h in s['dependencies'].items():assert digest(ROOT/'tools'/f)==h,f
    assert digest(OUT/'hourly-comparison.npz')==s['hourly_sha256']
    with np.load(OUT/'hourly-comparison.npz') as z:a={k:z[k] for k in z.files}
    observed=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices']
    np.testing.assert_array_equal(a['observed_prices'],observed)
    mask=np.isfinite(observed).all(axis=0);assert mask.sum()==41
    unchanged=~a['coupled_hours'];assert unchanged.sum()==6570
    np.testing.assert_array_equal(a['baseline_prices'][unchanged],a['linked_prices'][unchanged])
    np.testing.assert_array_equal(a['baseline_generation'][unchanged],a['linked_generation'][unchanged])
    prices=0;generation=0;hourly=0
    months=np.repeat(np.arange(1,13),[31*24,28*24,31*24,30*24,31*24,30*24,31*24,31*24,30*24,31*24,30*24,31*24])
    # Original Ember CSV cells, without producer's parsing/aggregation helpers.
    import csv,pycountry
    bank={}
    with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:
        for r in csv.DictReader(f):
            if r['Date'].startswith('2025-') and r['Area type'] in ['Country','Country or economy'] and r['Generation (TWh)'].strip():bank[r['ISO 3 code'],r['Electricity source'],int(r['Date'][5:7])]=float(r['Generation (TWh)'])
    for case in ['baseline','linked']:
        p=a[case+'_prices'];g=a[case+'_generation']
        assert abs(float(np.mean(np.abs(p[:,mask]-observed[:,mask])))-s['price_scores'][case]['mae'])<1e-10
        for row in [r for r in s['prices'] if r['case']==case]:
            zi=s['zones'].index(row['zone']);known=np.isfinite(observed[:,zi]);assert known.sum()==row['known_hours']
            if known.any():
                e=p[known,zi]-observed[known,zi]
                assert abs(abs(e).mean()-row['mae_eur_mwh'])<1e-10
                assert abs(e.mean()-row['bias_eur_mwh'])<1e-10
                assert abs(np.sqrt((e*e).mean())-row['rmse_eur_mwh'])<1e-10
                prices+=1
        for row in [r for r in s['ember_monthly'] if r['case']==case]:
            ci=s['countries'].index(row['country']);ids=[s['technologies'].index(f) for f in EMBER[row['fuel']]]
            value=g[months==row['month'],ci][:,ids].sum()/1e6
            assert abs(value-row['model_twh'])<1e-9
            iso='XKX' if row['country']=='XK' else pycountry.countries.get(alpha_2=row['country']).alpha_3
            assert row['observed_twh']==bank.get((iso,row['fuel'],row['month']))
            generation+=1
        for row in [r for r in s['hourly_generation'] if r['case']==case]:
            ci=s['countries'].index(row['country']);fi=s['technologies'].index(row['technology']);o=a['observed_generation'][:,ci,fi];good=np.isfinite(o)
            assert good.sum()==row['known_hours']
            if good.any():
                e=g[good,ci,fi]-o[good]
                assert abs(abs(e).mean()-row['mae_mw'])<1e-8
                assert abs(g[good,ci,fi].sum()/1e6-row['model_twh'])<1e-9
                hourly+=1
    result=dict(status='all_saved_prices_and_monthly_hourly_generation_metrics_replayed',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),hourly_sha256=digest(OUT/'hourly-comparison.npz'),price_zone_case_checks=prices,monthly_generation_checks=generation,hourly_generation_checks=hourly,seconds=time.perf_counter()-started,scope='Independent metric/source replay; allocation/source-capacity partition and primary-generation closure checked by producer. Original network/linked-price/storage certificates remain in parent annual audit.')
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)


if __name__=='__main__':audit()
