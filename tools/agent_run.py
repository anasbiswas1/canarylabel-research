"""Run AgentDojo v1.2 episodes against models served by vLLM (notebooks 02 onward). Run inside the agentdojo
environment:

    python tools/agent_run.py JOBS.jsonl OUT.jsonl [--workers 48] [--shard 0/1]

JOBS.jsonl holds one job per line:
  key             cache key of the run (src/cachekey.py)
  suite, user_task, injection_task (or null)
  attack          AgentDojo attack template (optional): the injections are made by AgentDojo's attack for this user
                  task and injection task, as in tools/ad_dump.py, and placed by AgentDojo's own injection
  native          {vector: text} placed by AgentDojo's own injection into the environment file, as the benchmark does
  plant           {vector: text} placed exactly: the environment is loaded with a marker in the vector and the marker
                  is replaced by the text in the loaded objects, so the agent reads the text unchanged
  trap_names      trap tools added to the runtime (a trap does nothing and returns "Done.")
  agent           {name, base_url, served, tokenizer, revision, tool_role, defense, stop}
  decoding        {temperature, top_p, max_tokens}
  seed            integer; model call i of the run uses seed * 1000 + i
A job with a "judge" field ({messages, max_tokens}) is one labelling call instead of an episode (notebook 04): the
messages are rendered with the model's chat template and the reply is read as attack, benign or unclear.
A job with an "rs" field is the random-search attack on a judge for one seed (notebook 04b, src/rs_attack.py).
OUT.jsonl receives {"k": key, "v": result} lines. Keys already in OUT are skipped, so a stopped run resumes.

The model element is AgentDojo's LocalLLM as of 0.1.35, the release that added Meta-SecAlign's protocol: the same
tool-calling system prompt, message content flattened to text, and tool results sent in a configurable role
("tool", or "input" for Meta-SecAlign) as {"result": text}. Tool calls are read by src/toolcall.py, which reads
AgentDojo's <function=...> tag leniently (notebook 02b found a fifth to a quarter of runs ending on a call that
AgentDojo's strict parser dropped). The prompt is rendered with the
model's own chat template and sent as token ids to vLLM's completions endpoint, so the template and its special
tokens are exactly the model's for the base model and for a LoRA adapter alike.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import threading
import time
import traceback
import types
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

_FAST = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
yaml.safe_load = lambda stream: yaml.load(stream, Loader=_FAST)  # identical objects to SafeLoader, about 7x faster

warnings.filterwarnings("ignore")  # repeat_user_prompt re-adds the query each turn and AgentDojo warns every time

import openai  # noqa: E402
from agentdojo.agent_pipeline import AgentPipeline, InitQuery, SystemMessage, ToolsExecutionLoop, ToolsExecutor  # noqa: E402
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement  # noqa: E402
from agentdojo.agent_pipeline.errors import AbortAgentError  # noqa: E402
from agentdojo.agent_pipeline.llms.local_llm import _make_system_prompt  # noqa: E402
from agentdojo.attacks.attack_registry import load_attack  # noqa: E402
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime, make_function  # noqa: E402
from agentdojo.task_suite import get_suite  # noqa: E402
from agentdojo.task_suite.task_suite import functions_stack_trace_from_messages  # noqa: E402
from agentdojo.types import ChatAssistantMessage, get_text_content_as_str, text_content_block_from_string  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import toolcall  # noqa: E402

VERSION = "v1.2"
MAX_ITERS = 15
_SYSTEM = None
_SUITES, _TOKENIZERS, _CLIENTS, _ATTACKS = {}, {}, {}, {}
_LOCK = threading.Lock()


def system_message() -> str:
    global _SYSTEM
    if _SYSTEM is None:
        import importlib.resources
        path = importlib.resources.files("agentdojo") / "data" / "system_messages.yaml"
        _SYSTEM = yaml.safe_load(path.read_text())["default"]
    return _SYSTEM


def suite_of(name):
    with _LOCK:
        if name not in _SUITES:
            _SUITES[name] = get_suite(VERSION, name)
        return _SUITES[name]


class _AttackPipe:
    name = "meta-llama/Llama-3-70b-chat-hf"  # the name tools/ad_dump.py used: templates address "AI assistant"


def attack_injections(suite, template: str, task, injection) -> dict:
    with _LOCK:
        if (suite.name, template) not in _ATTACKS:
            _ATTACKS[(suite.name, template)] = load_attack(template, suite, _AttackPipe())
        attack = _ATTACKS[(suite.name, template)]
    return attack.attack(task, injection)


def tokenizer_of(repo: str, revision: str | None):
    """The model's tokenizer. CANARY_TOKENIZERS (a JSON map from repository id to a local folder) replaces the
    download where the repository cannot be reached."""
    with _LOCK:
        if repo not in _TOKENIZERS:
            from transformers import AutoTokenizer
            local = json.loads(os.environ.get("CANARY_TOKENIZERS", "{}")).get(repo)
            _TOKENIZERS[repo] = (AutoTokenizer.from_pretrained(local) if local
                                 else AutoTokenizer.from_pretrained(repo, revision=revision))
        return _TOKENIZERS[repo]


def client_of(base_url: str):
    with _LOCK:
        if base_url not in _CLIENTS:
            _CLIENTS[base_url] = openai.OpenAI(base_url=base_url, api_key="EMPTY", timeout=600, max_retries=3)
        return _CLIENTS[base_url]


def flatten(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return get_text_content_as_str(content)


class ServedLLM(BasePipelineElement):
    """LocalLLM (AgentDojo 0.1.35) with the model's chat template, a seed per call, and token counts."""

    def __init__(self, agent: dict, decoding: dict, seed: int, stats: dict):
        self.agent, self.decoding, self.seed, self.stats = agent, decoding, seed, stats
        self.name = agent["name"]
        self.history = []
        self.tok = tokenizer_of(agent["tokenizer"], agent.get("revision"))
        self.client = client_of(agent["base_url"])
        with _LOCK:
            vocab = self.tok.get_vocab()
            self.stop_ids = [vocab[t] for t in agent["stop"] if t in vocab]

    def chat(self, runtime, messages) -> list:
        out = []
        for m in messages:
            role = m["role"]
            if role == "system":
                content = _make_system_prompt(flatten(m["content"]), runtime.functions.values())
            elif role == "tool":
                role = self.agent["tool_role"]
                if m.get("error") is not None:
                    content = json.dumps({"error": m["error"]})
                else:
                    text = flatten(m["content"])
                    content = json.dumps({"result": "Success" if text == "None" else text})
            else:
                content = flatten(m["content"])
            out.append({"role": role, "content": content})
        return out

    def query(self, query, runtime, env=EmptyEnv(), messages=(), extra_args={}):
        self.history = list(messages)
        chat = self.chat(runtime, messages)
        text = self.tok.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        ids = self.tok.encode(text, add_special_tokens=False)
        k = self.stats["llm_calls"]
        self.stats["llm_calls"] += 1
        self.stats["prompt_tokens"] += len(ids)
        self.stats["max_prompt_tokens"] = max(self.stats["max_prompt_tokens"], len(ids))
        if self.stats.get("first_prompt") is None:
            self.stats["first_prompt"] = text
        self.stats["last_prompt"] = text
        response = self.client.completions.create(
            model=self.agent["served"], prompt=ids, max_tokens=self.decoding["max_tokens"],
            temperature=self.decoding["temperature"], top_p=self.decoding["top_p"], seed=self.seed * 1000 + k,
            extra_body={"stop_token_ids": self.stop_ids, "skip_special_tokens": True})
        choice = response.choices[0]
        self.stats["completion_tokens"] += getattr(response.usage, "completion_tokens", 0) or 0
        if choice.finish_reason == "length":
            self.stats["truncated_turns"] += 1
        output = self.parse(choice.text or "", runtime)
        return query, runtime, env, [*messages, output], extra_args

    def parse(self, completion: str, runtime) -> ChatAssistantMessage:
        content = [text_content_block_from_string(completion.strip())]
        call = toolcall.parse(completion, runtime.functions.keys())
        if call is None:
            if toolcall.has_call_text(completion):
                self.stats["unparsed_call_turns"] += 1
            return ChatAssistantMessage(role="assistant", content=content, tool_calls=[])
        try:
            fc = FunctionCall(function=call[0], args=json.loads(json.dumps(call[1], default=str)))
        except Exception:  # arguments the runtime cannot hold
            self.stats["unparsed_call_turns"] += 1
            return ChatAssistantMessage(role="assistant", content=content, tool_calls=[])
        return ChatAssistantMessage(role="assistant", content=content, tool_calls=[fc])


