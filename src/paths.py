"""Where this repository's inputs and outputs live.

Shared inputs come from two earlier repositories on the same Drive and are read only: picalib-research
(detector D1, the second indirect source, the AgentDojo set, the paraphrase caches) and wani-research (the
rebuilt public sets of Liu, arXiv 2610.03448, and the registry of continued Wolf Defender checkpoints for
detector D2). They are listed with sha256 in data_manifest.json and never copied here. New files go under DATA.
"""
from __future__ import annotations

import os
from pathlib import Path

DRIVE = Path(os.environ.get("CANARY_DRIVE", "/content/drive/MyDrive"))
PROJECT_ROOT = Path(os.environ.get("CANARY_PROJECT_ROOT", str(DRIVE / "CanaryLabel_Research")))
REPO_ROOT = Path(os.environ.get("CANARY_REPO_ROOT", str(PROJECT_ROOT / "canarylabel-research")))

DATA = REPO_ROOT / "data"            # never committed
CACHE = DATA / "cache"               # model outputs under src/cachekey.py keys
STREAMS = DATA / "streams"           # chronological streams
MODELS = DATA / "models"             # candidate detectors, LoRA updates, checkpoints
POOL = DATA / "pool"                 # spot-check document pool (notebook 06)
REPORTS = REPO_ROOT / "reports"
FIGURES = REPO_ROOT / "figures"
TABLES = REPO_ROOT / "tables"
SCHEMA = REPO_ROOT / "schema"
NOTEBOOKS = REPO_ROOT / "notebooks"
MANIFEST = REPO_ROOT / "data_manifest.json"

REPOS = {
    "picalib": DRIVE / "PICALIB_Research" / "picalib-research",
    "wani": DRIVE / "WANI_Research" / "wani-research",
}
REPO_SLUGS = {"picalib": "anasbiswas1/picalib-research", "wani": "anasbiswas1/wani-research"}

# name -> (source repository, path inside that repository's data/ folder, what it is)
SHARED_FILES = {
    "structural_train": ("picalib", "structural/train.jsonl", "matched-pair training set of detector D1"),
    "structural_val": ("picalib", "structural/val.jsonl", "matched-pair validation set of detector D1"),
    "structural_test": ("picalib", "structural/test.jsonl", "matched-pair test set of detector D1"),
    "second_source": ("picalib", "opi/opi_eval.json", "second indirect source"),
    "agentdojo_own": ("picalib", "agentdojo/set.json", "own AgentDojo set"),
    "phase5_subset": ("picalib", "phase5v2/subset.json", "paraphrase attacker subset"),
    "phase5_rewrites": ("picalib", "phase5v2/rewrites.json", "paraphrase attacker rewrites"),
    "rewrites12_full": ("picalib", "phase5v3/rewrites_full.json", "twelve rewrites of the 210 BIPIA injections"),
    "rewrites12_extra": ("picalib", "phase5v3/rewrites_extra.json", "twelve rewrites of the 210 BIPIA injections, extra"),
    "liu_adclean": ("wani", "public/sets/adclean.jsonl", "Liu AD-Clean"),
    "liu_admatched": ("wani", "public/sets/admatched.jsonl", "Liu AD-Matched"),
    "liu_adshift": ("wani", "public/sets/adshift.jsonl", "Liu AD-Shift"),
    "liu_bipia_pairs": ("wani", "public/sets/bipia_pairs.jsonl", "Liu BIPIA pairs"),
    "liu_tbeval": ("wani", "public/sets/tbeval.jsonl", "Liu tau-bench evaluation set"),
}
SHARED_MODELS = {
    "D1_full_seed0": ("picalib", "structural/model_full/best", "DeBERTa matched-pair guard, seed 0 (detector D1)"),
}
SHARED_REGISTRIES = {
    "continued_models": ("wani", "continued/models.json", "continued Wolf Defender checkpoints (detector D2 is the twin arm, seed 0)"),
}

# open-weight models; revisions are pinned in the notebooks that load them
HF_MODELS = {
    "qwen7b": "Qwen/Qwen2.5-7B-Instruct",                          # canary C1 for T2; C2 for T1 and T3; judge L1
    "llama8b": "meta-llama/Llama-3.1-8B-Instruct",                 # target T1; canary C1 for T1 and T3; C2 for T2
    "secalign8b": "facebook/Meta-SecAlign-8B",                     # target T3; hardened judge L2 (gated)
    "twin7b": "anasbiswas/Qwen2.5-7B-Instruct-TwinDistillation",   # target T2, adapter on qwen7b
}


def repo_data(repo: str) -> Path:
    return REPOS[repo] / "data"


def shared(name: str) -> Path:
    for table in (SHARED_FILES, SHARED_MODELS, SHARED_REGISTRIES):
        if name in table:
            repo, rel, _ = table[name]
            return repo_data(repo) / rel
    raise KeyError(name)


def local(*parts) -> Path:
    p = DATA.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_dirs() -> None:
    for folder in (CACHE, STREAMS, MODELS, POOL, REPORTS, FIGURES, TABLES, SCHEMA):
        folder.mkdir(parents=True, exist_ok=True)
