"""Document pools for the canary study (plan v3, Section 9.2; amendment 1 in reports/amendment_01.md).

attack       AgentDojo tool outputs carrying an attack whose goal is a tool action the oracle can see
benign       clean AgentDojo tool outputs and vector defaults, plus benign documents of the shared sets
instruction  documents that carry an instruction but no tool goal in AgentDojo (BIPIA, tau-bench, the second
             source, AgentDojo goals that only ask the agent to say something); used as decoys and for the
             secondary detection result, never as working attacks
Every row gets a doc_id (hash of source and text), a host key and, for attacks, a payload seed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def doc_id(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}\n{text}".encode("utf-8")).hexdigest()[:16]


def norm_text(text: str) -> str:
    return " ".join(str(text).split()).lower()


def read_rows(path) -> list:
    """JSON list, JSON dict holding one list, or JSONL."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        lists = [v for v in obj.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        if lists:
            return max(lists, key=len)
    raise ValueError(f"no rows found in {p}")


def ad_attack_rows(pool_jsonl, text_goal_tasks: set) -> tuple:
    attack, instruction = [], []
    with open(pool_jsonl, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            row = dict(source="agentdojo", suite=r["suite"], host=f"{r['suite']}/{r['user_task']}",
                       user_task=r["user_task"], injection_task=r["injection_task"], template=r["template"],
                       step=r["step"], function=r["function"], vectors=r["vectors"], payload=r["payload"],
                       text=r["text"], label=1)
            row["doc_id"] = doc_id(row["source"], row["text"] + "|" + r["injection_task"] + "|" + r["template"])
            if (r["suite"], r["injection_task"]) in text_goal_tasks:
                row.update(pool="instruction", seed=f"{r['suite']}/{r['injection_task']}/{r['template']}")
                instruction.append(row)
            else:
                row.update(pool="attack", seed=f"{r['suite']}/{r['injection_task']}/{r['template']}")
                attack.append(row)
    return attack, instruction


def ad_clean_rows(user_tasks: dict) -> list:
    rows = []
    for suite, tasks in user_tasks.items():
        for tid, t in tasks.items():
            for o in t["clean_outputs"]:
                if o["text"].startswith("Error:") or not o["text"].strip():
                    continue
                rows.append(dict(pool="benign", source="agentdojo_clean", suite=suite, host=f"{suite}/{tid}",
                                 user_task=tid, step=o["step"], function=o["function"], text=o["text"], label=0))
    return rows


def ad_default_rows(suites: dict) -> list:
    rows = []
    for suite, meta in suites.items():
        for vec, text in meta["vectors"].items():
            if text and text.strip():
                rows.append(dict(pool="benign", source="agentdojo_default", suite=suite, host=f"{suite}/{vec}",
                                 vector=vec, text=text, label=0))
    return rows


def shared_rows(name: str, rows: list) -> tuple:
    """Benign and instruction-bearing rows from one shared set. Hosts follow each set's own structure."""
    benign, instruction = [], []
    for i, r in enumerate(rows):
        text = r.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        label = int(r.get("label", 0))
        if name == "picalib_agentdojo":
            if label == 1:
                continue  # the attacked slots repeat the AgentDojo payloads already in the attack pool
            host = f"{r.get('suite', '')}/{r.get('slot') or r.get('kind', '')}"
        elif name in ("liu_bipia_pairs", "liu_tbeval"):
            host = f"{r.get('suite', '')}/{r.get('task', i)}"
        elif name == "second_source":
            host = f"opi/{r.get('target_task', '')}/{hashlib.sha256(text.encode()).hexdigest()[:8] if label == 0 else i}"
        elif name == "structural_test":
            if r.get("form") == "embedded":
                instruction.append(dict(pool="instruction", source=name, host=f"structural/{r.get('host_src') or i}",
                                        family=r.get("family", ""), text=text, label=1))
                continue
            host = f"structural/{r.get('host_src') or r.get('unit') or i}"
        else:
            host = f"{name}/{i}"
        row = dict(source=name, host=host, text=text, label=label,
                   family=r.get("attack") or r.get("strategy") or r.get("family") or "", form=r.get("form", ""))
        if label == 0:
            benign.append(dict(row, pool="benign"))
        else:
            instruction.append(dict(row, pool="instruction"))
    return benign, instruction


def finalise(rows: list, exclude_texts: set = frozenset()) -> list:
    """Adds doc ids and drops duplicate texts within the list and texts listed in exclude_texts."""
    seen, out = set(exclude_texts), []
    for r in rows:
        key = norm_text(r["text"])
        if key in seen:
            continue
        seen.add(key)
        r.setdefault("doc_id", doc_id(r["source"], r["text"]))
        out.append(r)
    return out
