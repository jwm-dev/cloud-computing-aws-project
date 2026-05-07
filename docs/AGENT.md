# FINAL IMPLEMENTATION PROMPT — HIDDEN AGENDA RL SYSTEM

You are tasked with building a **complete, correct, minimal, end-to-end system** for the Hidden Agenda environment as specified below.

This is a **strict engineering execution task**.
No deviations, no feature creep, no interpretation beyond what is specified.

---

# 0. OBJECTIVE

Produce a fully working system that:

1. Implements **Hidden Agenda exactly as defined**
2. Exposes it as a **Gym-compatible multi-agent RL environment**
3. Supports **deterministic replay**
4. Can **run large batches of games and store them**
5. Provides:

   * API
   * dataset browser
   * live + replay viewer
6. Deploys on **single EC2 + S3 only**

---

# 1. CORE CONSTANTS (DO NOT MODIFY)

```
N_PLAYERS = 5
N_IMPOSTORS = 1
N_CREWMATES = 4

GRID_WIDTH = 40
GRID_HEIGHT = 31

MAX_STEPS = 3000
VOTING_INTERVAL = 200
VOTING_DURATION = 25

INVENTORY_CAPACITY = 2
FUEL_REQUIRED = 40

FREEZE_COOLDOWN = 50
FREEZE_RANGE_FORWARD = 2
FREEZE_WIDTH = 1
```

---

# 2. ENVIRONMENT IMPLEMENTATION

## 2.1 Class Definition

```
class HiddenAgendaEnv(gym.Env):
```

Must support:

```
reset() -> observations
step(actions) -> (observations, rewards, done, info)
```

Multi-agent format:

```
Dict[player_id -> observation]
Dict[player_id -> action]
Dict[player_id -> reward]
done: bool
```

---

## 2.2 STATE STRUCTURES (EXACT)

### GameState

```
GameState:
    players: List[Player]
    grid: Grid
    fuel_progress: int
    phase: {SITUATION, VOTING}
    step_count: int
    voting_timer: int
    last_vote_matrix: (5 x 7)
```

---

### Player

```
Player:
    id: int
    role: {CREWMATE, IMPOSTOR}
    position: (x, y)
    orientation: {N, S, E, W}
    inventory: int
    active: bool
    freeze_cooldown: int
```

---

### Grid

```
Cell:
    type: {EMPTY, WALL, FUEL, DEPOSIT, VOTING_ROOM}

Grid:
    cells[40][31]
```

---

# 3. OBSERVATION FUNCTION (NO LEAKAGE)

Each agent receives:

```
Observation:
    rgb_view: (88, 88, 3)
    inventory_ratio: float
    global_progress: float
    vote_matrix: (5 x 7)
```

### FOV RULES

```
11 x 11 centered view:
    left/right: 5
    forward: 9
    backward: 1
```

NO role information must be observable.

---

# 4. ACTION SPACE

## Situation Phase

```
0: move_forward
1: move_backward
2: move_left
3: move_right
4: rotate_left
5: rotate_right
6: interact
7: freeze (impostor only)
```

---

## Voting Phase

```
0–4: vote player_i
5: abstain
```

Inactive players → no-op only

---

# 5. TRANSITION LOGIC (STRICT ORDER)

```
step(actions):
    if phase == SITUATION:
        process_movement()
        process_interactions()
        process_freeze()
        update_cooldowns()
        check_vote_trigger()

    elif phase == VOTING:
        update_votes()
        voting_timer += 1
        if voting_timer == VOTING_DURATION:
            resolve_votes()
            switch_to_situation()

    step_count += 1
    check_terminal()
```

---

# 6. GAME MECHANICS

## Movement

* No wall penetration
* Discrete grid occupancy

---

## Fuel System

```
Pickup:
    if FUEL and inventory < capacity:
        inventory += 1

Deposit:
    if DEPOSIT:
        fuel_progress += inventory
        inventory = 0
```

---

## Freeze (Impostor Only)

```
If cooldown == 0:
    freeze all crewmates in beam
    cooldown = FREEZE_COOLDOWN
```

Beam:

