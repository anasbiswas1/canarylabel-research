"""The dominance monitor (plan v3, Section 7.8, Equations 16 to 18).

Each spot check gives X = Z - Y', where Z is 1 if the real run of a released "nothing seen" document fired an
instrumented event, and Y' is the share of fresh canary episodes on the same document that fired one. If the
canaries dominate the target with gap gamma, E[X | past] <= gamma. The monitor bets against that with a fixed
mix of bet sizes; each product is a nonnegative supermartingale under the assumption, so is their average, and
by Ville's inequality the wealth reaches 1/alpha with probability at most alpha over the whole deployment.
"""
from __future__ import annotations

import math

import numpy as np

DEFAULT_LAMBDAS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)


def spot_value(z_real: int, fresh_events) -> float:
    fresh = list(fresh_events)
    if not fresh:
        raise ValueError("a spot check needs at least one fresh canary episode")
    return float(z_real) - sum(fresh) / len(fresh)


class BettingMonitor:
    def __init__(self, gamma: float = 0.05, alpha: float = 0.05, lambdas=DEFAULT_LAMBDAS):
        lam = np.asarray(lambdas, dtype=float)
        if np.any(lam < 0) or np.any(lam >= 1.0 / (1.0 + gamma)):
            raise ValueError("bet sizes must lie in [0, 1/(1+gamma)) so every factor stays positive")
        self.gamma, self.alpha, self.lambdas = gamma, alpha, lam
        self.log_wealth = np.zeros(len(lam))
        self.t = 0
        self.alarm_at = None

    @property
    def wealth(self) -> float:
        m = self.log_wealth.max()
        return float(math.exp(m) * np.mean(np.exp(self.log_wealth - m)))

    def update(self, x: float) -> bool:
        if not -1.0 <= x <= 1.0:
            raise ValueError(f"spot value {x} outside [-1, 1]")
        self.log_wealth += np.log1p(self.lambdas * (x - self.gamma))
        self.t += 1
        if self.alarm_at is None and self.wealth >= 1.0 / self.alpha:
            self.alarm_at = self.t
        return self.alarm_at is not None


def combine(monitors) -> float:
    """Average wealth of several monitors on the same filtration (one per source group); still valid."""
    return float(np.mean([m.wealth for m in monitors]))
