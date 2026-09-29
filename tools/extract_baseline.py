#!/usr/bin/env python3
"""Extract baseline data from a solved PyPSA-Eur network into JSON/CSV files
consumed by the Grid Conductor app.

Reads the solved network (produced by build_pypsa_network.py / Snakemake) via
pypsa and writes:
  public/research/baseline/countries.json      - country metadata (name, lat, lon)
  public/research/baseline/generators.json      - generator fleet per country
  public/research/baseline/hourly_dispatch.csv  - hourly x country generation (MW)
  public/research/baseline/hourly_load.csv      - hourly x country demand (MW)
  public/research/baseline/hourly_price.csv     - hourly x country nodal price (EUR/MWh)
  public/research/baseline/hourly_carbon.csv    - hourly x country carbon intensity (gCO2e/MWh)
  public/research/baseline/hourly_flow.csv      - hourly x border net flow (MW)
  public/research/baseline/cross_borders.json   - cross-border assets + directional ATC
  public/research/baseline/summary.json         - totals and carbon intensity

The four `hourly_*` series carry one column per country (or per border) and are
the complete set of signals the app's dispatch model needs: price, carbon
intensity and load per country, plus net flow per border. Columns are country
codes; the row index is an ISO-8601 UTC timestamp. Cells that cannot be computed
(for example carbon intensity in an hour with zero load) are written as empty
fields so the app can treat them as missing rather than as zero.

Usage:
    python tools/extract_baseline.py [--network <solved.nc>] [--output <dir>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import pypsa

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "data" / "pypsa-eur" / "upstream"
OUT_DIR = ROOT / "public" / "research" / "baseline"

# ISO 3166-1 alpha-2 -> English country name, for the countries in the current
# PyPSA-Eur operating footprint. Used only for display; the app keys everything
# off the code.
COUNTRY_NAMES = {
    "AL": "Albania", "AT": "Austria", "BA": "Bosnia and Herzegovina",
    "BE": "Belgium", "BG": "Bulgaria", "CH": "Switzerland", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain",
    "FI": "Finland", "FR": "France", "GB": "United Kingdom", "GR": "Greece",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "ME": "Montenegro",
    "MK": "North Macedonia", "NL": "Netherlands", "NO": "Norway", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "SE": "Sweden",
    "SI": "Slovenia", "SK": "Slovakia", "XK": "Kosovo",
}


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


def _aggregate_by_country(
    df: pd.DataFrame, mapping: pd.Series, how: str = "sum"
) -> pd.DataFrame:
    """Reduce component columns (indexed by name) into columns grouped by country.

    `sum` is right for additive quantities (dispatch, load, emissions); `mean` for
    per-unit quantities such as a price, where adding buses together is wrong.

    The keys are validated because a mismatch is silent: pandas drops the
    unmatchable rows and returns zeros, which previously turned a whole
    emissions column into 0.0 without any error.
    """
    if set(mapping.index) != set(df.columns):
        missing = sorted(set(df.columns) - set(mapping.index))[:3]
        extra = sorted(set(mapping.index) - set(df.columns))[:3]
        raise ValueError(
            "Country mapping does not match the series columns "
            f"(unmapped columns e.g. {missing}; keys with no column e.g. {extra}). "
            "Keys must be indexed by the series' own column names."
        )
    df = df.copy()
    df.index.name = "component"
    return df.T.groupby(mapping, sort=True).agg(how).T


def _bus_country(n: pypsa.Network) -> pd.Series:
    """Map every bus name to its country code."""
    return n.buses["country"].astype(str)


def _country_of_components(
    n: pypsa.Network, table: pd.DataFrame, names: "pd.Index"
) -> pd.Series:
    """Country for each named component, resolved through the component's bus.

    The columns of `generators_t` / `loads_t` are component names, not bus
    names, so they cannot be looked up in `n.buses` directly.
    """
    bus_of = table["bus"].astype(str)
    buses = n.buses
    return pd.Series(
        [
            _str(buses.at[bus_of[name], "country"]) if bus_of[name] in buses.index else ""
            for name in names
        ],
        index=pd.Index(list(names)),
    )


def _hourly_co2_t(n: pypsa.Network) -> pd.DataFrame:
    """Operational CO2 emissions per country per hour, in tonnes CO2e.

    PyPSA-Eur's `carriers.co2_emissions` is expressed per MWh of *fuel* consumed,
    so electrical output has to be divided by the generator's efficiency to get
    the primary energy input the factor applies to. Every generator carrier in
    the network carries a factor; a missing one is treated as zero-emission,
    which matches how the solve itself scores the carrier.

    This is the single implementation of the accounting; build_pypsa_network.py
    and the previous revision of this module each carried their own copy, and
    the copy here had dropped the efficiency division (understating emissions by
    ~2.8x). Keep the arithmetic in one place.
    """
    if "co2_emissions" not in n.carriers:
        return pd.DataFrame(index=n.snapshots)
    factors = n.generators["carrier"].map(n.carriers["co2_emissions"]).fillna(0.0)
    efficiency = n.get_switchable_as_dense("Generator", "efficiency")
    emissions = (n.generators_t.p / efficiency) * factors  # tonnes CO2e per bus-hour
    mapping = _country_of_components(n, n.generators, n.generators_t.p.columns)
    return _aggregate_by_country(emissions, mapping)


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
            code,
            {"code": code, "name": COUNTRY_NAMES.get(code, code), "lat": 0.0, "lon": 0.0, "n_buses": 0},
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
    """Extract cross-border assets (AC lines and DC links) as country pairs.

    Alongside the asset list each border carries `cap_ab_mw` / `cap_ba_mw`, the
    available transfer capacity in each direction with `country_a` < `country_b`
    lexicographically. This is the `s_nom` / `p_nom` of the connecting assets
    resolved onto the canonical direction, which is what the app's dispatch
    model needs as its transfer limit. Inferring the limit from the largest
    observed flow instead understates it whenever a border never happens to run
    at its rating during the window.

    AC lines are bidirectional. A DC link can carry power in both directions
    only when PyPSA-Eur has set `p_min_pu < 0`; with `p_min_pu == 0` the link is
    a one-way path and counts towards its own bus0 -> bus1 direction only.
    """
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
            native_from = _country(_str(row.get("bus0")))
            native_to = _country(_str(row.get("bus1")))
            if not native_from or not native_to or native_from == native_to:
                continue
            capacity = float(row.get(nominal, 0.0) or 0.0)
            if capacity <= 0:
                continue
            a, b = sorted([native_from, native_to])
            key = f"{a}-{b}"
            entry = grouped.setdefault(
                (a, b),
                {
                    "id": key,
                    "country_a": a,
                    "country_b": b,
                    "assets": [],
                    "capacity_mw": 0.0,
                    "cap_ab_mw": 0.0,
                    "cap_ba_mw": 0.0,
                },
            )
            entry["assets"].append({
                "component": component,
                "id": name,
                "nominal_mw": round(capacity, 1),
                "bus0_country": native_from,
                "bus1_country": native_to,
            })
            entry["capacity_mw"] += capacity
            bidirectional = component == "Line" or float(row.get("p_min_pu", 0.0) or 0.0) < 0
            if bidirectional or native_from == a:
                entry["cap_ab_mw"] += capacity
            if bidirectional or native_from == b:
                entry["cap_ba_mw"] += capacity

    borders = []
    for (a, b), entry in grouped.items():
        for field in ("capacity_mw", "cap_ab_mw", "cap_ba_mw"):
            entry[field] = round(entry[field], 1)
        borders.append(entry)
    return sorted(borders, key=lambda b: (b["country_a"], b["country_b"]))


def extract_hourly_dispatch(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x country -> total generation (MW)."""
    p = n.generators_t.p
    return _aggregate_by_country(p, _country_of_components(n, n.generators, p.columns))


