"""Assemble N-zone EU dispatch input from a collected bank for the market model.

Reuses the FR–CH pilot methodology (public/research/market-model-pilot.md,
tools/build_market_pilot.py): realized demand, renewables and external exchanges
held fixed; thermal capacity = monthly observed peak x headroom with assumed
cost bands; reservoir energy budget = observed period production; storage net
injection fixed. Transmission caps come from the bank: published A61 where
available; absent directions block assembly. Lossless LP,
no commitment/ramping, unserved cost fixed high.

Bank series are quarter-hour arrays (None = missing); missing quarters fail
loudly (missing != 0) and each hour is the mean of its four quarters.
"""
import argparse, datetime as dt, json
from pathlib import Path
from carbon_pilot import ROOT, iso, FACTORS

THERMAL_COST={'B02':95,'B03':100,'B04':110,'B05':180,'B06':90}
STORAGE_OUT={'B10','B25'}           # dispatchable storage output held fixed (pumped turbines)
STORAGE_CHARGE={'B10','B25'}  # storage charging via consumption documents
UNSERVED_EUR_MWH=10000
MAX_NONSTORAGE_FILL_HOURS=48


def factor(kind):
    return None if kind not in FACTORS else FACTORS[kind][0]/1000.0


def read_bank(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data,list):data=data[0]
    return data


def to_hourly(quarter_values, hours, label, max_gap_hours=0):
    """Only complete hours are observations. Never interpolate or zero-fill."""
    import math
    if len(quarter_values)!=hours*4:raise ValueError(f'Bad length for {label}')
    out=[]
    for h in range(hours):
        vals=quarter_values[h*4:h*4+4]
        if any(v is not None and not math.isfinite(v) for v in vals):
            raise ValueError(f'Nonfinite value for {label}')
        out.append(sum(vals)/4 if all(v is not None for v in vals) else None)
    return out


def require_complete(values, label):
    if any(v is None for v in values):raise ValueError(f'Missing observations: {label}')
    return values


def interior_borders(bank):
    return [tuple(b[0:2]) for b in bank.get('interior_borders',[])]


