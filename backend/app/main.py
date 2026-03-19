"""FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.contributors import router as contributors_router
from app.api.leaderboard import router as leaderboard_router
from app.api.spam import router as spam_router
from app.api.webhooks.github import router as github_webhook_router
from app.middleware.rate_limit import RateLimitMiddleware

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

# Rate limiting -- uses Redis in production, in-memory for dev
app.add_middleware(
    RateLimitMiddleware,
    redis_url=os.environ.get("REDIS_URL"),
    enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false",
)

app.include_router(contributors_router)
app.include_router(leaderboard_router)
app.include_router(spam_router, prefix="/api", tags=["spam"])
app.include_router(github_webhook_router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
