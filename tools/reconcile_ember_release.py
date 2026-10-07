"""Compare country/fuel/month generation across Ember CSV format versions."""
import argparse,csv,json,math
from pathlib import Path
from hourly_renewable_estimates import digest


def read_generation(path,current):
    result={}
    with path.open(newline='') as stream:
        rows=csv.DictReader(stream)
        required={'ISO 3 code','Date','Area type'} | ({'Electricity source','Is aggregated source','Generation (TWh)'} if current else {'Category','Subcategory','Variable','Unit','Value'})
        if not required.issubset(rows.fieldnames or []):raise ValueError('Unexpected Ember schema')
        for row in rows:
            if not row['Date'].startswith('2025-') or row['Area type'] not in ['Country','Country or economy']:continue
            if current:
                if row['Is aggregated source']!='False':continue
                fuel=row['Electricity source'].lower();raw=row['Generation (TWh)']
                if fuel in ['demand','net imports'] or raw=='':continue
            else:
                if row['Category']!='Electricity generation' or row['Subcategory']!='Fuel' or row['Unit']!='TWh':continue
                fuel=row['Variable'].lower();raw=row['Value']
            code=row['ISO 3 code']
            if not code:raise ValueError('Country lacks ISO identity')
            if row['Date'] not in [f'2025-{m:02d}-01' for m in range(1,13)]:raise ValueError('Unexpected monthly date')
            value=float(raw)
            if not math.isfinite(value) or value<0:raise ValueError('Invalid generation')
            key=(code,fuel,row['Date'])
            if key in result:raise ValueError('Duplicate country/fuel/month')
            result[key]=value
    return result


def compare(old,new):
    shared=set(old)&set(new);changed=[]
    for key in sorted(shared):
        delta=new[key]-old[key]
        if abs(delta)>1e-9:changed.append(dict(iso3=key[0],fuel=key[1],month=key[2],old_twh=old[key],current_twh=new[key],difference_twh=delta))
    return dict(old_records=len(old),current_records=len(new),shared_records=len(shared),unchanged_records=len(shared)-len(changed),changed_records=len(changed),
        old_only=[list(k) for k in sorted(set(old)-set(new))],current_only=[list(k) for k in sorted(set(new)-set(old))],
        max_absolute_change_twh=max([abs(r['difference_twh']) for r in changed],default=0.),changes=changed)


def run(old,new,output):
    if output.exists():raise ValueError('Preserve previous audit')
    old_receipt=json.loads((old.parent/'receipt.json').read_text());new_receipt=json.loads((new.parent/'receipt.json').read_text())
    for path,receipt in [(old,old_receipt),(new,new_receipt)]:
        if digest(path)!=receipt['sha256']:raise ValueError('Provider cache changed')
    a=read_generation(old,False);b=read_generation(new,True)
    report=compare(a,b)
    # Scope of the existing pilot: original source country/technology/month keys.
    import pycountry
    pilot=json.loads(Path('data/pypsa-eur/hourly-renewable-estimates-v1/summary.json').read_text())
    keys=set()
    for row in pilot['countries']:
        code='XKX' if row['country']=='XK' else pycountry.countries.get(alpha_2=row['country']).alpha_3
        keys.update((code,row['technology'],f'2025-{m:02d}-01') for m in range(1,13))
    report['existing_pilot_comparison']=compare({k:v for k,v in a.items() if k in keys},{k:v for k,v in b.items() if k in keys})
    report.update(status='versioned_generation_release_comparison_not_hourly_validation',old_url=old_receipt['source_url'],current_url=new_receipt['source_url'],
        old_sha256=digest(old),current_sha256=digest(new),producer_sha256=digest(__file__),
        scope='2025 national monthly nonaggregate fuel generation; no price, capacity, emissions or method equivalence inferred')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    for name,r in [('all',report),('pilot',report['existing_pilot_comparison'])]:
        print(name,{k:r[k] for k in ['old_records','current_records','shared_records','changed_records','max_absolute_change_twh']},'old_only',len(r['old_only']),'current_only',len(r['current_only']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['old','current','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();run(a.old,a.current,a.output)
