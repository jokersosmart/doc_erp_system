from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import sqlalchemy as sa


def _load_migration_module() -> ModuleType:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0001_initial_core_and_lock_events.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0001", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyEnum(sa.String):
    def __init__(self) -> None:
        super().__init__()

    def create(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def drop(self, *_args: Any, **_kwargs: Any) -> None:
        return


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.created_indexes: list[tuple[str, str]] = []
        self.dropped_tables: list[str] = []
        self.dropped_indexes: list[tuple[str, str | None]] = []

    def get_bind(self) -> None:
        return None

    def create_table(self, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.created_tables.append(table_name)

    def create_index(self, index_name: str, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.created_indexes.append((index_name, table_name))

    def drop_table(self, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_tables.append(table_name)

    def drop_index(self, index_name: str, table_name: str | None = None, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_indexes.append((index_name, table_name))


def test_lock_events_migration_upgrade_and_downgrade_smoke(monkeypatch) -> None:
    module = _load_migration_module()
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(module, "lifecycle_state_enum", _DummyEnum())
    monkeypatch.setattr(module, "lock_state_enum", _DummyEnum())
    monkeypatch.setattr(module, "dependency_type_enum", _DummyEnum())

    module.upgrade()

    assert "lock_events" in fake_op.created_tables
    created_index_names = {name for name, _table in fake_op.created_indexes}
    assert "ix_lock_events_upstream_document_id" in created_index_names
    assert "ix_lock_events_bu_node_id" in created_index_names
    assert "ix_lock_events_triggered_at" in created_index_names

    module.downgrade()

    assert "lock_events" in fake_op.dropped_tables
    dropped_index_names = {name for name, _table in fake_op.dropped_indexes}
    assert "ix_lock_events_upstream_document_id" in dropped_index_names
    assert "ix_lock_events_bu_node_id" in dropped_index_names
    assert "ix_lock_events_triggered_at" in dropped_index_names
