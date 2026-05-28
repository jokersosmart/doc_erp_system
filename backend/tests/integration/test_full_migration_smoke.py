from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa


def _load_migration_module(filename: str, module_name: str) -> ModuleType:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location(module_name, migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module: {filename}")
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
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str]] = []
        self.dropped_indexes: list[tuple[str, str | None]] = []
        self.added_columns: list[tuple[str, str]] = []
        self.dropped_columns: list[tuple[str, str]] = []
        self.created_foreign_keys: list[str] = []
        self.dropped_constraints: list[str] = []

    def get_bind(self) -> None:
        return None

    def create_table(self, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.created_tables.append(table_name)

    def drop_table(self, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_tables.append(table_name)

    def create_index(self, index_name: str, table_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.created_indexes.append((index_name, table_name))

    def drop_index(self, index_name: str, table_name: str | None = None, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_indexes.append((index_name, table_name))

    def add_column(self, table_name: str, column: sa.Column[Any], *_args: Any, **_kwargs: Any) -> None:
        self.added_columns.append((table_name, column.name))

    def drop_column(self, table_name: str, column_name: str, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_columns.append((table_name, column_name))

    def create_foreign_key(self, name: str, *_args: Any, **_kwargs: Any) -> None:
        self.created_foreign_keys.append(name)

    def drop_constraint(self, name: str, *_args: Any, **_kwargs: Any) -> None:
        self.dropped_constraints.append(name)


@pytest.mark.parametrize(
    ("filename", "module_name", "expected_table", "expected_index"),
    [
        ("0002_audit_and_notifications.py", "migration_0002", "notifications", None),
        ("0003_document_lifecycle_and_eav.py", "migration_0003", "document_revisions", None),
        ("0004_traceability_suspect_management.py", "migration_0004", "suspect_resolutions", None),
        ("0005_ai_review_and_compliance.py", "migration_0005", "ai_review_jobs", None),
        ("0006_export_jobs_and_artifacts.py", "migration_0006", "export_jobs", None),
        (
            "0007_performance_hotspot_indexes.py",
            "migration_0007",
            None,
            "ix_export_jobs_status_completed_at",
        ),
    ],
)
def test_feature_migration_upgrade_and_downgrade_smoke(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    module_name: str,
    expected_table: str | None,
    expected_index: str | None,
) -> None:
    module = _load_migration_module(filename=filename, module_name=module_name)
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)

    for name in [k for k in vars(module) if k.endswith("_enum")]:
        monkeypatch.setattr(module, name, _DummyEnum())

    module.upgrade()
    if expected_table is not None:
        assert expected_table in fake_op.created_tables
    if expected_index is not None:
        created_index_names = {name for name, _table in fake_op.created_indexes}
        assert expected_index in created_index_names

    module.downgrade()
    if expected_table is not None:
        assert expected_table in fake_op.dropped_tables
    if expected_index is not None:
        dropped_index_names = {name for name, _table in fake_op.dropped_indexes}
        assert expected_index in dropped_index_names
