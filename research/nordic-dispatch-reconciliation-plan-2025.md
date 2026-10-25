# Nordic dispatch reconciliation: investigation and implementation plan

Status: source inventory started; no hydro correction, new dispatch solve or new
curve fitting has been performed. This is the active priority before optimizer
or architecture expansion. Keep the fast European clearing model and flexible
monotone bid curves. Establish which physical inputs need correction first.

## Scope and frozen comparison

Focus on NO1–NO5, SE1–SE4, FI, DK1/DK2, starting with northern Norway/Sweden.
Keep ALL48 European modeled zones and their interconnections in any evaluation;
Nordic price diagnosis must not become an isolated Nordic market solve.

Freeze January training/February evaluation at hourly-table Adam1.0/update29:
February price MAE31.66885EUR/MWh. This checkpoint was selected with February
labels among completed trials and is development evidence, not an untouched
forecast or an accepted baseline. Retain its weights, inputs and source hashes.
Rate2 finished before a planned pause was needed. Both higher-rate trials have
101 scores and verified source/pilot receipts; no numerical job remains active
at this review. Rate2 final Jan20.3095/Feb32.1568MAE reinforces the change in
priority. No signal was delivered and no pause receipt was created. Preserve
all checkpoints; no1000-update extension or automatic optimizer restart.

The original conditional-window/monthly-coordination/annual-reference acceptance
ordering remains. This plan does not complete or weaken those research gates,
replace the retained annual reference, resume retired searches, or authorize an
automatic public-app/baseline replacement. Recurring reviews remain disabled.

## Verified starting evidence

- NO4, SE2, SE1, NO3, FI contribute34.81% of February absolute price error in the
  frozen model; bias is predominantly positive. This is an error budget, not
  causal attribution. Price targets remain hourly ENTSO-E auction prices.
- Modeled Norwegian total hydro7.974TWh versus Ember14.007TWh in February.
- Fresh SHA-verified prepared-input inventory:

| Country | January fixed reservoir | February fixed reservoir | January Ember total hydro | February Ember total hydro |
|---|---:|---:|---:|---:|
| NO |17.292|7.726|15.262|14.007|
| SE |3.770|3.307|6.907|6.485|
| FI |0.534|0.466|1.225|0.999|
| DK |0|0|0.002|0.001|

All quantities TWh. Fixed reservoir is NOT total hydro: add modeled run-of-river
and reconcile pumping/reporting scope before making like-for-like comparisons.
Norway's large Jan→Feb schedule swing warrants tracing; it is not yet a verified
calendar bug, capacity deficit or explanation of the price bias.

Observed source paths:

- `tools/sigmoid_month_pairs_2025.py` builds fixed reservoir generation by copying
  the reservoir slice of `accepted_generation`; it does not fit a hydro bid.
- `tools/bidding_zone_network_2025.py` distributes fixed reservoir schedules by
  geographical plant-capacity shares and checks aggregate conservation there.
- `tools/nve_hydro_inputs_2025.py` compiles weekly HBV usable inflow and reservoir
  stocks, explicitly documenting country pooling rather than NO1–NO5 routing.
  Trace whether and how those artifacts reached the CURRENT prepared inputs;
  their existence does not establish that the current model uses them correctly.

Prepared inventory receipt is ignored under `nordic-source-inventory-v1/`.
Existing error report is `research/dispatch-error-budget-2025.md`.

## Stage1 — Trace energy through the actual input chain

Build a chronological ledger for NO/SE/FI/DK, all12months, emphasizing Jan/Feb.
Trace the CURRENT input hashes backward through the accepted-generation witness,
fixed-hydro preparation, NVE update, geographical redistribution and net-demand
subtraction. Record producer/configuration/version, units and exact time axes.
Do not run historical producers merely to regenerate a familiar receipt.

At every available transformation record hourly and monthly reservoir MW/MWh,
run-of-river separately, country/zone sums and any spill/pumping. Check:

1. UTC versus local timestamps, snapshot weights, missing/duplicated hours,
   January/February lengths, ISO weeks and partial boundary weeks.
2. MW/GW and MWh/GWh/TWh conversions; gross versus net electrical output;
   electrical-equivalent versus hydraulic-energy/efficiency conventions.
3. Whether clipping for grid feasibility, source replacement, chronology reindex,
   missing-zone fallback or country/zone allocation changes monthly totals.
4. Whether fixed hydro is subtracted exactly once from zonal demand and included
   exactly once in generation reporting; compare model demand reporting scope.
5. Whether the prepared schedule deliberately redistributes energy between
   months under an earlier objective, rather than representing observed dispatch.

Deliverable: source manifest and monthly conservation ledger showing the FIRST
stage where a mismatch appears. Distinguish missing source coverage from zero.
Gate: explain provenance and any transformation-induced energy difference before
changing bids, scaling hydro or selecting another model candidate.

## Stage2 — Reconcile observations and hydro energy budgets

