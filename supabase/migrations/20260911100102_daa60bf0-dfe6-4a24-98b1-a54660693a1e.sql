
CREATE OR REPLACE FUNCTION public.compute_targets(
  min_spread double precision DEFAULT 1.0,
  congestion_ratio double precision DEFAULT 0.98,
  relief_share double precision DEFAULT 0.10
) RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  n integer;
BEGIN
  WITH cap AS (
    SELECT zone_a, zone_b,
           max(greatest(flow_mw, 0))  AS cap_ab,
           max(greatest(-flow_mw, 0)) AS cap_ba,
           min(ts) AS ts_min,
           max(ts) AS ts_max
    FROM border_flow_hourly
    GROUP BY zone_a, zone_b
  ),
  h AS (
    SELECT f.zone_a, f.zone_b, f.ts, f.flow_mw,
           za.price_eur_mwh AS pa, zb.price_eur_mwh AS pb,
           za.carbon_intensity AS ca, zb.carbon_intensity AS cb,
           c.cap_ab, c.cap_ba, c.ts_min, c.ts_max
    FROM border_flow_hourly f
    JOIN cap c ON c.zone_a = f.zone_a AND c.zone_b = f.zone_b
    JOIN zone_hourly za ON za.zone_code = f.zone_a AND za.ts = f.ts
    JOIN zone_hourly zb ON zb.zone_code = f.zone_b AND zb.ts = f.ts
    WHERE za.price_eur_mwh IS NOT NULL AND zb.price_eur_mwh IS NOT NULL
  ),
  scored AS (
    SELECT h.*,
           abs(pa - pb) AS spread,
           CASE WHEN pa < pb THEN cap_ab ELSE cap_ba END AS dir_cap,
           CASE WHEN pa < pb THEN greatest(flow_mw, 0) ELSE greatest(-flow_mw, 0) END AS dir_flow,
           CASE WHEN pa < pb THEN coalesce(cb,0) - coalesce(ca,0)
                ELSE coalesce(ca,0) - coalesce(cb,0) END AS ci_gain
    FROM h
  ),
  agg AS (
    SELECT zone_a, zone_b,
           min(ts_min) AS period_start,
           max(ts_max) AS period_end,
           max(cap_ab) AS cap_ab,
           max(cap_ba) AS cap_ba,
           count(*) AS total_hours,
           count(*) FILTER (
             WHERE spread >= min_spread AND dir_cap > 0 AND dir_flow >= congestion_ratio * dir_cap
           ) AS congested_hours,
           coalesce(sum(
             CASE WHEN spread >= min_spread AND dir_cap > 0 AND dir_flow >= congestion_ratio * dir_cap
                  THEN spread * dir_cap * relief_share END
           ), 0) / 1e6 AS market_loss_meur,
           coalesce(sum(
             CASE WHEN spread >= min_spread AND dir_cap > 0 AND dir_flow >= congestion_ratio * dir_cap
                       AND ci_gain > 0
                  THEN ci_gain * dir_cap * relief_share END
           ), 0) / 1e6 AS climate_loss_ktco2,
           coalesce(avg(
             CASE WHEN spread >= min_spread AND dir_cap > 0 AND dir_flow >= congestion_ratio * dir_cap
                  THEN spread END
           ), 0) AS avg_congested_spread
    FROM scored
    GROUP BY zone_a, zone_b
  )
  INSERT INTO targets (
    zone_a, zone_b, period_start, period_end, congested_hours, total_hours,
    market_loss_meur, climate_loss_ktco2, observed_capacity_mw, metrics, computed_at
  )
  SELECT zone_a, zone_b, period_start, period_end, congested_hours, total_hours,
         market_loss_meur, climate_loss_ktco2, greatest(cap_ab, cap_ba),
         jsonb_build_object(
           'cap_ab_mw', cap_ab,
           'cap_ba_mw', cap_ba,
           'avg_congested_spread_eur_mwh', avg_congested_spread,
           'congestion_share', CASE WHEN total_hours > 0 THEN congested_hours::double precision / total_hours ELSE 0 END,
           'relief_share', relief_share,
           'min_spread_eur_mwh', min_spread,
           'congestion_ratio', congestion_ratio
         ),
         now()
  FROM agg
  WHERE total_hours > 0
  ON CONFLICT (zone_a, zone_b, period_start, period_end) DO UPDATE SET
    congested_hours = EXCLUDED.congested_hours,
    total_hours = EXCLUDED.total_hours,
    market_loss_meur = EXCLUDED.market_loss_meur,
    climate_loss_ktco2 = EXCLUDED.climate_loss_ktco2,
    observed_capacity_mw = EXCLUDED.observed_capacity_mw,
    metrics = EXCLUDED.metrics,
    computed_at = now();

  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END;
$$;

GRANT EXECUTE ON FUNCTION public.compute_targets(double precision, double precision, double precision) TO anon, authenticated, service_role;
