"""The gate statistics reproduce the numbers in plan v3."""
import math

import gate


def test_levels():
    assert abs(gate.alpha_r(1) - 7.60e-3) < 1e-4
    assert abs(sum(gate.delta_r(r) for r in range(1, 200000)) - 0.05) < 1e-5


def test_audit_table_of_plan_v3():
    assert gate.audit_size(0.02, 8) == 722
    assert gate.audit_size(0.01, 8) == 1452
    assert gate.audit_size(0.02, 8, new_error_rate=0.005) == 1587
    assert gate.audit_size(0.01, 8, new_error_rate=0.0025) == 3186
    assert gate.audit_size(0.02, 4) == 517


def test_lemma_numbers():
    assert abs(gate.lemma_bound(0.5, 0.05, 4) - 0.0915) < 1e-3
    assert abs(gate.lemma_bound(0.5, 0.05, 8) - 0.00837) < 1e-4
    b = gate.lemma_bound(0.5, 0.05, 8)
    assert abs((1 - (1 - b) ** 13) - 0.1035) < 1e-3
    assert gate.query_bound(13, b) >= 1 - (1 - b) ** 13
    assert gate.lemma_bound(0.03, 0.05, 8) == 1.0


def test_paired_bound_and_accept():
    assert gate.paired_delta_ucb(0, 0, 1587, gate.alpha_r(8)) <= 0.02
    assert gate.paired_delta_ucb(40, 0, 1587, gate.alpha_r(8)) > 0.02
    counts = {"miss": {"f_t": (0, 0), "f_0": (0, 3)}, "fpr": {"f_t": (0, 0), "f_0": (1, 1)}}
    ok, bounds = gate.accept(counts, 1587, 3186, r=8, eps_m=0.02, eps_f=0.01, escalation=0.10, e_max=0.15)
    assert ok and len(bounds) == 4
    ok, _ = gate.accept(counts, 1587, 3186, r=8, eps_m=0.02, eps_f=0.01, escalation=0.20, e_max=0.15)
    assert not ok
