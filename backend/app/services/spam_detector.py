"""
SolFoundry Advanced Spam Detector

ML-lite spam detection beyond the basic filter in ai_review.py.

Checks:
  - Submission velocity: >N PRs in 1 hour from same user
  - Code similarity: cosine similarity against previous rejected PRs
  - Repository history: new accounts with T2/T3 submissions
  - Bounty sniping: same user submitting to >N bounties simultaneously
  - Copy-paste detection: large identical blocks from known sources
  - AI slop patterns: excessive boilerplate, generic names, no project refs
  - Consecutive rejection detection: user has multiple recent rejections
  - Diff fingerprinting: hashing diff structure for duplicate submissions

Scoring: each check adds penalty points; threshold triggers flag or auto-reject.
Configurable thresholds per tier.
"""

import hashlib
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.models.spam import (
    SpamCheckDetail,
    SpamCheckResponse,
    SpamConfigResponse,
    SpamHistoryItem,
    SpamHistoryResponse,
    SpamStatsResponse,
)


# ── Configuration (mutable at runtime via PATCH /api/spam/config) ────────────

_config: dict = {
    "velocity_max_prs_per_hour": 3,
    "similarity_threshold": 0.75,
    "new_account_days": 7,
    "bounty_snipe_max_simultaneous": 5,
    "copy_paste_min_block_size": 50,
    "ai_slop_boilerplate_threshold": 30,
    "penalty_threshold_flag": 15.0,
    "penalty_threshold_reject": 30.0,
    "tier_multipliers": {
        "tier-1": 1.0,
        "tier-2": 1.3,
        "tier-3": 1.6,
        "unknown": 1.0,
    },
}


def get_config() -> SpamConfigResponse:
    return SpamConfigResponse(**_config)


def update_config(updates: dict) -> SpamConfigResponse:
    for key, value in updates.items():
        if value is not None and key in _config:
            _config[key] = value
    return get_config()


# ── In-memory stores (MVP — replace with Redis/DB in production) ─────────────

# Spam check history: list of SpamCheckResponse dicts
_history: list[dict] = []

# Per-user PR submission timestamps for velocity check
_user_submissions: dict[str, list[datetime]] = {}

# Rejected PR diffs for similarity comparison (pr_number -> tokenized diff)
_rejected_diffs: dict[int, list[str]] = {}

# Per-user active bounty issues (user -> set of issue numbers)
_user_active_bounties: dict[str, set[int]] = {}

# Per-user rejection counts (user -> list of rejection timestamps)
_user_rejections: dict[str, list[datetime]] = {}

# Diff fingerprints (hash -> pr_number) for dedup detection
_diff_fingerprints: dict[str, int] = {}

# False positive reports
_false_positive_count: int = 0


# ── Tokenizer / Similarity Helpers ───────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for code diffs."""
    # Strip diff metadata lines
    lines = []
    for line in text.split("\n"):
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+") or line.startswith("-"):
            lines.append(line[1:])
        else:
            lines.append(line)
    cleaned = " ".join(lines)
    tokens = re.findall(r"[a-zA-Z_]\w*|[{}()\[\];,=<>!+\-*/&|]", cleaned)
    return [t.lower() for t in tokens]


