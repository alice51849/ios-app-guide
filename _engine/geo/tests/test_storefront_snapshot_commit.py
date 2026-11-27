"""geo-daily commits the storefront snapshot alone before the route suites.

11-25 ruling 2307 item 1: when the route tests are red the run publishes no
routes, but the re-fetched ``.appstore_storefront_state.json`` (with its
readback-confirmed ``zero_since``) must still reach main, so a listing that
newly became free keeps its clock across two geo-daily runs instead of
restarting it every run.  These tests replay that with real git repos and the
real refresher (only the Apple lookup and the clock are faked).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_store_storefronts as stores  # noqa: E402
import check_storefront_snapshot as checker  # noqa: E402
import commit_storefront_snapshot as committer  # noqa: E402
import refresh_storefront_availability as refresher  # noqa: E402
if str(GEO / "tests") not in sys.path:
    sys.path.insert(0, str(GEO / "tests"))
# Module import only (no TestCase bound here), so its tests do not run twice.
import test_alternatives_i18n as stale_guard  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


APP_KEY = "lumibopomofo"
APP_ID = str(APPSTORE[APP_KEY])
ZERO = {"price": "0", "formatted": "免費"}
PAID = {"price": "90", "formatted": "$90.00"}
T0 = dt.datetime(2026, 11, 26, 1, 23, tzinfo=dt.timezone.utc)
ROUTE = "routes/metro.html"


def _iso(moment: dt.datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _refresh(checkout: Path, at: dt.datetime, reading=ZERO, *, force=False) -> None:
    """The real refresher; only Apple's lookup and the clock are faked."""

    def lookup(ids, country):
        return {
            str(app_id): {
                "price": float(reading["price"]),
                "currency": "TWD",
                "formattedPrice": reading["formatted"],
            }
            for app_id in ids
        }

    with mock.patch.object(refresher, "live_app_keys", return_value={APP_KEY}), \
            mock.patch.object(refresher, "_lookup_country_records", side_effect=lookup), \
            mock.patch.object(refresher, "_utc_now", return_value=at):
        refresher.refresh(checkout, force=force)


class _Repos(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="snapshot-commit-")
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        self.git(self.root, "init", "-q", "--bare", "--initial-branch=main", str(self.origin))
        seed = self.clone("seed")
        (seed / "routes").mkdir()
        (seed / ROUTE).write_text("route v1\n", encoding="utf-8")
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-q", "-m", "base")
        self.git(seed, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.runs = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=str(cwd), text=True, capture_output=True, check=False
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)}: {result.stderr}")
        return result.stdout

    def clone(self, name: str) -> Path:
        path = self.root / name
        if (self.origin / "HEAD").exists() and self.git(self.origin, "branch", "--list", "main"):
            self.git(self.root, "clone", "-q", "--branch", "main", str(self.origin), str(path))
        else:
            self.git(self.root, "init", "-q", "--initial-branch=main", str(path))
            self.git(path, "remote", "add", "origin", str(self.origin))
        self.git(path, "config", "user.name", "Snapshot Test")
        self.git(path, "config", "user.email", "snapshot@example.invalid")
        self.git(path, "config", "commit.gpgsign", "false")
        return path

    def refresh(self, checkout: Path, at: dt.datetime, reading=ZERO, *, force=False):
        _refresh(checkout, at, reading, force=force)

    def geo_daily_run(self, at: dt.datetime, *, snapshot_step: bool) -> tuple[Path, str]:
        """One geo-daily run whose route suite is red (no English commit)."""
        self.runs += 1
        checkout = self.clone(f"run{self.runs}")
        self.refresh(checkout, at)
        outcome = "skipped"
        if snapshot_step:
            outcome = committer.publish(checkout, retry_delay=0, now=_iso(at))
        # Routes were regenerated, then the full suite went red: the run stops
        # before "Commit English content first", so nothing else is committed.
        (checkout / ROUTE).write_text(f"route v{self.runs + 1}\n", encoding="utf-8")
        return checkout, outcome

    def origin_snapshot(self) -> dict:
        reader = self.clone(f"reader{self.runs}")
        return json.loads((reader / stores.STATE_FILE).read_text(encoding="utf-8"))


