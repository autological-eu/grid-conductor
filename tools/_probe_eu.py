import json,sys,time
sys.path.insert(0,r'tools')
from market_model import dispatch
d=json.load(open(r'data/eu-market/input.json',encoding='utf-8'))
t0=time.time();r=dispatch(d)
rows=r['hourly']
obs=d.get('observed_price_eur_mwh',{})
maes={}
for z,p in obs.items():
    pairs=[(m,o) for row in rows for (m,o) in [(row['price_eur_mwh'][z],v)] for v in [p[rows.index(row)]] if m is not None and v is not None]
    maes[z]=round(sum(abs(a-b) for a,b in pairs)/len(pairs),2) if pairs else None
print('dispatch OK in %.1fs'%(time.time()-t0))
print('total_cost_meur',round(r['total_cost_eur']/1e6,1),'co2_mt',round(r['total_co2_t']/1e3,1),'unserved_mwh',round(r['unserved_mwh']))
zs=sorted(maes,key=lambda z:-(maes[z] or 0))
print('price MAE vs observed, worst first')
for z in zs[:6]:print(' ',z,maes[z])
print(' best:')
print(' ',', '.join('%s=%s'%(z,maes[z]) for z in zs[-4:]))
h0=rows[0]
print('h0 prices:',', '.join('%s=%.0f'%(z,h0['price_eur_mwh'][z]) for z in ['DE-LU','FR','IT-North','BE','NL','ES','PL','GB']))
print('h10 DE-LU',round(h0['price_eur_mwh']['DE-LU']),'FR',round(h0['price_eur_mwh']['FR']))
print('flow FR>BE h0',round(h0['flow_mw']['FR-BE']),'DE-LU>FR h0',round(h0['flow_mw'].get('DE-LU-FR')))
osd=json.dumps(dict(price_mae_eur_mwh=maes,dispatch_cost_meur=round(r['total_cost_eur']/1e6,1),
    dispatch_co2_mt=round(r['total_co2_t']/1e3,1),unserved_mwh=round(r['unserved_mwh']),
    priced_zones=len(rows[0]['price_eur_mwh'])),indent=1)
open(r'output/eu-market-dispatch.json','w',encoding='utf-8').write(osd)
print('wrote output/eu-market-dispatch.json')
