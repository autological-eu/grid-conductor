"""Offline ENTSO-E carbon feasibility pilot. Python standard library only.

Never writes credentials or modifies application tables. See docs/carbon-pilot.md.
"""
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[1]
AREAS = {"FR": "10YFR-RTE------C", "DE": "10Y1001A1001A83F",
         "DK-DK1": "10YDK-1--------W", "DK-DK2": "10YDK-2--------M"}
# Germany's generation country domain differs from its DE-LU price domain.
IPCC = "https://archive.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf"
FACTORS = {
    "B01": (230, "Dedicated biomass proxy; biogenic accounting matters"),
    "B02": (820, "Pulverised coal proxy for lignite"),
    "B04": (490, "Combined-cycle gas proxy for all reported gas"),
    "B05": (820, "Pulverised coal"),
    "B09": (38, "Geothermal"),
    "B11": (24, "Hydropower proxy for run-of-river"),
    "B12": (24, "Hydropower proxy for reservoir"),
    "B13": (17, "Ocean energy"),
    "B14": (12, "Nuclear"),
    "B16": (48, "Utility PV proxy for all reported solar"),
    "B18": (12, "Offshore wind"),
    "B19": (11, "Onshore wind"),
}
FACTOR_VERSION = "ipcc-ar5-annex-iii-medians-pilot-v1"
STORAGE = {"B10", "B25"}


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamps must include a UTC offset")
    return result.astimezone(UTC)


