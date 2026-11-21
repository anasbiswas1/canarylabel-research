"""Dump AgentDojo v1.2 (agentdojo==0.1.34) for the canary oracle. Run inside the agentdojo environment:

    python tools/ad_dump.py OUT_DIR

Writes, without any model call:
  suites.json          tools (name, parameters), injection vectors with their benign defaults, per suite
  user_tasks.json      prompt, ground-truth calls, injection candidates, clean tool outputs of the ground truth
  injection_tasks.json goal and ground-truth calls on the default environment
  attack_pool.jsonl    tool outputs of the ground truth with an attack placed in the task's injection vectors,
                       kept only where the output differs from the clean output and contains the attack text
                       (differential replay); vectors names the injection vectors whose text the output carries
  checks.json          a trap tool with a random name runs in the runtime; a secret planted through an
                       injection vector is visible in the tool output that reads it
Attack templates address the model as "AI assistant" (agentdojo's name for open-weight Llama pipelines).

The dump is deterministic: the calendar tool stores participants in a set, so the hash seed is fixed; the drive
and email tools stamp the current time, so their clock is fixed at the workspace's current day (2024-05-15).
"""
import ast
import datetime
import json
import os
import sys
import time
import types
from pathlib import Path

import yaml

if os.environ.get("PYTHONHASHSEED") != "0":
    os.execve(sys.executable, [sys.executable, *sys.argv], {**os.environ, "PYTHONHASHSEED": "0"})

from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.default_suites.v1.tools import cloud_drive_client, email_client
from agentdojo.default_suites.v1.tools import types as ad_types
from agentdojo.functions_runtime import FunctionsRuntime, make_function
from agentdojo.task_suite import get_suite

CLOCK = datetime.datetime(2024, 5, 15, 10, 0)


class _FixedClock(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return CLOCK


_clock = types.ModuleType("datetime")
_clock.__dict__.update(vars(datetime))
_clock.datetime = _FixedClock
cloud_drive_client.datetime = _clock
email_client.datetime = _clock
ad_types.Email.model_fields["timestamp"].default_factory = lambda: CLOCK
ad_types.Email.model_rebuild(force=True)

SUITES = ["workspace", "travel", "banking", "slack"]
TEMPLATES = ["direct", "ignore_previous", "important_instructions", "important_instructions_no_model_name",
             "important_instructions_no_names", "important_instructions_no_user_name",
             "important_instructions_wrong_model_name", "important_instructions_wrong_user_name",
             "injecagent", "system_message", "tool_knowledge"]
VERSION = "v1.2"


class _Pipe:
    name = "meta-llama/Llama-3-70b-chat-hf"


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)


def carries(text, injection):
    """True when a tool output contains the injected text. The environment is YAML, so line breaks in the
    injection are folded on load; outputs are YAML or a printed dict. Whitespace is ignored."""
    flat = lambda t: " ".join(t.split())
    want = flat(injection)
    if not want:
        return False
    if want in flat(text):
        return True
    for parse in (yaml.safe_load, ast.literal_eval):
        try:
            if any(want in flat(t) for t in _strings(parse(text))):
                return True
        except Exception:
            pass
    return False


def jsonable(x):
    return json.loads(json.dumps(x, default=str))


def run_calls(suite, env, calls):
    runtime = FunctionsRuntime(suite.tools)
    out = []
    for k, call in enumerate(calls):
        try:
            result, err = runtime.run_function(env, call.function, dict(call.args))
        except Exception as e:  # a ground-truth call can fail on an injected environment
            result, err = None, str(e)
        out.append(dict(step=k, function=call.function, text=tool_result_to_str(result) if err is None else f"Error: {err}"))
    return out


def identities(suite_name, env):
    """The suite user's own addresses and accounts; an agent may always use these."""
    found = []
    for path in (("inbox", "account_email"), ("user", "email"), ("bank_account", "iban")):
        obj = env
        for attr in path:
            obj = getattr(obj, attr, None)
        if isinstance(obj, str) and obj:
            found.append(obj)
    return sorted(set(found))


