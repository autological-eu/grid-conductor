
CREATE TABLE public.zones (
  code text PRIMARY KEY,
  name text NOT NULL,
  country_code text NOT NULL,
  lat double precision NOT NULL,
  lon double precision NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zones TO authenticated;
GRANT SELECT ON public.zones TO anon;
GRANT ALL ON public.zones TO service_role;
ALTER TABLE public.zones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "zones readable" ON public.zones FOR SELECT USING (true);

CREATE TABLE public.borders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_a text NOT NULL REFERENCES public.zones(code) ON DELETE CASCADE,
  zone_b text NOT NULL REFERENCES public.zones(code) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (zone_a, zone_b),
  CHECK (zone_a < zone_b)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.borders TO authenticated;
GRANT SELECT ON public.borders TO anon;
GRANT ALL ON public.borders TO service_role;
ALTER TABLE public.borders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "borders readable" ON public.borders FOR SELECT USING (true);

CREATE TABLE public.zone_hourly (
  zone_code text NOT NULL REFERENCES public.zones(code) ON DELETE CASCADE,
  ts timestamptz NOT NULL,
  price_eur_mwh double precision,
  carbon_intensity double precision,
  load_mw double precision,
  mix jsonb,
  PRIMARY KEY (zone_code, ts)
);
CREATE INDEX zone_hourly_ts_idx ON public.zone_hourly (ts);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zone_hourly TO authenticated;
GRANT SELECT ON public.zone_hourly TO anon;
GRANT ALL ON public.zone_hourly TO service_role;
ALTER TABLE public.zone_hourly ENABLE ROW LEVEL SECURITY;
CREATE POLICY "zone_hourly readable" ON public.zone_hourly FOR SELECT USING (true);

CREATE TABLE public.border_flow_hourly (
  zone_a text NOT NULL REFERENCES public.zones(code) ON DELETE CASCADE,
  zone_b text NOT NULL REFERENCES public.zones(code) ON DELETE CASCADE,
  ts timestamptz NOT NULL,
  flow_mw double precision NOT NULL,
  PRIMARY KEY (zone_a, zone_b, ts)
);
CREATE INDEX border_flow_hourly_ts_idx ON public.border_flow_hourly (ts);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.border_flow_hourly TO authenticated;
GRANT SELECT ON public.border_flow_hourly TO anon;
GRANT ALL ON public.border_flow_hourly TO service_role;
ALTER TABLE public.border_flow_hourly ENABLE ROW LEVEL SECURITY;
CREATE POLICY "border_flow_hourly readable" ON public.border_flow_hourly FOR SELECT USING (true);

CREATE TABLE public.import_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_code text NOT NULL,
  signal text NOT NULL,
  range_start timestamptz NOT NULL,
  range_end timestamptz NOT NULL,
  cursor_ts timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  rows_imported integer NOT NULL DEFAULT 0,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (zone_code, signal, range_start, range_end)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.import_jobs TO authenticated;
GRANT SELECT ON public.import_jobs TO anon;
GRANT ALL ON public.import_jobs TO service_role;
ALTER TABLE public.import_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "import_jobs readable" ON public.import_jobs FOR SELECT USING (true);

CREATE TABLE public.job_locks (
  name text PRIMARY KEY,
  expires_at timestamptz NOT NULL,
  paused boolean NOT NULL DEFAULT false,
  pause_reason text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT ON public.job_locks TO authenticated, anon;
GRANT ALL ON public.job_locks TO service_role;
ALTER TABLE public.job_locks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "job_locks readable" ON public.job_locks FOR SELECT USING (true);

CREATE TABLE public.targets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_a text NOT NULL,
  zone_b text NOT NULL,
  period_start timestamptz NOT NULL,
  period_end timestamptz NOT NULL,
  congested_hours integer NOT NULL DEFAULT 0,
  total_hours integer NOT NULL DEFAULT 0,
  market_loss_meur double precision NOT NULL DEFAULT 0,
  climate_loss_ktco2 double precision NOT NULL DEFAULT 0,
  observed_capacity_mw double precision,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  computed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (zone_a, zone_b, period_start, period_end)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.targets TO authenticated, anon;
GRANT ALL ON public.targets TO service_role;
ALTER TABLE public.targets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "targets open" ON public.targets FOR ALL USING (true) WITH CHECK (true);

CREATE TABLE public.scenarios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  target_id uuid NOT NULL REFERENCES public.targets(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'draft',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scenarios TO authenticated, anon;
GRANT ALL ON public.scenarios TO service_role;
ALTER TABLE public.scenarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "scenarios open" ON public.scenarios FOR ALL USING (true) WITH CHECK (true);

CREATE TABLE public.scenario_units (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES public.scenarios(id) ON DELETE CASCADE,
  unit_type text NOT NULL,
  zone_code text,
  border_zone_a text,
  border_zone_b text,
  params jsonb NOT NULL DEFAULT '{}'::jsonb,
  capex_meur double precision NOT NULL DEFAULT 0,
  delivery_months integer NOT NULL DEFAULT 24,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scenario_units TO authenticated, anon;
GRANT ALL ON public.scenario_units TO service_role;
ALTER TABLE public.scenario_units ENABLE ROW LEVEL SECURITY;
CREATE POLICY "scenario_units open" ON public.scenario_units FOR ALL USING (true) WITH CHECK (true);

CREATE TABLE public.scenario_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES public.scenarios(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'complete',
  market_opportunity_meur double precision NOT NULL DEFAULT 0,
  climate_opportunity_ktco2 double precision NOT NULL DEFAULT 0,
  base_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  scenario_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  entsoe_indicators jsonb NOT NULL DEFAULT '{}'::jsonb,
  hourly_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scenario_results TO authenticated, anon;
GRANT ALL ON public.scenario_results TO service_role;
ALTER TABLE public.scenario_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "scenario_results open" ON public.scenario_results FOR ALL USING (true) WITH CHECK (true);

CREATE TABLE public.model_validation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  period_start timestamptz NOT NULL,
  period_end timestamptz NOT NULL,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  passed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.model_validation TO authenticated, anon;
GRANT ALL ON public.model_validation TO service_role;
ALTER TABLE public.model_validation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "model_validation open" ON public.model_validation FOR ALL USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER import_jobs_updated_at BEFORE UPDATE ON public.import_jobs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER scenarios_updated_at BEFORE UPDATE ON public.scenarios
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

INSERT INTO public.zones (code, name, country_code, lat, lon) VALUES
('AT','Austria','AT',47.6,14.1),
('BE','Belgium','BE',50.6,4.6),
('BG','Bulgaria','BG',42.7,25.3),
('CH','Switzerland','CH',46.8,8.2),
('CZ','Czechia','CZ',49.8,15.5),
('DE','Germany','DE',51.1,10.4),
('DK-DK1','Denmark West','DK',56.3,9.2),
('DK-DK2','Denmark East','DK',55.4,11.8),
('EE','Estonia','EE',58.7,25.5),
('ES','Spain','ES',40.2,-3.7),
('FI','Finland','FI',63.0,26.0),
('FR','France','FR',46.6,2.3),
('GR','Greece','GR',39.0,22.0),
('HR','Croatia','HR',45.4,16.0),
('HU','Hungary','HU',47.1,19.5),
('IE','Ireland','IE',53.2,-8.0),
('IT-CNO','Italy Centre-North','IT',43.4,11.5),
('IT-CSO','Italy Centre-South','IT',41.9,13.3),
('IT-NO','Italy North','IT',45.5,9.5),
('IT-SAR','Italy Sardinia','IT',40.0,9.1),
('IT-SIC','Italy Sicily','IT',37.6,14.2),
('IT-SO','Italy South','IT',40.6,16.4),
('LT','Lithuania','LT',55.3,23.9),
('LU','Luxembourg','LU',49.8,6.1),
('LV','Latvia','LV',56.9,24.9),
('NL','Netherlands','NL',52.2,5.5),
('NO-NO1','Norway South-East','NO',60.4,11.0),
('NO-NO2','Norway South-West','NO',58.9,7.0),
('NO-NO3','Norway Mid','NO',63.4,10.9),
('NO-NO4','Norway North','NO',68.5,17.5),
('NO-NO5','Norway West','NO',60.9,6.5),
('PL','Poland','PL',52.0,19.4),
('PT','Portugal','PT',39.5,-8.2),
('RO','Romania','RO',45.9,25.0),
('RS','Serbia','RS',44.0,20.9),
('SE-SE1','Sweden North','SE',67.0,20.0),
('SE-SE2','Sweden Mid-North','SE',64.0,17.5),
('SE-SE3','Sweden Mid-South','SE',59.8,15.5),
('SE-SE4','Sweden South','SE',56.5,14.0),
('SI','Slovenia','SI',46.1,14.8),
('SK','Slovakia','SK',48.7,19.5);

INSERT INTO public.borders (zone_a, zone_b)
SELECT LEAST(a,b), GREATEST(a,b) FROM (VALUES
('AT','DE'),('AT','CH'),('AT','CZ'),('AT','HU'),('AT','SI'),('AT','IT-NO'),('AT','SK'),
('BE','FR'),('BE','NL'),('BE','DE'),('BE','LU'),
('BG','GR'),('BG','RO'),('BG','RS'),
('CH','DE'),('CH','FR'),('CH','IT-NO'),
('CZ','DE'),('CZ','PL'),('CZ','SK'),
('DE','DK-DK1'),('DE','FR'),('DE','LU'),('DE','NL'),('DE','PL'),('DE','SE-SE4'),('DE','NO-NO2'),
('DK-DK1','DK-DK2'),('DK-DK1','NL'),('DK-DK1','NO-NO2'),('DK-DK1','SE-SE3'),
('DK-DK2','SE-SE4'),
('EE','FI'),('EE','LV'),
('ES','FR'),('ES','PT'),
('FI','SE-SE1'),('FI','SE-SE3'),('FI','NO-NO4'),
('FR','IT-NO'),
('GR','IT-SO'),
('HR','HU'),('HR','SI'),('HR','RS'),
('HU','RO'),('HU','RS'),('HU','SK'),
('IT-CNO','IT-NO'),('IT-CNO','IT-CSO'),('IT-CNO','IT-SAR'),
('IT-CSO','IT-SO'),('IT-CSO','IT-SAR'),
('IT-SIC','IT-SO'),
('IT-NO','SI'),
('LT','LV'),('LT','PL'),('LT','SE-SE4'),
('NL','NO-NO2'),
('NO-NO1','NO-NO2'),('NO-NO1','NO-NO3'),('NO-NO1','NO-NO5'),('NO-NO1','SE-SE3'),
('NO-NO2','NO-NO5'),
('NO-NO3','NO-NO4'),('NO-NO3','NO-NO5'),('NO-NO3','SE-SE2'),
('NO-NO4','SE-SE1'),('NO-NO4','SE-SE2'),
('PL','SE-SE4'),('PL','SK'),
('RO','RS'),
('SE-SE1','SE-SE2'),('SE-SE2','SE-SE3'),('SE-SE3','SE-SE4')
) AS t(a,b);