class ZeroSinceSurvivesRedRouteRunsTests(_Repos):
    """Judgement proof for 11-29: zero_since kept across two red-route runs."""

    def test_new_zero_keeps_zero_since_across_two_red_route_runs(self):
        first, outcome = self.geo_daily_run(T0, snapshot_step=True)
        self.assertEqual("pushed", outcome)
        # The caller's checkout is untouched: HEAD is still the base commit and
        # the snapshot stays in the working tree; routes stay unpublished.
        self.assertEqual(["base"], self.git(first, "log", "--format=%s").split("\n")[:-1])
        self.assertIn(stores.STATE_FILE, self.git(first, "status", "--porcelain"))
        self.assertIn(ROUTE, self.git(first, "status", "--porcelain"))
        self.assertEqual(_iso(T0), self.origin_snapshot()["details"]["tw"][APP_ID]["zero_since"])

        # Second run 6 h later: snapshot still fresh, refresh skipped, nothing to commit.
        _, outcome = self.geo_daily_run(T0 + dt.timedelta(hours=6), snapshot_step=True)
        self.assertEqual("unchanged", outcome)

        # Third run after the 20 h freshness window: real re-fetch.
        later = T0 + dt.timedelta(hours=21)
        third, outcome = self.geo_daily_run(later, snapshot_step=True)
        self.assertEqual("pushed", outcome)
        published = self.origin_snapshot()
        self.assertEqual(_iso(T0), published["details"]["tw"][APP_ID]["zero_since"])
        self.assertEqual(_iso(later), published["checked_at"])
        loaded = stores.load_storefront_details(third, now=later)
        self.assertEqual("0", loaded["tw"][APP_ID]["price"])
        # Routes were never published by any of the red runs.
        reader = self.clone("routes-reader")
        self.assertEqual("route v1\n", (reader / ROUTE).read_text(encoding="utf-8"))
        subjects = self.git(reader, "log", "--format=%s").splitlines()
        self.assertEqual([committer.MESSAGE, committer.MESSAGE, "base"], subjects)

    def test_without_the_step_the_zero_clock_restarts_every_run(self):
        # Control: the old all-or-nothing commit drops the snapshot on red.
        self.geo_daily_run(T0, snapshot_step=False)
        later = T0 + dt.timedelta(hours=21)
        checkout, _ = self.geo_daily_run(later, snapshot_step=False)
        detail = json.loads(
            (checkout / stores.STATE_FILE).read_text(encoding="utf-8")
        )["details"]["tw"][APP_ID]
        self.assertEqual(_iso(later), detail["zero_since"])
        self.assertNotIn(APP_ID, stores.load_storefront_details(checkout, now=later)["tw"])


