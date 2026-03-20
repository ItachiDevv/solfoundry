"""In-memory search & filter engine for bounties.

Provides text search with relevance scoring, multi-facet filtering,
configurable sorting, and cursor-based pagination.  Designed to be
swapped for PostgreSQL full-text search (tsvector + GIN) in production.
"""

from __future__ import annotations

import math
import re
from typing import Callable, Optional

from app.models.bounty import BountyDB
from app.models.search import (
    AutocompleteItem,
    AutocompleteResponse,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
    SortOrder,
)
from app.services.bounty_service import _bounty_store

# ---------- text helpers ----------

_SANITIZE_RE = re.compile(r"[^\w\s-]", re.UNICODE)


def _sanitize(text: str) -> str:
    """Strip special / potentially dangerous characters from user input."""
    return _SANITIZE_RE.sub("", text).strip()


def _words(text: str) -> list[str]:
    """Lowercase split, dropping empties."""
    return [w for w in text.lower().split() if w]

# ---------- relevance scoring ----------

_SCORE_RULES: list[tuple[str, Callable[[BountyDB, str, list[str]], float]]] = []


def _rule(label: str):
    """Decorator that registers a scoring rule."""
    def decorator(fn: Callable[[BountyDB, str, list[str]], float]):
        _SCORE_RULES.append((label, fn))
        return fn
    return decorator


@_rule("exact_title")
def _exact_title(b: BountyDB, q: str, words: list[str]) -> float:
    return 10.0 if b.title.lower() == q else 0.0


@_rule("title_contains")
def _title_contains(b: BountyDB, q: str, words: list[str]) -> float:
    tl = b.title.lower()
    if q not in tl:
        return 0.0
    return 7.0 if tl.startswith(q) else 5.0


@_rule("desc_contains")
def _desc_contains(b: BountyDB, q: str, words: list[str]) -> float:
    return 2.0 if q in b.description.lower() else 0.0


@_rule("word_hits")
def _word_hits(b: BountyDB, q: str, words: list[str]) -> float:
    tl, dl = b.title.lower(), b.description.lower()
    skills_blob = " ".join(s.lower() for s in b.required_skills)
    score = 0.0
    for w in words:
        score += 2.0 * (w in tl) + 1.0 * (w in dl) + 3.0 * (w in skills_blob)
    return score


def _compute_relevance(bounty: BountyDB, query: str) -> float:
    if not query:
        return 0.0
    q = _sanitize(query).lower()
    ws = _words(q)
    return sum(fn(bounty, q, ws) for _, fn in _SCORE_RULES)


def _matches_text(bounty: BountyDB, query: str) -> bool:
    """Return True when *any* query word appears in title / description / skills."""
    if not query:
        return True
    q = _sanitize(query).lower()
    ws = _words(q)
    searchable = f"{bounty.title} {bounty.description} {' '.join(bounty.required_skills)}".lower()
    return any(w in searchable for w in ws)

# ---------- filtering (single-pass pipeline) ----------

FilterFn = Callable[[BountyDB], bool]


def _build_filters(query: SearchQuery) -> list[FilterFn]:
    """Construct a list of predicate functions from the search query."""
    filters: list[FilterFn] = []
    if query.q:
        q_copy = query.q  # capture for closure
        filters.append(lambda b, _q=q_copy: _matches_text(b, _q))
    if query.tier is not None:
        t = query.tier
        filters.append(lambda b, _t=t: b.tier.value == _t)
    if query.status:
        s = query.status.lower()
        filters.append(lambda b, _s=s: b.status.value == _s)
    if query.reward_min is not None:
        mn = query.reward_min
        filters.append(lambda b, _mn=mn: b.reward_amount >= _mn)
    if query.reward_max is not None:
        mx = query.reward_max
        filters.append(lambda b, _mx=mx: b.reward_amount <= _mx)
    if query.skills:
        required = {s.lower() for s in query.skills}
        filters.append(lambda b, _r=required: _r.issubset({s.lower() for s in b.required_skills}))
    return filters


