"""Publish checked native/WASM Kirchhoff parity and measured three-trial timings."""
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'public/research/network-benchmark'
CACHE = ROOT/'data/pypsa-eur/network-benchmark'

def main():
    load = lambda path: json.loads(path.read_text())
    manifest = load(PUBLIC/'kirchhoff-manifest.json')
    assert hashlib.sha256((PUBLIC/'kirchhoff-input.json').read_bytes()).hexdigest() == manifest['input_file_sha256']
    assert hashlib.sha256((PUBLIC/'input.json').read_bytes()).hexdigest() == manifest['parent_input_file_sha256']
    bun = load(CACHE/'kirchhoff-bun-results.json')
    browser = load(CACHE/'kirchhoff-browser-results.json')
    carbon = load(CACHE/'kirchhoff-carbon-results.json')
    native = load(PUBLIC/'results.json')
    assert len(bun['trials']) == len(browser['trials']) == 3
    rows = []
    for i, ref in enumerate(native['cases']):
        br = [trial['cases'][i] for trial in browser['trials']]
        bu = [trial[i] for trial in bun['trials']]
        assert all(r['id'] == ref['id'] for r in br+bu)
        difference = max(abs(r['total_cost_eur']-ref['ac_cost_eur']) for r in br+bu)
        assert difference < .01
        assert all(r['unserved_mwh'] < 1e-6 and r['max_constraint_violation'] < 1e-5 for r in br+bu)
        rows.append(dict(id=ref['id'], native_ac_cost_eur=ref['ac_cost_eur'], native_ac_benefit_eur=ref['ac_benefit_eur'], browser_cost_eur=br[0]['total_cost_eur'], browser_median_request_ms=statistics.median(r['request_ms'] for r in br), bun_median_ms=statistics.median(r['elapsed_ms'] for r in bu), maximum_cost_difference_eur=difference))
    assert len(carbon['cases']) == 16
    assert all(abs(r['native_ac_difference_eur']) < .01 and r['max_constraint_violation'] < 1e-5 for r in carbon['cases'])
    report = dict(status='experimental_not_historically_validated', physics='Linearised lossless Kirchhoff AC network with controllable HVDC; fixed line impedance', input=manifest, period='2013-01-01 to 2013-01-08 exclusive; not 2025', runtime=browser['runtime'], timing_scope=browser['timing_scope'], trials=3, cases=rows, carbon_policy_parity=carbon)
    (PUBLIC/'kirchhoff-results.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Published seven investment cases and sixteen carbon-policy parity cases.')

if __name__ == '__main__':
    main()
