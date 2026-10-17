#!/usr/bin/env python3
"""The slot-gated workflows treat a cron-dispatcher catch-up exactly like their scheduled run.

GitHub drops or delays these crons by hours (10-16/17). The Mac's cron
dispatcher (00_GrowthEngine tools/cron_dispatcher) then dispatches the workflow
with ``cron=<the missed schedule>``. These tests evaluate each workflow's own
``if:`` / ``env:`` / ``run-name`` expressions for three runs -- the scheduled
one, the catch-up, and a plain manual dispatch -- and check that:

- the catch-up runs the slot gate with that schedule, posts only when the gate
  says so, and computes the same slot (and date) as the scheduled run;
- its run-name carries ``cron <schedule>``, so a later run of the same slot
  (late cron or catch-up) is blocked by social_slot_gate.py;
- a plain manual dispatch keeps its old behaviour.

Standard library only (no PyYAML on the runners): python3 test_cron_catchup.py
"""

from __future__ import annotations

import math
import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / "workflows"
GATED = ("social-extra.yml", "reels-daily.yml", "telegram-clips.yml", "ig-feed-daily.yml", "telegram-daily.yml")
CATCH_UP = GATED + ("clip-backup.yml",)


# --------------------------------------------------------------------------- #
# A small GitHub Actions expression evaluator (the operators these files use)
# --------------------------------------------------------------------------- #
_TOKEN = re.compile(
    r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<op>==|!=|&&|\|\||!|\(|\)|,)"
    r"|(?P<num>\d+(?:\.\d+)?)|(?P<id>[A-Za-z_][\w-]*(?:\.[A-Za-z_][\w-]*)*))"
)


def _number(value):
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return math.nan


def _equal(left, right):
    if isinstance(left, str) and isinstance(right, str):
        return left.lower() == right.lower()
    if type(left) is type(right):
        return left == right
    return _number(left) == _number(right)


def truthy(value):
    if isinstance(value, float) and math.isnan(value):
        return False
    return value not in (None, False, 0, "")


class Expression:
    def __init__(self, text, context):
        text = text.strip()
        if text.startswith("${{") and text.endswith("}}"):
            text = text[3:-2]
        self.tokens = []
        position = 0
        while position < len(text):
            match = _TOKEN.match(text, position)
            if not match or match.end() == position:
                if text[position:].strip() == "":
                    break
                raise ValueError(f"cannot read expression at {text[position:]!r}")
            kind = match.lastgroup
            self.tokens.append((kind, match.group(kind)))
            position = match.end()
        self.index = 0
        self.context = context

    def evaluate(self):
        value = self.either()
        if self.index != len(self.tokens):
            raise ValueError(f"trailing tokens {self.tokens[self.index:]}")
        return value

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else (None, None)

    def take(self, op):
        if self.peek() == ("op", op):
            self.index += 1
            return True
        return False

    def either(self):
        value = self.both()
        while self.take("||"):
            other = self.both()
            value = value if truthy(value) else other
        return value

    def both(self):
        value = self.compare()
        while self.take("&&"):
            other = self.compare()
            value = other if truthy(value) else value
        return value

    def compare(self):
        value = self.unary()
        if self.take("=="):
            return _equal(value, self.unary())
        if self.take("!="):
            return not _equal(value, self.unary())
        return value

    def unary(self):
        if self.take("!"):
            return not truthy(self.unary())
        return self.primary()

    def primary(self):
        kind, text = self.peek()
        self.index += 1
        if kind == "op" and text == "(":
            value = self.either()
            if not self.take(")"):
                raise ValueError("missing )")
            return value
        if kind == "str":
            return text[1:-1].replace("''", "'")
        if kind == "num":
            return float(text)
        if kind == "id":
            if text in ("true", "false"):
                return text == "true"
            if text == "null":
                return None
            if self.take("("):
                args = []
                if not self.take(")"):
                    args.append(self.either())
                    while self.take(","):
                        args.append(self.either())
                    if not self.take(")"):
                        raise ValueError("missing ) after arguments")
                return self.call(text, args)
            return self.context.get(text)
        raise ValueError(f"unexpected token {text!r}")

    @staticmethod
    def call(name, args):
        if name in ("always", "success"):
            return True
        if name in ("failure", "cancelled"):
            return False
        if name == "format":
            template = str(args[0])
            return re.sub(r"\{(\d+)\}", lambda m: "" if args[int(m.group(1)) + 1] is None
                          else str(args[int(m.group(1)) + 1]), template)
        raise ValueError(f"function {name}() is not modelled")


