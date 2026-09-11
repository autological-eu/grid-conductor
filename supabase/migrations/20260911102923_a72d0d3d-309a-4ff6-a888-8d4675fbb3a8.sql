
CREATE OR REPLACE FUNCTION public.zone_summary()
RETURNS TABLE (
  code text, name text, country_code text, lat double precision, lon double precision,
  avg_carbon_intensity double precision, avg_price double precision, hours bigint
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT z.code, z.name, z.country_code, z.lat, z.lon,
         avg(h.carbon_intensity), avg(h.price_eur_mwh), count(h.ts)
  FROM zones z
  LEFT JOIN zone_hourly h ON h.zone_code = z.code
  GROUP BY z.code, z.name, z.country_code, z.lat, z.lon
  ORDER BY z.code
$$;

GRANT EXECUTE ON FUNCTION public.zone_summary() TO anon, authenticated, service_role;
