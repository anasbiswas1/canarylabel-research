"""Refusal rules of tools/commit_cell.py, checked without touching git."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_commit_cell():
    spec = importlib.util.spec_from_file_location("commit_cell", ROOT / "tools" / "commit_cell.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_secret_patterns_fire_on_token_shapes():
    cc = load_commit_cell()
    samples = ["hf_" + "a" * 24, "ghp_" + "b" * 36, "github_pat_" + "c" * 44, "sk-" + "d" * 40,
               "sk-ant-" + "e" * 30, "AKIA" + "E" * 16, "AIza" + "f" * 35]
    for s in samples:
        assert any(p.search(s) for p in cc.SECRET_PATTERNS), s


def test_secret_patterns_quiet_on_ordinary_text():
    cc = load_commit_cell()
    for s in ["canarylabel-research", "sha256", "ghp_short", "sk-abc", "AKIA1234"]:
        assert not any(p.search(s) for p in cc.SECRET_PATTERNS), s


def test_refused_paths():
    cc = load_commit_cell()
    for p in ["data/cache/ab.jsonl", ".git-credentials", "src/x/model.safetensors", "adapter.bin", "_venvs/a/b"]:
        assert cc.refused(p), p
    for p in ["reports/plan_00.md", "src/gate.py", "data_manifest.json", "notebooks/00_setup.ipynb"]:
        assert not cc.refused(p), p
