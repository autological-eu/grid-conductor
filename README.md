# Grid Conductor — Alpha website

`main` is the source branch for the [public Grid Conductor website](https://autological-eu.github.io/grid-conductor/). The Pages workflow builds, tests and deploys this branch. `research` holds the active European market-model experiments, source checks and retained baseline evidence; research commits run CI without deploying the website.

The alpha site maps 2025 observed cross-zonal price gaps and flow–price congestion-rent estimates. Its browser-local line and battery scenarios use a reduced two-zone screening model. The offline European research dispatch is not integrated into those scenario calculations. Scenario benefits and carbon figures are estimates, not validated investment returns.

The [workbench methodology](docs/workbench-methodology.md) documents the live model, sources and limitations. The [research baselines overview](docs/research-baselines-2025.md) links to the retained research evidence on `research`. The country explorer displays archived model comparisons with their own provenance.

## Local website checks

Use Bun 1.4.2:

```sh
bun install --frozen-lockfile
bun run lint
bun run typecheck
bun run test
python3 tools/check_zone_price_traces.py
python3 tools/check_public_assets.py
bun run build
```

The Pages workflow also runs browser interaction tests before and after deployment. Direct routes are prepared for GitHub Pages under `/grid-conductor/`. Scenarios are stored only in the browser.

Research development and model promotion happen on [`research`](https://github.com/autological-eu/grid-conductor/tree/research). Its `PRODUCT.md`, `TASKS.md` and `AGENTS.md` are the current project context. Large provider inputs and numerical witnesses stay outside Git.
