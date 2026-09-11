-- WaterTrace: cache for Electricity Maps responses (written only by the edge function via service role)
create table if not exists public.em_cache (
  cache_key  text primary key,
  payload    jsonb not null,
  fetched_at timestamptz not null default now()
);

grant all on public.em_cache to service_role;

alter table public.em_cache enable row level security;
-- No policies: anon/authenticated clients cannot read or write; the service role bypasses RLS.

create index if not exists em_cache_fetched_at_idx on public.em_cache (fetched_at);