def _cosine_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Compute cosine similarity between two token lists."""
    if not tokens_a or not tokens_b:
        return 0.0
    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    all_tokens = set(counter_a.keys()) | set(counter_b.keys())

    dot = sum(counter_a.get(t, 0) * counter_b.get(t, 0) for t in all_tokens)
    mag_a = math.sqrt(sum(v ** 2 for v in counter_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in counter_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _fingerprint_diff(diff: str) -> str:
    """Create a structural fingerprint of a diff by hashing its shape."""
    lines = diff.strip().split("\n")
    # Keep only structural shape: line prefixes and lengths bucketed
    shape_parts = []
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        prefix = line[0] if line else " "
        length_bucket = len(line) // 20
        shape_parts.append(f"{prefix}{length_bucket}")
    shape = "|".join(shape_parts)
    return hashlib.sha256(shape.encode()).hexdigest()[:16]


# ── Individual Checks ────────────────────────────────────────────────────────

def _check_velocity(user: str) -> SpamCheckDetail:
    """Flag if user submitted >N PRs in the last hour."""
    max_prs = _config["velocity_max_prs_per_hour"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)

    recent = [ts for ts in _user_submissions.get(user, []) if ts > cutoff]
    if len(recent) >= max_prs:
        return SpamCheckDetail(
            check_name="submission_velocity",
            passed=False,
            penalty=10.0,
            reason=f"User submitted {len(recent)} PRs in the last hour (max: {max_prs})",
        )
    return SpamCheckDetail(check_name="submission_velocity", passed=True)


def _check_similarity(diff: str) -> SpamCheckDetail:
    """Compare diff against previously rejected PRs using cosine similarity."""
    threshold = _config["similarity_threshold"]
    tokens = _tokenize(diff)
    if not tokens:
        return SpamCheckDetail(check_name="code_similarity", passed=True)

    max_sim = 0.0
    matched_pr = None
    for pr_num, rejected_tokens in _rejected_diffs.items():
        sim = _cosine_similarity(tokens, rejected_tokens)
        if sim > max_sim:
            max_sim = sim
            matched_pr = pr_num

    if max_sim >= threshold:
        return SpamCheckDetail(
            check_name="code_similarity",
            passed=False,
            penalty=15.0,
            reason=f"Diff is {max_sim:.0%} similar to previously rejected PR #{matched_pr}",
        )
    return SpamCheckDetail(check_name="code_similarity", passed=True)


def _check_new_account(user: str, tier: str, account_age_days: Optional[int] = None) -> SpamCheckDetail:
    """Extra scrutiny for new accounts submitting T2/T3 bounties."""
    if tier not in ("tier-2", "tier-3"):
        return SpamCheckDetail(check_name="new_account_scrutiny", passed=True)

    min_days = _config["new_account_days"]
    # In production, query GitHub API for account age; for now use param or skip
    if account_age_days is None:
        return SpamCheckDetail(check_name="new_account_scrutiny", passed=True)

    if account_age_days < min_days:
        return SpamCheckDetail(
            check_name="new_account_scrutiny",
            passed=False,
            penalty=12.0,
            reason=f"Account is {account_age_days}d old (min {min_days}d for {tier})",
        )
    return SpamCheckDetail(check_name="new_account_scrutiny", passed=True)


def _check_bounty_sniping(user: str, bounty_issue: Optional[int] = None) -> SpamCheckDetail:
    """Flag if user is submitting to too many bounties simultaneously."""
    max_bounties = _config["bounty_snipe_max_simultaneous"]
    active = _user_active_bounties.get(user, set())
    if bounty_issue is not None:
        active = active | {bounty_issue}

    if len(active) > max_bounties:
        return SpamCheckDetail(
            check_name="bounty_sniping",
            passed=False,
            penalty=10.0,
            reason=f"User has {len(active)} active bounty submissions (max: {max_bounties})",
        )
    return SpamCheckDetail(check_name="bounty_sniping", passed=True)


def _check_copy_paste(diff: str) -> SpamCheckDetail:
    """Detect large blocks of identical code repeated in the diff."""
    min_block = _config["copy_paste_min_block_size"]
    lines = diff.split("\n")
    if len(lines) < min_block:
        return SpamCheckDetail(check_name="copy_paste_detection", passed=True)

    # Sliding window: find repeated blocks of min_block lines
    seen_blocks: dict[str, int] = {}
    max_repeats = 0
    for i in range(len(lines) - min_block + 1):
        block = "\n".join(lines[i : i + min_block])
        block_hash = hashlib.md5(block.encode()).hexdigest()
        seen_blocks[block_hash] = seen_blocks.get(block_hash, 0) + 1
        max_repeats = max(max_repeats, seen_blocks[block_hash])

    if max_repeats > 3:
        return SpamCheckDetail(
            check_name="copy_paste_detection",
            passed=False,
            penalty=8.0,
            reason=f"Detected {max_repeats} repeated blocks of {min_block}+ lines",
        )
    return SpamCheckDetail(check_name="copy_paste_detection", passed=True)


def _check_ai_slop(diff: str) -> SpamCheckDetail:
    """Detect AI-generated slop: excessive boilerplate, generic names, no project refs."""
    threshold = _config["ai_slop_boilerplate_threshold"]
    penalties = 0.0
    reasons = []

    # Generic variable names
    generic_names = re.findall(
        r"\b(?:temp|tmp|data|result|value|item|obj|thing|stuff|foo|bar|baz|myVar|myFunc)\b",
        diff,
        re.IGNORECASE,
    )
    if len(generic_names) > threshold:
        penalties += 5.0
        reasons.append(f"{len(generic_names)} generic variable names")

    # Excessive boilerplate comments
    boilerplate_comments = re.findall(
        r"(?://|#)\s*(?:TODO|FIXME|HACK|XXX|NOTE|PLACEHOLDER|implement|add logic here)",
        diff,
        re.IGNORECASE,
    )
    if len(boilerplate_comments) > 15:
        penalties += 8.0
        reasons.append(f"{len(boilerplate_comments)} boilerplate comments")

    # No project-specific references (SolFoundry, FNDRY, Solana, bounty)
    project_refs = re.findall(
        r"\b(?:solfoundry|fndry|solana|bounty|contributor)\b",
        diff,
        re.IGNORECASE,
    )
    lines_added = len([l for l in diff.split("\n") if l.startswith("+")])
    if lines_added > 100 and len(project_refs) == 0:
        penalties += 6.0
        reasons.append("No project-specific references in 100+ lines")

    # Excessive docstring-to-code ratio (AI loves verbose docstrings)
    docstring_lines = len(re.findall(r'^\+\s*(?:"""|\'\'\'|/\*\*|\*\s)', diff, re.MULTILINE))
    if lines_added > 50 and docstring_lines > lines_added * 0.4:
        penalties += 4.0
        reasons.append(f"High docstring ratio ({docstring_lines}/{lines_added} lines)")

    if penalties > 0:
        return SpamCheckDetail(
            check_name="ai_slop_patterns",
            passed=False,
            penalty=penalties,
            reason="; ".join(reasons),
        )
    return SpamCheckDetail(check_name="ai_slop_patterns", passed=True)


