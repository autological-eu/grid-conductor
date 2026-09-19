#!/usr/bin/env python3
"""Build a PyPSA-Eur operational network for Grid Conductor.

Runs the Snakemake pipeline (through pixi; directly on native Linux or WSL, or
via the WSL distro on Windows) from raw data through to a solved electricity
network, validates the output, and writes a manifest consumed by
extract_baseline.py and pypsa_border_targets.py.

Everything (window, clusters, run name, resolution) comes from the selected
config file. Default is the full-year production config; pass --config to use a
test-month config instead.

Usage:
    python tools/build_pypsa_network.py [--config config/pypsa-eur/full-year.yaml]
                                         [--dry-run] [--cutout-only]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "data" / "pypsa-eur" / "upstream"
PIXI = ROOT / "data" / "pypsa-eur" / "bin" / "pixi"
CONFIG_DIR = ROOT / "config" / "pypsa-eur"
DEFAULT_CONFIG = CONFIG_DIR / "full-year.yaml"
MANIFEST_PATH = ROOT / "data" / "pypsa-eur" / "baseline-manifest.json"
UPSTREAM_COMMIT = "a5408e9db5402c53345d7339fffb52afe96d6e43"

# pixi runs directly on native Linux/WSL; on a Windows host it runs inside the
# WSL distro where roots are mounted at /mnt/<drive>/<path>.
WSL_DISTRO = os.environ.get("GRID_CONDUCTOR_WSL", "Ubuntu")


def _on_posix() -> bool:
    return sys.platform.startswith("linux") or os.name == "posix"


def _inside_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _wsl_path(path: Path) -> str:
    if _on_posix():
        return str(path.resolve())
    rel = str(path.resolve())
    parts = rel.replace("\\", "/").split(":")
    drive, rest = parts[0].lower(), parts[1].lstrip("/") if len(parts) > 1 else parts[0]
    return f"/mnt/{drive}/{rest}"


def _run_wsl(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a command in the Linux environment.

    Directly on native Linux or inside WSL; through the `wsl` distro on a Windows
    host (override the distro with GRID_CONDUCTOR_WSL).
    """
    cwd = cwd or UPSTREAM
    quoted = shlex.join([c for c in cmd if c])
    if _on_posix():
        result = subprocess.run(
            ["bash", "-lc", f"cd '{_wsl_path(cwd)}' && {quoted}"],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "--", "bash", "-lc", f"cd {shlex.quote(_wsl_path(cwd))} && {quoted}"],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        print("STDOUT:\n" + result.stdout[-3000:], file=sys.stderr)
        print("STDERR:\n" + result.stderr[-5000:], file=sys.stderr)
        sys.exit(1)
    return result


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------

def check_prerequisites() -> None:
    """Verify CDS key, pixi/WSL, and upstream checkout exist before Snakemake runs."""
    cds_rc = ROOT / "data" / "pypsa-eur" / ".cdsapirc"
    home_rc = Path.home() / ".cdsapirc"
    if not cds_rc.exists() and not home_rc.exists():
        sys.exit(
            "ERROR: CDS API key not found. Create data/pypsa-eur/.cdsapirc with:\n"
            "  url: https://cds.climate.copernicus.eu/api\n"
            "  key: <your-key>"
        )
    print("[prereq] CDS API key present.")

    if not PIXI.exists():
        sys.exit(
            f"ERROR: pixi not found at {PIXI}. Run the pixi Linux installer and copy the binary there."
        )
    try:
        _run_wsl(["true"])
    except SystemExit as exc:
        if isinstance(exc.code, int) and exc.code == 1:
            sys.exit(f"ERROR: Linux environment not reachable. Set GRID_CONDUCTOR_WSL.")
        raise
    except FileNotFoundError:
        sys.exit("ERROR: `wsl` command not found on PATH (required on this Windows host).")
    host = "Linux" if _on_posix() else f"WSL distro '{WSL_DISTRO}'"
    print(f"[prereq] {host} reachable; pixi present.")

    if not (UPSTREAM / "Snakefile").exists():
        sys.exit(f"ERROR: Snakefile not found at {UPSTREAM / 'Snakefile'}")
    if not DEFAULT_CONFIG.exists():
        sys.exit(f"ERROR: Config not found at {DEFAULT_CONFIG}")
    print("[prereq] Upstream checkout and config OK.")


