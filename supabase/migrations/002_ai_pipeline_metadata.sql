alter table public.resume_analyses
  add column if not exists analysis_mode text not null default 'deterministic';

alter table public.resume_analyses
  add column if not exists telemetry jsonb not null default '{}'::jsonb;
