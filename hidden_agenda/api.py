import os
import json
from fastapi import FastAPI, BackgroundTasks, WebSocket, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from .env import HiddenAgendaEnv
from .runner import run_batch, DATA_DIR

app = FastAPI()

# mount static dashboard
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/favicon.ico')
def favicon():
    return Response(status_code=204)


def _static_page(filename: str):
    path = os.path.join(static_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='page not found')
    return FileResponse(path, media_type='text/html')


def _game_path(game_id: str):
    return os.path.join(DATA_DIR, f'game_{game_id}.json')


def _read_index_entries():
    index_path = os.path.join(DATA_DIR, 'index.jsonl')
    if not os.path.exists(index_path):
        return []
    entries = []
    with open(index_path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
    return entries


def _derive_game_id(entry):
    if isinstance(entry, dict):
        if entry.get('game_id'):
            return entry['game_id']
        path = entry.get('path', '')
        base = os.path.basename(path)
        if base.startswith('game_') and base.endswith('.json'):
            return base[5:-5]
    return None


def _load_game_record(game_id: str):
    path = _game_path(game_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='not found')
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    data['game_id'] = game_id
    data['replay_url'] = f'/games/{game_id}/replay'
    data['viewer_url'] = f'/viewer/{game_id}'
    data['snapshot_url'] = f'/games/{game_id}/frame/0'
    data['step_count'] = len(data.get('steps', []))
    return data


def _snapshot_for_frame(game_id: str, frame_index: int):
    record = _load_game_record(game_id)
    steps = record.get('steps', [])
    env = HiddenAgendaEnv(seed=int(record.get('seed', 0)), config=record.get('config') or {})
    env.reset()
    frame_index = max(0, min(frame_index, len(steps)))
    for step in steps[:frame_index]:
        actions = {int(pid): int(action) for pid, action in step.get('actions', {}).items()}
        env.step(actions)
    done, outcome = env._check_terminal()
    return {
        'game_id': game_id,
        'frame_index': frame_index,
        'total_frames': len(steps),
        'seed': int(record.get('seed', 0)),
        'config': record.get('config') or {},
        'terminal': bool(done),
        'outcome': outcome,
        'phase': env.phase,
        'step_count': env.step_count,
        'fuel_progress': env.fuel_progress,
        'voting_timer': env.voting_timer,
        'grid': env.grid.tolist(),
        'players': [
            {
                'id': player.id,
                'role': player.role,
                'position': list(player.position),
                'orientation': player.orientation,
                'inventory': player.inventory,
                'active': player.active,
                'freeze_cooldown': player.freeze_cooldown,
            }
            for player in env.players
        ],
        'last_vote_matrix': env.last_vote_matrix.tolist(),
        'actions': steps[frame_index - 1].get('actions', {}) if frame_index > 0 and steps else {},
        'state_hash': steps[frame_index - 1].get('state_hash') if frame_index > 0 and steps else None,
    }


@app.get('/')
def landing_page():
    return _static_page('landing.html')


@app.get('/dashboard')
def dashboard_page():
    return _static_page('dashboard.html')


@app.get('/viewer/{game_id}')
def viewer_page(game_id: str):
    return _static_page('viewer.html')

@app.post('/run')
def run_endpoint(payload: dict, background_tasks: BackgroundTasks):
    num_games = int(payload.get('num_games',1))
    config = payload.get('config',{})
    upload = payload.get('upload_s3')
    background_tasks.add_task(run_batch, config, num_games, None, upload)
    return {"status":"running","num_games":num_games,"dashboard_url":"/dashboard"}

@app.get('/games')
def list_games():
    entries = []
    for entry in _read_index_entries():
        game_id = _derive_game_id(entry)
        if not game_id:
            continue
        path = entry.get('path') if isinstance(entry, dict) else None
        if not path:
            path = _game_path(game_id)
        if not os.path.exists(path):
            continue
        entries.append({
            'game_id': game_id,
            'seed': entry.get('seed') if isinstance(entry, dict) else None,
            'config': entry.get('config') if isinstance(entry, dict) else {},
            'path': path,
            'steps': entry.get('steps') if isinstance(entry, dict) else None,
            'created_at': entry.get('created_at') if isinstance(entry, dict) else None,
            'replay_url': f'/games/{game_id}/replay',
            'viewer_url': f'/viewer/{game_id}',
        })
    entries.sort(key=lambda item: item.get('created_at') or '', reverse=True)
    return entries

@app.get('/games/{game_id}')
def get_game(game_id: str):
    return JSONResponse(_load_game_record(game_id))

@app.get('/games/{game_id}/replay')
def get_replay(game_id: str):
    return get_game(game_id)


@app.get('/games/{game_id}/frame/{frame_index}')
def get_game_frame(game_id: str, frame_index: int):
    return JSONResponse(_snapshot_for_frame(game_id, frame_index))

@app.get('/live/{game_id}')
def live_page(game_id: str):
    return RedirectResponse(url=f'/viewer/{game_id}', status_code=307)

@app.websocket('/ws/{game_id}')
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    try:
        data = _load_game_record(game_id)
    except HTTPException:
        await websocket.send_text('not found')
        await websocket.close()
        return
    for step in data.get('steps',[]):
        await websocket.send_text(json.dumps(step))
    await websocket.close()