class SnapshotStepGuardTests(_Repos):
    def test_red_format_check_commits_nothing(self):
        checkout = self.clone("red")
        self.refresh(checkout, T0)
        state = checkout / stores.STATE_FILE
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["details"]["tw"][APP_ID]["zero_since"] = _iso(T0 + dt.timedelta(hours=1))
        state.write_text(json.dumps(payload), encoding="utf-8")
        head = self.git(checkout, "rev-parse", "HEAD")
        with mock.patch("builtins.print"):
            self.assertEqual("red", committer.publish(checkout, retry_delay=0, now=_iso(T0)))
        self.assertEqual(head, self.git(checkout, "rev-parse", "HEAD"))
        self.assertEqual(["base"], self.git(self.origin, "log", "--format=%s", "main").split("\n")[:-1])

    def test_moved_main_gets_a_one_file_commit_on_its_tip(self):
        checkout = self.clone("worker")
        competitor = self.clone("competitor")
        (competitor / "other.txt").write_text("theirs\n", encoding="utf-8")
        self.git(competitor, "add", "-A")
        self.git(competitor, "commit", "-q", "-m", "foreign")
        self.git(competitor, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.refresh(checkout, T0)
        (checkout / ROUTE).write_text("unverified route\n", encoding="utf-8")
        self.assertEqual("pushed", committer.publish(checkout, retry_delay=0, now=_iso(T0)))
        reader = self.clone("reader")
        self.assertEqual("theirs\n", (reader / "other.txt").read_text(encoding="utf-8"))
        self.assertEqual("route v1\n", (reader / ROUTE).read_text(encoding="utf-8"))
        changed = self.git(reader, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual([stores.STATE_FILE], changed)
        self.assertNotIn("snapshot-wt-", self.git(checkout, "worktree", "list", "--porcelain"))

    def test_snapshot_changed_on_main_by_someone_else_is_not_overwritten(self):
        seed = self.clone("first")
        self.refresh(seed, T0, PAID)
        self.assertEqual("pushed", committer.publish(seed, retry_delay=0, now=_iso(T0)))
        checkout = self.clone("worker")
        person = self.clone("person")
        state = person / stores.STATE_FILE
        state.write_text(state.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.git(person, "commit", "-q", "-am", "manual snapshot edit")
        self.git(person, "push", "-q", "origin", "HEAD:refs/heads/main")
        later = T0 + dt.timedelta(hours=21)
        self.refresh(checkout, later, PAID)
        with mock.patch("builtins.print"):
            self.assertEqual("not-pushed", committer.publish(checkout, retry_delay=0, now=_iso(later)))
        self.assertEqual(
            "manual snapshot edit",
            self.git(self.origin, "log", "-1", "--format=%s", "main").strip(),
        )


class FailedPushKeepsOldBehaviourTests(_Repos):
    def test_failed_push_leaves_the_snapshot_for_the_later_commit_step(self):
        checkout = self.clone("worker")
        self.git(checkout, "remote", "set-url", "--push", "origin", str(self.root / "missing.git"))
        self.refresh(checkout, T0)
        head = self.git(checkout, "rev-parse", "HEAD")
        with mock.patch("builtins.print"):
            outcome = committer.publish(checkout, attempts=2, retry_delay=0, now=_iso(T0))
        self.assertEqual("not-pushed", outcome)
        # Nothing committed or staged locally: exactly the pre-step state.
        self.assertEqual(head, self.git(checkout, "rev-parse", "HEAD"))
        self.assertEqual("", self.git(checkout, "diff", "--cached", "--name-only"))
        self.assertIn(stores.STATE_FILE, self.git(checkout, "status", "--porcelain"))
        # Routes green, nothing else changed: the English step's `git add -A`
        # still sees the snapshot and publishes it, as before this step existed.
        self.git(checkout, "remote", "set-url", "--push", "origin", str(self.origin))
        self.git(checkout, "add", "-A")
        self.assertEqual([stores.STATE_FILE], self.git(checkout, "diff", "--cached", "--name-only").split())
        self.git(checkout, "commit", "-q", "-m", "Daily GEO content: new answer pages + refreshed sitemaps")
        self.git(checkout, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.assertEqual(_iso(T0), self.origin_snapshot()["details"]["tw"][APP_ID]["zero_since"])

    def test_after_a_pushed_snapshot_the_later_merge_is_clean(self):
        checkout, outcome = self.geo_daily_run(T0, snapshot_step=True)
        self.assertEqual("pushed", outcome)
        self.git(checkout, "add", "-A")
        self.git(checkout, "commit", "-q", "-m", "english")
        self.git(checkout, "fetch", "-q", "origin", "main")
        self.git(checkout, "merge", "-q", "--no-edit", "-X", "theirs", "FETCH_HEAD")
        self.assertEqual("", self.git(checkout, "diff", "FETCH_HEAD", "--", stores.STATE_FILE))


class TrackingRefUntouchedTests(_Repos):
    """11-27 run 45926703662: our own push must not make the checkout look stale."""

    def behind(self, checkout: Path) -> int:
        with mock.patch.dict("os.environ", {"ALTERNATIVES_GUIDE_BASE_REF": ""}):
            return stale_guard.AlternativesExact50Tests._guide_commits_behind(checkout)

    def test_pushed_snapshot_leaves_origin_main_and_the_stale_guard_at_zero(self):
        checkout = self.clone("worker")
        before = self.git(checkout, "rev-parse", "refs/remotes/origin/main")
        self.refresh(checkout, T0)
        with mock.patch("builtins.print"):
            self.assertEqual("pushed", committer.publish(checkout, retry_delay=0, now=_iso(T0)))
        # origin really moved, the caller's tracking ref did not.
        self.assertEqual(
            committer.MESSAGE,
            self.git(self.origin, "log", "-1", "--format=%s", "main").strip(),
        )
        self.assertEqual(before, self.git(checkout, "rev-parse", "refs/remotes/origin/main"))
        self.assertEqual("0", self.git(checkout, "rev-list", "--count", "HEAD..origin/main").strip())
        self.assertEqual(0, self.behind(checkout))

    def test_fetch_without_push_does_not_move_origin_main_either(self):
        checkout = self.clone("worker")
        competitor = self.clone("competitor")
        (competitor / "other.txt").write_text("theirs\n", encoding="utf-8")
        self.git(competitor, "add", "-A")
        self.git(competitor, "commit", "-q", "-m", "foreign")
        self.git(competitor, "push", "-q", "origin", "HEAD:refs/heads/main")
        before = self.git(checkout, "rev-parse", "refs/remotes/origin/main")
        self.git(checkout, "remote", "set-url", "--push", "origin", str(self.root / "missing.git"))
        self.refresh(checkout, T0)
        with mock.patch("builtins.print"):
            self.assertEqual(
                "not-pushed",
                committer.publish(checkout, attempts=1, retry_delay=0, now=_iso(T0)),
            )
        self.assertEqual(before, self.git(checkout, "rev-parse", "refs/remotes/origin/main"))

    def test_guard_still_catches_a_checkout_that_really_fell_behind(self):
        checkout = self.clone("worker")
        self.refresh(checkout, T0)
        with mock.patch("builtins.print"):
            self.assertEqual("pushed", committer.publish(checkout, retry_delay=0, now=_iso(T0)))
        self.assertEqual(0, self.behind(checkout))
        # A plain fetch (what any later step or person does) exposes the real lag.
        self.git(checkout, "fetch", "-q", "origin")
        self.assertEqual(1, self.behind(checkout))
        probe = stale_guard.AlternativesExact50Tests(
            "test_explicit_stack_binding_rejects_mutable_or_unknown_base"
        )
        with mock.patch.object(
            stale_guard.AlternativesExact50Tests, "_production_guide", return_value=checkout
        ), mock.patch.dict("os.environ", {"ALTERNATIVES_GUIDE_BASE_REF": ""}), \
                self.assertRaisesRegex(AssertionError, "落後"):
            probe._require_production_guide()


class SnapshotFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.pages = Path(self.temp.name)
        _refresh(self.pages, T0)
        self.payload = json.loads((self.pages / stores.STATE_FILE).read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def problems(self, payload=None, previous=None, now=T0):
        return checker.check_snapshot(payload or self.payload, previous=previous, now=now)

    def test_fresh_refresher_output_is_clean(self):
        self.assertEqual([], self.problems())

    def test_stale_or_future_checked_at_is_red(self):
        self.assertTrue(self.problems(now=T0 + dt.timedelta(hours=37)))
        self.assertTrue(self.problems(now=T0 - dt.timedelta(hours=1)))

    def test_lost_paid_history_is_red(self):
        previous = json.loads(json.dumps(self.payload))
        previous["paid_seen"] = {"tw": [APP_ID]}
        self.assertTrue(any("paid_seen.tw" in line for line in self.problems(previous=previous)))

    def test_reset_zero_since_is_red(self):
        previous = json.loads(json.dumps(self.payload))
        previous["details"]["tw"][APP_ID]["zero_since"] = _iso(T0 - dt.timedelta(days=1))
        self.assertTrue(any("zero_since 被重設" in line for line in self.problems(previous=previous)))

    def test_zero_since_without_confirmed_zero_is_red(self):
        broken = json.loads(json.dumps(self.payload))
        broken["details"]["tw"][APP_ID]["price_readback"] = "90"
        self.assertTrue(any("zero_since" in line for line in self.problems(broken)))

    def test_shape_errors_are_red(self):
        for mutate in (
            lambda p: p.update(version=1),
            lambda p: p.update(app_count=99),
            lambda p: p.update(storefronts=["tw"]),
            lambda p: p["countries"].update(xx=[]),
            lambda p: p["details"]["tw"][APP_ID].update(price="free"),
            lambda p: p["details"]["tw"][APP_ID].update(rating_value=4.5),
            lambda p: p.pop("paid_seen"),
        ):
            broken = json.loads(json.dumps(self.payload))
            mutate(broken)
            with self.subTest(mutate=mutate):
                self.assertTrue(self.problems(broken))

    def test_cli_reads_the_pages_snapshot(self):
        with mock.patch("builtins.print"):
            self.assertEqual(0, checker.main(["--pages", str(self.pages), "--now", _iso(T0)]))
            self.assertEqual(1, checker.main(["--pages", str(self.pages / "missing")]))


if __name__ == "__main__":
    unittest.main()