def evaluate(text, context):
    return Expression(text, context).evaluate()


def interpolate(text, context):
    """An env value such as ``${{ github.event.schedule || inputs.cron }}``."""
    def one(match):
        value = evaluate(match.group(1), context)
        return "" if value is None else ("true" if value is True else "false" if value is False else str(value))
    return re.sub(r"\$\{\{(.*?)\}\}", one, text)


# --------------------------------------------------------------------------- #
# Just enough of the workflow files: run-name, dispatch inputs, jobs, steps
# --------------------------------------------------------------------------- #
def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _value(lines, index, indent):
    """Value of `key: value` on lines[index]; folded / literal blocks joined."""
    rest = lines[index].split(":", 1)[1].strip()
    if rest and rest[0] in "|>":
        body = []
        for line in lines[index + 1:]:
            if line.strip() and _indent(line) <= indent:
                break
            body.append(line.strip())
        return (" " if rest[0] == ">" else "\n").join(body).strip()
    if rest[:1] in "'\"" and rest[-1:] == rest[:1]:
        return rest[1:-1]
    return rest


def workflow(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    lines = text.splitlines()
    info = {"text": text, "inputs": {}, "jobs": {}, "steps": [], "crons": [], "run_name": None}
    info["name"] = next(_value(lines, i, 0) for i, line in enumerate(lines) if line.startswith("name:"))
    for index, line in enumerate(lines):
        if line.startswith("run-name:"):
            info["run_name"] = _value(lines, index, 0)
        match = re.match(r"^\s+- cron:\s*['\"]([^'\"]+)['\"]", line)
        if match:
            info["crons"].append(" ".join(match.group(1).split()))
    # workflow_dispatch inputs (name -> {default, type, required})
    start = next((i for i, line in enumerate(lines) if line.strip() == "workflow_dispatch:"), None)
    if start is not None:
        current = None
        for index in range(start + 1, len(lines)):
            line = lines[index]
            if not line.strip() or line.strip().startswith("#"):
                continue
            if _indent(line) <= 2:
                break
            if _indent(line) == 6 and line.strip().endswith(":"):
                current = line.strip()[:-1]
                info["inputs"][current] = {}
            elif _indent(line) == 8 and current and ":" in line:
                key = line.strip().split(":", 1)[0]
                info["inputs"][current][key] = _value(lines, index, 8)
    # jobs (indent 2 under jobs:) and their steps (indent 6 "- ")
    jobs_at = lines.index("jobs:")
    job = None
    step = None
    for index in range(jobs_at + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = _indent(line)
        if indent == 2 and line.strip().endswith(":"):
            job = line.strip()[:-1]
            info["jobs"][job] = {"if": None}
            step = None
        elif indent == 4 and line.strip().startswith("if:"):
            info["jobs"][job]["if"] = _value(lines, index, 4)
        elif indent == 6 and line.lstrip().startswith("- "):
            step = {"job": job, "env": {}}
            info["steps"].append(step)
            first = line.lstrip()[2:]
            if ":" in first:
                lines[index] = " " * 8 + first
                step[first.split(":", 1)[0]] = _value(lines, index, 8)
        elif indent < 6:
            step = None
        elif step is not None and indent == 8 and ":" in line:
            key = line.strip().split(":", 1)[0]
            if key != "env":
                step[key] = _value(lines, index, 8)
        elif step is not None and indent == 10 and ":" in line and _env_block(lines, index):
            key = line.strip().split(":", 1)[0]
            step["env"][key] = _value(lines, index, 10)
    return info


def _env_block(lines, index):
    for back in range(index - 1, -1, -1):
        if lines[back].strip() and _indent(lines[back]) == 8:
            return lines[back].strip() == "env:"
    return False


def inputs_context(info, given):
    context = {}
    for name, spec in info["inputs"].items():
        default = spec.get("default", "")
        if spec.get("type") == "boolean":
            default = str(default).lower() == "true"
        context[f"inputs.{name}"] = given.get(name, default)
    return context


def simulate(info, *, event, cron, should_post, extra_inputs=None):
    """Which steps run, with their env, for one run of the workflow."""
    context = {"github.event_name": event, "github.ref": "refs/heads/main",
               "github.event.schedule": cron if event == "schedule" else None}
    if event == "workflow_dispatch":
        given = dict(extra_inputs or {})
        if cron is not None:
            given["cron"] = cron
        context.update(inputs_context(info, given))
    ran = {}
    for job, spec in info["jobs"].items():
        if spec["if"] and not truthy(evaluate(spec["if"], context)):
            continue
        for step in (s for s in info["steps"] if s["job"] == job):
            condition = step.get("if")
            if condition and not truthy(evaluate(condition, context)):
                continue
            env = {key: interpolate(value, context) for key, value in step["env"].items()}
            ran[step.get("name") or step.get("uses") or step.get("run", "")[:40]] = env
            if step.get("id") == "slot":
                context["steps.slot.outputs.should_post"] = should_post
            if step.get("id") == "cards":
                context["steps.cards.outputs.made"] = "true"
        if job == "post":
            context["needs.post.outputs.should_post"] = context.get("steps.slot.outputs.should_post")
    return ran


def gated_steps(info):
    return [step.get("name") for step in info["steps"]
            if "steps.slot.outputs.should_post" in (step.get("if") or "")]


class CatchUpWiringTests(unittest.TestCase):
    def test_every_catch_up_workflow_declares_the_cron_input(self):
        for name in CATCH_UP:
            with self.subTest(workflow=name):
                info = workflow(name)
                self.assertIn("cron", info["inputs"])
                if name == "telegram-daily.yml":
                    self.assertEqual("true", info["inputs"]["cron"].get("required"))
                else:
                    self.assertEqual("", info["inputs"]["cron"].get("default"))
                self.assertTrue(info["crons"])

    def test_run_name_records_the_cron_and_keeps_the_manual_title(self):
        for name in CATCH_UP:
            info = workflow(name)
            for cron in info["crons"]:
                with self.subTest(workflow=name, cron=cron):
                    scheduled = {"github.event_name": "schedule", "github.event.schedule": cron}
                    self.assertEqual(f"{info['name']} · cron {cron}", interpolate(info["run_name"], scheduled))
                    catch_up = {"github.event_name": "workflow_dispatch", "inputs.cron": cron}
                    self.assertEqual(f"{info['name']} · cron {cron}", interpolate(info["run_name"], catch_up))
            manual = {"github.event_name": "workflow_dispatch", "inputs.cron": ""}
            self.assertEqual(info["name"], interpolate(info["run_name"], manual), name)

    def test_the_gate_decides_for_the_scheduled_run_and_the_catch_up(self):
        for name in GATED:
            info = workflow(name)
            posting = gated_steps(info)
            self.assertTrue(posting, name)
            for cron in info["crons"]:
                for event in ("schedule", "workflow_dispatch"):
                    for verdict in ("true", "false"):
                        with self.subTest(workflow=name, cron=cron, event=event, should_post=verdict):
                            ran = simulate(info, event=event, cron=cron, should_post=verdict)
                            self.assertIn("Prevent duplicate UTC slot", ran)
                            for step in posting:
                                self.assertEqual(verdict == "true", step in ran, step)

    def test_the_gate_uses_the_named_schedule(self):
        for name in GATED:
            info = workflow(name)
            gate = next(step for step in info["steps"] if step.get("id") == "slot")
            if name == "telegram-daily.yml":
                # telegram_post.py publishes only the slot the clock is in (and
                # refuses a TELEGRAM_SCHEDULE of another slot), so its gate stays
                # on the clock; the catch-up names the current slot's cron.
                self.assertNotIn("--schedule", gate["run"])
                continue
            self.assertIn('--schedule "$SLOT_SCHEDULE"', gate["run"], name)
            for cron in info["crons"]:
                for event in ("schedule", "workflow_dispatch"):
                    with self.subTest(workflow=name, cron=cron, event=event):
                        ran = simulate(info, event=event, cron=cron, should_post="true")
                        self.assertEqual(cron, ran["Prevent duplicate UTC slot"]["SLOT_SCHEDULE"])

    def test_posting_steps_see_the_same_slot_in_both_runs(self):
        for name in GATED:
            info = workflow(name)
            for cron in info["crons"]:
                hour = cron.split()[1]
                runs = [simulate(info, event=event, cron=cron, should_post="true")
                        for event in ("schedule", "workflow_dispatch")]
                for step in gated_steps(info):
                    with self.subTest(workflow=name, cron=cron, step=step):
                        scheduled, catch_up = (ran[step] for ran in runs)
                        script = next(item for item in info["steps"] if item.get("name") == step).get("run", "")
                        self.assertEqual(set(scheduled), set(catch_up))
                        for key, value in catch_up.items():
                            if scheduled[key] == value:
                                continue
                            # An input's default where the scheduled run has none: the
                            # script must fall back to that same value.
                            self.assertEqual("", scheduled[key], key)
                            self.assertTrue(
                                f"${{{key}:-{value}}}" in script
                                or (value == "false" and f'"${key}" = "true"' in script),
                                f"{key}={value!r} differs from the scheduled run")
                        for key in ("SCHEDULE", "TELEGRAM_SCHEDULE"):
                            if key in catch_up:
                                self.assertEqual(cron, catch_up[key])
                        if "MANUAL_SLOT" in catch_up:
                            self.assertEqual("", catch_up["MANUAL_SLOT"])  # slot = the cron's hour
                            self.assertEqual(hour, (catch_up["MANUAL_SLOT"] or catch_up["SCHEDULE"].split()[1]))

    def test_a_plain_manual_dispatch_keeps_its_old_behaviour(self):
        for name in GATED:
            info = workflow(name)
            ran = simulate(info, event="workflow_dispatch", cron=None, should_post=None)
            with self.subTest(workflow=name):
                self.assertNotIn("Prevent duplicate UTC slot", ran)
                if name == "telegram-daily.yml":
                    self.assertEqual({}, ran)  # only slots publish Telegram text
                    continue
                posting = [step for step in gated_steps(info) if step in ran]
                self.assertTrue(posting)
                for step in posting:
                    if "MANUAL_SLOT" in ran[step]:
                        self.assertEqual(info["inputs"]["slot"]["default"], ran[step]["MANUAL_SLOT"])

    def test_telegram_daily_catch_up_reaches_the_clip_and_the_catalog(self):
        info = workflow("telegram-daily.yml")
        self.assertEqual("always() && (github.event_name == 'schedule' || "
                         "(github.event_name == 'workflow_dispatch' && inputs.cron != '')) && "
                         "github.ref == 'refs/heads/main' && needs.post.outputs.should_post == 'true'",
                         info["jobs"]["catalog"]["if"])
        for cron in info["crons"]:
            ran = simulate(info, event="workflow_dispatch", cron=cron, should_post="true")
            with self.subTest(cron=cron):
                self.assertIn("Post today's 7-second hook clip (video + App Store button)", ran)
                self.assertIn("Post today's all-App catalog (once per UTC day)", ran)
                self.assertEqual(cron, ran["Post to Telegram channel (free, no OpenAI)"]["TELEGRAM_SCHEDULE"])
        empty = simulate(info, event="workflow_dispatch", cron="", should_post="true")
        self.assertEqual({}, empty)

    def test_clip_backup_catch_up_takes_the_scheduled_branch(self):
        info = workflow("clip-backup.yml")
        which = next(step for step in info["steps"] if step.get("id") == "slot")
        for cron in info["crons"]:
            self.assertIn(f'"{cron}")', which["run"])
            ran = simulate(info, event="workflow_dispatch", cron=cron, should_post=None)
            self.assertEqual(cron, ran["Which slot"]["SCHEDULE"])
            self.assertEqual("", ran["Which slot"]["MANUAL_SLOT"])
        manual = simulate(info, event="workflow_dispatch", cron=None, should_post=None,
                          extra_inputs={"slot": "9", "date": "2026-10-16"})
        self.assertEqual("", manual["Which slot"]["SCHEDULE"])
        self.assertEqual("9", manual["Which slot"]["MANUAL_SLOT"])


class EvaluatorTests(unittest.TestCase):
    def test_loose_equality_and_short_circuit_values(self):
        self.assertTrue(evaluate("inputs.cron == ''", {}))  # null == '' (both 0)
        self.assertFalse(evaluate("inputs.cron != ''", {}))
        self.assertEqual("x", evaluate("inputs.a || 'x'", {}))
        self.assertEqual("", evaluate("inputs.cron == '' && inputs.slot || ''", {"inputs.cron": "1 2 * * *"}))
        self.assertEqual("7", evaluate("inputs.cron == '' && inputs.slot || ''", {"inputs.cron": "", "inputs.slot": "7"}))
        self.assertTrue(evaluate("inputs.dry_run != true", {}))
        self.assertTrue(evaluate("(a || b) == '0 1 * * *'", {"b": "0 1 * * *"}))
        self.assertEqual("R · cron 5", evaluate("format('R · cron {0}', a)", {"a": "5"}))


if __name__ == "__main__":
    unittest.main()
