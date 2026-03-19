"""Webhook event processing pipeline with idempotency and event logging."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.event_log import EventLog, EventStatus

logger = logging.getLogger(__name__)

_event_log_store: dict[str, EventLog] = {}

_CLOSES_PATTERN = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)",
    re.IGNORECASE,
)


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def get_event_log(delivery_id: str) -> Optional[EventLog]:
    return _event_log_store.get(delivery_id)


def list_event_logs() -> list[EventLog]:
    return list(_event_log_store.values())


def clear_event_logs() -> None:
    _event_log_store.clear()


def extract_issue_numbers(text: str) -> list[int]:
    return [int(m) for m in _CLOSES_PATTERN.findall(text or "")]


def is_duplicate(delivery_id: str) -> bool:
    return delivery_id in _event_log_store


def process_event(
    delivery_id: str,
    event_type: str,
    payload: bytes,
    parsed_data: dict[str, Any],
) -> EventLog:
    payload_hash = _hash_payload(payload)

    if is_duplicate(delivery_id):
        existing = _event_log_store[delivery_id]
        logger.info("Duplicate delivery_id=%s, skipping (status=%s)", delivery_id, existing.status)
        return existing

    event_log = EventLog(
        delivery_id=delivery_id,
        event_type=event_type,
        payload_hash=payload_hash,
        status=EventStatus.PENDING,
    )
    _event_log_store[delivery_id] = event_log

    try:
        raw_data = json.loads(payload)

        if event_type == "pull_request":
            _process_pull_request(raw_data)
        elif event_type == "issues":
            _process_issue(raw_data)

        event_log.status = EventStatus.PROCESSED
        event_log.processed_at = datetime.now(timezone.utc)

    except Exception as exc:
        logger.exception("Error processing %s event (delivery=%s)", event_type, delivery_id)
        event_log.status = EventStatus.FAILED
        event_log.error_message = str(exc)
        event_log.processed_at = datetime.now(timezone.utc)

    return event_log


def _process_pull_request(data: dict[str, Any]) -> None:
    from app.services.bounty_status_service import (
        find_bounty_by_issue_number,
        transition_to_completed,
        transition_to_in_progress,
    )

    action = data.get("action", "")
    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    repo_full_name = repo.get("full_name", "")
    pr_body = pr.get("body") or ""
    pr_number = pr.get("number") or data.get("number")

    issue_numbers = extract_issue_numbers(pr_body)
    if not issue_numbers:
        return

    merged = pr.get("merged", False)

    for issue_num in issue_numbers:
        bounty = find_bounty_by_issue_number(issue_num, repo_full_name)
        if not bounty:
            continue

        if action in ("opened", "reopened"):
            transition_to_in_progress(bounty)
            logger.info("PR #%s -> bounty %s set to in_progress", pr_number, bounty.id)

        elif action == "closed" and merged:
            transition_to_completed(bounty)
            logger.info("PR #%s merged -> bounty %s set to completed", pr_number, bounty.id)
            _trigger_payout_webhook(bounty.id, issue_num, pr_number, repo_full_name)


def _process_issue(data: dict[str, Any]) -> None:
    from app.services.bounty_status_service import auto_create_bounty_from_issue

    action = data.get("action", "")
    issue = data.get("issue", {})
    repo = data.get("repository", {})
    repo_full_name = repo.get("full_name", "")

    if action == "labeled":
        label = data.get("label", {})
        label_name = label.get("name", "")
        if label_name.lower() == "bounty":
            bounty_id = auto_create_bounty_from_issue(issue, repo_full_name)
            if bounty_id:
                logger.info("Issue #%s labeled 'bounty' -> created bounty %s", issue.get("number"), bounty_id)


def _trigger_payout_webhook(bounty_id: str, issue_number: int, pr_number: int, repo: str) -> None:
    logger.info("PAYOUT TRIGGER: bounty=%s, issue=#%s, pr=#%s, repo=%s", bounty_id, issue_number, pr_number, repo)
