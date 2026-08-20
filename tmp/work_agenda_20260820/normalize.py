from __future__ import annotations

from typing import Any

MAX_ITEMS = 8
MAX_TITLE = 160
MAX_PROJECT = 80
MAX_WORKSPACE = 48
MAX_STATUS = 40
MAX_ID = 64
MAX_DUE = 32
ALLOWED_PRIORITIES = {"urgent", "high", "normal", "low", "none"}
ALLOWED_SOURCE_STATUS = {"ok", "partial", "error", "unknown"}


def _text(value: Any, limit: int) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _count(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _priority(value: Any) -> str:
    value = _text(value, 16).lower() or "none"
    return value if value in ALLOWED_PRIORITIES else "none"


def _clickup_url(value: Any) -> str:
    value = _text(value, 300)
    return value if value.startswith("https://app.clickup.com/t/") else ""


def normalize_snapshot(raw: Any) -> dict[str, Any]:
    """Return the small privacy-bounded shape exposed to Home Assistant.

    Unknown keys are intentionally dropped. In particular, raw email content,
    HTML, attachments, message bodies and credentials can never become HA
    state attributes through this layer.
    """
    if not isinstance(raw, dict):
        raise ValueError("snapshot must be an object")

    items: list[dict[str, Any]] = []
    raw_items = raw.get("items")
    if isinstance(raw_items, list):
        for candidate in raw_items[:MAX_ITEMS]:
            if not isinstance(candidate, dict):
                continue
            task_id = _text(candidate.get("id"), MAX_ID)
            title = _text(candidate.get("title"), MAX_TITLE)
            if not task_id or not title:
                continue
            items.append(
                {
                    "id": task_id,
                    "title": title,
                    "project": _text(candidate.get("project"), MAX_PROJECT),
                    "workspace": _text(candidate.get("workspace"), MAX_WORKSPACE),
                    "status": _text(candidate.get("status"), MAX_STATUS),
                    "priority": _priority(candidate.get("priority")),
                    "due": _text(candidate.get("due"), MAX_DUE),
                    "url": _clickup_url(candidate.get("url")),
                    "source": "clickup",
                }
            )

    source_status = _text(raw.get("source_status"), 16).lower() or "unknown"
    if source_status not in ALLOWED_SOURCE_STATUS:
        source_status = "unknown"

    return {
        "generated_at": _text(raw.get("generated_at"), 40),
        "source_status": source_status,
        "open_count": _count(raw.get("open_count")),
        "urgent_count": _count(raw.get("urgent_count")),
        "overdue_count": _count(raw.get("overdue_count")),
        "today_count": _count(raw.get("today_count")),
        "mail_attention_count": _count(raw.get("mail_attention_count")),
        "items": items,
    }
