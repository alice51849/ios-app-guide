#!/usr/bin/env python3
"""Regression tests for bounded remote-first generated-tree publication."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / ".github" / "scripts" / "remote-first-publish.sh"


class GitPublishRaceTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parent / ".git-publish-race"
        scratch.mkdir(exist_ok=True)
        self.scratch = scratch
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=scratch)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        self.seed = self.root / "seed"
        self.worker = self.root / "worker"
        self.competitor = self.root / "competitor"

        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.origin))
        self.git(self.root, "init", "--initial-branch=main", str(self.seed))
        self.configure(self.seed)
        (self.seed / "videos").mkdir()
        (self.seed / "videos" / "browse.html").write_text(
            "base\n", encoding="utf-8"
        )
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "base")
        self.git(self.seed, "remote", "add", "origin", str(self.origin))
        self.git(self.seed, "push", "-u", "origin", "main")
        self.git(self.root, "clone", str(self.origin), str(self.worker))
        self.git(self.root, "clone", str(self.origin), str(self.competitor))
        self.configure(self.worker)
        self.configure(self.competitor)

    def tearDown(self) -> None:
        self.temp.cleanup()
        try:
            self.scratch.rmdir()
        except OSError:
            pass

    def git(
        self,
        cwd: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"git {' '.join(args)} failed in {cwd}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result

    def configure(self, repo: Path) -> None:
        self.git(repo, "config", "user.name", "Race Test")
        self.git(repo, "config", "user.email", "race@example.invalid")

    def commit_file(
        self,
        repo: Path,
        relative: str,
        content: str,
        subject: str,
    ) -> str:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.git(repo, "add", relative)
        self.git(repo, "commit", "-m", subject)
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def run_bash(
        self,
        script: str,
        *,
        expected_returncode: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(
            os.environ,
            REMOTE_FIRST_RETRY_DELAY_SECONDS="0",
            REMOTE_FIRST_TIMEOUT_SECONDS="30",
        )
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=self.worker,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            expected_returncode,
            result.returncode,
            f"{result.stdout}\n{result.stderr}",
        )
        return result

    def origin_head(self) -> str:
        return self.git(
            self.root,
            f"--git-dir={self.origin}",
            "rev-parse",
            "main",
        ).stdout.strip()

    def assert_origin_ancestor(self, ancestor: str) -> None:
        result = self.git(
            self.root,
            f"--git-dir={self.origin}",
            "merge-base",
            "--is-ancestor",
            ancestor,
            self.origin_head(),
            check=False,
        )
        self.assertEqual(0, result.returncode)

    def test_delete_recreate_vs_remote_modify_converges(self) -> None:
        path = self.worker / "videos" / "browse.html"
        path.unlink()
        self.git(self.worker, "add", "-A")
        self.git(self.worker, "commit", "-m", "delete generated browse")
        self.commit_file(
            self.worker,
            "videos/browse.html",
            "workflow-regenerated\n",
            "recreate generated browse",
        )
        remote_sha = self.commit_file(
            self.competitor,
            "videos/browse.html",
            "remote-publication\n",
            "concurrent publication",
        )
        self.git(self.competitor, "push", "origin", "main")

        script = f"""
source {shlex.quote(str(HELPER))}
reconcile_phase() {{
  grep -q 'remote-publication' videos/browse.html
  printf 'workflow-regenerated\\n' >> videos/browse.html
}}
remote_first_publish reconcile_phase origin main 5
printf 'attempts=%s\\n' "$REMOTE_FIRST_ATTEMPTS_USED"
"""
        result = self.run_bash(script)
        self.assertIn("attempts=1", result.stdout)
        self.assert_origin_ancestor(remote_sha)
        content = self.git(
            self.root,
            f"--git-dir={self.origin}",
            "show",
            "main:videos/browse.html",
        ).stdout
        self.assertIn("remote-publication", content)
        self.assertIn("workflow-regenerated", content)

    def test_remote_move_between_fetch_and_push_retries_once(self) -> None:
        self.commit_file(self.worker, "worker.txt", "worker\n", "worker content")
        competitor = shlex.quote(str(self.competitor))
        script = f"""
source {shlex.quote(str(HELPER))}
reconcile_phase() {{ :; }}
remote_first_before_push() {{
  if [ "$1" = "1" ]; then
    printf 'remote-race\\n' > {competitor}/race.txt
    git -C {competitor} add race.txt
    git -C {competitor} commit -m 'remote race'
    git -C {competitor} push origin main
  fi
}}
remote_first_publish reconcile_phase origin main 5
printf 'attempts=%s\\n' "$REMOTE_FIRST_ATTEMPTS_USED"
"""
        result = self.run_bash(script)
        self.assertIn("attempts=2", result.stdout)
        remote_sha = self.git(
            self.competitor, "rev-parse", "HEAD"
        ).stdout.strip()
        self.assert_origin_ancestor(remote_sha)
        self.assertEqual(
            "worker\n",
            self.git(
                self.root,
                f"--git-dir={self.origin}",
                "show",
                "main:worker.txt",
            ).stdout,
        )

    def test_persistent_churn_stops_after_five_without_data_loss(self) -> None:
        self.commit_file(self.worker, "worker.txt", "worker\n", "worker content")
        competitor = shlex.quote(str(self.competitor))
        script = f"""
source {shlex.quote(str(HELPER))}
reconcile_phase() {{ :; }}
remote_first_before_push() {{
  git -C {competitor} pull --ff-only origin main
  printf 'remote-%s\\n' "$1" >> {competitor}/churn.txt
  git -C {competitor} add churn.txt
  git -C {competitor} commit -m "remote churn $1"
  git -C {competitor} push origin main
}}
if remote_first_publish reconcile_phase origin main 5; then
  exit 90
fi
printf 'attempts=%s\\n' "$REMOTE_FIRST_ATTEMPTS_USED"
"""
        result = self.run_bash(script)
        self.assertIn("attempts=5", result.stdout)
        content = self.git(
            self.root,
            f"--git-dir={self.origin}",
            "show",
            "main:churn.txt",
        ).stdout
        self.assertEqual(
            "".join(f"remote-{attempt}\n" for attempt in range(1, 6)),
            content,
        )
        missing_worker = self.git(
            self.root,
            f"--git-dir={self.origin}",
            "cat-file",
            "-e",
            "main:worker.txt",
            check=False,
        )
        self.assertNotEqual(0, missing_worker.returncode)

    def test_helper_is_bounded_and_non_destructive(self) -> None:
        source = HELPER.read_text(encoding="utf-8")
        self.assertIn("attempt <= max_attempts", source)
        self.assertIn("git fetch --no-tags", source)
        self.assertIn("git merge --no-edit -X theirs", source)
        self.assertIn("git merge-base --is-ancestor", source)
        self.assertIn('git push "$remote" "HEAD:refs/heads/${branch}"', source)
        self.assertNotIn("rebase", source)
        self.assertNotIn("reset --hard", source)
        self.assertNotIn("--force", source)


if __name__ == "__main__":
    unittest.main()
