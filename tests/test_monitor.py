"""False alarms and detection of the betting monitor on simulated spot checks."""
import numpy as np
import pytest

from monitor import BettingMonitor, spot_value, combine


def stream(rng, n, share, p_target, q_canary, m_fresh=4, q_benign=0.02):
    att = rng.random(n) < share
    z = rng.random(n) < np.where(att, p_target, 0.0)
    y = rng.binomial(m_fresh, np.where(att, q_canary, q_benign)) / m_fresh
    return z.astype(float) - y


def alarm_time(xs, **kw):
    m = BettingMonitor(**kw)
    for x in xs:
        if m.update(float(x)):
            return m.alarm_at
    return None


def test_spot_value_and_bounds():
    assert spot_value(1, [0, 0, 1, 0]) == 0.75
    with pytest.raises(ValueError):
        spot_value(1, [])
    with pytest.raises(ValueError):
        BettingMonitor(lambdas=(0.99,))
    with pytest.raises(ValueError):
        BettingMonitor().update(1.5)


def test_few_false_alarms_on_the_boundary_of_the_assumption():
    rng = np.random.default_rng(0)
    alarms = sum(alarm_time(stream(rng, 400, 0.5, 0.30, 0.25)) is not None for _ in range(300))
    assert alarms / 300 <= 0.05


def test_detects_a_strong_violation():
    rng = np.random.default_rng(1)
    times = [alarm_time(stream(rng, 400, 0.5, 0.8, 0.0)) for _ in range(200)]
    hits = [t for t in times if t is not None]
    assert len(hits) / 200 >= 0.95 and np.median(hits) <= 60


def test_combine_is_an_average():
    a, b = BettingMonitor(), BettingMonitor()
    a.update(1.0)
    assert abs(combine([a, b]) - (a.wealth + 1.0) / 2) < 1e-12
