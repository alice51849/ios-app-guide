#!/usr/bin/env python3
"""Tests for clip_source.py: a local HTTP server stands in for the clip hosts (no internet)."""
import http.server
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_source as CS  # noqa: E402


def box(kind, payload=b""):
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def mp4(mdat_bytes=60_000):
    return box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2mp41") + box(b"moov", b"\x00" * 200) + \
        box(b"mdat", bytes(range(256)) * (mdat_bytes // 256))


CLIP = mp4()


class Host(http.server.BaseHTTPRequestHandler):
    """/r/<name>: 302 to /f/<name> (the clips-mirror release does this). /f/<name>: the file, Range answered with
    206; the first full answer of /cut/<name> stops halfway. /404/<name>: 404. /html/<name>: an error page."""
    cut_once = set()
    log = []

    def log_message(self, *a):
        pass

    def do_HEAD(self):  # the release answers HEAD with 401; a download never needs it
        self.send_response(401)
        self.end_headers()

    def do_GET(self):
        Host.log.append((self.path, self.headers.get("Range")))
        kind = self.path.split("/")[1]
        if kind == "r":
            self.send_response(302)
            self.send_header("Location", "/f/" + self.path.split("/", 2)[2])
            self.end_headers()
            return
        if kind == "404":
            self.send_error(404)
            return
        if kind == "html":
            body = b"<html>" + b"x" * 30_000 + b"</html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        start = 0
        rng = self.headers.get("Range")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(CLIP) - 1}/{len(CLIP)}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(CLIP) - start))
        self.end_headers()
        if kind == "cut" and self.path not in Host.cut_once and not rng:
            Host.cut_once.add(self.path)
            self.wfile.write(CLIP[: len(CLIP) // 2])
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(CLIP[start:])


class ClipSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Host)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        # never through a proxy from the environment: the server is local
        cls.direct = mock.patch.object(urllib.request, "_opener",
                                       urllib.request.build_opener(urllib.request.ProxyHandler({})))
        cls.direct.start()

    @classmethod
    def tearDownClass(cls):
        cls.direct.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Host.log.clear()
        self.dir = Path(tempfile.mkdtemp(prefix="clip-src-test-"))

    def fetch_clip(self, *urls):
        with mock.patch.object(CS, "sources", return_value=list(urls)), mock.patch("sys.stdout"):
            return CS.fetch_clip("https://files.catbox.moe/abc123.mp4", self.dir, label="t", sleep=lambda s: None)

    def test_mirror_first_then_catbox_with_the_same_id(self):
        for url in ("https://files.catbox.moe/e4a4ez.mp4",
                    "https://github.com/alice51849/ios-app-guide/releases/download/clips-mirror/e4a4ez.mp4"):
            self.assertEqual(CS.sources(url), [
                "https://github.com/alice51849/ios-app-guide/releases/download/clips-mirror/e4a4ez.mp4",
                "https://files.catbox.moe/e4a4ez.mp4"])
        self.assertEqual(CS.sources("https://cdn.example/x.mp4"), ["https://cdn.example/x.mp4"])
        self.assertEqual(CS.sources(""), [])
        self.assertTrue(CS.is_clip("https://cdn.example/x.mp4?sig=1"))
        self.assertFalse(CS.is_clip("https://raw.githubusercontent.com/a/b/main/feed.json"))

    def test_follows_the_redirect_and_never_asks_head(self):
        path = self.fetch_clip(f"{self.base}/r/a.mp4")
        self.assertEqual(path.read_bytes(), CLIP)
        self.assertEqual([p for p, _ in Host.log], ["/r/a.mp4", "/f/a.mp4"])

    def test_a_dropped_transfer_resumes_with_range(self):
        path = self.fetch_clip(f"{self.base}/cut/b.mp4")
        self.assertEqual(path.read_bytes(), CLIP)
        self.assertEqual(Host.log[0], ("/cut/b.mp4", None))
        self.assertEqual(Host.log[-1], ("/cut/b.mp4", f"bytes={len(CLIP) // 2}-"))

    def test_falls_back_to_the_next_source(self):
        path = self.fetch_clip(f"{self.base}/404/c.mp4", f"{self.base}/html/c.mp4", f"{self.base}/r/c.mp4")
        self.assertEqual(path.read_bytes(), CLIP)
        self.assertEqual(sum(1 for p, _ in Host.log if p == "/404/c.mp4"), 1)  # a 404 is not retried

    def test_no_good_source_raises_and_leaves_no_file(self):
        with self.assertRaises(CS.ClipUnavailable) as ctx:
            self.fetch_clip(f"{self.base}/404/d.mp4", f"{self.base}/html/d.mp4")
        self.assertIn("HTTP 404", str(ctx.exception))
        self.assertIn("ftyp", str(ctx.exception))
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_unreachable_host_is_retried_then_given_up(self):
        sleeps = []
        with mock.patch("sys.stdout"):
            err = CS.fetch("http://127.0.0.1:9/x.mp4", self.dir / "x.mp4", tries=3, timeout=2, sleep=sleeps.append)
        self.assertTrue(err)
        self.assertEqual(len(sleeps), 2)

    def test_mp4_check(self):
        good = self.dir / "good.mp4"
        good.write_bytes(CLIP)
        self.assertEqual(CS.mp4_problem(good), "")
        for name, data, why in (
                ("cut", CLIP[:-100], "truncated"),
                ("tiny", CLIP[:500], "too small"),
                ("nomoov", box(b"ftyp", b"isom") + box(b"mdat", b"\x00" * 30_000), "no moov"),
                ("html", b"<html>" + b"x" * 30_000, "ftyp"),
                ("nofile", None, "no file")):
            path = self.dir / f"{name}.mp4"
            if data is not None:
                path.write_bytes(data)
            self.assertIn(why, CS.mp4_problem(path), name)
        # a 64-bit size and a last box that runs to the end of the file (size 0) are both valid
        big = box(b"ftyp", b"isom") + box(b"moov") + struct.pack(">I", 1) + b"mdat" + struct.pack(">Q", 16 + 30_000) + \
            b"\x00" * 30_000
        tail = box(b"ftyp", b"isom") + box(b"moov") + struct.pack(">I", 0) + b"mdat" + b"\x00" * 30_000
        for name, data in (("big", big), ("tail", tail)):
            path = self.dir / f"{name}.mp4"
            path.write_bytes(data)
            self.assertEqual(CS.mp4_problem(path), "", name)

    def test_upload_reads_the_file(self):
        path = self.dir / "u.mp4"
        path.write_bytes(CLIP)
        up = CS.Upload(path)
        self.assertEqual((up.read(), up.size, up.content_type, up.filename), (CLIP, len(CLIP), "video/mp4", "clip.mp4"))


if __name__ == "__main__":
    unittest.main()
