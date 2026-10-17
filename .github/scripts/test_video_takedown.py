#!/usr/bin/env python3
"""Hook clip takedown (Telegram / Threads / Instagram list): targets, plan, apply with digest, marks (no network)."""
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import download_links as DL  # noqa: E402
import own_posts as OP  # noqa: E402
import video_takedown as V  # noqa: E402

NOW = dt.datetime(2026, 10, 17, 12, 0, tzinfo=dt.timezone.utc)   # 355 is past its 48 h window, the rest inside
ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/aa/AppIcon/512x512bb.jpg"
CAPTION = "收集 37 個 注音小夥伴\n聽聲音 選出對的注音\n在 App Store 搜尋「Lumi注音星球」\n\n#注音符號 #Lumi注音星球"


def targets_of(platform):
    return [t for t in V.TARGETS if t["platform"] == platform]


def log_doc():
    posts = [{"channel": t["platform"], "clip": t["clip"], "link": t["link"], "posted_at": t["posted_at"],
              "id": t["id"], "variant": "c"} for t in V.TARGETS]
    posts.append({"channel": "telegram", "clip": "claudeusagemini/ja", "link": "https://t.me/LumiApps2026/381",
                  "posted_at": "2026-10-17T08:04:29Z", "id": "381", "variant": "b"})
    return {"note": "n", "notes": [], "posts": posts}


class Fakes:
    """Telegram Bot API, the public preview, the Graph API reads and the Threads DELETE."""

    def __init__(self):
        self.calls = []
        self.chat_username = "LumiApps2026"
        self.tg_refuse_delete = set()     # ids whose deleteMessage Telegram refuses (48 h)
        self.tg_gone = set()               # ids already deleted on Telegram
        self.preview_lag = set()           # ids whose public preview still shows the deleted message
        self.replaced = set()
        self.graph = {t["id"]: {"id": t["id"], "media_type": "VIDEO", "permalink": t["link"],
                                "timestamp": t["posted_at"], "username": "hourstag.app"}
                      for t in V.TARGETS if t["platform"] in ("instagram", "threads")}
        self.deleted = set()
        self.delete_error = None
        self.me_error = None

    def tg(self, token, method, payload):
        self.calls.append(("tg", method, payload))
        assert token == "tg-token"
        if method == "getChat":
            return {"id": -100, "username": self.chat_username, "type": "channel"}
        mid = str(payload["message_id"])
        if method == "deleteMessage":
            if mid in self.tg_gone:
                raise RuntimeError("HTTP 400 Bad Request: message to delete not found")
            if mid in self.tg_refuse_delete:
                raise RuntimeError("HTTP 400 Bad Request: message can't be deleted for everyone")
            self.tg_gone.add(mid)
            return True
        if method == "editMessageMedia":
            self.replaced.add(mid)
            return {"message_id": int(mid), "photo": [{"file_id": "p"}], "caption": payload["media"]["caption"],
                    "reply_markup": payload["reply_markup"]}
        raise AssertionError(method)

    def preview(self, post_id):
        self.calls.append(("preview", post_id))
        if post_id in self.tg_gone and post_id not in self.preview_lag:
            return {"state": "missing", "video": False, "photo": False, "text": ""}
        if post_id in self.replaced:
            return {"state": "present", "video": False, "photo": True, "text": CAPTION}
        return {"state": "present", "video": True, "photo": False, "text": CAPTION}

    def get(self, url, params):
        self.calls.append(("get", url, dict(params)))
        assert params["access_token"] in ("ig-token", "th-token")
        path = url.split("/v", 1)[1].split("/", 1)[1]
        if path == "me":
            if self.me_error:
                raise self.me_error
            return {"id": "u1", "username": "hourstag.app" if "threads" in url else "lumi.apps"}
        if path.endswith("/replies"):
            return {"data": [{"id": "r1", "text": "App Store: https://apps.apple.com/app/id1", "is_reply_owned_by_me": True}]}
        if path in self.deleted or path not in self.graph:
            raise OP.ApiError(400, 100, "Object with ID does not exist, cannot be loaded due to missing permissions")
        return dict(self.graph[path])

    def delete(self, url, params):
        self.calls.append(("delete", url, dict(params)))
        if self.delete_error:
            raise self.delete_error
        media_id = url.rsplit("/", 1)[1]
        self.deleted.add(media_id)
        return {"success": True, "deleted_id": media_id}

    def writes(self):
        return [c for c in self.calls if c[0] == "delete" or (c[0] == "tg" and c[1] != "getChat")]


