create extension if not exists pgcrypto;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.resume_analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  resume_hash text not null,
  summary text not null,
  skills jsonb not null default '[]'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  analysis_mode text not null default 'deterministic',
  telemetry jsonb not null default '{}'::jsonb,
  encrypted_payload text,
  encryption_version text,
  created_at timestamptz not null default now()
);

create table if not exists public.job_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  target_role text not null,
  location text not null,
  source_mode text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.job_matches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  search_id uuid not null references public.job_searches(id) on delete cascade,
  external_job_id text not null,
  title text not null,
  company text not null,
  location text not null,
  job_url text not null,
  fit_score int not null check (fit_score between 0 and 100),
  matched_skills jsonb not null default '[]'::jsonb,
  missing_skills jsonb not null default '[]'::jsonb,
  explanation text not null,
  coaching jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.saved_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  external_job_id text not null,
  title text not null,
  company text not null,
  job_url text not null,
  notes text,
  created_at timestamptz not null default now(),
  unique (user_id, external_job_id)
);

create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  run_id text not null,
  rating int not null check (rating between 1 and 5),
  reason text,
  created_at timestamptz not null default now()
);

create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  run_id text not null,
  status text not null,
  model text,
  provider text,
  estimated_cost_usd numeric(12, 6) not null default 0,
  latency_ms numeric(12, 2),
  fallback_reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.resume_analyses enable row level security;
alter table public.job_searches enable row level security;
alter table public.job_matches enable row level security;
alter table public.saved_jobs enable row level security;
alter table public.feedback enable row level security;
alter table public.agent_runs enable row level security;

revoke all on public.profiles from anon, authenticated;
revoke all on public.resume_analyses from anon, authenticated;
revoke all on public.job_searches from anon, authenticated;
revoke all on public.job_matches from anon, authenticated;
revoke all on public.saved_jobs from anon, authenticated;
revoke all on public.feedback from anon, authenticated;
revoke all on public.agent_runs from anon, authenticated;

grant select, insert, update on public.profiles to authenticated;
grant select, insert, delete on public.resume_analyses to authenticated;
grant select, insert, delete on public.job_searches to authenticated;
grant select, insert, delete on public.job_matches to authenticated;
grant select, insert, update, delete on public.saved_jobs to authenticated;
grant insert on public.feedback to authenticated;
grant select on public.agent_runs to authenticated;

create policy "Users can read own profile"
on public.profiles for select to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can insert own profile"
on public.profiles for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can update own profile"
on public.profiles for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users own resume analyses"
on public.resume_analyses for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users own job searches"
on public.job_searches for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users own job matches"
on public.job_matches for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users own saved jobs"
on public.saved_jobs for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users can insert own feedback"
on public.feedback for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can read own agent runs"
on public.agent_runs for select to authenticated
using ((select auth.uid()) = user_id);

create index if not exists idx_resume_analyses_user_id on public.resume_analyses(user_id);
create index if not exists idx_job_searches_user_id on public.job_searches(user_id);
create index if not exists idx_job_matches_user_search on public.job_matches(user_id, search_id);
create index if not exists idx_saved_jobs_user_external on public.saved_jobs(user_id, external_job_id);
create index if not exists idx_feedback_user_id on public.feedback(user_id);
create index if not exists idx_agent_runs_user_run on public.agent_runs(user_id, run_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();
