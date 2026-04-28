"""
Experiment dispatch and status endpoints.

Endpoints
---------
POST   /experiments           Launch a new experiment
GET    /experiments            List all experiments
GET    /experiments/{id}       Get experiment metadata & status
DELETE /experiments/{id}       Cancel / remove an experiment
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.environment.hidden_agenda import HiddenAgendaEnv
from backend.storage import s3_client

router = APIRouter(prefix="/experiments", tags=["experiments"])

# In-memory registry of active experiments (resets on server restart).
# Persistent metadata is written to S3.
_active: Dict[str, Dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExperimentConfig(BaseModel):
    n_players: int = 5
    n_impostors: int = 1
    n_episodes: int = 1
    random_policy: bool = True   # use random actions (placeholder for real RL agents)
    description: Optional[str] = None


class ExperimentOut(BaseModel):
    experiment_id: str
    status: str
    config: Dict
    created_at: str
    episodes_completed: int
    episodes_total: int
    description: Optional[str]


# ---------------------------------------------------------------------------
# Background task: run episodes
# ---------------------------------------------------------------------------

def _run_experiment(experiment_id: str, config: ExperimentConfig):
    record = _active[experiment_id]
    record["status"] = "running"

    env = HiddenAgendaEnv(n_players=config.n_players, n_impostors=config.n_impostors)

    for ep_idx in range(config.n_episodes):
        obs, info = env.reset()
        episode_id = info["episode_id"]
        frames = [env.serialize_state()]
        total_rewards = [0.0] * config.n_players

        terminated = False
        truncated = False
        step = 0

        while not (terminated or truncated):
            # Random policy (placeholder)
            actions = [env.state.phase.value * 0] * config.n_players  # NOOP baseline
            if config.random_policy:
                import random
                actions = [random.randint(0, 13) for _ in range(config.n_players)]

            obs, rewards, terminated, truncated, info = env.step(actions)
            for i, r in enumerate(rewards):
                total_rewards[i] += r
            frames.append(env.serialize_state())
            step += 1

        metrics = {
            "episode_id": episode_id,
            "experiment_id": experiment_id,
            "steps": step,
            "winner": info.get("winner"),
            "fuel_deposited": info.get("fuel_deposited"),
            "total_rewards": total_rewards,
        }

        try:
            s3_client.put_replay(experiment_id, episode_id, frames)
            s3_client.put_analytics(experiment_id, episode_id, metrics)
        except Exception:
            pass  # S3 may not be configured in dev

        record["episodes_completed"] += 1

    record["status"] = "completed"
    try:
        s3_client.put_experiment(experiment_id, record)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=ExperimentOut, status_code=201)
def create_experiment(config: ExperimentConfig, background_tasks: BackgroundTasks):
    experiment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "experiment_id": experiment_id,
        "status": "queued",
        "config": config.model_dump(),
        "created_at": now,
        "episodes_completed": 0,
        "episodes_total": config.n_episodes,
        "description": config.description,
    }
    _active[experiment_id] = record
    background_tasks.add_task(_run_experiment, experiment_id, config)
    return record


@router.get("", response_model=List[ExperimentOut])
def list_experiments():
    return list(_active.values())


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment(experiment_id: str):
    if experiment_id not in _active:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _active[experiment_id]


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str):
    if experiment_id not in _active:
        raise HTTPException(status_code=404, detail="Experiment not found")
    del _active[experiment_id]
