"""
FastAPI application entry point for the Hidden Agenda RL-agent gym backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analytics, experiments, replays

app = FastAPI(
    title="Hidden Agenda RL-Agent Gym",
    description=(
        "REST API for running Hidden Agenda multi-agent RL experiments "
        "backed by AWS EC2 + S3."
    ),
    version="1.0.0",
)

# Allow the React frontend (and Cloudflare-proxied origins) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments.router)
app.include_router(analytics.router)
app.include_router(replays.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "hidden-agenda-rl-gym"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
