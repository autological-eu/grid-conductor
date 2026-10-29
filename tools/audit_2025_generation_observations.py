"""Re-audit cached A75/A16 generation against raw intervals, without factors.

No request, fitting, gap filling, availability inference or dispatch validation.
Only compact provenance/quantity coverage is written; raw records remain local.
"""
import argparse,calendar,datetime as dt,json,math
from pathlib import Path
from carbon_pilot import UTC,STORAGE,iso,parse_generation
from collect_map_carbon_2025 import registry
from monthly_dispatch import digest,save


def month_bounds(month):
    start=dt.datetime(2025,month,1,tzinfo=UTC)
    end=dt.datetime(2026,1,1,tzinfo=UTC) if month==12 else dt.datetime(2025,month+1,1,tzinfo=UTC)
    return start,end


def summarize(series,rows,zone,start,end):
    """Compare raw quarter-hour quantities with stored hourly MWh; preserve gaps."""
    hours=int((end-start).total_seconds()/3600)
    if len(rows)!=hours:raise ValueError('Expected exact UTC monthly hourly grid')
    primary=set(series)-STORAGE
    if not primary:raise ValueError('Reported primary generation required')
    energy={kind:[] for kind in series};counts={kind:0 for kind in series};complete=0;total=[];max_error=0.
    for index,row in enumerate(rows):
        instant=start+dt.timedelta(hours=index)
        if row['zone']!=zone or row['start']!=iso(instant) or row['reported_types']!=sorted(series):
            raise ValueError('Zone, reported categories or exact hourly identity differs')
        observed={};missing=[]
        for kind,samples in series.items():
            values=[samples.get(instant+dt.timedelta(minutes=15*i)) for i in range(4)]
            if any(v is None for v in values):missing.append(kind);continue
            if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):
                raise ValueError('Finite nonnegative raw production required')
            observed[kind]=math.fsum(values)*.25
            counts[kind]+=1;energy[kind].append(observed[kind])
        if set(row['generation_mwh_by_type'])!=set(observed) or set(row['missing_types'])!=set(missing):
            raise ValueError('Stored energy/missing categories differ from raw intervals')
        for kind,value in observed.items():
            saved=row['generation_mwh_by_type'][kind]
            if type(saved) not in (int,float) or not math.isfinite(saved) or saved<0:
                raise ValueError('Invalid stored generation energy')
            error=abs(saved-value);max_error=max(max_error,error)
            if error>1e-7:raise ValueError('Stored hourly energy differs from raw MW interval integral')
        expected=None if set(missing)&primary else math.fsum(observed[kind] for kind in primary)
        stored=row['primary_generation_mwh']
        if expected is None:
            if stored is not None:raise ValueError('Missing raw generation cannot have a complete hourly total')
        else:
            if type(stored) not in (int,float) or not math.isfinite(stored) or abs(stored-expected)>1e-7:
                raise ValueError('Stored primary generation total differs')
            complete+=1;total.append(expected)
    quantities={kind:dict(observed_hours=counts[kind],missing_hours=hours-counts[kind],
        reported_energy_mwh=math.fsum(energy[kind]),role='storage discharge' if kind in STORAGE else 'primary generation') for kind in sorted(series)}
    return dict(expected_hours=hours,complete_reported_primary_hours=complete,missing_primary_hours=hours-complete,
        complete_hour_primary_energy_mwh=math.fsum(total),
        full_reported_primary_energy_mwh=math.fsum(total) if complete==hours else None,
        max_raw_to_hourly_energy_difference_mwh=max_error,by_reported_type=quantities)


def audit(folder,raw_folder):
    areas=registry();results=[]
    for zone,area in sorted(areas.items()):
        months=[]
        for month in range(1,13):
            start,end=month_bounds(month);path=folder/zone/f'{month:02d}.json';receipt_path=folder/zone/f'{month:02d}.receipt.json'
            if not path.exists() or not receipt_path.exists():
                months.append(dict(month=month,status='unavailable_not_zero',expected_hours=calendar.monthrange(2025,month)[1]*24));continue
            receipt=json.loads(receipt_path.read_text());source=receipt['source']
            expected=dict(documentType='A75',processType='A16',in_Domain=area['eic'],
                periodStart=start.strftime('%Y%m%d%H%M'),periodEnd=end.strftime('%Y%m%d%H%M'))
            label={'DK1':'DK-DK1','DK2':'DK-DK2'}.get(zone,zone)
            raw=raw_folder/f'{label}-{start:%Y%m%d}-{end:%Y%m%d}.xml';metadata_path=raw.with_suffix('.metadata.json')
            metadata=json.loads(metadata_path.read_text())
            if (receipt['zone']!=zone or receipt['month']!=month or receipt['eic']!=area['eic']
                    or receipt['geographic_scope']!=area['scope'] or receipt['sha256']!=digest(path)
                    or source['request']!=expected or metadata['request']!=expected
                    or source['sha256']!=digest(raw) or metadata['sha256']!=source['sha256']):
                raise ValueError('Generation raw/processed source and geographic fingerprints differ')
            quantities=summarize(parse_generation(raw.read_bytes(),area['eic']),json.loads(path.read_text()),zone,start,end)
            if quantities['complete_reported_primary_hours']!=receipt['complete_hours']:
                raise ValueError('Declared complete generation coverage differs')
            months.append(dict(month=month,status='raw_interval_energy_replayed',eic=area['eic'],raw_sha256=digest(raw),
                raw_metadata_sha256=digest(metadata_path),processed_sha256=digest(path),receipt_sha256=digest(receipt_path),**quantities))
        available=[m for m in months if m['status']=='raw_interval_energy_replayed']
        complete=sum(m['complete_reported_primary_hours'] for m in available)
        results.append(dict(zone=zone,eic=area['eic'],geographic_scope=area['scope'],verified_months=len(available),
            expected_hours=8760,complete_reported_primary_hours=complete,missing_or_unavailable_hours=8760-complete,
            complete_hour_primary_energy_mwh=math.fsum(m['complete_hour_primary_energy_mwh'] for m in available),
            full_reported_primary_energy_mwh=math.fsum(m['complete_hour_primary_energy_mwh'] for m in available) if complete==8760 else None,
            monthly=months))
    tools=Path(__file__).parent
    return dict(status='raw_generation_observations_replayed_not_model_validation',year=2025,zones=results,
        verified_area_months=sum(r['verified_months'] for r in results),expected_area_months=12*len(results),
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['carbon_pilot.py','collect_map_carbon_2025.py','eu_zones.py']},
        unit='MWh',scope='Observed reported primary generation; storage discharge separate. No carbon factors or renewable availability inference.',
        limitations=['Completeness means all categories present in the source month; it does not prove whole-fleet coverage.',
            'Missing type-hours and unreported categories are not zero-filled; sums are labelled by their observed coverage.',
            'National generation proxies retain their geographic labels; Germany excludes Luxembourg.',
            'This replays cached raw interval integrals, not independent national energy totals.',
            'No dispatch comparison, fitted costs, acceptance thresholds, lifecycle intensity or avoided emissions inferred.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['generation','raw','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve previous observations audit')
    result=audit(args.generation,args.raw);args.output.parent.mkdir(parents=True,exist_ok=True);save(args.output,result)
    print(f"Raw generation intervals replayed for {result['verified_area_months']}/{result['expected_area_months']} area-months; not model validation.")
