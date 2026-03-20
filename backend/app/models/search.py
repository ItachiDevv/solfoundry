"""Search & filter models for the bounty search engine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    """Available sort options for search results."""
    NEWEST = "newest"
    OLDEST = "oldest"
    REWARD_HIGH = "reward_high"
    REWARD_LOW = "reward_low"
    DEADLINE_SOONEST = "deadline_soonest"


class SearchQuery(BaseModel):
    """Validated query parameters for bounty search."""
    q: Optional[str] = None
    tier: Optional[int] = Field(None, ge=1, le=3)
    status: Optional[str] = None
    reward_min: Optional[float] = Field(None, ge=0)
    reward_max: Optional[float] = Field(None, ge=0)
    skills: Optional[list[str]] = None
    sort: SortOrder = SortOrder.NEWEST
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SearchResultItem(BaseModel):
    """A single search result with relevance metadata."""
    id: str
    title: str
    description: str
    tier: int
    reward_amount: float
    status: str
    required_skills: list[str] = []
    deadline: Optional[str] = None
    created_by: str = "system"
    claim_count: int = 0
    submission_count: int = 0
    created_at: str
    updated_at: str
    relevance_score: float = 0.0


class SearchResponse(BaseModel):
    """Paginated search response with filter metadata."""
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    query: Optional[str] = None
    filters_applied: dict = Field(default_factory=dict)


class AutocompleteItem(BaseModel):
    """Single autocomplete suggestion."""
    id: str
    title: str
    tier: int
    reward_amount: float
    status: str


class AutocompleteResponse(BaseModel):
    """Wraps autocomplete suggestions with the original query."""
    suggestions: list[AutocompleteItem]
    query: str
