"""Source-hashed AC zonal PTDF experiment; zero-base N-0, not JAO capacity."""
import json
from pathlib import Path
import numpy as np
import pypsa
from synthetic_bids_2025 import SOURCE,HASH
from hourly_renewable_estimates import digest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def gsk(buses,countries,capacity,equal=False):
    zones=sorted(set(countries.loc[buses]))
    if any(not z for z in zones):raise ValueError('Missing country')
    weights=np.zeros((len(buses),len(zones)))
    for j,z in enumerate(zones):
        mask=(countries.loc[buses].values==z)
        w=mask.astype(float) if equal else np.where(mask,capacity.reindex(buses,fill_value=0).values,0)
        if not np.isfinite(w).all() or np.any(w<0) or w.sum()<=0:raise ValueError('No valid GSK capacity')
        weights[:,j]=w/w.sum()
    return zones,weights

def run():
    if digest(SOURCE)!=HASH:raise ValueError('Source hash mismatch')
    n=pypsa.Network(SOURCE);capacity=n.generators.groupby('bus').p_nom.sum();countries=n.buses.country.copy()
    original_links=len(n.links)
    n=n.copy(snapshots=n.snapshots[:1])
    for component in ['Generator','Load','StorageUnit','Store','Link','ShuntImpedance']:
        table=n.df(component)
        if len(table):n.remove(component,table.index)
    for bus in n.buses.index:n.add('Generator','probe:'+bus,bus=bus,p_nom=1e6,p_set=0)
    n.determine_network_topology();domains=[];checks=[];sens=[]
    n.generators.p_set=0.0;n.lpf()
    zero_flows={(comp,name):float(n.pnl(comp).p0.iloc[0][name]) for comp in ['Line','Transformer'] for name in n.df(comp).index}
    if zero_flows and max(abs(v) for v in zero_flows.values())>1e-8:raise ValueError('Nonzero reference flows require explicit offsets')
    for _,snrow in n.sub_networks.iterrows():
        sn=snrow.obj
        if len(sn.buses_i())<2 or snrow.carrier!='AC':continue
        sn.calculate_PTDF();buses=sn.buses_o;branches=sn.branches_i()
        zones,W=gsk(buses,countries,capacity);_,We=gsk(buses,countries,capacity,True)
        H=np.asarray(sn.PTDF);Z=H@W;Ze=H@We
        limits=[]
        for comp,name in branches:
            row=n.df(comp).loc[name];limits.append(float(row.s_nom*row.s_max_pu))
        limits=np.array(limits)
        if not np.isfinite(Z).all() or not np.isfinite(limits).all() or np.any(limits<=0):raise ValueError('Invalid physical coefficients/ratings')
        constraints=[]
        for i,(comp,name) in enumerate(branches):
            for sign in [1,-1]:constraints.append(dict(id=f'{comp}:{name}:{sign}',ptdf=dict(zip(zones,(sign*Z[i]).tolist())),ram_mw=float(limits[i])))
        domains.append(dict(island=str(sn.name),zones=zones,branches=len(branches),constraints=constraints,gsk_by_bus={z:{b:float(W[i,j]) for i,b in enumerate(buses) if W[i,j]>0} for j,z in enumerate(zones)}))
        if len(zones)<2:continue
        reference=zones.index('DE') if 'DE' in zones else zones.index('SE') if 'SE' in zones else 0
        for j in range(len(zones)):
            if j==reference:continue
            injection=100*(W[:,j]-W[:,reference]);n.generators.p_set=0.0
            for b,v in zip(buses,injection):n.generators.loc['probe:'+b,'p_set']=v
            n.lpf()
            actual=np.array([n.pnl(comp).p0.iloc[0][name] for comp,name in branches]);predicted=100*(Z[:,j]-Z[:,reference])
            error=float(abs(actual-predicted).max())
            if error>1e-6:raise ValueError('Native LPF mismatch')
            coeff=Z[:,j]-Z[:,reference];other=Ze[:,j]-Ze[:,reference]
            nz=abs(coeff)>1e-12;ne=abs(other)>1e-12
            bound=float(np.min(limits[nz]/abs(coeff[nz]))) if nz.any() else None
            equalbound=float(np.min(limits[ne]/abs(other[ne]))) if ne.any() else None
            checks.append(dict(island=str(sn.name),export_zone=zones[j],import_zone=zones[reference],transfer_mw=100,maximum_native_flow_error_mw=error,zero_base_transfer_limit_mw=bound,equal_gsk_transfer_limit_mw=equalbound))
            sens.append((zones[j]+' → '+zones[reference],bound,equalbound))
    out=ROOT/'public/research/physical-zonal-2025';out.mkdir(exist_ok=True)
    result=dict(status='verified_linear_sensitivity_experiment_not_market_domain',network_sha256=HASH,producer_sha256=digest(__file__),pypsa_version=pypsa.__version__,scope='Country aggregation separately inside each AC island',original_controllable_links_excluded=original_links,assumptions=['Static installed-generator-capacity GSK; equal-bus GSK sensitivity','Zero-injection reference; no scheduled flows','Native s_nom*s_max_pu branch active-power proxy; no additional margin','N-0 only; controllable links removed from experiment, not represented as free transfer'],domains=domains,native_lpf_checks=checks)
    (out/'constraints.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    fig,ax=plt.subplots(figsize=(11,max(4,len(sens)*.25)),layout='constrained');y=np.arange(len(sens))
    ax.barh(y-.18,[r[1]/1000 for r in sens],height=.35,label='Installed-capacity GSK');ax.barh(y+.18,[r[2]/1000 for r in sens],height=.35,label='Equal-bus GSK')
    ax.set(yticks=y,yticklabels=[r[0] for r in sens],xlabel='Zero-base N-0 transfer bound (GW)',title='Physical AC sensitivity cases — not commercial border capacities');ax.legend();fig.savefig(out/'gsk-sensitivity.svg');plt.close(fig)
    print(json.dumps(dict(islands=len(domains),branches=sum(d['branches'] for d in domains),checks=len(checks),maximum_error_mw=max(c['maximum_native_flow_error_mw'] for c in checks),excluded_links=original_links)))
if __name__=='__main__':run()
