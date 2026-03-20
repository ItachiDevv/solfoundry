"""Webhook event processing pipeline with idempotency and event logging.

Responsibilities:
- Deduplicate webhook deliveries by X-GitHub-Delivery ID
- Log every event with payload hash and processing status
- Extract structured metadata (issue references, actions) from events
- Provide an event log for auditing and replay

This module deliberately does NOT import or mutate bounty/sync state.
Downstream consumers should query the event log and react independently.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.event_log import EventLog, EventLogResponse, EventStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory event log (will be backed by a DB in production)
# ---------------------------------------------------------------------------

_event_log_store: dict[str, EventLog] = {}

# Regex matching GitHub-style "Closes #N", "Fixes #N", "Resolves #N"
_CLOSES_PATTERN = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_payload(payload: bytes) -> str:
    """SHA-256 hash of the raw payload bytes for integrity verification."""
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Public API -- event log queries
# ---------------------------------------------------------------------------


def get_event_log(delivery_id: str) -> Optional[EventLog]:
    """Return the log entry for a specific delivery, or None."""
    return _event_log_store.get(delivery_id)


def list_event_logs(
    *,
    event_type: Optional[str] = None,
    status: Optional[EventStatus] = None,
    limit: int = 100,
) -> list[EventLog]:
    """Return event logs, optionally filtered by type or status."""
    logs = list(_event_log_store.values())
    if event_type is not None:
        logs = [lg for lg in logs if lg.event_type == event_type]
    if status is not None:
        logs = [lg for lg in logs if lg.status == status]
    return logs[:limit]


def clear_event_logs() -> None:
    """Reset the in-memory store. Intended for test isolation."""
    _event_log_store.clear()


def event_log_responses() -> list[EventLogResponse]:
    """Return all event logs as API-safe response models."""
    return [
        EventLogResponse(
            delivery_id=lg.delivery_id,
            event_type=lg.event_type,
            payload_hash=lg.payload_hash,
            status=lg.status.value,
            error_message=lg.error_message,
            received_at=lg.received_at,
            processed_at=lg.processed_at,
        )
        for lg in _event_log_store.values()
    ]


# ---------------------------------------------------------------------------
# Public API -- text extraction helpers
# ---------------------------------------------------------------------------


def extract_issue_numbers(text: str) -> list[int]:
    """Extract issue numbers from Closes/Fixes/Resolves #N style references."""
    return [int(m) for m in _CLOSES_PATTERN.findall(text or "")]


# ---------------------------------------------------------------------------
# Public API -- idempotency check
# ---------------------------------------------------------------------------


def is_duplicate(delivery_id: str) -> bool:
    """Return True if the delivery_id has already been processed."""
    return delivery_id in _event_log_store


# ---------------------------------------------------------------------------
# Public API -- core processing
# ---------------------------------------------------------------------------


def process_event(
    delivery_id: str,
    event_type: str,
    payload: bytes,
    parsed_data: dict[str, Any],
) -> EventLog:
    """Process a single webhook event with idempotency guarantees.

    1. Check for duplicate delivery_id (return existing log if found).
    2. Create a PENDING log entry.
    3. Validate and extract metadata from the raw payload.
    4. Transition the log entry to PROCESSED or FAILED.

    Returns the EventLog record (always, even on failure).
    """
    # --- Idempotency guard ---
    if is_duplicate(delivery_id):
        existing = _event_log_store[delivery_id]
        logger.info(
            "Duplicate delivery_id=%s, returning existing (status=%s)",
            delivery_id,
            existing.status,
        )
        return existing

    payload_hash = _hash_payload(payload)

    event_log = EventLog(
        delivery_id=delivery_id,
        event_type=event_type,
        payload_hash=payload_hash,
        status=EventStatus.PENDING,
    )
    _event_log_store[delivery_id] = event_log

    try:
        raw_data = json.loads(payload)
        _extract_metadata(event_type, raw_data, event_log)

        event_log.status = EventStatus.PROCESSED
        event_log.processed_at = datetime.now(timezone.utc)

    except Exception as exc:
        logger.exception(
            "Error processing %s event (delivery=%s)", event_type, delivery_id
        )
        event_log.status = EventStatus.FAILED
        event_log.error_message = str(exc)
        event_log.processed_at = datetime.now(timezone.utc)

    return event_log


# ---------------------------------------------------------------------------
# Internal -- metadata extraction (no side-effects beyond logging)
# ---------------------------------------------------------------------------


def _extract_metadata(
    event_type: str, data: dict[str, Any], event_log: EventLog
) -> None:
    """Extract and log structured metadata from the event payload.

    This function is intentionally read-only: it inspects the payload and
    produces log messages but does NOT modify any external state (bounties,
    sync records, etc.). Downstream services should react to the event log.
    """
    repo = data.get("repository", {})
    repo_name = repo.get("full_name", "unknown")

    if event_type == "pull_request":
        action = data.get("action", "")
        pr = data.get("pull_request", {})
        pr_number = pr.get("number") or data.get("number")
        pr_body = pr.get("body") or ""
        merged = pr.get("merged", False)
        issue_refs = extract_issue_numbers(pr_body)

        logger.info(
            "PR #%s %s on %s (merged=%s, refs=%s)",
            pr_number, action, repo_name, merged, issue_refs,
        )

    elif event_type == "issues":
        action = data.get("action", "")
        issue = data.get("issue", {})
        issue_number = issue.get("number")
        labels = [
            lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
            for lbl in issue.get("labels", [])
        ]

        logger.info(
            "Issue #%s %s on %s (labels=%s)",
            issue_number, action, repo_name, labels,
        )

    elif event_type == "push":
        ref = data.get("ref", "")
        commits = data.get("commits", [])
        logger.info(
            "Push to %s on %s (%d commits)",
            ref, repo_name, len(commits),
        )

    else:
        logger.info("Event %s on %s (no special extraction)", event_type, repo_name)
