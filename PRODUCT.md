# Grid Conductor — product requirements

Current product direction, 3 October 2026. Requirements express intended behaviour;
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
| P2 | Clear baseline evidence | Primary annual congestion-rent estimate, floored at zero for display; secondary mean absolute price spread. Explain scheduled flows, coverage and signed calculation. Preserve signed source values. Neither metric is investment welfare or verified TSO income. |
| P3 | Inspectable prices | Every displayed border has two hourly price lines with shaded separation, UTC month/year selection, coverage and provenance. Missing hours remain gaps. |
| P4 | Local scenarios | Create, revisit, edit and remove interventions without login. Refresh retains state; edits invalidate old results. No cloud database. |
| P5 | Honest evaluation | Preserve screening equations and caps. Separate experimental network dispatch from screening; identify period, physics, inputs and assumptions. Do not extrapolate partial windows to annual benefits. |
| P6 | Research publication | Maintain methods, maths, worked examples, validation gates and downloadable JSON/CSV through Markdown in `docs/` and artifacts in `public/research/`. |
| P7 | Mobile and accessibility | Selection, panels, charts and scenarios work on narrow portrait and landscape screens. Dialogs fit and scroll; touch controls are usable; keyboard selection has visible focus. |
| P8 | Static public hosting | Public GitHub Pages URL, correct project base/deep links, reproducible Bun build and CI. No persistent server, paid service or credentials in the browser. |
| P10 | Carbon accounting | Separate hourly production, consumption and intervention emissions. Declare operational versus lifecycle factors, spatial scope, missing data, storage attribution and coverage. Full estimates remain unavailable when positive generation lacks factors; validate before replacing map climate proxies. |
| P9 | Verified annual network planning | Chronological storage and original renewable availability; matched native/fast inputs, feasibility and convergence bounds; smaller monolithic reference before annual-optimum claims. Integrate only verified results. |

## Model boundaries

Observed ENTSO-E price/flow evidence, reduced-form screening, the 2013 weekly
network benchmark, the 2025 conditional 48-hour benchmark and future annual
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

## Documentation ownership

- [README.md](README.md): introduction, setup, repository map and deployment.
- This file: product requirements and acceptance criteria.
- [TASKS.md](TASKS.md): current priorities, blockers and completion evidence.
- [AGENTS.md](AGENTS.md): coding and research operational instructions.
- `docs/*.md`: public research methods and results, including detailed model plans.
- `planning/archive/`: historical proposals; not current requirements.
