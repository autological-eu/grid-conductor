"""Source-based wind subtype reconciliation and explicit renewable offer controls.

Never infer available MW from observed generation. All original weather shapes
and geographic/GSK allocations are retained; solar BOS is a generic sensitivity.
"""
import json,re,subprocess
import numpy as np
import xarray as xr
from generation_mix_2025 import ROOT
from irena_capacity_reconciliation import number
from synthetic_bids_2025 import SOURCE

PDF=ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf'
PUBLIC=ROOT/'public/research/irena-capacity-2025/summary.json'
WIND={'onwind','offwind-ac','offwind-dc','offwind-float'}
PV={'solar','solar-hsat'}
CASES=['control','wind_subtypes','solar_bos','availability_combined','solar_bid','wind_bid','both_bids']
DESIGN=dict(cases=CASES,year=2025,hours=8760,
    wind='Replace total-wind-derived technology shares with IRENA end2024/end2025 onshore/offshore trajectories. Keep original source-country identity, within-subtype/spatial/weather shares, p_nom and GSK. Apply only when both subtype endpoints reconcile parent totals within2 MW and positive target fleets have source weather capacity. Missing/inconsistent rows retain original wind; never fill unknown capacity with zero.',
    solar='Generic PVGIS14% overall system-loss sensitivity replaces (does not compound) atlite CSi10% inverter-only loss: multiply original PV availability by0.86/0.90. Temperature/irradiance effects remain in original Huld model. Not an observed national fleet correction or a generation fit.',
    bids='Each original zero-price aggregate splits wind and PV source membership, retaining50/50 blocks. Selected controls offer lower half of original available wind/PV at -10 EUR/MWh, upper half0. No forced generation, subsidy entitlement or recovered actual bids. Other accepted seasonal/Ember bids unchanged.',
    comparison='Run an unmodified common-formulation control because same-cost source splitting can change LP duals and illustrative generation. Compare changes against this control and report accepted annual refit separately.',
    fixed='Source demand, original hourly weather timing, hydro injections/stocks, grid ratings/topology, static original p_nom GSK, fuel inputs and accepted calendar/Ember coefficients. No dispatch-based availability, new forecast, storage or commitment.',
    evaluation='Full-year reconstruction, all41 eligible price zones and48 modeled areas. No fitting or winner-selected baseline promotion. Monthly country/fuel and implied-trade checks retained. Seven finite annual cases; no adaptive search.')


def endpoints(text,names):
    out={}
    for page in text.split('\f'):
        if 'CAP (MW)' not in page:continue
        heading=page.strip().splitlines()[0].strip()
        if heading not in ['Wind energy','Onshore wind energy','Offshore wind energy']:continue
        header=next(x for x in page.splitlines() if 'CAP (MW)' in x);years=list(re.finditer(r'20\d\d',header))
        assert [m.group() for m in years]==[str(y) for y in range(2016,2026)]
        centers=[m.start()+2 for m in years];a=int((centers[-3]+centers[-2])/2);b=int((centers[-2]+centers[-1])/2)
        for line in page.splitlines():
            label=line[:a].strip();country=next((code for name,code in names.items() if label==name or label.startswith(name+'  ')),None)
            if country is None:continue
            cells=[line[a:b].strip(),line[b:].strip()]
            if not all(cells):continue
            try:values=[number(v) for v in cells]
            except ValueError:continue
            key=(country,heading);assert key not in out;out[key]=values
    return out


