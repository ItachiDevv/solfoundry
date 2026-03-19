"""Email notification service using Resend API.

Resend is opt-in and requires RESEND_API_KEY and RESEND_FROM_EMAIL env vars.
When not configured, email sending silently no-ops.
"""

import logging
import os
from typing import Any

import httpx

from app.models.notification import NotificationType

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _get_resend_config() -> tuple[str, str] | None:
    api_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("RESEND_FROM_EMAIL", "")
    if not api_key or not from_email:
        return None
    return api_key, from_email


_SUBJECT_MAP: dict[NotificationType, str] = {
    NotificationType.BOUNTY_CLAIMED: "Bounty Claimed",
    NotificationType.PR_SUBMITTED: "PR Submitted for Bounty",
    NotificationType.REVIEW_COMPLETE: "Review Complete",
    NotificationType.PAYOUT_SENT: "Payout Sent",
    NotificationType.BOUNTY_EXPIRED: "Bounty Expired",
    NotificationType.RANK_CHANGED: "Your Rank Changed",
}


def _build_email_body(
    notification_type: NotificationType, message: str, metadata: dict[str, Any],
) -> str:
    subject = _SUBJECT_MAP.get(notification_type, "Notification")
    lines = [f"SolFoundry Notification: {subject}", "", message, ""]
    if metadata:
        lines.append("Details:")
        for k, v in metadata.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
    lines.append("-- SolFoundry")
    return "\n".join(lines)


async def send_notification_email(
    to_email: str, notification_type: NotificationType,
    message: str, metadata: dict[str, Any] | None = None,
) -> bool:
    """Send email via Resend. Returns True on success, False otherwise."""
    config = _get_resend_config()
    if config is None:
        logger.debug("Resend not configured, skipping email to %s", to_email)
        return False
    api_key, from_email = config
    metadata = metadata or {}
    subject = f"[SolFoundry] {_SUBJECT_MAP.get(notification_type, 'Notification')}"
    body = _build_email_body(notification_type, message, metadata)
    payload = {"from": from_email, "to": [to_email], "subject": subject, "text": body}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                RESEND_API_URL, json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=10.0,
            )
        if resp.status_code in (200, 201):
            logger.info("Email sent to %s (type=%s)", to_email, notification_type.value)
            return True
        else:
            logger.warning("Resend API returned %d: %s", resp.status_code, resp.text)
            return False
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
