alter table public.resume_analyses
  add column if not exists encrypted_payload text;

alter table public.resume_analyses
  add column if not exists encryption_version text;