def assemble(bank, headroom_multiplier=1.25):
    from audit_eu_market import audit_bank
    quality=audit_bank(bank)
    if not quality['input_gate_passed']:
        raise ValueError('EU input gate failed; inspect eu-input-quality.json before solving')
    zones=sorted(bank['zones'])
    gen=bank.get('generation_mw',{})
    charge=bank.get('storage_charge_mw',{})
    caps=bank['caps_mw']
    flows=bank['flows_mw']
    prices=bank.get('prices',{})
    edges=interior_borders(bank)
    quarter_count=len(bank['load_mw'][zones[0]])
    hour_count=quarter_count//4
    month=dt.datetime.strptime(bank['month'],'%Y-%m').replace(tzinfo=dt.timezone.utc)
    stamps=[month+dt.timedelta(hours=h) for h in range(hour_count)]

    raw_load={z:to_hourly(bank['load_mw'][z],hour_count,z+' load') for z in zones}
    hours=hour_count
    hourly_load={z:raw_load[z][:hours] for z in zones}
    def hourly_series(name):
        return to_hourly(flows[name],hour_count,name)[:hours]
    def net_internal_in(z):
        out=[0.0]*hours
        for a,b in edges:
            for exporter,importer in [(a,b),(b,a)]:
                key=exporter+'>'+importer
                if key not in flows:continue
                hser=hourly_series(key)
                if exporter==z:
                    out=[o-v for o,v in zip(out,hser)]
                elif importer==z:
                    out=[o+v for o,v in zip(out,hser)]
        return out
    ext_net={z:[0.0]*hours for z in zones}
    for key,series in flows.items():
        a,b=key.split('>')
        if a in zones and b in zones:continue
        z=a if a in zones else b
        if z not in zones:continue
        hser=to_hourly(series,hour_count,key)[:hours]
        if a==z:
            ext_net[z]=[v-s for v,s in zip(ext_net[z],hser)]
        else:
            ext_net[z]=[v+s for v,s in zip(ext_net[z],hser)]

    blocks=[];observed={};audit={};fills={};storage_net={}
    for z in zones:
        storage_charge={k:require_complete(to_hourly(s,hour_count,z+' '+k+' charge')[:hours],z+' charge')
                        for k,s in charge.get(z,{}).items() if k in STORAGE_CHARGE}
        storage_out={k:require_complete(to_hourly(s,hour_count,z+' '+k+' storage out')[:hours],z+' storage out')
                     for k,s in gen.get(z,{}).items() if k in STORAGE_OUT}
        sc=[sum(storage_charge[k][h] for k in storage_charge) for h in range(hours)]
        so=[sum(storage_out[k][h] for k in storage_out) for h in range(hours)]
        storage_net[z]=[o-c for o,c in zip(so,sc)]
        actual={}
        for kind,samples in gen.get(z,{}).items():
            if kind in STORAGE_OUT:continue
            hser=to_hourly(samples,hour_count,z+' '+kind)[:hours]
            none_before=sum(1 for v in hser if v is None)
            if none_before:
                hser=require_complete(hser,z+' '+kind)
                fills.setdefault(z,{})[kind]=none_before
            actual[kind]=hser
            observed.setdefault(z,{})[kind]=hser
            if kind in THERMAL_COST and max(hser)>0:
                cap=max(v for v in samples if v is not None)*headroom_multiplier
                for band,share in enumerate([.5,.3,.2]):
                    blocks.append(dict(id=f'{z}-{kind}-{band}',zone=z,max_mw=[cap*share]*hours,
                        cost_eur_mwh=THERMAL_COST[kind]+band*20,co2_t_per_mwh=factor(kind),
                        availability_basis='assumed_multiple_of_monthly_observed_peak'))
            elif kind=='B12':
                cap=max(v for v in samples if v is not None)
                blocks.append(dict(id=f'{z}-B12',zone=z,min_mw=[0.0]*hours,max_mw=[cap]*hours,
                    cost_eur_mwh=5,energy_budget_mwh=sum(hser),co2_t_per_mwh=factor(kind),
                    availability_basis='observed_peak_and_period_water_energy_proxy'))
            else:
                blocks.append(dict(id=f'{z}-{kind}',zone=z,min_mw=hser,max_mw=hser,cost_eur_mwh=0,
                    co2_t_per_mwh=factor(kind),availability_basis='fixed_observed_output'))
        net_mid=net_internal_in(z)
        residual=[sum(v[h] for v in actual.values())+ext_net[z][h]+net_mid[h]+so[h]-sc[h]-hourly_load[z][h]
                  for h in range(hours)]
        audit[z]=dict(balance_residual_mae_mw=sum(abs(v) for v in residual)/len(residual),
            balance_residual_max_mw=max(abs(v) for v in residual) if residual else 0,
            generation_types=list(actual),
            interpolated_generation_hours=fills.get(z,{}),
            window_truncated_hours=hour_count-hours,
            generator_installed_capacity_available=False,outage_adjusted_availability_available=False)

    edge_rows=[]
    for a,b in edges:
        k_ab,k_ba=f'{a}>{b}',f'{b}>{a}'
        ab_list=caps[k_ab]
        ba_list=caps[k_ba]
        edge_rows.append(dict(id=a+'-'+b,a=a,b=b,
            ab_mw=to_hourly(ab_list,hour_count,k_ab)[:hours],
            ba_mw=to_hourly(ba_list,hour_count,k_ba)[:hours]))
    observed_flow={}
    for k,v in flows.items():
        a,b=k.split('>')
        if a in zones and b in zones:
            observed_flow[k]=to_hourly(v,hour_count,k)[:hours]
    observed_price={}
    for z in zones:
        if z not in prices:continue
        observed_price[z]=to_hourly(prices[z],hour_count,z+' price')[:hours]
    synthetic=set(bank.get('caps_synthetic',[]))
    assumptions=[
        f'Ex-post EU-wide {hours}-hour experiment; realized demand, renewables and exchanges, not an auction replay',
        f'Thermal capacity proxy = monthly observed peak x {headroom_multiplier}; not installed or outage-adjusted',
        'Assumed thermal costs 95-240 EUR/MWh by fuel and efficiency band; not calibrated fuel-based bids',
        'Reservoir energy budget equals observed period production; turbine proxy equals observed monthly peak',
        'All non-thermal generation and historical storage net injection held fixed',
        'Caps: published A61 via ENTSO-E where available; no synthetic fallback; not a full flow-based constraint model',
        'Lossless ATC transport LP across bidding zones, no commitment, ramping or endogenous storage',
        'Emission factors are IPCC AR5 lifecycle median proxies; assumption pricing withheld until validated',
        'No baseline fit acceptance thresholds established: headlines withheld']
    return dict(timestamps=[iso(t) for t in stamps],interval_hours=1,zones=sorted(zones),load_mw=hourly_load,
        external_net_import_mw={z:[v+s for v,s in zip(ext_net[z],storage_net[z])] for z in zones},generators=blocks,storage=[],
        unserved_cost_eur_mwh=UNSERVED_EUR_MWH,
        edges=edge_rows,
        observed_generation_mw=observed,observed_flow_mw=observed_flow,
        observed_price_eur_mwh=observed_price,
        emission_basis='ipcc_ar5_lifecycle_median_pilot_proxy',
        assumptions=assumptions,
        provenance=dict(source='bank: A44/A75/A65/A11/A61',
            caps_real=len([k for k in caps if k not in synthetic]),
            caps_synthetic=sorted(synthetic),audit=audit))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank',type=Path,default=ROOT/'data/eu-market/bank-2026-08.json')
    p.add_argument('--headroom-multiplier',type=float,default=1.25)
    p.add_argument('--output',type=Path,default=ROOT/'data/eu-market/input.json')
    args=p.parse_args()
    data=assemble(read_bank(args.bank),args.headroom_multiplier)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,allow_nan=False),encoding='utf-8')
    audit=data['provenance']['audit']
    print(json.dumps(dict(output=str(args.output),zones=len(data['zones']),edges=len(data['edges']),
        generators=len(data['generators']),
        priced_zones=sum(z in data['observed_price_eur_mwh'] for z in data['zones']),
        balance_mae_mw=round(max(a['balance_residual_mae_mw'] for a in audit.values()),1),
        audit=audit),indent=2,ensure_ascii=False))


if __name__=='__main__':main()