def iso(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def put_sample(series, kind, instant, value):
    slots = series.setdefault(kind, {})
    if instant in slots and slots[instant] != value:
        raise ValueError(f"Conflicting overlapping generation: {kind} {instant}")
    slots[instant] = value


def parse_generation(raw, area):
    """Normalize MW intervals to quarter-hours; A03 is a stepwise curve.

    A01 gaps remain missing. Conflicting overlaps fail, rather than summing
    revisions or mixing area aggregates. Consumption series are excluded.
    """
    root = ET.fromstring(raw)
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
    if root.tag != "GL_MarketDocument":
        raise ValueError("ENTSO-E did not return a generation document")
    series = {}
    for ts in root.findall("TimeSeries"):
        if ts.find("outBiddingZone_Domain.mRID") is not None:
            continue
        if ts.findtext("inBiddingZone_Domain.mRID") != area:
            raise ValueError("Unexpected generation area")
        if ts.findtext("quantity_Measure_Unit.name") != "MAW":
            raise ValueError("Expected MW generation")
        if ts.findtext("businessType") != "A01" or ts.findtext("objectAggregation") != "A08":
            raise ValueError("Expected production aggregated by resource type")
        kind = ts.findtext("MktPSRType/psrType")
        if not kind:
            raise ValueError("Missing production type")
        curve = ts.findtext("curveType")
        if curve not in {"A01", "A03"}:
            raise ValueError(f"Unsupported curve: {curve}")
        series.setdefault(kind, {})
        for period in ts.findall("Period"):
            start = timestamp(period.findtext("timeInterval/start"))
            end = timestamp(period.findtext("timeInterval/end"))
            resolution = period.findtext("resolution")
            minutes = {"PT15M": 15, "PT30M": 30, "PT60M": 60}.get(resolution)
            if minutes is None or start.minute % 15 or start.second or end <= start:
                raise ValueError("Unsupported generation interval")
            count_float = (end - start).total_seconds() / (minutes * 60)
            if not count_float.is_integer():
                raise ValueError("Misaligned period end")
            count = int(count_float)
            points = {}
            for point in period.findall("Point"):
                pos = int(point.findtext("position"))
                value = float(point.findtext("quantity"))
                if pos < 1 or pos > count or pos in points:
                    raise ValueError("Invalid or repeated point position")
                points[pos] = value if math.isfinite(value) and value >= 0 else None
            previous = None
            for pos in range(1, count + 1):
                if pos in points:
                    previous = points[pos]
                value = previous if curve == "A03" else points.get(pos)
                for quarter in range(minutes // 15):
                    instant = start + dt.timedelta(minutes=(pos - 1) * minutes + quarter * 15)
                    put_sample(series, kind, instant, value)
    if not series:
        raise ValueError("No production series returned")
    return series


def calculate(series, zone, start, end, unknown_factor=1500):
    """Energy-weighted hourly intensities of primary generation only.

    Unmapped generation is NEVER zero-filled into a central estimate. Two
    explicit sensitivity scenarios use 0 and a configurable factor instead.
    They are not confidence intervals or scientifically guaranteed bounds.
    """
    primary = sorted(set(series) - STORAGE)
    if not primary:
        raise ValueError("No primary generation categories")
    rows = []
    hour = start
    while hour < end:
        energy, missing = {}, []
        for kind, samples in series.items():
            values = [samples.get(hour + dt.timedelta(minutes=15 * i)) for i in range(4)]
            if any(v is None for v in values):
                missing.append(kind)
            else:
                energy[kind] = sum(values) / 4  # MW * 0.25 h => MWh
        row = {"zone": zone, "start": iso(hour), "basis": "reported_primary_production",
               "emission_factor_type": "lifecycle", "unit": "gCO2e/kWh",
               "factor_version": FACTOR_VERSION, "missing_types": missing,
               "reported_types": sorted(series), "generation_mwh_by_type": energy,
               "carbon_intensity": None, "mapped_mix_intensity": None,
               "mapped_generation_share": None, "sensitivity_low": None,
               "sensitivity_high": None, "primary_generation_mwh": None,
               "storage_discharge_mwh": sum(energy[k] for k in STORAGE if k in energy),
               "storage_data_complete": not (set(missing) & STORAGE)}
        if set(missing) & set(primary):
            row["status"] = "missing_generation"
        else:
            total = sum(energy[k] for k in primary)
            mapped = sum(energy[k] for k in primary if k in FACTORS)
            unknown = total - mapped
            emissions = sum(energy[k] * FACTORS[k][0] for k in primary if k in FACTORS)
            row["primary_generation_mwh"] = total
            row["unmapped_types"] = [k for k in primary if k not in FACTORS and energy[k] > 0]
            if total <= 0:
                row["status"] = "zero_generation"
            else:
                row.update(mapped_generation_share=mapped / total,
                           mapped_mix_intensity=emissions / mapped if mapped else None,
                           sensitivity_low=emissions / total,
                           sensitivity_high=(emissions + unknown * unknown_factor) / total,
                           status="partial_factor_coverage" if unknown > 1e-8 else "complete")
                if row["status"] == "complete":
                    row["carbon_intensity"] = emissions / total
        rows.append(row)
        hour += dt.timedelta(hours=1)
    return rows


def download(zone, start, end, directory):
    """Cache one UTC month, with secret-free request metadata and SHA-256."""
    path = directory / f"{zone}-{start:%Y%m%d}-{end:%Y%m%d}.xml"
    metadata_path = path.with_suffix(".metadata.json")
    params = {"documentType": "A75", "processType": "A16", "in_Domain": AREAS[zone],
              "periodStart": start.strftime("%Y%m%d%H%M"), "periodEnd": end.strftime("%Y%m%d%H%M")}
    if path.exists() and metadata_path.exists():
        raw = path.read_bytes()
        metadata = json.loads(metadata_path.read_text())
        if metadata["sha256"] != hashlib.sha256(raw).hexdigest() or metadata["request"] != params:
            raise ValueError("Raw cache integrity check failed")
        return raw, metadata
    token = os.environ.get("ENTSOE_API_KEY")
    if not token:
        raise ValueError("Set ENTSOE_API_KEY to download; cached runs need no key")
    url = "https://web-api.tp.entsoe.eu/api?" + urllib.parse.urlencode(dict(params, securityToken=token))
    try:
        with urllib.request.urlopen(url, timeout=90) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ENTSO-E request failed: HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("ENTSO-E connection failed; request URL withheld") from None
    parse_generation(raw, AREAS[zone])
    metadata = {"provider": "ENTSO-E Transparency Platform", "request": params,
                "retrieved_at": iso(dt.datetime.now(UTC)), "sha256": hashlib.sha256(raw).hexdigest()}
    directory.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return raw, metadata


def comparison(rows, archive):
    """Cross-basis diagnostics, not validation errors or ground truth."""
    with closing(sqlite3.connect(archive.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        values = {(z, t): (v, estimated) for z, t, v, estimated in db.execute(
            "SELECT zone,start,value,estimated FROM observations WHERE metric='carbon' AND start>=? AND start<=?",
            (min(r["start"] for r in rows), max(r["start"] for r in rows)))}
    result = {}
    for zone in sorted({r["zone"] for r in rows}):
        pairs = [(r, values.get((zone, r["start"]))) for r in rows if r["zone"] == zone]
        pairs = [(r, v) for r, v in pairs if r["sensitivity_low"] is not None and v and v[0] is not None]
        result[zone] = {"matched_hours": len(pairs),
                        "comparison_type": "production-versus-consumption diagnostic; not accuracy",
                        "electricity_maps_basis": "consumption_lifecycle",
                        "estimated_benchmark_hours": sum(bool(v[1]) for _, v in pairs)}
        if pairs:
            result[zone].update(
                electricity_maps_mean=statistics.mean(v[0] for _, v in pairs),
                pilot_sensitivity_low_mean=statistics.mean(r["sensitivity_low"] for r, _ in pairs),
                pilot_sensitivity_high_mean=statistics.mean(r["sensitivity_high"] for r, _ in pairs))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default="2026-08", help="UTC calendar month YYYY-MM")
    parser.add_argument("--zones", nargs="+", choices=AREAS, default=list(AREAS))
    parser.add_argument("--archive", type=Path, help="Read-only Electricity Maps indicators.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "data/carbon-pilot/entsoe")
    parser.add_argument("--unknown-factor", type=float, default=1500,
                        help="Unmapped-fuel high sensitivity assumption, gCO2e/kWh; not a bound")
    args = parser.parse_args()
    if not math.isfinite(args.unknown_factor) or args.unknown_factor < 0:
        parser.error("unknown-factor must be finite and nonnegative")
    start = dt.datetime.strptime(args.month, "%Y-%m").replace(tzinfo=UTC)
    end = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    rows, provenance = [], {}
    for zone in args.zones:
        raw, metadata = download(zone, start, end, args.output / "raw")
        rows.extend(calculate(parse_generation(raw, AREAS[zone]), zone, start, end, args.unknown_factor))
        provenance[zone] = metadata
        print(f"Processed {zone}", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    run = args.output / args.month
    run.mkdir(exist_ok=True)
    (run / "hourly.jsonl").write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in rows), encoding="utf-8")
    summary = {"start": iso(start), "end_exclusive": iso(end), "source": provenance,
               "factor_version": FACTOR_VERSION, "factor_source": IPCC,
               "factors": FACTORS, "unknown_factor_scenarios": [0, args.unknown_factor],
               "limitations": ["Reported primary generation, not consumption or marginal emissions",
                               "Generic technology factors, not country-specific factors",
                               "Absent production categories cannot be assumed zero",
                               "Sensitivity range is not a confidence interval",
                               "Storage discharge excluded; incomplete storage flagged separately"],
               "zones": {}}
    for zone in args.zones:
        group = [r for r in rows if r["zone"] == zone]
        valid = [r for r in group if r["sensitivity_low"] is not None]
        summary["zones"][zone] = {"hours": len(group), "usable_sensitivity_hours": len(valid),
            "complete_estimate_hours": sum(r["carbon_intensity"] is not None for r in group),
            "reported_types": group[0]["reported_types"],
            "unmapped_types": sorted({k for r in valid for k in r.get("unmapped_types", [])}),
            "energy_weighted_mapped_share": (sum(r["mapped_generation_share"] * r["primary_generation_mwh"] for r in valid)
                                             / sum(r["primary_generation_mwh"] for r in valid)) if valid else None}
    if args.archive:
        summary["benchmark"] = comparison(rows, args.archive)
        summary["benchmark_archive"] = str(args.archive.resolve())
    (run / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"results": str(run), "zones": summary["zones"], "benchmark": summary.get("benchmark")}, indent=2))


if __name__ == "__main__":
    main()
