"""Escalation band (plan v3, Section 7.2, Equations 1 and 2).

A document with detector score s is passed unchecked when s < lambda_lo, blocked unchecked when s >= lambda_hi, and
escalated to the labeller otherwise. Learn-then-Test on a calibration set: lambda_lo is the largest grid value such
that, for it and every smaller grid value, the one-sided Clopper-Pearson upper bound on the share of working attacks
scoring below it is at most alpha; lambda_hi is the smallest grid value such that, for it and every larger grid
value, the bound on the share of benign documents scoring at or above it is at most beta. When no grid value
qualifies, lambda_lo is 0 (nothing passes unchecked) and lambda_hi is above 1 (nothing is blocked unchecked).
"""
from __future__ import annotations

from gate import cp_upper

GRID = tuple(i / 100 for i in range(101))


def lambda_lo(attack_scores, alpha: float, delta: float = 0.05, grid=GRID) -> float:
    n = len(attack_scores)
    best = 0.0
    for lam in grid:  # small to large: stop at the first value whose bound exceeds alpha
        if cp_upper(sum(s < lam for s in attack_scores), n, delta) > alpha:
            break
        best = lam
    return best


def lambda_hi(benign_scores, beta: float, delta: float = 0.05, grid=GRID) -> float:
    n = len(benign_scores)
    best = 1.01
    for lam in sorted(grid, reverse=True):  # large to small
        if cp_upper(sum(s >= lam for s in benign_scores), n, delta) > beta:
            break
        best = lam
    return best


def route(score: float, lo: float, hi: float) -> str:
    return "pass" if score < lo else ("block" if score >= hi else "escalate")
