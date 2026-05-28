from __future__ import annotations

from app.main import app


def test_export_contract_paths_and_methods_present() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/exports" in paths
    assert "post" in paths["/api/v1/exports"]

    assert "/api/v1/exports/{jobId}" in paths
    assert "get" in paths["/api/v1/exports/{jobId}"]

    assert "/api/v1/dashboard/summary" in paths
    assert "get" in paths["/api/v1/dashboard/summary"]


def test_export_contract_response_codes_declared() -> None:
    schema = app.openapi()
    create_responses = schema["paths"]["/api/v1/exports"]["post"]["responses"]

    assert "202" in create_responses
