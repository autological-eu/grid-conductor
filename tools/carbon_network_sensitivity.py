"""Paired carbon-price sensitivity of the archived weekly technical benchmark.

Carbon values are illustrative assumptions, not historical EU ETS observations.
"""
import copy
import hashlib
import json
from pathlib import Path
import platform
import pypsa
import scipy
import highspy
ROOT=Path(__file__).resolve().parents[1]
from run_network_benchmark import patch, transport_network, source_ac, solve
from market_model import dispatch
def main():
    raw=(ROOT/'public/research/network-benchmark/input.json').read_bytes()
    base=json.loads(raw)
    manifest=json.loads((ROOT/'public/research/network-benchmark/manifest.json').read_text())
    cases=[c for c in manifest['cases'] if c['id'] in ['baseline','swepol-plus-500','battery-PL-100-400','meshed-DE-FR-plus-500']]
    report=dict(status='experimental_sensitivity_not_historical_validation',source_input_file_sha256=hashlib.sha256(raw).hexdigest(),carbon_prices_eur_t=[0,40,80,120],hours=len(base['timestamps']),versions=dict(python=platform.python_version(),pypsa=pypsa.__version__,scipy=scipy.__version__,native_highs=highspy.Highs().version()),assumptions=['Only generator marginal cost changes: archive cost + illustrative carbon price × declared direct generation CO2 intensity. No observed ETS-price claim.','Every carbon-price setting has its own baseline and paired intervention; compare benefits within a setting.','Same archived 2013 week, fixed fleet, availability, inflows and weekly cyclic storage; no annualisation.','Carbon-inclusive objective is a modelled dispatch incentive, not a measured social cost of carbon or a complete project NPV.'],cases=[])
    cache=ROOT/'data/pypsa-eur/network-benchmark/carbon';cache.mkdir(parents=True,exist_ok=True)
    for carbon in report['carbon_prices_eur_t']:
        data=copy.deepcopy(base)
        for g in data['generators']:g['cost_eur_mwh']+=carbon*g['co2_t_per_mwh']
        for case in cases:
            d=patch(data,case)
            row=dict(carbon_price_eur_t=carbon,id=case['id'],patch=case)
            for name,run in [('scipy_transport',lambda:dispatch(d)),('pypsa_transport',lambda:solve(transport_network(d),d)),('pypsa_ac',lambda:solve(source_ac(d,case),d))]:
                result=run()
                if result['unserved_mwh']>1e-6:raise ValueError('Shortage prevents ordinary benefit interpretation')
                row[name]={k:result[k] for k in ['total_cost_eur','total_co2_t','unserved_mwh']}
                row[name]['non_carbon_operating_cost_eur']=result['total_cost_eur']-carbon*result['total_co2_t']
            if abs(row['scipy_transport']['total_cost_eur']-row['pypsa_transport']['total_cost_eur'])>.01:raise ValueError('Transport numerical parity failed')
            baseline=row if case['id']=='baseline' else next(r for r in report['cases'] if r['carbon_price_eur_t']==carbon and r['id']=='baseline')
            for name in ['scipy_transport','pypsa_transport','pypsa_ac']:
                for key,target in [('total_cost_eur','carbon_inclusive_benefit_eur'),('total_co2_t','avoided_co2_t'),('non_carbon_operating_cost_eur','non_carbon_operating_benefit_eur')]:row[name][target]=baseline[name][key]-row[name][key]
            report['cases'].append(row)
            (cache/'native-results.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)

if __name__=='__main__':
    main()
