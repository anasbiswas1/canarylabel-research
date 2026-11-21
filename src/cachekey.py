"""Cache keys and an append-only cache for model outputs (plan v3, Section 10.1).

A key is the sha256 of every field that can change a model's output. Each kind of output has required fields;
a missing one is an error, so an output can never be reused under a looser key. Document text enters the key as
its own sha256. The cache is a set of JSONL shards per namespace, so a run that stops half way keeps everything
written before it; a broken last line is skipped on reading.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REQUIRED = {
    "canary_run": ("text", "model", "revision", "role", "task", "mode", "draw", "seed", "decoding",
                   "prompt_version", "oracle_version"),
    "control_run": ("text", "model", "revision", "role", "task", "mode", "draw", "seed", "decoding",
                    "prompt_version", "oracle_version"),
    "target_run": ("text", "model", "revision", "task", "context", "seed", "decoding", "prompt_version"),
    "judge": ("text", "model", "revision", "task", "seed", "decoding", "prompt_version"),
    "detector": ("text", "model", "revision", "max_len"),
}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_key(kind: str, **fields) -> str:
    if kind not in REQUIRED:
        raise KeyError(f"unknown kind {kind!r}; known: {sorted(REQUIRED)}")
    missing = [f for f in REQUIRED[kind] if f not in fields or fields[f] is None]
    if missing:
        raise ValueError(f"{kind}: missing fields {missing}")
    record = dict(fields)
    record["text"] = text_hash(record["text"])
    blob = json.dumps({"kind": kind, **record}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Cache:
    """cache = Cache(root, "canary_run"); cache.get(key) -> value or None; cache.put(key, value)."""

    def __init__(self, root, namespace: str):
        self.dir = Path(root) / namespace
        self.dir.mkdir(parents=True, exist_ok=True)
        self._loaded = {}

    def _shard(self, key: str) -> Path:
        return self.dir / f"{key[:2]}.jsonl"

    def _load(self, shard: Path) -> dict:
        if shard not in self._loaded:
            table = {}
            if shard.exists():
                with open(shard, encoding="utf-8") as f:
                    for line in f:
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        table[row["k"]] = row["v"]
            self._loaded[shard] = table
        return self._loaded[shard]

    def get(self, key: str):
        return self._load(self._shard(key)).get(key)

    def has(self, key: str) -> bool:
        return key in self._load(self._shard(key))

    def put(self, key: str, value) -> None:
        shard = self._shard(key)
        table = self._load(shard)
        if key in table:
            return
        with open(shard, "a", encoding="utf-8") as f:
            f.write(json.dumps({"k": key, "v": value}, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
        table[key] = value

    def __len__(self) -> int:
        return sum(len(self._load(s)) for s in sorted(self.dir.glob("*.jsonl")))
