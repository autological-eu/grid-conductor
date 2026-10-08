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

## Reconciliation experiments

A reproducible follow-up, `tools/reconcile_jao_2025.py`, rehashed the cached
auxiliary responses and tested two hypotheses without changing published RAM,
PTDF coefficients or positions. These are diagnostics, not accepted market rules.

| Published position UTC | Direct violation MW | Global sign-flip violation MW | FB/LTA hull hypothesis |
| --- | ---: | ---: | --- |
| 15 January 12:00 | 141.574 | 21.771 | infeasible |
| 15 July 12:00 | 0.000 | 807.762 | feasible; zero LTA weight |
| 15 December 12:00 | 22.210 | 912.798 | infeasible |
| 15 December 12:15 | 27.322 | 861.347 | infeasible |
| 15 December 12:30 | 29.914 | 848.441 | infeasible |
| 15 December 12:45 | 27.612 | 854.590 | infeasible |

A global sign flip still fails January and substantially worsens July/December.
It therefore cannot explain these samples by itself.

The second experiment asks whether observed net positions can be expressed as
`n = y + B b`, where `y` belongs to a scaled final flow-based domain and `b`
is a scaled directed LTA border-flow vector. Specifically, it imposes
`A y ≤ λ RAM`, `0 ≤ b ≤ (1 − λ) LTA`, `sum(y) = 0`, and `0 ≤ λ ≤ 1`.
`B` maps directed border flows to net exports. The objective maximises `λ`.
All published PTDF hubs remain in the problem. Unknown positive-capacity borders
are rejected. The single hourly LTA table is assumed applicable to December's
four position intervals; this assumption needs confirmation from interval metadata.

This simplified convex-hull hypothesis omits allocation constraints, BEX
restrictions, nominations and explicit virtual-connector coupling. It is **not**
a verified implementation of Core LTA inclusion. HiGHS reports infeasibility
(status 2) for January and all four December positions. July's witness has
`λ = 1`, with independent equality/inequality residuals below `1e−6 MW`.
These results reject this particular explanation; they do not establish the
cause of the discrepancy or rule out the correctly specified inclusion mechanism.

[Download the reconciliation results and July witness](../../research/jao-2025-reconciliation.json).
The next reconciliation step is to establish the exact published position
quantity, applicable domain version, LTA inclusion rule and connector mappings
from regional methodology, then replay that formulation against these same hours.
Do not calibrate synthetic bids to compensate for unresolved network semantics.

## How PyPSA can help

There are two useful routes, with different meanings:

1. **Commercial-domain clearing:** use PyPSA's zonal energy balances and native
   optimisation model, then add audited JAO PTDF/RAM and auxiliary inequalities
   through Linopy. Explicit variables must map physical bidding-zone net exports
   and connector flows to every published hub. LTA/allocation rules and external
   interfaces must be implemented before the failed samples can validate this
   route. Adding ordinary physical lines does not repair missing market rules.
2. **Our own physical constraint model:** use the PyPSA-Eur grid as a backbone,
   calculate nodal PTDFs and aggregate them to zones using declared generation
   shift keys (GSKs). Choose monitored elements, contingency cases, ratings,
   reference flows and reliability margins explicitly. For a chosen convention,
   `RAM = allowed monitored flow − reference flow`; signs and the base-point
   definition must be consistent with zonal net-position changes. JAO can inform
   comparisons of published sensitivities and headroom, but cannot silently
   supply missing physical assumptions.

The physical route needs a dated topology, transformer/link treatment,
zone-to-node mapping and credible 2025 ratings/outages. GSKs depend on how
incremental production is distributed within each zone; installed capacity alone
is insufficient. Validate nodal-to-zonal sensitivities against small native
PyPSA perturbations, replay feasibility and contingency limits, and assess
sensitivity to GSKs and margins. Label its output **model-derived physical
constraints**, with provenance and limitations. It would support scenario
research, but would not reproduce the actual commercial day-ahead domain or
certify EUPHEMIA prices. Neither route has been executed as a European solve here.

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
