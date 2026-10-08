# Grid Conductor — product requirements

Current product direction, 5 October 2026. Requirements express intended behaviour;
implementation and verification status belong in [TASKS.md](TASKS.md).

## Purpose and audience

An experimental European electricity-grid planning and investment workbench for
students, researchers and planners. Help people identify recurring cross-zone
price separation, inspect its evidence, and explore transmission and storage
interventions with transparent assumptions. The map is the landing page.
The product supports investigation; it does not certify investment returns.

## Core journey

1. Select a European bidding-zone border on the map or in the accessible picker.
2. Understand the observed annual metrics and inspect the hourly price evidence.
3. Create a browser-local scenario and add a line or battery.
4. Evaluate it with an explicitly identified model.
5. Review estimated benefits, costs, climate assumptions and limitations.

A new visitor should understand this workflow within roughly 30 seconds.

## Requirements and acceptance criteria

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| P1 | Map-first workbench | One edge per unordered zone pair; both related countries highlight on selection; reverse directional scenario selection works. |
| P2 | Clear baseline evidence | Primary annual congestion-rent estimate, floored at zero for display; secondary mean absolute price spread. Explain coverage, signed calculation and audited flow-source type. If historical scheduled/physical classification is unverified, show that limitation rather than asserting a type. Preserve signed source values. Neither metric is investment welfare or verified TSO income. |
| P3 | Inspectable prices | Every displayed border has two hourly price lines with shaded separation, UTC month/year selection, coverage and provenance. Missing hours remain gaps. |
| P4 | Local scenarios | Create, revisit, edit and remove interventions without login. Refresh retains state; edits invalidate old results. No cloud database. |
| P5 | Honest evaluation | Preserve screening equations and caps. Separate experimental network dispatch from screening; identify period, physics, inputs and assumptions. Do not extrapolate partial windows to annual benefits. |
| P6 | Research publication | Maintain methods, maths, worked examples, validation gates and downloadable JSON/CSV through Markdown in `docs/` and artifacts in `public/research/`. |
| P7 | Mobile and accessibility | Selection, panels, charts and scenarios work on narrow portrait and landscape screens. Dialogs fit and scroll; touch controls are usable; keyboard selection has visible focus. |
| P8 | Static public hosting | Public GitHub Pages URL, correct project base/deep links, reproducible Bun build and CI. No persistent server, paid service or credentials in the browser. |
| P10 | Carbon accounting | Separate hourly production, consumption and intervention emissions. Declare operational versus lifecycle factors, spatial scope, missing data, storage attribution and coverage. Full estimates remain unavailable when positive generation lacks factors; validate before replacing map climate proxies. |
| P9 | Verified annual network planning | Chronological storage and original renewable availability; matched native/fast inputs, feasibility and convergence bounds; smaller monolithic reference before annual-optimum claims. Integrate only verified results. |

## Milestone: production-based lifecycle carbon intensity

Estimate the carbon intensity of electricity **produced in each supported zone**
from its observed generation mix and documented lifecycle emissions factors.
Prioritize full-year 2025 where data coverage supports it; label partial periods.
Cover the countries/bidding zones displayed on the map and allow inspection
of production estimates during jointly observed hours with absolute cross-zone
price spread above €5/MWh. This selection is price separation, not proof of
physical congestion. Show generation/factor coverage and national proxies
explicitly; unavailable areas remain unknown.
This is separate from import-adjusted consumption intensity and avoided emissions
from investments.

Use **g CO2e/kWh of electricity generated** with a consistent lifecycle boundary:
fuel extraction and processing, manufacturing/construction, operation, and
decommissioning/end-of-life where included by the selected source. Record the
boundary rather than claiming every published factor covers identical stages.
Prefer authoritative harmonised assessments (such as IPCC) and regionally
appropriate fleet estimates over undocumented constants.

Completion requires:

- Hourly generation by technology, with zone identity, provenance and audited
  coverage; independent monthly-total checks. National data must not be presented
  as individual bidding-zone data.
- A versioned factor registry recording source, technology, units, lifecycle
  boundary, geography, representative value/range and justified mapping.
- Explicit treatment of biomass biogenic carbon, waste fossil share, CHP
  allocation, hydro variation and technology/fleet differences. Unresolved
  sources remain unknown rather than receiving zero emissions.
