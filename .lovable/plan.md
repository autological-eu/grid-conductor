# EU Cross-Border Arbitrage Workbench — where we are and what's next

## Done so far

- **Database** on Lovable Cloud: 42 European bidding zones with coordinates, the borders
  between them, hourly tables for prices / CO2 intensity / load / generation mix, hourly
  cross-border flows, plus tables for targets, scenarios, units, results and model validation.
- **Data importers**: a resumable importer that pulls a full year of hourly history
  (ending yesterday) from Electricity Maps in 10-day chunks, with progress tracking,
  pause-on-quota and per-zone/per-signal jobs. An ENTSO-E client fetches official
  day-ahead transfer capacity for a border.
- **Target detection**: a database routine scans every border hour by hour, flags hours where
  the price gap is meaningful *and* the flow sits at its highest observed level in that
  direction (i.e. the line is full), and totals the yearly market loss (MEUR) and
  climate loss (ktCO2) per border.
- **Simulation engine**: an hourly model of the sub-network around a target (the two zones
  plus their neighbours). Each hour, energy is shifted from cheaper to dearer zones until
  prices meet or a line fills up. Batteries do daily price arbitrage, wind/solar add
  generation, new lines raise the transfer limit. Base year vs scenario year gives the
  market and climate opportunity.
- **Scenario management + evaluation**: create scenarios under a target, add units with
  cost and delivery time, run them, and store ENTSO-E CBA-style indicators
  (welfare, CO2, RES integration, losses, security of supply, flexibility, transfer
  capability, capex, NPV, benefit/cost, payback).

## Still to build

1. **Data loading screen** — start the year-long import and watch progress per zone.
2. **The one-page workbench**
   - Center: map of Europe with the zones shaded, and target borders highlighted by size of
     the opportunity. Clicking a target opens its panel.
   - Left: target folders containing scenarios, with drag-and-drop of unit types
     (battery, solar, wind, transmission line, demand response) onto a scenario, and
     editable parameters, cost and delivery time.
   - Right: scenario evaluations with the two headline indicators, expandable to the full
     ENTSO-E indicator set.
3. **Report view** — a printable per-scenario report following the ENTSO-E CBA structure:
   assumptions, method, indicators, sensitivity, and the model validation figures.
4. **Model validation panel** — how closely the base run reproduces observed flows and
   prices (flow direction accuracy, mean errors), shown alongside results so numbers can
   be trusted.

## Method notes

- Congestion is inferred from observed data (full lines + persistent price gap), with
  official ENTSO-E capacity overlaid on the top borders where published.
- Each zone's price response is calibrated from its own history (how its price moves with
  net exports), so added supply or storage moves prices realistically rather than by a
  guessed rule.
- Target losses are reported for a reference relief of 10% of the border's observed
  capacity, so borders can be compared on a like-for-like basis.
