"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.contributors import router as contributors_router
from app.api.leaderboard import router as leaderboard_router
from app.api.webhooks.github import router as github_webhook_router
from router.api import router as llm_router

app = FastAPI(
    title="SolFoundry Backend",
    description="Autonomous AI Software Factory on Solana",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(contributors_router)
app.include_router(leaderboard_router)
app.include_router(llm_router)
app.include_router(github_webhook_router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
