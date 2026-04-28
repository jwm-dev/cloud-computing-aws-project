"""
Replay storage and retrieval endpoints.

Endpoints
---------
GET  /replays/{experiment_id}                     List episode IDs
GET  /replays/{experiment_id}/{episode_id}        Full frame-by-frame replay
"""

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from backend.storage import s3_client

router = APIRouter(prefix="/replays", tags=["replays"])


@router.get("/{experiment_id}", response_model=List[str])
def list_replays(experiment_id: str):
    """Return a list of episode IDs that have stored replays."""
    try:
        episodes = s3_client.list_replays(experiment_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 error: {exc}") from exc
    return episodes


@router.get("/{experiment_id}/{episode_id}", response_model=Dict)
def get_replay(experiment_id: str, episode_id: str):
    """Return the full frame-by-frame replay for a specific episode."""
    try:
        replay = s3_client.get_replay(experiment_id, episode_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 error: {exc}") from exc
    if replay is None:
        raise HTTPException(status_code=404, detail="Replay not found")
    return replay
