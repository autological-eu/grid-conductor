"""Inspect assembled static operating-cost assumptions; never alter the network.

Source direct emissions are operational fuel factors, not lifecycle intensity.
Carbon-price sensitivities are slopes, not observed 2025 allowance prices.
"""
import argparse,json,math
from pathlib import Path
from importlib.metadata import version
from monthly_dispatch import digest,save


def summarize(carriers,costs,capacities,efficiencies,emissions):
    if not (len(carriers)==len(costs)==len(capacities)==len(efficiencies)):
        raise ValueError('Matching generator attribute lengths required')
    rows=[]
    for carrier in sorted(set(carriers)):
        assets=[(float(c),float(p),float(e)) for k,c,p,e in zip(carriers,costs,capacities,efficiencies) if k==carrier]
        if any(not all(math.isfinite(v) for v in asset) or asset[1]<0 or asset[2]<=0 for asset in assets):
            raise ValueError('Finite costs, nonnegative capacity and positive efficiency required')
        active=[asset for asset in assets if asset[1]>0]
        phi=emissions.get(carrier)
        if phi is not None and (type(phi) not in (int,float) or not math.isfinite(phi) or phi<0):
            raise ValueError('Finite nonnegative source operational fuel factor required')
        intensity=[] if phi is None else [phi/asset[2] for asset in active]
        rows.append(dict(carrier=carrier,generators=len(assets),positive_capacity_generators=len(active),
            nominal_capacity_mw=math.fsum(asset[1] for asset in assets),
            static_marginal_cost_eur_mwh_min=min(a[0] for a in assets),static_marginal_cost_eur_mwh_max=max(a[0] for a in assets),
            source_direct_fuel_emissions_tco2_per_mwh_thermal=phi,
            carbon_price_slope_tco2_per_mwh_electric_min=min(intensity) if intensity else None,
            carbon_price_slope_tco2_per_mwh_electric_max=max(intensity) if intensity else None))
    return rows


def audit(path):
    import xarray as xr
    with xr.open_dataset(path) as ds:
        meta=json.loads(ds.attrs['meta'])
        required=['generators_carrier','generators_marginal_cost','generators_p_nom','generators_efficiency','carriers_co2_emissions','carriers_i']
        if any(name not in ds for name in required):raise ValueError('Assembled static cost/emissions attributes required')
        factors={str(k):float(v) for k,v in zip(ds['carriers_i'].values,ds['carriers_co2_emissions'].values)}
        rows=summarize([str(k) for k in ds['generators_carrier'].values],ds['generators_marginal_cost'].values,
            ds['generators_p_nom'].values,ds['generators_efficiency'].values,factors)
        costs=meta.get('costs',{});emission=costs.get('emission_prices',{});electricity=meta.get('electricity',{})
        cost_year=costs.get('year');enabled=emission.get('enable');carbon_price=emission.get('co2');dynamic=emission.get('dynamic')
        # Publish only these known non-secret scalar configuration fields.
        if type(cost_year) is not int or type(enabled) is not bool or type(dynamic) is not bool or type(carbon_price) not in (int,float) or not math.isfinite(carbon_price):
            raise ValueError('Explicit scalar source cost/emission-price configuration required')
        dynamic_fields=[name for name in ds.variables if name.startswith('generators_t_') and any(k in name for k in ['marginal_cost','efficiency'])]
        source=dict(cost_year=cost_year,emission_price_enabled=enabled,configured_carbon_price_eur_tco2=carbon_price,
            dynamic_emission_price_enabled=dynamic,co2_budget_enabled=electricity.get('co2limit_enable'),
            archived_powerplant_version=meta.get('data',{}).get('powerplants',{}).get('version'),
            time_varying_cost_or_efficiency_fields=dynamic_fields)
    return dict(status='prepared_cost_assumptions_audited_not_market_validation',input_sha256=digest(path),
        source_configuration=source,generators=rows,producer_sha256=digest(Path(__file__)),xarray_version=version('xarray'),
        units=dict(marginal_cost='EUR/MWh electrical output',carbon_price='EUR/tCO2',
            source_fuel_factor='tCO2/MWh thermal fuel input',carbon_price_slope='tCO2/MWh electrical output'),
        limitations=['Source emission factors are direct operational factors, not lifecycle factors or observed zonal intensities.',
            'A carbon-price slope describes a hypothetical additive operating-cost change, not an observed 2025 allowance price.',
            'Zero configured emission pricing is a material empirical limitation; it can distort fossil mix, prices and exchanges.',
            'Cost-year metadata does not establish observed hourly fuel prices, fleet completeness or outage accuracy.',
            'The source remains unchanged. Any policy-price or calibrated variant requires a separately hashed matched baseline/intervention comparison.',
            'No annual optimisation, empirical agreement or investment validity inferred.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve previous cost-assumption audit')
    result=audit(args.input);args.output.parent.mkdir(parents=True,exist_ok=True);save(args.output,result)
    config=result['source_configuration'];print(f"Prepared {config['cost_year']} cost assumptions audited; carbon pricing enabled: {config['emission_price_enabled']}. Source unchanged; no market validation.")
