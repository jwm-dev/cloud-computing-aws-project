import os
import json
from datetime import datetime, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from .env import HiddenAgendaEnv
from .agents import RandomAgent
import boto3

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

os.makedirs(DATA_DIR, exist_ok=True)


def _run_single(seed, config=None, game_id=None):
    env = HiddenAgendaEnv(seed=seed, config=config)
    agents = [RandomAgent() for _ in range(5)]
    obs = env.reset()
    done = False
    steps=0
    while not done and steps < 10000:
        actions = {}
        for i in range(5):
            actions[i] = agents[i].act(obs[i])
        obs, rewards, done, info = env.step(actions)
        steps+=1
    # save replay
    game_id = game_id or uuid4().hex
    out = os.path.join(DATA_DIR, f'game_{game_id}.json')
    env.save_replay(out)
    return {
        'game_id': game_id,
        'seed': int(seed),
        'path': out,
        'steps': len(env.log.get('steps', [])),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'config': config or {},
    }


def run_batch(config, num_games=1, seeds=None, upload_s3=None):
    seeds = seeds or [int(config.get('seed',0))+i for i in range(num_games)]
    records=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(_run_single, s, config, uuid4().hex) for s in seeds]
        for f in futures:
            records.append(f.result())
    # write index
    index = os.path.join(DATA_DIR, 'index.jsonl')
    with open(index,'a') as idx:
        for record in records:
            idx.write(json.dumps(record)+"\n")
    if upload_s3:
        s3 = boto3.client('s3')
        bucket = upload_s3['bucket']
        prefix = upload_s3.get('prefix','')
        for record in records:
            key = os.path.join(prefix, os.path.basename(record['path']))
            s3.upload_file(record['path'], bucket, key)
    return records
