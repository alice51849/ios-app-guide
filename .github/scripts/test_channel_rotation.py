#!/usr/bin/env python3
"""Tests for channel_rotation.py and the main-post gates (no network).

The holdout plan (00_GrowthEngine reports/holdout/channel_rotation_plan.json, copied byte for byte) takes one
channel off per UTC week. A main post to that channel is skipped with a ::notice:: and the run stays green, the
other channels post as usual, and a missing or altered plan pauses nothing.
"""
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import channel_rotation as CR  # noqa: E402

# The digest the plan was registered with in 00_GrowthEngine (reports/holdout/channel_rotation_plan.json).
REGISTERED_DIGEST = "371921137339d5960665c30233af4708e622f543172d34cd5f6df7473dc0875d"
GE_PLAN = Path(__file__).resolve().parents[3] / "00_GrowthEngine" / "reports" / "holdout" / "channel_rotation_plan.json"
TELEGRAM_WEEK = dt.date(2026, 10, 28)    # week 1: 2026-10-26..2026-11-02 telegram off
INSTAGRAM_WEEK = dt.date(2026, 11, 3)    # week 2: instagram off
BLUESKY_WEEK = dt.date(2026, 11, 10)     # week 3: bluesky off
THREADS_WEEK = dt.date(2026, 11, 24)     # week 5: threads off
BEFORE = dt.date(2026, 10, 25)
PLAN = CR.load_plan()


def on(day):
    return mock.patch.object(CR, "today_utc", return_value=day)


class PlanTest(unittest.TestCase):
    def test_the_copy_is_the_registered_plan(self):
        plan = CR.load_plan()
        self.assertEqual(REGISTERED_DIGEST, plan["digest"])
        self.assertEqual(CR._digest({k: v for k, v in plan.items() if k != "digest"}), plan["digest"])
        self.assertEqual(list(CR.ROTATION_CHANNELS), plan["channels"])
        self.assertEqual(15, len(plan["weeks"]))
        if GE_PLAN.exists():  # next to a 00_GrowthEngine checkout: the copy must be byte for byte
            self.assertEqual(GE_PLAN.read_bytes(), CR.PLAN_PATH.read_bytes())

    def test_weeks_are_utc_dates_with_an_exclusive_end(self):
        plan = CR.load_plan()
        self.assertIsNone(CR.off_channel(BEFORE, plan))
        self.assertEqual("telegram", CR.off_channel(dt.date(2026, 10, 26), plan))
        self.assertEqual("telegram", CR.off_channel(dt.date(2026, 11, 1), plan))
        self.assertEqual("instagram", CR.off_channel(dt.date(2026, 11, 2), plan))
        self.assertIsNone(CR.off_channel(dt.date(2027, 2, 8), plan))
        self.assertTrue(CR.is_paused("telegram", TELEGRAM_WEEK, plan))
        self.assertFalse(CR.is_paused("threads", TELEGRAM_WEEK, plan))
        for never in ("web", "reply_scout", "link_backfill", "outreach"):
            self.assertNotIn(never, {w["off"] for w in plan["weeks"]})

    def test_a_missing_or_altered_plan_pauses_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        altered = json.loads(CR.PLAN_PATH.read_text(encoding="utf-8"))
        altered["weeks"][0]["off"] = "threads"
        (tmp / "altered.json").write_text(json.dumps(altered), encoding="utf-8")
        (tmp / "broken.json").write_text("{not json", encoding="utf-8")
        for path in (tmp / "missing.json", tmp / "altered.json", tmp / "broken.json"):
            with self.subTest(path=path.name), mock.patch.object(CR, "PLAN_PATH", path), \
                    mock.patch.object(CR.load_plan, "__defaults__", (path,)), on(TELEGRAM_WEEK):
                with self.assertRaises((OSError, ValueError)):
                    CR.load_plan()
                self.assertFalse(CR.is_paused("telegram", TELEGRAM_WEEK))
                self.assertFalse(CR.is_paused("threads", TELEGRAM_WEEK))
                self.assertIsNone(CR.paused_week("telegram"))
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertFalse(CR.paused_notice("telegram"))
                self.assertEqual("", out.getvalue())

    def test_the_notice_names_the_channel_and_its_week(self):
        out = io.StringIO()
        with on(TELEGRAM_WEEK), redirect_stdout(out):
            self.assertTrue(CR.paused_notice("telegram"))
            self.assertFalse(CR.paused_notice("threads"))
        self.assertEqual("::notice::channel rotation holdout: telegram paused 2026-10-26..2026-11-02\n", out.getvalue())

    def test_check_cli_writes_the_step_output_and_exits_zero(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        gh_out = tmp / "out"
        with on(TELEGRAM_WEEK), mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_out)}), redirect_stdout(io.StringIO()):
            self.assertEqual(0, CR.main(["check", "telegram"]))
            self.assertEqual(0, CR.main(["check", "threads"]))
        self.assertEqual("paused=true\npaused=false\n", gh_out.read_text())

    def test_paused_within_covers_an_evidence_window_that_reaches_into_the_week(self):
        utc = dt.timezone.utc
        self.assertIsNotNone(CR.paused_within("telegram", dt.datetime(2026, 10, 26, 0, 41, tzinfo=utc), 30))
        # the Monday after the week: a 30 h window still reaches its last Sunday
        self.assertIsNotNone(CR.paused_within("telegram", dt.datetime(2026, 11, 2, 0, 41, tzinfo=utc), 30))
        self.assertIsNone(CR.paused_within("telegram", dt.datetime(2026, 11, 3, 12, 41, tzinfo=utc), 30))
        self.assertIsNone(CR.paused_within("threads", dt.datetime(2026, 10, 28, 12, 0, tzinfo=utc), 24))


