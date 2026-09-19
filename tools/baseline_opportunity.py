"""Baseline (single-solve) border market diagnostics for Grid Conductor.

Loads a solved operational PyPSA network and produces two per-border measures
without any per-border planning experiments:

1. Congestion rent (MEUR/window) = sum over hours and assets of
   |locational price gap| x |actual flow| x weight  -- the market wedge carried
   by the current dispatch. Derived from the recorded build solve's nodal prices
   and flows (the canonical surface published in public/research/baseline/).

2. Marginal capacity value (EUR/MW/window) from the flow-constraint duals of
   ONE baseline re-solve with all duals assigned (assign_all_duals=True). Per
   asset the relieving value per MW is max(-mu_upper, 0) + max(mu_lower, 0)
   (PyPSA stores cost-sensitivity duals, mu_upper <= 0 and mu_lower >= 0); the
   border aggregates assets capacity-proportionally (share_i = nominal_i / sum
   nominal), which is the exact Delta->0 linearization of pypsa_border_targets'
   +MW experiments. Duals are certified LP shadow prices; a presence gate fails
   closed when the solver returns no flow-limit duals. Re-solving can shift the
   simplex basis (degenerate optima), so the per-asset relation
   `price gap ~= mu_upper - mu_lower` is reported as the `kkt_max_residual`
   diagnostic together with `lmp_recheck_max_eur_mwh`; both are non-gating.

modelled_opportunity_meur / opportunity_meur stay null: exact per-border
capacity runs live in pypsa_border_targets.py and are out of scope here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pypsa_border_targets import (
    UPSTREAM_COMMIT,
    border_catalog,
    digest,
    operational_emissions,
    solve,
    verify_operational,
    write_json,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "public" / "research" / "pypsa-targets.json"
SRC_MIRROR = ROOT / "src" / "data" / "baseline-targets.json"
SPREAD_EPS = 0.05
DUAL_EPS = 1e-3

# ---------------------------------------------------------------------------
# Pure diagnostic functions
# ---------------------------------------------------------------------------


def spread_stats(gap_abs, weights=None, spread_eps=SPREAD_EPS):
    """gap_abs: (H, A) array of |price gap| per hour per border asset.

    Returns mean/max absolute spread and the number of hours in which at least
    one asset of the border carries a nonzero locational gap.
    """
    gap_abs = np.asarray(gap_abs, dtype=float)
    if gap_abs.size == 0:
        raise ValueError("Empty spread matrix")
    w = np.ones(gap_abs.shape[0]) if weights is None else np.asarray(weights, dtype=float)
    w = w / w.sum()
    return {
        "mean_abs_spread_eur_mwh": round(float((gap_abs * w[:, None]).sum()), 2),
        "max_abs_spread_eur_mwh": round(float(np.nanmax(gap_abs)), 1),
        "spread_hours": int((gap_abs > spread_eps).any(axis=1).sum()),
    }


def rent_meur(gap_abs, flow_abs, weights=None):
    """Congestion rent = sum_h w_h x sum_a |gap|_ha x |flow|_ha, in MEUR."""
    gap_abs = np.asarray(gap_abs, dtype=float)
    flow_abs = np.asarray(flow_abs, dtype=float)
    if gap_abs.shape != flow_abs.shape:
        raise ValueError("Gap and flow matrices must have the same shape")
    hourly = (gap_abs * flow_abs).sum(axis=1)
    w = np.ones(hourly.size) if weights is None else np.asarray(weights, dtype=float)
    if w.size != hourly.size:
        raise ValueError("Weights must have as many entries as hours")
    return float((hourly * w).sum()) / 1e6


def share_weights(nominal_mw):
    nominal = np.asarray(nominal_mw, dtype=float)
    if nominal.size == 0 or not np.isfinite(nominal).all() or (nominal <= 0).any():
        raise ValueError("Border assets need positive finite nominal capacity")
    return nominal / nominal.sum()


def marginal_value_eur_mw(mu_upper, mu_lower, shares, weights=None):
    """Capacity-proportional marginal value of easing a border, EUR/MW/window.

    PyPSA stores flow-constraint duals as cost sensitivities: mu_upper <= 0 and
    mu_lower >= 0, so the per-MW relieving value of raising s_nom is
    max(-mu_upper, 0) + max(mu_lower, 0) (it relaxes both bounds). Per hour the
    border value is sum over assets of share_i x that relieving value; hourly
    values are accumulated with the snapshot weights (1 h here).
    """
    mu_upper = np.asarray(mu_upper, dtype=float)
    mu_lower = np.asarray(mu_lower, dtype=float)
    if mu_upper.shape != mu_lower.shape:
        raise ValueError("mu_upper and mu_lower must share shape")
    if not (np.isfinite(mu_upper) & np.isfinite(mu_lower)).all():
        raise ValueError("Nonfinite flow-constraint duals")
    relief = np.maximum(-mu_upper, 0.0) + np.maximum(mu_lower, 0.0)
    hourly = relief @ np.asarray(shares, dtype=float)
    w = np.ones(hourly.size) if weights is None else np.asarray(weights, dtype=float)
    if w.size != hourly.size:
        raise ValueError("Weights must have as many entries as hours")
    return float((hourly * w).sum())


def kkt_gaps_ok(gap_signed, mu_upper, mu_lower, rel_tol=0.02, abs_floor=0.5):
    """Optimality identity for capacity constraints, agnostic to dual sign.

    Returns (ok, max_residual). The price gap across a single lossless radial
    asset equals the signed difference of its flow-limit duals. Used as a
    diagnostic: in meshed KVL-constrained networks the identity is structurally
    violated per asset, so the caller must not treat a nonzero residual as a
    solver failure.
    """
    gap = np.asarray(gap_signed, dtype=float)
    mu = np.asarray(mu_upper, dtype=float) - np.asarray(mu_lower, dtype=float)
    if gap.shape != mu.shape or not (np.isfinite(gap) & np.isfinite(mu)).all():
        return False, float("nan")
    residuals = np.minimum(
        np.abs(gap - mu),
        np.abs(gap + mu),
    )
    tol = np.maximum(rel_tol * np.maximum(np.abs(gap), 1.0), abs_floor)
    return bool((residuals <= tol).all()), float(np.max(residuals))


def window_years(start_iso, end_iso):
    start = pd.Timestamp(start_iso)
    end = pd.Timestamp(end_iso)
    if (
        start.month == 1
        and start.day == 1
        and start.hour == 0
        and end == pd.Timestamp(start.year + 1, 1, 1)
    ):
        return 1.0
    return round((end - start).total_seconds() / (365.25 * 86400), 4)


def build_target(border, diagnostic, marginal_value):
    """Schema-v2 target row: diagnostics present, opportunity left null."""
    return {
        "id": border["id"],
        "a": border["a"],
        "b": border["b"],
        "assets": border["assets"],
        "status": "baseline_diagnostic",
        "baseline_rent_meur": round(diagnostic["rent_meur"], 3),
        "mean_abs_spread_eur_mwh": diagnostic["mean_abs_spread_eur_mwh"],
        "max_abs_spread_eur_mwh": diagnostic["max_abs_spread_eur_mwh"],
        "spread_hours": diagnostic["spread_hours"],
        "congested_hours": diagnostic["congested_hours"],
        "marginal_value_eur_mw": round(marginal_value, 2),
        "opportunity_meur": None,
        "modelled_opportunity_meur": None,
        "modelled_climate_opportunity_tonnes": None,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(network_path: Path, manifest_path: Path, output: Path) -> dict:
    import pypsa

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    original = pypsa.Network(network_path)
    verify_operational(original, manifest, network_path)
    borders = border_catalog(original, allow_zero_capacity=True)
    if not borders:
        raise ValueError("No cross-border assets found in network")
    saved_price = original.buses_t.marginal_price

    candidate = original.copy()
    baseline_cost = solve(candidate)
    solved_price = candidate.buses_t.marginal_price
    try:
        aligned = original.buses_t.marginal_price.reindex_like(solved_price)
        lmp_recheck = float((aligned - solved_price).abs().max().max())
    except (KeyError, ValueError, TypeError):
        lmp_recheck = None

    weights = candidate.snapshot_weightings.generators.to_numpy(dtype=float)

    rows = []
    rent_total = 0.0
    kkt_max_residual = 0.0
    for border in borders:
        gaps, flows, mus_u, mus_l, nominal = [], [], [], [], []
        for asset in border["assets"]:
            if asset["component"] == "Link":
                table, p0 = candidate.links, original.links_t.p0[asset["id"]]
            else:
                table, p0 = candidate.lines, original.lines_t.p0[asset["id"]]
            try:
                mu_u_series = (
                    candidate.links_t.mu_upper[asset["id"]]
                    if asset["component"] == "Link"
                    else candidate.lines_t.mu_upper[asset["id"]]
                )
                mu_l_series = (
                    candidate.links_t.mu_lower[asset["id"]]
                    if asset["component"] == "Link"
                    else candidate.lines_t.mu_lower[asset["id"]]
                )
            except KeyError as exc:
                raise ValueError(
                    f"Missing capacity duals for {asset['component']}/{asset['id']}: "
                    "solver returned no flow-limit duals"
                ) from exc
            if mu_u_series.isna().all() or mu_l_series.isna().all():
                raise ValueError(
                    f"Missing capacity duals for {asset['component']}/{asset['id']}: "
                    "solver returned no flow-limit duals"
                )
            mu_u = mu_u_series.fillna(0.0)
            mu_l = mu_l_series.fillna(0.0)
            bus0, bus1 = table.at[asset["id"], "bus0"], table.at[asset["id"], "bus1"]
            gap = saved_price[bus0] - saved_price[bus1]
            gaps.append(gap.abs().to_numpy(dtype=float))
            flows.append(np.abs(p0.to_numpy(dtype=float)))
            mus_u.append(np.asarray(mu_u, dtype=float))
            mus_l.append(np.asarray(mu_l, dtype=float))
            nominal.append(asset["nominal_mw"])
            _, residual = kkt_gaps_ok(
                gap.to_numpy(dtype=float),
                np.asarray(mu_u, dtype=float),
                np.asarray(mu_l, dtype=float),
            )
            kkt_max_residual = max(kkt_max_residual, residual)
        gap_a = np.stack(gaps, axis=1)
        flow_a = np.stack(flows, axis=1)
        stats = spread_stats(gap_a, weights)
        rent = rent_meur(gap_a, flow_a, weights)
        rent_total += rent
        congested_hours = int(
            (
                (
                    np.maximum(-np.stack(mus_u, axis=1), 0.0)
                    + np.maximum(np.stack(mus_l, axis=1), 0.0)
                )
                > DUAL_EPS
            )
            .any(axis=1)
            .sum()
        )
        marginal = marginal_value_eur_mw(
            np.stack(mus_u, axis=1), np.stack(mus_l, axis=1), share_weights(nominal), weights
        )
        rows.append(
            (
                border,
                {"rent_meur": rent, "congested_hours": congested_hours, **stats},
                marginal,
            )
        )

    nodes = []
    for country, buses in candidate.buses.groupby("country"):
        nodes.append(dict(id=country, x=float(buses.x.mean()), y=float(buses.y.mean())))

    try:
        co2 = operational_emissions(candidate)
        climate_error = None
    except ValueError as exc:
        co2, climate_error = None, str(exc)

    report = {
        "schema_version": 2,
        "status": "experimental_not_validated",
        "start": manifest["start"],
        "end_exclusive": manifest["end_exclusive"],
        "metric": "system_operating_cost_reduction",
        "baseline_metric": "congestion_rent_and_marginal_capacity_value",
        "unit": "MEUR/period",
        "window_years": window_years(manifest["start"], manifest["end_exclusive"]),
        "additional_mw": None,
        "annual_opportunity_meur": None,
        "network_sha256": digest(network_path),
        "upstream_commit": UPSTREAM_COMMIT,
        "manifest_sha256": digest(manifest_path),
        "observations_sha256": None,
        "pypsa_version": pypsa.__version__,
        "baseline_cost_eur": baseline_cost,
        "baseline_rent_meur_total": round(rent_total, 3),
        "baseline_co2_tonnes": co2,
        "climate_error": climate_error,
        "climate_basis": "direct_operational_generator_co2_not_lifecycle",
        "lmp_recheck_max_eur_mwh": lmp_recheck,
        "kkt_max_residual": round(kkt_max_residual, 6),
        "validation": {
            "status": "observations_unavailable",
            "price_basis": None,
            "entsoe_quantities": "pending_generation_flow_and_load_reconciliation",
            "jao": "pending_physical_to_market_domain_reconciliation",
        },
        "nodes": nodes,
        "targets": [
            build_target(border, diagnostic, marginal)
            for border, diagnostic, marginal in rows
        ],
    }
    write_json(output, report)
    write_json(SRC_MIRROR, report)
    print(f"[baseline] Public dataset: {output}")
    print(f"[baseline] Bundled server mirror: {SRC_MIRROR}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, type=Path, help="Schema-v2 targets JSON"
    )
    args = parser.parse_args()
    result = run(args.network, args.manifest, args.output)
    print(
        json.dumps(
            dict(
                status=result["status"],
                window_years=result["window_years"],
                rent_total_meur=result["baseline_rent_meur_total"],
                kkt_max_residual=result["kkt_max_residual"],
                lmp_recheck_max_eur_mwh=result["lmp_recheck_max_eur_mwh"],
                borders=len(result["targets"]),
            )
        )
    )