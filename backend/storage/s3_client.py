"""
AWS S3 client wrapper for storing experiment data and replays.
"""

import json
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "hidden-agenda-rl-gym")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _get_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


# ---------------------------------------------------------------------------
# Replay storage
# ---------------------------------------------------------------------------

def put_replay(experiment_id: str, episode_id: str, frames: List[Dict]) -> str:
    """
    Persist a replay (list of serialized environment states) to S3.

    Returns the S3 key.
    """
    key = f"replays/{experiment_id}/{episode_id}.json"
    body = json.dumps({"experiment_id": experiment_id, "episode_id": episode_id, "frames": frames})
    _get_client().put_object(Bucket=BUCKET_NAME, Key=key, Body=body, ContentType="application/json")
    return key


def get_replay(experiment_id: str, episode_id: str) -> Optional[Dict]:
    """Retrieve a stored replay. Returns None if not found."""
    key = f"replays/{experiment_id}/{episode_id}.json"
    try:
        response = _get_client().get_object(Bucket=BUCKET_NAME, Key=key)
        return json.loads(response["Body"].read())
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def list_replays(experiment_id: str) -> List[str]:
    """List all episode IDs stored for a given experiment."""
    prefix = f"replays/{experiment_id}/"
    paginator = _get_client().get_paginator("list_objects_v2")
    episodes = []
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            episode_id = key[len(prefix):].removesuffix(".json")
            episodes.append(episode_id)
    return episodes


# ---------------------------------------------------------------------------
# Experiment metadata storage
# ---------------------------------------------------------------------------

def put_experiment(experiment_id: str, metadata: Dict) -> str:
    key = f"experiments/{experiment_id}/metadata.json"
    _get_client().put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(metadata),
        ContentType="application/json",
    )
    return key


def get_experiment(experiment_id: str) -> Optional[Dict]:
    key = f"experiments/{experiment_id}/metadata.json"
    try:
        response = _get_client().get_object(Bucket=BUCKET_NAME, Key=key)
        return json.loads(response["Body"].read())
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def list_experiments() -> List[Dict]:
    prefix = "experiments/"
    paginator = _get_client().get_paginator("list_objects_v2")
    experiments = []
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            experiment_id = cp["Prefix"][len(prefix):].rstrip("/")
            experiments.append({"experiment_id": experiment_id})
    return experiments


# ---------------------------------------------------------------------------
# Analytics storage
# ---------------------------------------------------------------------------

def put_analytics(experiment_id: str, episode_id: str, metrics: Dict) -> str:
    key = f"analytics/{experiment_id}/{episode_id}.json"
    _get_client().put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(metrics),
        ContentType="application/json",
    )
    return key


def get_analytics(experiment_id: str) -> List[Dict]:
    prefix = f"analytics/{experiment_id}/"
    paginator = _get_client().get_paginator("list_objects_v2")
    results = []
    client = _get_client()
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            response = client.get_object(Bucket=BUCKET_NAME, Key=obj["Key"])
            results.append(json.loads(response["Body"].read()))
    return results