class ClipPostsGateTest(unittest.TestCase):
    def run_main(self, channel, day):
        import clip_posts
        with on(day), mock.patch.object(sys, "argv", ["clip_posts.py", channel, "--slot", "1"]), \
                mock.patch.object(clip_posts, "CLIPS", mock.Mock(exists=lambda: True)), \
                mock.patch.object(clip_posts, "load", return_value={}), \
                mock.patch.object(clip_posts, "scheduled", return_value=None) as scheduled, \
                redirect_stdout(io.StringIO()) as out:
            rc = clip_posts.main()
        return rc, scheduled, out.getvalue()

    def test_the_off_channel_skips_green_and_the_others_post(self):
        rc, scheduled, out = self.run_main("telegram", TELEGRAM_WEEK)
        self.assertEqual(0, rc)
        scheduled.assert_not_called()
        self.assertIn("::notice::channel rotation holdout: telegram paused", out)
        for channel in ("instagram", "threads"):
            rc, scheduled, out = self.run_main(channel, TELEGRAM_WEEK)
            self.assertEqual(0, rc)
            scheduled.assert_called_once()
            self.assertNotIn("channel rotation", out)

    def test_outside_the_experiment_every_channel_posts(self):
        for channel in ("telegram", "instagram", "threads"):
            rc, scheduled, _ = self.run_main(channel, BEFORE)
            scheduled.assert_called_once()


class CardLoopGateTest(unittest.TestCase):
    """countdown_cards / utility_cards post one card to several channels: only the off channel sits out."""

    def run_countdown(self, day):
        import countdown_cards as C
        e = C.EVENTS[0]
        calls = []
        with on(day), mock.patch.object(CR, "load_plan", return_value=PLAN), \
                mock.patch.object(sys, "argv", ["c", "post", "--card", "x.jpg"]), \
                mock.patch.object(C.Path, "read_text",
                                  return_value='{"event": "%s", "locale": "%s", "caption": "c"}' % (e["id"], e["locale"])), \
                mock.patch.object(C, "qa_problems", return_value=[]), \
                mock.patch.object(C, "post_telegram", side_effect=lambda *a: calls.append("telegram")), \
                mock.patch.object(C, "post_threads", side_effect=lambda *a: calls.append("threads")), \
                mock.patch.object(C, "post_instagram", side_effect=lambda *a: calls.append("instagram")), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(0, C.main())
        return calls

    def test_countdown(self):
        self.assertEqual(["threads", "instagram"], self.run_countdown(TELEGRAM_WEEK))
        self.assertEqual(["telegram", "instagram"], self.run_countdown(THREADS_WEEK))
        self.assertEqual(["telegram", "threads"], self.run_countdown(INSTAGRAM_WEEK))
        self.assertEqual(["telegram", "threads", "instagram"], self.run_countdown(BEFORE))
        self.assertEqual(["telegram", "threads", "instagram"], self.run_countdown(BLUESKY_WEEK))

    def run_utility(self, day):
        import utility_cards as U
        calls = []
        with on(day), mock.patch.object(CR, "load_plan", return_value=PLAN), \
                mock.patch.object(sys, "argv", ["u", "post", "--card", "x.jpg"]), \
                mock.patch.object(U.Path, "read_text", return_value='{"key": "k", "caption": "c"}'), \
                mock.patch.object(U, "card_from_meta", return_value={}), \
                mock.patch.object(U, "qa_problems", return_value=[]), \
                mock.patch.object(U, "post_telegram", side_effect=lambda *a: calls.append("telegram")), \
                mock.patch.object(U, "post_instagram", side_effect=lambda *a: calls.append("instagram")), \
                mock.patch.object(U, "post_threads", side_effect=lambda *a: calls.append("threads")), \
                mock.patch("clip_progress.record_post"), redirect_stdout(io.StringIO()):
            self.assertEqual(0, U.main())
        return calls

    def test_utility(self):
        self.assertEqual(["instagram", "threads"], self.run_utility(TELEGRAM_WEEK))
        self.assertEqual(["telegram", "instagram"], self.run_utility(THREADS_WEEK))
        self.assertEqual(["telegram", "instagram", "threads"], self.run_utility(BEFORE))


