ALTER TABLE public.scenarios
  ADD COLUMN is_template boolean NOT NULL DEFAULT false,
  ADD COLUMN template_key text,
  ADD COLUMN budget_meur double precision;

CREATE UNIQUE INDEX scenarios_template_key_uq
  ON public.scenarios (target_id, template_key, budget_meur)
  WHERE is_template;