ENV = {"TELEGRAM_BOT_TOKEN": "tg-token", "TELEGRAM_CHAT_ID": "@LumiApps2026", "IG_ACCESS_TOKEN": "ig-token",
       "THREADS_TOKEN": "th-token"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.posts = Path(self.tmp.name) / "clip-posts.json"
        self.report = Path(self.tmp.name) / "video-takedown.json"
        V.save_posts(log_doc(), self.posts)
        self.f = Fakes()

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, env=ENV, now=NOW):
        return V.Context(env=env, get=self.f.get, delete=self.f.delete, tg=self.f.tg, preview=self.f.preview,
                         icon=lambda ios: ICON, sleeper=lambda s: None, now=now, log=lambda *_: None)

    def go(self, mode, confirm="", **kw):
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            return V.run(mode, confirm=confirm, ctx=self.ctx(**kw), posts_path=self.posts, report_path=self.report)

    def entries(self):
        return {(p["channel"], p["id"]): p for p in json.loads(self.posts.read_text(encoding="utf-8"))["posts"]}

    def by_id(self, doc):
        return {(r["platform"], r["id"]): r for r in doc["rows"]}


class TargetTests(unittest.TestCase):
    def test_ten_posts_none_of_a_compliant_key_each_logged_in_the_real_post_log(self):
        self.assertEqual([], V.check_targets())
        self.assertEqual({"telegram": 4, "instagram": 4, "threads": 2},
                         {p: len(targets_of(p)) for p in ("telegram", "instagram", "threads")})
        log = V.load_posts()   # the repo's own clip-posts.json
        for t in V.TARGETS:
            self.assertIsNone(V.record_problem(log, t), t)
            self.assertNotIn(V.app_of(t["clip"]), V.COMPLIANT_KEYS)

    def test_broken_lists_are_refused(self):
        bad = [dict(V.TARGETS[0], clip="hourstaglite/en"), dict(V.TARGETS[1]), dict(V.TARGETS[1]),
               dict(V.TARGETS[2], link="https://t.me/other/366"), dict(V.TARGETS[3], reason="x")]
        text = " ".join(V.check_targets(bad))
        for want in ("compliant clip key", "listed twice", "not the channel message", "unknown reason"):
            self.assertIn(want, text)

    def test_digest_is_stable_and_follows_the_list(self):
        self.assertEqual(V.digest(), V.digest(tuple(V.TARGETS)))
        self.assertNotEqual(V.digest(), V.digest(V.TARGETS[1:]))


