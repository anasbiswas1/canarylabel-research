import importlib
import os


def test_shared_and_local(tmp_path, monkeypatch):
    monkeypatch.setenv("CANARY_DRIVE", str(tmp_path / "drive"))
    monkeypatch.setenv("CANARY_REPO_ROOT", str(tmp_path / "repo"))
    import paths
    importlib.reload(paths)
    assert paths.shared("liu_admatched") == tmp_path / "drive" / "WANI_Research" / "wani-research" / "data" / "public" / "sets" / "admatched.jsonl"
    assert paths.shared("D1_full_seed0").name == "best"
    p = paths.local("cache", "x", "y.jsonl")
    assert p.parent.is_dir() and str(p).startswith(str(tmp_path / "repo" / "data"))
