#!/usr/bin/env python3
"""Regression and mutation tests for the natural GEO schedule chain."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = (
    ROOT
    / ".github"
    / "fixtures"
    / "geo-natural-schedule-20260822-20260829.json"
)
GEO_WORKFLOW = ROOT / ".github" / "workflows" / "geo-daily.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
INDEXNOW_WORKFLOW = ROOT / ".github" / "workflows" / "indexnow-daily.yml"
BOUNDED_RETRY = HERE / "bounded-retry.sh"
REMOTE_FIRST = HERE / "remote-first-publish.sh"
GEO_RUNTIME = HERE / "geo-runtime.sh"
SCRATCH = HERE / ".geo-schedule-reliability-tests"

sys.path.insert(0, str(HERE))
import geo_schedule_reliability as reliability  # noqa: E402


@contextmanager
def project_temporary_directory():
    SCRATCH.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="case-", dir=SCRATCH)
    try:
        yield Path(temporary.name)
    finally:
        temporary.cleanup()
        try:
            SCRATCH.rmdir()
        except OSError:
            pass


class HistoricalReplayTests(unittest.TestCase):
    def test_all_28_natural_roots_replay_to_the_audited_counts(self):
        result = reliability.replay_fixture(FIXTURE)
        self.assertEqual(28, result["run_count"])
        self.assertEqual([], result["mismatches"])
        self.assertEqual(
            {
                "success": 4,
                "code/config": 12,
                "timeout": 0,
                "quota": 0,
                "remote drift": 4,
                "concurrency": 8,
                "Pages": 0,
                "IndexNow": 0,
                "external service": 0,
            },
            result["counts"],
        )

    def test_fixture_has_unique_schedule_roots(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        run_ids = [record["run_id"] for record in data["runs"]]
        self.assertEqual(len(run_ids), len(set(run_ids)))
        self.assertEqual(28, data["window"]["expected_natural_roots"])

    def test_classifier_keeps_downstream_and_platform_failures_distinct(self):
        cases = {
            "timeout": {
                "conclusion": "failure",
                "signals": ["normalized exit 124 after timeout"],
            },
            "quota": {
                "conclusion": "failure",
                "signals": ["HTTP 429 API rate limit quota"],
            },
            "Pages": {
                "conclusion": "failure",
                "signals": ["GitHub Pages deploy-pages failed"],
            },
            "IndexNow": {
                "conclusion": "failure",
                "signals": ["IndexNow endpoint rejected the request"],
            },
            "external service": {
                "conclusion": "failure",
                "signals": ["HTTP 503 service unavailable"],
            },
        }
        for expected, record in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(
                    expected,
                    reliability.classify_record(record),
                )


class WorkflowContractMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = GEO_WORKFLOW.read_text(encoding="utf-8")
        cls.pages = PAGES_WORKFLOW.read_text(encoding="utf-8")
        cls.indexnow = INDEXNOW_WORKFLOW.read_text(encoding="utf-8")

    def errors(self, geo=None, pages=None, indexnow=None):
        return reliability.validate_workflow_contracts(
            self.geo if geo is None else geo,
            self.pages if pages is None else pages,
            self.indexnow if indexnow is None else indexnow,
        )

    def test_current_natural_root_chain_is_valid(self):
        self.assertEqual([], self.errors())

    def test_schedule_event_gate_mutations_fail(self):
        mutations = (
            self.geo.replace(
                "\npermissions:",
                "\n  workflow_dispatch:\n\npermissions:",
                1,
            ),
            self.geo.replace(" && github.run_attempt == 1", "", 1),
            self.geo.replace("ref: ${{ github.sha }}", "ref: main", 1),
            self.geo.replace("timeout-minutes: 170", "timeout-minutes: 360", 1),
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated[:80]):
                self.assertTrue(self.errors(geo=mutated))

    def test_publish_order_mutations_fail(self):
        mutations = (
            self.geo.replace("REMOTE_FIRST_VALIDATE_ONLY=1 ", "", 1),
            self.geo.replace(
                "- name: Upload sealed candidate evidence",
                "- name: Missing sealed candidate evidence",
                1,
            ),
            self.geo.replace(
                'REMOTE_FIRST_MAX_ATTEMPTS: "3"',
                'REMOTE_FIRST_MAX_ATTEMPTS: "9"',
                1,
            ),
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated[-120:]):
                self.assertTrue(self.errors(geo=mutated))

    def test_downstream_root_chain_mutations_fail(self):
        pages_mutations = (
            self.pages.replace(
                "actions/download-artifact@v4",
                "actions/download-artifact@missing",
                1,
            ),
            self.pages.replace(
                "ref: ${{ steps.source.outputs.sha }}",
                "ref: main",
                1,
            ),
        )
        for mutated in pages_mutations:
            with self.subTest():
                self.assertTrue(self.errors(pages=mutated))
        mutated_indexnow = self.indexnow.replace(
            "Pin exact deployed source tree",
            "Missing exact deployed source tree",
            1,
        )
        self.assertTrue(self.errors(indexnow=mutated_indexnow))


class BoundedRetryTests(unittest.TestCase):
    def run_shell(self, cwd: Path, body: str):
        env = dict(os.environ, BOUNDED_RETRY_DELAY_CAP_SECONDS="0")
        return subprocess.run(
            ["bash", "-c", body],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_transient_failure_retries_then_succeeds(self):
        with project_temporary_directory() as root:
            script = root / "flaky.py"
            counter = root / "count"
            script.write_text(
                (
                    "from pathlib import Path\n"
                    f"p=Path({str(counter)!r})\n"
                    "n=int(p.read_text())+1 if p.exists() else 1\n"
                    "p.write_text(str(n))\n"
                    "raise SystemExit(0 if n == 2 else 7)\n"
                ),
                encoding="utf-8",
            )
            body = (
                f"source {shlex.quote(str(BOUNDED_RETRY))}\n"
                "run_bounded_retry 5 3 0 fixture "
                f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}\n"
            )
            result = self.run_shell(root, body)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("2", counter.read_text())

    def test_persistent_failure_stops_at_bound(self):
        with project_temporary_directory() as root:
            script = root / "fail.py"
            counter = root / "count"
            script.write_text(
                (
                    "from pathlib import Path\n"
                    f"p=Path({str(counter)!r})\n"
                    "n=int(p.read_text())+1 if p.exists() else 1\n"
                    "p.write_text(str(n))\n"
                    "raise SystemExit(9)\n"
                ),
                encoding="utf-8",
            )
            body = (
                f"source {shlex.quote(str(BOUNDED_RETRY))}\n"
                "run_bounded_retry 5 3 0 fixture "
                f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}\n"
            )
            result = self.run_shell(root, body)
            self.assertEqual(9, result.returncode)
            self.assertEqual("3", counter.read_text())

    def test_timeout_is_retried_but_never_unbounded(self):
        with project_temporary_directory() as root:
            script = root / "slow.py"
            counter = root / "count"
            script.write_text(
                (
                    "from pathlib import Path\n"
                    "import time\n"
                    f"p=Path({str(counter)!r})\n"
                    "n=int(p.read_text())+1 if p.exists() else 1\n"
                    "p.write_text(str(n))\n"
                    "time.sleep(5)\n"
                ),
                encoding="utf-8",
            )
            body = (
                f"source {shlex.quote(str(BOUNDED_RETRY))}\n"
                "run_bounded_retry 0.3 2 0 fixture "
                f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}\n"
            )
            result = self.run_shell(root, body)
            self.assertEqual(124, result.returncode)
            self.assertEqual("2", counter.read_text())


class GeoRuntimeTests(unittest.TestCase):
    def test_natural_root_and_utc_clock_are_explicit(self):
        body = f"""