def _deep_update(base: dict, overlay: dict) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def _load_config(config_path: Path) -> dict:
    """Load a config over config.default.yaml the way Snakemake merges them."""
    default_path = UPSTREAM / "config" / "config.default.yaml"
    merged = copy.deepcopy(yaml.safe_load(default_path.read_text(encoding="utf-8")) or {})
    specific = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    _deep_update(merged, specific)
    return merged


def _run_context(config: dict) -> tuple[str, str, str, int]:
    """Extract (run_name, start, end_exclusive, clusters) from config."""
    run_name = config["run"]["name"]
    start = config["snapshots"]["start"]
    end = config["snapshots"].get("end")
    if end:
        end_exclusive = end
    else:
        # snapshots may be a single year string like '2025'
        end_exclusive = str(int(start[:4]) + 1)
    clusters = config["scenario"]["clusters"][0]
    return run_name, start, end_exclusive, clusters


# ---------------------------------------------------------------------------
# Snakemake invocation
# ---------------------------------------------------------------------------

def run_snakemake(
    config_path: Path,
    dry_run: bool = False,
    cutout_only: bool = False,
) -> str:
    """Run Snakemake through pixi and return the path to the solved network
    (relative to UPSTREAM directory)."""
    config = _load_config(config_path)
    run_name, _start, _end, clusters = _run_context(config)

    pixi_w = _wsl_path(PIXI)
    config_w = _wsl_path(config_path)
    snake_w = _wsl_path(UPSTREAM / "Snakefile")

    if cutout_only:
        # Build every configured cutout (default + any secondaries e.g. the
        # full-year runoff-only cutout used by the hydro profile).
        cutout_names = [config["atlite"]["default_cutout"]] + [
            name
            for name in config["atlite"].get("cutouts", {})
            if name != config["atlite"]["default_cutout"]
        ]
        source = config["data"]["cutout"]["source"]
        version = "unknown"  # upstream versions.csv tags build cutouts with version 'unknown'
        target = ";".join(
            f"data/cutout/{source}/{version}/{name}.nc" for name in cutout_names
        )
        targets = [
            f"data/cutout/{source}/{version}/{name}.nc" for name in cutout_names
        ]
        print(f"[snakemake] Cutout targets derived from config: {targets}")
    else:
        solved_rel = f"results/{run_name}/networks/base_s_{clusters}_elec_.nc"
        solved_abs = UPSTREAM / solved_rel
        targets = [solved_rel]

    snakemake_cmd = [
        str(pixi_w),
        "run",
        "snakemake",
        *targets,
        "--configfile",
        config_w,
        "--snakefile",
        snake_w,
        "-j",
        "1",
    ]

    if dry_run:
        snakemake_cmd.append("--dryrun")
        print(f"[snakemake] Dry run: {' '.join(snakemake_cmd)}")
        result = _run_wsl(snakemake_cmd)
        print(result.stdout[-4000:])
        return ";".join(targets)

    print(f"[snakemake] Building: {'; '.join(targets)}")
    print(f"[snakemake] Config:   {config_path}")
    _run_wsl(snakemake_cmd)

    if not cutout_only:
        if not solved_abs.exists():
            sys.exit(
                f"ERROR: Solved network not found at {solved_abs} after Snakemake completed.\n"
                "Check Snakemake logs in data/pypsa-eur/upstream/logs/"
            )
        print(f"[snakemake] Solved network: {solved_abs}")
        return solved_rel
    return ";".join(targets)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _host_pypsa() -> bool:
    return importlib.util.find_spec("pypsa") is not None


