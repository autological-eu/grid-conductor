# 2025 baseline import-chain audit

Measured 29 October 2026 against the six source-hashed entrypoints for the two retained research baselines, plus three site checks. This is a **static transitive import** count: imports inside functions are included even when a given run never calls the function. It is 91 distinct Python modules (87 baseline, four additional site-only). Importing all six baseline entrypoints in the pinned environment actually loaded 76 local modules before any fit or LP clear. These are module counts, not 91 independent models.

| Primary role | Modules | What they do |
|---|---:|---|
| Data and source | 15 | Load weather, generation and price inputs; ENTSO-E exchange parsing; fuel, solar and hydro source preparation; provenance. |
| Network and capacities | 21 | Build bidding zones, corridors, generator availability, hydro, storage and physical constraint matrices. |
| Fast fitting | 33 | Supply splines, batched transport clearing, price-root retries, gradients, monthly optimizer and older experiment helpers. |
| LP evaluation | 18 | Transfer fitted costs, run annual LP, replay primals/duals and calculate price/generation scores. |
| Site checks | 4 | Verify live workbench assets, country explorer and named research witnesses. |

The first four categories contain 87 modules. Assignment below reflects each file's *main* responsibility; several cross category boundaries.

## Dependency map

```
source data -> capacity/network assembly -> batched transport + curve fit
                                    \-> original 799-offer LP + audits
```

Three wide imports explain much of the fan-out:

- `monthly_lp_spline_inputs_2025` imports `run_independent_hourly_transport_2025` to obtain its `setup()` result, which in turn imports several earlier spline and transfer experiments.
- `run_batched_transport_2025` imports prototype training and report helpers at module load, although the active fit needs chiefly its `setup()` data path.
- `sigmoid_month_pairs_2025` provides `ROOT`, `digest`, `metric` and month helpers but also contains older network-building and fitting code; callers inherit much of that graph.

Other bridges include `nve_hydro_diagnostics` (hydro inputs and LP solver), `solar_anchor_bids_2025` (source preparation and accepted LP), and `monthly_lp_spline_inputs_2025` (source arrays plus physical LP alignment). These should be split by responsibility in a new implementation. They must not be edited in place while saved source hashes certify the existing baselines.

## Path to at most 20 active imports

Create a new versioned implementation, retain the original scripts as immutable replay evidence, and set an import-graph gate on the new entrypoints. A suitable budget is three source modules, four network modules, six fitting modules, five LP/evaluation modules and two orchestration/verification modules. Count only project Python modules, but include imports inside executable functions and all nested imports. External NumPy/SciPy/HiGHS packages are outside that count.

1. Extract immutable 2025 source loading, chronology and provenance from the old experiment drivers. Rebuild the same 48-zone, 326 fit-group and 799 LP-offer inputs. Check array equality and original availability, demand, hydro and corridor bounds.
2. Extract the transport equations, monotone curve parameters, certified multi-start price roots, observed-price selection and generation/price gradient into the fitting layer. Compare a bounded monthly pilot at initialization and after updates against saved curves and flow/price witnesses. Preserve the three declared Baltic gradient exclusions and all-cell scoring.
3. Extract offer-cost transfer and LP model building without importing fit drivers. Require exact offer-column mapping, one 8,760-hour chronological LP clear, zero emergency and unchanged primal/dual tolerances. Compare price and mix scores with both retained witnesses.
4. Only after equivalence passes, point new runs at the compact entrypoints. Keep historical source hashes and receipts unchanged. If a numerical result changes, assign a new candidate ID and rerun the acceptance gates before calling it a baseline.

The current source-hashed baselines are **not yet** refactored to the 20-module target. The repository retains hash-only producer files outside this graph because source receipts refer to their exact bytes. A file-count-only move would make the dependency look smaller while leaving the computation unchanged.

