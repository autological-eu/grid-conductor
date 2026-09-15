#!/usr/bin/env python3
"""Extract baseline data from a solved PyPSA-Eur network into JSON/CSV files
consumed by the Grid Conductor app.

Reads the solved network (produced by build_pypsa_network.py / Snakemake) via
pypsa and writes:
  public/research/baseline/countries.json      - country metadata (lat, lon)
  public/research/baseline/generators.json      - generator fleet per country
  public/research/baseline/hourly_dispatch.csv  - hourly x country generation (MW)
  public/research/baseline/hourly_load.csv      - hourly x country demand (MW)
  public/research/baseline/hourly_flow.csv      - hourly x border link flow (MW)
  public/research/baseline/cross_borders.json   - cross-border link/interconnector list
  public/research/baseline/summary.json         - totals and carbon intensity

Usage:
    python tools/extract_baseline.py [--network <solved.nc>] [--output <dir>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "data" / "pypsa-eur" / "upstream"
OUT_DIR = ROOT / "public" / "research" / "baseline"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(v) -> str:
    if v is None or pd.isna(v):
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return str(v)


def _de_dupe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate index labels of a component table, keeping the first."""
    if df.index.has_duplicates:
        df = df[~df.index.duplicated(keep="first")]
    return df


def _aggregate_by_country(df: pd.DataFrame, mapping: pd.Series) -> pd.DataFrame:
    """Sum component rows (indexed by name) into columns grouped by country."""
    df = df.copy()
    df.index.name = "component"
    return df.T.groupby(mapping).sum().T


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_countries(n: pypsa.Network) -> list[dict]:
    """Extract distinct country metadata from bus coordinates."""
    buses = n.buses
    by_code: dict[str, dict] = {}
    for _name, row in buses.iterrows():
        code = _str(row.get("country"))
        if not code or code == "nan":
            continue
        entry = by_code.setdefault(
            code, {"code": code, "name": code, "lat": 0.0, "lon": 0.0, "n_buses": 0}
        )
        entry["n_buses"] += 1
        x, y = float(row.get("x", 0.0)), float(row.get("y", 0.0))
        # PyPSA x = longitude, y = latitude
        entry["lon"] = x if entry["n_buses"] == 1 else (entry["lon"] * (entry["n_buses"] - 1) + x) / entry["n_buses"]
        entry["lat"] = y if entry["n_buses"] == 1 else (entry["lat"] * (entry["n_buses"] - 1) + y) / entry["n_buses"]
    result = []
    for entry in sorted(by_code.values(), key=lambda r: r["code"]):
        entry["lat"] = round(entry["lat"], 4)
        entry["lon"] = round(entry["lon"], 4)
        result.append(entry)
    return result


def extract_generators(n: pypsa.Network) -> list[dict]:
    """Extract generator fleet summarised per fuel and country."""
    buses = n.buses
    gen = n.generators
    rows = []
    for name, g in gen.iterrows():
        bus = _str(g.get("bus"))
        country = _str(buses.at[bus, "country"]) if bus in buses.index else ""
        carrier = _str(g.get("carrier"))
        rows.append({
            "name": name,
            "carrier": carrier,
            "fuel": carrier,
            "country": country,
            "p_nom_mw": round(float(g.get("p_nom", 0.0) or 0.0), 1),
            "efficiency": round(float(g.get("efficiency", 1.0) or 1.0), 3),
            "build_year": int(g.get("build_year", 0))
            if pd.notna(g.get("build_year", None)) and g.get("build_year") else None,
        })
    return rows


def extract_cross_borders(n: pypsa.Network) -> list[dict]:
    """Extract cross-border assets (AC lines and DC links) as country pairs."""
    buses = n.buses
    grouped: dict[tuple[str, str], dict] = {}

    def _country(name: str) -> str:
        return _str(buses.at[name, "country"]) if name in buses.index else ""

    for component, table, nominal, carriers in (
        ("Line", n.lines, "s_nom", None),
        ("Link", n.links, "p_nom", ("DC", "B2B")),
    ):
        for name, row in table.iterrows():
            if carriers and _str(row.get("carrier")) not in carriers:
                continue
            a, b = _country(_str(row.get("bus0"))), _country(_str(row.get("bus1")))
            if not a or not b or a == b:
                continue
            capacity = float(row.get(nominal, 0.0) or 0.0)
            if capacity <= 0:
                continue
            a, b = sorted([a, b])
            key = f"{a}-{b}"
            entry = grouped.setdefault(
                (a, b),
                {"id": key, "country_a": a, "country_b": b, "assets": [], "capacity_mw": 0.0},
            )
            entry["assets"].append({
                "component": component,
                "id": name,
                "nominal_mw": round(capacity, 1),
            })
            entry["capacity_mw"] += capacity

    borders = []
    for (a, b), entry in grouped.items():
        entry["capacity_mw"] = round(entry["capacity_mw"], 1)
        borders.append(entry)
    return sorted(borders, key=lambda b: (b["country_a"], b["country_b"]))


