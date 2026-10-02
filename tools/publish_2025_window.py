"""Gate and publish conditional 2025 comparisons, never annualise window benefits."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def publish(folder):
 native=json.loads((folder/'native-cases.json').read_text());fast=json.loads((folder/'fast-cases.json').read_text());cases=json.loads((folder/'cases.json').read_text());raw=(folder/'input.json').read_bytes();rows=[]
 if [a['id'] for a in native]!=[a['id'] for a in fast] or len(native)!=3:raise ValueError('Incomplete cases')
 for a,b in zip(native,fast):
  delta=b['cost_eur']-a['cost_eur']
  if abs(delta)>.01 or a['shortage_mwh']>1e-6 or b['shortage_mwh']>1e-6 or b['max_constraint_violation']>1e-5:raise ValueError(('Parity/feasibility gate failed',a,b))
  rows.append(dict(id=a['id'],native_cost_eur=a['cost_eur'],fast_cost_eur=b['cost_eur'],difference_eur=delta,native_benefit_eur=native[0]['cost_eur']-a['cost_eur'],fast_benefit_eur=fast[0]['cost_eur']-b['cost_eur'],native_seconds=a['elapsed_seconds'],fast_seconds=b['elapsed_seconds']))
 out=ROOT/'public/research/network-benchmark-2025';out.mkdir(exist_ok=True)
 report=dict(status='conditional_window_objective_parity_passed_not_annual_validation',hours=48,year=2025,input_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,results=rows,limitations=['Fixed January reference terminal inventories; not annual optimum or annual investment valuation.','2024 nuclear availability proxy; no historical calibration.','Both solvers include nodal disposal and shortage diagnostics. Disposal can affect conditional-window economics.','Single trials ran with concurrent jobs; not a controlled speed benchmark. Native IPM uses two threads; WASM uses its default solver.','Equal objectives do not require identical dispatch for degenerate solutions.'])
 (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copyfile(folder/'input.json',out/'input.json')
 table='\n'.join(f"| {a['id']} | {a['native_benefit_eur']:,.2f} | {a['fast_benefit_eur']:,.2f} | {a['difference_eur']:.6f} |" for a in rows)
 doc=f'''# 2025 conditional network benchmark

This experiment compares native PyPSA and the browser-compatible Kirchhoff solver on the same 128-node network for **1–2 January 2025 (48 hours)**. It is separate from the existing 2013 weekly benchmark. It does not estimate annual investment value.

## Matched inputs and boundaries

Both use the prepared 2025 fleet, demand, renewable availability, reservoir inflows, efficiencies, lossless AC Kirchhoff constraints and directional HVDC limits. Generation dispatch is never substituted for renewable availability. Storage starts at the original initial inventories and ends at inventories taken from the sequential January reference run. These fixed boundaries condition the result; they do not optimise seasonal water value. Nuclear availability uses a declared 2024 country proxy.

## Why the first comparison failed

The first native run omitted nodal disposal variables that the fast solver includes. Its objective was €41,933 higher. Adding identical nonnegative shortage and disposal variables to the native model removed that model mismatch. Tightening native IPM tolerances reduced numerical differences below one cent. Disposal is free; shortage costs €10,000/MWh. All three cases pass a shortage gate of 10⁻⁶ MWh. Disposal is a diagnostic modelling choice and can change conditional-window economics; it must not be hidden in an investment claim.

For each case, gross operating-cost benefit is

$$B = C_{{baseline}} - C_{{intervention}}.$$

This excludes capital cost and is a 48-hour benefit, not an annual estimate. The cable case adds 500 MW to the existing Sweden–Poland model link. The battery adds 100 MW / 400 MWh at its Polish endpoint, with 95% charging and discharging efficiencies and empty initial and terminal inventory.

| Case | Native benefit (€ / window) | Fast benefit (€ / window) | Fast − native cost (€) |
| --- | ---: | ---: | ---: |
{table}

## What has and has not passed

All three objectives agree within €0.01. Fast solver constraint residuals are below 10⁻⁵, and both implementations pass the shortage gate. These are technical parity checks, not historical calibration or proof of annual optimality. Different optimal dispatch or disposal quantities can occur through degeneracy.

The current timings are single trials with concurrent jobs and different solver/thread settings. They do **not** establish a speed advantage. A controlled repeat benchmark and independent checks against native constraint coefficients remain necessary.

The saved twelve monthly 2025 solves preserve chronology and inventory continuity but do not coordinate future water value. The next annual milestone is to validate a boundary-state coordinator against a monolithic smaller problem before using it for annual investment valuation.

[Machine-readable comparison](../research/network-benchmark-2025/comparison.json) · [Exact fast input](../research/network-benchmark-2025/input.json)

Reproduce with `tools/export_2025_window.py`, `tools/run_2025_window.py`, `tools/run_2025_window.ts` and `tools/publish_2025_window.py`. Prepared NetCDF files remain offline and ignored; input provenance contains its native-window file hash.
'''
 (ROOT/'docs/2025-conditional-network-benchmark.md').write_text(doc)
 print('Published gated three-case window comparison')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);publish(p.parse_args().folder)