The read-only input-load test initially failed after the publication cleanup because the IRENA capacity archive and source-hashed helper files were missing. They were restored and both retained input paths now load. A broad recursive scan of older ignored receipts still finds historical hash differences from later pointer adoption, updated country explorer exports and retired calibration attempts; that scan is not a valid current-baseline gate. The successor needs a deliberately scoped source manifest so each input and its hash have one authoritative version.

## Inventory by primary role

### Data and source (15)

`carbon_pilot`, `collect_entsoe_flows_2025`, `compare_2025_generation_reference`, `compare_daily_dispatch_prices`, `compare_native_exchange_reference`, `eu_zones`, `flow_tracing`, `generation_mix_2025`, `hourly_renewable_estimates`, `irena_linear_dispatch_capacity`, `monthly_dispatch`, `nve_hydro_inputs_2025`, `prepare_fuel_prices`, `solar_fleet_audit_2025`, `solar_country_fit_2025`.

### Network and capacities (21)

`bidding_zone_network_2025`, `compile_transport_corridors_2025`, `daily_market_clearing`, `derive_physical_zonal_constraints`, `european_physical_bids_2025`, `european_reservoir_clearing_2025`, `fixed_reservoir_screening_2025`, `global_bidding_zone_2025`, `grouped_master_dual`, `hybrid_fixed_hydro_2025`, `nve_hydro_diagnostics`, `perfect_foresight_dispatch`, `regional_water_candidate_2025`, `run_bidding_zone_network_2025`, `run_regional_water_candidate_2025`, `simple_resource_bids`, `submonthly_inventory_driver`, `submonthly_objective_donor`, `synthetic_bids_2025`, `thermal_bid_rules`, `update_norway_hydro_2025`.

### Fast fitting (33)

`batched_transport_cold_retry_2025`, `batched_transport_dispatch_2025`, `batched_transport_newton_recovery_2025`, `batched_transport_observed_price_multistart_2025`, `differentiable_spline_clearing`, `fit_identified_multistart_aligned_mixed_flow_2025`, `fit_identified_multistart_mixed_flow_2025`, `fit_monthly_fast_splines_2025`, `flow_adjusted_zonal_clearing_2025`, `forward_hourly_splines_2025`, `hour_table_conditioner_2025`, `hourly_spline_numerical_recovery_2025`, `hourly_spline_reconstruction_2025`, `independent_hourly_transport_2025`, `intraday_offer_bids_2025`, `monthly_diurnal_splines_2025`, `monthly_lp_spline_inputs_2025`, `pilot_batched_transport_2025`, `report_batched_transport_2025`, `run_batched_transport_2025`, `run_batched_transport_fit_2025`, `run_batched_transport_recovery_2025`, `run_batched_transport_robust_2025`, `run_differentiable_spline_2025`, `run_fast_fit_physical_transfer_2025`, `run_forward_hourly_splines_2025`, `run_independent_hourly_transport_2025`, `run_supply_knots_lp_2025`, `sigmoid_month_pairs_2025`, `spline_europe_2025`, `supply_knot_network_2025`, `supply_knot_splines_2025`, `transport_curve_physical_transfer_2025`.

### LP evaluation (18)

`audit_identified_aligned_fast_joint_lp_2025`, `audit_identified_aligned_mixed_flow_2025`, `audit_nve_hydro_diagnostics_2025`, `audit_solar_anchor_bids_2025`, `bid_calibration_2025`, `clear_monthly_fast_lp_2025`, `europe_linked_clearing_2025`, `hourly_offer_curves_2025`, `joint_network_clear_2025`, `linked_order_reclearing`, `linked_profile_orders`, `monthly_fast_lp_costs_2025`, `price_mechanism_2025`, `run_identified_aligned_fast_joint_lp_2025`, `run_seasonal_calendar_bids_2025`, `seasonal_calendar_bids_2025`, `solar_anchor_bids_2025`, `weekly_supply_bids_2025`.

### Site checks (4)

`check_baseline_catalog`, `check_country_explorer`, `check_public_assets`, `check_zone_price_traces`.
