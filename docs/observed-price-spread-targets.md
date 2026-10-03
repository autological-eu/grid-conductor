The map and sidebar display **annual scheduled-exchange value, floored at zero**: max(0, annual signed total). Negative hours still reduce the annual total; we do not clip individual hours. Signed research artifacts remain unchanged. This display convention does not establish actual TSO congestion income or investment welfare.

# Observed annual price-spread targets

The current Stage-1 sidebar shows **mean absolute price spread (€/MWh)** and **annual signed congestion rent (M€)**. The map colours use the annual signed total floored at zero; mean absolute spread is secondary. The accumulated spread described below remains an intermediate used to calculate the mean by dividing by covered hours.

Congestion rent sums both directed scheduled exchange × signed destination-minus-origin price spread × interval duration, including negative contributions. These are ENTSO-E scheduled exchanges, not metered physical flows. Missing rent inputs are unavailable, not zero. Mean spread requires matching directional coverage counts; interval-mask identity cannot be audited from these aggregate-only artifacts. Scenario welfare remains separate.

The workbench now uses accumulated absolute price spread as its map headline:

$$A_{AB}=\sum_{t\in observed}|P_{B,t}-P_{A,t}|\Delta t.$$

Units are **€/MW-year**, equivalently €/MWh × hours accumulated over 2025. This is neither project revenue nor recoverable welfare. There is no assumed cable size, price response, slope, event threshold or investment cost in this metric. Opposite directions do not cancel.

The archived screening publishes a 500 MW fixed-price ladder in each direction. Dividing each by 500 MW and undoing its million-euro display scale, then adding both directions, recovers this metric. The original **joint known-price and scheduled-flow coverage mask remains**. It is a covered-period sum, not an extrapolation of missing intervals. The workbench retains its existing eligible candidate set; this update does not establish complete coverage of every European zone pair.

Scenario evaluations retain their separate experimental welfare methodology. Their bound is labelled separately in the sidebar; it no longer defines the map colour or headline.

## Hourly details

Select a corridor and open **Hourly price difference** in the sidebar. The plot shows signed hourly mean prices, destination minus origin, and observed-hour coverage. Missing observations break the line.

France–Italy North uses a bundled historical trace, covering 8,759 of 8,760 UTC hours. Other zones use bundled published prices when available; there are no live third-party browser requests. Unsupported zones, rate limits or browser restrictions produce an explicit error; they do not produce a synthetic trace. All 68 displayed corridors now have static two-zone traces (39 zones), with at least 8,758 jointly observed hours out of 8,760. A published manifest identifies missing intervals and their source. The Energy-Charts provider permits republication for only a subset. The offline ENTSO-E collector fills remaining zones directly from A44; the coverage manifest records every source, monthly receipt and failed collection month.

The plot is a price-only cross-source check. It does not apply the archived scheduled-flow mask. Its sum of absolute **hourly mean** spreads can differ from the map's **quarter-hour absolute** sum, especially where direction changes within an hour. Source attribution is Energy-Charts / SMARD, CC BY 4.0 as declared by the API; the price trace is not fetched directly from the original ENTSO-E cache.

The hourly pop-out draws both zones’ prices and shades between them. Its month selector allows close inspection without replacing the full-year view. Shading is price separation, not flow-weighted rent. Null hours break the shaded area as well as the price lines.

Reproduce static traces with `tools/publish_zone_price_traces.py` for openly licensed public-provider zones, then `tools/publish_entsoe_zone_prices.py` for the remainder using `ENTSOE_API_KEY` offline. Credentials and raw response caches stay in ignored `data/price-trace/`; only hourly values and non-secret provenance ship. No modelling dispatch is used to substitute for observed prices.
