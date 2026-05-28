from __future__ import annotations

from app.schemas.messages import get_message


def test_get_message_uses_locale_first() -> None:
    assert get_message("workflow.document.approved", "zh-TW") == "文件已核准。"


def test_get_message_falls_back_to_en_us_for_unknown_locale() -> None:
    assert (
        get_message("workflow.export.completed", "fr-FR")
        == "Audit export job completed."
    )


def test_get_message_returns_key_when_missing_everywhere() -> None:
    assert get_message("unknown.key", "zh-TW") == "unknown.key"
