import json
from hidden_agenda.env import HiddenAgendaEnv


def test_reset_and_observations():
    env = HiddenAgendaEnv(seed=123)
    obs = env.reset()
    assert isinstance(obs, dict)
    assert len(obs)==5


def test_determinism():
    env1 = HiddenAgendaEnv(seed=42)
    env2 = HiddenAgendaEnv(seed=42)
    env1.reset(); env2.reset()
    # run a few steps with deterministic random agents
    for _ in range(5):
        actions = {i:0 for i in range(5)}
        o1, r1, d1, _ = env1.step(actions)
        o2, r2, d2, _ = env2.step(actions)
        assert d1==d2
        assert env1._state_hash() == env2._state_hash()


def test_replay_logging():
    env = HiddenAgendaEnv(seed=7)
    env.reset()
    actions = {i:0 for i in range(5)}
    env.step(actions)
    assert 'steps' in env.log
    assert len(env.log['steps'])>=1
