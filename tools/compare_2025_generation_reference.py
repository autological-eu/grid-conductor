"""Compare reported national generation with a separately cached annual reference.

No bidding-zone/national substitution, annualisation or independent-validation
claim. Accounting boundaries and shared upstream sources require reconciliation.
"""
import argparse,csv,json,math
from pathlib import Path
from monthly_dispatch import digest,save

ISO3={'AL':'ALB','AT':'AUT','BE':'BEL','BG':'BGR','CH':'CHE','CZ':'CZE','DE-LU':'DEU',
    'EE':'EST','ES':'ESP','FI':'FIN','FR':'FRA','GR':'GRC','HR':'HRV','HU':'HUN','IE':'IRL',
    'LT':'LTU','LV':'LVA','MK':'MKD','NL':'NLD','PL':'POL','PT':'PRT','RO':'ROU','RS':'SRB','SI':'SVN','SK':'SVK'}


def reference(rows):
    result={}
    for row in rows:
        if (row['Year']!='2025' or row['Area type'] not in ('Country','Country or economy') or row['Category']!='Electricity generation'
                or row['Unit']!='TWh' or row['Subcategory'] not in ('Fuel','Total')):continue
        if row['Subcategory']=='Total' and row['Variable']!='Total Generation':continue
        value=float(row['Value'])
        if not math.isfinite(value) or value<0:raise ValueError('Finite nonnegative annual reference generation required')
        code=row['ISO 3 code'];entry=result.setdefault(code,dict(area=row['Area'],total_generation_twh=None,by_reported_fuel_twh={}))
        if entry['area']!=row['Area']:raise ValueError('Reference country identity differs')
        target=entry if row['Subcategory']=='Total' else entry['by_reported_fuel_twh']
        key='total_generation_twh' if row['Subcategory']=='Total' else row['Variable']
        if key in target and target[key] is not None:raise ValueError('Duplicate annual reference generation record')
        target[key]=value
    return result



def hydro_diagnostic(zone,ref):
    """Keep alternative hydro/storage boundaries visible; never correct totals."""
    months=zone.get('monthly',[])
    if len(months)!=12:return dict(status='monthly_type_inventory_unavailable')
    energy={};hours={}
    for month in months:
        if month['status']!='raw_interval_energy_replayed':return dict(status='incomplete_monthly_type_inventory')
        for kind,values in month['by_reported_type'].items():
            energy[kind]=energy.get(kind,0.)+values['reported_energy_mwh']/1e6
            hours[kind]=hours.get(kind,0)+values['observed_hours']
    present=[kind for kind in ('B11','B12') if kind in energy]
    if not present or any(hours[kind]!=8760 for kind in present):
        return dict(status='incomplete_reported_primary_hydro_not_annualised')
    primary=math.fsum(energy[kind] for kind in present)
    discharge=energy.get('B10') if hours.get('B10')==8760 else None
    reference_hydro=ref['by_reported_fuel_twh'].get('Hydro')
    return dict(status='unreconciled_hydro_storage_boundary_diagnostic',
        reported_primary_hydro_twh=primary,reported_pumped_storage_discharge_twh=discharge,
        reported_hydro_including_pumped_discharge_twh=None if discharge is None else primary+discharge,
        reference_hydro_twh=reference_hydro,
        primary_difference_twh=None if reference_hydro is None else primary-reference_hydro,
        including_discharge_difference_twh=None if reference_hydro is None or discharge is None else primary+discharge-reference_hydro,
        limitation='Pumped discharge is not new primary generation. Reference hydro/storage accounting is unreconciled; neither alternative corrects generation, carbon intensity or missing coverage.')

def compare(zones,bank):
    result=[]
    for zone in zones:
        name=zone['zone'];code=ISO3.get(name)
        if code is None or not (zone['geographic_scope']=='national area' or name=='DE-LU'):
            result.append(dict(zone=name,status='no_national_comparison_for_bidding_zone',scope=zone['geographic_scope']));continue
        ref=bank.get(code)
        if ref is None or ref['total_generation_twh'] is None:
            result.append(dict(zone=name,status='national_reference_unavailable',scope=zone['geographic_scope']));continue
        reported=zone['full_reported_primary_energy_mwh']
        complete=reported is not None and zone['complete_reported_primary_hours']==8760 and zone['verified_months']==12
        if reported is not None and not complete:raise ValueError('Incomplete observations cannot carry a full reported-year total')
        twh=reported/1e6 if complete else None
        if twh is not None and (not math.isfinite(twh) or twh<0):raise ValueError('Finite nonnegative observed annual energy required')
        total=ref['total_generation_twh']
        result.append(dict(zone=name,iso3=code,reference_area=ref['area'],scope=zone['geographic_scope'],
            status='unreconciled_national_quantity_comparison' if complete else 'incomplete_reported_generation_not_annualised',
            complete_reported_primary_hours=zone['complete_reported_primary_hours'],
            reference_generation_twh=total,reported_primary_generation_twh=twh,
            difference_twh=None if twh is None else twh-total,
            reported_to_reference_ratio=None if twh is None or total==0 else twh/total,
            reference_reported_fuels_twh=ref['by_reported_fuel_twh'],hydro_storage_diagnostic=hydro_diagnostic(zone,ref),
            accounting_scope='ENTSO-E reported primary generation excludes storage discharge; reference national generation boundary remains to be reconciled. Ratio is not a verified coverage fraction.'))
    return result


def audit(observations,provider):
    metadata_path=provider.with_suffix('.metadata.json');metadata=json.loads(metadata_path.read_text())
    if metadata['sha256']!=digest(provider):raise ValueError('Cached provider fingerprint changed')
    source=json.loads(observations.read_text())
    if source['year']!=2025 or source['status']!='raw_generation_observations_replayed_not_model_validation':
        raise ValueError('Raw-replayed 2025 observed generation inventory required')
    with provider.open(newline='') as stream:bank=reference(csv.DictReader(stream))
    if not bank:raise ValueError('No supported 2025 national generation reference records')
    return dict(status='national_reference_diagnostic_not_validation',year=2025,observations_sha256=digest(observations),
        reference_sha256=digest(provider),reference_metadata_sha256=digest(metadata_path),source_url=metadata['source_url'],
        producer_sha256=digest(Path(__file__)),comparisons=compare(source['zones'],bank),
        limitations=['National reference generation is not individual bidding-zone generation.',
            'Incomplete reported hours are not annualised; unavailable reference data remains unavailable.',
            'Net/gross generation, storage, autoproducers, reporting coverage and fuel definitions need reconciliation.',
            'The reference may share upstream observations; this is not independent measurement or model validation.',
            'No carbon factors, calibrated dispatch, coverage corrections or investment benefits inferred.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['observations','reference','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve existing national comparison')
    result=audit(args.observations,args.reference);args.output.parent.mkdir(parents=True,exist_ok=True);save(args.output,result)
    count=sum(row['status']=='unreconciled_national_quantity_comparison' for row in result['comparisons'])
    print(f'Compared {count} complete reported national quantities with cached 2025 reference; definitions unreconciled, no validation inferred.')
