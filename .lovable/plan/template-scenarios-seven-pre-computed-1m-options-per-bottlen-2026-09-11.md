# Template scenarios: seven pre-computed €1M options per bottleneck

Give every new user something to look at immediately: when a bottleneck (target) is selected, the sidebar lists seven ready-made, budget-normalised scenarios so they can compare technologies side by side without building anything by hand.

## The seven templates

For a border between country A and country B:

1. Battery storage in A
2. Battery storage in B
3. Transmission line A–B
4. Wind farm in A
5. Wind farm in B
6. Solar farm in A
7. Solar farm in B

Every template spends the same normalised budget, so the comparison is "what does one million euros buy in each technology, and what does it deliver".

## Budget normalisation

A single shared budget (default €1M, editable at the top of the template list) is converted into physical capacity using current European market prices, then into delivered energy using each technology's annual capacity factor.

| Technology | Installed cost | Capacity per €1M | Capacity factor | Annual output per €1M |
|---|---|---|---|---|
| Battery (2 h) | ~€250 / kWh | 2 MW / 4 MWh | ~1.5 cycles/day | ~2.2 GWh throughput |
| Onshore wind | ~€1.3M / MW | 0.77 MW | ~27% | ~1.8 GWh |
| Solar PV | ~€0.7M / MW | 1.43 MW | ~12% | ~1.5 GWh |
| Transmission | ~€0.4M per MW·100 km | scaled by border length | n/a (availability ~97%) | n/a |

Prices live in one editable cost-assumption table so they can be updated in one place, and each template card shows the price and capacity factor it used. Because €1M buys only a few MW, the cards make clear that results scale roughly linearly — the budget field lets a user jump to €10M or €100M to see a realistic project size.

## Behaviour

- Selecting a bottleneck shows the template list at the bottom of the left sidebar, under the user's own scenarios, in a "Templates" section.
- Each row shows the technology icon, where it sits (country A, country B, or the border), the capacity the budget buys, and — once computed — the two headline numbers: market opportunity (MEUR/year) and climate opportunity (ktCO2/year).
- Templates are pre-computed in the background as soon as a bottleneck is opened for the first time, then stored, so a returning user sees the numbers instantly. A small "computing…" state covers the first run.
- Clicking a template selects it exactly like a normal scenario: the unit appears on the map, and the right-hand evaluation panel opens with the full assessment.
- "Copy to my scenarios" turns a template into an editable scenario the user can tune.
- Recomputing all templates for a bottleneck is available from the settings menu.

## Technical notes

- New server function `ensureTemplateScenarios({ targetId, budgetMeur })` creates the seven scenarios (flagged `is_template`, with a `template_key`) with capacity derived from the cost table, then runs the existing hourly simulation for each and stores results in `scenario_results`.
- Migration: add `is_template boolean default false` and `template_key text` to `scenarios`; templates are keyed per target plus budget so a changed budget triggers a fresh set.
- New `src/lib/costAssumptions.ts` holds the price, capacity-factor, and duration constants shared by the sizing logic (mirrored into `supabase/functions/_shared` if that copy is used).
- Transmission sizing uses the great-circle distance between the two zone centroids already stored in the zones table.
- `TargetSidebar.tsx` gains the Templates section and budget input; `listScenarios` returns the template flag so the two groups can be split.
- Simulation, evaluation, and reporting code are unchanged — templates are ordinary scenarios with generated units.