class ThreadsGateTest(unittest.TestCase):
    def test_publish_linked_posts_no_new_top_level_post_in_the_threads_week(self):
        import threads_post as T
        with on(THREADS_WEEK), mock.patch.object(T.DL, "threads_reply_problems", return_value=[]), \
                mock.patch.object(T.threads_cap, "account_status", side_effect=AssertionError("no cap read")), \
                mock.patch.object(T, "publish_post", side_effect=AssertionError("must not post")), \
                redirect_stdout(io.StringIO()) as out:
            result = T.publish_linked("t", "u", "text", "links", "https://apps.apple.com/app/id1",
                                      find=lambda *a: None)
        self.assertEqual((None, True), tuple(result))  # a skip, the step stays green
        self.assertIn("::notice::channel rotation holdout: threads paused", out.getvalue())

    def test_a_link_reply_under_a_post_already_up_is_never_held(self):
        import threads_post as T
        with on(THREADS_WEEK), mock.patch.object(T.DL, "threads_reply_problems", return_value=[]), \
                mock.patch.object(T, "publish_link_reply", return_value="r1") as reply, \
                redirect_stdout(io.StringIO()):
            result = T.publish_linked("t", "u", "text", "links", "https://apps.apple.com/app/id1",
                                      find=lambda *a: "p1", find_reply=lambda *a: None)
        reply.assert_called_once()
        self.assertEqual(("p1", True), tuple(result))

    def test_publish_linked_posts_outside_the_threads_week(self):
        import threads_post as T
        with on(TELEGRAM_WEEK), mock.patch.object(T.DL, "threads_reply_problems", return_value=[]), \
                mock.patch.object(T.threads_cap, "account_status", return_value=T.threads_cap.ROOM), \
                mock.patch.object(T, "publish_post", return_value="p9") as post, \
                mock.patch.object(T, "publish_link_reply", return_value="r9"), redirect_stdout(io.StringIO()):
            result = T.publish_linked("t", "u", "text", "links", "https://apps.apple.com/app/id1",
                                      find=lambda *a: None)
        post.assert_called_once()
        self.assertEqual(("p9", True), tuple(result))

    def test_publish_text(self):
        import threads_post as T
        with on(THREADS_WEEK), mock.patch.object(T, "publish_post", side_effect=AssertionError("must not post")), \
                redirect_stdout(io.StringIO()):
            self.assertIsNone(T.publish_text("t", "u", "text"))
        with on(BEFORE), mock.patch.object(T.threads_cap, "account_status", return_value=T.threads_cap.ROOM), \
                mock.patch.object(T, "publish_post", return_value="p1"):
            self.assertEqual("p1", T.publish_text("t", "u", "text"))


class TelegramGateTest(unittest.TestCase):
    def run_main(self, day):
        import telegram_post as TP
        with on(day), mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "chat"}), \
                mock.patch.object(TP, "production_context", return_value={"source_sha": "x"}), \
                mock.patch.object(TP, "load_pool", side_effect=RuntimeError("reached the send path")) as pool, \
                redirect_stdout(io.StringIO()):
            try:
                rc = TP.main([])
            except RuntimeError:
                rc = "sent"
        return rc, pool

    def test_the_telegram_week_skips_green(self):
        rc, pool = self.run_main(TELEGRAM_WEEK)
        self.assertEqual(0, rc)
        pool.assert_not_called()

    def test_other_weeks_reach_the_send_path(self):
        for day in (BEFORE, THREADS_WEEK):
            rc, pool = self.run_main(day)
            self.assertEqual("sent", rc)

    def test_portfolio(self):
        import portfolio_daily as P
        for platform, day in (("telegram", TELEGRAM_WEEK), ("threads", THREADS_WEEK)):
            with on(day), mock.patch.object(P, "already_published_today", side_effect=AssertionError("reached")), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(0, P.main(["--platform", platform]))
        with on(TELEGRAM_WEEK), mock.patch.object(P, "already_published_today", return_value=True) as done, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(0, P.main(["--platform", "threads"]))
        done.assert_called_once()


