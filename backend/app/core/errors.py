"""Domain-level exceptions with stable API error codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DomainError(Exception):
    message: str
    code: str
    status_code: int

    def to_dict(self) -> dict[str, str]:
        return {"detail": self.message, "code": self.code}


class AuthorizationError(DomainError):
    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__(message=message, code="AUTHZ_ERROR", status_code=403)


class ValidationError(DomainError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)


class ConflictError(DomainError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message=message, code="CONFLICT", status_code=409)


class NotFoundError(DomainError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message=message, code="NOT_FOUND", status_code=404)
