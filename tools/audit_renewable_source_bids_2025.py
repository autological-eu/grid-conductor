"""Independent wind endpoint, availability, renewable-bid and annual LP replay."""
import argparse,json,logging,re,resource,signal,subprocess,time
from pathlib import Path
import numpy as np
import xarray as xr
import yaml
from bs4 import BeautifulSoup
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from audit_nve_hydro_diagnostics_2025 import physics
from price_mechanism_2025 import dual_replay
from audit_seasonal_calendar_bids_2025 import compare,price_summary
from synthetic_bids_2025 import SOURCE


WIND={'onwind','offwind-ac','offwind-dc','offwind-float'}
PV={'solar','solar-hsat'}


def parse_irena():
    public=json.loads((ROOT/'public/research/irena-capacity-2025/summary.json').read_text());names={r['provider_area']:r['country'] for r in public['irena_rows']}
    pdf=ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf';assert digest(pdf)==public['irena_pdf_sha256']
    text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],stderr=subprocess.DEVNULL).decode();bank={}
    for page in text.split('\f'):
        if 'CAP (MW)' not in page:continue
        tech=page.strip().splitlines()[0].strip()
        if tech not in ['Wind energy','Onshore wind energy','Offshore wind energy']:continue
        h=next(x for x in page.splitlines() if 'CAP (MW)' in x);centers=np.array([m.start()+2 for m in re.finditer(r'20\d\d',h)])
        assert len(centers)==10
        for line in page.splitlines():
            label=re.split(r'\s{2,}',line.strip())[0]
            if label not in names:continue
            cells=list(re.finditer(r'\d+(?: \d{3})*(?:\.\d+)?(?: [oue])?',line))
            if len(cells)<2:continue
            last=cells[-2:]
            if [int(np.argmin(abs(centers-(m.start()+m.end())/2))) for m in last]!=[8,9]:continue
            vals=[]
            for match in last:
                value=match.group();flag=value[-1] if value[-1] in 'oue' else None
                if flag:value=value[:-1].strip()
                vals.append(dict(mw=float(value.replace(' ','')),source_flag=flag))
            k=names[label],tech;assert k not in bank;bank[k]=vals
    return bank


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert digest(ROOT/'tools/run_renewable_source_bids_2025.py')==s['producer_sha256']
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    for p,h in s['files'].items():assert digest(folder/p)==h
    bank=parse_irena();records=json.loads((folder/'capacity-inventory.json').read_text())
    produced={(r['country'],r['technology']):[r['capacity_2024'],r['capacity_2025']] for r in records['endpoints']}
    for key,values in produced.items():compare(values,bank[key])
    additional=set(bank)-set(produced)
    # The independent parser can recover narrow onshore cells rejected by the
    # producer. They must not complete a usable parent/subtype trio unnoticed.
    for c,t in additional:
        assert any((c,k) not in bank for k in ['Wind energy','Onshore wind energy','Offshore wind energy'])
    extra_rows=[dict(country=c,technology=t,reason='Producer conservatively rejected narrow cells; no complete independent parent/on/off trio, so original fleet remains.') for c,t in sorted(additional)]
    panel=ROOT/'data/pypsa-eur/upstream/.pixi/envs/default/lib/python3.12/site-packages/atlite/resources/solarpanel/CSi.yaml';assert yaml.safe_load(panel.read_text())['inverter_efficiency']==.9
    text=BeautifulSoup((folder/'pvgis-methodology.html').read_text(),'html.parser').get_text(' ',strip=True)
    assert 'default value of 14%' in text
    root=ROOT/s['accepted_folder'];accepted=json.loads((root/'summary.json').read_text())
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    native={}
    with xr.open_dataset(SOURCE) as ds:
        countries=dict(zip(ds.buses_i.values,ds.buses_country.values))
        for name,bus,carrier,power in zip(ds.generators_i.values,ds.generators_bus.values,ds.generators_carrier.values,ds.generators_p_nom.values):native[str(name)]=(countries[bus],str(carrier),float(power))
    def kind(carrier):
        return 'wind' if carrier in WIND else 'solar' if carrier in PV else 'gas' if carrier in ['CCGT','OCGT'] else 'coal' if carrier in ['coal','lignite'] else 'nuclear' if carrier=='nuclear' else 'other'
    grouped={}
    for i,(_,g) in enumerate(n.generators.iterrows()):grouped.setdefault((base['buszone'][g.bus],raw[:,i].tobytes(),g.carrier=='emergency'),[]).append(i)
    assert len(grouped)==base['ng']
    layout=dict(parent=[],fractions=[],kinds=[],ranks=[],members=[],origin=[],source_weights=[])
    for parent,ids in enumerate(grouped.values()):
        for family in sorted({kind(n.generators.iloc[i].carrier) for i in ids}):
            selected=[i for i in ids if kind(n.generators.iloc[i].carrier)==family]
            parts=[.5,.35,.15] if family in ['gas','coal'] else [.5,.5] if family in ['wind','solar'] else [1.]
            for rank,f in enumerate(parts):
                for key,value in [('parent',parent),('fractions',f),('kinds',family),('ranks',rank),('members',selected)]:layout[key].append(value)
                layout['origin']+=selected;layout['source_weights'] += [f]*len(selected)
    compare(layout,json.loads((folder/'layout.json').read_text()))
    parent=np.array(layout['parent']);m=base.copy();m['ng']=len(parent);m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc();m['cost']=base['cost'][:,parent]
    for k in ['offer_zones','emergency_mask']:m[k]=base[k][parent]
    source=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    coefficients={};inventory=[];identities=[]
    for c in sorted({v[0] for v in native.values()}):
        on=sum(v[2] for v in native.values() if v[0]==c and v[1]=='onwind');offshore=sum(v[2] for v in native.values() if v[0]==c and v[1] in WIND-{'onwind'})
        r=[bank.get((c,t)) for t in ['Wind energy','Onshore wind energy','Offshore wind energy']];item=dict(source_country=c,source_onshore_mw=on,source_offshore_mw=offshore)
        if any(v is None for v in r) or on+offshore<=0:item['status']='missing_endpoints_or_source_fleet_original_retained';inventory.append(item);continue
        v=np.array([[q[0]['mw'],q[1]['mw']] for q in r]);item['irena_endpoints_mw']=v.tolist()
        if np.max(abs(v[0]-v[1]-v[2]))>2:item['status']='parent_child_rounding_scope_conflict_original_retained';inventory.append(item);continue
        if (on<=0 and v[1].max()>0) or (offshore<=0 and v[2].max()>0):item['status']='positive_target_without_source_weather_original_retained';inventory.append(item);continue
        item['status']='onshore_offshore_capacity_trajectories_reconciled';inventory.append(item)
        for family,p,i in [('on',on,1),('off',offshore,2)]:coefficients[c,family]=(v[0],v[i],p,on+offshore)
    compare(inventory,s['capacity_inventory']);compare(inventory,records['records'])
    wind=np.ones_like(source);hour=np.arange(8760)/8760
    for j,(name,g) in enumerate(n.generators.iterrows()):
        old=native.get(str(name).split('::',1)[0]);identities.append(None if old is None else old[0])
        if g.carrier not in WIND:continue
        assert old is not None and old[1]==g.carrier
        key=old[0],'on' if g.carrier=='onwind' else 'off'
        if key in coefficients:
            total,target,power,whole=coefficients[key];den=(total[0]+(total[1]-total[0])*hour)*power/whole;num=target[0]+(target[1]-target[0])*hour
            wind[:,j]=np.divide(num,den,out=np.ones(8760),where=den>0)
    countries=s['countries'];fuels=['Wind','Solar','Nuclear','Gas','Coal'];fmap={v:k for k,vs in EMBER.items() for v in vs};labels=[(n.buses.loc[g.bus,'country'],fmap.get(CARRIER[g.carrier])) for _,g in n.generators.iterrows()]
    shares=np.zeros((m['ng'],len(countries)))
    for j,ids in enumerate(layout['members']):
        for i in ids:shares[j,countries.index(labels[i][0])]+=n.generators.iloc[i].p_nom
        if shares[j].sum():shares[j]/=shares[j].sum()
    proposal=json.loads((root/'proposal-refit.json').read_text());beta=np.array(proposal['beta']);gamma=np.array(proposal['gamma'])
    with np.load(root/'calendar.npz') as z:features=z['features'];season=z['season']
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    water=np.zeros((8760,len(countries)));demand=np.zeros_like(water);loads=n.get_switchable_as_dense('Load','p_set')
    for ci,c in enumerate(countries):
        buses=n.buses.index[n.buses.country==c];water[:,ci]=fixed[buses].sum(axis=1);demand[:,ci]=loads[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1)
    certs=[]
    for name,info in s['annuals'].items():
        path=folder/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        av=source.copy()
        if name!='control':
            if name!='solar_bos':av*=wind
            if name!='wind_subtypes':av[:,n.generators.carrier.isin(PV)]*=.86/.9
        candidate=m.copy();candidate['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
        assert immutable_hashes(candidate,flow)==s['case_physical_inputs'][name]
        native_case=base.copy();native_case['availability']=np.column_stack([av[:,ids].sum(axis=1) for ids in grouped.values()])
        original=np.zeros((8760,base['ng']))
        for j,k in enumerate(parent):original[:,k]+=x[:,j]
        residual=physics(n,native_case,np.c_[original,x[:,m['ng']:]],base['load'],off.copy(),0)
        cost=m['cost'].copy()
        for j,(family,rank) in enumerate(zip(layout['kinds'],layout['ranks'])):
            if family in ['gas','coal','nuclear']:
                zi=m['zones'].index(m['offer_zones'][j]);fi=['gas','coal','nuclear'].index(family)
                d=(features[:,zi]*beta[zi]).sum(axis=1)+(season@gamma[:,fi].T)@shares[j]
                cost[:,j]=np.maximum(cost[:,j]+np.clip(d,-30,30)*(.25 if family=='nuclear' else 1),0)
            if rank==0 and ((family=='solar' and name in ['solar_bid','both_bids']) or (family=='wind' and name in ['wind_bid','both_bids'])):cost[:,j]-=10
        errors=[np.maximum(-x[:,:m['ng']],0).max(),np.maximum(x[:,:m['ng']]-candidate['availability'],0).max()]
        assert max(errors)<1e-4
        error=float(abs((x[:,:m['ng']]*cost).sum(axis=1)-obj).max());assert error<.05
        reduced=np.c_[cost,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@y.T).T
        dual=dual_replay(candidate|dict(cost=cost),x,y,reduced,obj,flow)
        compare(price_summary(y[:,:m['nz']],target['prices'],m['zones']),s['outcomes'][name]['prices'])
        lo=np.zeros((12,len(countries),5));hi=np.zeros_like(lo);cl=np.zeros((12,len(countries)));cu=np.zeros_like(cl);cp=np.zeros_like(cl)
        def add(v):return np.bincount(MONTH,weights=v,minlength=13)[1:]/1e6
        for j,(ids,f) in enumerate(zip(layout['members'],layout['fractions'])):
            a=av[:,ids].sum(axis=1)*f;q=np.clip(x[:,j],0,a)
            for c in {labels[i][0] for i in ids}:
                ci=countries.index(c);real=[i for i in ids if labels[i][0]==c and n.generators.iloc[i].carrier!='emergency'];cap=av[:,real].sum(axis=1)*f
                cl[:,ci]+=add(np.maximum(q-a+cap,0));cu[:,ci]+=add(np.minimum(q,cap));cp[:,ci]+=add(np.divide(q*cap,a,out=np.zeros(8760),where=a>0))
                for fuel in fuels:
                    selected=[i for i in real if labels[i][1]==fuel]
                    if not selected:continue
                    cap=av[:,selected].sum(axis=1)*f;fi=fuels.index(fuel);lo[:,ci,fi]+=add(np.maximum(q-a+cap,0));hi[:,ci,fi]+=add(np.minimum(q,cap))
        dm=np.column_stack([add(demand[:,i]) for i in range(len(countries))]);w=np.column_stack([add(water[:,i]) for i in range(len(countries))]);cl+=w-dm;cu+=w-dm;cp+=w
        monthly=[dict(month=i+1,generation_lower_twh=lo[i].tolist(),generation_upper_twh=hi[i].tolist(),generation_point_twh=cp[i].tolist(),net_export_lower_twh=cl[i].tolist(),net_export_upper_twh=cu[i].tolist(),net_export_point_twh=(cp-dm)[i].tolist(),demand_twh=dm[i].tolist()) for i in range(12)]
        compare(monthly,s['outcomes'][name]['monthly_quantities'])
        ref=target['generation'];tr=target['trade'];known=np.isfinite(ref);tk=np.isfinite(tr)
        q=dict(price=s['outcomes'][name]['prices']['equal_zone_mae'],generation=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean()),trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean()),price_areas=41,generation_targets=int(known.sum()),trade_targets=int(tk.sum()))
        compare(q,s['outcomes'][name]['quantity_errors'])
        for row in s['availability_audits'][name]:
            carriers={'onshore':{'onwind'},'offshore':WIND-{'onwind'},'solar':PV}[row['technology']]
            ids=[i for i,g in enumerate(n.generators.itertuples()) if identities[i]==row['source_country'] and g.carrier in carriers]
            assert abs(row['original_available_twh']-source[:,ids].sum()/1e6)<1e-8 and abs(row['case_available_twh']-av[:,ids].sum()/1e6)<1e-8
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency-info['emergency_mwh'])<1e-8
        certs.append(dict(case=name,hours=8760,original_component_residual_mw=residual,source_group_bound_residual_mw=float(max(errors)),objective_error_eur=error,**dual));print('Replayed',name,flush=True)
    for name,inputs in s['case_physical_inputs'].items():
        for k,v in s['case_physical_inputs']['control'].items():
            if k!='availability':assert inputs[k]==v
    out.mkdir(parents=True,exist_ok=False);result=dict(status='renewable_capacity_endpoints_availability_resource_bids_physics_duals_and_annual_metrics_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certs,irena_endpoint_rows=len(bank),independent_additional_rows_not_applied=extra_rows,elapsed_seconds=time.perf_counter()-began)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder,a.out or a.folder/'verification-v1')
