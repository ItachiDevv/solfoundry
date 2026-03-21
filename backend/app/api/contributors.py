"""Contributor profiles API router.

Uses in-memory store as primary source and mirrors writes to PostgreSQL
for cross-restart persistence via async sessions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contributor import (
    ContributorCreate,
    ContributorResponse,
    ContributorListResponse,
    ContributorUpdate,
)
from app.services import contributor_service

router = APIRouter(prefix="/contributors", tags=["contributors"])


@router.get("", response_model=ContributorListResponse)
async def list_contributors(
    search: Optional[str] = Query(
        None, description="Search by username or display name"
    ),
    skills: Optional[str] = Query(None, description="Comma-separated skill filter"),
    badges: Optional[str] = Query(None, description="Comma-separated badge filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List contributors with optional search, skill, and badge filters."""
    skill_list = skills.split(",") if skills else None
    badge_list = badges.split(",") if badges else None
    return contributor_service.list_contributors(
        search=search, skills=skill_list, badges=badge_list, skip=skip, limit=limit
    )


@router.post("", response_model=ContributorResponse, status_code=201)
async def create_contributor(
    data: ContributorCreate, session: AsyncSession = Depends(get_db),
):
    """Create a new contributor, persisting to both memory and PostgreSQL."""
    if contributor_service.get_contributor_by_username(data.username):
        raise HTTPException(
            status_code=409, detail=f"Username '{data.username}' already exists"
        )
    result = contributor_service.create_contributor(data)
    try:
        await contributor_service.create_contributor_async(data, session)
    except Exception:
        pass  # In-memory write succeeded; DB mirror is best-effort
    return result


@router.get("/{contributor_id}", response_model=ContributorResponse)
async def get_contributor(contributor_id: str):
    """Fetch a single contributor by ID."""
    c = contributor_service.get_contributor(contributor_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contributor not found")
    return c


@router.patch("/{contributor_id}", response_model=ContributorResponse)
async def update_contributor(
    contributor_id: str, data: ContributorUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Partially update an existing contributor."""
    c = contributor_service.update_contributor(contributor_id, data)
    if not c:
        raise HTTPException(status_code=404, detail="Contributor not found")
    try:
        await contributor_service.update_contributor_async(contributor_id, data, session)
    except Exception:
        pass
    return c


@router.delete("/{contributor_id}", status_code=204)
async def delete_contributor(
    contributor_id: str, session: AsyncSession = Depends(get_db),
):
    """Delete a contributor by ID."""
    if not contributor_service.delete_contributor(contributor_id):
        raise HTTPException(status_code=404, detail="Contributor not found")
    try:
        await contributor_service.delete_contributor_async(contributor_id, session)
    except Exception:
        pass
