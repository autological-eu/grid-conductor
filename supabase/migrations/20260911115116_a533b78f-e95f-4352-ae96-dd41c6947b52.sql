create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

create table if not exists public.app_config (
  key text primary key,
  value text not null
);

grant select on public.app_config to service_role;

alter table public.app_config enable row level security;
-- no policies: only the service role (backend) can read it

insert into public.app_config (key, value) values
  ('daily_refresh_secret', gen_random_uuid()::text),
  ('daily_refresh_url', 'https://project--7e94c247-d214-4db4-8db5-ab838b1488d8-dev.lovable.app/api/public/daily-refresh')
on conflict (key) do nothing;

select cron.schedule(
  'daily-refresh',
  '0 5 * * *',
  $$
  select net.http_post(
    url := (select value from public.app_config where key = 'daily_refresh_url'),
    headers := jsonb_build_object(
      'content-type', 'application/json',
      'x-refresh-secret', (select value from public.app_config where key = 'daily_refresh_secret')
    ),
    body := '{}'::jsonb
  );
  $$
);