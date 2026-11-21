"""The five data splits and the task bank split (plan v3, Section 9.2).

Attack documents are split by payload seed (suite, injection task, template), so paraphrases, twins and grafts of
one seed stay in one split. Two templates are held out for CONFIRM and two for DEV only; one injection task per suite
(among those with ground truth) is held out for CONFIRM with every template. Benign documents are split by host.
User tasks are split into BANK (random-mode canary tasks) and DEPLOY (held-out contexts for real runs). Every
assignment is a hash of the key with a fixed salt, so it never depends on the order of the data.
"""
from __future__ import annotations

import hashlib

SALT = "canarylabel-01"
SPLITS = ("DEV", "CAL", "AUDIT", "STRESS", "CONFIRM")
SHARES_ATTACK = {"DEV": 0.15, "CAL": 0.10, "AUDIT": 0.45, "STRESS": 0.10, "CONFIRM": 0.20}
SHARES_BENIGN = {"DEV": 0.15, "CAL": 0.10, "AUDIT": 0.50, "STRESS": 0.05, "CONFIRM": 0.20}
HELDOUT_TEMPLATES = {"CONFIRM": ("tool_knowledge", "injecagent"),
                     "DEV": ("system_message", "important_instructions_wrong_user_name")}


def unit(key: str, salt: str = SALT) -> float:
    return int(hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()[:15], 16) / 16 ** 15


def assign(key: str, shares: dict, salt: str = SALT) -> str:
    u, acc = unit(key, salt), 0.0
    for name in SPLITS:
        acc += shares[name]
        if u < acc:
            return name
    return SPLITS[-1]


def heldout_goals(injection_tasks: dict, salt: str = SALT) -> dict:
    """One injection task per suite, among those with ground truth, held out for CONFIRM."""
    out = {}
    for suite, tasks in injection_tasks.items():
        with_gt = sorted(t for t, v in tasks.items() if v.get("gt"))
        if with_gt:
            out[suite] = min(with_gt, key=lambda t: unit(f"goal|{suite}|{t}", salt))
    return out


def attack_split(suite: str, injection_task: str, template: str, goals_out: dict, salt: str = SALT) -> str:
    if goals_out.get(suite) == injection_task:
        return "CONFIRM"
    for split, templates in HELDOUT_TEMPLATES.items():
        if template in templates:
            return split
    return assign(f"seed|{suite}|{injection_task}|{template}", SHARES_ATTACK, salt)


def benign_split(host: str, salt: str = SALT) -> str:
    return assign(f"host|{host}", SHARES_BENIGN, salt)


def bank_or_deploy(suite: str, task_id: str, salt: str = SALT) -> str:
    return "BANK" if unit(f"task|{suite}|{task_id}", salt) < 0.5 else "DEPLOY"
