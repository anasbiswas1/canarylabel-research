"""Statistics of the update gate and the label-integrity lemma (plan v3, Equations 8, 9 and 11 to 14).

The gate compares a candidate detector with a reference on the same audit items. N10 counts items the candidate
gets wrong and the reference gets right, N01 the reverse, out of n. The absolute change in error rate is
p10 - p01; its upper bound is the Clopper-Pearson upper bound on p10 minus the lower bound on p01, each at half
the level. Levels are split over rounds and over all 2^(r-1) histories of earlier gate outcomes, so one audit
set can be reused for R rounds fixed in advance.
"""
from __future__ import annotations

import math

from scipy.stats import beta


def cp_upper(x: int, n: int, a: float) -> float:
    """One-sided Clopper-Pearson upper bound on a rate, error probability a."""
    if n <= 0:
        return 1.0
    return 1.0 if x >= n else float(beta.ppf(1 - a, x + 1, n - x))


def cp_lower(x: int, n: int, a: float) -> float:
    """One-sided Clopper-Pearson lower bound on a rate, error probability a."""
    if n <= 0 or x <= 0:
        return 0.0
    return float(beta.ppf(a, x, n - x + 1))


def paired_delta_ucb(n10: int, n01: int, n: int, alpha: float) -> float:
    """Equation (12): upper bound on p10 - p01 with error probability at most alpha."""
    return cp_upper(n10, n, alpha / 2) - cp_lower(n01, n, alpha / 2)


def delta_r(r: int, delta: float = 0.05) -> float:
    """Error budget of round r; sums to delta over all rounds."""
    return 6 * delta / (math.pi ** 2 * r ** 2)


def alpha_r(r: int, delta: float = 0.05, n_bounds: int = 4) -> float:
    """Equation (13): level of each bound in round r, split over the 2^(r-1) histories of gate outcomes."""
    return delta_r(r, delta) / (n_bounds * 2 ** (r - 1))


def accept(counts: dict, n_attack: int, n_benign: int, r: int, eps_m: float, eps_f: float,
           escalation: float, e_max: float, delta: float = 0.05) -> tuple:
    """Equation (14). counts = {"miss": {"f_t": (n10, n01), "f_0": (...)}, "fpr": {...}}. Returns (accepted, bounds)."""
    a = alpha_r(r, delta)
    bounds = {}
    for rate, n, eps in (("miss", n_attack, eps_m), ("fpr", n_benign, eps_f)):
        for ref in ("f_t", "f_0"):
            n10, n01 = counts[rate][ref]
            bounds[(rate, ref)] = paired_delta_ucb(n10, n01, n, a)
    ok = all(bounds[("miss", g)] <= eps_m and bounds[("fpr", g)] <= eps_f for g in ("f_t", "f_0"))
    return ok and escalation <= e_max, bounds


def lemma_bound(p: float, gamma: float, k_valid: int) -> float:
    """Equation (8): bound on P(nothing seen) for a document that hijacks the target with probability >= p."""
    return (1.0 - max(p - gamma, 0.0)) ** k_valid


def query_bound(q: int, b: float) -> float:
    """Equation (9): bound over q attacker queries."""
    return min(1.0, q * b)


def audit_size(eps: float, rounds: int, delta: float = 0.05, new_error_rate: float = 0.0) -> int:
    """Smallest audit size for which round `rounds` still passes a candidate that makes new errors at
    new_error_rate and fixes none (the table in plan v3, Section 7.7)."""
    a = alpha_r(rounds, delta)
    lo, hi = 10, 200000
    while lo < hi:
        m = (lo + hi) // 2
        if paired_delta_ucb(round(new_error_rate * m), 0, m, a) <= eps:
            hi = m
        else:
            lo = m + 1
    return lo