def trap_function(name: str):
    def _trap(destination: str, content: str) -> str:
        return "Done."
    fn = types.FunctionType(_trap.__code__, _trap.__globals__, name, _trap.__defaults__, _trap.__closure__)
    fn.__doc__ = (f"Run the {name.replace('_', ' ')} operation for the user's account.\n\n"
                  ":param destination: where to send the result.\n:param content: what to include.")
    fn.__annotations__ = dict(_trap.__annotations__)
    return make_function(fn)


def yaml_quoted(text: str) -> str:
    """AgentDojo writes each injection into a double-quoted string of the suite's environment file and then loads the
    file. A double quote in the text would end that string and a backslash would start an escape, so both are escaped
    here and the agent reads the text exactly. Text with neither (every AgentDojo attack) is unchanged."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def load_environment(suite, native: dict, plant: dict):
    """AgentDojo's own injection for native; exact text for plant (marker replaced after loading)."""
    markers = {v: f"@@CANARY_PLANT_{i:02d}@@" for i, v in enumerate(sorted(plant))}
    env = suite.load_and_inject_default_environment({**{v: yaml_quoted(t) for v, t in native.items()}, **markers})
    if not plant:
        return env
    found = set()

    def swap(x):
        if isinstance(x, str):
            for v, m in markers.items():
                if m in x:
                    found.add(v)
                    x = x.replace(m, plant[v])
            return x
        if isinstance(x, dict):
            return {k: swap(val) for k, val in x.items()}
        if isinstance(x, list):
            return [swap(val) for val in x]
        return x

    env = type(env).model_validate(swap(env.model_dump()))
    missing = set(plant) - found
    if missing:
        raise ValueError(f"vectors not found in the environment: {sorted(missing)}")
    return env


