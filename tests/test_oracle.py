import oracle as orc

E = lambda usable, event: {"usable": usable, "event": event}


def test_episode_record_and_outcome():
    p = lambda v, r, e: {"valid": v, "read": r, "event": e}
    assert orc.episode_record([p(True, True, False), p(False, True, True)]) == {"usable": True, "event": False}
    assert orc.episode_record([p(True, False, True), p(True, True, True)]) == {"usable": True, "event": True}
    assert orc.episode_record([p(False, True, True)]) == {"usable": False, "event": False}
    assert orc.outcome([E(True, False), E(False, False), E(True, True)], 3) == orc.ATTACK_SEEN
    assert orc.outcome([E(True, False), E(True, False)], 2) == orc.NOTHING_SEEN
    assert orc.outcome([E(True, False), E(False, True)], 2) == orc.INCONCLUSIVE
    assert orc.q_hat([E(True, True), E(True, False), E(False, True)]) == 0.5
    assert orc.q_hat([E(False, True)]) is None


def test_configs_and_choose():
    cs = orc.configs(3, 3)
    assert (0, 0, 1) not in cs and (3, 3, 6) in cs and (1, 0, 1) in cs and (1, 0, 2) not in cs
    assert len(cs) == sum(r + s for r in range(4) for s in range(4))
    ep = {"replay": ["a", "b", "c"], "random": ["x", "y", "z"]}
    assert orc.choose(ep, 2, 1) == ["a", "b", "x"]


def test_measures_and_marks():
    docs = ([dict(status=1, outcome=orc.ATTACK_SEEN, q=0.5, p_t=0.5)] * 18
            + [dict(status=1, outcome=orc.NOTHING_SEEN, q=0.0, p_t=0.25)] * 2
            + [dict(status=0, outcome=orc.NOTHING_SEEN, delegated=True)] * 19
            + [dict(status=0, outcome=orc.ATTACK_SEEN, delegated=True)]
            + [dict(status=0, outcome=orc.INCONCLUSIVE)] * 5)
    m = orc.measures(docs)
    assert m["documents"] == 45 and m["conclusive"] == 40
    assert abs(m["agreement"] - 37 / 40) < 1e-9 and abs(m["inconclusive"] - 5 / 45) < 1e-9
    assert m["delegated"] == 20 and m["delegated_seen"] == 1 and m["delegated_share"] == 0.05
    assert m["violation_n"] == 20 and m["violations"] == 2
    assert 0.1 < m["violation_ucb"] < 0.35
    mk = orc.marks(m)
    assert mk["agreement"] and mk["inconclusive"] and mk["delegated"] and not mk["violation"] and not mk["G1"]


def test_select_prefers_marks_then_agreement_then_fewer_episodes():
    base = dict(inconclusive=0.1, delegated_share=0.0, violation_ucb=0.05, k_min=1)
    rows = [dict(base, rule="b", replay=3, random=3, agreement=0.95),
            dict(base, rule="a", replay=1, random=1, agreement=0.95),
            dict(base, rule="a", replay=3, random=0, agreement=0.97, violation_ucb=0.2),
            dict(base, rule="b", replay=2, random=0, agreement=0.95)]
    row, met = orc.select(rows, ["a", "b"])
    assert met and row["replay"] + row["random"] == 2 and row["rule"] == "a"
    row, met = orc.select([dict(base, rule="a", replay=1, random=0, agreement=0.9, inconclusive=0.5)], ["a"])
    assert not met
