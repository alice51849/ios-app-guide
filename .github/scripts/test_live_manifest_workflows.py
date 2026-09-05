from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


class LiveManifestWorkflowTests(unittest.TestCase):
    def workflows(self):
        for name in ("geo-daily.yml", "sov-weekly.yml"):
            source = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            yield name, source, next(iter(yaml.safe_load(source)["jobs"].values()))

    def test_all_scorecard_workflows_use_explicit_v2_runtime_evidence(self):
        for name, source, job in self.workflows():
            with self.subTest(workflow=name):
                self.assertNotIn("GEO_PUBLIC_INVENTORY_BASELINE", source)
                self.assertEqual(
                    "${{ github.workspace }}/.growth-runtime/live-app-manifest.json",
                    job["env"]["GROWTH_LIVE_MANIFEST"],
                )
                self.assertEqual(
                    "${{ github.workspace }}/.growth-runtime/outreach",
                    job["env"]["GEO_REPORTS"],
                )
                scripts = [step.get("run", "") for step in job["steps"]]
                refresh = next(index for index, script in enumerate(scripts) if "live_app_manifest.py --refresh" in script)
                coverage = next(index for index, script in enumerate(scripts) if "outreach_scorecard.py" in script)
                self.assertLess(refresh, coverage)
                self.assertIn('--output "$GROWTH_LIVE_MANIFEST"', scripts[refresh])
                self.assertNotIn("--adopt", scripts[refresh])
                subprocess.run(["bash", "-n"], input=scripts[refresh], text=True, check=True)

    def test_last_good_cache_is_scoped_to_roster_and_shared_between_workflows(self):
        prefixes = []
        for name, _, job in self.workflows():
            with self.subTest(workflow=name):
                steps = job["steps"]
                restore = next(index for index, step in enumerate(steps) if step.get("uses") == "actions/cache/restore@v4")
                refresh = next(index for index, step in enumerate(steps) if "live_app_manifest.py --refresh" in step.get("run", ""))
                save = next(index for index, step in enumerate(steps) if step.get("uses") == "actions/cache/save@v4")
                self.assertLess(restore, refresh)
                self.assertLess(refresh, save)
                self.assertEqual(".growth-runtime/live-app-manifest.json", steps[restore]["with"]["path"])
                self.assertEqual(steps[restore]["with"]["path"], steps[save]["with"]["path"])
                self.assertEqual(steps[restore]["with"]["key"], steps[save]["with"]["key"])
                prefix = steps[restore]["with"]["restore-keys"]
                self.assertIn("hashFiles('_engine/geo/live_app_manifest.json'", prefix)
                prefixes.append(prefix)
        self.assertEqual(prefixes[0], prefixes[1])

    def test_weekly_measurements_are_artifacts_not_source_commits(self):
        _, source, job = next(item for item in self.workflows() if item[0] == "sov-weekly.yml")
        self.assertNotIn("git commit", source)
        self.assertNotIn("git add", source)
        upload = next(step for step in job["steps"] if step.get("uses") == "actions/upload-artifact@v4")
        self.assertEqual(".growth-runtime/outreach", upload["with"]["path"])
        self.assertTrue(upload["with"]["include-hidden-files"])

    def test_git_add_all_ignores_runtime_but_keeps_versioned_roster(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
            (root / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
            identity = root / "_engine" / "geo" / "live_app_manifest.json"
            identity.parent.mkdir(parents=True)
            identity.write_text("{}", encoding="utf-8")
            runtime = root / ".growth-runtime"
            runtime.mkdir()
            engine_runtime = root / "_engine" / ".growth-runtime"
            engine_runtime.mkdir()
            for generation in (1, 2):
                (runtime / "live-app-manifest.json").write_text(str(generation), encoding="utf-8")
                (runtime / "outreach.json").write_text(str(generation), encoding="utf-8")
                (root / ".live_app_manifest.json").write_text(str(generation), encoding="utf-8")
                (engine_runtime / "live-app-manifest.json").write_text(str(generation), encoding="utf-8")
                subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
                tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
                self.assertEqual([".gitignore", "_engine/geo/live_app_manifest.json"], tracked)


if __name__ == "__main__":
    unittest.main()
