"""
Hidden Agenda gym environment.

Hidden Agenda is a 5-player social deduction game:
  - 4 Crewmates: collect fuel cells, deposit them at the center, vote out the Impostor.
  - 1 Impostor: freeze Crewmates with a beam; prevent fuel collection.

The environment exposes an OpenAI Gym-compatible interface.
"""

import random
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAP_WIDTH = 40
MAP_HEIGHT = 31
INVENTORY_CAPACITY = 2
SITUATION_PHASE_TICKS = 200
VOTING_PHASE_TICKS = 25
MAX_EPISODE_TICKS = 3000
FREEZE_BEAM_RANGE = 3
FUEL_GOAL = 10          # total fuel cells needed for Crewmates to win
FUEL_CELLS_ON_MAP = 12  # initial fuel cells scattered on the map
N_PLAYERS = 5
N_IMPOSTORS = 1
N_CREWMATES = N_PLAYERS - N_IMPOSTORS


class Phase(IntEnum):
    SITUATION = 0
    VOTING = 1


class Role(IntEnum):
    CREWMATE = 0
    IMPOSTOR = 1


class WinCondition(str):
    NONE = "none"
    CREWMATES_FUEL = "crewmates_fuel"
    CREWMATES_VOTE = "crewmates_vote"
    IMPOSTOR = "impostor"
    DRAW = "draw"


# ---------------------------------------------------------------------------
# Action encoding
# ---------------------------------------------------------------------------

class Action(IntEnum):
    NOOP = 0
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    PICK_UP = 5
    DEPOSIT = 6
    FREEZE = 7      # Impostor only; no-op for Crewmates
    VOTE_0 = 8      # vote for player index 0
    VOTE_1 = 9
    VOTE_2 = 10
    VOTE_3 = 11
    VOTE_4 = 12
    ABSTAIN = 13    # voting-phase abstain


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Position:
    x: int
    y: int

    def manhattan(self, other: "Position") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


@dataclass
class PlayerState:
    player_id: int
    role: Role
    position: Position
    inventory: int = 0          # number of fuel cells carried
    active: bool = True         # False if frozen or voted out
    frozen: bool = False
    voted_out: bool = False
    vote_target: Optional[int] = None   # index of player voted for this phase


