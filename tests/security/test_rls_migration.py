from __future__ import annotations

import pathlib

MIGRATION = pathlib.Path("supabase/migrations/001_initial_schema.sql")
AI_METADATA_MIGRATION = pathlib.Path("supabase/migrations/002_ai_pipeline_metadata.sql")
ENCRYPTION_BACKFILL_MIGRATION = pathlib.Path(
    "supabase/migrations/003_resume_analysis_encryption_columns.sql"
)


def test_all_user_tables_enable_rls() -> None:
    sql = MIGRATION.read_text()
    for table in [
        "profiles",
        "resume_analyses",
        "job_searches",
        "job_matches",
        "saved_jobs",
        "feedback",
        "agent_runs",
    ]:
        assert f"alter table public.{table} enable row level security;" in sql


def test_resume_analysis_supports_app_layer_encryption() -> None:
    sql = MIGRATION.read_text()

    assert "encrypted_payload text" in sql
    assert "encryption_version text" in sql


def test_existing_resume_analysis_tables_get_encryption_columns() -> None:
    sql = ENCRYPTION_BACKFILL_MIGRATION.read_text()

    assert "alter table public.resume_analyses" in sql
    assert "add column if not exists encrypted_payload text" in sql
    assert "add column if not exists encryption_version text" in sql


def test_existing_resume_analysis_tables_get_ai_metadata_columns() -> None:
    sql = AI_METADATA_MIGRATION.read_text()

    assert "add column if not exists analysis_mode text" in sql
    assert "add column if not exists telemetry jsonb" in sql
