from __future__ import annotations

from app.main import app


def test_traceability_contract_paths_and_methods_present() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/traceability/links" in paths
    assert "post" in paths["/api/v1/traceability/links"]

    assert "/api/v1/documents/{documentId}/impacts" in paths
    assert "get" in paths["/api/v1/documents/{documentId}/impacts"]

    assert "/api/v1/traceability/links/{linkId}/resolve" in paths
    assert "post" in paths["/api/v1/traceability/links/{linkId}/resolve"]


def test_traceability_contract_error_responses_declared() -> None:
    schema = app.openapi()

    create_responses = schema["paths"]["/api/v1/traceability/links"]["post"]["responses"]
    resolve_responses = schema["paths"]["/api/v1/traceability/links/{linkId}/resolve"]["post"][
        "responses"
    ]

    assert "409" in create_responses
    assert "422" in resolve_responses
