"""Detector D1 scores: P(injection) from picalib's DeBERTa matched-pair guard (structural_train.score_texts in
picalib-research: softmax over two labels, label 1 is injection, 512 tokens with truncation).

CANARY_FAKE_D1=1 replaces the model with a hash of the text, for the CPU dry run only.
"""
from __future__ import annotations

import hashlib
import os

MAX_LEN = 512


def score_texts(model_dir, texts, batch: int = 32, max_len: int = MAX_LEN) -> list:
    texts = list(texts)
    if os.environ.get("CANARY_FAKE_D1"):
        return [int(hashlib.sha256(t.encode()).hexdigest()[:6], 16) / 0xFFFFFF for t in texts]
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).float().to(dev).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            b = tok(texts[i:i + batch], truncation=True, max_length=max_len, padding=True, return_tensors="pt").to(dev)
            out += torch.softmax(model(**b).logits.float(), -1)[:, 1].cpu().tolist()
    del model
    if dev == "cuda":
        torch.cuda.empty_cache()
    return out
