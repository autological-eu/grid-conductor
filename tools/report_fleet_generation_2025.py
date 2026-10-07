"""Compare a replayed full-year native dispatch diagnostic with national inventories."""
import argparse, json, math
from pathlib import Path
import pycountry
import numpy as np
from matplotlib.colors import TwoSlopeNorm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reconcile_ember_release import read_generation
from hourly_renewable_estimates import digest

GROUPS={'solar':['solar','solar-hsat'],'wind':['onwind','offwind-ac','offwind-dc','offwind-float'],'hydro':['ror','hydro-reservoir'],'bioenergy':['biomass'],'coal':['coal','lignite'],'gas':['CCGT','OCGT'],'nuclear':['nuclear'],'other fossil':['oil']}
def replay_accounting(folder, output):
    # NpzFile indexing decompresses an array on each lookup. Cache only one block.
    import summarize_annual_native_generation as native
    original = native.energy
    native.energy = lambda arrays, record: original({k: arrays[k] for k in arrays.files}, record)
    try:
        result = native.summarize(folder)
    finally:
        native.energy = original
    if output.exists():
        raise ValueError('Preserve previous replay')
    native.save(output, result)

def run(replay):
    base=Path('data/pypsa-eur')
    d=json.loads(replay.read_text()); saved=json.loads((base/'2025-fixed-inventory-native-generation-candidate-006-v2.json').read_text())
    if any(d[k]!=saved[k] for k in ['status','year','hours','unit','input_sha256','annual_replay_sha256','mapping_calendar_sha256','countries','rows','limitations']):
        raise ValueError('Independent hourly accounting replay differs')
    cap=json.loads((base/'irena-capacity-variant-v1/summary.json').read_text())
    if cap['network_sha256']!=d['input_sha256']: raise ValueError('Mismatched network')
    ep=base/'ember-current-release/monthly.csv'; receipt=json.loads((base/'ember-current-release/reconciliation.json').read_text())
    if digest(ep)!=receipt['current_sha256']: raise ValueError('Ember source changed')
    obs=read_generation(ep,True);rows=[]
    for c in d['countries']:
        iso='XKX' if c['country']=='XK' else pycountry.countries.get(alpha_2=c['country']).alpha_3
        for fuel,carriers in GROUPS.items():
            months=[]
            for m in c['monthly']:
                model=math.fsum(m['primary_generation_mwh_by_model_carrier'].get(k,0) for k in carriers)/1e6
                observed=obs.get((iso,fuel,f"2025-{m['month']:02d}-01"))
                months.append(dict(month=m['month'],model_twh=model,ember_twh=observed))
            model=math.fsum(r['model_twh'] for r in months)
            observed=None if any(r['ember_twh'] is None for r in months) else math.fsum(r['ember_twh'] for r in months)
            rows.append(dict(country=c['country'],fuel=fuel,model_twh=model,ember_twh=observed,coverage_months=sum(r['ember_twh'] is not None for r in months),difference_twh=None if observed is None else model-observed,relative_difference_pct=None if not observed else 100*(model-observed)/observed,monthly=months))
    out=Path('public/research/fleet-generation-2025');out.mkdir(parents=True,exist_ok=True)
    result=dict(status='national_accounting_comparison_not_validation',year=2025,hours=8760,trajectory='PyPSA-Eur 2025 hourly solve, candidate 006; fixed inventories across 59 chronological blocks; not current best or optimum',network_sha256=d['input_sha256'],annual_replay_sha256=d['annual_replay_sha256'],accounting_producer_sha256=d['producer_sha256'],accounting_dependencies=d['dependencies'],ember_sha256=digest(ep),irena_pdf_sha256=cap['irena_pdf_sha256'],capacity_inventory=cap['capacity_inventory'],generation=rows,mapping=GROUPS,limitations=['National scope is not audited bidding-zone scope.','Pumped-storage output excluded from primary generation.','Oil-only model comparator does not exhaust Ember other fossil; waste and geothermal are not silently assigned.','IRENA renewable inventory cannot validate fossil or nuclear capacity.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    plt.rcParams['svg.fonttype']='none'
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,country in zip(axes.flat,['DE','FR','ES','PL']):
        rr=[r for r in rows if r['country']==country and r['fuel'] in ['solar','wind','hydro','coal','gas','nuclear']]
        ax.bar([i-.18 for i in range(len(rr))],[r['model_twh'] for r in rr],.36,label='PyPSA-Eur 2025 hourly solve')
        ax.bar([i+.18 for i in range(len(rr))],[float('nan') if r['ember_twh'] is None else r['ember_twh'] for r in rr],.36,label='Ember current release')
        ax.set_xticks(range(len(rr)),[r['fuel'] for r in rr]);ax.set_title(country);ax.set_ylabel('2025 generation (TWh)');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'annual.svg');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for ax,(country,fuel) in zip(axes.flat,[('DE','gas'),('FR','nuclear'),('ES','wind'),('PL','coal')]):
        r=next(r for r in rows if (r['country'],r['fuel'])==(country,fuel))
        ax.plot(range(1,13),[m['model_twh'] for m in r['monthly']],label='PyPSA-Eur 2025 hourly solve')
        ax.plot(range(1,13),[m['ember_twh'] for m in r['monthly']],label='Ember');ax.set_title(f'{country}: {fuel}');ax.set_ylabel('Monthly TWh');ax.set_xlabel('UTC month');ax.legend()
    fig.tight_layout();fig.savefig(out/'monthly.svg');plt.close(fig)
    countries=sorted({r['country'] for r in rows})
    fuels=list(GROUPS)
    values=np.array([[next(r['difference_twh'] for r in rows if r['country']==c and r['fuel']==f) for f in fuels] for c in countries],dtype=float)
    bound=float(np.nanmax(np.abs(values))) or 1.
    fig,ax=plt.subplots(figsize=(11,15))
    cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#dddddd')
    im=ax.imshow(np.ma.masked_invalid(values),cmap=cmap,norm=TwoSlopeNorm(vmin=-bound,vcenter=0,vmax=bound),aspect='auto')
    ax.set_yticks(range(len(countries)),[f"{c} — {('Kosovo' if c=='XK' else pycountry.countries.get(alpha_2=c).name)}" for c in countries])
    ax.set_xticks(range(len(fuels)),[f if f!='other fossil' else 'Oil / other fossil*' for f in fuels],rotation=35,ha='right')
    for i in range(len(countries)):
        for j in range(len(fuels)):
            v=values[i,j];ax.text(j,i,'—' if not np.isfinite(v) else f'{v:+.1f}',ha='center',va='center',fontsize=8,color='white' if np.isfinite(v) and abs(v)>.55*bound else 'black')
    ax.set_title('2025 annual generation differences by country and fuel\nPyPSA-Eur hourly solve (candidate 006) minus Ember, TWh',pad=18)
    fig.colorbar(im,ax=ax,label='Difference (TWh): negative = model below Ember',shrink=.65)
    fig.text(.05,.015,'Grey / —: incomplete or missing twelve-month observations. *Oil-only model versus broader Ember category.\nNational scope remains unreconciled; differences are diagnostics, not validated accuracy scores.',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));fig.savefig(out/'differences.svg');plt.close(fig)
    for p in out.glob('*.svg'):p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
    for r in rows:
        if r['country'] in ['DE','FR','ES','PL'] and r['fuel'] in ['solar','wind','gas','nuclear']:print(r['country'],r['fuel'],round(r['model_twh'],3),r['ember_twh'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--replay',type=Path,required=True);parser.add_argument('--mapping',type=Path);args=parser.parse_args()
    if args.mapping: replay_accounting(args.mapping,args.replay)
    run(args.replay)