Use original cached receipts first. Candidate references are NVE hydrology,
reservoir stocks and generation/production statistics; ENTSO-E reservoir,
run-of-river and pumped-storage series; Ember national monthly totals. For Sweden
use Svenska kraftnät/ENTSO-E and relevant national official data; Finland Fingrid/
ENTSO-E; Denmark Energinet/ENTSO-E. Verify actual series, licensing, dates and
coverage before treating any candidate as usable. Fetch only missing evidence.

Build a coverage/taxonomy table: national vs bid-zone domain, reservoir vs ROR,
pumping consumption vs generation, gross/net and excluded autoproduction. Require
all constituent zones before claiming a complete country hourly total; existing
NO5 coverage gaps must remain explicit. Country totals do not identify zonal
hourly hydro. Do not invent hourly observations by expanding monthly totals.

For reservoir components, replay an explicit consistent-basis water ledger:

    stock_end = stock_start + usable_inflow + pumping_input
                - turbine_withdrawal - spill - other_declared_losses

Relate turbine withdrawal to electrical generation with declared efficiencies.
If source units are already electrical equivalents, do not apply efficiency a
second time. Treat gross-stock/net-inflow basis differences as reconciliation
issues. Preserve turbine MW, usable stock bounds, efficiency, spill and boundary
conditions; document interpolated observations and partial weeks.

Deliverable: comparable hydro volumes with known coverage, uncertainty and water
closure. Gate: observed generation remains a validation target, NEVER an
availability profile or a freely scalable water supply. A stock/inflow budget
must support any changed reservoir schedule. No source harmonization claim from
agreement in a single monthly total alone.

## Stage3 — Check zonal allocation and deliverability

First separate national energy differences from geographic distribution errors.
Check NO1–NO5 and SE1–SE4 plant/reservoir assignments and parent-to-zone shares;
capacity shares alone do not establish hourly generation or inflow shares.
Require national/zone conservation, documented fallbacks and no double allocation.

Compare hourly zonal demand, generation and implied net positions against
covered observations, keeping physical flows and commercial schedules distinct.
Inspect existing corridor direction/sign, losses, cross-border capacities and
north–south bottlenecks. Model-derived thermal ceilings are not commercial NTC.
Research verified Nordic commercial constraints if needed; do not apply JAO Core
domains to Nordics or infer an applicable domain from a familiar provider name.

Inspect selected ordinary overpricing hours and extreme-price hours; selection
rules must be declared in advance of model-change scoring. Check whether hydro
can actually reach local load/exports under the represented network. Original
physical/PTDF checks are separate from fast independent-corridor feasibility.

Deliverable: zonal energy/exchange ledger plus diagnosed mapping/constraint flags.
Gate: do not widen transfers or inject missing generation to force price agreement.

## Stage4 — Controlled source-backed corrections

Only after Stages1–3 identify a justified change, create a fresh immutable input
release and a small named experiment. Keep the frozen bid coefficients initially:
this isolates the effect of input/schedule/mapping corrections from refitting.

Prefer the least complex correction supported by evidence: timestamp/unit fix,
reporting-scope fix, water-feasible schedule repair or geographic allocation fix.
Retain fixed hydro as the first control; adaptive hydro is not assumed necessary.
If fixed schedules remain inadequate, consider a separately declared precomputed
water-feasible schedule or water-value formulation. Any retrospective use of
observed stocks/generation is labelled reconstruction; a transferable variant
must state what is available in prediction and avoid target-label leakage.

Test changes separately before combining them. Only after a source-corrected
frozen-bid replay may the SAME original fitting procedure be rerun. Keep the
initialization, budget, losses and optimizer fixed for that comparison. No
simultaneous neural architecture/learning-rate search.

## Stage5 — Evaluation and report

Report Jan and Feb separately plus Europe-wide and all Nordic per-zone metrics:
price MAE/bias/correlation, generation quantities/timing where coverage permits,
exchanges/net positions, negative-price and high-price errors, and water/physical
residuals. Reuse the original error-budget cohort definitions. Report both frozen-
bid and refitted effects, all regressions and non-Nordic spillovers. Do not count
February tuning as untouched validation. Once frozen, assess further chronological
months without modifying the method from their labels; retain prior2025 exposure.

Existing numerical source/energy/feasibility/economic gates remain unchanged.
A benefit must improve predictive evidence without violating water physics or
creating unexplained generation/flow distortions. No invented acceptance score
or silent relaxation; the existing below10EUR/MWh research target is unchanged.
Document tradeoffs before promotion. Baseline fit is not validation of investment
effects: check transmission/storage perturbations separately when inputs qualify.

Final report: concise source ledger, hydro quantities, per-zone prices and error
contributions, a few fixed representative hourly examples, runtime, provenance,
limitations and remaining blockers. Publish only when explicitly within the
requested publication scope and after actual CI/Pages/public-URL verification;
this planning update is local. Commit only compact code/config/docs/summary
artifacts; raw data stays ignored. No main merge, force-push or credential output.

## Immediate next action

Stage1 ledger: locate the exact origin of Norway's17.292→7.726TWh fixed-reservoir
change, compare it with source weekly stock/inflow and verify transfer into current
net demand. Inventory already started; conservation/source reconciliation, a
model correction and causal price evidence are still pending. Stage gates need
verified evidence, not repeated user approval for already-authorized safe work.
