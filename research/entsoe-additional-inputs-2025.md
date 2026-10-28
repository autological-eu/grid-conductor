# Additional ENTSO-E evidence for the 2025 zonal model

## Scope and result

On 28 October 2026, we retrieved four annual ENTSO-E source classes for the
44 of 48 retained model zones with a justified EIC mapping. We also collected
monthly generation-unit outage notices, a four-corridor grid-outage pilot and
day-ahead directional transfer capacity for the 90 mapped border pairs. The
downloaded sources are **diagnostic evidence**, not yet replacement dispatch
constraints. The current baseline and its price scores have not changed.

| ENTSO-E API product | Source-covered | Missing response | What it can check |
| --- | ---: | ---: | --- |
| A65/A01 day-ahead load forecast | 41 / 44 zones | 3 | Demand forecast versus fixed observed demand |
| A69/A01 day-ahead solar/wind generation forecast | 41 / 44 | 3 | Expected weather-linked output versus model and actual generation |
| A71/A33 year-ahead installed generation capacity per unit | 41 / 44 | 3 | Unit identity and capacity inventory |
| A72 reservoir filling | 31 / 44 | 13 | Reported storage trajectory, subject to scope matching |
| A80 generation-unit outage | 440 / 528 zone-months with notices | 88 | Reported remaining capacity during outages |
| A61/A01 day-ahead transfer capacity | 58 / 180 directions complete, 10 partial | 112 | Bilateral capacity where this product applies |
| A78 grid-outage pilot | 82 / 96 border-months with notices | 14 | Grid unavailability diagnostics on four corridors |

The 44 mapped zones exclude `FR-COR`, `IE-SEM`, `IT-CALA` and `XK`; no nearby
zone was silently substituted. A61 covers 29 of the 90 queried pairs in both
directions for all 2025 quarter-hours. The A78 pilot covers `FR–BE`,
`DE-LU–DK1`, `NO2–DK1` and `SE2–SE3`, both directions. An absent document is
**unknown coverage**, not zero forecast, no outage, or zero capacity.

## Hourly compilation and checks

The A65 and A69 documents were parsed by declared UTC intervals, resolution,
curve type, business type and technology. A 15-minute, 30-minute or hourly
source contributes an hourly MW value only if all four quarter-hour slots are
present. Missing slots remain `NaN`. The 82 compiled zone-product files each
have 8,760 hourly positions. Among returned sources, 34/41 load series have
all 8,760 hours; only 18/41 renewable products have all their reported
technology series complete. For example, `DE-LU` solar and onshore wind have
8,759 covered hours, while its offshore wind has 8,760. Technologies absent
from a document were **not** synthesized as zero. Forecast generation is an
expected generation quantity, not the physical renewable availability or a
capacity ceiling.

The independent replay verified all 176 annual raw documents against the
request and SHA-256 receipts, XML type, zone identity and series count. It
replayed all 528 A80 zone-month pages (63,057 document appearances), 96 A78
border-months (3,117 appearances), and all 180 A61 directional XML responses
and quarter-hour timestamps. Those outage counts are repeated appearances of
documents across queried months and revisions; they are **not** counts of
distinct events or curtailed MW. At least 4,184 A80 document appearances have
a creation timestamp after the queried month ended. Thus a current API extract
cannot be assumed to represent the notices an auction participant saw at the
time. All source and audit receipts stay in the ignored
`data/eu-market/additional-2025` and `data/eu-market/flow-refresh-2025`
directories; no large raw response was added to Git.

## Meaning and model use

ENTSO-E's outage field reports the **remaining available capacity during the
event**. A unit-specific derating requires a verified nameplate/unit match,
the event's valid interval and a publication-time view; simply subtracting
the reported MW from model capacity would reverse its meaning. Reporting
thresholds also mean a missing notice is no proof of full availability.

A61 is bilateral day-ahead capacity where returned. It does not reconstruct a
CORE flow-based market domain, so its many missing corridors cannot be filled
with zero or promoted over the existing JAO/physical constraint sources. A78
notices describe unavailable grid assets, not an hourly numeric border limit.
The separately audited A09/A01 commercial exchanges and A11 physical flows
remain distinct observations (see [flow refresh](entsoe-flow-refresh-2025.md)).

Next, compare A65 against observed/model load and A69 against actual and model
solar/wind on matched hours; audit A71 unit identifiers against the model fleet;
reconstruct A80 revisions and remaining capacity only for matched units; and
test A61 against JAO on compatible non-CORE borders. Only source-backed,
independently replayed changes should enter a frozen-bid diagnostic before any
same-method refit. These data alone do not validate investment scenarios or
resolve Nordic reservoir geography.

Source semantics: [ENTSO-E Transparency API implementation guide](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fweb+api%2FRestfulAPI_IG.pdf)
and [Detailed Data Descriptions](https://www.entsoe.eu/fileadmin/user_upload/_library/resources/Transparency/02_MoP%20Ref02%20-%20DDD_V2R5.pdf).