def _check_consecutive_rejections(user: str) -> SpamCheckDetail:
    """Flag users with multiple recent rejections."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)
    recent = [ts for ts in _user_rejections.get(user, []) if ts > cutoff]

    if len(recent) >= 3:
        return SpamCheckDetail(
            check_name="consecutive_rejections",
            passed=False,
            penalty=12.0,
            reason=f"User has {len(recent)} rejections in the last 48h",
        )
    if len(recent) >= 2:
        return SpamCheckDetail(
            check_name="consecutive_rejections",
            passed=False,
            penalty=6.0,
            reason=f"User has {len(recent)} rejections in the last 48h",
        )
    return SpamCheckDetail(check_name="consecutive_rejections", passed=True)


def _check_diff_fingerprint(diff: str, pr_number: int) -> SpamCheckDetail:
    """Detect duplicate submissions via structural diff fingerprinting."""
    fp = _fingerprint_diff(diff)
    existing = _diff_fingerprints.get(fp)
    if existing is not None and existing != pr_number:
        return SpamCheckDetail(
            check_name="diff_fingerprint",
            passed=False,
            penalty=20.0,
            reason=f"Diff structure matches PR #{existing} (duplicate submission)",
        )
    return SpamCheckDetail(check_name="diff_fingerprint", passed=True)


# ── Main Check Runner ────────────────────────────────────────────────────────

def run_spam_check(
    pr_number: int,
    pr_author: str,
    pr_title: str = "",
    pr_body: str = "",
    diff: str = "",
    tier: str = "unknown",
    bounty_issue: Optional[int] = None,
    account_age_days: Optional[int] = None,
) -> SpamCheckResponse:
    """Run all spam checks and return aggregated result."""
    details: list[SpamCheckDetail] = []

    # Run all checks
    details.append(_check_velocity(pr_author))
    details.append(_check_similarity(diff))
    details.append(_check_new_account(pr_author, tier, account_age_days))
    details.append(_check_bounty_sniping(pr_author, bounty_issue))
    details.append(_check_copy_paste(diff))
    details.append(_check_ai_slop(diff))
    details.append(_check_consecutive_rejections(pr_author))
    details.append(_check_diff_fingerprint(diff, pr_number))

    # Apply tier multiplier to penalties
    multiplier = _config["tier_multipliers"].get(tier, 1.0)
    total_penalty = sum(d.penalty for d in details) * multiplier

    threshold_flag = _config["penalty_threshold_flag"]
    threshold_reject = _config["penalty_threshold_reject"]

    is_spam = total_penalty >= threshold_flag
    if total_penalty >= threshold_reject:
        auto_action = "auto-reject"
    elif total_penalty >= threshold_flag:
        auto_action = "flag"
    else:
        auto_action = "none"

    response = SpamCheckResponse(
        pr_number=pr_number,
        pr_author=pr_author,
        is_spam=is_spam,
        total_penalty=round(total_penalty, 1),
        threshold=threshold_flag,
        details=details,
        auto_action=auto_action,
    )

    # Record in history
    _history.append(response.model_dump())

    # Record user submission timestamp
    now = datetime.now(timezone.utc)
    if pr_author not in _user_submissions:
        _user_submissions[pr_author] = []
    _user_submissions[pr_author].append(now)

    # Record diff fingerprint
    if diff:
        fp = _fingerprint_diff(diff)
        _diff_fingerprints[fp] = pr_number

    # Track active bounties per user
    if bounty_issue is not None:
        if pr_author not in _user_active_bounties:
            _user_active_bounties[pr_author] = set()
        _user_active_bounties[pr_author].add(bounty_issue)

    return response


def record_rejection(pr_number: int, pr_author: str, diff: str = ""):
    """Record a rejection for tracking consecutive rejections and similarity."""
    now = datetime.now(timezone.utc)
    if pr_author not in _user_rejections:
        _user_rejections[pr_author] = []
    _user_rejections[pr_author].append(now)

    if diff:
        _rejected_diffs[pr_number] = _tokenize(diff)


def report_false_positive():
    """Increment the false positive counter."""
    global _false_positive_count
    _false_positive_count += 1


def get_history(skip: int = 0, limit: int = 20) -> SpamHistoryResponse:
    """Return paginated spam check history (newest first)."""
    sorted_history = sorted(_history, key=lambda x: x["checked_at"], reverse=True)
    total = len(sorted_history)
    items = []
    for h in sorted_history[skip : skip + limit]:
        items.append(SpamHistoryItem(
            pr_number=h["pr_number"],
            pr_author=h["pr_author"],
            is_spam=h["is_spam"],
            total_penalty=h["total_penalty"],
            auto_action=h["auto_action"],
            checked_at=h["checked_at"],
        ))
    return SpamHistoryResponse(items=items, total=total, skip=skip, limit=limit)


def get_stats() -> SpamStatsResponse:
    """Return aggregated spam detection stats."""
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    total = len(_history)
    flagged = sum(1 for h in _history if h["is_spam"])
    rejected = sum(1 for h in _history if h["auto_action"] == "auto-reject")
    clean = total - flagged

    # Checks in time windows
    checks_24h = sum(
        1 for h in _history
        if _parse_dt(h["checked_at"]) > cutoff_24h
    )
    checks_7d = sum(
        1 for h in _history
        if _parse_dt(h["checked_at"]) > cutoff_7d
    )

    # Top failure reasons
    reason_counter: Counter = Counter()
    for h in _history:
        for d in h.get("details", []):
            if not d.get("passed", True) and d.get("reason"):
                reason_counter[d["check_name"]] += 1
    top_reasons = [
        {"check": name, "count": count}
        for name, count in reason_counter.most_common(5)
    ]

    return SpamStatsResponse(
        total_checks=total,
        total_flagged=flagged,
        total_auto_rejected=rejected,
        total_clean=clean,
        false_positives_reported=_false_positive_count,
        top_reasons=top_reasons,
        checks_last_24h=checks_24h,
        checks_last_7d=checks_7d,
    )


def _parse_dt(val) -> datetime:
    """Parse a datetime from either a datetime object or ISO string."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return datetime.min.replace(tzinfo=timezone.utc)


# ── Store reset (for testing) ────────────────────────────────────────────────

def _reset_stores():
    """Reset all in-memory stores. For testing only."""
    global _false_positive_count
    _history.clear()
    _user_submissions.clear()
    _rejected_diffs.clear()
    _user_active_bounties.clear()
    _user_rejections.clear()
    _diff_fingerprints.clear()
    _false_positive_count = 0
    # Reset config to defaults
    _config.update({
        "velocity_max_prs_per_hour": 3,
        "similarity_threshold": 0.75,
        "new_account_days": 7,
        "bounty_snipe_max_simultaneous": 5,
        "copy_paste_min_block_size": 50,
        "ai_slop_boilerplate_threshold": 30,
        "penalty_threshold_flag": 15.0,
        "penalty_threshold_reject": 30.0,
        "tier_multipliers": {
            "tier-1": 1.0,
            "tier-2": 1.3,
            "tier-3": 1.6,
            "unknown": 1.0,
        },
    })