def source_factors(n):
    public=json.loads(PUBLIC.read_text());names={r['provider_area']:r['country'] for r in public['irena_rows']}
    text=subprocess.check_output(['pdftotext','-layout',str(PDF),'-']).decode();bank=endpoints(text,names)
    for r in public['irena_rows']:
        key=(r['country'],r['technology'])
        if key in bank:assert bank[key]==[r['capacity_2024'],r['capacity_2025']]
    with xr.open_dataset(SOURCE) as d:
        countries=dict(zip(d.buses_i.values,d.buses_country.values));native={str(name):dict(country=countries[bus],carrier=str(carrier),power=float(p)) for name,bus,carrier,p in zip(d.generators_i.values,d.generators_bus.values,d.generators_carrier.values,d.generators_p_nom.values)}
    plans={};inventory=[];elapsed=np.arange(8760)/8760
    for country in sorted({r['country'] for r in native.values()}):
        powers={k:sum(r['power'] for r in native.values() if r['country']==country and r['carrier'] in carriers) for k,carriers in [('on',{'onwind'}),('off',WIND-{'onwind'})]}
        rows=[bank.get((country,k)) for k in ['Wind energy','Onshore wind energy','Offshore wind energy']]
        item=dict(source_country=country,source_onshore_mw=powers['on'],source_offshore_mw=powers['off'])
        if any(r is None for r in rows) or sum(powers.values())<=0:item['status']='missing_endpoints_or_source_fleet_original_retained';inventory.append(item);continue
        v=np.array([[r[0]['mw'],r[1]['mw']] for r in rows]);item['irena_endpoints_mw']=v.tolist()
        if abs(v[0]-v[1:].sum(axis=0)).max()>2:item['status']='parent_child_rounding_scope_conflict_original_retained';inventory.append(item);continue
        if any(powers[k]<=0 and v[i].max()>0 for i,k in [(1,'on'),(2,'off')]):item['status']='positive_target_without_source_weather_original_retained';inventory.append(item);continue
        total=v[0,0]+(v[0,1]-v[0,0])*elapsed
        for i,k in [(1,'on'),(2,'off')]:
            desired=v[i,0]+(v[i,1]-v[i,0])*elapsed;old=total*powers[k]/sum(powers.values())
            plans[country,k]=np.divide(desired,old,out=np.ones(8760),where=old>0)
        item['status']='onshore_offshore_capacity_trajectories_reconciled';inventory.append(item)
    factor=np.ones((8760,len(n.generators)));identity=[]
    for j,(name,g) in enumerate(n.generators.iterrows()):
        key=str(name).split('::',1)[0];original=native.get(key)
        if g.carrier in WIND:
            assert original is not None and original['carrier']==g.carrier
            factor[:,j]=plans.get((original['country'],'on' if g.carrier=='onwind' else 'off'),np.ones(8760))
        identity.append(None if original is None else original['country'])
    assert np.isfinite(factor).all() and (factor>=0).all()
    return factor,inventory,identity,bank


def compile_resources(base,context):
    parent=[];fractions=[];kinds=[];ranks=[];members=[];groups=[];origin=[];weights=[]
    def family(i):
        key=context['generation_keys'][i]
        return 'wind' if key and key[1]=='Wind' else 'solar' if key and key[1]=='Solar' else context['classes'][next(k for k,ids in enumerate(context['groups']) if i in ids)] or 'other'
    labels={i:family(i) for ids in context['groups'] for i in ids}
    for k,ids in enumerate(context['groups']):
        for kind in sorted({labels[i] for i in ids}):
            selected=[i for i in ids if labels[i]==kind];parts=[.5,.35,.15] if kind in ['gas','coal'] else [.5,.5] if kind in ['wind','solar'] else [1.]
            for rank,f in enumerate(parts):
                parent.append(k);fractions.append(f);kinds.append(kind);ranks.append(rank);members.append(selected)
                groups.append(list(range(len(origin),len(origin)+len(selected))));origin.extend(selected);weights.extend([f]*len(selected))
    p=np.array(parent);m=base.copy();m['ng']=len(p);m['A']=base['A'][:,np.r_[p,np.arange(base['ng'],base['A'].shape[1])]].tocsc();m['cost']=base['cost'][:,p].copy()
    m['availability']=np.column_stack([context['availability'][:,ids].sum(axis=1)*f for ids,f in zip(members,fractions)])
    for key in ['offer_zones','emergency_mask']:m[key]=base[key][p]
    ctx=context.copy();ctx.update(groups=groups,availability=context['availability'][:,origin]*weights,classes=[k if k in ['gas','coal','nuclear'] else None for k in kinds])
    for key in ['generation_keys','country_keys']:ctx[key]=[context[key][i] for i in origin]
    layout=dict(parent=parent,fractions=fractions,kinds=kinds,ranks=ranks,members=members,origin=origin,source_weights=weights)
    return m,ctx,layout


def availability(n,source,wind,case):
    assert case in CASES
    factor=np.ones_like(source)
    if case not in ['control','solar_bos']:factor*=wind
    if case not in ['control','wind_subtypes']:
        ids=np.flatnonzero(n.generators.carrier.isin(PV));factor[:,ids]*=.86/.90
    return source*factor
