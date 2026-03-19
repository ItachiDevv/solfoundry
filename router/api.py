"""FastAPI router exposing the LLM Router endpoints."""

from fastapi import APIRouter, HTTPException

from router.config import ModelId
from router.llm_router import LLMRouter, LLMRouterError
from router.models import CostSummary, ReviewRequest, ReviewResponse, RouterHealthResponse

router = APIRouter(prefix="/api/router", tags=["llm-router"])

# Singleton router instance — replaced in tests via dependency override.
_llm_router = LLMRouter()


def get_llm_router() -> LLMRouter:
    """Return the module-level LLM router (allows test overrides)."""
    return _llm_router


@router.post("/review", response_model=ReviewResponse)
async def submit_review(request: ReviewRequest):
    """Submit content for LLM review. The router picks the best model."""
    try:
        return get_llm_router().route(request)
    except LLMRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/costs", response_model=list[CostSummary])
async def get_costs():
    """Return per-model cost summary."""
    return get_llm_router().get_cost_summary()


@router.get("/costs/{model_id}", response_model=CostSummary)
async def get_model_cost(model_id: ModelId):
    """Return cost summary for a specific model."""
    try:
        return get_llm_router().get_cost_for_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Model not found") from exc


@router.get("/health", response_model=RouterHealthResponse)
async def router_health():
    """Health check for all configured LLM providers."""
    llm = get_llm_router()
    models_status = {
        mid.value: cfg.enabled for mid, cfg in llm.models.items()
    }
    return RouterHealthResponse(
        healthy=any(models_status.values()),
        models=models_status,
    )
