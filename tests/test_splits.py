import collections

import splits


def test_heldout_templates_and_goals():
    goals = {"banking": "injection_task_4"}
    assert splits.attack_split("banking", "injection_task_4", "direct", goals) == "CONFIRM"
    assert splits.attack_split("banking", "injection_task_1", "tool_knowledge", goals) == "CONFIRM"
    assert splits.attack_split("banking", "injection_task_1", "system_message", goals) == "DEV"


def test_deterministic_and_close_to_shares():
    keys = [f"seed{i}" for i in range(20000)]
    counts = collections.Counter(splits.assign(k, splits.SHARES_ATTACK) for k in keys)
    assert [splits.assign(k, splits.SHARES_ATTACK) for k in keys[:50]] == [splits.assign(k, splits.SHARES_ATTACK) for k in keys[:50]]
    for name, share in splits.SHARES_ATTACK.items():
        assert abs(counts[name] / len(keys) - share) < 0.015


def test_heldout_goal_needs_ground_truth():
    tasks = {"workspace": {"injection_task_6": {"gt": []}, "injection_task_0": {"gt": [{"function": "send_email"}]}}}
    assert splits.heldout_goals(tasks) == {"workspace": "injection_task_0"}


def test_bank_deploy_roughly_even():
    c = collections.Counter(splits.bank_or_deploy("s", f"t{i}") for i in range(4000))
    assert abs(c["BANK"] / 4000 - 0.5) < 0.03