```
depth = 2
width = ±1
forward direction only
```

---

## Voting Trigger

Trigger if:

```
- freeze observed
OR
- steps_since_last_vote >= VOTING_INTERVAL
```

---

## Voting Phase

```
- teleport all players to voting room
- votes updated each timestep
- visible with 1-step delay
```

Vote matrix:

```
[5 x 7]:
    0–4: vote targets
    5: abstain
    6: inactive
```

---

## Vote Resolution

```
if any player >= 50% of active votes:
    player.active = False
```

---

# 7. REWARDS

## Terminal

```
Crewmate win: +4
Crewmate loss: -4
Impostor win: +4
Impostor loss: -4
```

---

## Shaping

```
Crewmate:
    +0.25 pickup
    +0.25 deposit
    -1 frozen

Impostor:
    +1 freeze success
```

---

# 8. TERMINATION

```
if fuel_progress >= FUEL_REQUIRED:
    CREWMATES WIN

if impostor eliminated:
    CREWMATES WIN

if active_crewmates <= 1:
    IMPOSTOR WIN

if step_count >= MAX_STEPS:
    DRAW
```

---

# 9. DETERMINISM + REPLAY (MANDATORY)

## Requirements

* Single RNG seed controls:

  * map generation
  * agent ordering
  * all stochasticity

* Every step logged

---

## Log Schema

```
{
  "seed": int,
  "config": {...},
  "steps": [
    {
      "phase": "...",
      "actions": {...},
      "state_hash": "..."
    }
  ],
  "outcome": {...}
}
```

Replay must reproduce identical trajectory.

---

# 10. GAME RUNNER

Implement:

```
run_batch(config, num_games) -> dataset_path
```

Must:

* run parallel games
* write JSONL or Parquet
* upload to S3

---

# 11. API (FASTAPI)

Endpoints:

```
POST /run
GET  /games
GET  /games/{id}
GET  /games/{id}/replay
GET  /live/{game_id}
```

---

# 12. DASHBOARD

Minimal UI:

* list games
* filter by:

  * seed
  * outcome
* inspect game

---

# 13. VIEWER

## Replay Mode

* step-by-step playback
* show grid, players, votes

## Live Mode

* websocket stream
* real-time state updates

---

# 14. AWS DEPLOYMENT (STRICT LIMIT)

Architecture:

```
EC2 (single instance):
    API
    runner
    dashboard
    viewer

S3:
    dataset storage
```

NO:

* load balancers
* custom networking
* distributed services

---

## Deployment Steps

1. Launch EC2 (Ubuntu)
2. Install Docker
3. Run single container exposing port 8000
4. Configure S3 via boto3

---

# 15. BASELINE AGENTS

Implement:

### RandomAgent

* uniform random

### HeuristicAgent

* simple proximity + naive voting

---

# 16. TRAINING (MINIMAL)

```
1 impostor agent
4 crewmate agents
fixed roles across episodes
```

Loop:

```
reset()
while not done:
    actions = policy(obs)
    step(actions)
```

---

# 17. NETWORK (REFERENCE)

```
RGB → CNN
+ scalars
+ vote matrix

→ MLP → LSTM →

outputs:
    policy logits
    value
```

---

# 18. VALIDATION TARGETS

System is correct if:

* replay is bit-exact
* agents exhibit:

  * clustering (crew)
  * isolation (impostor)
  * vote convergence
* multiple equilibria emerge across runs

---

# 19. IMPLEMENTATION ORDER (ENFORCE)

1. Grid + movement
2. Fuel system
3. Freeze
4. Voting
5. Rewards + termination
6. Observations
7. Gym wrapper
8. Runner
9. API
10. UI + viewer
11. AWS deploy

---

# 20. FAILURE CONDITIONS

Do NOT:

* leak roles in observations
* allow nondeterminism
* overengineer infrastructure
* deviate from constants
* mix phases incorrectly

---

# FINAL REQUIREMENT

Output:

1. Full repository tree
2. Fully implemented:

   * env
   * runner
   * api
3. Dockerfile
4. Exact deployment commands

No placeholders. No stubs. Fully runnable.
