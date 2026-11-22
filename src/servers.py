"""vLLM servers and batched agent runs (notebook 02 onward).

vLLM 0.34.0 lives in its own environment: it needs torch 2.14 and transformers 5, which the Colab runtime does not
carry. A server serves one base model and its LoRA adapter under the names of src/agents.py, with weights pinned
to revisions. Sampling follows the request alone (--generation-config vllm), so every agent decodes alike.
Agent runs go to tools/agent_run.py in the agentdojo environment, split over several processes; each process
appends its results to its own file, so a run that stops resumes where it stopped.

CANARY_SERVER_CMD (a command template with {port} and {names}) replaces the vLLM launch where no GPU is present.
"""
from __future__ import annotations

import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import agents
import envs

VLLM_VERSION = "0.34.0"
MAX_MODEL_LEN = 24576  # Meta's AgentDojo setting for Meta-SecAlign


def hf_login() -> None:
    """HF_TOKEN from the environment or Colab Secrets, otherwise a hidden prompt. The token is never printed."""
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        try:
            from google.colab import userdata  # type: ignore
            tok = userdata.get("HF_TOKEN")
        except Exception:
            tok = None
    if not tok and not os.environ.get("CANARY_SERVER_CMD"):
        import getpass
        tok = getpass.getpass("Hugging Face token with access to Llama-3.1 and Meta-SecAlign-8B: ")
    if tok:
        os.environ["HF_TOKEN"] = tok


def vllm_python() -> str:
    if os.environ.get("CANARY_SERVER_CMD"):
        return sys.executable
    return envs.ensure_env("/content/_venvs/vllm", [f"vllm=={VLLM_VERSION}"], system_site=False)


def adapter_dirs(cache_dir) -> dict:
    """LoRA adapters downloaded at their pinned revisions into local folders vLLM can load."""
    if os.environ.get("CANARY_SERVER_CMD"):
        return {name: name for s in agents.SERVERS.values() for name in s["loras"]}
    from huggingface_hub import snapshot_download
    out = {}
    for server in agents.SERVERS.values():
        for name, repo in server["loras"].items():
            out[name] = snapshot_download(repo, revision=agents.REVISIONS[repo], local_dir=str(Path(cache_dir) / name),
                                          token=os.environ.get("HF_TOKEN"))
    return out


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def served_names(port: int) -> set:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as r:
            return {m["id"] for m in json.load(r)["data"]}
    except Exception:
        return set()


