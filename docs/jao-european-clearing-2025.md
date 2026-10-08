# JAO constraints for European synthetic market clearing — 2025 investigation

## Summary

Live bounded queries retrieved presolved/nonredundant final flow-based constraints
for all six fixed 2025 sample hours: Core and Nordic at noon UTC on 15 January,
15 July and 15 December. JAO is a usable source of commercial network-domain
inputs. It is **not yet dispatch-ready in our European clearing model**.

Core July published net positions pass the simple PTDF × net-position ≤ RAM
check at 0.1 MW tolerance. Core January and December fail that check, by up to
141.574 MW and 29.914 MW respectively. Nordic's probed `netPos` endpoint returned
zero rows; those checks are **unavailable**, not successful or failed solves.
No constraints were relaxed to make these observations pass.

This is six sampled hours, not a full-year coverage audit. No European dispatch
or investment calculation was run. Previous 2026 sample evidence stays separate.

## What was retrieved and checked

The existing collector hashes/compresses raw responses under ignored `data/jao`.
Core requests require `presolved=true`; Nordic uses `nonRedundant=true`. Pagination
counts, offsets and unique row identities are checked. Every PTDF hub, including
virtual hubs, is retained. Negative RAM remains negative; it is not clipped.
Auxiliary endpoint responses are separately hashed. The reproducible probe is
`tools/probe_jao_2025.py` with two bounded concurrent collection tasks.

| Region | UTC start | Constraints in hour | Published domain timestamps | PTDF hubs | Position check | Worst violation MW |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Core | 2025-01-15T12:00Z | 126 | 1 | 14 | failed_simple_ptdf_ram_check | 141.574 |
| Core | 2025-07-15T12:00Z | 129 | 1 | 14 | passed | 0.000 |
| Core | 2025-12-15T12:00Z | 91 | 1 | 14 | failed_simple_ptdf_ram_check | 29.914 |
| Nordic | 2025-01-15T12:00Z | 142 | 1 | 31 | not_available | — |
| Nordic | 2025-07-15T12:00Z | 117 | 1 | 31 | not_available | — |
| Nordic | 2025-12-15T12:00Z | 500 | 4 | 31 | not_available | — |

Core domain samples have hourly timestamps. Published Core net positions were
hourly in January/July and quarter-hourly in December. The hourly December domain
was checked against each of its four published positions. Nordic domain samples
were hourly in January/July but quarter-hourly in December. **Do not apply the
existing January-2026 quarter-hour assumption to the whole Nordic 2025 year.**
Use actual interval metadata and validate transition dates before annual assembly.

![Sample constraint counts and Core residuals](../../research/jao-2025-samples.svg)

## Why failed checks matter

January's worst sampled row is `Ensdorf - Vigy VIGY2 S`, opposite direction:
RAM 376 MW versus approximately 517.574 MW from the published hub positions.
The summed published net positions balance to roundoff, so simply enforcing
regional balance does not resolve this residual. December similarly fails across
all four checked quarter-hours. July passes, but passing one hour does not certify
the formulation across the year.

These are failures of the **simple final-domain interpretation**, not evidence
that JAO or the market clearing was wrong. Long-term-right inclusion, allocation
rules, published quantity definitions and final-domain/position consistency need
investigation. We have not established which explains the residuals. Do not add
an unexplained margin, drop offending rows or call the domain validated.

## Auxiliary inputs and virtual hubs

Core returned `allocationConstraint`, `bexRestrictions`, `lta` and `ltn` data
for each sample. Receiving these tables is not reconstructing their mathematics.
Core retains ALBE and ALDE alongside the physical market hubs; Nordic includes
many connector-specific hubs. They cannot be dropped, set to zero or assigned
independent free generation/load. They need explicit connector/flow relationships
under the published market formulation, including bounds and sign conventions.

Nordic `netPos` and `allocationConstraint` returned zero rows in these probes;
`bexRestrictions`, `lta` and `ltn` returned HTTP 404. This describes the probed
endpoints/windows, not proof that equivalent Nordic data is unavailable elsewhere.
Identify the correct regional publication tables before accepting Nordic inputs.

## Europe-wide formulation

The European model needs one set of physical bidding-zone energy balances and
explicit representations of commercial flow-based regions and external borders.
For each regional domain, retain its published hub vector and impose each
PTDF/RAM inequality with an audited mapping from physical net exports and
connector flows to that vector. Enforce the appropriate regional balance and
connector conservation; do not infer these mappings from hub names alone.

Use verified transfer-capacity constraints for borders outside each flow-based
region and the interfaces between regions. Do not add independent internal
bilateral limits on top of a flow-based region by default. Conversely, physical
PyPSA-Eur line limits are not automatically the day-ahead capacity domain. Keep
physical-grid sensitivity cases explicitly separate.

The existing `market_model.py` supports generic PTDF/RAM regions with complete
hub coefficients and regional balance, and rejects overlapping regions, unmapped
hubs and internal bilateral edges. Its analytical tests verify congestion and
shadow prices. **It does not reconstruct JAO virtual-hub coupling or LTA inclusion.**
The six samples therefore do not bypass the compiler's coverage and physics gates.

## Implementation sequence

1. Resolve Core January/December residuals with documented position definitions,
   long-term-right inclusion and allocation constraints. Recheck the actual domains
   against published outcomes without tuning tolerance or replacing RAM.
2. Find Nordic publication endpoints/definitions for positions and connector
   variables, then test historical hourly and quarter-hour transitions.
3. Implement a versioned, explicit physical-zone/virtual-hub mapping and auxiliary
   constraint compiler. Reject unknown hubs and incomplete required tables.
4. Test smaller coupled synthetic cases against independent native formulations,
   including cross-region connectors, negative RAM and binding auxiliary restrictions.
5. Collect the verified 2025 calendar in resumable daily batches with source hashes,
   interval coverage and missing-data diagnostics. Samples do not establish this gate.
6. Complete commercial-capacity coverage outside Core/Nordic and confirm European
   accounting, then run coupled synthetic bids with demand and chronological storage.
7. Publish numerical and observed-data comparisons and paired investment cases.
   Preserve original availability, existing annual gates and the retained reference.

## Data, sources and limitations

- [Historical probe receipts and checks](../../research/jao-2025-probes.json)
- [JAO publication tool](https://publicationtool.jao.eu/)
- [Synthetic coupled-clearing plan](synthetic-zonal-clearing-plan.md)

Public output contains compact coverage/check summaries and request provenance,
not raw constraint archives or credentials. HTTP access and data availability
were tested for these requests; full-year availability and complete allocation
semantics remain unverified. Core January and December failed the initial data
check; Nordic position checks remain unavailable. No annual welfare, dispatch
validation or EUPHEMIA reconstruction is claimed.