@dataclass
class EnvironmentState:
    phase: Phase = Phase.SITUATION
    tick: int = 0
    phase_tick: int = 0
    fuel_deposited: int = 0
    fuel_cells: List[Position] = field(default_factory=list)
    players: List[PlayerState] = field(default_factory=list)
    winner: Optional[str] = None
    done: bool = False
    last_freeze_witnessed: bool = False  # did an active Crewmate witness a freeze?


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class HiddenAgendaEnv:
    """
    Minimal Hidden Agenda environment compatible with the gym step/reset API.

    Observations are returned as plain Python dicts (no NumPy dependency required).
    Actions are integers from the Action enum.
    """

    metadata: Dict[str, Any] = {"render_modes": ["human", "json"]}

    def __init__(self, n_players: int = N_PLAYERS, n_impostors: int = N_IMPOSTORS):
        assert n_players > n_impostors >= 1
        self.n_players = n_players
        self.n_impostors = n_impostors
        self.n_crewmates = n_players - n_impostors
        self.state: Optional[EnvironmentState] = None
        self.episode_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self) -> Tuple[List[Dict], Dict]:
        """Reset the environment and return initial observations."""
        self.episode_id = str(uuid.uuid4())
        state = EnvironmentState()
        state.fuel_cells = self._scatter_fuel_cells()

        roles = [Role.IMPOSTOR] * self.n_impostors + [Role.CREWMATE] * self.n_crewmates
        random.shuffle(roles)

        state.players = [
            PlayerState(
                player_id=i,
                role=roles[i],
                position=self._random_center_position(),
            )
            for i in range(self.n_players)
        ]

        self.state = state
        obs = self._get_observations()
        info = {"episode_id": self.episode_id, "phase": state.phase.name}
        return obs, info

    def step(
        self, actions: List[int]
    ) -> Tuple[List[Dict], List[float], bool, bool, Dict]:
        """
        Apply one action per player.

        Returns:
            observations, rewards, terminated, truncated, info
        """
        if self.state is None:
            raise RuntimeError("Call reset() before step().")

        state = self.state
        if state.done:
            raise RuntimeError("Episode is finished; call reset().")

        rewards = [0.0] * self.n_players

        if state.phase == Phase.SITUATION:
            rewards = self._process_situation_step(actions)
        else:
            rewards = self._process_voting_step(actions)

        state.tick += 1
        state.phase_tick += 1

        self._check_win_conditions()
        self._maybe_transition_phase()

        obs = self._get_observations()
        terminated = state.done
        truncated = False
        info = {
            "phase": state.phase.name,
            "tick": state.tick,
            "fuel_deposited": state.fuel_deposited,
            "winner": state.winner,
            "episode_id": self.episode_id,
        }
        return obs, rewards, terminated, truncated, info

    def render(self, mode: str = "json") -> Any:
        if self.state is None:
            return None
        if mode == "json":
            return self._serialize_state()
        if mode == "human":
            print(self._ascii_map())
        return None

    def serialize_state(self) -> Dict:
        return self._serialize_state()

    # ------------------------------------------------------------------
    # Private helpers – situation phase
    # ------------------------------------------------------------------

    def _process_situation_step(self, actions: List[int]) -> List[float]:
        state = self.state
        rewards = [0.0] * self.n_players
        freeze_event: Optional[Tuple[int, int]] = None  # (attacker_id, victim_id)

        for i, player in enumerate(state.players):
            if not player.active:
                continue
            action = Action(actions[i])

            if action in (Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT):
                self._move_player(player, action)

            elif action == Action.PICK_UP:
                if player.inventory < INVENTORY_CAPACITY:
                    picked = self._pick_up_fuel(player)
                    if picked:
                        player.inventory += 1
                        if player.role == Role.CREWMATE:
                            rewards[i] += 0.1

            elif action == Action.DEPOSIT:
                if player.inventory > 0 and self._near_deposit(player):
                    deposited = player.inventory
                    player.inventory = 0
                    state.fuel_deposited += deposited
                    if player.role == Role.CREWMATE:
                        rewards[i] += deposited * 0.5

            elif action == Action.FREEZE:
                if player.role == Role.IMPOSTOR:
                    victim = self._freeze_target(player)
                    if victim is not None:
                        victim.frozen = True
                        victim.active = False
                        freeze_event = (i, victim.player_id)
                        rewards[i] += 1.0
                        rewards[victim.player_id] -= 1.0

        # Check if any active Crewmate outside the freeze radius witnessed the beam
        if freeze_event is not None:
            attacker_id, victim_id = freeze_event
            attacker_pos = state.players[attacker_id].position
            for j, p in enumerate(state.players):
                if j == attacker_id or j == victim_id:
                    continue
                if p.active and p.role == Role.CREWMATE:
                    if p.position.manhattan(attacker_pos) > FREEZE_BEAM_RANGE:
                        state.last_freeze_witnessed = True
                        break

        return rewards

    def _process_voting_step(self, actions: List[int]) -> List[float]:
        state = self.state
        rewards = [0.0] * self.n_players

        for i, player in enumerate(state.players):
            if not player.active:
                continue
            action = Action(actions[i])
            if Action.VOTE_0 <= action <= Action.VOTE_4:
                player.vote_target = int(action) - int(Action.VOTE_0)
            else:
                player.vote_target = None  # abstain

        # At the final tick of the voting phase, tally votes
        if state.phase_tick >= VOTING_PHASE_TICKS - 1:
            vote_counts: Dict[int, int] = {i: 0 for i in range(self.n_players)}
            active_count = sum(1 for p in state.players if p.active)
            for player in state.players:
                if player.active and player.vote_target is not None:
                    vote_counts[player.vote_target] += 1

            for target_id, count in vote_counts.items():
                if active_count > 0 and count >= active_count / 2:
                    target = state.players[target_id]
                    if target.active:
                        target.voted_out = True
                        target.active = False
                        if target.role == Role.IMPOSTOR:
                            for j, p in enumerate(state.players):
                                if p.role == Role.CREWMATE and p.active:
                                    rewards[j] += 2.0
                        else:
                            # Crewmate wrongly voted out
                            for j, p in enumerate(state.players):
                                if p.role == Role.IMPOSTOR:
                                    rewards[j] += 1.0

        return rewards

    # ------------------------------------------------------------------
    # Win condition & phase transition
    # ------------------------------------------------------------------

    def _check_win_conditions(self):
        state = self.state

        # Crewmates win: enough fuel deposited
        if state.fuel_deposited >= FUEL_GOAL:
            state.done = True
            state.winner = WinCondition.CREWMATES_FUEL
            self._assign_terminal_rewards(WinCondition.CREWMATES_FUEL)
            return

        # Crewmates win: Impostor voted out
        for p in state.players:
            if p.role == Role.IMPOSTOR and not p.active and p.voted_out:
                state.done = True
                state.winner = WinCondition.CREWMATES_VOTE
                self._assign_terminal_rewards(WinCondition.CREWMATES_VOTE)
                return

        # Impostor wins: all but one Crewmate inactivated
        active_crewmates = sum(1 for p in state.players if p.role == Role.CREWMATE and p.active)
        if active_crewmates <= 1:
            state.done = True
            state.winner = WinCondition.IMPOSTOR
            self._assign_terminal_rewards(WinCondition.IMPOSTOR)
            return

        # Draw: time limit reached
        if state.tick >= MAX_EPISODE_TICKS:
            state.done = True
            state.winner = WinCondition.DRAW
            return

    def _assign_terminal_rewards(self, condition: str):
        # Step-level rewards are accumulated during play; no additional terminal
        # bonus is applied here. This hook exists for future policy-gradient use.
        pass

    def _maybe_transition_phase(self):
        state = self.state
        if state.done:
            return

        if state.phase == Phase.SITUATION:
            if state.last_freeze_witnessed or state.phase_tick >= SITUATION_PHASE_TICKS:
                state.phase = Phase.VOTING
                state.phase_tick = 0
                state.last_freeze_witnessed = False
                self._teleport_to_voting_room()
        else:
            if state.phase_tick >= VOTING_PHASE_TICKS:
                state.phase = Phase.SITUATION
                state.phase_tick = 0
                self._teleport_from_voting_room()

    # ------------------------------------------------------------------
    # Map helpers
    # ------------------------------------------------------------------

    def _scatter_fuel_cells(self) -> List[Position]:
        corners = [
            (5, 5), (35, 5), (5, 25), (35, 25),
            (4, 6), (36, 6), (4, 26), (36, 26),
            (6, 4), (34, 4), (6, 26), (34, 26),
        ]
        cells = [Position(x, y) for x, y in corners[:FUEL_CELLS_ON_MAP]]
        return cells

    def _random_center_position(self) -> Position:
        return Position(
            x=random.randint(18, 22),
            y=random.randint(13, 17),
        )

    def _move_player(self, player: PlayerState, action: Action):
        p = player.position
        deltas = {
            Action.MOVE_UP: (0, -1),
            Action.MOVE_DOWN: (0, 1),
            Action.MOVE_LEFT: (-1, 0),
            Action.MOVE_RIGHT: (1, 0),
        }
        dx, dy = deltas[action]
        player.position = Position(
            x=max(0, min(MAP_WIDTH - 1, p.x + dx)),
            y=max(0, min(MAP_HEIGHT - 1, p.y + dy)),
        )

    def _pick_up_fuel(self, player: PlayerState) -> bool:
        state = self.state
        for cell in state.fuel_cells:
            if cell.x == player.position.x and cell.y == player.position.y:
                state.fuel_cells.remove(cell)
                return True
        return False

    def _near_deposit(self, player: PlayerState) -> bool:
        deposit = Position(MAP_WIDTH // 2, MAP_HEIGHT // 2)
        return player.position.manhattan(deposit) <= 2

    def _freeze_target(self, player: PlayerState) -> Optional[PlayerState]:
        state = self.state
        for p in state.players:
            if p.player_id != player.player_id and p.active and p.role == Role.CREWMATE:
                if player.position.manhattan(p.position) <= FREEZE_BEAM_RANGE:
                    return p
        return None

    def _teleport_to_voting_room(self):
        for i, player in enumerate(self.state.players):
            if player.active:
                player.position = Position(x=20, y=2 + i)

    def _teleport_from_voting_room(self):
        for player in self.state.players:
            if player.active:
                player.position = self._random_center_position()

    # ------------------------------------------------------------------
    # Observation building
    # ------------------------------------------------------------------

    def _get_observations(self) -> List[Dict]:
        state = self.state
        obs = []
        impostor_ids = [p.player_id for p in state.players if p.role == Role.IMPOSTOR]
        for player in state.players:
            player_obs = {
                "player_id": player.player_id,
                "role": player.role.name,
                "position": {"x": player.position.x, "y": player.position.y},
                "inventory": player.inventory,
                "active": player.active,
                "phase": state.phase.name,
                "tick": state.tick,
                "phase_tick": state.phase_tick,
                "fuel_deposited": state.fuel_deposited,
                # Crewmates see player positions but NOT roles (except self)
                "players_visible": [
                    {
                        "player_id": p.player_id,
                        "position": {"x": p.position.x, "y": p.position.y},
                        "active": p.active,
                        # Impostor knows all roles; Crewmates only know their own role
                        "role": p.role.name
                        if (player.role == Role.IMPOSTOR or p.player_id == player.player_id)
                        else "UNKNOWN",
                    }
                    for p in state.players
                ],
                "fuel_cells_visible": [
                    {"x": c.x, "y": c.y}
                    for c in state.fuel_cells
                ],
            }
            obs.append(player_obs)
        return obs

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_state(self) -> Dict:
        state = self.state
        return {
            "episode_id": self.episode_id,
            "phase": state.phase.name,
            "tick": state.tick,
            "phase_tick": state.phase_tick,
            "fuel_deposited": state.fuel_deposited,
            "fuel_goal": FUEL_GOAL,
            "done": state.done,
            "winner": state.winner,
            "players": [
                {
                    "player_id": p.player_id,
                    "role": p.role.name,
                    "position": {"x": p.position.x, "y": p.position.y},
                    "inventory": p.inventory,
                    "active": p.active,
                    "frozen": p.frozen,
                    "voted_out": p.voted_out,
                }
                for p in state.players
            ],
            "fuel_cells": [{"x": c.x, "y": c.y} for c in state.fuel_cells],
        }

    def _ascii_map(self) -> str:
        state = self.state
        grid = [["." for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        for cell in state.fuel_cells:
            grid[cell.y][cell.x] = "F"
        # deposit location
        grid[MAP_HEIGHT // 2][MAP_WIDTH // 2] = "D"
        for p in state.players:
            symbol = "I" if p.role == Role.IMPOSTOR else str(p.player_id)
            grid[p.position.y][p.position.x] = symbol
        rows = ["".join(row) for row in grid]
        return "\n".join(rows)
