"""Compare the retained annual dispatch, not renewable availability, with quantities."""
import argparse
import fcntl
import json
import logging
import resource
import signal
import sys
import time
from pathlib import Path
import numpy as np

from generation_mix_2025 import ROOT, FAMILIES, CARRIER, EMBER, MONTH, digest, allocate, quantity_metrics, ember_rows, observations
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from audit_nve_hydro_diagnostics_2025 import physics
from audit_2025_generation_observations import audit as generation_audit
from compare_native_exchange_reference import CODES


def run(out):
    started = time.perf_counter()
    design = dict(year=2025, scope='All source countries in annual-v7; annual/monthly Ember and matched-hour ENTSO-E PSR diagnostics',
        allocation='Identical annual bid/zone offers retain saved aggregate output. Availability-proportional point is illustrative; individual-label min/max ranges retain all tie freedom, not jointly attainable bounds.',
        missing='Unreported types/hours and missing constituent zones remain unknown. Full-year totals need 12 months or 8760 known hours; no partial annualisation.',
        trade='Generation minus prepared demand gives implied signed net exports, not independently measured branch/bilateral flows; source-country allocation within shared commercial zones is conditional.',
        taxonomy='Hydro excludes modeled pumped discharge; observed B10/B25 separate. Ember Hydro/storage, Bioenergy/biogenic waste and Other fossil/fossil waste boundaries remain proxies.',
        flags='Outside tie range >1 MW hourly, >0.001 TWh monthly and >0.01 TWh annually are diagnostic rounding guards, not acceptance thresholds.',
        unchanged='No new solve, dispatch fit, hydro flexibility, changed availability or accepted baseline')
    (out/'design.json').write_text(json.dumps(design, indent=2)+'\n')
    base = ROOT/'data/bidding-zone-network-2025/annual-v7'
    s = json.loads((base/'summary.json').read_text()); prior = json.loads((base/'audit.json').read_text())
    assert digest(base/'annual.npz') == s['witness_sha256']
    assert prior['source_summary_sha256'] == digest(base/'summary.json')
    for name, sha in s['dependencies'].items(): assert digest(ROOT/'tools'/name) == sha
    sources = {str((base/name).relative_to(ROOT)):digest(base/name) for name in ['summary.json','annual.npz','audit.json','mapping.json']}
    ember = ROOT/'data/pypsa-eur/ember-current-release/monthly.csv'
    receipt = json.loads((ember.parent/'receipt.json').read_text()); assert digest(ember) == receipt['sha256']
    for p in [ember, ember.parent/'receipt.json']: sources[str(p.relative_to(ROOT))] = digest(p)
    bank = ember_rows(ember)
    print('Fresh raw ENTSO-E generation replay', flush=True)
    replay = generation_audit(ROOT/'data/carbon-pilot/map-2025', ROOT/'data/carbon-pilot/entsoe/raw')
    (out/'observations-replay.json').write_text(json.dumps(replay,indent=2)+'\n')
    print('Rebuilding unchanged fleet and grouped dispatch', flush=True)
    n, cost, fixed, mapping, original, old, hp = build()
    assert mapping == json.loads((base/'mapping.json').read_text())
    m, off = compile_global(n, cost, fixed, 'bidding_zone')
    countries = sorted(n.buses.country.unique()); keys = [(c,f) for c in countries for f in FAMILIES]
    groups = {}; generator_keys = []
    for j, (_, g) in enumerate(n.generators.iterrows()):
        key = (m['buszone'][g.bus], cost[:,j].tobytes(), g.carrier=='emergency')
        groups.setdefault(key, []).append(j)
        generator_keys.append((n.buses.loc[g.bus,'country'], CARRIER[g.carrier]))
    ids = list(groups.values()); assert len(ids) == m['ng']
    av = n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    for k, members in enumerate(ids):
        np.testing.assert_allclose(av[:,members].sum(axis=1),m['availability'][:,k],atol=1e-7,rtol=1e-12)
        np.testing.assert_array_equal(cost[:,members[0]],m['cost'][:,k])
    with np.load(base/'annual.npz') as a:
        assert a['bidding_zone_optimal'].all()
        values = a['bidding_zone_values']
        primal = physics(n,m,values,m['load'],off.reset_index(drop=True).copy(),0)
        point, lower, upper, caps = allocate(av,values[:,:m['ng']],ids,generator_keys,keys)
        # Country/fuel bounds must aggregate capacities BEFORE bounding, not sum marginal label bounds.
        country_point, country_lower, country_upper, _ = allocate(av,values[:,:m['ng']],ids,[c if f!='emergency' else None for c,f in generator_keys],countries)
        ekeys = [(c,fuel) for c in countries for fuel in EMBER]
        fmap = {family:fuel for fuel, families in EMBER.items() for family in families}
        # Emergency has zero actual dispatch and is never counted as real generation.
        assert abs(point[:,[j for j,k in enumerate(keys) if k[1]=='emergency']]).max() < 1e-5
        ep, el, eu, _ = allocate(av,values[:,:m['ng']],ids,[(c,fmap[f]) if f!='emergency' else None for c,f in generator_keys],ekeys)
        shape = (8760,len(countries),len(FAMILIES))
        point, lower, upper, caps = [v.reshape(shape) for v in [point,lower,upper,caps]]
        ep, el, eu = [v.reshape(8760,len(countries),len(EMBER)) for v in [ep,el,eu]]
        demand = np.zeros((8760,len(countries))); reservoir = np.zeros_like(demand)
        for j,c in enumerate(countries):
            buses = n.buses.index[n.buses.country==c]
            reservoir[:,j] = fixed[buses].sum(axis=1)
            loads = n.loads.index[n.loads.bus.isin(buses)]
            demand[:,j] = n.get_switchable_as_dense('Load','p_set')[loads].sum(axis=1)
        h = FAMILIES.index('reservoir'); eh = list(EMBER).index('Hydro')
        for v in [point,lower,upper]: v[:,:,h] += reservoir
        for v in [ep,el,eu]: v[:,:,eh] += reservoir
        for v in [country_point,country_lower,country_upper]: v += reservoir
        # Global accounting closes against controllable-link losses; no storage reset or double counting.
        flows = values[:,m['ng']:m['ng']+m['nl']]
        losses = flows @ (1-n.links.efficiency.to_numpy())
        closure = float(abs(country_point.sum(axis=1)-demand.sum(axis=1)-losses).max())
        assert closure < 1e-4
    country_areas = {}
    known = {r['zone']:r for r in replay['zones']}
    labels = n.buses.bidding_zone.replace({'ES-IB-MA':'ES'})
    for c in countries:
        if c=='DE': areas=['DE-LU']  # Explicit Germany national A75 domain, not DE-LU prices.
        elif c=='LU': areas=[]  # Germany's national A75 domain must never become Luxembourg data.
        elif c in known and known[c]['geographic_scope']=='national area': areas=[c]
        else: areas=sorted(set(labels[n.buses.country==c]))
        country_areas[c]=areas
    observed, coverage = observations(replay,country_areas,sources)
    hourly = []; annual = []; mix = []; energy = []
    for j,c in enumerate(countries):
        for k,f in enumerate(FAMILIES[:-1]):
            ref = observed[:,j,k]
            hourly.append(dict(country=c,technology=f,year=quantity_metrics(point[:,j,k],ref,lower[:,j,k],upper[:,j,k]),
                monthly=[dict(month=month,**quantity_metrics(point[MONTH==month,j,k],ref[MONTH==month],lower[MONTH==month,j,k],upper[MONTH==month,j,k])) for month in range(1,13)]))
        hourly.append(dict(country=c,technology='reported_primary_total',year=quantity_metrics(country_point[:,j],observed[:,j,-3],country_lower[:,j],country_upper[:,j]),
            monthly=[dict(month=month,**quantity_metrics(country_point[MONTH==month,j],observed[MONTH==month,j,-3],country_lower[MONTH==month,j],country_upper[MONTH==month,j])) for month in range(1,13)]))
        code = CODES.get(c); total = [bank.get((code,'Total generation',month)) for month in range(1,13)]
        ref_total = sum(total) if all(v is not None for v in total) else None
        model_total = float(country_point[:,j].sum()/1e6)
        for k,fuel in enumerate(EMBER):
            monthly = []
            for month in range(1,13):
                mask = MONTH==month; ref = bank.get((code,fuel,month))
                p,lo,hi = [float(v[mask,j,k].sum()/1e6) for v in [ep,el,eu]]
                monthly.append(dict(month=month,model_twh=p,lower_twh=lo,upper_twh=hi,ember_twh=ref,
                    difference_twh=None if ref is None else p-ref,
                    outside_range_twh=None if ref is None else max(lo-ref,ref-hi,0.)))
            complete=all(r['ember_twh'] is not None for r in monthly)
            ref=sum(r['ember_twh'] for r in monthly) if complete else None
            p,lo,hi = [float(v[:,j,k].sum()/1e6) for v in [ep,el,eu]]
            annual.append(dict(country=c,technology=fuel,reference_months=sum(r['ember_twh'] is not None for r in monthly),
                model_twh=p,lower_twh=lo,upper_twh=hi,ember_twh=ref,difference_twh=None if ref is None else p-ref,
                outside_range_twh=None if ref is None else max(lo-ref,ref-hi,0.),
                model_share_pct=100*p/model_total if model_total>0 else None,
                ember_share_pct=100*ref/ref_total if ref is not None and ref_total and ref_total>0 else None,monthly=monthly))
        mix.append(dict(country=c,model_total_twh=model_total,lower_twh=float(country_lower[:,j].sum()/1e6),upper_twh=float(country_upper[:,j].sum()/1e6),
            ember_total_twh=ref_total,reference_months=sum(v is not None for v in total),difference_twh=None if ref_total is None else model_total-ref_total))
        monthly=[]
        for month in range(1,13):
            mask=MONTH==month; d=float(demand[mask,j].sum()/1e6); g=float(country_point[mask,j].sum()/1e6)
            imp=bank.get((code,'Net imports',month)); refd=bank.get((code,'Demand',month))
            monthly.append(dict(month=month,model_demand_twh=d,ember_demand_twh=refd,model_implied_net_export_twh=g-d,
                lower_net_export_twh=float(country_lower[mask,j].sum()/1e6)-d,upper_net_export_twh=float(country_upper[mask,j].sum()/1e6)-d,
                ember_net_export_twh=None if imp is None else -imp))
        full=lambda key:sum(r[key] for r in monthly) if all(r[key] is not None for r in monthly) else None
        energy.append(dict(country=c,model_demand_twh=full('model_demand_twh'),ember_demand_twh=full('ember_demand_twh'),
            model_implied_net_export_twh=full('model_implied_net_export_twh'),ember_net_export_twh=full('ember_net_export_twh'),
            lower_net_export_twh=full('lower_net_export_twh'),upper_net_export_twh=full('upper_net_export_twh'),monthly=monthly))
    np.savez_compressed(out/'quantities.npz',countries=np.array(countries),families=np.array(FAMILIES),ember_types=np.array(list(EMBER)),
        point=point,lower=lower,upper=upper,available=caps,ember_point=ep,ember_lower=el,ember_upper=eu,
        country_point=country_point,country_lower=country_lower,country_upper=country_upper,demand=demand,fixed_reservoir=reservoir,observed=observed)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    result=dict(status='dispatch_generation_mix_diagnostic_not_fitted_or_accepted',countries=countries,design=design,
        hourly=hourly,annual=annual,country_totals=mix,energy=energy,observation_coverage=coverage,
        storage_observed=[dict(country=c,pumped_discharge_known_hours=int(np.isfinite(observed[:,j,-2]).sum()),battery_discharge_known_hours=int(np.isfinite(observed[:,j,-1]).sum()),
            pumped_discharge_on_known_hours_twh=float(np.nansum(observed[:,j,-2])/1e6) if np.isfinite(observed[:,j,-2]).any() else None) for j,c in enumerate(countries)],
        maximum_network_residual_mw=primal,maximum_global_energy_closure_mw=closure,
        source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/generation_mix_2025.py'),
        observations_replay_sha256=digest(out/'observations-replay.json'),design_sha256=digest(out/'design.json'),witness_sha256=digest(out/'quantities.npz'),
        elapsed_seconds=time.perf_counter()-started,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Completed dispatch mix for',len(countries),'countries',round(result['elapsed_seconds'],2),'seconds',flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1500);run(a.out)
