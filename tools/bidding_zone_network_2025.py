"""Boundary-preserving grid refinement and conserved allocation of retained inputs.

Original aggregate generator profiles remain proxies. No prices/generation targets
are used to allocate supply. Raw member buses, demand and plant locations decide
allocation; unknown intracluster renewable location uses explicit member shares.
"""
import json, logging, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa, xarray as xr
import networkx as nx
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from pypsa.clustering.spatial import get_clustering_from_busmap
from nve_hydro_diagnostics import ROOT, rebuild, digest
from european_physical_bids_2025 import compile_model
from european_reservoir_clearing_2025 import aggregate_offers

BASE=ROOT/'data/bidding-zone-network-2025'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'

def boundaries():
    f=BASE/'sources';path=f/'electricitymaps-world.geojson';receipt=json.loads(path.with_name(path.name+'.receipt.json').read_text());assert digest(path)==receipt['sha256']
    features=json.loads(path.read_text())['features'];zones={};countries={};sources={str(path.relative_to(ROOT)):digest(path)}
    rename={'DE':'DE-LU','LU':'DE-LU','IE':'IE-SEM','GB-NIR':'IE-SEM','DK-DK1':'DK1','DK-DK2':'DK2'}
    for feature in features:
        props=feature['properties'];name=props['zoneName'];country=props.get('countryKey','')
        if country=='IT' or country=='NO':continue
        if name.startswith('SE-SE'):name=name.split('-')[1]
        name=rename.get(name,name)
        zones.setdefault(name,[]).append(shape(feature['geometry']));countries.setdefault(country,set()).add(name)
    path=ROOT/'data/bidding-zone-source-audit-2025/nve-zones.json';meta=json.loads(path.with_suffix('.meta.json').read_text());assert digest(path)==meta['sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
    for feature in json.loads(path.read_text())['features']:
        name=feature['properties']['ElSpotOmr'];zones.setdefault(name,[]).append(shape(feature['geometry']));countries.setdefault('NO',set()).add(name)
    names={'IT_NORD':'IT-North','IT_CNOR':'IT-CNOR','IT_CSUD':'IT-CSUD','IT_SUD':'IT-SUD','IT_CALA':'IT-CALA','IT_SARD':'IT-SARD','IT_SICI':'IT-SICI'}
    for source,name in names.items():
        path=f/('italian-zones.geojson' if source=='IT_NORD' else source+'.geojson')
        receipt_path=path.with_name(path.name+'.receipt.json') if source=='IT_NORD' else path.with_suffix('.receipt.json')
        assert digest(path)==json.loads(receipt_path.read_text())['sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
        zones[name]=[shape(v['geometry']) for v in json.loads(path.read_text())['features']];countries.setdefault('IT',set()).add(name)
    return {k:unary_union(v).buffer(0) for k,v in zones.items()},countries,sources

def locate(point,country,shapes,countries):
    candidates=sorted(countries.get(country,set()))
    if not candidates:raise ValueError('No geographic source for '+country)
    # Countries with one modeled commercial area do not require a coastal snap.
    if len(candidates)==1:return candidates[0],'single_area_country',0.
    contained=[z for z in candidates if shapes[z].covers(point)]
    if len(contained)==1:return contained[0],'polygon',0.
    if len(contained)>1:raise ValueError('Overlapping bidding-zone polygons: '+str(contained))
    nearest=sorted((shapes[z].distance(point),z) for z in candidates)
    # Coordinates are WGS84; distance is only a transparent snap diagnostic.
    distance,z=nearest[0]
    if distance>.5:raise ValueError('Unresolved offshore/coastal bus: '+country+' '+str(point))
    return z,'nearest_polygon_proxy',float(distance)

def raw_mapping(raw):
    shapes,countries,sources=boundaries();rows=[]
    offshore={};graph=nx.Graph();graph.add_nodes_from(raw.buses.index)
    for component in ['Line','Link']:
        for _,r in raw.df(component).iterrows():
            if raw.buses.loc[r.bus0,'country']==raw.buses.loc[r.bus1,'country']:graph.add_edge(r.bus0,r.bus1)
    if 'onshore_bus' in raw.buses:
        for country,bs in raw.buses.groupby('country'):
            shores=bs.index[bs.onshore_bus]
            if len(shores):
                paths=nx.multi_source_dijkstra_path(graph.subgraph(bs.index),sorted(shores))
                offshore.update({b:path[0] for b,path in paths.items() if b not in shores})
    for b,r in raw.buses.iterrows():
        if b in offshore:
            shore=raw.buses.loc[offshore[b]];z,_,distance=locate(Point(shore.x,shore.y),shore.country,shapes,countries);method='electrical_shore_connection_proxy'
        else:z,method,distance=locate(Point(r.x,r.y),r.country,shapes,countries)
        rows.append(dict(bus=b,zone=z,method=method,distance_degrees=distance))
    return pd.DataFrame(rows).set_index('bus'),sources

def build():
    original,old,hp,mask,water,nve=rebuild();raw=pypsa.Network()
    # NetCDF variable-length geometry strings inflate to >1.6 GiB Unicode
    # arrays on import. Physics uses x/y and electrical attributes, not WKT/tags.
    with xr.open_dataset(GRID/'networks/base.nc') as ds:
        unused=[v for v in ds.data_vars if v.endswith(('_geometry','_tags','_symbol'))]
        raw.import_from_netcdf(ds.drop_vars(unused))
    del ds
    mapping,sources=raw_mapping(raw);simple=pd.read_csv(GRID/'busmap_base_s.csv',index_col=0).iloc[:,0];old_parent=pd.read_csv(GRID/'busmap_base_s_128.csv',index_col=0).iloc[:,0]
    parent=simple.map(old_parent);assert set(parent)==set(original.buses.index)
    mixed_simple=mapping.zone.groupby(simple.reindex(mapping.index)).nunique();mixed_simple=mixed_simple[mixed_simple>1].to_dict()
    # Use pinned upstream voltage/converter/DC-chain routines, but DO NOT remove
    # stubs: country-only stub elimination erased three commercial crossings.
    for _,r in raw.transformers.iterrows():assert mapping.loc[r.bus0,'zone']==mapping.loc[r.bus1,'zone'],'Transformer crosses an unresolved zone boundary'
    upstream=ROOT/'data/pypsa-eur/upstream';sys.path.insert(0,str(upstream))
    from scripts.simplify_network import simplify_network_to_380,remove_converters,simplify_links
    typ='Al/St 240/40 4-bundle 380.0'
    raw,tm=simplify_network_to_380(raw,typ);raw,cm=remove_converters(raw);raw,dc=simplify_links(raw,1.,-1.)
    raw.buses.carrier='AC'
    mapping=mapping.reindex(raw.buses.index);parent=parent.reindex(raw.buses.index)
    assert not mapping.zone.isna().any() and not parent.isna().any()
    factor=original.lines.s_max_pu.unique();assert len(factor)==1;raw.lines.s_max_pu=float(factor[0])
    descriptive=['symbol','tags','under_construction','onshore_bus','geometry','underground','project_status']
    raw.buses.drop(columns=descriptive,errors='ignore',inplace=True);raw.lines.drop(columns=descriptive,errors='ignore',inplace=True)
    mapping['parent']=parent;mapping['refined_bus']=mapping['parent']+'::'+mapping['zone']
    # Split each existing cluster at actual member-bus zone boundaries BEFORE
    # aggregating branches. Cross-zone source branches can no longer disappear.
    physical=get_clustering_from_busmap(raw,mapping.refined_bus,with_time=False,bus_strategies={'country':'first','substation_lv':lambda x:bool(x.any()),'substation_off':lambda x:bool(x.any())},custom_line_groupers=['build_year']).n
    physical.set_snapshots(original.snapshots);physical.snapshot_weightings=original.snapshot_weightings.copy()
    zone_by_bus=mapping.groupby('refined_bus').zone.first();physical.buses['bidding_zone']=zone_by_bus
    physical.determine_network_topology()
    children={p:sorted(mapping.loc[mapping.parent==p,'refined_bus'].unique()) for p in original.buses.index}
    counts=mapping.groupby('refined_bus').size()
    demands={b:np.zeros(8760) for b in physical.buses.index}
    groups=simple.reindex(mapping.index).groupby(simple.reindex(mapping.index)).groups
    splits={s:mapping.loc[list(ids),'refined_bus'].value_counts(normalize=True).to_dict() for s,ids in groups.items()}
    # Stream bus blocks instead of allocating the 276 MiB demand array alongside
    # the reconstructed source network and weather/cost witnesses.
    with xr.open_dataarray(GRID/'electricity_demand_base_s.nc') as d:
        columns=d.bus.values
        for start in range(0,len(columns),128):
            batch=columns[start:start+128];values=d.sel(bus=batch).values
            for j,s in enumerate(batch):
                for b,share in splits.get(str(s),{}).items():demands[b]+=values[:,j]*share
    # Preserve source demand hour by hour at each old parent, not country totals only.
    source_load=original.get_switchable_as_dense('Load','p_set');allocated={};allocation=[]
    for name,r in original.loads.iterrows():
        bs=children[r.bus];den=sum(demands[b] for b in bs)
        for b in bs:
            share=np.divide(demands[b],den,out=np.full(8760,counts[b]/sum(counts[x] for x in bs)),where=den>0)
            allocated[name+'::'+b]=source_load[name].values*share
            physical.add('Load',name+'::'+b,bus=b)
        np.testing.assert_allclose(sum(allocated[name+'::'+b] for b in bs),source_load[name].values,atol=1e-7,rtol=1e-12)
    physical.loads_t.p_set=pd.DataFrame(allocated,index=original.snapshots)
    plants=pd.read_csv(GRID/'powerplants_s_128.csv');plant_rows=[];shapes,countries,_=boundaries()
    plants=plants[(plants.DateIn.isna()|(plants.DateIn<=2025))&(plants.DateOut.isna()|(plants.DateOut>2025))]
    for _,r in plants.iterrows():
        if r.bus not in children or not np.isfinite(r.lon+r.lat):continue
        try:z,method,distance=locate(Point(r.lon,r.lat),str(r.Country),shapes,countries)
        except ValueError:continue
        b=str(r.bus)+'::'+z
        if b in physical.buses.index:plant_rows.append(dict(bus=b,parent=r.bus,fuel=r.Fueltype,technology=r.Technology,capacity=r.Capacity))
    plantframe=pd.DataFrame(plant_rows)
    fuel={'CCGT':'Natural Gas','OCGT':'Natural Gas','coal':'Hard Coal','lignite':'Lignite','oil':'Oil','nuclear':'Nuclear','ror':'Hydro','biomass':'Bioenergy'}
    def shares(parent,carrier,hydro=False):
        bs=children[parent]
        if len(bs)==1:return {bs[0]:1.},'pure_cluster'
        q=plantframe[(plantframe.parent==parent)&(plantframe.fuel==('Hydro' if hydro else fuel.get(carrier,'')))]
        if hydro:q=q[q.technology=='Reservoir']
        if carrier=='ror':q=q[q.technology=='Run-Of-River']
        weights=q.groupby('bus').capacity.sum().reindex(bs,fill_value=0.)
        if weights.sum()>0:method='source_plant_capacity'
        else:weights=counts.reindex(bs).astype(float);method='source_member_count_proxy'
        return (weights/weights.sum()).to_dict(),method
    av=original.get_switchable_as_dense('Generator','p_max_pu');grows=[];gparents=[];gshares=[]
    for j,(name,r) in enumerate(original.generators.iterrows()):
        weights,method=shares(r.bus,r.carrier)
        for b,share in weights.items():
            if share<=0:continue
            row=r.copy();row.name=name+'::'+b;row.bus=b;row.p_nom*=share;grows.append(row);gparents.append(j);gshares.append(share)
        allocation.append(dict(component='Generator',name=name,parent=r.bus,method=method,shares=weights))
    frame=pd.DataFrame(grows);physical.add('Generator',frame.index,**{c:frame[c].values for c in frame.columns})
    physical.generators_t.p_max_pu=pd.DataFrame(av.values[:,gparents],index=physical.snapshots,columns=physical.generators.index)
    fixed={b:np.zeros(8760) for b in physical.buses.index};su=original.storage_units.query("carrier=='hydro'")
    for j,(name,r) in enumerate(su.iterrows()):
        weights,method=shares(r.bus,'hydro',True)
        for b,share in weights.items():fixed[b]+=hp[:,j]*share
        allocation.append(dict(component='FixedReservoir',name=name,parent=r.bus,method=method,shares=weights))
    fixed=pd.DataFrame(fixed,index=physical.snapshots)
    np.testing.assert_allclose(fixed.sum(axis=1),hp.sum(axis=1),atol=1e-7,rtol=1e-12)
    native_cost=old['native_cost'][:,gparents]
    # Retain the existing explicit EUR10,000 shortage offer in every new area.
    # This is diagnostic emergency supply, never counted as real fleet capacity.
    extra_emergency=[]
    for (island,zone),bs in physical.buses.groupby(['sub_network','bidding_zone']):
        names=physical.generators.index[physical.generators.bus.isin(bs.index)&(physical.generators.carrier=='emergency')]
        if len(names):continue
        name='emergency:'+str(island)+':'+zone
        physical.add('Generator',name,bus=bs.index[0],carrier='emergency',p_nom=1e6,marginal_cost=10000.)
        extra_emergency.append(dict(name=name,area=str(island)+':'+zone))
    if extra_emergency:native_cost=np.column_stack([native_cost,np.full((8760,len(extra_emergency)),10000.)])
    sources.update({str((GRID/f).relative_to(ROOT)):digest(GRID/f) for f in ['networks/base.nc','busmap_base_s.csv','busmap_base_s_128.csv','electricity_demand_base_s.nc','powerplants_s_128.csv']})
    sources[str((upstream/'scripts/simplify_network.py').relative_to(ROOT))]=digest(upstream/'scripts/simplify_network.py')
    mixed=mapping.groupby('parent').zone.nunique();mixed=mixed[mixed>1]
    metadata=dict(sources=sources,nve_summary_sha256=digest(ROOT/'data/hydro-observations-2025/nve-updated-model-v5/summary.json'),producer_sha256=digest(__file__),raw_buses=len(raw.buses),refined_buses=len(physical.buses),protected_simplification_crossings=mixed_simple,security_factor=float(factor[0]),mixed_clusters=mixed.to_dict(),zone_by_bus=zone_by_bus.to_dict(),membership=mapping.reset_index().to_dict('records'),allocation=allocation,extra_emergency=extra_emergency,limitations=['Current open geographic sources are retrospective, not certified historical 2025 boundaries.','Plant capacity allocates original aggregate offers; original weather/cost time series retained.','Mixed-cluster renewable/unsupported-fuel allocation uses raw member-bus counts, not reconstructed site capacity or zonal weather.','Original hourly parent demand is allocated by preclustered source demand; unresolved pre-simplification demand splits use member counts, not independently audited observed zonal load.','Fixed reservoir schedule split by plant capacity; original pooled water allocation and exact aggregate chronology retained.','Boundary-preserving grid is rebuilt before stub removal, so topology/ratings differ from frozen 128-bus checkpoint; original uniform security factor retained.','Model-derived N-0 limits are not JAO commercial domains. Offshore shore connection and source simplification remain proxies.','Newly separate areas retain the existing EUR10,000 emergency bid, disclosed separately from real capacity.'])
    return physical,native_cost,fixed,metadata,original,old,hp

def compile_case(n,cost,fixed,level):
    original_country=n.buses.country.copy()
    if level=='bidding_zone':n.buses.country=n.buses.bidding_zone
    elif level=='country':n.buses.country=original_country.replace({'LU':'DE'})
    else:raise ValueError('Unknown clearing geography')
    m=compile_model(n);n.buses.country=original_country
    m['load']=m['load'].copy()-fixed.T.groupby(fixed.columns.map(m['buszone'])).sum().T.reindex(columns=m['zones'],fill_value=0.).values
    off=pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
    actual_load=n.loads_t.p_set.T.groupby(n.loads.bus).sum().T.reindex(columns=n.buses.index,fill_value=0.)
    actual=fixed-actual_load
    for b in n.buses.index:
        off[b]+=actual[b]
        for target,w in m['weights'][m['buszone'][b]].items():off[target]-=w*actual[b]
    m['cost']=cost.copy();m=aggregate_offers(n,m)
    return m,off
