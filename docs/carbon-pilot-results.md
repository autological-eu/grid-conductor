# August 2026 carbon pilot: results

Run on 12 September 2026 using the ENTSO-E Transparency Platform directly.
Period: 1 August 00:00 UTC to 1 September 00:00 UTC, end exclusive.
Implementation: [method and reproduction instructions](carbon-pilot.md).

The download and calculation pipeline works across France, Germany and both
Danish bidding zones. It generates 2,976 hourly records; 2,912 have complete
reported primary-generation inputs. However, **none yet has full emission-factor
coverage**, so the pipeline correctly withholds a single full-grid intensity.

| Zone | Usable hours / 744 | Factor coverage of reported generation* | Pilot sensitivity means** | Electricity Maps mean** |
|---|---:|---:|---:|---:|
| France | 742 | 98.97% | 37.3–52.9 | 36.1 |
| Germany | 744 | 96.21% | 264.7–326.5 | 314.3 |
| Denmark west (DK1) | 682 | 97.35% | 79.9–131.5 | 89.7 |
| Denmark east (DK2) | 744 | 88.63% | 76.4–270.4 | 116.9 |

*Energy-weighted share during usable hours, relative to reported primary
generation, not an independently verified national generation total.

**gCO2e/kWh, arithmetic means of the same matched hourly observations for each
zone. Pilot range endpoints apply hypothetical factors of 0 and 1500 to
unsupported generation. They are not statistical confidence limits. Electricity
Maps measures consumption; the pilot measures reported primary production.
These numbers cannot establish accuracy or validation success. No matched
Electricity Maps observations were flagged estimated in the archived field.

## What the run revealed

- France has two unusable offshore-wind hours on 3 August, beginning at 07:00
  and 08:00 UTC. DK1 has 62 unusable solar hours. No missing primary-generation
  hours were found in Germany or DK2 under the parser's reported-category test.
- Oil (B06) and waste (B17) need factors in all four zones. Germany additionally
  reports coal-derived gas (B03), other renewable (B15), and other (B20).
  Those categories retain their energy and remain visibly unmapped.
- DK2 is particularly sensitive to these unresolved factors. Its wide range
  would make a precise border carbon-opportunity ranking premature.
- France's benchmark mean is below even the pilot's low sensitivity scenario.
  The unknown-fuel assumptions therefore cannot alone reconcile the models:
  accounting basis, fleet factors, storage and coverage must be investigated.
- The initial public Energy-Charts downloads remain available locally, but
  **were not used for the reported ENTSO-E results**.

## Deliverables and next decision

`tools/carbon_pilot.py` is a repeatable, dependency-free analysis pipeline.
`data/carbon-pilot/entsoe/raw` contains the four month-long XML responses and
their secret-free provenance records. `data/carbon-pilot/entsoe/2026-08` contains
the hourly records and machine-readable summary. Downloads and generated data
are ignored by Git; the implementation and documentation are reviewable on
the local `codex/carbon-pilot` branch. No deployment or application database
changes were made.

Tests cover energy weighting, missing data, unmapped fuels, storage exclusion,
zero generation, ENTSO-E curve handling, units, overlapping records, UTC
windows and benchmark joins. A cached replay also verifies that the pipeline
can run without credentials after retrieval.

Proceed by resolving the fuel factors and comparing like-for-like accounting
bases before extending this to a full year and connecting the carbon signal
to the app's target rankings. The archived Electricity Maps dataset remains
useful as a diagnostic benchmark throughout that work.
