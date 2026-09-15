"""Assemble a clearly labeled ex-post FR–CH experiment from ENTSO-E snapshots."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from carbon_pilot import ROOT, timestamp, iso, parse_generation, STORAGE, FACTORS
from flow_tracing import fetch, parse_quantity, hourly, charging, parse_day_ahead_prices

DOMAINS={'FR':'10YFR-RTE------C','CH':'10YCH-SWISSGRIDZ','DE':'10Y1001A1001A83F',
         'BE':'10YBE----------2','ES':'10YES-REE------0','GB':'10YGB----------A',
         'IT-NO':'10Y1001A1001A73I','AT':'10YAT-APG------L'}
NEIGHBORS={'FR':['BE','DE','GB','CH','ES','IT-NO'],'CH':['FR','DE','AT','IT-NO']}
THERMAL_COST={'B02':95,'B04':100,'B05':110,'B06':180}


def assemble(start, hours, generation, charge, loads, caps, flows, observed_eur, headroom_multiplier):
    """Build the FR–CH dispatch input from parsed ENTSO-E samples.

    Pure function: no fetching, no sqlite. `caps`/`flows` are keyed by the
    unordered/targeted pairs the pilot queries; every other series is a
    `{kind or datetime: value}` quarter-hour sample map as produced by the
    shared parsers.
    """
    stamps=[start+dt.timedelta(hours=h) for h in range(hours)]
    def series(samples,label):
        result=[hourly(samples,t) for t in stamps]
        if any(v is None for v in result):raise ValueError('Missing required hourly data: '+label)
        return result
    hourly_load={z:series(samples,z+' load') for z,samples in loads.items()}
    hourly_caps={(a,b):series(samples,a+' capacity') for (a,b),samples in caps.items()}
    hourly_flows={(a,b):series(samples,a+'>'+b) for (a,b),samples in flows.items()}
    def factor(kind):
        return None if kind not in FACTORS else FACTORS[kind][0]/1000.0
    blocks=[];fixed_imports={};audit={};observed={}
    for z in ['FR','CH']:
        fixed_imports[z]=[sum(hourly_flows[b,z][h]-hourly_flows[z,b][h] for b in NEIGHBORS[z] if b not in ['FR','CH']) for h in range(hours)]
        storage_charge=[sum(series(s,z+' charging')[h] for s in charge.get(z,{}).values()) for h in range(hours)]
        # Historical storage is fixed in this first real-data experiment, not free zero-carbon supply.
        storage_out=[sum(series(s,z+' storage discharge')[h] for k,s in generation[z].items() if k in STORAGE) for h in range(hours)]
        fixed_imports[z]=[v+d-c for v,d,c in zip(fixed_imports[z],storage_out,storage_charge)]
        actual={}
        for kind,samples in generation[z].items():
            if kind in STORAGE:continue
            values=series(samples,z+' '+kind);actual[kind]=values;observed.setdefault(z,{})[kind]=values
            if kind in THERMAL_COST and max(values)>0:
                # Explicit proxy scenario, never relabeled installed or outage-adjusted capacity.
                cap=max(v for v in samples.values() if v is not None)*headroom_multiplier
                for band,share in enumerate([.5,.3,.2]):
                    blocks.append(dict(id=z+'-'+kind+'-'+str(band),zone=z,max_mw=[cap*share]*hours,
                        cost_eur_mwh=THERMAL_COST[kind]+band*20,co2_t_per_mwh=factor(kind),
                        availability_basis='assumed_multiple_of_monthly_observed_peak'))
            elif kind=='B12':
                cap=max(v for v in samples.values() if v is not None)
                blocks.append(dict(id=z+'-'+kind,zone=z,max_mw=[cap]*hours,cost_eur_mwh=5,
                    energy_budget_mwh=sum(values),co2_t_per_mwh=factor(kind),
                    availability_basis='observed_peak_and_period_water_energy_proxy'))
            else:
                blocks.append(dict(id=z+'-'+kind,zone=z,min_mw=values,max_mw=values,cost_eur_mwh=0,
                    co2_t_per_mwh=factor(kind),availability_basis='fixed_observed_output'))
        residual=[sum(v[h] for v in actual.values())+fixed_imports[z][h]+hourly_flows[('CH' if z=='FR' else 'FR'),z][h]
            -hourly_flows[z,('CH' if z=='FR' else 'FR')][h]-hourly_load[z][h] for h in range(hours)]
        audit[z]=dict(balance_residual_mae_mw=sum(abs(v) for v in residual)/len(residual),
            balance_residual_max_mw=max(abs(v) for v in residual),generation_types=list(actual),
            generator_installed_capacity_available=False,outage_adjusted_availability_available=False)
    assumptions=[
        f'Ex-post {hours}-hour default experiment; realized demand, renewable output and external exchanges, not a day-ahead auction replay',
        f'Thermal capacity proxy = monthly observed peak × {headroom_multiplier}; not installed or outage-adjusted capacity',
        'Assumed thermal costs 95–220 EUR/MWh by fuel and efficiency band; not calibrated fuel-based bids',
        'Reservoir energy budget equals observed period production; turbine proxy equals observed monthly peak',
        'All other generation, historical storage net injection and exchanges with third countries held fixed',
        'Transmission uses published A61 day-ahead forecast capacity; not independently verified actual allocation domain',
        'Lossless two-zone transport LP, no commitment, ramping or endogenous storage in this real-data input',
        'Emission factors are IPCC AR5 lifecycle median proxies; not meter-measured operational emissions',
        'No baseline fit acceptance thresholds established: annual and climate headlines withheld']
    return dict(timestamps=[iso(t) for t in stamps],interval_hours=1,zones=['FR','CH'],load_mw=hourly_load,
        external_net_import_mw=fixed_imports,generators=blocks,storage=[],unserved_cost_eur_mwh=10000,
        edges=[dict(id='FR-CH',a='FR',b='CH',ab_mw=hourly_caps['FR','CH'],ba_mw=hourly_caps['CH','FR'])],
        observed_generation_mw=observed,observed_flow_mw={'FR-CH':hourly_flows['FR','CH']},
        observed_price_eur_mwh={z:[observed_eur.get((z,iso(t))) for t in stamps] for z in ['FR','CH']},
        emission_basis='ipcc_ar5_lifecycle_median_pilot_proxy',
        assumptions=assumptions,provenance=dict(source='ENTSO-E quantities and A44 prices; prices for diagnostics only',audit=audit))


def collect(start, hours, headroom_multiplier=1.25):
    """Fetch (cache-first) and assemble the FR–CH input for a January-free August window."""
    end=start+dt.timedelta(hours=hours)
    params=dict(periodStart='202608010000',periodEnd='202609010000')
    cache=ROOT/'data/carbon-pilot/flow-tracing/raw';provenance=[]
    def get(extra,capacity=False):
        request=dict(params,**extra);raw=fetch(request,ROOT/'data/carbon-pilot/market/raw' if capacity else cache)
        provenance.append(dict(request=request,sha256=hashlib.sha256(raw).hexdigest()))
        return raw
    generation={};charge={};loads={};caps={};flows={}
    for z in ['FR','CH']:
        raw=get(dict(documentType='A75',processType='A16',in_Domain=DOMAINS[z]))
        generation[z]=parse_generation(raw,DOMAINS[z]);charge[z]=charging(raw,DOMAINS[z])
        raw=get(dict(documentType='A65',processType='A16',outBiddingZone_Domain=DOMAINS[z]))
        loads[z]=parse_quantity(raw,{'outBiddingZone_Domain.mRID':DOMAINS[z]})
    for a,b in [('FR','CH'),('CH','FR')]:
        request=dict(documentType='A61',out_Domain=DOMAINS[a],in_Domain=DOMAINS[b]);request['contract_MarketAgreement.Type']='A01'
        raw=get(request,True)
        caps[a,b]=parse_quantity(raw,{'out_Domain.mRID':DOMAINS[a],'in_Domain.mRID':DOMAINS[b]})
    for z,neighbors in NEIGHBORS.items():
        for other in neighbors:
            for a,b in [(z,other),(other,z)]:
                if (a,b) in flows:continue
                raw=get(dict(documentType='A11',out_Domain=DOMAINS[a],in_Domain=DOMAINS[b]))
                flows[a,b]=parse_quantity(raw,{'out_Domain.mRID':DOMAINS[a],'in_Domain.mRID':DOMAINS[b]})
    obs={}
    for z in ['FR','CH']:
        request=dict(params,documentType='A44',processType='A01',in_Domain=DOMAINS[z],out_Domain=DOMAINS[z])
        raw=fetch(request,ROOT/'data/eu-market/raw')
        provenance.append(dict(request=request,sha256=hashlib.sha256(raw).hexdigest()))
        samples=parse_day_ahead_prices(raw)
        for h in range(hours):
            instant=start+dt.timedelta(hours=h)
            obs[z,iso(instant)]=hourly(samples,instant)
    data=assemble(start,hours,generation,charge,loads,caps,flows,obs,headroom_multiplier)
    data['provenance']['requests']=provenance
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',default='2026-08-10T00:00:00Z');p.add_argument('--hours',type=int,default=72)
    p.add_argument('--headroom-multiplier',type=float,default=1.25)
    p.add_argument('--output',type=Path,default=ROOT/'data/carbon-pilot/market/input.json')
    args=p.parse_args()
    if args.hours<1 or not 1<=args.headroom_multiplier<=2:p.error('Invalid hours/headroom multiplier')
    start=timestamp(args.start);end=start+dt.timedelta(hours=args.hours)
    if start.minute or start.second or start.microsecond:p.error('Start must be an hour boundary')
    if start<timestamp('2026-08-01T00:00Z') or end>timestamp('2026-09-01T00:00Z'):p.error('Pilot limited to August 2026')
    data=collect(start,args.hours,args.headroom_multiplier)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(output=str(args.output),audit=data['provenance']['audit']),indent=2))


if __name__=='__main__':main()