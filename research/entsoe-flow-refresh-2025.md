# Fresh 2025 ENTSO-E border-flow download

On 27 October 2026 we queried the ENTSO-E Transparency API for two **separate**
directional datasets over 1 January–1 January 2026 UTC:

- `A11`, published physical flow (`businessType=A66`).
- `A09`, scheduled commercial exchange restricted to day-ahead contract `A01`
  (`businessType=A06`). Other A09 contract classes are excluded.

The collector uses the reviewed EIC registry plus the 95 corridor pairs in the
retained 48-zone network snapshot. It plans 90 pairs (180 directions): 86 mapped
model corridors and four additional older-registry pairs. Nine model corridors
cannot be queried without a justified bidding-zone code for `FR-COR`, `IE-SEM`,
`IT-CALA` or `XK`. No country or neighboring zone code was substituted.

| Source | Full directions | Partial directions | No quantity data | Model pairs with both directions full |
| --- | ---: | ---: | ---: | ---: |
| Physical A11 | 139 | 23 | 18 | 69 / 95 |
| Day-ahead commercial A09/A01 | 128 | 34 | 18 | 64 / 95 |

The remaining modeled pairs include nine unmapped and six mapped pairs with an
unavailable direction in **each** source; eleven A11 and sixteen A09 model pairs
have two returned directions but at least one time gap. These counts describe
source coverage, not modeled flow accuracy. An unavailable document or interval
is **missing**, never zero. A full 2025 quarter-hour direction has 35,040 samples.
Examples of A09 gaps: `SE1>SE2` lacks the 24 hours starting 29 September 22:00
UTC; `GB>IE` ends after 1 October; `BG>GR` begins only in July. The present
registry's `IE` is not automatically the model's combined `IE-SEM` area.

The independent replay checks request metadata and raw SHA-256, XML document
and business/contract types, directed EICs, all parsed timestamps, bounds of
the UTC year, and exact quarter-hour counts. Its ignored local receipts are
`data/eu-market/flow-refresh-2025/{physical,day-ahead-commercial}-audit.json`;
raw XML and request receipts are ignored under that root. The key is read from
the environment or a Git-ignored local `.env` and is never saved in requests.

For historical **zonal market** comparisons, A09/A01 is the closer exchange
observation; A11 physical flow answers a different question. Neither source
supplies an investment scenario's flows. A changed line or supply fleet must be
cleared again under network constraints, and these observations can then score
the baseline flow errors only on covered, compatible corridors and hours.
Before fitting to A09, reconcile the remaining zone domains, market-coupling
scope, netting/direction convention, losses, and partial/missing intervals.
The downloaded observations do not validate or replace the model's JAO and
physical constraint assumptions by themselves.