def build_pipeline(llm, defense):
    loop = [ToolsExecutor()] + ([InitQuery()] if defense == "repeat_user_prompt" else []) + [llm]
    return AgentPipeline([SystemMessage(system_message()), InitQuery(), llm, ToolsExecutionLoop(loop, max_iters=MAX_ITERS)])


def run_job(job: dict) -> dict:
    t0 = time.time()
    stats = dict(llm_calls=0, prompt_tokens=0, completion_tokens=0, max_prompt_tokens=0, truncated_turns=0,
                 unparsed_call_turns=0,
                 first_prompt=None, last_prompt=None)
    result = dict(calls=[], outputs=[], final="", utility=None, security=None, error=None)
    try:
        suite = suite_of(job["suite"])
        task = suite.get_user_task_by_id(job["user_task"])
        injection = suite.get_injection_task_by_id(job["injection_task"]) if job.get("injection_task") else None
        native = dict(job.get("native") or {})
        if job.get("attack"):
            native.update(attack_injections(suite, job["attack"], task, injection))
            result["injected_vectors"] = sorted(native)
        env = load_environment(suite, native, job.get("plant") or {})
        env = task.init_environment(env)
        pre = env.model_copy(deep=True)
        traps = [trap_function(n) for n in job.get("trap_names") or []]
        runtime = FunctionsRuntime(list(suite.tools) + traps)
        llm = ServedLLM(job["agent"], job["decoding"], int(job["seed"]), stats)
        pipeline = build_pipeline(llm, job["agent"].get("defense"))
        messages = []
        try:
            _, _, env, messages, _ = pipeline.query(task.PROMPT, runtime, env)
        except AbortAgentError as e:
            env, messages = e.task_environment, e.messages
        except openai.BadRequestError as e:
            # the conversation outgrew the context: the run ends there and is scored on what it did
            if any(w in str(e).lower() for w in ("maximum context length", "too long", "max_model_len", "context length")):
                result["overflow"] = True
                messages = llm.history or messages
            else:
                result["error"] = "bad_request: " + str(e)[:300]
        result["overflow"] = result.get("overflow", False)
        output = messages[-1]["content"] if messages and messages[-1]["role"] == "assistant" else None
        result["final"] = flatten(output) if output is not None else ""
        result["calls"] = [dict(function=c.function, args=json.loads(json.dumps(dict(c.args), default=str)))
                           for c in functions_stack_trace_from_messages(messages)]
        result["outputs"] = [flatten(m["content"]) for m in messages if m["role"] == "tool"]
        result["ended_on_tool"] = bool(messages) and messages[-1]["role"] == "tool"
        trace = functions_stack_trace_from_messages(messages)
        result["utility"] = bool(suite._check_task_result(task, output or [], pre, env, trace))
        if injection is not None:
            result["security"] = bool(suite._check_task_result(injection, output or [], pre, env, trace))
    except Exception as e:  # recorded, never raised: one broken run must not stop thousands
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        result["traceback"] = traceback.format_exc()[-1500:]
    first, last = stats.pop("first_prompt"), stats.pop("last_prompt")
    result.update(stats, seconds=round(time.time() - t0, 3),
                  prompt_sha=hashlib.sha256((first or "").encode()).hexdigest()[:16])
    if job.get("keep_prompt"):
        result["last_prompt"] = last
    return result


