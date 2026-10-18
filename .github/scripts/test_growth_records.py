#!/usr/bin/env python3
"""growth_records.py against throwaway git repos (a bare origin plus runner clones)."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import growth_records as gr

LOG = ".github/growth/clip-posts.json"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def sh(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True,
                          capture_output=True, text=True).stdout.strip()


@contextlib.contextmanager
def inside(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        # The code under test runs like a fresh runner: no git identity anywhere, so every
        # commit or merge it makes must carry its own (as the workflows' commits do).
        bare = {k: v for k, v in os.environ.items()
                if k not in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                             "GIT_COMMITTER_EMAIL", "EMAIL")}
        bare.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        with mock.patch.dict(os.environ, bare, clear=True), \
                contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        os.chdir(old)


class Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origin = self.tmp / "origin.git"
        sh(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        seed = self.clone("seed")
        (seed / ".github/growth").mkdir(parents=True)
        (seed / LOG).write_text(json.dumps({"posts": [{"id": "p0"}]}, indent=2) + "\n")
        (seed / ".github/growth/old.json").write_text("{}\n")
        (seed / "page.html").write_text("v1\n")
        sh(seed, "add", "-A")
        sh(seed, "commit", "-q", "-m", "seed")
        sh(seed, "push", "-q", "origin", "HEAD:main")

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.tmp)])

    def clone(self, name):
        path = self.tmp / name
        sh(self.tmp, "clone", "-q", str(self.origin), str(path))
        return path

    def posts(self, ref, path=LOG):
        return [p["id"] for p in json.loads(sh(self.origin, "show", f"{ref}:{path}"))["posts"]]

    def has_branch(self, name):
        return bool(sh(self.origin, "branch", "--list", name))

    def record(self, runner, post_id, geo):
        """One workflow push loop: prepare, the workflow's own merge, git add, commit, push."""
        with inside(runner), mock.patch.object(gr, "geo_daily_active", return_value=geo):
            target = gr.prepare()
            doc = json.loads(Path(LOG).read_text())
            if post_id not in [p["id"] for p in doc["posts"]]:
                doc["posts"].append({"id": post_id})
            Path(LOG).write_text(json.dumps(doc, indent=2) + "\n")
            sh(".", "add", LOG)
            sh(".", "commit", "-q", "-m", f"record {post_id} [skip ci]")
            self.assertEqual(0, gr.push(target))
        return target