def gpu_memory():
    """(used MiB, total MiB) of GPU 0, or None where nvidia-smi is absent."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=30)
        used, total = (float(x) for x in out.stdout.strip().splitlines()[0].split(","))
        return used, total
    except Exception:
        return None


def vllm_processes() -> list:
    """vLLM processes of this machine: anything run from the vLLM environment, and engine cores."""
    try:
        import psutil
    except ImportError:
        return []
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
            if "/_venvs/vllm/" in cmd or (p.info["name"] or "").startswith("VLLM"):
                if p.pid != os.getpid():
                    out.append(p)
        except Exception:
            continue
    return out


def kill_vllm() -> int:
    procs = vllm_processes()
    for p in procs:
        try:
            p.kill()
        except Exception:
            pass
    return len(procs)


def wait_gpu_free(need_frac: float, timeout: int = 300) -> None:
    """Waits until the free share of GPU memory reaches need_frac; a stopped server's engine can hold its memory
    for a while after its port closes. Leftover vLLM processes are killed after 60 s."""
    if os.environ.get("CANARY_SERVER_CMD") or gpu_memory() is None:
        return
    t0, killed = time.time(), False
    while True:
        used, total = gpu_memory()
        if (total - used) / total >= need_frac:
            print(f"GPU memory free: {(total - used) / 1024:.1f} of {total / 1024:.1f} GiB")
            return
        if time.time() - t0 > 60 and not killed:
            print(f"GPU memory still held ({used / 1024:.1f} GiB); stopping {kill_vllm()} leftover vLLM processes")
            killed = True
        if time.time() - t0 > timeout:
            smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
            raise RuntimeError(f"GPU memory not released after {timeout} s:\n{smi}")
        time.sleep(5)


def release(port: int) -> None:
    """Stops whatever still listens on the port (a server left by an earlier kernel holds GPU memory)."""
    if not port_open(port):
        return
    try:
        import psutil
        pids = {c.pid for c in psutil.net_connections(kind="tcp") if c.laddr and c.laddr.port == port and c.pid}
        for pid in pids:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
    except ImportError:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
    for _ in range(60):
        if not port_open(port):
            return
        time.sleep(2)
    raise RuntimeError(f"port {port} still in use")


def only(name: str) -> None:
    """Frees the GPU of every other agent server, and of leftover vLLM processes, before this one starts."""
    for other, spec in agents.SERVERS.items():
        if other != name:
            release(spec["port"])
    spec = agents.SERVERS[name]
    if not ({spec["served"], *spec["loras"]} <= served_names(spec["port"])):
        n = kill_vllm()
        if n:
            print(f"stopped {n} leftover vLLM processes")


def command(name: str, py: str, adapters: dict, gpu_frac: float) -> list:
    s = agents.SERVERS[name]
    names = [s["served"], *s["loras"]]
    override = os.environ.get("CANARY_SERVER_CMD")
    if override:
        return shlex.split(override.format(port=s["port"], names=",".join(names), py=sys.executable))
    return [str(Path(py).parent / "vllm"), "serve", s["model"], "--revision", agents.REVISIONS[s["model"]],
            "--served-model-name", s["served"], "--host", "127.0.0.1", "--port", str(s["port"]),
            "--max-model-len", str(MAX_MODEL_LEN), "--gpu-memory-utilization", str(gpu_frac), "--dtype", "bfloat16",
            "--generation-config", "vllm", "--enable-prefix-caching", "--seed", "0",
            "--enable-lora", "--max-lora-rank", str(s["max_lora_rank"]), "--max-loras", "1",
            "--lora-modules", *[f"{n}={adapters[n]}" for n in s["loras"]]]


class Server:
    def __init__(self, name: str, py: str, adapters: dict, log_dir, gpu_frac: float = 0.85):
        self.name, self.spec, self.gpu_frac = name, agents.SERVERS[name], gpu_frac
        self.cmd = command(name, py, adapters, gpu_frac)
        self.log = Path(log_dir) / f"vllm_{name}.log"
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.proc = None
        self.want = {self.spec["served"], *self.spec["loras"]}

    def start(self, timeout: int = 2400) -> float:
        port = self.spec["port"]
        if port_open(port):
            if self.want <= served_names(port):
                return 0.0
            raise RuntimeError(f"port {port} is taken by something else")
        only(self.name)
        wait_gpu_free(self.gpu_frac + 0.02)
        t0 = time.time()
        self.proc = subprocess.Popen(self.cmd, stdout=open(self.log, "w"), stderr=subprocess.STDOUT,
                                     env=dict(os.environ), start_new_session=True)
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.name} server exited with code {self.proc.returncode}:\n{self.cause()}")
            if self.want <= served_names(port):
                print(f"{self.name} server up after {time.time() - t0:.0f} s: {sorted(self.want)}")
                return time.time() - t0
            time.sleep(5)
        self.stop()
        raise RuntimeError(f"{self.name} server did not come up in {timeout} s:\n{self.cause()}")

    def cause(self) -> str:
        """The error lines of the server log (the root cause sits above the final traceback), then its tail."""
        lines = open(self.log, errors="replace").read().splitlines()
        keys = ("error", "exception", "out of memory", "cuda", "insufficient", "not enough", "free memory")
        hits = [l for l in lines if any(k in l.lower() for k in keys) and not l.lstrip().startswith("File ")]
        return ("Error lines:\n" + "\n".join(hits[-25:]) + "\n\nLast lines:\n" + "\n".join(lines[-25:]))

    def stop(self) -> None:
        """Stops the server and its engine processes, then waits until their GPU memory is released."""
        if self.proc is not None:
            if self.proc.poll() is None:
                try:
                    os.killpg(self.proc.pid, signal.SIGTERM)
                    self.proc.wait(timeout=120)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc = None
        else:
            release(self.spec["port"])
        for _ in range(60):
            if not port_open(self.spec["port"]):
                break
            time.sleep(2)
        kill_vllm()
        wait_gpu_free(self.gpu_frac + 0.02, timeout=180)
        print(f"{self.name} server stopped")


def run_jobs(jobs: list, tag: str, ad_py: str, run_dir, procs: int = 4, workers: int = 48,
             max_error_share: float = 0.02, server: "Server | None" = None) -> dict:
    """Runs the jobs not yet in run_dir/<tag>.p*.jsonl and returns key -> result for every job. The server is
    started only when some run is still to do, so a rerun over cached results loads no model."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    jobs_path = run_dir / f"{tag}.jobs.jsonl"
    agents.write_jobs(jobs, jobs_path)
    outs = [run_dir / f"{tag}.p{i}.jsonl" for i in range(procs)]
    have = agents.read_results(sorted(run_dir.glob(f"{tag}.p*.jsonl")))
    todo = sum(j["key"] not in have for j in jobs)
    t0 = time.time()
    if todo:
        if server is not None:
            server.start()
        print(f"{tag}: {todo} of {len(jobs)} runs to go", flush=True)
        ps = [subprocess.Popen([ad_py, "tools/agent_run.py", str(jobs_path), str(outs[i]), "--workers", str(workers),
                                "--shard", f"{i}/{procs}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, env=dict(os.environ)) for i in range(procs)]
        for p in ps:
            for line in p.stdout:
                if line.startswith("shard") or "Error" in line or "Traceback" in line:
                    print(line, end="", flush=True)
        codes = [p.wait() for p in ps]
        if any(codes):
            raise RuntimeError(f"{tag}: runner exit codes {codes}")
    res = agents.read_results(sorted(run_dir.glob(f"{tag}.p*.jsonl")))
    missing = [j["key"] for j in jobs if j["key"] not in res]
    if missing:
        raise RuntimeError(f"{tag}: {len(missing)} runs have no result")
    errs = [res[j["key"]] for j in jobs if res[j["key"]].get("error")]
    share = len(errs) / max(len(jobs), 1)
    print(f"{tag}: {len(jobs)} runs, {len(errs)} with errors ({share:.3f}), {time.time() - t0:.0f} s this call",
          flush=True)
    if share > max_error_share:
        sample = "\n---\n".join((e.get("error") or "") + "\n" + (e.get("traceback") or "")[-600:] for e in errs[:3])
        raise RuntimeError(f"{tag}: error share {share:.3f} above {max_error_share}:\n{sample}")
    return {j["key"]: res[j["key"]] for j in jobs}