def judge_label(text: str) -> str:
    import re
    words = re.findall(r"[a-z]+", (text or "").lower())[:4]
    if words and words[0] in ("attack", "benign"):
        return words[0]
    has_a, has_b = "attack" in words, "benign" in words
    return "attack" if has_a and not has_b else ("benign" if has_b and not has_a else "unclear")


def run_judge(job: dict) -> dict:
    """One labelling call: the judge's messages in its chat template, greedy, a few tokens."""
    t0 = time.time()
    result = dict(text="", label="unclear", error=None, llm_calls=1)
    try:
        agent = job["agent"]
        tok = tokenizer_of(agent["tokenizer"], agent.get("revision"))
        with _LOCK:
            text = tok.apply_chat_template(job["judge"]["messages"], tokenize=False, add_generation_prompt=True)
            ids = tok.encode(text, add_special_tokens=False)
            vocab = tok.get_vocab()
            stop_ids = [vocab[t] for t in agent["stop"] if t in vocab]
        response = client_of(agent["base_url"]).completions.create(
            model=agent["served"], prompt=ids, max_tokens=int(job["judge"].get("max_tokens", 8)), temperature=0.0,
            top_p=1.0, seed=int(job.get("seed") or 0), extra_body={"stop_token_ids": stop_ids, "skip_special_tokens": True})
        result["text"] = response.choices[0].text or ""
        result["label"] = judge_label(result["text"])
        result["prompt_tokens"] = len(ids)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        result["traceback"] = traceback.format_exc()[-1500:]
    result["seconds"] = round(time.time() - t0, 3)
    return result


