"""Extract an hourly storage offer example from sealed results; no solve or fit."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from hourly_storage_bids import coefficients, advance

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/bidding-zone-network-2025'
NAME = 'de-lu-storage-supply-curves-2025'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def report():
    old = json.loads((DATA / 'baseline-supply-curve-example-v1/summary.json').read_text())
    for path, sha in (old['sources'] | old['exports']).items():
        assert digest(ROOT / path) == sha, path
    folder = DATA / 'hourly-storage-bids-v1'
    inputs = json.loads((folder / 'inputs.json').read_text())
    summary = json.loads((folder / 'summary.json').read_text())
    audit = json.loads((folder / 'audit.json').read_text())
    assert audit['summary_sha256'] == digest(folder / 'summary.json')
    assert audit['inputs_sha256'] == summary['inputs_sha256'] == digest(folder / 'inputs.json')
    assert summary['forecast_sha256'] == digest(folder / 'forecast.npz')
    for path, sha in inputs['sources'].items():
        assert digest(ROOT / path) == sha, path
    for path, sha in inputs['dependencies'].items():
        assert digest(ROOT / 'tools' / path) == sha, path
    case = summary['cases']['phs_plus_battery_demo']
    assert digest(ROOT / case['witness']) == case['witness_sha256']
    hour = old['hour_utc']
    t = int((np.datetime64(hour.removesuffix('Z')) - np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
    assets = case['assets']; S = len(assets)
    with np.load(ROOT / case['witness']) as w:
        energy = w['energy_mwh'][t-1] if t else w['initial_energy_mwh']
        n = w['values'].shape[1] - 2*S
        charge = w['values'][t, n:n+S]; discharge = w['values'][t, n+S:n+2*S]
        closing = w['energy_mwh'][t]
        price = float(w['row_duals'][t, inputs['zones'].index('DE-LU')])
    with np.load(folder / 'forecast.npz') as f:
        reference = f['reference'][t]
    b = coefficients(assets, inputs['zones'], energy, reference, inputs['design']['bid_margin_eur_mwh'])
    expected, _ = advance(b, charge, discharge)
    np.testing.assert_allclose(expected, closing, rtol=0, atol=1e-7)
    with (ROOT / 'research/de-lu-baseline-supply-curves-2025.csv').open() as f:
        generators = list(csv.DictReader(f))
    for r in generators:
        r['available_mw'] = float(r['available_mw']); r['bid_eur_mwh'] = float(r['bid_eur_mwh'])
    rows = []
    for j, asset in enumerate(assets):
        if asset['zone'] != 'DE-LU':
            continue
        rows.append(dict(asset=asset['id'], technology=asset['technology'], zone=asset['zone'], hour_utc=hour,
                         opening_mwh=float(energy[j]), closing_mwh=float(closing[j]), capacity_mwh=asset['energy_mwh'],
                         buy_eur_mwh=float(b['buy'][j]), sell_eur_mwh=float(b['sell'][j]),
                         charge_offer_mw=float(b['charge_max'][j]), discharge_offer_mw=float(b['discharge_max'][j]),
                         cleared_charge_mw=float(charge[j]), cleared_discharge_mw=float(discharge[j])))
    out = ROOT / 'research' / f'{NAME}.csv'
    with out.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    tech = ['onshore_wind', 'offshore_wind', 'solar', 'nuclear', 'ror', 'gas', 'hard_coal', 'lignite', 'oil', 'biomass', 'waste', 'geothermal']
    names = ['Onshore wind', 'Offshore wind', 'Solar', 'Nuclear', 'Run-of-river', 'Gas', 'Hard coal', 'Lignite', 'Oil / CHP', 'Biomass', 'Waste', 'Geothermal']
    fig, axes = plt.subplots(4, 4, figsize=(16, 12))
    for ax, fuel, title in zip(axes.ravel()[:12], tech, names, strict=True):
        rr = [(r['available_mw'], r['bid_eur_mwh']) for r in generators if r['technology'] == fuel]
        draw(ax, rr, title, '#277b86')
    for ax, fuel, direction in zip(axes.ravel()[12:], ['PHS', 'PHS', 'battery', 'battery'], ['discharge', 'charge', 'discharge', 'charge'], strict=True):
        rr = [(r[f'{direction}_offer_mw'], r['sell_eur_mwh' if direction == 'discharge' else 'buy_eur_mwh']) for r in rows if r['technology'] == fuel]
        label = 'Pumped storage' if fuel == 'PHS' else 'Hypothetical battery'
        draw(ax, rr, label + (' · supply' if direction == 'discharge' else ' · charging demand'), '#8761a8' if direction == 'discharge' else '#c07524', direction == 'charge')
    fig.suptitle('Hourly offers by technology, including storage · DE-LU\n15 July 2025, 12:00–13:00 UTC / 14:00–15:00 CEST', fontsize=17)
    fig.text(.5, .012, 'Each panel has its own axes. Volume is offered availability, not dispatch. Reservoir hydro remains a separate fixed injection.', ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .03, 1, .94))
    picture = ROOT / 'research/assets' / f'{NAME}.png'; fig.savefig(picture, dpi=145); plt.close(fig)
    battery = next(r for r in rows if r['technology'] == 'battery')
    P = float(reference[inputs['zones'].index('DE-LU')])
    lines = ['# How hourly technology curves are generated', '',
             '**DE-LU, 15 July 2025, 12:00–13:00 UTC (14:00–15:00 CEST).** Exact generator offers from the accepted baseline, plus exact stock-limited offers from the audited storage candidate. No new clearing or calibration.', '',
             f'![Technology offers including storage](assets/{NAME}.png)', '',
             '## Shared rules, changing hourly inputs', '',
             'The model evaluates resource- and zone-specific rules every hour. It does not fit 8,760 independent hourly models. Wind/solar weather and capacity determine offered MW; their current offer price is zero. Thermal bids combine technology-specific cost assumptions, fuel/carbon inputs and calibrated zonal seasonal/local-clock adjustments. Gas uses monthly fuel prices; oil uses daily Brent inputs. Nuclear has its own bounded adjustment; other technologies retain their cost offers. These are synthetic bids, not recovered exchange order books. Calendar coefficients were calibrated on the same 2025 observations used for evaluation.', '',
             'The solver sorts all available offers and clears them together across the European network. A domestic curve alone does not determine the zonal price: imports, exports and network constraints matter.', '',
             '## Why the steps?', '',
             'Each horizontal segment represents a finite MW tranche offered at one price. Moving right reaches another tranche/source group at a different price. Gas and coal/lignite source groups use 50%/35%/15% capacity tranches; combining many groups creates many steps. The solver can accept any fraction of each segment: these are divisible hourly offers, not binary block bids. Equal-price tranches appear as a single flat line. Technology labels inside mixed source pools are an availability-preserving display allocation, not separately inferred plant bids.', '',
             '## Storage: two sides of the market', '',
             f'The own-baseline future-48-hour median reference is **{P:.2f} €/MWh**. Discharge asks `P + 1`; charging willingness-to-pay is `round_trip_efficiency × P − 1`. Both prices are recomputed each hour; offered volumes also depend on actual carried stock, power limits, efficiency and remaining energy capacity. Charging is demand, so it is plotted separately from supply. Charging-demand segments are sorted from highest willingness-to-pay downward.', '',
             '| Technology | Charge bid €/MWh | Discharge bid €/MWh | Charge offer GW | Discharge offer GW | Actual charge GW | Actual discharge GW |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for fuel, name in [('PHS', 'Pumped storage'), ('battery', 'Hypothetical battery')]:
        rr = [r for r in rows if r['technology'] == fuel]
        lines.append(f"| {name} | {rr[0]['buy_eur_mwh']:.2f} | {rr[0]['sell_eur_mwh']:.2f} | {sum(r['charge_offer_mw'] for r in rr)/1000:.3f} | {sum(r['discharge_offer_mw'] for r in rr)/1000:.3f} | {sum(r['cleared_charge_mw'] for r in rr)/1000:.3f} | {sum(r['cleared_discharge_mw'] for r in rr)/1000:.3f} |")
    lines += ['', f"The battery starts this hour at **{battery['opening_mwh']/1000:.2f} of {battery['capacity_mwh']/1000:.2f} GWh**. Its remaining 0.20 GWh needs 0.211 GWh of grid energy at 95% charging efficiency: hence only **{battery['charge_offer_mw']/1000:.3f} GW** of charging for this one-hour interval, despite a 1 GW charger. It finishes full. Storage-candidate clearing is **{price:.2f} €/MWh**: below both charging bids and the discharge ask. Both technologies charge and do not discharge.", '',
              'The inventory update uses accepted charging/discharging, not all offered MW. Stock carries into the next hour and across days. Source pumped storage and the demo battery share a sell threshold here but have different charging thresholds because round-trip efficiencies are 75% and 90.25%. Their stock/power limits can also differ.', '',
              '## Scope', '',
              'Reservoir hydro remains a fixed hourly injection, not a flexible storage bid; it is zero in this DE-LU hour. PHS source energy capacities are not verified 2025 inventories. The battery is a hypothetical 1 GW/4 GWh demonstration asset. This candidate worsened annual observed-price fit and has not replaced the accepted baseline. The storage rule is a rolling heuristic, not an annual optimal schedule or a simultaneous daily auction.', '',
              f'[Exact storage offers, stocks and dispatch]({NAME}.csv) · [Exact generator segments](de-lu-baseline-supply-curves-2025.csv) · [Annual storage evaluation](hourly-storage-bids-2025.md).', '']
    doc = ROOT / 'research' / f'{NAME}.md'; doc.write_text('\n'.join(lines))
    receipt = DATA / 'storage-supply-curve-example-v1'; receipt.mkdir(exist_ok=True)
    sources = [folder / v for v in ['inputs.json', 'summary.json', 'audit.json', 'forecast.npz']] + [ROOT / case['witness'], DATA / 'baseline-supply-curve-example-v1/summary.json']
    result = dict(producer_sha256=digest(__file__), hour_utc=hour, case='phs_plus_battery_demo', reference_eur_mwh=P, clearing_eur_mwh=price,
                  sources={str(f.relative_to(ROOT)):digest(f) for f in sources}, exports={str(f.relative_to(ROOT)):digest(f) for f in [out, picture, doc]})
    (receipt / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(reference=P, clearing=price, battery=battery), indent=2))


def draw(ax, rows, title, color, demand=False):
    rows = sorted([(mw, bid) for mw, bid in rows if mw > 1e-7], key=lambda r: r[1], reverse=demand)
    ax.set_title(title, loc='left', fontsize=10, fontweight='bold')
    if rows:
        x = np.r_[0, np.cumsum([r[0] for r in rows])/1000]
        y = np.array([r[1] for r in rows]); span = max(float(np.ptp(y)), 10)
        ax.step(x, np.r_[y, y[-1]], where='post', color=color, lw=2)
        ax.set_xlim(0, x[-1]*1.05); ax.set_ylim(y.min()-.2*span, y.max()+.35*span)
        ax.text(.03, .9, f'{x[-1]:.3f} GW · {y.min():.1f}–{y.max():.1f} €/MWh', transform=ax.transAxes, fontsize=8)
    else:
        ax.text(.5, .5, 'No available offer volume', transform=ax.transAxes, ha='center', fontsize=9)
    ax.set_xlabel('Cumulative offered volume, GW', fontsize=8); ax.set_ylabel('Bid, €/MWh', fontsize=8); ax.grid(alpha=.2)


if __name__ == '__main__':
    report()
