"""Prepare and solve a conditional 48-hour window; never claim an annual optimum."""
import pathlib,json,time,hashlib,sys
import pandas as pd,pypsa
r=pathlib.Path(__file__).resolve().parents[1];d=r/'data/pypsa-eur';out=d/'benchmark-2025-window';out.mkdir(exist_ok=True)
source=d/'upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc'
reference=d/'monthly-dispatch-sequential/01.nc'
status=out/'status.json'
def record(**kw):status.write_text(json.dumps(kw,indent=2)+'\n')
record(status='native_window_starting',hours=48,method='conditional January window; fixed reference terminal inventory; not annual valuation')
n=pypsa.Network(source);ref=pypsa.Network(reference);snap=n.snapshots[:48]
terminal=ref.storage_units_t.state_of_charge.loc[snap[-1]].copy()
n.set_snapshots(snap)
n.storage_units['cyclic_state_of_charge']=False
n.storage_units['cyclic_state_of_charge_per_period']=False
n.global_constraints=n.global_constraints.iloc[:0]
for k in n.storage_units.index:
 values=pd.Series(float('nan'),index=snap);values.iloc[-1]=terminal[k];n.storage_units_t.state_of_charge_set[k]=values
n.export_to_netcdf(out/'native-input.nc')
record(status='native_window_solving',hours=48,method='conditional January window; fixed reference terminal inventory; not annual valuation')
t=time.perf_counter();result=n.optimize(solver_name='highs',solver_options={'solver':'ipm','run_crossover':'off','threads':2},include_objective_constant=False)
if result!=('ok','optimal'):raise RuntimeError(str(result))
n.export_to_netcdf(out/'native-solved.nc')
record(status='native_window_solved_pending_fast_comparison',hours=48,objective_eur=float(n.objective),elapsed_seconds=time.perf_counter()-t,method='conditional January window; fixed reference terminal inventory; not annual valuation',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