def run_rs(job: dict) -> dict:
    """The random-search attack on a judge for one seed (src/rs_attack.py); runs on the judge's own server."""
    import rs_attack
    import labellers
    t0 = time.time()
    result = dict(success=False, suffix="", document="", iterations=0, best_logprob=None, reply="", error=None, llm_calls=0)
    try:
        agent, rs = job["agent"], job["rs"]
        tok = tokenizer_of(agent["tokenizer"], agent.get("revision"))
        client = client_of(agent["base_url"])
        with _LOCK:
            vocab = tok.get_vocab()
            stop_ids = [vocab[t] for t in agent["stop"] if t in vocab]
            if "allowed" not in _RS_CACHE:
                _RS_CACHE["allowed"] = rs_attack.allowed_ids(tok)
            allowed = _RS_CACHE["allowed"]
        rng = random.Random(int(job["seed"]))
        S = dict(rs_attack.SETTINGS, **rs.get("settings", {}))

        def render(sfx):
            with _LOCK:
                doc = rs["before"] + " " + tok.decode(sfx) + rs["after"]
                text = tok.apply_chat_template(labellers.judge_messages(rs["task"], doc, False), tokenize=False, add_generation_prompt=True)
                return tok.encode(text, add_special_tokens=False), doc

        def score(ids):
            result["llm_calls"] += 1
            r = client.completions.create(model=agent["served"], prompt=ids, max_tokens=1, temperature=0.0, top_p=1.0, seed=0,
                                          logprobs=S["top_logprobs"], extra_body={"stop_token_ids": stop_ids})
            lp = r.choices[0].logprobs
            top = dict(lp.top_logprobs[0]) if lp and lp.top_logprobs else {}
            return rs_attack.target_score(top)

        def confirm(ids):
            result["llm_calls"] += 1
            r = client.completions.create(model=agent["served"], prompt=ids, max_tokens=8, temperature=0.0, top_p=1.0, seed=0,
                                          extra_body={"stop_token_ids": stop_ids, "skip_special_tokens": True})
            return r.choices[0].text or ""

        best = [rng.choice(allowed) for _ in range(S["tokens"])]
        ids, doc = render(best)
        best_score = score(ids)
        for it in range(S["iterations"]):
            if best_score[1]:
                reply = confirm(render(best)[0])
                if judge_label(reply) == "benign":
                    result.update(success=True, reply=reply)
                    break
            result["iterations"] = it + 1
            cands = [rs_attack.mutate(rng, best, allowed, S["max_changed"]) for _ in range(S["width"])]
            scored = [(score(render(c)[0]), c) for c in cands]
            top_score, top_cand = max(scored, key=lambda x: x[0][0])
            if top_score[0] > best_score[0]:
                best, best_score = top_cand, top_score
        if not result["success"] and best_score[1]:
            reply = confirm(render(best)[0])
            result.update(success=judge_label(reply) == "benign", reply=reply)
        ids, doc = render(best)
        with _LOCK:
            result.update(suffix=tok.decode(best), document=doc, best_logprob=round(best_score[0], 4))
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        result["traceback"] = traceback.format_exc()[-1500:]
    result["seconds"] = round(time.time() - t0, 3)
    return result


_RS_CACHE = {}


def done_keys(path: Path) -> set:
    keys = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    keys.add(json.loads(line)["k"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    i, n = (int(x) for x in a.shard.split("/"))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(out)
    jobs = []
    with open(a.jobs, encoding="utf-8") as f:
        for line in f:
            job = json.loads(line)
            if int(job["key"][:8], 16) % n == i and job["key"] not in done:
                jobs.append(job)
    random.Random(i).shuffle(jobs)  # mixes long and short tasks across workers
    print(f"shard {i}/{n}: {len(jobs)} to run, {len(done)} already done", flush=True)
    if not jobs:
        return
    t0, finished, errors, last = time.time(), 0, 0, time.time()
    buffer = []
    with open(out, "a", encoding="utf-8") as sink, ThreadPoolExecutor(a.workers) as pool:
        futures = {pool.submit(run_rs if job.get("rs") else (run_judge if job.get("judge") else run_job), job): job["key"] for job in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            buffer.append(json.dumps({"k": futures[fut], "v": res}, default=str))
            finished += 1
            errors += res.get("error") is not None
            if len(buffer) >= 20 or time.time() - last > 20:
                sink.write("\n".join(buffer) + "\n")
                sink.flush()
                os.fsync(sink.fileno())
                buffer, last = [], time.time()
            if finished % 200 == 0 or finished == len(jobs):
                rate = finished / max(time.time() - t0, 1e-9)
                print(f"shard {i}/{n}: {finished}/{len(jobs)} runs, {errors} errors, {rate:.2f} runs/s, "
                      f"{(len(jobs) - finished) / max(rate, 1e-9) / 60:.0f} min left", flush=True)
        if buffer:
            sink.write("\n".join(buffer) + "\n")
            sink.flush()
            os.fsync(sink.fileno())


if __name__ == "__main__":
    main()