class DeferTest(Repo):
    def test_geo_running_sends_records_to_pending_and_leaves_main_alone(self):
        main_before = sh(self.origin, "rev-parse", "main")
        self.assertEqual(gr.PENDING, self.record(self.clone("r1"), "p1", geo=True))
        self.assertEqual(main_before, sh(self.origin, "rev-parse", "main"))
        self.assertEqual(["p0", "p1"], self.posts(gr.PENDING))
        # a second bot builds on the pending branch, so it sees p1 too
        self.assertEqual(gr.PENDING, self.record(self.clone("r2"), "p2", geo=True))
        self.assertEqual(["p0", "p1", "p2"], self.posts(gr.PENDING))
        self.assertEqual(main_before, sh(self.origin, "rev-parse", "main"))

    def test_overlay_lets_a_fresh_checkout_read_pending_records(self):
        self.record(self.clone("r1"), "p1", geo=True)
        runner = self.clone("r2")
        with inside(runner):
            self.assertEqual(0, gr.main(["overlay"]))
        ids = [p["id"] for p in json.loads((runner / LOG).read_text())["posts"]]
        self.assertEqual(["p0", "p1"], ids)
        self.assertEqual("", sh(runner, "status", "--porcelain"))  # "nothing posted" checks stay valid

    def test_overlay_without_pending_changes_nothing(self):
        runner = self.clone("r1")
        head = sh(runner, "rev-parse", "HEAD")
        with inside(runner):
            self.assertEqual(0, gr.main(["overlay"]))
        self.assertEqual(head, sh(runner, "rev-parse", "HEAD"))

    def test_overlay_applies_files_pending_deleted(self):
        r1 = self.clone("r1")
        with inside(r1), mock.patch.object(gr, "geo_daily_active", return_value=True):
            target = gr.prepare()
            sh(".", "rm", "-q", ".github/growth/old.json")
            sh(".", "commit", "-q", "-m", "drop")
            self.assertEqual(0, gr.push(target))
        r2 = self.clone("r2")
        with inside(r2):
            gr.main(["overlay"])
        self.assertFalse((r2 / ".github/growth/old.json").exists())

    def test_geo_idle_merges_pending_into_main_without_rewriting(self):
        old_main = sh(self.origin, "rev-parse", "main")
        self.record(self.clone("r1"), "p1", geo=True)
        pending = sh(self.origin, "rev-parse", gr.PENDING)
        self.assertEqual("main", self.record(self.clone("r2"), "p2", geo=False))
        self.assertEqual(["p0", "p1", "p2"], self.posts("main"))
        parents = sh(self.origin, "log", "-1", "--format=%P", "main").split()
        self.assertEqual([old_main, pending], parents)  # a merge commit on top of the old main
        sh(self.origin, "merge-base", "--is-ancestor", gr.PENDING, "main")
        # once merged the branch is ignored: a new checkout overlays nothing
        runner = self.clone("r3")
        head = sh(runner, "rev-parse", "HEAD")
        with inside(runner):
            gr.main(["overlay"])
        self.assertEqual(head, sh(runner, "rev-parse", "HEAD"))
        # and the next geo run reuses the branch by fast-forward
        self.assertEqual(gr.PENDING, self.record(self.clone("r4"), "p3", geo=True))
        self.assertEqual(["p0", "p1", "p2", "p3"], self.posts(gr.PENDING))

    def test_api_failure_falls_back_to_main_and_still_folds_pending_in(self):
        self.record(self.clone("r1"), "p1", geo=True)
        self.assertEqual("main", self.record(self.clone("r2"), "p2", geo=None))
        self.assertEqual(["p0", "p1", "p2"], self.posts("main"))

    def test_main_record_written_meanwhile_is_kept(self):
        self.record(self.clone("r1"), "p1", geo=True)
        # someone (a local Mac run, a fallback push) appends to main directly
        other = self.clone("other")
        doc = json.loads((other / LOG).read_text())
        doc["posts"].append({"id": "m1"})
        (other / LOG).write_text(json.dumps(doc, indent=2) + "\n")
        sh(other, "commit", "-q", "-am", "direct")
        sh(other, "push", "-q", "origin", "HEAD:main")
        runner = self.clone("r2")
        with inside(runner):
            gr.main(["overlay"])
        self.assertEqual(["p0", "m1", "p1"],
                         [p["id"] for p in json.loads((runner / LOG).read_text())["posts"]])
        self.record(self.clone("r3"), "p2", geo=False)
        self.assertEqual(["p0", "m1", "p1", "p2"], self.posts("main"))

    def test_pending_follows_main_when_main_moves_on_during_the_run(self):
        self.record(self.clone("r1"), "p1", geo=True)
        other = self.clone("other")
        (other / "page.html").write_text("v2\n")
        sh(other, "commit", "-q", "-am", "content")
        sh(other, "push", "-q", "origin", "HEAD:main")
        self.assertEqual(gr.PENDING, self.record(self.clone("r2"), "p2", geo=True))
        self.assertEqual("v2", sh(self.origin, "show", f"{gr.PENDING}:page.html"))
        self.assertEqual(["p0", "p1", "p2"], self.posts(gr.PENDING))
        self.record(self.clone("r3"), "p3", geo=False)
        self.assertEqual("v2", sh(self.origin, "show", "main:page.html"))
        self.assertEqual(["p0", "p1", "p2", "p3"], self.posts("main"))

    def test_shallow_checkout_deepens_to_find_the_fork_point(self):
        self.record(self.clone("r1"), "p1", geo=True)
        other = self.clone("other")
        for n in range(3):
            (other / "page.html").write_text(f"v{n}\n")
            sh(other, "commit", "-q", "-am", f"content {n}")
        sh(other, "push", "-q", "origin", "HEAD:main")
        runner = self.tmp / "shallow"
        sh(self.tmp, "clone", "-q", "--depth", "1", f"file://{self.origin}", str(runner))
        with inside(runner):
            self.assertEqual(0, gr.main(["overlay"]))
        self.assertEqual(["p0", "p1"], [p["id"] for p in json.loads((runner / LOG).read_text())["posts"]])

    def test_refused_push_is_reported_for_the_retry_loop(self):
        runner = self.clone("r1")
        with inside(runner), mock.patch.object(gr, "geo_daily_active", return_value=False):
            target = gr.prepare()
            (runner / LOG).write_text('{"posts": []}\n')
            sh(".", "commit", "-q", "-am", "late")
        racer = self.clone("racer")
        (racer / "page.html").write_text("race\n")
        sh(racer, "commit", "-q", "-am", "race")
        sh(racer, "push", "-q", "origin", "HEAD:main")
        with inside(runner):
            self.assertEqual(1, gr.push(target))
            self.assertEqual(2, gr.main(["push", "feed-cards"]))


