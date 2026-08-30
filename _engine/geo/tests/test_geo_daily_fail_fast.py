from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest


GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "geo-daily.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
BOUNDED_HELPER = ROOT / ".github" / "scripts" / "bounded-resumable.sh"


def workflow_step(source: str, name: str, next_name: str) -> str:
    return source.split(f"- name: {name}", 1)[1].split(
        f"- name: {next_name}",
        1,
    )[0]


class GeoDailyFailFastContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The engine-repo mirror of this file has no .github tree; the
        # contract only exists where the workflow does.
        if not WORKFLOW.exists():
            raise unittest.SkipTest("geo-daily.yml not in this checkout")
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    @staticmethod
    def python_commands(source: str) -> list[str]:
        lines = source.splitlines()
        commands: list[str] = []
        position = 0
        while position < len(lines):
            stripped = lines[position].strip()
            if not stripped.startswith("python3 "):
                position += 1
                continue
            parts = [stripped.removesuffix("\\").strip()]
            while lines[position].rstrip().endswith("\\"):
                position += 1
                if position >= len(lines):
                    raise AssertionError("unterminated multiline Python command")
                parts.append(lines[position].strip().removesuffix("\\").strip())
            commands.append(" ".join(parts))
            position += 1
        return commands

    def assert_high_intent_closure(self, source: str) -> None:
        commands = self.python_commands(source)
        generators = [
            index for index, command in enumerate(commands)
            if "--materialize-current-inventory" in command
        ]
        closures = [
            index for index, command in enumerate(commands)
            if "--check-materialization-closure" in command
        ]
        self.assertEqual(1, len(generators))
        self.assertEqual(1, len(closures))
        generator = generators[0]
        closure = closures[0]
        self.assertLess(generator, closure)

        def next_command(name: str, after: int) -> int:
            return next(
                index
                for index in range(after + 1, closure)
                if name in commands[index]
            )

        graph = next_command("close_sitemap_graph.py", generator)
        attribution = next_command("gen_store_attribution.py", graph)
        feed = next_command("gen_feed.py", attribution)
        audit = next_command("audit_link_depth.py", feed)
        self.assertLess(audit, closure)

    def test_high_intent_routes_close_all_four_mutation_paths(self):
        segments = (
            workflow_step(
                self.source,
                "Materialize newly live app surfaces",
                "Verify zero-cost growth infrastructure",
            ),
            workflow_step(
                self.source,
                "Commit English content first (fast, before slow localization)",
                "Localize from curated dictionaries (zero-cost, no API)",
            ),
            workflow_step(
                self.source,
                "Final link and availability cleanup",
                "Verify localized output before commit",
            ),
            workflow_step(
                self.source,
                "Commit localized pages if any",
                "Unlink site dir",
            ),
        )
        self.assertEqual(4, self.source.count("--materialize-current-inventory"))
        self.assertEqual(4, self.source.count("--check-materialization-closure"))
        for segment in segments:
            self.assert_high_intent_closure(segment)

    def test_every_pages_upload_has_external_source_hard_gate(self):
        self.assertTrue(PAGES_WORKFLOW.is_file())
        source = PAGES_WORKFLOW.read_text(encoding="utf-8")
        cursor = 0
        uploads = 0
        marker = "actions/upload-pages-artifact@"
        while (upload := source.find(marker, cursor)) >= 0:
            uploads += 1
            prepare = source.rfind(
                "- name: Prepare externally bound high-intent deployment",
                0,
                upload,
            )
            self.assertGreater(prepare, -1)
            gate = source.rfind("--prepare-pages-deployment", 0, upload)
            self.assertGreater(gate, prepare)
            guarded = source[prepare:upload]
            self.assertIn(
                "GROWTH_ENGINE_DEPLOY_KEY: "
                "${{ secrets.GROWTH_ENGINE_DEPLOY_KEY }}",
                guarded,
            )
            self.assertIn("git@github.com:alice51849/00_GrowthEngine.git", guarded)
            self.assertIn("umask 077", guarded)
            self.assertIn("unset GROWTH_ENGINE_DEPLOY_KEY", guarded)
            self.assertIn("https://api.github.com/meta", guarded)
            self.assertIn("StrictHostKeyChecking=yes", guarded)
            self.assertNotIn("StrictHostKeyChecking=accept-new", guarded)
            self.assertIn('rm -f "$key_file" "$known_hosts"', guarded)
            self.assertIn("--current-source-root", guarded)
            self.assertIn("--engine-source-revision", guarded)
            self.assertIn('rm -rf "$source_dir"', guarded)
            self.assertIn("trap cleanup_growth_source EXIT", guarded)
            self.assertNotIn("uses: actions/checkout@", guarded)
            self.assertNotIn("continue-on-error: true", source[gate:upload])
            cursor = upload + len(marker)
        self.assertGreater(uploads, 0)

    def test_pages_readback_rejects_partial_or_degraded_manifests(self):
        source = PAGES_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if any(.[]; . == null)', source)
        self.assertIn('.version == 3', source)
        self.assertIn('.fallback_records == 0', source)

    def test_localization_only_tolerates_normalized_bounded_timeouts(self):
        localized = workflow_step(
            self.source,
            "Localize from curated dictionaries (zero-cost, no API)",
            "Fix EN hreflang reciprocity (declare newly-added locale versions)",
        )
        self.assertNotRegex(self.source, r"\|\|\s*(?:echo|true)\b")
        self.assertNotIn("continue-on-error:", localized)
        self.assertIn(
            'source "$GITHUB_WORKSPACE/.github/scripts/'
            'bounded-resumable.sh"',
            localized,
        )
        expected = (
            (
                'run_bounded_resumable 600 "i18n_harvest_existing"',
                "python3 i18n_harvest_existing.py",
            ),
            (
                'run_bounded_resumable 900 "new-page localization"',
                "python3 aeo_answers_i18n.py",
            ),
            (
                'run_bounded_resumable 1200 "refresh localization"',
                "python3 aeo_answers_i18n.py",
            ),
        )
        self.assertEqual(3, localized.count("run_bounded_resumable "))
        for invocation, command in expected:
            with self.subTest(invocation=invocation):
                self.assertIn(invocation, localized)
                self.assertIn(command, localized)
        self.assertNotRegex(localized, r"(?m)^\s+timeout\s")
        self.assertIn("python3 l10n_coverage.py --sample 40", localized)

    def test_unbounded_localization_commands_fail_closed(self):
        for command in (
            "python3 l10n_coverage.py",
            "python3 fix_en_hreflang.py",
            "python3 add_related_answers.py",
        ):
            with self.subTest(command=command):
                occurrences = [
                    line.strip()
                    for line in self.source.splitlines()
                    if command in line
                ]
                self.assertTrue(occurrences)
                self.assertTrue(
                    all("||" not in line for line in occurrences),
                    occurrences,
                )

    def test_parallel_full_suites_preserve_specialized_and_final_gates(self):
        zero_cost = workflow_step(
            self.source,
            "Verify zero-cost growth infrastructure",
            "Rebuild availability-dependent surfaces",
        )
        self.assertIn(
            "python3 _engine/geo/parallel_unittest.py --jobs 3",
            zero_cost,
        )
        self.assertIn(
            "-s _engine/social/tests",
            zero_cost,
        )
        self.assertIn(
            '-p "test_standard_site.py"',
            zero_cost,
        )
        self.assertNotIn("-s _engine/geo/tests", zero_cost)

        english = self.source.split("reconcile_english_phase() {", 1)[1].split(
            "export REMOTE_FIRST_RECONCILE_MESSAGE",
            1,
        )[0]
        self.assertIn(
            "python3 _engine/geo/parallel_unittest.py --jobs 3",
            english,
        )
        self.assertNotIn("python3 -m unittest discover", english)
        self.assertEqual(
            4,
            self.source.count(
                "python3 _engine/geo/parallel_unittest.py --jobs 3"
            ),
        )
        self.assertNotRegex(
            self.source,
            r"parallel_unittest\.py\s+--jobs\s+(?:[4-9]|\d{2,})",
        )

        final_gate = workflow_step(
            self.source,
            "Verify localized output before commit",
            "Commit localized pages if any",
        )
        prepare = final_gate.index("verified_tree.py prepare")
        tests = final_gate.index("parallel_unittest.py --jobs 3")
        seal = final_gate.index("verified_tree.py seal")
        self.assertLess(prepare, tests)
        self.assertLess(tests, seal)


class BoundedResumableExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not BOUNDED_HELPER.exists():
            raise unittest.SkipTest("bounded-resumable.sh not in this checkout")

    def run_sequence(
        self,
        command: list[str],
        *,
        # Generous by default: the child processes here exit on their own the
        # instant they start, so the bound only matters as a safety net. A
        # tight 2s bound turned real signal exits into normalized timeouts on
        # loaded CI runners (python3 startup alone blew the budget), which
        # made rc-139 look like rc-0 (2026-08-30 flake).
        seconds: float = 30,
    ) -> subprocess.CompletedProcess[str]:
        shell = "\n".join(
            (
                "set -euo pipefail",
                "ulimit -c 0",
                f"source {shlex.quote(str(BOUNDED_HELPER))}",
                "run_bounded_resumable "
                f"{seconds} fixture {shlex.join(command)}",
                'echo "FINAL_FULL_GATE"',
            )
        )
        environment = dict(os.environ)
        environment["GITHUB_WORKSPACE"] = str(ROOT)
        return subprocess.run(
            ["bash", "-c", shell],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def python(self, source: str) -> list[str]:
        return [sys.executable, "-c", source]

    def test_exit_zero_reaches_final_gate(self):
        result = self.run_sequence(self.python("raise SystemExit(0)"))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("FINAL_FULL_GATE", result.stdout)

    def test_normalized_timeout_124_reaches_final_gate(self):
        result = self.run_sequence(
            self.python("import time; time.sleep(5)"),
            seconds=0.05,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("normalized exit 124", result.stdout)
        self.assertIn("FINAL_FULL_GATE", result.stdout)

    def test_explicit_exit_124_reaches_final_gate(self):
        result = self.run_sequence(self.python("raise SystemExit(124)"))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("normalized exit 124", result.stdout)
        self.assertIn("FINAL_FULL_GATE", result.stdout)

    def test_exit_one_stops_before_final_gate(self):
        result = self.run_sequence(self.python("raise SystemExit(1)"))
        self.assertEqual(1, result.returncode)
        self.assertNotIn("FINAL_FULL_GATE", result.stdout)

    def test_sigkill_137_stops_before_final_gate(self):
        result = self.run_sequence(
            self.python("import os, signal; os.kill(os.getpid(), signal.SIGKILL)")
        )
        self.assertEqual(137, result.returncode)
        self.assertNotIn("FINAL_FULL_GATE", result.stdout)

    def test_sigterm_is_not_treated_as_timeout(self):
        result = self.run_sequence(
            self.python("import os, signal; os.kill(os.getpid(), signal.SIGTERM)")
        )
        self.assertEqual(143, result.returncode)
        self.assertNotIn("FINAL_FULL_GATE", result.stdout)

    def test_segfault_139_stops_before_final_gate(self):
        result = self.run_sequence(
            self.python("import os, signal; os.kill(os.getpid(), signal.SIGSEGV)")
        )
        self.assertEqual(139, result.returncode)
        self.assertNotIn("FINAL_FULL_GATE", result.stdout)

    def test_unrelated_app_value_error_stops_immediately(self):
        result = self.run_sequence(
            self.python(
                "raise ValueError("
                "'translation names an unrelated portfolio app')"
            )
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("unrelated portfolio app", result.stderr)
        self.assertNotIn("FINAL_FULL_GATE", result.stdout)


if __name__ == "__main__":
    unittest.main()
