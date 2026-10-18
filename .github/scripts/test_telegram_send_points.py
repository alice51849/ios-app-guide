"""Every Telegram send point in this repository is either the internal-alert gate or a reviewed public one.

Internal messages (watchdog alerts, health checks, conversion-guard / regression /
growth-effect summaries, ``line_watchdog.py --telegram``) go only through
``.github/scripts/telegram_alert_guard.py``: TELEGRAM_ALERT_CHAT_ID, never the
public promo channel TELEGRAM_CHAT_ID (65 internal alerts leaked there before
2026-10-18). This test scans every checked-out, non-test code file and workflow:

* a file that calls the Telegram Bot API (or a Telegram client library) must be
  the guard or be listed in SEND_POINTS as a reviewed promo / public-channel
  maintenance / read-only point, so a new internal sender that bypasses the
  guard fails here;
* only those public points may read TELEGRAM_CHAT_ID; a non-promo workflow may
  bind ``secrets.TELEGRAM_CHAT_ID`` only as ``TELEGRAM_PUBLIC_CHAT_ID`` (the
  guard's comparison, never a target);
* TELEGRAM_ALERT_CHAT_ID is used only through the guard, and never by a public point.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# path -> (kind, why it may talk to Telegram). kind: guard | promo | public_maintenance | read_only.
SEND_POINTS = {
    ".github/scripts/telegram_alert_guard.py": ("guard", "內部訊息唯一出口：只發 TELEGRAM_ALERT_CHAT_ID，拒發公開頻道"),
    ".github/scripts/telegram_post.py": ("promo", "每日宣傳貼文發到公開頻道 t.me/LumiApps2026（download_links 守門）"),
    ".github/scripts/clip_posts.py": ("promo", "鉤子短片（影片＋App Store 按鈕）發到公開頻道"),
    ".github/scripts/countdown_cards.py": ("promo", "倒數卡／工具卡（圖＋下載按鈕）發到公開頻道"),
    ".github/scripts/portfolio_daily.py": ("promo", "每日全 App 精選，經 telegram_post._send_message 發到公開頻道"),
    ".github/scripts/telegram_link_fix.py": ("public_maintenance", "替已發出的宣傳貼文補下載按鈕（editMessageReplyMarkup）"),
    ".github/scripts/video_takedown.py": ("public_maintenance", "下架不合規的自家影片貼文（只動自家宣傳貼文）"),
    ".github/scripts/telegram_alert_cleanup.py": ("public_maintenance", "清理 10-18 前誤發到公開頻道的內部警報：只動已複審名單的 id（刪除或改成（此訊息已移除））"),
    ".github/workflows/telegram-daily.yml": ("promo", "每日宣傳貼文／鉤子片／全 App 精選"),
    ".github/workflows/telegram-clips.yml": ("promo", "時段鉤子片"),
    ".github/workflows/clip-backup.yml": ("promo", "鉤子片備援發文"),
    ".github/workflows/countdown-daily.yml": ("promo", "倒數卡"),
    ".github/workflows/utility-daily.yml": ("promo", "工具卡"),
    ".github/workflows/portfolio-daily.yml": ("promo", "每日全 App 精選"),
    ".github/workflows/telegram-link-fix.yml": ("public_maintenance", "補下載按鈕"),
    ".github/workflows/video-takedown.yml": ("public_maintenance", "下架影片貼文"),
    ".github/workflows/telegram-alert-cleanup.yml": ("public_maintenance", "清理誤發的內部警報（只能手動）"),
}


# ---------------------------------------------------------------------------
# The scanner below is the same in 00_GrowthEngine, ios-app-guide and threads-autopilot;
# only SEND_POINTS above differs per repository.
GUARD = ".github/scripts/telegram_alert_guard.py"
KINDS = {"guard", "promo", "public_maintenance", "read_only"}
PUBLIC_KINDS = {"promo", "public_maintenance"}
CODE_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".command", ".yml", ".yaml", ".mjs", ".cjs", ".js", ".ts", ".rb"}
MAX_BYTES = 3_000_000

BOT_API = re.compile(r"api\.telegram\.org|\btelethon\b|\bTelegramClient\b|\btelegraf\b|node-telegram-bot-api"
                     r"|\bfrom telegram(?:\.ext)? import\b|^\s*import telegram\s*$|\baiogram\b|\bpyrogram\b", re.M)
SEND_METHOD = re.compile(
    r"""["'/](?:send(?:Message|Photo|Video|Document|Animation|Audio|Voice|MediaGroup|Sticker|Poll|Location|Contact)"""
    r"""|copyMessages?|forwardMessages?|editMessage(?:Text|Caption|Media|ReplyMarkup)|deleteMessages?)\b""")
