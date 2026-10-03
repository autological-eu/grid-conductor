#!/usr/bin/env bash
# Foreground worker; use a named screen session to keep it alive after disconnect.
set -euo pipefail
GRID_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p -- "$GRID_ROOT/data/pypsa-eur/monthly-weather"
if [[ -f "$GRID_ROOT/data/pypsa-eur/.cdsapirc" ]]; then
  export CDSAPI_RC="$GRID_ROOT/data/pypsa-eur/.cdsapirc"
fi
cd -- "$GRID_ROOT/data/pypsa-eur/upstream"
exec ../bin/pixi run python "$GRID_ROOT/tools/monthly_weather.py" \
  --config "$GRID_ROOT/config/pypsa-eur/full-year.yaml" --wait-lock --finish \
  >> "$GRID_ROOT/data/pypsa-eur/monthly-weather/pipeline.log" 2>&1
