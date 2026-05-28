"""Localized workflow status and error message catalog."""

from __future__ import annotations


MESSAGE_CATALOG: dict[str, dict[str, str]] = {
    "zh-TW": {
        "workflow.document.approved": "文件已核准。",
        "workflow.traceability.suspect": "追溯關聯已標記為 SUSPECT。",
        "workflow.ai.review.queued": "AI 審查請求已排入佇列。",
        "workflow.ai.review.retryable": "AI 審查服務暫時不可用，可稍後重試。",
        "workflow.export.completed": "稽核匯出作業已完成。",
        "error.validation": "輸入資料驗證失敗。",
        "error.conflict": "資料狀態衝突，請重新整理後再試。",
        "error.not_found": "找不到指定資源。",
        "error.internal": "系統發生未預期錯誤。",
    },
    "en-US": {
        "workflow.document.approved": "Document approved.",
        "workflow.traceability.suspect": "Traceability link marked as SUSPECT.",
        "workflow.ai.review.queued": "AI review request queued.",
        "workflow.ai.review.retryable": "AI review service is temporarily unavailable. Please retry.",
        "workflow.export.completed": "Audit export job completed.",
        "error.validation": "Validation failed.",
        "error.conflict": "Resource conflict detected. Please refresh and retry.",
        "error.not_found": "Requested resource was not found.",
        "error.internal": "Unexpected internal error occurred.",
    },
}


DEFAULT_LOCALE = "zh-TW"
FALLBACK_LOCALE = "en-US"


def get_message(message_key: str, locale: str = DEFAULT_LOCALE) -> str:
    localized = MESSAGE_CATALOG.get(locale, {})
    if message_key in localized:
        return localized[message_key]

    fallback = MESSAGE_CATALOG.get(FALLBACK_LOCALE, {})
    if message_key in fallback:
        return fallback[message_key]

    return message_key