def validate_network(network_path: Path) -> dict:
    """Load the solved network via pypsa and perform sanity checks."""
    import pypsa

    print(f"[validate] Loading {network_path}")
    n = pypsa.Network(network_path)

    snapshots = n.snapshots
    if len(snapshots) != 8760:
        print(f"  WARNING: expected 8760 hourly snapshots, got {len(snapshots)}")

    # No extendable investment decisions
    for table in (
        n.generators, n.links, n.lines, n.transformers,
        n.storage_units, n.stores,
    ):
        for flag in ("p_nom_extendable", "s_nom_extendable", "e_nom_extendable"):
            if flag in table and table[flag].any():
                raise ValueError(
                    f"Disable all investment decisions before baseline dispatch "
                    f"({flag} on {table.name})"
                )

    # Nonzero generation and load
    if n.generators.empty or n.loads.empty:
        raise ValueError("Base topology has no operational generation/demand inputs")

    # NaN check on critical columns
    for table, cols in (
        (n.generators, ("p_nom", "carrier")),
        (n.links, ("bus0", "bus1")),
    ):
        for col in cols:
            if col in table:
                nans = int(table[col].isna().sum())
                if nans:
                    print(f"  WARNING: {nans} NaN in {table.name}.{col}")

    total_load_mwh = float(n.loads_t.p.sum().sum())
    total_gen_mwh = float(n.generators_t.p.sum().sum())
    if total_load_mwh <= 0:
        raise ValueError("Zero total load in solved network")

    # Cross-border connectivity
    buses = n.buses
    def _country(name: str) -> str:
        try:
            return str(buses.at[name, "country"])
        except Exception:
            return ""
    cross_links = sum(
        1
        for _name, row in n.links.iterrows()
        if row.get("carrier") == "DC" and _country(row.bus0) != _country(row.bus1)
    )
    cross_lines = sum(
        1
        for _name, row in n.lines.iterrows()
        if _country(row.bus0) != _country(row.bus1)
    )
    countries = set()
    for table in (n.links, n.lines):
        for _name, row in table.iterrows():
            countries.add(_country(row.bus0))
            countries.add(_country(row.bus1))
    countries.discard("")

    # CO2 from carrier emission factors
    co2_by_carrier = {}
    if "co2_emissions" in n.carriers:
        co2_by_carrier = n.carriers["co2_emissions"].to_dict()

    # Per-carrier generation and operational CO2
    gen = n.generators
    carrier_of = gen.set_index(gen.index)["carrier"]
    by_carrier = n.generators_t.p.T.groupby(carrier_of).sum().T.sum(axis=0) * 1e-6  # GWh
    co2_kt = 0.0
    if len(n.generators_t.p):
        efficiency = n.get_switchable_as_dense("Generator", "efficiency")
        factors = gen.carrier.map(co2_by_carrier).fillna(0.0)
        weights = n.snapshot_weightings["generators"].to_numpy(dtype=float)
        co2_t = float(
            ((n.generators_t.p / efficiency) * factors).mul(weights, axis=0).sum().sum()
        )
        co2_kt = co2_t / 1e3  # tonnes -> kt

    stats = {
        "n_snapshots": len(snapshots),
        "n_buses": len(n.buses),
        "n_generators": len(n.generators),
        "n_links": len(n.links),
        "n_lines": len(n.lines),
        "n_countries": len(countries),
        "n_cross_border_dc_links": cross_links,
        "n_cross_border_ac_lines": cross_lines,
        "total_load_gwh": round(total_load_mwh / 1e3, 1),
        "total_generation_gwh": round(total_gen_mwh / 1e3, 1),
        "generation_by_carrier_gwh": {k: round(v, 1) for k, v in by_carrier.to_dict().items()},
        "total_co2_from_dispatch_kt": round(co2_kt, 1),
        "marginal_price_eur_mwh_mean": round(float(n.buses_t.marginal_price.mean().mean()), 2) if "marginal_price" in n.buses_t else None,
    }
    print(f"[validate] {json.dumps(stats, indent=2)}")
    return stats


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------

