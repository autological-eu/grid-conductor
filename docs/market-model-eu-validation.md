# European ENTSO-E input and baseline status

Status: **blocked_input_quality**. The previous 715-hour European dispatch is a legacy experiment and must not be used for opportunity rankings.

## Reproducible pipeline

1. `python tools/eu_zones.py` writes the versioned-in-code geographic registry to the local data directory.
2. `python tools/build_eu_market.py --month 2026-08 --output data/eu-market/bank-2026-08-v2.json` collects ENTSO-E API data, reusing raw responses after checking their request and content hashes. Set ENTSOE_API_KEY in the process environment for uncached requests. Never commit credentials.
3. `python tools/validate_eu_market.py --bank data/eu-market/bank-2026-08-v2.json` publishes coverage, historical balances and the baseline decision under public/research. Assembly and dispatch run only after the input gate passes.

## Current August result

- 33 modelled bidding zones, including separate SE1–SE4; the registry remains a first-pass topology, not a certified exhaustive European network.
- 146 directed physical-flow series; 66 published directed estimated-NTC series, including exterior connections.
- 319 successful API responses in provenance. Other requests returned acknowledgements rather than the requested data document. This does not prove the data does not exist under another valid area or endpoint.
- No synthetic capacities or opposite-direction substitutions.
- Full window: 744 UTC hours, 2026-08-01 inclusive to 2026-09-01 exclusive. No shortened common window or annualisation.
- 180 input-gate issues: 70 incomplete internal capacity series, 12 incomplete flow series, 58 incomplete generation series, 3 incomplete load series, 14 incomplete charging series, 22 historical balance failures and one unresolved generation geography (DE-LU versus Germany).
- European dispatch **not run** for these corrected inputs. See the generated JSON for authoritative issue counts and series-level details.

The earlier 1.53 TWh unmet-demand result belonged to the defective assembly. It represented approximately 0.81% of that model's demand, not 0.07%; it is not evidence of a historical electricity shortage.

## Observation and reconciliation policy

A price, load, generation or flow hour requires all four quarter-hour observations. Complete-hour values are means in EUR/MWh or MW; MW multiplied by one hour gives MWh. Explicit zero remains zero; missing remains null. A03 step blocks are expanded according to their published validity intervals, up to the next change or period end. This is decoding, not imputation. Missing A01 points and explicit missing blocks remain unknown; no interpolation or zero fill. Required quantity gaps block assembly; missing validation prices neither create shortages nor truncate physical inputs.

Generation and charging are collected independently of load. Demand, prices and borders use exact bidding-zone domains. Different generation domains are recorded and block acceptance pending a documented reconciliation. Reported B10/B25 storage discharge minus charging is included both in historical balance and as fixed net injection in dispatch; it is not dispatchable fuel supply. Absent storage/fuel categories are not proof of zero installed capacity; the report discloses this source-coverage limitation.

For each zone and hour, residual = reported generation + imports - exports - charging - load. Residuals are computed only where every included series is observed. The initial gate requires complete required quantities and sum(abs(residual))/sum(load) <= 5% in every zone. This threshold is a provisional data-quality screen, not validation of estimated offers. No residual is silently converted into generation.

A61 provides estimated NTC for the requested day-ahead horizon. It is neither a physical line rating nor a complete set of flow-based market constraints. Both directions are required. Missing CORE constraints block this transport approximation; observed flow is never used to manufacture capacity. Even complete A61 inputs would not make this an exact auction replay.

## Baseline validation repairs

The FR–CH validator now uses ENTSO-E A44 prices, aligns observations before excluding unserved hours, slices held-out generation by date, sums thermal offer bands before comparison, actually evaluates reservoir hydro, and treats missing/nonfinite metrics as failures. The naive price benchmark is fitted on the calibration slice, not the held-out slice. JSON contains no NaN values. Partially covered generator emissions no longer appear as complete totals.

The rerun remains experimental_not_validated: P1, P2, P3 and P4 all fail. Held-out flow MAE is about 800 MW and model unmet demand is about 4,190 MWh. These are model diagnostics, not measured historical shortages. The global hydro budget and observed-output availability proxies make this an ex-post diagnostic split, not an independent predictive test.

## Next work

Resolve exact topology/domain definitions and API coverage first, including the Italian zone registry and Germany/Luxembourg generation reconciliation. Investigate incomplete quantity series without assuming missing means zero. Obtain appropriate historical market constraints, or define a clearly bounded experiment with fixed exterior exchanges. Rerun the same gates before fitting supply assumptions or publishing paired-border benefits. Annual opportunity remains null.

## Primary references

- [ENTSO-E document types](https://transparencyplatform.zendesk.com/hc/en-us/articles/15857043092756-DocumentType): A61 is estimated net transfer capacity.
- [Svenska kraftnät day-ahead market](https://www.svk.se/om-kraftsystemet/om-elmarknaden/dagen-fore-marknaden--fysisk-handel-med-el/): separate Swedish bidding zones.

## Older-month comparison and price decoding

January 2026 has now been compared using the same 33-zone registry, endpoints and quality gates. Its reports are stored under public/research/january-2026, separately from August. A more complete older month would be useful for the first baseline, but January-only benefits cannot be multiplied by twelve to estimate annual opportunity.

During this comparison, raw A44 responses revealed A03 block encoding. The former price parser omitted unchanged-price intervals; expanding the published blocks restored complete August price coverage in 32 of 33 modelled zones after decoding (also unchanged after intraday filtering). Intraday (A07 contract) series are now excluded even when returned alongside day-ahead prices. Highest reported day-ahead classification sequence is retained as an explicit selection convention, not interpreted as a document revision number.

Reference: [ENTSO-E A01 versus A03 curves](https://transparencyplatform.zendesk.com/hc/en-us/articles/30262342482961-CurveType-A01-vs-CurveType-A03).

### Completed January versus August comparison

Both windows contain 744 UTC hours. Complete series under identical rules:

| Input | January 2026 | August 2026 |
|---|---:|---:|
| Day-ahead prices | 32 / 33 zones | 32 / 33 zones |
| Demand | 32 / 33 zones | 30 / 33 zones |
| Reported generation by fuel | 303 / 352 series | 294 / 352 series |
| Directed physical flows | 144 / 154 expected series | 142 / 154 expected series |
| Directed internal estimated NTC | 32 / 102 expected series | 32 / 102 expected series |
| Full-month balance gate | 12 / 33 zones | 11 / 33 zones |

January has somewhat better demand and generation coverage. Charging coverage is worse (66.5% of reported series-hours versus 72.5%; the reported category count differs). The unchanged NTC coverage and geography problems remain the principal blockers. Neither month passes the input gate and neither corrected European dataset has been dispatched. These comparisons do not establish that reporting delay caused the differences.

Recommendation: retain January as the winter baseline candidate and August as a summer cross-check while resolving the shared constraints and geography problems. Use a full-year dataset for annual opportunity, never January multiplied by twelve. Machine-readable comparison: public/research/eu-month-comparison.json.

## JAO extension

The A61-only coverage figures above remain a record of that endpoint. The pipeline now retrieves Core and Nordic flow-based domains from JAO as a separate network representation. See jao-network-integration.md and public/research/network-evidence-coverage.json. Publication availability is not dispatch readiness; virtual-hub and long-term-rights integration remains necessary before replacing the bilateral network in a real-data solve.
