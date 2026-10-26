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

The country schedule currently inherits hourly geographic shares from the old
hydro dispatch. A fresh Swedish source plant-capacity allocation control is being
qualified, preserving country water budgets and network feasibility. The first
attempt rejected a numerical source value−2.84e-14MW; its failure is retained.
Version2 uses the existing1e-4MW gate, without clipping the source or weakening
market/water gates. Inspect actual completion/audit before claiming results.

Local figures and complete data are in nordic-input-controls-report-v1 and
nordic-zonal-hydro-comparison-v1. Source receipts, arrays and figures stay ignored.
No public deployment, accepted-baseline replacement or annual corrected-input
claim. Swedish weeks14/27 remain missing; geographic pooling and inflow-source
scope remain explicit limitations.
