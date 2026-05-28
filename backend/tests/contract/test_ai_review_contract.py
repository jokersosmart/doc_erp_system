from __future__ import annotations

from app.main import app


def test_ai_review_contract_paths_and_methods_present() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/ai/reviews" in paths
    assert "post" in paths["/api/v1/ai/reviews"]

    assert "/api/v1/ai/reviews/{jobId}" in paths
    assert "get" in paths["/api/v1/ai/reviews/{jobId}"]

    assert "/api/v1/ai/reviews/{jobId}/suggestions/{suggestionId}/decisions" in paths
    assert "post" in paths["/api/v1/ai/reviews/{jobId}/suggestions/{suggestionId}/decisions"]


def test_ai_review_contract_response_codes_declared() -> None:
    schema = app.openapi()

    create_responses = schema["paths"]["/api/v1/ai/reviews"]["post"]["responses"]
    decision_responses = schema["paths"]["/api/v1/ai/reviews/{jobId}/suggestions/{suggestionId}/decisions"][
        "post"
    ]["responses"]

    assert "202" in create_responses
    assert "422" in decision_responses
