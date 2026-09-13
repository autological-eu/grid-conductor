# European target screening

The app's `/targets` page reads `public/research/targets.json`. It is a historical
screening snapshot, separate from the existing map's database targets and scenario
identifiers. `/docs` describes the implemented methods and remaining gaps.

Reproduce with Python 3.10+, no third-party dependencies:

```text
python tools/compute_targets.py
python tools/compute_targets.py --days 30 --threshold 20 --min-coverage 0.8 --output data/carbon-pilot/targets-threshold20.json
python -m unittest discover -s tools -p "test_*.py" -v
```

Defaults read the earlier workspace's `data/annual/indicators.sqlite` in read-only
mode and `data/annual/graph.json`. Override `--archive` and `--graph` if necessary.
No API key or database write is required. The default end is the last complete
UTC day boundary in the price archive; `--end` accepts an explicit exclusive UTC
midnight. The archive is not automatically updated by this command.

Each configured border is evaluated, including borders with missing data. Only
finite EUR/MWh prices on both sides are comparable. Negative and zero prices are
valid. Missing intervals and changes in cheaper-to-dearer direction split events.
An event qualifies at absolute spread >= threshold. Carbon is evaluated only on
event hours where both consumption-lifecycle observations exist in gCO2e/kWh.
Its denominator is separate from price coverage. A positive receiving-minus-
sending intensity difference is context, not marginal emissions savings.

Ranked candidates require at least 80% matched price coverage and one event.
Sort by event-hour share, mean event spread, then stable border identifier.
Mean and p95 spreads use event hours only; p95 is linearly interpolated. Timestamps,
days and durations are UTC. The CLI settings and topology revision/hash are saved.
Operational status is unverified for the provider-configured topology. No claim
of complete geographical coverage or spare capacity is made.

First run, 13 September 2026: 107 borders, 54 zones, 12 August–10 September 2026;
80 screened, 79 ranked, 23 without comparable prices and four below coverage.
The carbon source is the archived Electricity Maps model, explicitly labeled in
the page. The independent flow-tracing pilot is not silently substituted.

The JSON includes all event intervals; the page shows the first 25 events per
border and offers the full download. Currency conversion, event-time transfer
constraints, supply evidence and independent Europe-wide carbon are still needed.
Do not use these screening metrics as project welfare or avoided-emissions KPIs.