class InstagramAndExtraGateTest(unittest.TestCase):
    def test_store_shot_feed(self):
        import store_shot_cards as S
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "plan.json").write_text(json.dumps({"key": "k"}), encoding="utf-8")
        argv = ["post", "--dir", str(tmp), "--base-url", "https://example.invalid/"]
        with mock.patch.object(S, "qa", return_value=[]), mock.patch.object(S.post_qa, "gate", return_value=True), \
                mock.patch.object(S, "post_instagram", return_value=None) as post, redirect_stdout(io.StringIO()):
            with on(INSTAGRAM_WEEK):
                self.assertEqual(0, S.main(argv))
            post.assert_not_called()
            with on(TELEGRAM_WEEK):
                self.assertEqual(0, S.main(argv))
            post.assert_called_once()

    def test_social_extra_skips_only_the_off_channel(self):
        import social_extra as X
        planned = []
        with on(BLUESKY_WEEK), mock.patch.object(X, "load_posts", return_value=[]), \
                mock.patch.object(X, "configured", return_value=True), \
                mock.patch.object(X, "plan", side_effect=lambda ch, *a, **k: planned.append(ch) or []), \
                redirect_stdout(io.StringIO()):
            X.run(["bluesky", "facebook", "youtube"], BLUESKY_WEEK, 1, data={})
        self.assertEqual(["facebook", "youtube"], planned)
        planned.clear()
        with on(BLUESKY_WEEK), mock.patch.object(X, "load_posts", return_value=[]), \
                mock.patch.object(X, "configured", return_value=True), \
                mock.patch.object(X, "plan", side_effect=lambda ch, *a, **k: planned.append(ch) or []), \
                redirect_stdout(io.StringIO()):
            X.run(["bluesky"], BLUESKY_WEEK, 1, dry_run=True, data={})  # a dry run still shows the plan
        self.assertEqual(["bluesky"], planned)


class WatchdogTest(unittest.TestCase):
    def row(self, line, fresh=False, max_age=30):
        return {"line": line, "kind": "evidence", "fresh": fresh, "last_success": "n/a", "max_age_hours": max_age,
                "in_progress": False, "action": "none", "note": "run 1 succeeded without a Telegram message_id"}

    def test_a_quiet_channel_in_its_off_week_is_expected_not_red(self):
        import line_watchdog as W
        now = dt.datetime(2026, 10, 28, 12, 41, tzinfo=dt.timezone.utc).timestamp()
        row = W.rotation_holdout(self.row("telegram_message_id"), now)
        self.assertTrue(row["fresh"])
        self.assertEqual("rotation_holdout", row["action"])
        self.assertIn("輪流停開週", row["note"])
        self.assertIn("⏸ 輪流停開週", W.render_table([row], now))

    def test_other_weeks_and_other_lines_still_go_red(self):
        import line_watchdog as W
        later = dt.datetime(2026, 11, 4, 12, 41, tzinfo=dt.timezone.utc).timestamp()
        self.assertFalse(W.rotation_holdout(self.row("telegram_message_id"), later)["fresh"])
        during = dt.datetime(2026, 10, 28, 12, 41, tzinfo=dt.timezone.utc).timestamp()
        self.assertFalse(W.rotation_holdout(self.row("guide_deployment", max_age=6), during)["fresh"])
        self.assertFalse(W.rotation_holdout(self.row("threads_receipts", max_age=24), during)["fresh"])

    def test_an_altered_plan_judges_as_before(self):
        import line_watchdog as W
        now = dt.datetime(2026, 10, 28, 12, 41, tzinfo=dt.timezone.utc).timestamp()
        with mock.patch.object(CR, "load_plan", side_effect=ValueError("digest mismatch")):
            self.assertFalse(W.rotation_holdout(self.row("telegram_message_id"), now)["fresh"])


if __name__ == "__main__":
    unittest.main()