def write_manifest(
    solved_abs: Path,
    config_path: Path,
    validation_stats: dict,
) -> Path:
    """Write baseline-manifest.json consumed by extract_baseline.py and
    pypsa_border_targets.py."""
    config = _load_config(config_path)
    run_name, start, end_exclusive, clusters = _run_context(config)

    manifest = {
        "version": 1,
        "built_at": _now_iso(),
        "run_name": run_name,
        "config_file": config_path.relative_to(ROOT).as_posix(),
        "start": start,
        "end_exclusive": end_exclusive,
        "clusters": clusters,
        "network_file": solved_abs.relative_to(UPSTREAM).as_posix(),
        "network_sha256": _digest(solved_abs),
        "upstream_commit": UPSTREAM_COMMIT,
        "assumptions": {
            "solver": config["solving"]["solver"]["name"],
            "unit_commitment": config["conventional"].get("unit_commitment", False),
            "investment_planning": "disabled",
            "extension_carriers": config["electricity"].get("extendable_carriers", {}),
            "transmission_limit": config["electricity"].get("transmission_limit"),
            "time_resolution_h": 1,
            "clusters": clusters,
            "co2_limit": None,
            "costs_year": config["costs"].get("year"),
        },
        "sources": {
            "osm": config["data"].get("osm"),
            "powerplants": config["data"].get("powerplants"),
            "entsoe_electricity_demand": config["data"].get("entsoe_electricity_demand"),
            "cutout": config["data"].get("cutout", {"source": "build"}),
            "upstream": {"revision": UPSTREAM_COMMIT},
        },
        "validation": validation_stats,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(MANIFEST_PATH)
    print(f"[manifest] Written to {MANIFEST_PATH}")
    return MANIFEST_PATH


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build PyPSA-Eur operational baseline")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to config YAML under config/pypsa-eur/",
    )
    parser.add_argument("--dry-run", action="store_true", help="Snakemake dry run only")
    parser.add_argument(
        "--cutout-only",
        action="store_true",
        help="Only build/download the ERA5 cutout and stop",
    )
    parser.add_argument(
        "--postprocess",
        type=Path,
        help="Internal: validate a solved network and write the manifest under pixi",
    )
    args = parser.parse_args()

    if args.postprocess:
        config = _load_config(args.config)
        stats = validate_network(args.postprocess)
        print()
        write_manifest(args.postprocess, args.config, stats)
        return

    config = _load_config(args.config)
    run_name, start, end_exclusive, clusters = _run_context(config)
    print("=== PyPSA-Eur Baseline Build ===")
    resolved = args.config.resolve()
    config_label = resolved.relative_to(ROOT) if resolved.is_relative_to(ROOT) else args.config
    print(
        f"Run: {run_name}  Window: {start} -> {end_exclusive}  Clusters: {clusters}  "
        f"Config: {config_label}"
    )
    print()

    check_prerequisites()
    print()

    target = run_snakemake(args.config, args.dry_run, args.cutout_only)
    print()

    if not args.dry_run and not args.cutout_only:
        solved_abs = UPSTREAM / target
        if not _host_pypsa():
            print("[validate] host Python has no pypsa; re-invoking post-process under pixi")
            cmd = [
                str(PIXI),
                "run",
                "python",
                str(ROOT / "tools" / "build_pypsa_network.py"),
                "--postprocess",
                str(solved_abs),
                "--config",
                str(args.config.resolve()),
            ]
            _run_wsl(cmd)
            return
        stats = validate_network(solved_abs)
        print()
        write_manifest(solved_abs, args.config, stats)
    else:
        print(f"[{'dry-run' if args.dry_run else 'cutout'}] Skipping validation and manifest.")


if __name__ == "__main__":
    main()
