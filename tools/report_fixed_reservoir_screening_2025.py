"""Report fixed-reservoir screening separately from adaptive hydro."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/research/fixed-reservoir-screening-2025'

def run():
    s=json.loads((OUT/'summary.json').read_text());d=pd.read_csv(OUT/'hourly-de.csv',parse_dates=['utc']);a=pd.read_csv(OUT/'area-summary.csv')
    if s['hours']!=8760 or len(d)!=8760 or s['provenance']['producer_sha256']!=digest(ROOT/'tools/fixed_reservoir_screening_2025.py'):raise ValueError('Changed producer or incomplete year')
    if abs((d.fixed_hydro_de_eur_mwh-d.chronological_de_eur_mwh).abs().mean()-s['germany']['price_mae_vs_chronological_eur_mwh'])>1e-9:raise ValueError('Price export mismatch')
    if abs(a.emergency_supply_twh.sum()-s['emergency_supply_twh'])>1e-9:raise ValueError('Shortage export mismatch')
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained');w=d.set_index('utc').resample('7D').mean()
    for column,label in [('observed_de_lu_eur_mwh','Observed DE-LU'),('chronological_de_eur_mwh','Chronological reservoirs'),('fixed_hydro_de_eur_mwh','Fixed hourly hydro')]:axes[0].plot(w.index,w[column],label=label)
    axes[0].set(title='German price proxy — seven-day means of all hourly results',ylabel='EUR/MWh');axes[0].legend();axes[1].hist(d.fixed_hydro_de_eur_mwh-d.chronological_de_eur_mwh,bins=60);axes[1].set(title='All 8760 hours — fixed-hydro versus chronological marginal prices',xlabel='Price difference EUR/MWh',ylabel='Hours');fig.savefig(OUT/'price-comparison.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained');ax.barh(['Chronological LP solves','Fixed-schedule solve/replay loop','Fixed-schedule preparation/water check'],[s['chronological_solver_seconds'],s['warm_solve_replay_seconds'],s['preparation_and_water_audit_seconds']]);ax.set(xlabel='Measured seconds',title='Offline hydro calculation versus reusable fixed-schedule clearing');fig.savefig(OUT/'runtime-comparison.svg');plt.close(fig)
    g=s['germany'];text=f'''## Fast screening: precomputed hourly reservoir output

The verified chronological reservoir schedule can now be reused for fast
independent-hour network clearing. All **8,760 hours** clear in **{s['warm_solve_replay_seconds']:.2f}
seconds**, including network replay. Preparation, source checks and replay of the
full water schedule add **{s['preparation_and_water_audit_seconds']:.2f} seconds**. These
measurements exclude Python imports, the offline 17.1-minute reservoir solve,
separate native verification and reporting. This demonstrates fast reuse of a
precomputed schedule, not seconds-scale adaptive reservoir optimisation.

Each of the 93 reservoirs contributes its saved electric turbine output as an
explicit **fixed injection**, in its original country/island area. Original demand,
weather-based generator availability, IRENA wind/PV trajectory, GSKs and physical
constraints remain unchanged. Dispatch is not relabelled as availability. Negative
residual demand means fixed hydro exceeds that area's load and must be exported;
original demand itself is not replaced with negative values.

| Metric | Chronological reservoirs | Fixed hourly reservoir schedule |
| --- | ---: | ---: |
| Reported LP solve / hourly solve-and-replay seconds | 1027.42 | {s['warm_solve_replay_seconds']:.2f} |
| European emergency supply TWh | 0.0298195 | {s['emergency_supply_twh']:.7f} |
| Hours with emergency supply | 4 | {s['shortage_hours']} |
| German observed-price MAE €/MWh | 23.07 | {g['mae_eur_mwh']:.2f} |
| German observed-price bias €/MWh | −9.29 | {g['bias_eur_mwh']:+.2f} |
| German observed-price RMSE €/MWh | 35.96 | {g['rmse_eur_mwh']:.2f} |

![Measured offline and reusable solve timings](../../research/fixed-reservoir-screening-2025/runtime-comparison.svg)

Total operating cost differs from the chronological result by only
**{s['objective_difference_vs_chronological_eur']:.6f} euros**. Fixing the saved conditional
hydro output leaves an independently solvable network problem per hour; this
cost agreement checks reuse of that solution under unchanged assumptions. It
is not verification of a changed-input or investment scenario.

Three January/July/December native PyPSA solves with the same fixed injections
match objectives within **€0.000003**. Full-year network/bound replay has maximum
residual **{s['maximum_network_residual_mw']:.2e} MW**. Original hourly water balances,
turbine/energy limits, spill and annual closure are replayed before screening;
maximum water residual is **{s['maximum_water_residual_mwh']:.2e} MWh**. {len(s["cold_retries"])} nonoptimal
warm-basis solves recovered through unchanged-input cold retries. Two new tests
reject double-spent water, broken closure and incorrect area mapping, and check
fixed-injection accounting when local hydro exceeds demand.

![Hourly-price comparison with chronological hydro and observations](../../research/fixed-reservoir-screening-2025/price-comparison.svg)

German fixed-schedule marginal prices differ from chronological prices by
**{g['price_mae_vs_chronological_eur_mwh']:.3f} €/MWh on average**, with maximum absolute
hourly difference **{g['maximum_price_difference_vs_chronological_eur_mwh']:.2f} €/MWh**.
Matching operating cost does not require matching dual prices: fixed hydro
cannot respond at the margin, whereas the chronological LP can reallocate water.
The observed DE-LU comparison remains an uncalibrated mainland-DE scope proxy.

**Conclusion:** the fixed-schedule variant achieves a seconds-scale annual
screening loop for this baseline. Hydro cannot respond to new transmission,
batteries, demand or bid costs. A future intervention case would be conditional
on the same hydro schedule and would need its own verification; adaptive hydro
requires water-value bids and enforceable water budgets, or a fresh chronological
solve. The other 67 battery/PHS units remain excluded. This research pipeline
has not replaced the browser scenario estimator or closed annual/investment gates.

[Summary, native checks and source/witness hashes](../../research/fixed-reservoir-screening-2025/summary.json),
[all area comparisons](../../research/fixed-reservoir-screening-2025/area-summary.csv),
and [hourly German prices](../../research/fixed-reservoir-screening-2025/hourly-de.csv).
Large calculation witnesses remain in the ignored cloud cache.

'''
    p=ROOT/'docs/european-physical-synthetic-clearing-2025.md';body=p.read_text();start=body.find('## Fast screening: precomputed hourly reservoir output');end=body.index('## Reservoir-enabled full-year result')
    p.write_text(body[:(start if start>=0 else end)]+text+body[end:]);print('Fixed-hydro report updated')

if __name__=='__main__':run()
