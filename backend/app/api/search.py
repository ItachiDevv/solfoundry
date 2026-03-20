"""Search & filter API endpoints for bounties."""

from typing import Optional

from fastapi import APIRouter, Query

from app.models.search import AutocompleteResponse, SearchQuery, SearchResponse, SortOrder
from app.services import search_service

router = APIRouter(prefix="/api/bounties", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search_bounties(
    q: Optional[str] = Query(None, description="Full-text search keyword"),
    tier: Optional[int] = Query(None, ge=1, le=3),
    status: Optional[str] = Query(None, description="open|in_progress|completed|paid"),
    reward_min: Optional[float] = Query(None, ge=0),
    reward_max: Optional[float] = Query(None, ge=0),
    skills: Optional[str] = Query(None, description="Comma-separated skill tags"),
    sort: SortOrder = Query(SortOrder.NEWEST),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """Search bounties with full-text search, filters, sorting, and pagination."""
    parsed_skills = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    return search_service.search_bounties(SearchQuery(
        q=q, tier=tier, status=status, reward_min=reward_min,
        reward_max=reward_max, skills=parsed_skills, sort=sort,
        page=page, page_size=page_size,
    ))


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_bounties(
    q: str = Query(..., min_length=1, description="Prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=50),
) -> AutocompleteResponse:
    """Return title-based autocomplete suggestions (prefix > substring)."""
    return search_service.autocomplete(query=q, limit=limit)
