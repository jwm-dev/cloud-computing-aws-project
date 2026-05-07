import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict
import numpy as np
import gym
from gym import spaces
from .constants import *
from .renderer import render_rgb_from_grid, EMPTY, FUEL, DEPOSIT, VOTING_ROOM


@dataclass
class Player:
    id: int
    role: str
    position: Tuple[int, int]
    orientation: str
    inventory: int = 0
    active: bool = True
    freeze_cooldown: int = 0


class HiddenAgendaEnv(gym.Env):
    metadata = {"render.modes": ["rgb_array"]}

    def __init__(self, seed: int = 0, config: Dict = None):
        self.config = config or {}
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._make_spaces()
        self.reset()

    def _make_spaces(self):
        # action space: dict players -> discrete
        self.action_space = spaces.Dict({str(i): spaces.Discrete(8) for i in range(N_PLAYERS)})
        # observation space per player
        self.observation_space = spaces.Dict({
            'rgb_view': spaces.Box(low=0, high=255, shape=OBS_RGB, dtype=np.uint8),
            'inventory_ratio': spaces.Box(low=0.0, high=1.0, shape=()),
            'global_progress': spaces.Box(low=0.0, high=1.0, shape=()),
            'vote_matrix': spaces.Box(low=0, high=6, shape=(N_PLAYERS,7), dtype=np.int8)
        })

    def reset(self):
        # deterministic map generation
        self.grid = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=np.int8)  # 0 empty
        # place walls deterministically (simple pattern)
        for x in range(0, GRID_WIDTH, 10):
            for y in range(GRID_HEIGHT):
                self.grid[x, y] = -1
        # place fuel and deposit deterministically from rng
        for i in range(60):
            x = int(self.rng.integers(0, GRID_WIDTH))
            y = int(self.rng.integers(0, GRID_HEIGHT))
            self.grid[x, y] = FUEL if (i % 5 != 0) else DEPOSIT
        # voting room region mark as VOTING_ROOM in corner
        self.grid[0:3, 0:3] = VOTING_ROOM

        # players
        self.players: List[Player] = []
        ids = list(range(N_PLAYERS))
        self.rng.shuffle(ids)
        impostor_ids = set(ids[:N_IMPOSTORS])
        for i in range(N_PLAYERS):
            role = 'IMPOSTOR' if i in impostor_ids else 'CREWMATE'
            # place players avoiding walls
            while True:
                pos = (int(self.rng.integers(0, GRID_WIDTH)), int(self.rng.integers(0, GRID_HEIGHT)))
                if self.grid[pos[0], pos[1]] != -1:
                    break
            orientation = self.rng.choice(['N', 'S', 'E', 'W'])
            self.players.append(Player(i, role, pos, orientation))
        self.fuel_progress = 0
        self.phase = 'SITUATION'
        self.step_count = 0
        self.voting_timer = 0
        self.last_vote_matrix = np.zeros((N_PLAYERS, 7), dtype=np.int8)
        self.last_vote_matrix[:, 6] = 6  # inactive flag default
        # vote visibility delay buffer: observations see previous step's matrix (1-step delay)
        self._vote_observation_buffer = self.last_vote_matrix.copy()
        self.log = {
            'seed': int(self.seed),
            'config': self.config,
            'steps': []
        }
        return self._observations()

    def _state_hash(self):
        s = json.dumps({
            'players': [asdict(p) for p in self.players],
            'grid': self.grid.tolist(),
            'fuel_progress': int(self.fuel_progress),
            'phase': self.phase,
            'step_count': int(self.step_count)
        }, sort_keys=True).encode('utf-8')
        return hashlib.sha256(s).hexdigest()

    def _observations(self):
        obs = {}
        for i, p in enumerate(self.players):
            rgb = render_rgb_from_grid(self.grid, [asdict(pl) for pl in self.players], i)
            inv_ratio = p.inventory / INVENTORY_CAPACITY
            global_progress = self.fuel_progress / FUEL_REQUIRED
            # vote matrix visible with 1-step delay
            obs[i] = {
                'rgb_view': rgb,
                'inventory_ratio': float(inv_ratio),
                'global_progress': float(global_progress),
                'vote_matrix': self._vote_observation_buffer.copy()
            }
        return obs

    def step(self, actions: Dict[int,int]):
        # actions: dict player_id->action
        if self.phase == 'SITUATION':
            self._process_movement(actions)
            self._process_interactions(actions)
            self._process_freeze(actions)
            self._update_cooldowns()
            self._check_vote_trigger(actions)
        elif self.phase == 'VOTING':
            self._update_votes(actions)
            self.voting_timer += 1
            if self.voting_timer >= VOTING_DURATION:
                self._resolve_votes()
                self._switch_to_situation()
        self.step_count += 1
        done, outcome = self._check_terminal()
        # log step
        self.log['steps'].append({
            'phase': self.phase,
            'actions': {str(k): int(v) for k, v in actions.items()},
            'state_hash': self._state_hash()
        })
        # update vote observation buffer (1-step delay): buffer shows last_vote_matrix from previous timestep
        self._vote_observation_buffer = self.last_vote_matrix.copy()
        obs = self._observations()
        rewards = self._compute_rewards()
        info = {'outcome': outcome}
        return obs, rewards, done, info

    def _process_movement(self, actions):
        for pid in range(N_PLAYERS):
            if not self.players[pid].active:
                continue
            a = actions.get(pid,0)
            if a in (0,1,2,3):
                dx,dy = 0,0
                ori = self.players[pid].orientation
                if a==0:  # forward
                    if ori=='N': dy=-1
                    if ori=='S': dy=1
                    if ori=='E': dx=1
                    if ori=='W': dx=-1
                elif a==1:  # backward
                    if ori=='N': dy=1
                    if ori=='S': dy=-1
                    if ori=='E': dx=-1
                    if ori=='W': dx=1
                elif a==2:  # left
                    if ori=='N': dx=-1
                    if ori=='S': dx=1
                    if ori=='E': dy=-1
                    if ori=='W': dy=1
                elif a==3:  # right
                    if ori=='N': dx=1
                    if ori=='S': dx=-1
                    if ori=='E': dy=1
                    if ori=='W': dy=-1
                nx = max(0, min(GRID_WIDTH-1, self.players[pid].position[0]+dx))
                ny = max(0, min(GRID_HEIGHT-1, self.players[pid].position[1]+dy))
                if self.grid[nx,ny] != -1:  # not a wall (we use -1 for wall)
                    # ensure no other active player occupies
                    if not any((pl.active and pl.position==(nx,ny)) for pl in self.players):
                        self.players[pid].position = (nx,ny)
            elif a==4:
                # rotate left
                self.players[pid].orientation = self._rot_left(self.players[pid].orientation)
            elif a==5:
                self.players[pid].orientation = self._rot_right(self.players[pid].orientation)

    def _rot_left(self, ori):
        order = ['N','W','S','E']
        return order[(order.index(ori)+1)%4]

    def _rot_right(self, ori):
        order = ['N','E','S','W']
        return order[(order.index(ori)+1)%4]

    def _process_interactions(self, actions):
        for pid, a in actions.items():
            pid = int(pid)
            pl = self.players[pid]
            if not pl.active:
                continue
            if a == 6:  # interact
                x, y = pl.position
                cell = self.grid[x, y]
                if cell == FUEL and pl.inventory < INVENTORY_CAPACITY:
                    pl.inventory += 1
                    # shaping reward logged later
                elif cell == DEPOSIT and pl.inventory > 0:
                    self.fuel_progress += pl.inventory
                    pl.inventory = 0

    def _process_freeze(self, actions):
        for pid, a in actions.items():
            pid = int(pid)
            pl = self.players[pid]
            if a == 7 and pl.role == 'IMPOSTOR' and pl.freeze_cooldown == 0:
                ox, oy = pl.position
                ori = pl.orientation
                frozen = 0
                for d in range(1, FREEZE_RANGE_FORWARD + 1):
                    for w in range(-FREEZE_WIDTH, FREEZE_WIDTH + 1):
                        tx, ty = ox, oy
                        if ori == 'N':
                            tx += w; ty -= d
                        if ori == 'S':
                            tx += w; ty += d
                        if ori == 'E':
                            tx += d; ty += w
                        if ori == 'W':
                            tx -= d; ty += w
                        if 0 <= tx < GRID_WIDTH and 0 <= ty < GRID_HEIGHT:
                            for other in self.players:
                                if other.role == 'CREWMATE' and other.active and other.position == (tx, ty):
                                    other.active = False
                                    frozen += 1
                if frozen > 0:
                    pl.freeze_cooldown = FREEZE_COOLDOWN
                    # reward shaping applied later

    def _update_cooldowns(self):
        for pl in self.players:
            if pl.freeze_cooldown > 0:
                pl.freeze_cooldown -= 1

    def _check_vote_trigger(self, actions):
        # if any freeze observed? we check actions for freeze
        if any(int(a)==7 for a in actions.values()):
            self._start_voting()
            return
        if (self.step_count - getattr(self,'last_vote_step',0)) >= VOTING_INTERVAL:
            self._start_voting()

    def _start_voting(self):
        self.phase = 'VOTING'
        self.voting_timer = 0
        # teleport players to voting room deterministic positions
        for i, pl in enumerate(self.players):
            pl.position = (i % 3, i // 3)
        # reset vote matrix to show inactive as 6 for simplicity
        self.last_vote_matrix = np.zeros((N_PLAYERS,7), dtype=np.int8)
        self.last_vote_matrix[:,6]=6
        self.last_vote_step = self.step_count

    def _update_votes(self, actions):
        # actions keys are ints or strings
        for pid,a in actions.items():
            pid=int(pid)
            if not self.players[pid].active:
                self.last_vote_matrix[pid, :] = 0
                self.last_vote_matrix[pid, 6] = 6
                continue
            choice = int(a)
            self.last_vote_matrix[pid, :] = 0
            if 0 <= choice < 5:
                self.last_vote_matrix[pid, choice] = 1
            elif choice == 5:
                self.last_vote_matrix[pid, 5] = 1

    def _resolve_votes(self):
        # count active votes excluding abstain
        counts = np.sum(self.last_vote_matrix[:, :5], axis=0)
        # active votes are sum of non-zero votes excluding abstain
        active_votes = int(np.sum(self.last_vote_matrix[:, :6])) - int(np.sum(self.last_vote_matrix[:, 5]))
        if active_votes<=0:
            return
        for pid,count in enumerate(counts):
            if count >= 0.5 * active_votes:
                # eliminate player
                self.players[pid].active = False
                break

    def _switch_to_situation(self):
        self.phase='SITUATION'
        self.voting_timer=0

    def _check_terminal(self):
        # terminal conditions
        # impostor eliminated?
        impostors = [p for p in self.players if p.role == 'IMPOSTOR' and p.active]
        crewmates = [p for p in self.players if p.role == 'CREWMATE' and p.active]
        if self.fuel_progress >= FUEL_REQUIRED:
            return True, {'winner':'CREWMATES'}
        if len(impostors)==0:
            return True, {'winner':'CREWMATES'}
        if len(crewmates) <= 1:
            return True, {'winner':'IMPOSTOR'}
        if self.step_count >= MAX_STEPS:
            return True, {'winner':'DRAW'}
        return False, {}

    def _compute_rewards(self):
        # shaping and terminal rewards
        rewards = {i: 0.0 for i in range(N_PLAYERS)}
        # shaping: pickups/deposits/freeze/frozen
        # detect pickups/deposits by comparing last log step? For simplicity, we give shaping zero here and rely on event recording.
        # Terminal outcome rewards
        done, outcome = self._check_terminal()
        if done:
            winner = outcome.get('winner')
            if winner == 'CREWMATES':
                for i, p in enumerate(self.players):
                    rewards[i] = 4.0 if p.role == 'CREWMATE' else -4.0
            elif winner == 'IMPOSTOR':
                for i, p in enumerate(self.players):
                    rewards[i] = 4.0 if p.role == 'IMPOSTOR' else -4.0
            else:
                for i in rewards:
                    rewards[i] = 0.0
        return rewards

    def save_replay(self, path):
        with open(path,'w') as f:
            json.dump(self.log, f, indent=2)
