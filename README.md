# Grid Conductor

An experimental European electricity-grid investment and market-opportunity
workbench. The interactive map is the landing page: select a border,
inspect published evidence, create a scenario, add transmission or battery
interventions, and evaluate estimated economic and climate indicators.

Public site: **https://autological-eu.github.io/grid-conductor/**.
Deployment requires GitHub Pages to be enabled for this repository; a successful
build alone does not establish a live deployment.

## Project documents and repository map

- [Product requirements](PRODUCT.md): purpose, scope and acceptance criteria.
- [Current tasks](TASKS.md): ordered milestones, blockers and verification gates.
- [Agent instructions](AGENTS.md): implementation and research operating rules.
- `src/`: static browser application; `tests/`: Bun tests.
- `tools/` and `config/`: offline research, verification and publication tooling.
- `docs/` and `public/research/`: published methods and reviewed artifacts.
- `planning/archive/`: preserved historical plans, not current architecture.
- `.github/workflows/`: verification and Pages deployment.
- Ignored `data/`: private local inputs, credentials and large generated outputs.

## Browser application

**Bun → Vite → React 19 → TanStack Router → static GitHub Pages.** Tailwind v4,
shadcn/ui and TanStack Query support the existing workbench. No continuously
running Bun/Node server, authentication, cloud database or paid service is needed.

- `/`: European map, bottleneck selection, local scenarios and evaluation.
- `/docs`: research publications sourced from `docs/*.md`, plus published artifacts.
- `/docs/<document-slug>`: individual Markdown publication.
- `/network`: experimental HiGHS/WASM coupled dispatch lab; complete local input
  or load the verified 2025 conditional-window input; separate IndexedDB workspace.
  Annual scenario claims remain gated on verified inputs and paired solves.
  See [2025 PyPSA-Eur comparison](docs/pypsa-fleet-generation-comparison-2025.md). No validated
  European annual dataset yet. See the [2025 rebuild](docs/fast-network-2025-rebuild.md).
- `/targets`: separate observed-spread and PyPSA-Eur evidence views.
- `src/lib/workbench.ts`: versioned IndexedDB persistence; stable IDs, ordered
  interventions, scenario snapshots and results. Edits invalidate old evaluations.
- `src/lib/fast-entsoe-lp.ts`: pure-JavaScript Step-2 screening calculations,
  fetched from `public/research/entsoe-fast-targets.json` through the base-aware
  research loader. The LP module is loaded when a scenario is evaluated.

Scenarios belong to this browser and origin. Refreshing or reopening retains
state; clearing site data removes it. There is no synchronization, account or
SQLite migration. Browser storage must be available. Lines and batteries are the
supported public-v1 interventions; renewables and demand response remain research
extensions. Unit placement selects the target's zones/corridor; the reduced-form
model does not simulate detailed geographic placement or an hourly network.

## Local development

