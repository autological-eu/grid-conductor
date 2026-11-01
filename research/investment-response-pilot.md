# Declared investment-response pilot — 2025 accepted baseline

## Status

The declared ten-case pilot completed on the retained 2025 `mixed_curve_fitting`
LP. All 8,760 hours of each case cleared with zero emergency supply. The
zero-delta run reproduced the retained all-hour objective and zonal prices
**exactly**. Nothing here changes `config/active-research-baseline.json` or
establishes a supported investment estimator.

## Full-year pilot results

The plan selected DE-LU for both solar and onshore wind by highest source-profile
annual availability, and the NO2–GB commercial link by highest baseline absolute
model congestion rent. The generator addition is a separate zero-bid offer using
the sealed zone–technology **availability** profile. The accepted renewable
offers are pooled, so the source selector reads this technology profile directly
instead of demanding a nonexistent pure solar or wind offer column.

| Case | Modeled offer-cost reduction, M€ | Added generator income, M€ | NO2–GB signed rent, M€ |
| --- | ---: | ---: | ---: |
| Zero delta | 0.00 | — | 536.28 baseline |
| DE-LU solar +500 MW | 35.42 | 35.30 | — |
| DE-LU solar +1,000 MW | 70.60 | 70.15 | — |
| DE-LU solar +2,000 MW | 140.30 | 138.48 | — |
| DE-LU onshore wind +500 MW | 63.46 | 63.28 | — |
| DE-LU onshore wind +1,000 MW | 126.59 | 125.91 | — |
| DE-LU onshore wind +2,000 MW | 251.81 | 249.06 | — |
| NO2–GB link envelope ×1.25 | 119.87 | — | **542.90** |
| NO2–GB link envelope ×1.5 | 212.45 | — | 492.41 |
| NO2–GB link envelope ×2.0 | 326.63 | — | 357.56 |

Each case has 8,760/8,760 optimal hours and zero emergency MWh. The largest
primal residual across all cases is **2.07×10⁻⁶ MW**, below the retained
10⁻⁴ MW gate. Solver time totals **328.9 seconds** across ten clears; model
loading and reporting are additional. The model-only annual offer-cost reduction
is a *within-model* welfare measure, not verified social benefit. Added
generator income is simulated energy revenue minus its declared zero bid cost,
before capital, operating, balancing and financing costs. Link rent is not
necessarily the return to the owner of a new cable.

The solar daytime sanity check passed: when the 500/1,000/2,000 MW added solar
offers dispatch, mean DE-LU model prices change by **−0.236/−0.466/−0.901
€/MWh**; they do not rise in any such hour. The link's binding hours fall from
**7,246** to **6,637/5,851/4,526** across the three larger envelopes. Its own
signed rent, however, **rises** from 536.28 M€ at baseline to 542.90 M€ at
×1.25 before falling at ×1.5 and ×2.0. Thus the declared rent-decline
expectation does not hold for the first step: extra flow initially outweighs
the change in price spread. Preserve this non-monotonic result when interpreting
the line ladder.

The completed plan, full hourly witnesses and individual summaries remain in
ignored `data/bidding-zone-network-2025/compact-scenarios-v1/`. The tracked
[source-hashed result index](data/compact-scenario-pilot-2025.json) records the
ten summary and witness hashes. `python -m baselines.compact.run_scenario report`
renders the ordered Markdown table. The public two-zone workbench is unchanged.

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
