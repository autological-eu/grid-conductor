# 2025 production-carbon pilot

This experiment uses **January 2025 ENTSO-E actual generation** for France and Danish bidding zones DK1 and DK2. It is historical production accounting, not consumption intensity, marginal emissions or investment benefits. It does not replace the map climate proxy.

[Hourly observations, factor assumptions and provenance](../public/research/production-carbon-2025/results.json)

![Reported generation mix and hourly partial operational/lifecycle intensity, with missing-hour gaps.](../public/research/production-carbon-2025/production-carbon.svg)

## Coverage comes first

| Zone | Complete reported-generation hours | Lifecycle mapped energy | Operational mapped energy | Full intensity estimates |
| --- | ---: | ---: | ---: | ---: |
| France | 319 / 744 | 99.31% | 98.78% | 0 |
| DK1 | 744 / 744 | 97.23% | 87.42% | 0 |
| DK2 | 744 / 744 | 94.84% | 69.31% | 0 |

**There is not yet a defensible whole-zone intensity value in this pilot.** Every zone has positive generation with unmapped factors. We retain those quantities and return null for full intensity instead of assigning zero.

The chart divides emissions by generation for the **mapped subset only**. Denmark's operational subset excludes biomass, making its coverage lower than lifecycle coverage. Differences between the curves reflect both different emissions boundaries and different subsets; they do not measure lifecycle overhead.

An hour is usable only when every reported primary-generation category has four quarter-hour samples. Missing intervals break the chart; absent categories are never assumed zero. France's 425 rejected hours need investigation before using its remaining hours as a representative month. Complete reported-category coverage does not prove complete generating-fleet coverage.

## Maths and an example

$$I_{z,t}=\frac{\sum_g G_{z,g,t}e_g}{\sum_g G_{z,g,t}}$$

G is generation in MWh; e is kg CO2/MWh for operational accounting or kg CO2e/MWh for lifecycle accounting. Intensities have the same numeric value as g/kWh. For a partial estimate, numerator and denominator contain only mapped technologies.

For gas we use 56.1 kg CO2/GJ and **assumed 50% electrical efficiency**:

$$e_{gas}=56.1\times3.6/0.50=403.92\;\mathrm{kg\ CO_2/MWh}$$

A hypothetical hour with 50 MWh gas and 50 MWh nuclear has direct combustion intensity of 201.96 g CO2/kWh. Positive generation from an unsupported fuel makes the full estimate unavailable; the known subset remains a partial calculation.

Generation bars include complete-generation hours only. Monthly intensity requires summed emissions divided by summed generation, not an unweighted average of hourly intensities. No January result is extrapolated to a year.

## Separate factor boundaries

| Technology | Operational pilot | Lifecycle pilot |
| --- | --- | --- |
| Gas | 56.1 kg CO2/GJ; assumed 50% efficiency | IPCC AR5 combined-cycle median proxy |
| Hard coal | 94.6 kg CO2/GJ; assumed 40% efficiency | IPCC AR5 pulverised-coal median |
| Lignite | 101 kg CO2/GJ; assumed 35% efficiency | Generic coal proxy |
| Wind, solar, nuclear and hydro | Zero direct combustion CO2 | IPCC AR5 lifecycle proxies |
| Biomass | Unmapped; biogenic accounting unresolved | Dedicated-biomass proxy with accounting caveat |
| Oil, waste and unsupported fuels | Unmapped | Unmapped where no existing factor is documented |

These are generic factors and assumed efficiencies, not measured country-specific fleet emissions. Zero direct combustion does not imply zero lifecycle or reservoir greenhouse gases. Operational results cover CO2; lifecycle factors cover CO2-equivalent greenhouse gases. Imports are not traced. Pumped-storage and battery discharge are excluded from primary generation because their carbon requires charging-origin accounting.

[IPCC 2006 fuel factors, chapter 2](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf) · [IPCC AR5 lifecycle factors](https://archive.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf)

## Next gates

1. Investigate missing intervals and audit independent monthly generation totals.
2. Resolve unsupported fuels, biomass/CHP allocation and fleet-specific efficiencies; publish sensitivities.
3. Add physical flows, demand and chronological storage-origin accounting for consumption intensity.
4. Compare paired verified dispatch scenarios for intervention emissions, separately from historical accounting.

France is national generation; DK1 and DK2 remain separate. Nothing here represents SE3 or SE4. Collection success is not model validation or avoided emissions.

See [existing carbon gates](carbon-pilot.md), [flow tracing](flow-tracing.md) and [conditional 2025 dispatch](2025-conditional-network-benchmark.md).

## Reproduce

    python tools/carbon_pilot.py --month 2025-01 --zones FR DK-DK1 DK-DK2
    python tools/publish_production_carbon_2025.py
    python -m unittest discover -s tools -p 'test*carbon*.py'

Uncached collection requires an offline ENTSO-E credential. Raw XML and credentials remain ignored; public provenance contains request parameters and hashes without security tokens. The publisher needs matplotlib and numpy in the research environment.