Install [Bun](https://bun.sh/) **1.4.2**, then:

```sh
bun install --frozen-lockfile
bun run dev
```

Open the URL printed by Vite **with `/grid-conductor/` appended** (normally
`http://localhost:5173/grid-conductor/`). No `.env` or API credentials are needed.
The dependency policy retains a 24-hour minimum package release age.

```sh
bun run lint
bun run typecheck
bun run test
bun run build
bun run preview
```

`dist/` is the complete deployable static site. Vite owns React, Tailwind and
TanStack Router configuration explicitly; no Lovable or TanStack Start/SSR
runtime remains. Router generation updates `src/routeTree.gen.ts`; do not edit it
manually. The small Bun test suite covers screening caps/annual units and the
IndexedDB lifecycle using fake-indexeddb. For the real Chromium smoke check:

```sh
bunx playwright install chromium
bun run preview                  # keep running in another terminal
bun run test:browser
```

`SMOKE_URL` can target another static server or the deployed project-site URL.
The smoke check uses fresh browser contexts, creates local test scenarios and
checks desktop/mobile interaction, reload persistence and direct routes.

## Research and methodology

Offline Python, ENTSO-E, JAO and PyPSA-Eur tooling in `tools/` and `config/`
produces reviewed publications in `docs/*.md` and artifacts in
`public/research/*`. Vite publishes Markdown without bundling Python or heavy
models. Add a Markdown file to `docs/` to publish another research article;
relative links between publications are resolved by the renderer. Retain
provenance, period, assumptions and validation status in each artifact.

The workbench uses full-year **2025 screening**, not validated hourly dispatch:

- Cable welfare retains the exact trapezoid price-response calculation.
- Batteries retain the javascript-lp-solver daily-cycle model and finite-difference
  shadow-price re-solves. Combined gains remain capped at Step-1 deadweight loss.
- Annual values are annual sums, never a representative month multiplied by 12.
- Climate figures are unsigned average-mix proxies, **not demonstrated avoided
  emissions**. The 25-year benefit-minus-capex figure is undiscounted.
- Separate FR–CH and EU research gates retain their published failed/blocked
  status; PyPSA-Eur topology and JAO coverage are not validated investment benefits.

Start with [screening methodology](docs/fast-entsoe-screening.md),
[validation](docs/market-model-validation.md),
[European input quality](docs/market-model-eu-validation.md),
[carbon integration gates](docs/carbon-pilot.md),
[flow tracing](docs/flow-tracing.md) and
[PyPSA-Eur targets](docs/pypsa-eur-targets.md).
The previous hard-coded methodology page is preserved as
[historical Markdown](docs/methodology-overview.md).

Research setup depends on the selected toolchain; see `requirements-market.txt`
in `tools/` and the PyPSA-Eur runbook rather than installing it for frontend work.
Where available, run `python -m unittest discover -s tools -p 'test_*.py' -v`.
API keys are needed only for offline uncached research collection. Never commit
keys, `.env`, caches, solved networks or ignored generated research directories.

## GitHub Pages deployment

`.github/workflows/pages.yml` installs pinned Bun, uses the frozen lockfile, runs
lint/typecheck/tests/build plus Chromium desktop/mobile checks, uploads `dist/`, and deploys with the Pages Actions.
Pull requests verify without deploying. Pushes to `public-v1` deploy the previewed
public-v1 implementation; `main` deploys only after a reviewed merge. The workflow
can also be run manually. No automatic merge or history rewrite is performed.

Repository administrators must select **Settings → Pages → Source → GitHub
Actions** and permit `public-v1` (and later `main`) in the `github-pages`
environment's deployment branch rules. Pages Actions require `pages: write` and
`id-token: write`, and the organization must allow these Actions. Public Pages
from a private repository requires an eligible GitHub plan; confirm the site is
public rather than an access-controlled enterprise Pages site. Source visibility
is a separate choice and must not be changed automatically.

Vite and Router use `/grid-conductor/`. `tools/prepare-pages.ts` generates real
`index.html` entries for `/docs`, `/targets` and every research article, so direct
links work on Pages without server rewrites. `404.html` boots the router for
unknown URLs and displays a not-found page. All public artifact links/fetches use
the same base path. After deployment inspect the Actions result and open the
public URL without authentication; build success is insufficient.

See [public-v1 audit and verification](docs/public-v1-architecture.md) for the
server-boundary audit and deployment limitations.

## Fast coupled network prototype

The experimental worker solves paired network dispatch with chronological storage,
energy budgets, ramps and optional PTDF/RAM regions. Independent hours can be
solved in exact small blocks; linked cases retain chronology and resource guards.
The existing map screening model is unchanged. HiGHS 1.15.3 works under Bun and
in the production browser worker; the old Step-2 solver has not been replaced.

See [methods and input contract](docs/fast-network-model.md) and
[phased implementation plan](docs/fast-network-model-plan.md). Offline tools:
`export_fast_network.py`, `audit_fast_network.py`,
`check_fast_network_reference.py`; benchmark: `bun tools/benchmark_fast_network.ts`.
Python parity fixtures are generated offline with SciPy, then checked by Bun tests
without a Python dependency in frontend CI. Browser checks additionally run
`bun tools/network-browser-smoke.ts` against preview or the public URL.

Prepared 2025 inputs and sequential monthly solves exist offline. A certified
annual network comparison remains blocked by inventory-coordination validation
and the unfinished annual coordinator; the annual solved baseline and publication
manifest are not ready. Do not infer them from dispatch
outputs or substitute analytical test fixtures for published research.

## Daily market simulation research

The separate offline daily model uses simple, explicit bids for each resource,
clears 24 hourly UTC periods at a time, and carries inventories into the next day.
It supports transmission, hydro, batteries, solar and wind through the same paired
investment schema as the linked perfect-foresight benchmark. See
[simple resource bidding](docs/simple-resource-bidding.md) for results,
forecast assumptions, numerical checks and limitations. Producer:
`tools/simple_daily_market.py`; saved-witness replay and optional independent
native checks: `tools/audit_simple_daily_market.py`. Defaults:
`config/simple-bidding/defaults.json`. The earlier optimisation-based operator
policy remains a separate incomplete diagnostic, with failed annual receipts.
These experiments do not replace the public
workbench solver or certify an annual optimum, actual market bids or investments.
