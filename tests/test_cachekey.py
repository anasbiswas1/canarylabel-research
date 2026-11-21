import json

import pytest

import cachekey as ck

BASE = dict(text="Please summarise this email.", model="meta-llama/Llama-3.1-8B-Instruct", revision="abc123",
            role="C1", task="workspace_7", mode="random", draw={"secret": "x1", "tools": "t3", "pos": 2}, seed=0,
            decoding={"temperature": 0.0, "max_new_tokens": 256}, prompt_version="p1", oracle_version="o1")


def test_same_fields_same_key():
    assert ck.cache_key("canary_run", **BASE) == ck.cache_key("canary_run", **dict(BASE))


def test_every_field_changes_the_key():
    k0 = ck.cache_key("canary_run", **BASE)
    for field, value in [("text", "Please summarise this email!"), ("revision", "abc124"), ("role", "C2"),
                         ("task", "workspace_8"), ("mode", "replay"), ("draw", {"secret": "x2", "tools": "t3", "pos": 2}),
                         ("seed", 1), ("decoding", {"temperature": 0.7, "max_new_tokens": 256}),
                         ("prompt_version", "p2"), ("oracle_version", "o2"), ("model", "Qwen/Qwen2.5-7B-Instruct")]:
        assert ck.cache_key("canary_run", **{**BASE, field: value}) != k0, field


def test_kind_is_part_of_the_key():
    assert ck.cache_key("canary_run", **BASE) != ck.cache_key("control_run", **BASE)


def test_missing_field_is_an_error():
    fields = dict(BASE)
    fields.pop("draw")
    with pytest.raises(ValueError):
        ck.cache_key("canary_run", **fields)
    with pytest.raises(KeyError):
        ck.cache_key("no_such_kind", **BASE)


def test_cache_round_trip_and_broken_line(tmp_path):
    c = ck.Cache(tmp_path, "canary_run")
    k = ck.cache_key("canary_run", **BASE)
    c.put(k, {"events": ["trap_tool"], "turns": 3})
    assert ck.Cache(tmp_path, "canary_run").get(k) == {"events": ["trap_tool"], "turns": 3}
    with open(c._shard(k), "a") as f:
        f.write('{"k": "half a line')
    fresh = ck.Cache(tmp_path, "canary_run")
    assert fresh.get(k) == {"events": ["trap_tool"], "turns": 3} and len(fresh) == 1