- Energy-weighted hourly, monthly and annual estimates with missing-data and
  factor-coverage diagnostics, plus sensitivity to plausible factor choices.
  Full estimates stay unavailable for incomplete generation or positive
  generation with unresolved factors.
- Published generation-mix and intensity charts, methods, downloadable artifacts
  and transparent limitations. Integrate verified production estimates into the
  app under their own label; do not overwrite consumption or marginal metrics.
- Separate storage discharge from primary generation until charging-origin
  attribution prevents double counting.

A lifecycle factor describes emissions attributed per unit of generated
electricity across a technology's life; it is not a claim that those emissions
occur during the displayed hour. Do not combine operational and lifecycle
factors within one purportedly consistent estimate.

## Goal: memory-efficient 2025 dispatch with observed-data validation

Run a full-calendar-year PyPSA-based dispatch within the managed environment's
memory budget, preserving hourly chronology, network constraints, storage physics
and original renewable availability. Aim for defensible agreement with observed
2025 ENTSO-E evidence, rather than numerical solver agreement alone.

Acceptance requires:

- Record peak memory, runtime, checkpoint/restart behaviour, exact input/code
  hashes, feasibility checks and convergence bounds. A feasible annual trial
  may be reported as experimental; it is not an annual optimum certificate.
- Define and audit the mapping from model nodes to actual bidding zones. Declare
  price aggregation, UTC alignment, interval weighting and jointly observed
  coverage; preserve gaps and spatial proxies. Nodal marginal prices and zonal
  day-ahead prices are different quantities and need explicit interpretation.
- Compare hourly price bias, absolute error, correlation and seasonal patterns;
  prioritise border-spread magnitude, direction and duration. Cross-check
  generation by technology and scheduled/physical exchanges under their correct
  labels, so apparent price agreement is supported by plausible dispatch.
- Predeclare quantitative acceptance thresholds, minimum coverage and the
  calibration/held-out split before fitting or assessing the model. Numerical
  thresholds are not yet selected. Do not tune and claim validation on the same
  observations or select only favourable zones/hours after seeing errors.
- Declare fuel-cost year, operational carbon-pricing assumptions and any policy
  or calibrated variants, with separate input hashes and matched baselines. Keep
  operational pricing factors distinct from production lifecycle accounting.
- Publish supported zones/periods, error metrics, validation failures, assumptions
  and limitations. Explain fuel-cost, outage, fleet, weather and market-design
  mismatches; do not force exact price matching through undocumented changes.

Keep computational consistency (matched native/fast solves) separate from
empirical validation (agreement with observations). Preserve existing research
and annual acceptance gates. Investment benefits and carbon effects require their
own paired-dispatch checks; price agreement alone does not validate them.

## Model boundaries

Observed ENTSO-E price/flow evidence, reduced-form screening,
the 2025 conditional 48-hour benchmark and annual reference
results are separate products of separate assumptions. Keep them labelled.

Climate screening uses average-mix proxies, not demonstrated avoided emissions.
Network climate outputs require signed dispatch differences and complete factors.
Gross system operating-cost savings are not investor income. The existing
25-year screening benefit-minus-capex figure is undiscounted.

Do not infer physical congestion solely from price separation. Do not replace
renewable availability with observed or modelled dispatch. Keep offline Python,
PyPSA-Eur and credential-backed collection outside the browser.

## Scope and exclusions

Public v1 supports transmission and battery interventions. Authentication,
cloud synchronization, paid hosting, detailed siting, dispatch-grade certification,
and unvalidated annual or within-zone investment claims are outside current scope.
Future extensions require explicit model inputs and verification.

## Engineering constraints

Static Bun/Vite/React/TanStack Router, IndexedDB and published research artifacts.
Keep useful existing UI and research. Never commit credentials or ignored large
caches/networks. Work on `public-v1`; reviewed merge only, no force-push.

## Research cache and recovery

Keep large reproducible provider inputs as local caches; do not upload
multi-gigabyte backups to GitHub or establish third-party bulk backups merely
to mirror those inputs. Preserve source requests, versions and hashes for
reconstruction. Prioritise compact solver-state/result recovery with provenance;
a changed reconstructed input must not silently resume saved optimisation cuts.

## Documentation ownership

- [README.md](README.md): introduction, setup, repository map and deployment.
- This file: product requirements and acceptance criteria.
- [TASKS.md](TASKS.md): current priorities, blockers and completion evidence.
- [AGENTS.md](AGENTS.md): coding and research operational instructions.
- `docs/*.md`: public research methods and results, including detailed model plans.
- `planning/archive/`: historical proposals; not current requirements.

