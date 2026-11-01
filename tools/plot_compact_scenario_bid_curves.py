"""Plot accepted DE-LU offers and the saved 1 GW solar scenario, without a re-solve."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.run_scenario import OUT, baseline_evidence, build_scenario, read
from baselines.compact.source import digest

ROOT = Path(__file__).resolve().parents[1]
NAME = 'gen-solar-DE-LU-1000'
model, costs, base = physical_lp(), *saved_annual()
plan = read(OUT / 'plan.json')
entry = next(row for row in plan['scenarios'] if row['name'] == NAME)
evidence = baseline_evidence()
scenario = build_scenario(entry, evidence['sources'], evidence['endpoints'])
addition = scenario.generators[0]
folder = OUT / NAME
summary = read(folder / 'summary.json')
if digest(folder / 'annual.npz') != summary['witness_sha256']:
    raise ValueError('Scenario witness hash changed')
with np.load(folder / 'annual.npz') as archive:
    trial = {key: archive[key] for key in ('values', 'row_duals', 'hours')}
if not np.array_equal(trial['hours'], np.arange(8760)):
    raise ValueError('Scenario chronology changed')
zone = list(map(str, model['zones'])).index('DE-LU')
base_price = base['row_duals'][:, zone]
trial_price = trial['row_duals'][:, zone]
price_delta = trial_price - base_price
eligible = np.flatnonzero((addition.profile_mw > 100) & (np.abs(price_delta) > 0.1))
if not eligible.size:
    raise ValueError('No representative active hour')
# Median magnitude among active, price-changing hours: a stated selection rule.
hour = int(eligible[np.argsort(np.abs(price_delta[eligible]))[len(eligible) // 2]])
mask = (model['offer_zones'].astype(str) == 'DE-LU') & ~model['emergency_mask']
avail = model['availability'][hour, mask]
bids = costs[hour, mask]
valid = avail > 0
avail, bids = avail[valid], bids[valid]
order = np.argsort(bids, kind='stable')
avail, bids = avail[order], bids[order]

def stack(capacity, price):
    order = np.argsort(price, kind='stable')
    cumulative = np.r_[0, np.cumsum(capacity[order])] / 1000
    return cumulative, price[order]

xb, yb = stack(avail, bids)
xs, ys = stack(np.r_[avail, addition.profile_mw[hour]], np.r_[bids, addition.bid_eur_mwh])
old_dispatch = float(base['values'][hour, :model['ng']][mask].sum())
old_in_trial = float(trial['values'][hour, :model['ng']][mask].sum())
new_dispatch = float(trial['values'][hour, model['ng']])

fig, (ax, timeline) = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw={'width_ratios': [1.3, 1]})
ax.step(xb, np.r_[yb, yb[-1]], where='post', label='Existing offers · both cases', color='#5b657b', lw=2)
ax.step(xs, np.r_[ys, ys[-1]], where='post', label='With 1 GW solar addition', color='#007f78', lw=2)
ax.axhline(base_price[hour], color='#5b657b', ls=':', lw=1.8, label='Baseline network price')
ax.axhline(trial_price[hour], color='#007f78', ls='--', lw=1.8, label='Scenario network price')
ax.scatter([old_dispatch / 1000], [base_price[hour]], color='#5b657b', zorder=5)
ax.scatter([(old_in_trial + new_dispatch) / 1000], [trial_price[hour]], color='#007f78', zorder=5)
ax.set(xlabel='Cumulative DE-LU offered output (GW)', ylabel='Bid / cleared price (€/MWh)',
       title='Local offer stack and network-cleared result')
ax.set_xlim(40, 78)  # Deliberate zoom around the modeled clearing quantity.
ax.set_ylim(-110, 490)
ax.grid(alpha=.2)
ax.legend(fontsize=8, loc='upper left')

start = hour // 24 * 24
hours = np.arange(start, start + 24)
timeline.plot(hours - start, base_price[hours], label='Baseline price', color='#5b657b', lw=2)
timeline.plot(hours - start, trial_price[hours], label='With solar', color='#007f78', lw=2)
timeline.fill_between(hours - start, base_price[hours], trial_price[hours], color='#007f78', alpha=.15)
timeline.axvline(hour - start, color='#222', ls=':', lw=1)
timeline.set(xlabel='UTC hour of day', ylabel='DE-LU network price (€/MWh)',
             title='Same date · hourly price response')
timeline.set_xticks(np.arange(0, 24, 3))
timeline.grid(alpha=.2)
timeline.legend(fontsize=8)

stamp = str(np.datetime64('2025-01-01T00') + np.timedelta64(hour, 'h'))
fig.suptitle(f'DE-LU · {stamp} UTC · 1 GW new solar (median active price effect)', fontsize=13)
fig.text(.5, .015, 'Offer stack zoom: 40–78 GW. Markers show modeled local dispatch after network exchange, not observed demand.',
         ha='center', fontsize=9, color='#555')
fig.tight_layout(rect=[0, .04, 1, .94])
output = ROOT / 'research/figures/compact-solar-bid-curves-2025.png'
fig.savefig(output, dpi=180)
plt.close(fig)
print(json.dumps(dict(hour=hour, timestamp_utc=stamp, new_available_mw=float(addition.profile_mw[hour]),
                      new_dispatched_mw=new_dispatch, baseline_price_eur_mwh=float(base_price[hour]),
                      scenario_price_eur_mwh=float(trial_price[hour]),
                      baseline_local_offer_dispatch_mw=old_dispatch,
                      scenario_existing_offer_dispatch_mw=old_in_trial,
                      selection_population_hours=int(eligible.size), figure=str(output)), indent=2))
