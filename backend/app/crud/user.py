"""User CRUD operations - simple in-memory store for JWT auth demo."""
# NOTE: For this spec, users are managed via JWT claims.
# This module provides a simple fixed user store for the auth demo.
# A full user management system (CRUD) is out of scope per spec A-06.

from app.core.security import get_password_hash, verify_password

# Pre-seeded users: username -> {password_hash, role, partition_access, id}
_USERS: dict[str, dict] = {
    "admin": {
        "id": "user-admin-001",
        "username": "admin",
        "password_hash": get_password_hash("Admin@123"),
        "role": "Admin",
        "partition_access": [],  # Admin has access to all
    },
    "rd_user": {
        "id": "user-rd-001",
        "username": "rd_user",
        "password_hash": get_password_hash("RD@123456"),
        "role": "RD",
        "partition_access": ["SWE", "HW"],
    },
    "qa_user": {
        "id": "user-qa-001",
        "username": "qa_user",
        "password_hash": get_password_hash("QA@123456"),
        "role": "QA",
        "partition_access": ["SWE", "SYS", "HW", "Safety", "Security"],
    },
    "pm_user": {
        "id": "user-pm-001",
        "username": "pm_user",
        "password_hash": get_password_hash("PM@123456"),
        "role": "PM",
        "partition_access": ["SWE", "SYS", "HW", "Safety", "Security"],
    },
}


def get_user_by_username(username: str) -> dict | None:
    """Get user by username."""
    return _USERS.get(username)


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user and return user dict if valid, else None."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
