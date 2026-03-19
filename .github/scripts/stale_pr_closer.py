#!/usr/bin/env python3
"""
SolFoundry Stale PR Auto-Closer

Closes PRs that have had the "changes-requested" label for >72 hours
with no new commits. Skips PRs labelled "do-not-close".
Posts an explanatory comment, labels "auto-closed", and notifies Telegram.
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

STALE_HOURS = 72
REPO = os.environ.get("GITHUB_REPOSITORY", "SolFoundry/solfoundry")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
API_BASE = f"https://api.github.com/repos/{REPO}"


def get_open_prs_with_label(label: str) -> list[dict]:
    """Fetch all open PRs that carry a specific label."""
    prs = []
    page = 1
    while True:
        resp = requests.get(
            f"{API_BASE}/pulls",
            headers=HEADERS,
            params={"state": "open", "per_page": 100, "page": page},
        )
        if resp.status_code != 200:
            print(f"Failed to fetch PRs (page {page}): {resp.status_code}")
            break
        batch = resp.json()
        if not batch:
            break
        for pr in batch:
            labels = [l["name"] for l in pr.get("labels", [])]
            if label in labels:
                prs.append(pr)
        page += 1
    return prs


def label_applied_at(pr_number: int, label_name: str) -> datetime | None:
    """Find when a label was added to a PR via the timeline API."""
    resp = requests.get(
        f"{API_BASE}/issues/{pr_number}/events",
        headers=HEADERS,
        params={"per_page": 100},
    )
    if resp.status_code != 200:
        return None
    for event in resp.json():
        if event.get("event") == "labeled" and event.get("label", {}).get("name") == label_name:
            return datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    return None


def latest_commit_date(pr_number: int) -> datetime | None:
    """Get the date of the most recent commit on a PR."""
    resp = requests.get(
        f"{API_BASE}/pulls/{pr_number}/commits",
        headers=HEADERS,
        params={"per_page": 100},
    )
    if resp.status_code != 200:
        return None
    commits = resp.json()
    if not commits:
        return None
    last = commits[-1]
    date_str = last.get("commit", {}).get("committer", {}).get("date", "")
    if not date_str:
        return None
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def close_pr(pr_number: int, comment: str):
    """Post a comment, add auto-closed label, and close the PR."""
    # Post comment
    requests.post(
        f"{API_BASE}/issues/{pr_number}/comments",
        headers=HEADERS,
        json={"body": comment},
    )
    # Add auto-closed label
    requests.post(
        f"{API_BASE}/issues/{pr_number}/labels",
        headers=HEADERS,
        json={"labels": ["auto-closed"]},
    )
    # Close PR
    requests.patch(
        f"{API_BASE}/pulls/{pr_number}",
        headers=HEADERS,
        json={"state": "closed"},
    )
    print(f"  Closed PR #{pr_number}")


def notify_telegram(closed_prs: list[dict]):
    """Send a summary of auto-closed PRs to Telegram."""
    bot_token = os.environ.get("SOLFOUNDRY_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("SOLFOUNDRY_TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram not configured — skipping notification")
        return

    if not closed_prs:
        return

    lines = [f"\U0001f551 <b>Stale PR Auto-Closer</b> — {len(closed_prs)} PR(s) closed\n"]
    for pr in closed_prs:
        lines.append(
            f"  \u2022 <b>#{pr['number']}</b>: {pr['title']}\n"
            f"    by {pr['author']} — stale {pr['stale_hours']}h\n"
            f"    <a href='{pr['url']}'>View PR</a>"
        )

    msg = "\n".join(lines)
    if len(msg) > 3800:
        msg = msg[:3800] + "\n\n<i>... truncated</i>"

    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )
    print(f"Telegram notification: {resp.status_code}")


def main():
    print(f"SolFoundry Stale PR Closer — checking {REPO}")
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=STALE_HOURS)

    prs = get_open_prs_with_label("changes-requested")
    print(f"Found {len(prs)} open PRs with 'changes-requested' label")

    closed = []
    for pr in prs:
        number = pr["number"]
        title = pr["title"]
        author = pr.get("user", {}).get("login", "unknown")
        labels = [l["name"] for l in pr.get("labels", [])]
        html_url = pr.get("html_url", "")

        # Skip PRs with do-not-close label
        if "do-not-close" in labels:
            print(f"  PR #{number}: has do-not-close label — skipping")
            continue

        # Check when the label was applied
        label_time = label_applied_at(number, "changes-requested")
        if not label_time:
            print(f"  PR #{number}: could not determine label time — skipping")
            continue

        if label_time > cutoff:
            age_hours = (now - label_time).total_seconds() / 3600
            print(f"  PR #{number}: label applied {age_hours:.1f}h ago — not stale yet")
            continue

        # Check if there have been commits since the label was applied
        last_commit = latest_commit_date(number)
        if last_commit and last_commit > label_time:
            print(f"  PR #{number}: has commits after label — skipping")
            continue

        stale_hours = round((now - label_time).total_seconds() / 3600, 1)
        print(f"  PR #{number}: stale for {stale_hours}h — closing")

        comment = (
            f"\U0001f551 **Auto-closed — no updates in {STALE_HOURS} hours**\n\n"
            f"This PR was marked as needing changes {stale_hours:.0f} hours ago, "
            f"but no new commits were pushed.\n\n"
            f"**What you can do:**\n"
            f"- Address the review feedback and open a new PR\n"
            f"- If you need more time, ask a maintainer to add the `do-not-close` label\n\n"
            f"The bounty is still available for anyone to claim.\n\n"
            f"---\n*SolFoundry Stale PR Closer*"
        )

        close_pr(number, comment)
        closed.append({
            "number": number,
            "title": title,
            "author": author,
            "url": html_url,
            "stale_hours": stale_hours,
        })

    print(f"\nDone. Closed {len(closed)} stale PR(s).")
    notify_telegram(closed)


if __name__ == "__main__":
    main()
