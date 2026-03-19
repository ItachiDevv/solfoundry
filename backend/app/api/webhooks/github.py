"""GitHub webhook receiver endpoint."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.services.event_processor import is_duplicate as _evt_is_dup
from app.services.event_processor import process_event as _evt_proc
from app.services.webhook_service import (
    WebhookVerificationError,
    parse_event,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/github")
async def receive_github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
) -> JSONResponse:
    """Receive and process GitHub webhook events."""
    payload = await request.body()

    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if webhook_secret:
        try:
            verify_signature(payload, x_hub_signature_256 or "", webhook_secret)
        except WebhookVerificationError as exc:
            logger.warning("Webhook verification failed: %s", exc)
            return JSONResponse(status_code=401, content={"error": str(exc)})
    else:
        logger.warning("GITHUB_WEBHOOK_SECRET not set -- skipping verification")

    event_type = x_github_event or "unknown"

    try:
        parsed: dict[str, Any] = parse_event(event_type, payload)
    except Exception as exc:
        logger.error("Failed to parse %s event: %s", event_type, exc)
        return JSONResponse(status_code=422, content={"error": f"Parse error: {exc}"})

    if event_type == "ping":
        return JSONResponse(status_code=200, content={"msg": "pong"})

    delivery_id = x_github_delivery or ""
    if delivery_id and _evt_is_dup(delivery_id):
        return JSONResponse(status_code=200, content={"status": "duplicate", "event": event_type})

    if delivery_id:
        event_log = _evt_proc(delivery_id, event_type, payload, parsed)
        logger.info("Event processed: delivery=%s status=%s", delivery_id, event_log.status)

    return JSONResponse(status_code=202, content={"status": "accepted", "event": event_type})