PUBLIC_CHAT_ENV_READ = re.compile(
    r"""(?:environ(?:\.get)?\s*[(\[]\s*|getenv\(\s*|env(?:\.get)?\s*[(\[]\s*)["']TELEGRAM_CHAT_ID["']"""
    r"""|\$\{?TELEGRAM_CHAT_ID\b|process\.env\.TELEGRAM_CHAT_ID\b""")
PUBLIC_SECRET = re.compile(r"secrets\.TELEGRAM_CHAT_ID\b")
PUBLIC_SECRET_COMPARE_ONLY = re.compile(r"^\s*TELEGRAM_PUBLIC_CHAT_ID:\s*\$\{\{\s*secrets\.TELEGRAM_CHAT_ID\s*\}\}\s*$")
ALERT_CHAT = re.compile(r"TELEGRAM_ALERT_CHAT_ID")
GUARD_USE = re.compile(r"telegram_alert_guard|line_alert\.py")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             check=True, capture_output=True).stdout
        names = [name for name in out.decode("utf-8", "replace").split("\0") if name]
    except (OSError, subprocess.CalledProcessError):
        names = [str(path.relative_to(root)) for path in root.rglob("*")
                 if path.is_file() and ".git" not in path.relative_to(root).parts]
    return sorted(set(names))


def is_test(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    return (name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".test.mjs"))
            or "tests" in parts[:-1] or "__tests__" in parts[:-1])


def scan(root: Path) -> dict[str, dict]:
    """Every checked-out, non-test code file that touches the Telegram Bot API or the public chat id."""
    found: dict[str, dict] = {}
    for rel in tracked_files(root):
        path = root / rel
        if path.suffix not in CODE_SUFFIXES or is_test(rel) or not path.is_file():
            continue  # a sparse checkout simply has fewer files on disk
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        workflow = rel.startswith(".github/workflows/")
        hit = {
            "bot_api": bool(BOT_API.search(text) or SEND_METHOD.search(text)),
            "reads_public_chat": bool(PUBLIC_CHAT_ENV_READ.search(text)),
            "public_secret_lines": [line.strip() for line in text.splitlines() if PUBLIC_SECRET.search(line)]
            if workflow else [],
            "alert_chat": bool(ALERT_CHAT.search(text)),
            "uses_guard": bool(GUARD_USE.search(text)),
            "workflow": workflow,
        }
        if hit["bot_api"] or hit["reads_public_chat"] or hit["public_secret_lines"] or hit["alert_chat"]:
            found[rel] = hit
    return found


class TelegramSendPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = repo_root()
        cls.found = scan(cls.root)
        cls.tracked = set(tracked_files(cls.root))

    def test_registry_is_well_formed(self):
        self.assertEqual("guard", SEND_POINTS.get(GUARD, ("",))[0])
        for rel, (kind, reason) in SEND_POINTS.items():
            self.assertIn(kind, KINDS, rel)
            self.assertTrue(reason.strip(), rel)

    def test_every_telegram_api_call_site_is_the_guard_or_a_reviewed_public_send_point(self):
        unregistered = sorted(rel for rel, hit in self.found.items() if hit["bot_api"] and rel not in SEND_POINTS)
        self.assertEqual([], unregistered,
                         "new Telegram send point(s): an internal message (alert, health check, guard, summary) "
                         "must go through .github/scripts/telegram_alert_guard.py (TELEGRAM_ALERT_CHAT_ID only); "
                         "a promo post to the public channel must be reviewed and added to SEND_POINTS")

    def test_only_public_send_points_read_the_public_chat_id(self):
        offenders = sorted(rel for rel, hit in self.found.items() if hit["reads_public_chat"]
                           and SEND_POINTS.get(rel, ("",))[0] not in PUBLIC_KINDS | {"guard"})
        self.assertEqual([], offenders,
                         "TELEGRAM_CHAT_ID is the public promo channel: internal code must use "
                         "telegram_alert_guard (TELEGRAM_ALERT_CHAT_ID), never TELEGRAM_CHAT_ID")

    def test_internal_workflows_pass_the_public_chat_only_for_comparison(self):
        offenders = []
        for rel, hit in self.found.items():
            if not hit["workflow"] or SEND_POINTS.get(rel, ("",))[0] in PUBLIC_KINDS:
                continue
            for line in hit["public_secret_lines"]:
                if not PUBLIC_SECRET_COMPARE_ONLY.match(line):
                    offenders.append(f"{rel}: {line}")
        self.assertEqual([], offenders,
                         "a non-promo workflow may bind secrets.TELEGRAM_CHAT_ID only as "
                         "`TELEGRAM_PUBLIC_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}` (the guard's comparison)")

    def test_alert_chat_users_send_through_the_guard(self):
        offenders = sorted(rel for rel, hit in self.found.items()
                           if hit["alert_chat"] and rel != GUARD and not hit["uses_guard"]
                           and SEND_POINTS.get(rel, ("",))[0] != "read_only")
        self.assertEqual([], offenders, "TELEGRAM_ALERT_CHAT_ID is read only through telegram_alert_guard / line_alert.py")

    def test_public_send_points_never_touch_the_internal_alert_chat(self):
        offenders = sorted(rel for rel, hit in self.found.items()
                           if hit["alert_chat"] and SEND_POINTS.get(rel, ("",))[0] in PUBLIC_KINDS)
        self.assertEqual([], offenders, "promo / public-channel code must not send internal alerts")

    def test_registry_has_no_stale_entries(self):
        stale = []
        for rel in SEND_POINTS:
            if rel not in self.tracked:
                stale.append(f"{rel} (not in the repository)")
            elif (self.root / rel).is_file() and rel not in self.found:
                stale.append(f"{rel} (no Telegram call any more)")
        self.assertEqual([], stale, "remove or fix stale SEND_POINTS entries")

    def test_the_guard_is_present_and_is_the_shared_copy(self):
        guard = self.root / GUARD
        if not guard.is_file():
            self.skipTest("sparse checkout without the guard")
        text = guard.read_text(encoding="utf-8")
        self.assertIn("def send_internal_alert(", text)
        self.assertIn('ALERT_CHAT_ENV = "TELEGRAM_ALERT_CHAT_ID"', text)

    def test_the_scanner_catches_an_unrouted_internal_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agent").mkdir()
            (root / "agent" / "health_ping.py").write_text(
                'import os, urllib.request\n'
                'url = f"https://api.telegram.org/bot{os.environ[\'TELEGRAM_BOT_TOKEN\']}/sendMessage"\n'
                'chat = os.environ.get("TELEGRAM_CHAT_ID")\n', encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "health.yml").write_text(
                "env:\n  TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}\n"
                "  TELEGRAM_PUBLIC_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}\n", encoding="utf-8")
            (root / "agent" / "test_health_ping.py").write_text('URL = "https://api.telegram.org/x"\n', encoding="utf-8")
            with mock.patch(f"{__name__}.tracked_files", lambda r: sorted(
                    str(p.relative_to(r)) for p in r.rglob("*") if p.is_file())):
                found = scan(root)
        self.assertTrue(found["agent/health_ping.py"]["bot_api"])
        self.assertTrue(found["agent/health_ping.py"]["reads_public_chat"])
        self.assertNotIn("agent/test_health_ping.py", found)
        lines = found[".github/workflows/health.yml"]["public_secret_lines"]
        self.assertEqual([False, True], [bool(PUBLIC_SECRET_COMPARE_ONLY.match(line)) for line in lines])


if __name__ == "__main__":
    unittest.main()