class PlanTests(Base):
    def test_plan_writes_nothing_and_names_a_method_for_every_post(self):
        code, doc = self.go("plan")
        self.assertEqual(0, code)
        self.assertEqual([], self.f.writes())
        rows = self.by_id(doc)
        self.assertEqual("delete_or_replace_video", rows[("telegram", "355")]["action"])   # past 48 h
        for mid in ("363", "366", "373"):
            self.assertEqual("delete", rows[("telegram", mid)]["action"])
        for t in targets_of("instagram"):
            self.assertEqual("local_archive", rows[("instagram", t["id"])]["action"])
        for t in targets_of("threads"):
            self.assertEqual("delete", rows[("threads", t["id"])]["action"])
            self.assertEqual("r1", rows[("threads", t["id"])]["own_replies_kept"][0]["id"])
        fb = rows[("telegram", "355")]["fallback"]
        self.assertTrue(fb["ready"])
        self.assertEqual(ICON, fb["photo"])
        self.assertTrue(DL.has_app_store_link(fb["caption"], "https://apps.apple.com/app/id6773017109"))
        self.assertTrue(fb["caption"].startswith(CAPTION.split("\n")[0]))
        self.assertEqual(CAPTION, rows[("telegram", "355")]["caption"])
        self.assertEqual(4, len(doc["handoff_local"]))
        self.assertEqual(log_doc(), json.loads(self.posts.read_text(encoding="utf-8")))   # the log is untouched
        self.assertEqual(V.digest(), json.loads(self.report.read_text(encoding="utf-8"))["digest"])

    def test_a_post_the_log_does_not_back_is_blocked(self):
        doc = log_doc()
        doc["posts"][0]["clip"] = "claudeusagemini/zh-Hant"
        V.save_posts(doc, self.posts)
        code, rep = self.go("plan")
        self.assertEqual(1, code)
        self.assertEqual("blocked", self.by_id(rep)[("telegram", "355")]["action"])

    def test_another_telegram_chat_blocks_every_telegram_post(self):
        self.f.chat_username = "SomeOtherChannel"
        code, rep = self.go("plan")
        self.assertEqual(1, code)
        for t in targets_of("telegram"):
            self.assertIn("not @LumiApps2026", self.by_id(rep)[("telegram", t["id"])]["problem"])

    def test_graph_checks_owner_type_and_link(self):
        th, ig = targets_of("threads")[0]["id"], targets_of("instagram")[0]["id"]
        self.f.graph[th]["username"] = "someone.else"
        self.f.graph[ig]["media_type"] = "IMAGE"
        gone = targets_of("threads")[1]["id"]
        del self.f.graph[gone]
        code, rep = self.go("plan")
        rows = self.by_id(rep)
        self.assertEqual(1, code)
        self.assertIn("not @hourstag.app", rows[("threads", th)]["problem"])
        self.assertIn("not VIDEO", rows[("instagram", ig)]["problem"])
        self.assertEqual("none", rows[("threads", gone)]["action"])

    def test_a_token_that_cannot_read_its_account_never_reads_as_gone(self):
        self.f.me_error = OP.ApiError(400, 100, "Object with ID 'me' does not exist, cannot be loaded due to "
                                                "missing permissions")
        code, rep = self.go("plan")
        self.assertEqual(1, code)
        for t in targets_of("threads") + targets_of("instagram"):
            row = self.by_id(rep)[(t["platform"], t["id"])]
            self.assertEqual("blocked", row["action"])
            self.assertIn("cannot read its own account", row["problem"])

    def test_an_unknown_field_is_not_taken_for_a_deleted_post(self):
        self.assertFalse(V.gone_error(OP.ApiError(400, 100, "Tried accessing nonexisting field (shortcode)")))
        self.assertTrue(V.gone_error(OP.ApiError(400, 100, "Object with ID '1' does not exist")))

    def test_missing_tokens_block_instead_of_guessing(self):
        code, rep = self.go("plan", env={})
        self.assertEqual(1, code)
        self.assertTrue(all(r["action"] == "blocked" for r in rep["rows"]))

    def test_past_the_window_without_a_fallback_is_blocked(self):
        with mock.patch.object(V, "android_apps", return_value={}):
            code, rep = self.go("plan")
        rows = self.by_id(rep)
        self.assertEqual(1, code)
        self.assertEqual("blocked", rows[("telegram", "355")]["action"])
        self.assertEqual("delete", rows[("telegram", "363")]["action"])   # inside the window it can still be deleted


class ApplyTests(Base):
    def test_apply_needs_the_plans_digest(self):
        for confirm in ("", "f" * 64):
            with self.assertRaises(V.Refused):
                self.go("apply", confirm=confirm)
        self.assertEqual([], self.f.calls)
        self.assertFalse(self.report.exists())

    def test_apply_deletes_reads_back_and_marks(self):
        code, doc = self.go("apply", confirm=V.digest())
        self.assertEqual(0, code, [r for r in doc["rows"] if r["action"] not in ("done", "handed_to_local")])
        rows = self.by_id(doc)
        for t in targets_of("telegram") + targets_of("threads"):
            self.assertEqual("done", rows[(t["platform"], t["id"])]["action"], t)
        for t in targets_of("instagram"):
            self.assertEqual("handed_to_local", rows[("instagram", t["id"])]["action"])
        self.assertEqual({"355", "363", "366", "373"}, self.f.tg_gone)
        self.assertEqual({t["id"] for t in targets_of("threads")}, self.f.deleted)
        entries = self.entries()
        for t in V.TARGETS:
            mark = entries[(t["platform"], t["id"])]["taken_down"]
            want = "pending_local_archive" if t["platform"] == "instagram" else "deleted"
            self.assertEqual(want, mark["status"], t)
            self.assertEqual(V.SUMMARY_REPORT, mark["report"])
        self.assertNotIn("taken_down", entries[("telegram", "381")])   # a compliant clip stays as it is
        self.assertEqual(CAPTION, doc["receipts"]["telegram"]["355"]["caption_before"])

    def test_a_refused_telegram_delete_swaps_the_video_for_the_icon_with_the_links(self):
        self.f.tg_refuse_delete = {"355"}
        code, doc = self.go("apply", confirm=V.digest())
        self.assertEqual(0, code)
        edit = next(c[2] for c in self.f.calls if c[0] == "tg" and c[1] == "editMessageMedia")
        self.assertEqual(355, edit["message_id"])
        self.assertEqual(("photo", ICON), (edit["media"]["type"], edit["media"]["media"]))
        store = "https://apps.apple.com/app/id6773017109"
        self.assertTrue(DL.has_app_store_link(edit["media"]["caption"], store))
        self.assertTrue(any("apps.apple.com" in b["url"] for b in edit["reply_markup"]["inline_keyboard"][0]))
        receipt = doc["receipts"]["telegram"]["355"]
        self.assertEqual(("video_replaced", True), (receipt["status"], receipt["verified"]))
        self.assertEqual("video_replaced", self.entries()[("telegram", "355")]["taken_down"]["status"])

    def test_a_threads_delete_without_permission_is_red_and_unmarked(self):
        self.f.delete_error = OP.ApiError(403, 10, "Application does not have permission for this action")
        code, doc = self.go("apply", confirm=V.digest())
        self.assertEqual(1, code)
        for t in targets_of("threads"):
            row = self.by_id(doc)[("threads", t["id"])]
            self.assertEqual("failed", row["action"])
            self.assertIn("threads_delete", row["problem"])
            self.assertNotIn("taken_down", self.entries()[("threads", t["id"])])

    def test_a_lagging_preview_is_unverified_and_a_rerun_heals_it(self):
        self.f.preview_lag = {"363"}
        code, doc = self.go("apply", confirm=V.digest())
        self.assertEqual(1, code)
        self.assertEqual("unverified", self.by_id(doc)[("telegram", "363")]["action"])
        self.assertNotIn("taken_down", self.entries()[("telegram", "363")])
        self.f.preview_lag = set()
        self.f.calls.clear()
        code, doc = self.go("apply", confirm=V.digest())
        self.assertEqual(0, code)
        self.assertEqual("deleted", self.entries()[("telegram", "363")]["taken_down"]["status"])
        self.assertTrue(doc["receipts"]["telegram"]["363"]["verified"])
        # the rerun reads the preview ("Post not found") and writes nothing; done posts are not touched again
        self.assertEqual([], self.f.writes())