def extract_hourly_dispatch(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x country -> total generation (MW)."""
    buses = n.buses
    p = n.generators_t.p
    mapping = pd.Series(
        [_str(buses.at[_str(g), "country"]) for g in p.columns],
        index=p.columns,
    )
    return _aggregate_by_country(p, mapping)


def extract_hourly_load(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x country -> total load (MW)."""
    buses = n.buses
    p = n.loads_t.p
    mapping = pd.Series(
        [_str(buses.at[_str(l), "country"]) for l in p.columns],
        index=p.columns,
    )
    return _aggregate_by_country(p, mapping)


def extract_hourly_flow(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x border -> flow (MW). Positive = country_a -> country_b.

    Lines carry s_nom 'AC' flows; links (interconnectors) carry DC. Both are
    oriented bus0 -> bus1. Borders with both an AC line and a DC link would
    collide; keep the DC link as authoritative for arbitrage and skip colliding
    AC lines (mark with suffix where needed).
    """
    buses = n.buses

    def _country(name: str) -> str:
        return _str(buses.at[name, "country"]) if name in buses.index else ""

    frames = []
    for table, pcol in ((n.lines, n.lines_t.p0), (n.links, n.links_t.p0)):
        for name in pcol.columns:
            a0, b0 = _str(table.at[name, "bus0"]), _str(table.at[name, "bus1"])
            ca, cb = _country(a0), _country(b0)
            if not ca or not cb or ca == cb:
                continue
            series = pcol[name].copy()
            label = f"{sorted([ca, cb])[0]}->{sorted([ca, cb])[1]}"
            # Orient so that positive flow = a->b (minimum country code first)
            if ca == sorted([ca, cb])[0]:
                pass
            else:
                series = -series
            frames.append((label, series))
    # Sum flows on the same border (rare; multiple assets on one border)
    merged: dict[str, pd.Series] = {}
    for label, series in frames:
        merged[label] = merged.get(label, pd.Series(0.0, index=series.index)) + series
    if not merged:
        return pd.DataFrame()
    result = pd.DataFrame(merged)
    result.index.name = "timestamp"
    return result


def compute_summary(
    n: pypsa.Network,
    countries: list[dict],
    generators: list[dict],
) -> dict:
    """Aggregate totals: capacity by fuel, load, CO2, carbon intensity."""
    fuel_capacity: dict[str, float] = {}
    for g in generators:
        fuel_capacity[g["fuel"]] = fuel_capacity.get(g["fuel"], 0.0) + g["p_nom_mw"]

    total_load_mwh = float(n.loads_t.p.sum().sum())
    total_gen_mwh = float(n.generators_t.p.sum().sum())

    # Operational CO2 per carrier, from dispatch x carrier emission factor
    co2_by_carrier = {}
    if "co2_emissions" in n.carriers:
        co2_by_carrier = n.carriers["co2_emissions"].to_dict()
    carrier_of = n.generators.set_index(n.generators.index)["carrier"]
    by_carrier_gwh = (n.generators_t.p.T.groupby(carrier_of).sum().T.sum(axis=0) * 1e-6).to_dict()
    co2_kt = 0.0
    for carrier, gwh in by_carrier_gwh.items():
        factor = co2_by_carrier.get(carrier)
        if factor:
            co2_kt += gwh * factor * 1e6 / 1e3

    carbon_intensity = round(co2_kt * 1e6 / total_load_mwh, 1) if total_load_mwh > 0 else None

    summary = {
        "n_countries": len(countries),
        "n_generators": len(generators),
        "capacity_by_fuel_mw": {k: round(v, 1) for k, v in sorted(fuel_capacity.items())},
        "generation_by_carrier_gwh": {k: round(v, 1) for k, v in sorted(by_carrier_gwh.items())},
        "total_load_gwh": round(total_load_mwh / 1e3, 1),
        "total_generation_gwh": round(total_gen_mwh / 1e3, 1),
        "total_co2_kt": round(co2_kt, 1),
        "carbon_intensity_gco2_per_kwh": carbon_intensity,
    }
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_solved_network() -> Path:
    """Auto-discover the solved network from the manifest or results dir."""
    manifest = ROOT / "data" / "pypsa-eur" / "baseline-manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text())
        rel = data.get("network_file", "")
        full = UPSTREAM / rel
        if full.exists():
            return full

    results_dir = UPSTREAM / "results"
    if results_dir.exists():
        candidates = sorted(results_dir.rglob("base_s_*_elec_.nc"))
        if candidates:
            return candidates[-1]

    sys.exit("ERROR: No solved network found. Run build_pypsa_network.py first.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract baseline from solved PyPSA-Eur network")
    parser.add_argument("--network", type=Path, default=None, help="Path to solved .nc file")
    parser.add_argument("--output", type=Path, default=OUT_DIR, help="Output directory")
    args = parser.parse_args()

    nc_path = args.network or find_solved_network()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    print(f"[extract] Loading {nc_path}")
    n = pypsa.Network(nc_path)

    print("[extract] Countries...")
    countries = extract_countries(n)
    (out / "countries.json").write_text(json.dumps(countries, indent=2) + "\n")
    print(f"  -> {len(countries)} countries")

    print("[extract] Generators...")
    generators = extract_generators(n)
    (out / "generators.json").write_text(json.dumps(generators, indent=2) + "\n")
    print(f"  -> {len(generators)} generators")

    print("[extract] Cross-border links...")
    borders = extract_cross_borders(n)
    (out / "cross_borders.json").write_text(json.dumps(borders, indent=2) + "\n")
    print(f"  -> {len(borders)} borders")

    print("[extract] Hourly dispatch...")
    dispatch = extract_hourly_dispatch(n)
    dispatch.to_csv(out / "hourly_dispatch.csv")
    print(f"  -> {dispatch.shape}")

    print("[extract] Hourly load...")
    load = extract_hourly_load(n)
    load.to_csv(out / "hourly_load.csv")
    print(f"  -> {load.shape}")

    print("[extract] Hourly flow...")
    flow = extract_hourly_flow(n)
    if not flow.empty:
        flow.to_csv(out / "hourly_flow.csv")
        print(f"  -> {flow.shape}")
    else:
        print("  -> no cross-border flows found")

    print("[extract] Summary...")
    summary = compute_summary(n, countries, generators)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"  -> {json.dumps(summary, indent=2)}")

    print(f"\n[extract] Done. All files written to {out}")


if __name__ == "__main__":
    main()