## Accepted direction: network dispatch for scenario screening

Move toward coupled fast network dispatch as the scenario estimator, verified
against matched native PyPSA baseline/intervention solves. Expose the verified
2025 conditional window as a clearly labelled experiment now; annual map
replacement remains gated on complete annual inputs, geography, chronology,
paired native/fast verification and existing empirical/investment requirements.
Publish comparative evidence as a readable report with data visualisations,
clear summary and conclusion, without requiring scenario-menu interaction.
Use one retained 2025 hourly PyPSA-Eur reference for generation/capacity
comparisons. Retire obsolete result publications and local research candidates;
retain the selected reference’s reproducible evidence and source inputs.
Reports must name the model and actual solve period in tables and charts. Explain
internal candidate identifiers and whether inventories are fixed, annual bounds
are converged, and comparisons represent numerical parity or observed-data
differences. Country/fuel differences must retain missing observations and
unequal accounting scopes explicitly.


## Accepted direction: hourly zonal dispatch

Build an actual 8,760-hour 2025 bidding-zone dispatch model for paired baseline
and transmission/battery scenarios. Prepare demand, original renewable
availability, hydro inflows and other audited inputs once; reuse them across
solves. Preserve chronological storage and label commercial network assumptions.
Aim for results in seconds, verified by measured runtime and numerical accuracy;
precomputed response curves and statistical surrogates are optional future
alternatives, not the primary calculation. Existing annual and empirical gates
remain intact; an aggregated model cannot certify the old physical-model optimum.
See [hourly zonal dispatch plan](docs/hourly-zonal-dispatch-plan.md) for proposed
implementation, verification and unresolved design choices.

## Accepted direction: synthetic coupled market clearing

Implement continuous synthetic supply bids with fixed observed demand as the
first demand representation, then verified commercial cross-zone constraints
and chronological resources. It is EUPHEMIA-inspired, not reconstruction of
actual order books or full nonconvex EUPHEMIA rules. Declare bid assumptions and
operational carbon pricing separately from lifecycle accounting. Keep
uncalibrated diagnostics separate from training and held-out validation.
Publish German offer curves and simulated-versus-observed DE-LU prices with
coverage, source scope, errors and failures, followed by coupled model evidence.
The existing numerical, annual, empirical and paired-investment gates remain
required before scenario integration. See the step-by-step plan in
[synthetic zonal clearing](docs/synthetic-zonal-clearing-plan.md).


Model-derived physical constraints are an authorized synthetic-clearing sensitivity
route, kept distinct from verified commercial JAO constraints. Preserve separate
AC-island accounting and explicit bounded, efficiency-consistent controllable links.
Independent-hour results that exclude hydro/storage must disclose shortages and
cannot satisfy chronological annual or scenario-integration gates. Native numerical
parity and observed-market validity remain separate.


Use the accepted IRENA end-2024 to end-2025 linear capacity trajectory for wind
and solar in the current synthetic-clearing diagnostic, preserving original
weather profiles and recording unreconciled coverage. Linear net capacity change
is an assumption, not observed commissioning dates. Retain the original-fleet
comparison and do not infer reservoir water/inventory or other technology inputs
from renewable turbine/generator MW alone.

The reservoir extension must schedule original hourly inflows with turbine,
energy, efficiency and standing-loss limits and continuous inventories across
blocks. A first conditional run may fix boundaries to the retained annual
reference, explicitly distinguishing that case from a jointly optimised annual
solution. Independently replay water/network feasibility and annual closure;
verify a matched chronological case against native PyPSA before annual execution.
Do not infer water availability from IRENA capacity or silently reset inventories.

A fast screening variant may reuse an audited hourly reservoir output schedule
as explicit fixed injections, preserving original generator availability and
checking the full water balance first. Label this conditional on the offline
hydro schedule: it cannot estimate hydro response to investments. Keep timing
of offline preparation separate from reusable screening, and compare marginal
prices as well as objective cost against chronological and matched native cases.
Adaptive water-value bids remain a separate, unverified extension.

The public European physical-clearing report should present the final fast
fixed-reservoir model as one coherent report, with current results, visualisations,
input/method provenance and numerical/observed-price verification. Omit superseded
model narratives and comparison charts from that report while retaining supporting
evidence and material limitations, especially fixed-hydro price sensitivity.
