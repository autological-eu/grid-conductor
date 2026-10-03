# Observed annual price-spread targets

The workbench now uses accumulated absolute price spread as its map headline:

$$A_{AB}=\sum_{t\in observed}|P_{B,t}-P_{A,t}|\Delta t.$$

Units are **€/MW-year**, equivalently €/MWh × hours accumulated over 2025. This is neither project revenue nor recoverable welfare. There is no assumed cable size, price response, slope, event threshold or investment cost in this metric. Opposite directions do not cancel.

The archived screening publishes a 500 MW fixed-price ladder in each direction. Dividing each by 500 MW and undoing its million-euro display scale, then adding both directions, recovers this metric. The original **joint known-price and scheduled-flow coverage mask remains**. It is a covered-period sum, not an extrapolation of missing intervals. The workbench retains its existing eligible candidate set; this update does not establish complete coverage of every European zone pair.

Scenario evaluations retain their separate experimental welfare methodology. Their bound is labelled separately in the sidebar; it no longer defines the map colour or headline.

## Hourly details

Select a corridor and open **Hourly price difference** in the sidebar. The plot shows signed hourly mean prices, destination minus origin, and observed-hour coverage. Missing observations break the line.

France–Italy North uses a bundled historical trace, covering 8,759 of 8,760 UTC hours. Other zones request public Energy-Charts historical prices on demand. Unsupported zones, rate limits or browser restrictions produce an explicit error; they do not produce a synthetic trace. Broader bundled trace coverage is still needed for consistent offline access.

The plot is a price-only cross-source check. It does not apply the archived scheduled-flow mask. Its sum of absolute **hourly mean** spreads can differ from the map's **quarter-hour absolute** sum, especially where direction changes within an hour. Source attribution is Energy-Charts / SMARD, CC BY 4.0 as declared by the API; the price trace is not fetched directly from the original ENTSO-E cache.
