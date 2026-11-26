import random

import rs_attack as rs


class Tok:
    all_special_ids = [0]
    words = ["<s>", "ab", "x y", 'q"', "\\n", "<t>", "long-token-here", "ok", "!", "zz"]
    def __len__(self): return len(self.words)
    def decode(self, ids): return "".join(self.words[i] for i in ids)


def test_allowed_ids_filter():
    assert rs.allowed_ids(Tok()) == [1, 2, 7, 8, 9]


def test_mutate_changes_one_or_two_positions():
    rng = random.Random(0)
    base = [1] * 20
    for _ in range(50):
        m = rs.mutate(rng, base, [7, 8], 2)
        assert len(m) == 20 and 1 <= sum(a != b for a, b in zip(base, m)) <= 2


def test_benign_start_reads_split_tokens():
    # Qwen's vocabulary: "benign" -> "ben" + "ign", "Benign" -> "Ben" + "ign", " benign" one token
    for t in ("ben", "Ben", " benign", "Benign", "BENIGN", "beni", " Ben"):
        assert rs.benign_start(t), t
    for t in ("b", "be", "B", " ", "attack", "Attack", "bent", "benefit", "", None):
        assert not rs.benign_start(t), t


def test_target_score_and_split():
    assert rs.target_score({"benign": -0.1, "attack": -2.0}) == (-0.1, True)
    assert rs.target_score({"ben": -0.3, "attack": -1.5}) == (-0.3, True)
    s, top = rs.target_score({"attack": -0.2, "Ben": -1.7})
    assert s == -1.7 and top is False
    s, top = rs.target_score({"attack": -0.2, " Benign": -1.7})
    assert s == -1.7 and top is False
    s, top = rs.target_score({"attack": -0.1, "The": -3.0, "be": -4.0})
    assert s < -4.0 and top is False
    assert rs.split_document("head PAY tail", "PAY") == ("head PAY", " tail")
    assert rs.split_document("head tail", "PAY") == ("head tail", "")