def extract_hourly_load(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x country -> total load (MW)."""
    p = n.loads_t.p
    return _aggregate_by_country(p, _country_of_components(n, n.loads, p.columns))


def extract_hourly_price(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x country -> mean nodal dual price (EUR/MWh).

    The marginal price recorded by the solve is nodal, not zonal, so a country
    with several buses gets the unweighted mean across them. These are modelled
    locational prices, not day-ahead auction prices, and are labelled as such
    wherever they are displayed.
    """
    if "marginal_price" not in n.buses_t:
        return pd.DataFrame(index=n.snapshots)
    prices = n.buses_t.marginal_price
    return _aggregate_by_country(prices, _bus_country(n), how="mean")


def extract_hourly_carbon(n: pypsa.Network, load: pd.DataFrame) -> pd.DataFrame:
    """Snapshots x country -> carbon intensity (gCO2e/MWh of electricity).

    Operational emissions of the country divided by that country's own load in
    the same hour. Dividing by a near-zero load produces meaningless intensities
    (a country whose buses happen to run coal in an hour it consumes almost
    nothing reads as thousands of gCO2e/MWh), so hours where load falls below
    1% of that country's mean load are left empty rather than reported.

    The figure is domestic emissions over domestic load, so a country that
    exports fossil-heavy power while importing little reads high: the exported
    MWh are credited to the importing country's intensity, not the exporter's.
    Expect the lignite-heavy south-east (MK, XK, RS, CZ, BG) to run well above
    the north-west, and the values to peak in the morning hours when solar is
    zero. This is a property of the definition, not a modelling error; it is not
    comparable to a consumption-based national inventory.
    """
    emissions = _hourly_co2_t(n)  # tonnes CO2e per country-hour
    if emissions.empty:
        return pd.DataFrame(index=n.snapshots)
    aligned = load.reindex(columns=emissions.columns).fillna(0.0)
    floor = aligned.mean() * 0.01
    # tonnes CO2e per MWh -> gCO2e per MWh is x1e3.
    intensity = emissions.div(aligned.where(aligned > floor)) * 1e3
    intensity.index.name = "timestamp"
    return intensity


def extract_hourly_flow(n: pypsa.Network) -> pd.DataFrame:
    """Snapshots x border -> net flow (MW). Positive = country_a -> country_b.

    AC lines and DC links are both oriented bus0 -> bus1 and are sign-flipped
    onto the canonical direction (the lexicographically smaller country code
    first). Every asset joining the same pair of countries is then summed, so a
    border with both an AC line and an interconnector reports the net transfer
    across that border rather than one asset's contribution.
    """
    buses = n.buses

    def _country(name: str) -> str:
        return _str(buses.at[name, "country"]) if name in buses.index else ""

    frames = []
    # Filters mirror extract_cross_borders so that the flow columns and the
    # cross_borders asset list describe the same set of borders.
    for table, pcol, nominal, carriers in (
        (n.lines, n.lines_t.p0, "s_nom", None),
        (n.links, n.links_t.p0, "p_nom", ("DC", "B2B")),
    ):
        for name in pcol.columns:
            if carriers and _str(table.at[name, "carrier"]) not in carriers:
                continue
            if float(table.at[name, nominal] or 0.0) <= 0:
                continue
            a0, b0 = _str(table.at[name, "bus0"]), _str(table.at[name, "bus1"])
            ca, cb = _country(a0), _country(b0)
            if not ca or not cb or ca == cb:
                continue
            series = pcol[name].copy()
            # Canonical direction: lexicographically smaller country code first.
            label = f"{sorted([ca, cb])[0]}-{sorted([ca, cb])[1]}"
            if ca != sorted([ca, cb])[0]:
                series = -series
            frames.append((label, series))
    # Sum every asset on the same border
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

    carrier_of = n.generators.set_index(n.generators.index)["carrier"]
    # generators_t is MW; snapshots are hourly with unit weights, so the sum over
    # time is MWh and GWh is that scaled by 1e-3.
    by_carrier_gwh = (n.generators_t.p.T.groupby(carrier_of).sum().T.sum(axis=0) * 1e-3).to_dict()

    # Operational CO2, using the same efficiency-corrected arithmetic as the
    # per-country hourly series.
    co2_t = float(_hourly_co2_t(n).sum().sum())
    co2_kt = co2_t / 1e3
    # tonnes CO2e per MWh -> gCO2e per kWh is x1e3 (1 t = 1e6 g, 1 MWh = 1e3 kWh).
    carbon_intensity = round(co2_t * 1e3 / total_load_mwh, 1) if total_load_mwh > 0 else None

    summary = {
        "n_countries": len(countries),
        "n_generators": len(generators),
        "n_snapshots": len(n.snapshots),
        "start": str(n.snapshots[0]),
        "end_exclusive": str(n.snapshots[-1]),
        "capacity_by_fuel_mw": {k: round(v, 1) for k, v in sorted(fuel_capacity.items())},
        "generation_by_carrier_gwh": {k: round(v, 1) for k, v in sorted(by_carrier_gwh.items())},
        "total_load_gwh": round(total_load_mwh / 1e3, 1),
        "total_generation_gwh": round(total_gen_mwh / 1e3, 1),
        "total_co2_kt": round(co2_kt, 1),
        "carbon_intensity_gco2_per_mwh": carbon_intensity,
    }
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_hourly(df: pd.DataFrame, path: Path, decimals: int = 3) -> None:
    """Write an hourly series with ISO-8601 UTC timestamps.

    pandas writes a DatetimeIndex as '2025-03-01 00:00:00', which is not the
    ISO-8601 UTC form the app and the rest of the research artefacts use.

    Values are rounded before writing. The full-year window is ~12x this size
    and the app parses these files into its own memory budget, so carrying 17
    significant figures through the CSV buys nothing: 0.001 EUR/MWh on a price
    and 1 kW on a load are far below the model's own accuracy.
    """
    out = df.round(decimals)
    out.index = pd.DatetimeIndex(out.index).strftime("%Y-%m-%dT%H:%M:%SZ")
    out.index.name = "timestamp"
    out.to_csv(path)


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

    # pypsa is only needed to read the network, so it is imported here rather
    # than at module scope: the aggregation and unit-conversion logic above is
    # then importable (and testable) on a host Python without the pixi env.
    import pypsa

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
    _write_hourly(dispatch, out / "hourly_dispatch.csv")
    print(f"  -> {dispatch.shape}")

    print("[extract] Hourly load...")
    load = extract_hourly_load(n)
    _write_hourly(load, out / "hourly_load.csv")
    print(f"  -> {load.shape}")

    print("[extract] Hourly price...")
    price = extract_hourly_price(n)
    _write_hourly(price, out / "hourly_price.csv")
    print(f"  -> {price.shape}")

    print("[extract] Hourly carbon intensity...")
    carbon = extract_hourly_carbon(n, load)
    _write_hourly(carbon, out / "hourly_carbon.csv")
    print(f"  -> {carbon.shape}")

    print("[extract] Hourly flow...")
    flow = extract_hourly_flow(n)
    if not flow.empty:
        _write_hourly(flow, out / "hourly_flow.csv")
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