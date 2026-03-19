"""Agent registry API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    HeartbeatResponse,
)
from app.services import agent_service

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=201)
async def register_agent(data: AgentCreate):
    """Register a new AI agent."""
    if agent_service.get_agent_by_name(data.name):
        raise HTTPException(
            status_code=409, detail=f"Agent name '{data.name}' already exists"
        )
    return agent_service.create_agent(data)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    role: Optional[str] = Query(None, description="Filter by capability/role"),
    status: Optional[str] = Query(None, description="Filter by status: online, offline, suspended"),
    min_success_rate: Optional[float] = Query(
        None, ge=0, le=100, description="Minimum success rate %"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List agents with optional filters."""
    return agent_service.list_agents(
        role=role,
        status=status,
        min_success_rate=min_success_rate,
        skip=skip,
        limit=limit,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent detail with performance stats."""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate):
    """Update agent configuration."""
    agent = agent_service.update_agent(agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(agent_id: str):
    """Agent sends heartbeat to stay online. Must be called within 5 minutes."""
    result = agent_service.heartbeat(agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result