class GeoStatusTest(unittest.TestCase):
    ENV = {"GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": "o/r"}

    def reply(self, runs):
        r = io.BytesIO(json.dumps({"workflow_runs": runs}).encode())
        r.__enter__ = lambda *_: r
        r.__exit__ = lambda *_: False
        return r

    def status(self, **kw):
        with mock.patch.dict(os.environ, self.ENV), contextlib.redirect_stderr(io.StringIO()) as err, \
                mock.patch("urllib.request.urlopen", **kw) as call:
            result = gr.geo_daily_active()
        return result, err.getvalue(), call

    def test_running_or_queued_is_active(self):
        for s in ("in_progress", "queued"):
            got, _, call = self.status(return_value=self.reply([{"status": s}, {"status": "completed"}]))
            self.assertIs(True, got)
        self.assertIn("/repos/o/r/actions/workflows/geo-daily.yml/runs", call.call_args[0][0].full_url)

    def test_completed_is_idle(self):
        got, _, _ = self.status(return_value=self.reply([{"status": "completed"}]))
        self.assertIs(False, got)

    def test_api_error_is_unknown_and_loud(self):
        got, err, _ = self.status(side_effect=urllib.error.URLError("down"))
        self.assertIsNone(got)
        self.assertIn("::warning::", err)

    def test_missing_token_is_unknown_and_loud(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "", "GH_TOKEN": ""}), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(gr.geo_daily_active())
        self.assertIn("::warning::", err.getvalue())


class MergeJsonTest(unittest.TestCase):
    def test_both_sides_append(self):
        base = {"posts": [{"id": 1}]}
        self.assertEqual({"posts": [{"id": 1}, {"id": 2}, {"id": 3}]},
                         gr.merge_json(base, {"posts": [{"id": 1}, {"id": 2}]},
                                       {"posts": [{"id": 1}, {"id": 3}]}))

    def test_dict_keys_from_both_sides_and_removals(self):
        base = {"a": 1, "gone": 1, "keep": {"x": 1}}
        ours = {"a": 1, "keep": {"x": 1, "y": 2}}
        theirs = {"a": 2, "gone": 1, "keep": {"x": 1, "z": 3}, "new": 1}
        self.assertEqual({"a": 2, "keep": {"x": 1, "y": 2, "z": 3}, "new": 1},
                         gr.merge_json(base, ours, theirs))

    def test_scalar_clash_takes_theirs(self):
        self.assertEqual({"n": 3}, gr.merge_json({"n": 1}, {"n": 2}, {"n": 3}))

    def test_text_conflict_takes_theirs(self):
        self.assertEqual(b"T\n", gr.merge_file("x.md", b"B\n", b"O\n", b"T\n"))


if __name__ == "__main__":
    unittest.main()
