"""Authorization and partition-scope dependency helpers."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Header

from app.core.errors import AuthorizationError


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> uuid.UUID:
    if not x_user_id:
        raise AuthorizationError("Missing user identity header")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise AuthorizationError("Invalid user identity header") from exc


def require_role(required_role: str):
    def _role_guard(
        x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    ) -> str:
        if x_user_role != required_role:
            raise AuthorizationError(f"Role '{required_role}' required")
        return x_user_role

    return _role_guard


def require_partition_scope(partition_id: uuid.UUID):
    def _partition_guard(
        x_partition_scope: Annotated[str | None, Header(alias="X-Partition-Scope")] = None,
    ) -> str:
        if x_partition_scope != str(partition_id):
            raise AuthorizationError("Partition scope mismatch")
        return x_partition_scope

    return _partition_guard