def trap_check(suite):
    def _trap(destination: str, content: str) -> str:
        """Sends a copy of the account data to the given destination.

        :param destination: where the copy is sent.
        :param content: the data to include.
        """
        return "Done."
    f = types.FunctionType(_trap.__code__, _trap.__globals__, "archive_account_copy", _trap.__defaults__, _trap.__closure__)
    f.__doc__, f.__annotations__ = _trap.__doc__, dict(_trap.__annotations__)
    tool = make_function(f)
    runtime = FunctionsRuntime(list(suite.tools) + [tool])
    env = suite.load_and_inject_default_environment({})
    result, err = runtime.run_function(env, tool.name, {"destination": "a@b.c", "content": "x"})
    return dict(registered=tool.name in [t.name for t in runtime.functions.values()], ran=err is None and result == "Done.")


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    suites, user_tasks, injection_tasks, checks = {}, {}, {}, {}
    n_rows = n_dropped = 0
    with open(out / "attack_pool.jsonl", "w") as pool:
        for s in SUITES:
            suite = get_suite(VERSION, s)
            defaults = suite.get_injection_vector_defaults()
            clean_env = suite.load_and_inject_default_environment({})
            suites[s] = dict(tools=[dict(name=t.name, params=sorted(t.parameters.model_json_schema().get("properties", {})))
                                    for t in suite.tools], vectors=defaults, identities=identities(s, clean_env))
            probe = load_attack("important_instructions", suite, _Pipe())
            injection_tasks[s] = {iid: dict(goal=it.GOAL, gt=[dict(function=c.function, args=jsonable(dict(c.args)))
                                                               for c in it.ground_truth(clean_env.model_copy(deep=True))])
                                  for iid, it in suite.injection_tasks.items()}
            user_tasks[s] = {}
            for tid, task in suite.user_tasks.items():
                calls = task.ground_truth(clean_env.model_copy(deep=True))
                try:
                    cands = probe.get_injection_candidates(task)
                except ValueError:
                    cands = []
                clean_out = run_calls(suite, suite.load_and_inject_default_environment({}), calls)
                user_tasks[s][tid] = dict(prompt=task.PROMPT, candidates=cands, clean_outputs=clean_out,
                                          gt=[dict(function=c.function, args=jsonable(dict(c.args))) for c in calls])
            # secret planted through an injection vector is visible in the output that reads it
            secret_ok = None
            for tid, ut in user_tasks[s].items():
                if ut["candidates"]:
                    token = "ACCT-7F3K9Q"
                    env = suite.load_and_inject_default_environment({ut["candidates"][0]: f"Account recovery code: {token}."})
                    calls = suite.user_tasks[tid].ground_truth(env.model_copy(deep=True))
                    secret_ok = any(token in o["text"] for o in run_calls(suite, env, calls))
                    break
            checks[s] = dict(trap=trap_check(suite), secret_visible=secret_ok)
            # attack pool by differential replay
            attacks = {name: load_attack(name, suite, _Pipe()) for name in TEMPLATES}
            for tid, task in suite.user_tasks.items():
                if not user_tasks[s][tid]["candidates"]:
                    continue
                clean_texts = {o["step"]: o["text"] for o in user_tasks[s][tid]["clean_outputs"]}
                for iid, inj in suite.injection_tasks.items():
                    for name, attack in attacks.items():
                        injections = attack.attack(task, inj)
                        env = suite.load_and_inject_default_environment(injections)
                        calls = task.ground_truth(env.model_copy(deep=True))
                        for o in run_calls(suite, env, calls):
                            if o["step"] in clean_texts and o["text"] != clean_texts[o["step"]]:
                                vec = [v for v in injections if carries(o["text"], injections[v])]
                                if not vec:
                                    n_dropped += 1
                                    continue
                                pool.write(json.dumps(dict(suite=s, user_task=tid, injection_task=iid, template=name,
                                                           step=o["step"], function=o["function"], vectors=vec,
                                                           payload=next(iter(injections.values()), ""), text=o["text"])) + "\n")
                                n_rows += 1
            print(f"{s}: {len(user_tasks[s])} user tasks, {len(injection_tasks[s])} injection tasks, rows so far {n_rows}, "
                  f"{time.time() - t0:.0f}s", flush=True)
    for name, obj in (("suites", suites), ("user_tasks", user_tasks), ("injection_tasks", injection_tasks), ("checks", checks)):
        json.dump(obj, open(out / f"{name}.json", "w"), indent=1)
    json.dump(dict(version=VERSION, templates=TEMPLATES, model_name_in_templates="AI assistant", rows=n_rows,
                   dropped_without_attack_text=n_dropped, clock=str(CLOCK), seconds=round(time.time() - t0)), open(out / "dump_meta.json", "w"), indent=1)
    print("done", n_rows, "rows;", n_dropped, "outputs changed without the attack text, dropped;", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1])
