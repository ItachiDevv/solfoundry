"""Async GitHub API client for creating issues, labels, and comments."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClientError(Exception):
    """Raised when a GitHub API call fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    """Thin async wrapper around the GitHub REST API.

    Uses httpx for async HTTP calls. Requires a personal access token
    via the ``GITHUB_TOKEN`` env var (or injected at init).
    """

    def __init__(self, token: str | None = None, base_url: str = GITHUB_API_BASE):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = base_url.rstrip("/")

    # ── helpers ────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self, method: str, path: str, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method, url, headers=self._headers(), json=json_body, timeout=30.0
            )
        if resp.status_code >= 400:
            logger.error(
                "GitHub API %s %s returned %s: %s",
                method, path, resp.status_code, resp.text[:500],
            )
            raise GitHubClientError(
                f"GitHub API error {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
            )
        return resp.json()

    # ── public methods ────────────────────────────────────────────────

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue on the given repo.

        Args:
            repo: ``owner/name`` format, e.g. ``SolFoundry/solfoundry``.
            title: Issue title.
            body: Markdown body.
            labels: Label names to attach.
            assignees: GitHub logins to assign.

        Returns:
            The full issue JSON from the API.
        """
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        return await self._request("POST", f"/repos/{repo}/issues", json_body=payload)

    async def update_issue(
        self,
        repo: str,
        issue_number: int,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Update an existing issue."""
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        return await self._request(
            "PATCH", f"/repos/{repo}/issues/{issue_number}", json_body=payload
        )

    async def add_comment(
        self, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Post a comment on an issue or PR."""
        return await self._request(
            "POST",
            f"/repos/{repo}/issues/{issue_number}/comments",
            json_body={"body": body},
        )

    async def add_labels(
        self, repo: str, issue_number: int, labels: list[str]
    ) -> list[dict[str, Any]]:
        """Add labels to an issue."""
        result = await self._request(
            "POST",
            f"/repos/{repo}/issues/{issue_number}/labels",
            json_body={"labels": labels},
        )
        return result if isinstance(result, list) else [result]

    async def get_issue(self, repo: str, issue_number: int) -> dict[str, Any]:
        """Fetch a single issue."""
        return await self._request("GET", f"/repos/{repo}/issues/{issue_number}")


# Module-level singleton (lazy — no network call at import time)
_default_client: GitHubClient | None = None


def get_client() -> GitHubClient:
    """Return the module-level singleton, creating it on first call."""
    global _default_client
    if _default_client is None:
        _default_client = GitHubClient()
    return _default_client
