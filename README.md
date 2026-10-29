# Grid Conductor — Alpha

Grid Conductor is an experimental European electricity bottleneck and scenario workbench. The [public app](https://autological-eu.github.io/grid-conductor/) maps 2025 ENTSO-E price separation and estimated congestion rent. Its browser-local line and battery scenarios use a two-zone screening model. The European dispatch models below are offline research and have **not** been integrated into that scenario engine.

## Named 2025 research baselines

| Name | Method | Corrected ENTSO-E hourly price MAE | Hourly country/technology generation MAE |
|---|---|---:|---:|
| `fast_dispatch_only` | Solar-anchor offers, one annual joint LP clear | 26.795 EUR/MWh | 0.633 GW |
| `mixed_curve_fitting` **active** | Twelve monthly technology/zone/local-hour bid fits, then one annual joint LP clear | 25.051 EUR/MWh | 0.552 GW |

Both comparisons use the same 2025 price coverage and original physical LP network. The active 8,760-hour LP replay passed independent primal, dual and no-emergency checks. The monthly fitting is retrospective and price-conditioned; these numbers are **in-sample reconstruction scores**, not forward-price or investment-value validation. Mixed offers prevent a unique technology allocation. Fixed hydro does not respond to an investment.

The [baseline catalog](baselines/catalog.json) resolves these names to the archived and active manifests. See [fast dispatch](baselines/fast_dispatch_only/README.md), [mixed curve fitting](baselines/mixed_curve_fitting/README.md), and the [annual comparison](research/observed-root-monthly-baseline-2025.md) for scripts, hashes, provenance and limitations. Source-hashed producer scripts remain at their original `tools/` paths. Large source extracts, annual witnesses and fitted curves live in ignored `data/` directories, so a Git checkout alone cannot reproduce the numeric results.

## Repository guide

- [PRODUCT.md](PRODUCT.md): product requirements and acceptance gates.
- [TASKS.md](TASKS.md): current evidence, blockers and next work.
- [AGENTS.md](AGENTS.md): operational rules for research and publication.
- [Workbench methodology](docs/workbench-methodology.md): the current public app's data and equations.
- [Baseline decision](research/baseline-decision-2026-10-23.md): why the preceding control was retained.

The accepted research baseline does not change the public app. Before scenario use, investment responses need chronology, storage, flow, feasibility and independent evaluation checks. Price and generation improvements alone do not establish EUPHEMIA equivalence.

## Development

Use Bun 1.4.2:

```sh
bun install --frozen-lockfile
bun run dev
bun run lint
bun run typecheck
bun run test
bun run build
```

Check research artifact pointers with the pinned scientific environment:

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python tools/check_baseline_catalog.py
```

The public site is built by `.github/workflows/pages.yml`. Automatic check-ins are disabled. This cleanup keeps the two named baselines and the existing public site; retired experiments remain available in Git history.
