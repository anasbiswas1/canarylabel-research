import random

import pytest

import sandbox as sb


def test_draw_is_reproducible_and_well_formed():
    args = ("workspace", "user_task_13", ["email_events_injection", "drive_feedback_injection"],
            ["email_events_injection", "drive_feedback_injection", "email_hiking_injection"], "random", ["send_email"])
    a = sb.draw_episode(random.Random(sb.seed_for("doc1", 0)), *args)
    b = sb.draw_episode(random.Random(sb.seed_for("doc1", 0)), *args)
    c = sb.draw_episode(random.Random(sb.seed_for("doc1", 1)), *args)
    assert a == b and a != c
    assert a["secret_vector"] != a["position"] and a["secret"] in a["secret_text"]
    assert len(set(a["trap_names"])) == 2 and all(n.isidentifier() and n != "send_email" for n in a["trap_names"])


def test_single_candidate_uses_another_suite_vector():
    d = sb.draw_episode(random.Random(3), "banking", "user_task_0", ["injection_bill_text"],
                        ["injection_bill_text", "injection_landloard_notice"], "replay")
    assert d["position"] == "injection_bill_text" and d["secret_vector"] == "injection_landloard_notice"


def test_no_candidates_is_an_error():
    with pytest.raises(ValueError):
        sb.draw_episode(random.Random(0), "slack", "user_task_x", [], ["v"], "random")


def test_tokens_avoid_ambiguous_characters():
    t = sb.secret_token(random.Random(5))
    assert t.startswith("ACCT-") and not set(t[5:]) & set("O0I1")
