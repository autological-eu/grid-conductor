# Monthly weather preparation with bounded disk growth

The 2025 model still covers all 8,760 hours and the original European weather
grid. Only preprocessing is monthly. Dispatch, storage and hydro remain linked
across the full year. No sampling of representative days or reduction in countries.

## What is stored

`tools/monthly_weather.py` downloads one month of ERA5 wind, irradiation and
temperature into an owned raw directory. Atlite converts the weather to per-cell
generation factors for every turbine/panel configuration used by PyPSA-Eur.
These nonlinear conversions are retained as float32 compressed NetCDF; original
weather is not retained after successful verification. The reduction is less
aggressive than storing only regional averages, but preserves PyPSA-Eur's annual
capacity-factor weighting, resource classes, exclusion matrices and regional
aggregation. Different technology assumptions require rebuilding the affected
conversions; the loader rejects unknown parameter combinations.

The existing annual hydro runoff cutout (~113 MiB) is retained separately. Hydro
normalisation is still performed over the year. The compact wind/solar loader
does not pretend to contain runoff, temperatures or data for sector coupling or
dynamic line rating. This workflow is electricity-only with dynamic line rating
disabled.

## Disk monitor and recovery

The supervisor allows at most 10 GiB of weather-work storage and stops workers
at 9 GiB, leaving 1 GiB reaction margin. It also stops below 3 GiB free physical
disk space. This is a sampled process guard, not a filesystem quota: it checks
every two seconds. Temporary ERA5 files are explicitly stored inside the watched
directory. Concurrent physical disk consumption can also trigger a safe stop.
One pipeline lock prevents two supervised downloaders running together.

Only a verified batch's raw directory is recursively removed. Cleanup resolves
the absolute path, requires it to be a strict child of the owned weather folder,
and rejects symbolic-link cleanup targets. A failure retains the batch for
diagnosis/restart. No user-folder or package-cache cleanup is performed.

Each receipt records exact hour coverage, conversion settings, the atlite version,
raw and compact SHA-256 hashes, and output bytes. Verification reopens the file,
checks every hour and finite values, and compares sampled converted values within
float32 tolerance. Resuming rechecks hashes and configuration before skipping work.

The annual assembler requires all 12 receipts, identical settings, identical grids
and exact annual timestamps. Monthly profiles remain restart checkpoints. A
verified annual file is linked into upstream's cutout directory without duplicating
its storage. Existing raw annual weather is not requested by the compact config.

## Commands

Run inside the pinned PyPSA-Eur pixi environment, from grid-conductor:

```text
python tools/install_compact_weather_adapter.py
python tools/monthly_weather.py --months 1
python tools/monthly_weather.py
python tools/monthly_weather.py --assemble
python tools/monthly_weather.py --publish
python tools/build_pypsa_network.py --config config/pypsa-eur/full-year.yaml
```

`bash tools/run_monthly_weather.sh` waits for any existing supervised batch, resumes
all twelve months, then assembles and publishes the verified annual file. It logs
to `data/pypsa-eur/monthly-weather/pipeline.log` and stops on failure. It does not
start the model solve automatically: solver disk/memory and demand readiness still
need to pass their own checks.

The first command applies a tracked adapter to the local pinned upstream checkout.
Regional renewable calculations continue through upstream's original code. Raw
atlite cutouts retain their original loader. A missing compact file fails with an
instruction to run preprocessing, rather than silently triggering a large download.

The initial month establishes measured storage requirements; the 10 GiB target is
not a claim that the full model or all dependencies occupy only 10 GiB. Baseline
solver temporary files and outputs need a separate resource check before dispatch.
Progress is recorded in `data/pypsa-eur/monthly-weather/status.json` and individual
month logs. No opportunity estimate is published merely because weather preparation
has completed; demand and market validation remain separate gates.
