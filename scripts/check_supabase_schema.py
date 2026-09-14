"""Verify the live Supabase schema has every column the API actually reads and writes.

A missing column does not surface as a startup error: PostgREST rejects the individual
request, so the API keeps returning 200 while silently persisting nothing. Run this
before pushing.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

# Columns the code in app/services/storage.py selects, inserts, or upserts.
EXPECTED_COLUMNS: dict[str, list[str]] = {
    "resume_analyses": [
        "user_id",
        "resume_hash",
        "summary",
        "skills",
        "warnings",
        "analysis_mode",
        "telemetry",
        "encrypted_payload",
        "encryption_version",
        "created_at",
    ],
    "job_searches": ["id", "user_id", "target_role", "location", "source_mode"],
    "job_matches": [
        "user_id",
        "search_id",
        "external_job_id",
        "title",
        "company",
        "location",
        "job_url",
        "fit_score",
        "matched_skills",
        "missing_skills",
        "explanation",
    ],
    "saved_jobs": [
        "user_id",
        "external_job_id",
        "title",
        "company",
        "job_url",
        "notes",
        "created_at",
    ],
    "feedback": ["user_id", "run_id", "rating", "reason"],
    "agent_runs": [
        "user_id",
        "run_id",
        "status",
        "model",
        "provider",
        "estimated_cost_usd",
        "latency_ms",
        "fallback_reason",
        "metadata",
    ],
}

FIX_HINT = """
Apply the pending migrations in supabase/migrations/ to the linked project.

  supabase db push

If port 5432 is blocked on your network (the CLI will report a dial timeout), paste the
statements from the unapplied migration files into the Supabase SQL editor instead:
https://supabase.com/dashboard/project/_/sql
"""


def column_exists(client, table: str, columns: str) -> bool:
    """PostgREST raises on an unknown column, so a successful select is the probe."""
    try:
        client.table(table).select(columns).limit(1).execute()
    except Exception:  # noqa: BLE001 - any failure means the column is unusable
        return False
    return True


def missing_columns(client, table: str, columns: list[str]) -> list[str]:
    if column_exists(client, table, ",".join(columns)):
        return []
    # The batch select failed, so find the individual offenders.
    return [column for column in columns if not column_exists(client, table, column)]


def main() -> int:
    from app.services.storage import get_supabase_client, supabase_configured

    if not supabase_configured():
        print("Supabase is not configured (demo mode); skipping live schema check.")
        return 0

    client = get_supabase_client()
    failures: dict[str, list[str]] = {}

    for table, columns in EXPECTED_COLUMNS.items():
        missing = missing_columns(client, table, columns)
        if missing:
            print(f"FAIL {table}: missing {', '.join(missing)}")
            failures[table] = missing
        else:
            print(f"ok   {table}: {len(columns)} columns present")

    if failures:
        print(f"\nSchema drift in {len(failures)} table(s). The API will accept requests and")
        print("silently fail to persist until this is applied.")
        print(FIX_HINT)
        return 1

    print("\nLive Supabase schema matches what the API reads and writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
