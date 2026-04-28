"""
Analytics endpoints – aggregate metrics for experiments.

Endpoints
---------
GET /analytics/{experiment_id}          All per-episode metrics
GET /analytics/{experiment_id}/summary  Aggregated summary statistics
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.storage import s3_client

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{experiment_id}", response_model=List[Dict])
def get_analytics(experiment_id: str):
    """Return raw per-episode metric objects stored in S3."""
    try:
        data = s3_client.get_analytics(experiment_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 error: {exc}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="No analytics found for this experiment")
    return data


@router.get("/{experiment_id}/summary", response_model=Dict[str, Any])
def get_summary(experiment_id: str):
    """Return aggregated statistics across all episodes of an experiment."""
    try:
        data = s3_client.get_analytics(experiment_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 error: {exc}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="No analytics found for this experiment")

    n = len(data)
    winner_counts: Dict[str, int] = {}
    total_steps = 0
    total_fuel = 0.0

    for ep in data:
        winner = ep.get("winner") or "draw"
        winner_counts[winner] = winner_counts.get(winner, 0) + 1
        total_steps += ep.get("steps", 0)
        total_fuel += ep.get("fuel_deposited", 0)

    return {
        "experiment_id": experiment_id,
        "episodes": n,
        "winner_distribution": {k: v / n for k, v in winner_counts.items()},
        "avg_steps_per_episode": total_steps / n,
        "avg_fuel_deposited": total_fuel / n,
    }
