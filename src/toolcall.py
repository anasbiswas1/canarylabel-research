"""Reading a tool call from a model's reply (tools/agent_run.py, notebook 02c onward).

AgentDojo's local protocol asks for <function=name>{json}</function>. Its parser takes the first tag and accepts
only strict JSON up to the closing tag, so a call written with Python literals (True, None, single quotes), a
trailing comma, a code fence or words after the object is dropped, and the run ends there (notebook 02b: a fifth to
a quarter of clean runs). This parser reads the same tag more leniently, and reads the two native forms of the
model families (Qwen's <tool_call>{"name", "arguments"}</tool_call>, Llama's {"name", "parameters"}) only when the
name is one of the run's tools. Like AgentDojo's parser it returns the first call of the reply.
"""
from __future__ import annotations

import ast
import json
import re

TAG = re.compile(r"<function\s*=\s*([^>]*)>", re.S)
NATIVE = re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.S)
FENCE = re.compile(r"```(?:json|python)?", re.I)
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def first_object(text: str):
    """The first balanced {...} in text, reading quoted strings correctly; None if there is none."""
    start = text.find("{")
    while start != -1:
        depth, quote, escape = 0, None, False
        for i in range(start, len(text)):
            ch = text[i]
            if quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        start = text.find("{", start + 1)
    return None


def loads(s: str):
    """JSON, then JSON without trailing commas, then a Python literal; a dict or None."""
    if s is None:
        return None
    for attempt in (s, re.sub(r",\s*([}\]])", r"\1", s)):
        try:
            v = json.loads(attempt, strict=False)
            return v if isinstance(v, dict) else None
        except (json.JSONDecodeError, ValueError):
            pass
    try:
        v = ast.literal_eval(s)
        return v if isinstance(v, dict) else None
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None


def python_call(s: str):
    """name(a=1, b='x') -> (name, {'a': 1, 'b': 'x'}); None if it is not such a call."""
    try:
        node = ast.parse(s.strip(), mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.args:
        return None
    try:
        return node.func.id, {k.arg: ast.literal_eval(k.value) for k in node.keywords if k.arg}
    except ValueError:
        return None


def _unwrap(name: str, args: dict) -> dict:
    """<function=f>{"name": "f", "parameters": {...}}</function> -> the inner parameters."""
    inner = args.get("parameters", args.get("arguments"))
    if set(args) <= {"name", "parameters", "arguments"} and args.get("name") == name and isinstance(inner, dict):
        return inner
    return args


def _tag_call(text: str):
    m = TAG.search(text)
    if not m:
        return None
    head = m.group(1).strip()
    rest = text[m.end():]
    end = rest.find("</function>")
    body = FENCE.sub("", rest[:end] if end != -1 else rest).strip()
    nm = NAME.match(head)
    if not nm:
        return None
    name, tail = nm.group(0), head[nm.end():].strip()
    args = None
    if tail.startswith("("):
        pc = python_call(head)
        args = pc[1] if pc else None
    elif tail.startswith("{"):
        args = loads(first_object(tail))
    if args is None:
        obj = first_object(body)
        if obj is not None:
            args = loads(obj)
        elif body.startswith("("):
            pc = python_call(name + body.split("\n")[0])
            args = pc[1] if pc else None
        elif not body or body.split("\n")[0].strip() in ("", "{}"):
            args = {}
    if not isinstance(args, dict):
        return None
    return name, _unwrap(name, args)


def _native_call(text: str, names):
    candidates = [m.group(1) for m in NATIVE.finditer(text)] or [text]
    for c in candidates:
        obj = loads(first_object(FENCE.sub("", c)))
        if not obj or obj.get("name") not in names:
            continue
        args = obj.get("arguments", obj.get("parameters", {}))
        if isinstance(args, str):
            args = loads(args)
        if isinstance(args, dict):
            return obj["name"], args
    return None


def parse(text: str, names=()):
    """The first tool call of a reply as (name, args), or None."""
    text = text or ""
    call = _tag_call(text)
    if call is None and names:
        call = _native_call(text, set(names))
    return call


def has_call_text(text: str) -> bool:
    return bool(TAG.search(text or "")) or "<tool_call>" in (text or "")
