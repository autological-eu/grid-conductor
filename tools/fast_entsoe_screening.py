"""Step-1 fast ENTSO-E border screening over the cached EU-market bank (v2).

Reads only locally cached `data/eu-market/bank-*.json` (schema_v2; quarter-hour
A44 prices per bidding zone, directed A11 flows, directed A61 day-ahead caps).
No network, no ENTSO-E key, no scipy required (numpy only). For every interior
border it computes:

  * realized_rent_meur_yr  = 1e-6 * sum_t F_AB,t * (P_B,t - P_A,t)  [signed]
  * rent_by_direction      = same but only where the spread is positive
                             (the congestion rent the capacity actually earns)
  * opportunity_DC_meur_yr = 1e-6 * sum_t  max(0, P_B,t - P_A,t) * DeltaC
                             for DeltaC in {500, 1000} MW  (theoretical ladder)
  * congested_hours        = hours with positive spread > 5 EUR/MWh
  * average_positive_spread = mean of the profitable-spread samples
  * price_response_slope   = affine slope dP/d(f) per zone (Step-2 LP input),
                             from the OLS of zone price on net scheduled
                             inflow, clipped to a strictly-positive floor.

Outputs `public/research/entsoe-fast-targets.json` (decision ladder ranked by
theoretical opportunity) plus a coverage manifest. Published data is
deterministic and resumable; rerunning over the same cache is a no-op.
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "data" / "eu-market"
PUBLIC = ROOT / "public" / "research"
OUT = PUBLIC / "entsoe-fast-targets.json"
LADDERS = (500, 1000)  # candidate cable capacity increments in MW


def read_bank(path):
    bank = json.loads(path.read_text(encoding="utf-8"))
    if bank.get("schema_version") != 2:
        raise ValueError(f"{path.name}: expected schema_version 2, got {bank.get('schema_version')}")
    return bank


def border_pairs(bank):
    return [tuple(b) for b in bank.get("interior_borders", [])]


def price_series(bank, zone):
    return bank.get("prices", {}).get(zone)


def realized_metrics(prices_a, prices_b, flows):
    """Rent + ladder for one border over aligned quarter-hour arrays (NaN-aware)."""
    pa = np.asarray(prices_a, dtype=float)
    pb = np.asarray(prices_b, dtype=float)
    f = np.asarray(flows, dtype=float)
    n = min(len(pa), len(pb), len(f))
    pa, pb, f = pa[:n], pb[:n], f[:n]
    spread = pb - pa
    ok = np.isfinite(pa) & np.isfinite(pb) & np.isfinite(f)
    has_data = bool(np.isfinite(pa[:n]).any() and np.isfinite(pb[:n]).any())
    if not has_data:
        return None
    n_ok = int(ok.sum())
    if n_ok == 0:
        # prices present but not a single usable flow sample: realized rent is
        # unknowable, opportunity still exists in theory from pure spread.
        mean_spread = float(np.nanmean(spread)) if np.isfinite(spread).any() else None
        congested = int(np.nansum(np.where(np.isfinite(spread), spread > 5.0, False)))
        real = dict(realized_rent_meur_yr=None, positive_rent_meur_yr=None,
                    congested_hours=congested, average_positive_spread_eur_mwh=(
                        float(np.mean(spread[(np.isfinite(spread)) & (spread > 5.0)]))
                        if np.any((np.isfinite(spread)) & (spread > 5.0)) else None),
                    observed_quarters=n)
        real["opportunity_meur_yr"] = {
            dc: float(np.nansum(np.where(np.isfinite(spread), np.clip(spread, 0, None), 0) * dc) * 1e-6)
            for dc in LADDERS}
        return real
    realized = float(np.sum(f[ok] * spread[ok]) * 1e-6)
    positive = float(np.sum(f[ok] * np.clip(spread[ok], 0, None)) * 1e-6)
    congested = int(np.sum(spread[ok] > 5.0))
    pos_spread = spread[ok][spread[ok] > 5.0]
    avg = float(np.mean(pos_spread)) if pos_spread.size else None
    opportunity = {dc: float(np.sum(np.clip(spread[ok], 0, None) * dc) * 1e-6) for dc in LADDERS}
    return dict(realized_rent_meur_yr=realized, positive_rent_meur_yr=positive,
                congested_hours=congested, average_positive_spread_eur_mwh=avg,
                opportunity_meur_yr=opportunity, observed_quarters=n_ok)


def price_response_slope(price, net_inflow):
    """Affine dP/d(f) slope (EUR/MWh per GW) for the Step-2 LP, OLS of price on
    net scheduled inflow, floored at a small positive epsilon."""
    p = np.asarray(price, dtype=float)
    f = np.asarray(net_inflow, dtype=float)
    mask = np.isfinite(p) & np.isfinite(f) & (f != 0)
    if int(mask.sum()) < 24:
        return None
    pm, fm = p[mask], f[mask]
    num = float(np.sum((pm - pm.mean()) * (fm - fm.mean())))
    den = float(np.sum((fm - fm.mean()) ** 2))
    return max(float(num / den) if den > 1e-9 else 0.0, 1e-6)


def screening(banks):
    rows = []
    for bank in banks:
        pairs = border_pairs(bank)
        tbl_flows = bank.get("flows_mw", {})
        tbl_caps = bank.get("caps_mw", {})
        for a, b in pairs:
            pa = price_series(bank, a)
            pb = price_series(bank, b)
            if pa is None or pb is None:
                continue
            flows_ab = tbl_flows.get(f"{a}>{b}")
            cap_ab = tbl_caps.get(f"{a}>{b}")
            if flows_ab is None:
                flows_ab = [np.nan] * len(pa)
            metrics = realized_metrics(pa, pb, flows_ab)
            if metrics is None:
                continue
            # net scheduled inflow into zone a, summed across its incident borders
            net_inflow_a = np.zeros(len(pa), dtype=float)
            for a2, b2 in pairs:
                if a not in (a2, b2):
                    continue
                fwd = tbl_flows.get(f"{a2}>{b2}")
                rev = tbl_flows.get(f"{b2}>{a2}")
                if fwd is None and rev is None:
                    continue
                siz = min(len(net_inflow_a),
                          len(fwd) if fwd is not None else len(rev),
                          len(rev) if rev is not None else len(fwd))
                for i in range(siz):
                    net = 0.0
                    if fwd is not None and i < len(fwd) and fwd[i] is not None:
                        net += fwd[i] if a2 == a else -fwd[i]
                    if rev is not None and i < len(rev) and rev[i] is not None:
                        net += rev[i] if b2 == a else -rev[i]
                    net_inflow_a[i] += net
            slope_a = price_response_slope(pa, net_inflow_a)
            rows.append(dict(month=bank.get("month"), border=f"{a}>{b}",
                **metrics, cap_ab_mw=cap_ab[0] if cap_ab else None, slope_a=slope_a))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--banks", nargs="*", default=[str(DUMP / "bank-2026-01-v2.json"),
                                                    str(DUMP / "bank-2026-08-v2.json")])
    p.add_argument("--output", type=Path, default=OUT)
    args = p.parse_args()
    banks = [read_bank(Path(x)) for x in args.banks]
    rows = sorting(screening(banks))
    payload = dict(schema_version=1, source="ENTSO-E cached bank v2 (data/eu-market)",
        months=[b.get("month") for b in banks],
        ladder_mw=list(LADDERS),
        formula="opportunity = 1e-6*sum_t max(0,P_B-P_A,t)*DeltaC; "
                "realized = 1e-6*sum_t F_AB*(P_B-P_A)",
        targets=rows,
        coverage=dict(borders=len(rows), months=[b.get("month") for b in banks],
            cache_first=True, live_lp="server fn (Step 2)"),
        next_steps="see docs/fast-entsoe-screening.md")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, allow_nan=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(output=str(args.output), borders=len(rows),
        months=[b.get("month") for b in banks])))


def sorting(rows):
    return sorted(rows, key=lambda r: r["opportunity_meur_yr"][LADDERS[-1]], reverse=True)


if __name__ == "__main__":
    main()
