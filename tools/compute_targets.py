"""Reproducible European border screening from the archived hourly indicators."""
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics

from carbon_pilot import ROOT, iso, timestamp

VERSION = 'border-events-v1'


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values)-1)*q
    a = int(pos)
    return values[a] + (values[min(a+1,len(values)-1)]-values[a])*(pos-a)


def screen(a, b, observations, start, end, threshold=10, min_coverage=.8):
    if threshold <= 0 or not math.isfinite(threshold) or not 0 <= min_coverage <= 1:
        raise ValueError('Invalid screening settings')
    events, spreads, days = [], [], set()
    eligible = carbon_hours = estimated_hours = joint = 0
    excluded_units = set()
    directions = {a+'→'+b:dict(hours=0,carbon_hours=0,joint_hours=0,contrasts=[]),
                  b+'→'+a:dict(hours=0,carbon_hours=0,joint_hours=0,contrasts=[])}
    t = start
    while t < end:
        key = iso(t)
        pa,pb = [observations.get((z,'price',key)) for z in (a,b)]
        prices = [pa,pb]
        for p in prices:
            if p and p['unit'] != 'EUR/MWh':
                excluded_units.add(p['unit'])
        if all(p and p['value'] is not None and math.isfinite(p['value']) and p['unit']=='EUR/MWh' for p in prices):
            eligible += 1
            spread = pb['value']-pa['value']
            if abs(spread) >= threshold:
                source,target = (a,b) if spread > 0 else (b,a)
                direction = source+'→'+target
                d = directions[direction]
                d['hours'] += 1
                spreads.append(abs(spread))
                days.add(key[:10])
                ca,cb = [observations.get((z,'carbon',key)) for z in (source,target)]
                contrast = None
                if all(c and c['value'] is not None and math.isfinite(c['value']) and c['unit']=='gCO2e/kWh' for c in (ca,cb)):
                    contrast = cb['value']-ca['value']
                    carbon_hours += 1
                    d['carbon_hours'] += 1
                    estimated_hours += bool(ca['estimated'] or cb['estimated'])
                    d['contrasts'].append(contrast)
                    if contrast > 0:
                        joint += 1
                        d['joint_hours'] += 1
                if events and events[-1]['end_exclusive'] == key and events[-1]['direction'] == direction:
                    event = events[-1]
                    event['hours'] += 1
                    event['spread_sum'] += abs(spread)
                else:
                    event = dict(start=key,end_exclusive=key,hours=1,direction=direction,
                                 spread_sum=abs(spread),carbon_hours=0,joint_hours=0)
                    events.append(event)
                event['end_exclusive'] = iso(t+dt.timedelta(hours=1))
                event['carbon_hours'] += contrast is not None
                event['joint_hours'] += contrast is not None and contrast > 0
        t += dt.timedelta(hours=1)
    expected = int((end-start).total_seconds()/3600)
    for e in events:
        e['mean_spread_eur_mwh'] = e.pop('spread_sum')/e['hours']
    for d in directions.values():
        cs = d.pop('contrasts')
        d['mean_carbon_contrast'] = statistics.mean(cs) if cs else None
    return dict(expected_hours=expected,eligible_hours=eligible,coverage=eligible/expected,
        event_hours=len(spreads),event_share=len(spreads)/eligible if eligible else None,
        affected_days=len(days),mean_event_spread=statistics.mean(spreads) if spreads else None,
        p95_event_spread=percentile(spreads,.95),longest_event_hours=max((e['hours'] for e in events),default=0),
        carbon_event_hours=carbon_hours,joint_hours=joint,joint_share=joint/carbon_hours if carbon_hours else None,
        estimated_carbon_event_hours=estimated_hours,excluded_price_units=sorted(excluded_units),
        status='no_comparable_prices' if not eligible else 'low_coverage' if eligible/expected<min_coverage else 'screened',
        capacity_status='not_assessed',directions=directions,events=events)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=ROOT.parent/'data/annual/indicators.sqlite')
    p.add_argument('--graph',type=Path,default=ROOT.parent/'data/annual/graph.json')
    p.add_argument('--end',help='Exclusive UTC midnight; default latest complete archive day')
    p.add_argument('--days',type=int,default=30)
    p.add_argument('--threshold',type=float,default=10)
    p.add_argument('--min-coverage',type=float,default=.8)
    p.add_argument('--output',type=Path,default=ROOT/'public/research/targets.json')
    args=p.parse_args()
    if args.days<1:
        p.error('days must be positive')
    graph=json.loads(args.graph.read_text())
    with closing(sqlite3.connect(args.archive.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        latest=timestamp(db.execute("SELECT max(start) FROM observations WHERE metric='price'").fetchone()[0])+dt.timedelta(hours=1)
        end=timestamp(args.end) if args.end else latest.replace(hour=0,minute=0,second=0,microsecond=0)
        if end.hour or end.minute or end.second or end.microsecond:
            p.error('end must be UTC midnight')
        start=end-dt.timedelta(days=args.days)
        obs={(z,m,t):dict(value=v,unit=u,estimated=e) for z,m,t,v,u,e in db.execute(
            'SELECT zone,metric,start,value,unit,estimated FROM observations WHERE start>=? AND start<?',(iso(start),iso(end)))}
    targets=[]
    for edge in graph['connections']:
        a,b=edge['a'],edge['b']
        if a not in graph['zones'] or b not in graph['zones']:
            raise ValueError('Topology has unknown endpoint')
        targets.append(dict(id=edge['id'],a=a,b=b,name_a=graph['zones'][a]['name'],name_b=graph['zones'][b]['name'],
            topology_status=edge.get('topology_status'),operational_status=edge.get('operational_status'),
            topology_source=edge['source'],**screen(a,b,obs,start,end,args.threshold,args.min_coverage)))
    targets.sort(key=lambda r:(r['status']!='screened',-(r['event_share'] or 0),-(r['mean_event_spread'] or 0),r['id']))
    rank=0
    for r in targets:
        r['rank']=None
        if r['status']=='screened' and r['event_hours']:
            rank+=1
            r['rank']=rank
    result=dict(version=VERSION,computed_at=iso(dt.datetime.now(dt.timezone.utc)),start=iso(start),end_exclusive=iso(end),
        threshold_eur_mwh=args.threshold,min_price_coverage=args.min_coverage,zone_count=len(graph['zones']),
        topology_revision=graph['revision'],topology_sha256=hashlib.sha256(args.graph.read_bytes()).hexdigest(),
        data_source='Archived Electricity Maps hourly price and consumption lifecycle carbon; not independent ENTSO-E carbon',
        carbon_basis='consumption_lifecycle',targets=targets,
        limitations=['Topology is provider-configured, operation unverified; not every European connection is guaranteed covered',
                      'Only EUR/MWh prices compared; no implicit GBP, MDL or TRY conversion',
                      'No event-time capacity assessment, no causal congestion or avoided-emissions estimate',
                      'Independent flow-traced pilot not substituted for the archive',
                      'Carbon contrasts use archived point estimates, not uncertainty bounds'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(period=[iso(start),iso(end)],borders=len(targets),ranked=rank,
        screened=sum(r['status']=='screened' for r in targets),no_prices=sum(r['status']=='no_comparable_prices' for r in targets),
        low_coverage=sum(r['status']=='low_coverage' for r in targets),output=str(args.output)),indent=2))


if __name__=='__main__':
    main()