class MarkTests(Base):
    def test_mark_is_idempotent_survives_a_reset_and_keeps_the_log_format(self):
        self.go("apply", confirm=V.digest())
        self.assertEqual(0, V.mark(self.posts, self.report))
        V.save_posts(log_doc(), self.posts)   # origin/main without the marks
        self.assertEqual(len(V.TARGETS), V.mark(self.posts, self.report))
        raw = self.posts.read_text(encoding="utf-8")
        self.assertEqual(json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + "\n", raw)

    def test_unverified_receipts_are_not_marked(self):
        V.save_posts(log_doc(), self.posts)
        self.report.write_text(json.dumps({"receipts": {"telegram": {"355": {
            "at": "2026-10-17T12:00:00Z", "status": "deleted", "verified": False}}}}), encoding="utf-8")
        self.assertEqual(0, V.mark(self.posts, self.report))


class PreviewTests(unittest.TestCase):
    PAGE = ('<div class="tgme_widget_message" data-post="LumiApps2026/{id}">'
            '<div class="tgme_widget_message_video_wrap"><video class="tgme_widget_message_video"></video></div>'
            '<div class="tgme_widget_message_text js-message_text">Line one<br/>Line &amp; two<br/>'
            '<a href="?q=%23tag">#tag</a></div></div>')

    def opener(self, body):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return lambda req, timeout=30: Resp(body.encode())

    def test_present_video_with_its_caption_lines(self):
        got = V.tg_preview("355", opener=self.opener(self.PAGE.format(id=355)), sleeper=lambda s: None)
        self.assertEqual({"state": "present", "video": True, "photo": False, "text": "Line one\nLine & two\n#tag"}, got)

    def test_post_not_found_and_another_message(self):
        missing = V.tg_preview("355", opener=self.opener('<div class="tgme_widget_message_error">Post not found</div>'))
        self.assertEqual("missing", missing["state"])
        other = V.tg_preview("355", opener=self.opener(self.PAGE.format(id=356)), sleeper=lambda s: None)
        self.assertEqual("unknown", other["state"])

    def test_network_errors_are_unknown_not_missing(self):
        def broken(req, timeout=30):
            raise urllib.error.URLError("reset")
        got = V.tg_preview("355", opener=broken, sleeper=lambda s: None)
        self.assertEqual("unknown", got["state"])

    def test_bot_api_errors_never_carry_the_token(self):
        def refuse(req, timeout=30):
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request",
                                         {}, io.BytesIO(b'{"ok":false,"description":"message can\'t be deleted"}'))
        with self.assertRaises(RuntimeError) as err:
            V.tg_api("123:SECRET", "deleteMessage", {"chat_id": "x", "message_id": 1}, opener=refuse)
        self.assertNotIn("SECRET", str(err.exception))
        self.assertIn("can't be deleted", str(err.exception))


if __name__ == "__main__":
    unittest.main()
