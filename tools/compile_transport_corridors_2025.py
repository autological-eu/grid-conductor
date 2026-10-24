"""Model-derived corridor thermal ceilings, not commercial NTC/ATC data."""
import numpy as np
import xarray as xr
from sigmoid_month_pairs_2025 import ROOT,digest

NATIVE=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'


def compile_corridors(sealed,data):
    zones=sealed['zones'];pairs={};components=[];internal=0
    with xr.open_dataset(NATIVE) as n:
        labels=n['buses_bidding_zone'].values.astype(str)
        labels=np.where(labels=='ES-IB-MA','ES',labels)
        bus=dict(zip(n['buses_i'].values.astype(str),labels))
        if set(labels)!=set(zones):raise ValueError('Native/source bidding-zone coverage differs')
        def add(a,b,lo,hi,kind,name):
            nonlocal internal
            za,zb=bus[str(a)],bus[str(b)]
            if za==zb:internal+=1;return
            i,j=zones.index(za),zones.index(zb)
            if i>j:i,j=j,i;lo,hi=-hi,-lo
            key=(i,j)
            if key not in pairs:pairs[key]=[np.zeros(8760),np.zeros(8760)]
            pairs[key][0]+=lo;pairs[key][1]+=hi
            components.append(dict(component=kind,name=str(name),zone0=zones[i],zone1=zones[j]))
        for kind in ['lines','transformers']:
            if kind+'_i' not in n:continue
            for k,name in enumerate(n[kind+'_i'].values):
                rating=float(n[kind+'_s_nom'].values[k]*n[kind+'_s_max_pu'].values[k])/1000
                if not np.isfinite(rating) or rating<=0:raise ValueError('Invalid source thermal rating')
                add(n[kind+'_bus0'].values[k],n[kind+'_bus1'].values[k],-rating,rating,kind,name)
        if len(n['links_i'])!=data['link_min'].shape[1]:raise ValueError('Controllable link order/size mismatch')
        for field,key,default in [('p_min_pu','link_min',0.),('p_max_pu','link_max',1.)]:
            if 'links_t_'+field not in n:
                pu=n['links_'+field].values if 'links_'+field in n else np.full(len(n['links_i']),default)
                native=pu*n['links_p_nom'].values
                np.testing.assert_allclose(data[key],np.broadcast_to(native,data[key].shape),atol=1e-8,rtol=0)
        efficiency=n['links_efficiency'].values if 'links_efficiency' in n else np.ones(len(n['links_i']))
        if not np.allclose(efficiency,1,atol=0,rtol=0):raise ValueError('Lossy signed links need a separate declared formulation')
        for k,name in enumerate(n['links_i'].values):
            add(n['links_bus0'].values[k],n['links_bus1'].values[k],data['link_min'][:,k]/1000,data['link_max'][:,k]/1000,'links',name)
    edges=sorted(pairs)
    lower=np.column_stack([pairs[k][0] for k in edges]);upper=np.column_stack([pairs[k][1] for k in edges])
    if not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower>upper).any():raise ValueError('Invalid corridor limits')
    return np.array(edges),lower,upper,dict(native_sha256=digest(NATIVE),zones=zones,corridors=len(edges),cross_zone_components=components,
        internal_components_removed=internal,limit_scope='Sum of cross-zone model thermal ratings and native hourly controllable-link bounds; not verified commercial NTC/ATC. Passive loop-flow, intra-zone and AC-island coupling removed in this candidate only.')
