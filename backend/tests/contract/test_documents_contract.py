from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from app.main import app


def _build_docx_bytes(text: str) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
                archive.writestr(
                        "[Content_Types].xml",
                        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
                )
                archive.writestr(
                        "_rels/.rels",
                        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
                )
                archive.writestr(
                        "word/document.xml",
                        f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
    </w:body>
</w:document>""",
                )

        return buffer.getvalue()


def test_documents_contract_paths_and_methods_present() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/documents" in paths
    assert "post" in paths["/api/v1/documents"]

    assert "/api/v1/documents/{documentId}" in paths
    assert "get" in paths["/api/v1/documents/{documentId}"]
    assert "put" in paths["/api/v1/documents/{documentId}"]

    assert "/api/v1/documents/{documentId}/transitions" in paths
    assert "post" in paths["/api/v1/documents/{documentId}/transitions"]


def test_documents_contract_error_responses_declared() -> None:
    schema = app.openapi()
    get_responses = schema["paths"]["/api/v1/documents/{documentId}"]["get"]["responses"]
    put_responses = schema["paths"]["/api/v1/documents/{documentId}"]["put"]["responses"]
    convert_request = schema["paths"]["/api/v1/documents/convert"]["post"]["requestBody"]

    assert "404" in get_responses
    assert "409" in put_responses
    assert "multipart/form-data" in convert_request["content"]


def test_document_conversion_endpoint_converts_docx_to_markdown() -> None:
    client = TestClient(app)
    docx_bytes = _build_docx_bytes("Hello from MarkItDown")

    response = client.post(
        "/api/v1/documents/convert",
        files={
            "file": (
                "sample.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_filename"] == "sample.docx"
    assert "Hello from MarkItDown" in payload["markdown"]


def test_health_endpoint_still_operational() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
