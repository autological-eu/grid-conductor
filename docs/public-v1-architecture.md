# Public-v1 architecture and server-boundary audit

## Runtime split

Bun is a development/build tool. Vite produces a static React 19 / TanStack
Router app. GitHub Pages serves files; no process, secret or database server is
required. Offline research tooling and published artifacts remain intact.

| Former boundary                                                    | Classification                                              | Public-v1 implementation                                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `step1.server.ts`, `listFastSummary`, summary API                  | Static data + deterministic adapter                         | Base-aware browser fetch of published screening JSON, unchanged summary adapter in `step1.ts`   |
| `fast-entsoe-lp.server.ts`, LP API                                 | Deterministic JavaScript                                    | `fast-entsoe-lp.ts`; unchanged cable trapezoid, battery LP, shadow-price re-solves and DWL caps |
| `workbench.server.ts` (`bun:sqlite`)                               | Scenario persistence                                        | Versioned IndexedDB abstraction in `workbench.ts`, atomic edits and evaluation writes           |
| `scenarios.functions.ts` Start handlers                            | CRUD/calculation orchestration                              | Validated ordinary async browser services; year/zone snapshots retained                         |
| ENTSO-E, ENTSO-E-flow and Electricity Maps server modules          | Secret-backed legacy collection, unused by active workbench | Removed from frontend; offline Python research collection remains                               |
| Start server/CSRF/error shell, Nitro, Lovable config and telemetry | Server/build infrastructure not needed for v1               | Removed; explicit Vite plugins and browser error boundary                                       |

No API credentials are shipped. No Python model runs in the browser. Neither
research methodology nor published JSON/CSV artifacts are replaced with demo data.

## Persistence and interpretation

Scenario IDs and intervention IDs are UUIDs. Directed target IDs, zones, year
window, parameters, cost and delivery assumptions are retained. Ordered unit
arrays and saved results belong to their scenario; deletion removes both. Changes
atomically clear results and set draft status. Evaluation writes compare the
scenario revision to prevent stale results after concurrent edits.

Scenarios persist after reopening on the same browser/origin. There is no cloud
sync or old SQLite migration; clearing site data removes them. Storage failures
are reported, not silently replaced with temporary in-memory persistence.

Only line/battery units are exposed. The two-node screening model aggregates
capacity, not detailed spatial or hourly dispatch. Climate outputs preserve the
original unsigned average-mix proxy but are labelled as estimates, not avoided
emissions. Data availability is not calibration/validation. The legacy
`npv_25y_meur` field is displayed as undiscounted benefit minus capex.

## Research publications

All top-level `docs/*.md` documents render through a reusable Markdown/GFM
component at `/docs/<slug>`. The research index links published machine-readable
artifacts to their role and known validation limitations. The former hard-coded
methodology is preserved in `methodology-overview.md` as a historical document.
Existing Python tooling, configuration, datasets and research warnings remain.

## Pages and verification

Vite, Router and static artifact URLs use `/grid-conductor/`. The build generates
HTML entries for `/docs`, `/targets` and every publication, with a 404 SPA shell
for unknown routes. CI installs pinned Bun with a frozen lockfile and verifies
lint, types, targeted tests, the static build and Chromium desktop/mobile checks
before uploading and deploying.

Local Chromium smoke checks passed at 1440 px and 390 px against a plain static
file server, covering map rendering/selection, research loading, local scenarios,
line/battery interventions, evaluation, removal, refresh persistence, direct routes
and horizontal overflow. A legacy comparison found exact parity for all 140
borders (700 matrix rows and 560 line/battery scenarios).

The test suite checks published annual DWL caps, exact cable integration, battery
cycle efficiency/shadow prices, annual units, persistent IDs/order, atomic edits,
concurrent writes, cascade deletion and stale evaluation rejection.

Deployment is not established until an Actions deployment succeeds and the URL
is opened without authentication. The repository remains private; public Pages
requires an eligible plan and public Pages settings. The connected integration
initially denied Pages settings access (403), so repository administration may
require manual action. See the pull request and completion report for observed
Actions/browser verification and outstanding deployment settings.

## Follow-up research and product work

- Validate hourly dispatch and marginal emissions separately before upgrading
  screening labels or making avoided-emissions claims.
- Scenario export/import and migration/versioning for future artifact years.
- Richer Markdown charts and article-to-workbench links.
- Hourly battery modelling, renewables/demand response and detailed spatial
  effects remain separate research extensions.