def _apply_filters(bounties: list[BountyDB], query: SearchQuery) -> list[BountyDB]:
    predicates = _build_filters(query)
    if not predicates:
        return bounties
    return [b for b in bounties if all(p(b) for p in predicates)]

# ---------- sorting ----------

_SORT_KEYS: dict[SortOrder, tuple[Callable[[BountyDB], object], bool]] = {
    SortOrder.NEWEST: (lambda b: b.created_at, True),
    SortOrder.OLDEST: (lambda b: b.created_at, False),
    SortOrder.REWARD_HIGH: (lambda b: b.reward_amount, True),
    SortOrder.REWARD_LOW: (lambda b: b.reward_amount, False),
}


def _sort_results(bounties: list[BountyDB], sort: SortOrder) -> list[BountyDB]:
    if sort == SortOrder.DEADLINE_SOONEST:
        return sorted(bounties, key=lambda b: (b.deadline is None, b.deadline or b.created_at))
    key_fn, reverse = _SORT_KEYS.get(sort, (lambda b: b.created_at, True))
    return sorted(bounties, key=key_fn, reverse=reverse)

# ---------- conversion ----------


def _to_result(bounty: BountyDB, relevance: float = 0.0) -> SearchResultItem:
    return SearchResultItem(
        id=bounty.id, title=bounty.title, description=bounty.description,
        tier=bounty.tier.value, reward_amount=bounty.reward_amount,
        status=bounty.status.value, required_skills=bounty.required_skills,
        deadline=bounty.deadline.isoformat() if bounty.deadline else None,
        created_by=bounty.created_by, claim_count=bounty.claim_count,
        submission_count=bounty.submission_count,
        created_at=bounty.created_at.isoformat(),
        updated_at=bounty.updated_at.isoformat(), relevance_score=relevance,
    )

# ---------- public API ----------


def search_bounties(query: SearchQuery) -> SearchResponse:
    """Full pipeline: filter -> score -> sort -> paginate."""
    all_bounties = list(_bounty_store.values())
    filtered = _apply_filters(all_bounties, query)

    # Compute relevance when there is a text query
    relevance_map: dict[str, float] = {}
    if query.q:
        relevance_map = {b.id: _compute_relevance(b, query.q) for b in filtered}

    # Sort: relevance-first when text search + default sort, else explicit sort
    if query.q and query.sort == SortOrder.NEWEST:
        filtered.sort(key=lambda b: relevance_map.get(b.id, 0.0), reverse=True)
    else:
        filtered = _sort_results(filtered, query.sort)

    total = len(filtered)
    total_pages = max(1, math.ceil(total / query.page_size))
    offset = (query.page - 1) * query.page_size
    page_items = filtered[offset: offset + query.page_size]

    items = [_to_result(b, relevance_map.get(b.id, 0.0)) for b in page_items]

    filters_applied = {
        k: v for k, v in {
            "tier": query.tier, "status": query.status,
            "reward_min": query.reward_min, "reward_max": query.reward_max,
            "skills": query.skills,
        }.items() if v is not None
    }

    return SearchResponse(
        items=items, total=total, page=query.page,
        page_size=query.page_size, total_pages=total_pages,
        query=query.q, filters_applied=filters_applied,
    )


def autocomplete(query: str, limit: int = 10) -> AutocompleteResponse:
    """Prefix-first autocomplete over bounty titles."""
    q = _sanitize(query).lower()
    if not q:
        return AutocompleteResponse(suggestions=[], query=query)

    PREFIX, SUBSTRING = 0, 1
    candidates: list[tuple[int, BountyDB]] = []
    for bounty in _bounty_store.values():
        tl = bounty.title.lower()
        if tl.startswith(q):
            candidates.append((PREFIX, bounty))
        elif q in tl:
            candidates.append((SUBSTRING, bounty))

    candidates.sort(key=lambda x: (x[0], x[1].title.lower()))

    suggestions = [
        AutocompleteItem(
            id=b.id, title=b.title, tier=b.tier.value,
            reward_amount=b.reward_amount, status=b.status.value,
        )
        for _, b in candidates[:limit]
    ]
    return AutocompleteResponse(suggestions=suggestions, query=query)
