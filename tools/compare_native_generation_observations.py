"""Compare fixed-inventory model generation with reported national quantities.

Unreconciled coverage/geographic scopes remain visible. No validation gate,
calibration, missing-category zero, partial-year annualisation or carbon factor.
"""
import argparse,json,math
from pathlib import Path
from monthly_dispatch import digest,save
from audit_2025_price_mapping import NATIONAL_ZONES

CARRIERS={'B01':['biomass'],'B02':['lignite'],'B04':['CCGT','OCGT'],'B05':['coal'],'B06':['oil'],
    'B09':['geothermal'],'B11':['ror'],'B12':['hydro-reservoir'],'B14':['nuclear'],
    'B16':['solar','solar-hsat'],'B18':['offwind-ac','offwind-dc','offwind-float'],'B19':['onwind'],'B17':['waste']}


def reported_month(row):
    if row['status']!='raw_interval_energy_replayed':return None,{}
    total=row['full_reported_primary_energy_mwh'];types={}
    if total is not None and row['complete_reported_primary_hours']!=row['expected_hours']:
        raise ValueError('Incomplete reported month cannot carry a complete total')
    for kind,data in row['by_reported_type'].items():
        types[kind]=data['reported_energy_mwh'] if data['observed_hours']==row['expected_hours'] else None
    return total,types


def compare(native,observed):
    if (native['status']!='annual_fixed_inventory_generation_accounting_diagnostic_not_validation'
            or observed['status']!='raw_generation_observations_replayed_not_model_validation'
            or native['year']!=2025 or native['hours']!=8760 or observed['year']!=2025):
        raise ValueError('Complete native year and raw-replayed 2025 reported observations required')
    bank={r['zone']:r for r in observed['zones']};rows=[]
    for country in native['countries']:
        name=country['country'];zone='DE-LU' if name=='DE' else name if name in NATIONAL_ZONES else None
        ref=bank.get(zone)
        if ref is None:
            rows.append(dict(country=name,status='no_supported_national_observation_comparison',observed_zone=None));continue
        if ref['geographic_scope']!='national area' and name!='DE':
            rows.append(dict(country=name,status='unsupported_observed_geographic_scope',observed_zone=zone));continue
        if [r['month'] for r in country['monthly']]!=list(range(1,13)) or [r['month'] for r in ref['monthly']]!=list(range(1,13)):
            raise ValueError('Ordered twelve-month evidence required')
        months=[];available=[]
        for model,observation in zip(country['monthly'],ref['monthly']):
            total,types=reported_month(observation);mix=model['primary_generation_mwh_by_model_carrier'];m=math.fsum(mix.values())
            components=[]
            for kind,carriers in CARRIERS.items():
                # Absence in either taxonomy does not establish zero output.
                value=types.get(kind)
                represented=[k for k in carriers if k in mix]
                amount=math.fsum(mix[k] for k in represented) if represented else None
                components.append(dict(observed_type=kind,model_carriers=represented,model_energy_mwh=amount,
                    reported_energy_mwh=value,difference_mwh=None if amount is None or value is None else amount-value))
            if total is not None:available.append(total)
            months.append(dict(month=model['month'],model_primary_generation_mwh=m,reported_primary_generation_mwh=total,
                difference_mwh=None if total is None else m-total,components=components,
                scope='Reported complete categories only; no independent whole-fleet/geographic/fuel-taxonomy validation.'))
        annual=math.fsum(available) if len(available)==12 else None;model_total=country['primary_generation_mwh']
        rows.append(dict(country=name,observed_zone=zone,observed_geographic_scope=ref['geographic_scope'],
            status='unreconciled_fixed_inventory_national_generation_diagnostic',
            model_primary_generation_mwh=model_total,reported_primary_generation_mwh=annual,
            difference_mwh=None if annual is None else model_total-annual,
            relative_difference=None if annual is None or annual==0 else (model_total-annual)/annual,
            complete_reported_months=len(available),monthly=months,
            germany_scope='German model country compared with German national generation proxy; Luxembourg excluded.' if name=='DE' else None))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','observed','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous empirical diagnostic')
    native=json.loads(a.native.read_text());observed=json.loads(a.observed.read_text())
    tools=Path(__file__).parent
    if native['producer_sha256']!=digest(tools/'summarize_annual_native_generation.py') or observed['producer_sha256']!=digest(tools/'audit_2025_generation_observations.py'):
        raise ValueError('Observation or native-accounting producer changed')
    for record in (native,observed):
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Observation or accounting implementation changed')
    result=dict(status='fixed_inventory_generation_observation_diagnostic_not_validation',year=2025,
        input_sha256=native['input_sha256'],native_accounting_sha256=digest(a.native),observations_audit_sha256=digest(a.observed),
        producer_sha256=digest(Path(__file__)),comparisons=compare(native,observed),
        limitations=['Not a converged annual optimum, calibration or validated market simulation.',
            'Country/model-mainland scopes and reported whole-fleet coverage remain unreconciled.',
            'Fuel mappings are provisional; absent/partial categories are not zero-filled or annualised.',
            'Pumped storage recycling is excluded from primary generation on both sides.',
            'No prices, exchanges, lifecycle factors or investment benefits validated.'])
    save(a.output,result);print('Prepared fixed-inventory generation diagnostics; no validation inferred.')