source {shlex.quote(str(GEO_RUNTIME))}
GITHUB_EVENT_NAME=schedule
GITHUB_RUN_ATTEMPT=1
geo_require_natural_root
geo_refresh_utc_date 2026-08-29T23:59:59Z
test "$TZ" = UTC
test "$GEO_BUILD_DATE" = 2026-08-29
"""
        result = subprocess.run(
            ["bash", "-c", body],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_dispatch_and_rerun_are_rejected(self):
        for event, attempt in (("workflow_dispatch", "1"), ("schedule", "2")):
            body = f"""
source {shlex.quote(str(GEO_RUNTIME))}
GITHUB_EVENT_NAME={event}
GITHUB_RUN_ATTEMPT={attempt}
geo_require_natural_root
"""
            result = subprocess.run(
                ["bash", "-c", body],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(78, result.returncode)


class RemoteFirstValidationTests(unittest.TestCase):
    def test_validate_only_never_needs_a_remote_or_pushes(self):
        with project_temporary_directory() as root:
            marker = root / "validated"
            body = f"""
source {shlex.quote(str(REMOTE_FIRST))}
reconcile_phase() {{
  printf validated > {shlex.quote(str(marker))}
}}
REMOTE_FIRST_VALIDATE_ONLY=1 \
  remote_first_publish reconcile_phase missing main 5
test "$REMOTE_FIRST_ATTEMPTS_USED" = "0"
"""
            result = subprocess.run(
                ["bash", "-c", body],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("validated", marker.read_text())

    def test_remote_source_change_is_fail_closed(self):
        with project_temporary_directory() as root:
            subprocess.run(
                ["git", "init", "-q", "-b", "main"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "test"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            (root / "answers").mkdir()
            (root / "answers" / "one.html").write_text("one")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "base"],
                cwd=root,
                check=True,
            )
            base = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
            ).strip()
            (root / "_engine" / "geo").mkdir(parents=True)
            (root / "_engine" / "geo" / "generator.py").write_text("VALUE=2\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "source drift"],
                cwd=root,
                check=True,
            )
            remote = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
            ).strip()
            result = reliability.check_remote_drift(
                root,
                base,
                remote,
                root / "evidence.json",
            )
            self.assertFalse(result["publishable"])
            self.assertEqual(
                ["_engine/geo/generator.py"],
                result["critical_paths"],
            )


class RunEvidenceTests(unittest.TestCase):
    def test_evidence_never_equates_delivery_with_exposure(self):
        with project_temporary_directory() as root:
            subprocess.run(
                ["git", "init", "-q", "-b", "main"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "test"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            (root / "file.txt").write_text("content\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "base"],
                cwd=root,
                check=True,
            )
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
            ).strip()
            output = root / "evidence" / "run.json"
            env = {
                "GITHUB_EVENT_NAME": "schedule",
                "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_RUN_ID": "123",
                "GITHUB_SHA": sha,
                "GEO_JOB_STATUS": "success",
                "GEO_PUBLISHED_SHA": sha,
                "GEO_STEP_PUBLISH": "success",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                evidence = reliability.write_run_evidence(output, root)
            self.assertFalse(
                evidence["truth_contract"]["pages_deploy_is_exposure"]
            )
            self.assertFalse(
                evidence["truth_contract"]["indexnow_acceptance_is_exposure"]
            )
            self.assertEqual(f"{sha}\n", (output.parent / "published-sha.txt").read_text())


if __name__ == "__main__":
    unittest.main()
