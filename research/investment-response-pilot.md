# Declared investment-response pilot — 2025 accepted baseline

## Status

Protocol declared; no scenario runs completed yet. The retained `data/`
witnesses and the pinned scientific interpreter are required. Nothing here
changes `config/active-research-baseline.json`.

## Question

Does the accepted `mixed_curve_fitting` LP respond plausibly to a declared
investment — a solar or wind generator addition, or a cross-zonal transmission
upgrade — and what do the two accounting views say about it?

- **Model welfare gain**: the annual reduction in total offer cost with fixed,
  price-inelastic demand. Inside the fitted-offer model this equals the change
  in total surplus because consumer payments and producer revenue cancel. It is
  bid-welfare, not verified resource cost or social welfare.
- **Investor income**: generator revenue minus its own declared bid cost, or
  the congestion rent on the price spread across an upgraded commercial link.

These are separate questions. A positive welfare gain does not imply the
investor earns it, and congestion rent is not net social benefit.

## Declared matrix

One full 8,760-hour reclear per entry, no sampling:

| Entry | Delta |
| --- | --- |
| `zero-delta` | none; must reproduce the retained witness within tolerance |
| `gen-solar-<zone>-{500,1000,2000}` | one zero-bid offer column in the highest-availability solar zone |
| `gen-wind-<zone>-{500,1000,2000}` | one zero-bid offer column in the highest-availability wind zone |
| `line-<a>-<b>-x{1.25,1.5,2.0}` | highest-rent commercial link; observed envelope released to a capacity band |

Host zones and the upgraded link are selected from the accepted witness itself:
maximum annual availability for the technology, maximum annual absolute
congestion rent for the link. The selection rule is recorded with the run.

## Declared assumptions

- A new generator follows its zone-technology fitted availability shape, scaled
  so its annual peak equals the declared nameplate. It is a zero-bid offer for
  solar and wind, and it participates in the network only through the
  endogenous zonal net-injection variable, exactly like every other offer.
- A link upgrade scales the historical observed commercial-exchange envelope of
  one link column. Releasing the envelope to a symmetric capacity band is
  declared per entry. The released band is a flow proxy, not verified NTC/ATC.
- PTDF branch ratings are unchanged: the retained inputs carry no
  row-to-branch mapping, so no physical AC circuit upgrade is declared.
- Demand, source fuel costs, original renewable availability, fixed hydro,
  network rows, chronology and the no-emergency gate are unchanged.

## Gates

1. Baseline reproduction: sampled hours of the accepted LP with saved bids match
   the retained objective and zonal prices (objective 0.01 EUR, price 1e-5
   EUR/MWh).
2. Zero-delta scenario: all 8,760 hours match the witness within the same
   tolerances, or the run fails and writes no witness.
3. Every scenario: 8,760/8,760 optimal, zero emergency dispatch, primal
   residual within the accepted 1e-4 MW tolerance.
4. Ladder sanity: the upgraded link's own rent should fall as its capacity
   grows; a solar addition should suppress prices around its host zone in
   daylight hours. Adverse effects in other zones are reported, not repaired.

## Reported per scenario

Annual welfare gain in M EUR; generator dispatch, revenue, bid cost, income and
capacity factor; link signed and absolute rent, binding hours and mean absolute
spread before and after; the ten zones with the largest mean price change;
per-zone generation change; emergency and residual gates. Results are written to
ignored `data/bidding-zone-network-2025/compact-scenarios-v1/` and summarised
here by `run_scenario.py report`.

## Limitations that must accompany every number

- In-sample fitted bids with observed-price root selection; no forward or
  out-of-sample validation.
- Fixed hydro and unchanged original renewable availability.
- Historical exchange envelopes are waived on upgraded links, so a link result
  is a declared capacity sensitivity, not a verified commercial domain.
- 311-row linear PTDF network, N-0, no AC row-to-branch upgrade mapping.
- 48 modeled zones versus 41 complete-price zones; mixed renewable offers have
  no unique technology allocation.

## Commands

```sh
python -m baselines.compact.run_scenario candidates
python -m baselines.compact.run_scenario plan
python -m baselines.compact.run_scenario run
python -m baselines.compact.run_scenario report
```

`report` prints the summary table. Paste it below once every gate has passed;
do not overwrite this declared protocol with generated output.

## Results

Not run yet.
