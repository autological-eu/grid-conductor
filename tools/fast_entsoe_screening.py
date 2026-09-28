"""Step-1 fast ENTSO-E border screening over the cached EU-market banks (v2).

Reads only locally cached `data/eu-market/bank-*-v2.json` (schema_v2; quarter-hour
A44 prices per bidding zone, directed A11 flows, directed A61 day-ahead caps).
No network, no ENTSO-E key, no scipy required (numpy only). For every interior
border, in BOTH directions (`a>b` and `b>a`), it computes:

  * realized_rent_meur_*    = 1e-6 * 0.25 * sum_t F_AB,t * (P_B,t - P_A,t)  [signed]
  * positive_rent_meur_*    = same but only where the spread is positive
                              (the congestion rent the capacity actually earns)
  * opportunity_meur_*[dc]  = 1e-6 * 0.25 * sum_t max(0, P_B,t - P_A,t) * dc
                              for dc in {500, 1000} MW  (theoretical ladder)
  * congested_quarters      = quarter-hours with positive spread > 5 EUR/MWh
  * average_positive_spread = mean of the profitable-spread samples
  * slope_{a,b}             = effective dP/d(f) slope per zone (Step-2 LP
                              input), OLS of zone price on net scheduled
                              inflow, clamped to 0 when the raw fit is <= 0.
  * slope_raw_{a,b}         = the raw OLS slope (may be negative / null).

Energy sums carry the 0.25 h factor because the bank series are quarter-hour
samples (energy = MW * 0.25 h). Field suffixes are `_month` for a single bank
and `_year` for a calendar-year concat (see concat_banks); the year rows are
full-year sums, NOT an x12 extrapolation.

Outputs `public/research/entsoe-fast-targets.json` (schema_version 3: annual
`targets` ranked by theoretical opportunity, plus per-month `monthly`
diagnostics and a coverage summary). Published data is deterministic and
resumable; rerunning over the same cache is a no-op.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "data" / "eu-market"
PUBLIC = ROOT / "public" / "research"
OUT = PUBLIC / "entsoe-fast-targets.json"
LADDERS = (500, 1000)  # candidate cable capacity increments in MW
HOURS_PER_SAMPLE = 0.25  # bank series are quarter-hour (energy = MW * 0.25 h)
SAMPLE_MIN = dt.timedelta(minutes=15)


def read_bank(path):
    bank = json.loads(path.read_text(encoding="utf-8"))
    if bank.get("schema_version") != 2:
        raise ValueError(f"{path.name}: expected schema_version 2, got {bank.get('schema_version')}")
    return bank


def border_pairs(bank):
    return [tuple(b) for b in bank.get("interior_borders", [])]


def price_series(bank, zone):
    return bank.get("prices", {}).get(zone)


def _fmt_dt(value):
    """Format a datetime as ENTSO-E period text 'YYYYMMDDHHMM'."""
    return value.strftime("%Y%m%d%H%M")


def _parse_dt(text):
    for fmt in ("%Y%m%d%H%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(str(text), fmt)
        except (TypeError, ValueError):
            continue
    return None


def bank_window(bank):
    """Resolve the bank's time window as (start, end) datetimes.

    Uses the ENTSO-E `period` block (periodStart/periodEnd) when present,
    otherwise derives a window from the `month` label and the series length.
    """
    period = bank.get("period")
    if isinstance(period, dict):
        start = _parse_dt(period.get("periodStart"))
        end = _parse_dt(period.get("periodEnd"))
        if start and end:
            return start, end
    if isinstance(period, str) and ">" in period:
        start, end = map(_parse_dt, period.split(">", 1))
        if start and end:
            return start, end
    month = bank.get("month")
    if month:
        start = _parse_dt(month + "-01 00:00")
        if start:
            series = next(iter(bank.get("prices", {}).values()), None)
            length = len(series) if series is not None else 0
            return start, start + SAMPLE_MIN * length
    raise ValueError("cannot resolve bank window (no period/month metadata)")


def concat_banks(banks, year=None):
    """Merge monthly banks into one calendar-year bank on a NaN-padded grid.

    All banks are quarter-hour aligned on contiguous month boundaries, so the
    global grid is [min(periodStart), max(periodEnd)) at 15-min resolution.
    Every zone / directed flow / directed cap series is reindexed onto that
    grid (missing intervals become NaN) and concatenated bank-by-bank. The
    merged bank carries `month` = the year label and the full `period` window,
    so `screening` can treat it exactly like a physical month.
    """
    starts, ends = zip(*[bank_window(b) for b in banks])
    start = min(starts)
    end = max(ends)
    total = int((end - start) / SAMPLE_MIN)
    if total <= 0:
        raise ValueError("empty concat window")

    zones = set()
    directed = set()
    for b in banks:
        zones |= set(b.get("prices", {}))
        directed |= set(b.get("flows_mw", {})) | set(b.get("caps_mw", {}))
    borders = sorted(
        set(tuple(sorted(z.split(">"))) for z in directed if ">" in z)
        | {tuple(p) for b in banks for p in border_pairs(b)}
    )

    # Build the merged bank from aligned series (NaN-padded global grid).
    prices = {}
    for zone in sorted(zones):
        prices[zone] = [float(v) for v in align_series_for_zone(banks, zone, start, total)]
    flows = {}
    caps = {}
    for key in sorted(directed):
        flows[key] = [float(v) for v in align_directed(banks, key, "flows_mw", start, total)]
        caps[key] = [float(v) for v in align_directed(banks, key, "caps_mw", start, total)]

    bank = dict(
        schema_version=2,
        month=str(year) if year is not None else None,
        period={"periodStart": _fmt_dt(start), "periodEnd": _fmt_dt(end)},
        interior_borders=borders,
        prices=prices,
        flows_mw=flows,
        caps_mw=caps,
        concat_of=[b.get("month") for b in banks],
    )
    return bank


def align_series_for_zone(banks, zone, start, total):
    out = np.full(total, np.nan)
    for i, b in enumerate(banks):
        series = b.get("prices", {}).get(zone)
        if series is None:
            continue
        b_start, _ = bank_window(b)
        off = int((b_start - start) / SAMPLE_MIN)
        arr = np.asarray(series, dtype=float)
        out[off : off + len(arr)] = arr
    return out


def align_directed(banks, key, table, start, total):
    out = np.full(total, np.nan)
    for i, b in enumerate(banks):
        series = b.get(table, {}).get(key)
        if series is None:
            continue
        b_start, _ = bank_window(b)
        off = int((b_start - start) / SAMPLE_MIN)
        arr = np.asarray(series, dtype=float)
        out[off : off + len(arr)] = arr
    return out


def realized_metrics(prices_a, prices_b, flows, suffix="_month"):
    """Rent + ladder for one directed border over aligned quarter-hour arrays (NaN-aware).

    Only samples with finite price AND flow contribute to realized and
    opportunity figures (a known-flow mask, so the ladder is not an upper
    bound over months where flow data is missing). Keys carry `suffix`
    (`_month` per single bank, `_year` for a concatenated calendar year);
    energy = MW * 0.25 h.
    """
    pa = np.asarray(prices_a, dtype=float)
    pb = np.asarray(prices_b, dtype=float)
    f = np.asarray(flows, dtype=float)
    n = min(len(pa), len(pb), len(f))
    pa, pb, f = pa[:n], pb[:n], f[:n]
    spread = pb - pa
    ok = np.isfinite(pa) & np.isfinite(pb) & np.isfinite(f)
    n_ok = int(ok.sum())
    row = dict(congested_quarters=int(np.sum(spread[ok] > 5.0)), observed_quarters=n_ok)
    pos_mask = ok & (spread > 5.0)
    pos_spread = spread[pos_mask]
    row["average_positive_spread_eur_mwh"] = float(np.mean(pos_spread)) if pos_spread.size else None
    row["realized_rent_meur" + suffix] = (
        float(np.sum(f[ok] * spread[ok]) * HOURS_PER_SAMPLE * 1e-6) if n_ok else None
    )
    row["positive_rent_meur" + suffix] = (
        float(np.sum(f[pos_mask] * spread[pos_mask]) * HOURS_PER_SAMPLE * 1e-6) if n_ok else None
    )
    opp = {}
    for dc in LADDERS:
        opp[str(dc)] = float(np.sum(np.clip(spread[ok], 0, None) * dc) * HOURS_PER_SAMPLE * 1e-6)
    row["opportunity_meur" + suffix] = opp
    return row


def price_response_slope(price, net_inflow):
    """Raw affine dP/d(f) slope (EUR/MWh per MW), OLS of price on net scheduled
    inflow. Returns None when there are too few usable samples. The raw slope
    may be negative (noise on short windows); the effective slope used by Step 2
    is this value clamped to 0 (see effective_slope)."""
    p = np.asarray(price, dtype=float)
    f = np.asarray(net_inflow, dtype=float)
    mask = np.isfinite(p) & np.isfinite(f) & (f != 0)
    if int(mask.sum()) < 24:
        return None
    pm, fm = p[mask], f[mask]
    num = float(np.sum((pm - pm.mean()) * (fm - fm.mean())))
    den = float(np.sum((fm - fm.mean()) ** 2))
    return float(num / den) if den > 1e-9 else 0.0


def effective_slope(raw):
    """Step-2 price-response slope: raw OLS slope, or 0 when raw is None / <= 0."""
    return max(raw, 0.0) if raw is not None else 0.0


def zone_slopes(bank):
    """Raw price-response slope per zone (OLS of zone price on net scheduled inflow)."""
    tbl_flows = bank.get("flows_mw", {})
    pairs = border_pairs(bank)
    slopes = {}
    for zone in bank.get("prices", {}):
        price = price_series(bank, zone)
        if price is None:
            continue
        net_inflow = np.zeros(len(price), dtype=float)
        for a2, b2 in pairs:
            if zone not in (a2, b2):
                continue
            fwd = tbl_flows.get(f"{a2}>{b2}")
            rev = tbl_flows.get(f"{b2}>{a2}")
            if fwd is None and rev is None:
                continue
            siz = min(len(net_inflow),
                      len(fwd) if fwd is not None else len(rev),
                      len(rev) if rev is not None else len(fwd))
            for i in range(siz):
                net = 0.0
                if fwd is not None and i < len(fwd) and fwd[i] is not None:
                    net += fwd[i] if a2 == zone else -fwd[i]
                if rev is not None and i < len(rev) and rev[i] is not None:
                    net += rev[i] if b2 == zone else -rev[i]
                net_inflow[i] += net
        slopes[zone] = price_response_slope(price, net_inflow)
    return slopes


def screening(banks, suffix="_month"):
    rows = []
    for bank in banks:
        pairs = border_pairs(bank)
        tbl_flows = bank.get("flows_mw", {})
        tbl_caps = bank.get("caps_mw", {})
        slopes = zone_slopes(bank)
        start, end = bank_window(bank)
        period = f"{_fmt_dt(start)}>{_fmt_dt(end)}"
        for a, b in pairs:
            pa = price_series(bank, a)
            pb = price_series(bank, b)
            if pa is None or pb is None:
                continue
            for fwd, rev in ((a, b), (b, a)):
                flows_ab = tbl_flows.get(f"{fwd}>{rev}")
                if flows_ab is None:
                    flows_ab = [np.nan] * len(pa)
                cap_ab = tbl_caps.get(f"{fwd}>{rev}")
                cap_val = None
                if cap_ab is not None:
                    cap_arr = np.asarray(cap_ab, dtype=float)
                    finite = cap_arr[np.isfinite(cap_arr)]
                    cap_val = float(finite[0]) if finite.size else None
                metrics = (
                    realized_metrics(pa, pb, flows_ab, suffix=suffix)
                    if fwd == a else realized_metrics(pb, pa, flows_ab, suffix=suffix)
                )
                # slope_a/slope_raw_a belong to the directed row's START zone,
                # slope_b/slope_raw_b to its END zone (they swap when reversed).
                rows.append(dict(month=bank.get("month"), period=period, border=f"{fwd}>{rev}",
                                 slope_a=effective_slope(slopes.get(fwd)), slope_b=effective_slope(slopes.get(rev)),
                                 slope_raw_a=slopes.get(fwd), slope_raw_b=slopes.get(rev),
                                 cap_ab_mw=cap_val, **metrics))
    return rows


def sorting(rows, suffix="_month"):
    return sorted(rows, key=lambda r: r["opportunity_meur" + suffix][str(LADDERS[-1])], reverse=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--banks", nargs="*", default=None,
                   help="explicit bank paths (overrides --year)")
    p.add_argument("--year", type=int, default=2025,
                   help="screen all `bank-{year}-*-v2.json` banks as one calendar year")
    p.add_argument("--output", type=Path, default=OUT)
    args = p.parse_args()

    if args.banks:
        paths = [Path(x) for x in args.banks]
        year = None
    else:
        paths = list(sorted(DUMP.glob(f"bank-{args.year}-*-v2.json")))
        if not paths:
            raise SystemExit(f"no banks found for year {args.year} in {DUMP}")
        year = str(args.year)

    banks = [read_bank(path) for path in paths]
    months = [b.get("month") for b in banks]

    monthly = sorting(screening(banks, suffix="_month"))
    year_bank = concat_banks(banks, year=year if year is not None else None)
    annual = sorting(screening([year_bank], suffix="_year"), suffix="_year")

    start, end = bank_window(year_bank)
    labels = [b.get("month") for b in banks]
    payload = dict(
        schema_version=3,
        year=year,
        source="ENTSOE cached banks v2 (data/eu-market)",
        months=months,
        ladder_mw=list(LADDERS),
        formula="opportunity = 1e-6*0.25*sum_t max(0,P_B-P_A,t)*DeltaC M€ per window; "
                "realized = 1e-6*0.25*sum_t F_AB*(P_B-P_A); directed rows a>b and b>a; "
                "year rows are the full-year sum, NOT an x12 extrapolation",
        targets=annual,
        monthly=dict(labels=labels, rows=monthly),
        coverage=dict(
            borders=len({tuple(sorted(r["border"].split(">"))) for r in annual}),
            directed_rows=len(annual), months=len(annual) and labels,
            window=f"{_fmt_dt(start)}>{_fmt_dt(end)}",
            quarter_hours=int((end - start) / SAMPLE_MIN),
            cache_first=True, live_lp="server fn (Step 2)"),
        next_steps="see docs/fast-entsoe-screening.md",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, allow_nan=False, indent=2), encoding="utf-8")
    kpi = annual[0] if annual else None
    print(json.dumps(dict(
        output=str(args.output), year=year, months=len(months),
        directed_rows=len(annual), monthly_rows=len(monthly),
        window=payload["coverage"]["window"],
        top_border=kpi["border"] if kpi else None,
        top_opportunity_meur_year=kpi["opportunity_meur_year"]["1000"] if kpi else None)))


if __name__ == "__main__":
    main()