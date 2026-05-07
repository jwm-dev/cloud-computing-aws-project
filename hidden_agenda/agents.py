import numpy as np
from .constants import N_PLAYERS

class RandomAgent:
    def __init__(self, rng=None):
        self.rng = rng or np.random.default_rng()

    def act(self, obs):
        # Determine phase from obs keys
        # If vote_matrix present and small values indicate voting phase; assume env decides
        # We'll pick legal action length 8 for situation, 6 for voting
        if 'vote_matrix' in obs:
            # voting phase: 0-4 players, 5 abstain
            return int(self.rng.integers(0, 6))
        return int(self.rng.integers(0, 8))

class HeuristicAgent:
    def __init__(self):
        pass

    def act(self, obs):
        # Very simple: if inventory_ratio < 1, move randomly to find fuel
        rm = obs.get('vote_matrix')
        if rm is not None and hasattr(rm, 'shape') and rm.shape == (5, 7):
            # voting: abstain
            return 5
        # situation: if low progress, move forward
        if obs['inventory_ratio'] < 0.5:
            return 0
        return 6
