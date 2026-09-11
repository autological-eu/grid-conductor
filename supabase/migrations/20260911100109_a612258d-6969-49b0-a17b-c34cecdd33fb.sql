
REVOKE EXECUTE ON FUNCTION public.compute_targets(double precision, double precision, double precision) FROM anon, authenticated, public;
GRANT EXECUTE ON FUNCTION public.compute_targets(double precision, double precision, double precision) TO service_role;
