"""Isolated Python environments for tools that conflict with the Colab runtime (agentdojo 0.1.34, vllm).

On the Colab runtime `python -m venv` fails (no ensurepip), so environments are made with virtualenv.
An environment is reused when its package list has not changed.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def ensure_env(path, packages=(), system_site: bool = True, python: str = sys.executable) -> str:
    path = Path(path)
    py = path / "bin" / "python"
    if not py.exists():
        subprocess.run([python, "-m", "pip", "install", "-q", "virtualenv"], check=True)
        args = [python, "-m", "virtualenv", "-q"] + (["--system-site-packages"] if system_site else []) + [str(path)]
        subprocess.run(args, check=True)
    stamp = path / ".packages_sha256"
    want = hashlib.sha256("\n".join(sorted(packages)).encode()).hexdigest()
    if packages and (not stamp.exists() or stamp.read_text().strip() != want):
        subprocess.run([str(py), "-m", "pip", "install", "-q", *packages], check=True)
        stamp.write_text(want)
    return str(py)
