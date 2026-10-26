# Nordic input controls: demand, river supply and hydro timing

Goal remains open. All tests keep frozen bid coefficients and the full European
network. January/February are development diagnostics, not untouched forecasts.

| Max-border-flow control | January price MAE | February price MAE |
|---|---:|---:|
| Previous stock/network reconstruction |20.3854|24.1156|
| Norwegian metered demand shares, national load preserved |20.6017|24.3481|
| Consistent reservoir/run-of-river inflow partition |20.4382|24.3810|

Demand shares were not adopted. The additive metered-plus-residual control was
rejected: at2025-02-10T11UTC metered consumption exceeds modeled national demand
by658.43MW. This residual cannot simply be called losses. No hour was dropped.
The proportional allocation is only a scope sensitivity, not a verified demand
replacement. Its complete1416-hour water/market replay passes.

Norway's ROR availability already matches the updated inflow source. Sweden's
February ROR availability falls0.64727→0.36904TWh when using the same published
inflow partition as its reservoir reconstruction. Original turbine limits and
explicit spill remain; wind/solar availability is unchanged. Swedish February
modeled hydro falls6.78066→6.54466TWh against Ember6.485TWh. January agreement
worsens6.89578→6.85606 against6.907TWh. Both JAO envelope controls pass independent
water, bid, flow, generation and price replay. The alternative maxExchanges price
MAEs are20.8663/24.3380. These results are research controls, not adoption.

NVE's published handbook explains that filling ratios are calculated from a
measurement sample and extrapolated to total capacity. Regional sample coverage
varies91.58–97.74%. Applying sample weights reduces the maximum national/regional
stock discrepancy from148.30GWh to5.80GWh across bounding weekly observations.
This substantially explains non-additivity; the remaining discrepancy is not
silently normalized. Weekly sample changes and current table dating remain caveats.
Area attribution uses downstream power-plant energy equivalents, not simply the
reservoir's physical location. Sources:

- https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/
- https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/

Raw Elhub and Swedish ENTSO-E generation comparisons reveal a timing problem.
After river reconciliation, SE2February hydro totals3.44343TWh against reported
3.48590TWh, but hourly correlation is0.0701 and generation MAE2347.89MW. NO4
produces2.43256TWh versus metered1.92595TWh. Monthly totals therefore conceal
large timing and geographical errors. Swedish observations report B12; unreported
categories are not zero-filled or silently reclassified. Generation remains a
validation target, never an availability profile.

The preceding country schedule inherited hourly geographic shares from the old
hydro dispatch. A Swedish source plant-capacity allocation control was completed
with the same country water budgets and network feasibility gates. Its first
attempt rejected a numerical source value of −2.84e-14 MW; that failure is
retained. Version 2 uses the existing 1e-4 MW gate, without clipping the source
or weakening market/water gates.

Local figures and complete data are in nordic-input-controls-report-v1 and
nordic-zonal-hydro-comparison-v1. Source receipts, arrays and figures stay ignored.
No public deployment, accepted-baseline replacement or annual corrected-input
claim. Swedish weeks14/27 remain missing; geographic pooling and inflow-source
scope remain explicit limitations.

## Completed static Swedish geography control

Version2 completed all1,416hours for both JAO envelope controls and passed the
independent water, market, polynomial bid, flow, generation and metric replay.
Only the inherited hourly geographic shares were replaced with source mapped
reservoir plant capacity shares; country water schedules, river source, bid
coefficients and demand totals were preserved. Original gates were unchanged.

| Consistent river + geography | Jan MAE | Feb MAE |
|---|---:|---:|
| Inherited hourly hydro shares, maxBorderFlow |20.4382|24.3810|
| Static plant capacity shares, maxBorderFlow |20.1633|23.8711|
| Inherited hourly hydro shares, maxExchanges |20.8663|24.3380|
| Static plant capacity shares, maxExchanges |20.6525|23.9526|

Price MAE is EUR/MWh across41complete targets. Generation MAE improves slightly
in February:0.278064→0.277967TWh under maxBorderFlow and0.277148→0.276928TWh
under maxExchanges. This is a source grounded improvement in the two-month
retrospective diagnostic; it does not establish correct zonal water routing or a
full-year forecast. Raw observed zonal generation is reserved for validation.

The independently audited raw observations provide a stronger check on the
geographic change. With the new allocation, SE2's February hourly hydro shape
correlation rises from 0.0701 to 0.5065 and hourly MAE falls from 2,347.89 to
798.76 MW. Yet its modelled volume is 3.2822 TWh against 3.4859 TWh reported.
SE1's February modelled 2.5118 TWh remains above its reported 1.8283 TWh,
with correlation 0.3917 and hourly MAE 1,160.16 MW. NO4 remains 2.4368 TWh
versus 1.9259 TWh metered, with correlation 0.2621. The observation and saved
market replay hashes, plus all January/February zone scores, are in the ignored
`sweden-static-hydro-allocation-v2/observed-hydro-audit.json`. These comparisons
are validation of reported generation, not substitutions for availability.
