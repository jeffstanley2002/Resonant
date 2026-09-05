from __future__ import annotations

import asyncio

from app.services import storage


def test_delete_user_data_scopes_every_table_to_user(monkeypatch) -> None:
    operations: list[tuple[str, str, str | None, str | None]] = []

    class FakeTable:
        def __init__(self, name: str) -> None:
            self.name = name

        def delete(self):
            operations.append((self.name, "delete", None, None))
            return self

        def eq(self, field: str, value: str):
            operations.append((self.name, "eq", field, value))
            return self

        def execute(self) -> None:
            operations.append((self.name, "execute", None, None))

    class FakeClient:
        def table(self, name: str) -> FakeTable:
            return FakeTable(name)

    monkeypatch.setattr(storage, "get_supabase_client", lambda: FakeClient())

    deleted_tables = asyncio.run(storage.delete_user_data("user_123"))

    assert deleted_tables == storage.USER_DATA_TABLES
    eq_operations = [operation for operation in operations if operation[1] == "eq"]
    assert eq_operations == [
        (table, "eq", "user_id", "user_123") for table in storage.USER_DATA_TABLES
    ]
