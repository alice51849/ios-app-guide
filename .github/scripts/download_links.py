#!/usr/bin/env python3
"""Every promo text carries the app's direct download link (fail closed, zero token).

Owner rule (2026-10-17): every promo post, update and text must carry the app's direct download link -
the App Store link, plus the Google Play link when the app is live on Android. Posts that went out
without one (Instagram Reels captions had "Link in bio" and the store name only) are the reason this
module exists. The posters share these three helpers:

- has_download_link(text, app_store_url, play_url): is the link of that exact app in the text?
- link_problems(text, ...): QA-gate style list of what is missing (post_qa.py calls it before posting).
- ensure_download_link(text, ...): the last-line defence at the send call. A text without the link gets
  the template link lines appended (the body is trimmed to the platform limit, hashtags first); when the
  app has no known link, or no room is left, it raises MissingDownloadLink so nothing is sent silently.

Platform rules stay as they are: Instagram captions cannot hold a clickable link, so the full URL is
written into the text *and* the "link in bio" line stays; Threads keeps its link in the first reply
(account limit history), so its main text is not checked here - threads_reply_problems() checks the reply.

    python3 download_links.py check "text" --app-store https://apps.apple.com/app/id1   # exit 1 when missing
"""
import json
import os
import re
import sys
import urllib.parse

APP_STORE_URL = re.compile(r"https?://(?:apps|itunes)\.apple\.com/[^\s\"'<>)]+", re.I)
APP_STORE_BARE = re.compile(r"https?://(?:apps|itunes)\.apple\.com/[^\s\"'<>)]*?/id(\d+)(?![A-Za-z0-9_])", re.I)
PLAY_LINK = re.compile(r"https?://play\.google\.com/store/apps/details\?(?:[^\s\"'<>)]*&)?id=([A-Za-z0-9_.]+)", re.I)
HASHTAG_LINE = re.compile(r"^\s*(?:#\S+\s*)+$")


class MissingDownloadLink(ValueError):
    """The text has no download link and none could be added: the post must not go out."""


def app_store_id(url):
    """The numeric App Store id of an apps.apple.com / itunes.apple.com link, or ''."""
    m = APP_STORE_BARE.search(url or "")
    return m.group(1) if m else ""


def play_package(url):
    """The package name of a Google Play details link, or ''."""
    m = PLAY_LINK.search(url or "")
    return m.group(1) if m else ""


def _plain(text):
    """The text with percent-encoded URLs read as plain ones (a platform may hand a link back wrapped)."""
    text = text or ""
    return urllib.parse.unquote(text) if "%2F" in text.upper() or "%3A" in text.upper() else text


def store_ids_in(text):
    """App ids the text links as a DOWNLOAD page. A write-review link (?action=write-review) is the same
    app page but not a download link, so it does not count."""
    ids = set()
    for m in APP_STORE_URL.finditer(_plain(text)):
        url = m.group(0)
        if "action=write-review" in url.lower():
            continue
        found = APP_STORE_BARE.search(url)
        if found:
            ids.add(found.group(1))
    return ids


def play_packages_in(text):
    return {m.group(1) for m in PLAY_LINK.finditer(_plain(text))}


def links_covered(text, wanted_text):
    """True when `text` holds every App Store page and Google Play package that `wanted_text` links to
    (compared by app id / package, so a changed campaign token or a rewritten URL does not matter)."""
    ids, packages = store_ids_in(wanted_text), play_packages_in(wanted_text)
    return bool(ids or packages) and ids <= store_ids_in(text) and packages <= play_packages_in(text)


def has_app_store_link(text, app_store_url):
    """True when the text links this app's App Store page (any storefront, any campaign token)."""
    wanted = app_store_id(app_store_url)
    return bool(wanted) and wanted in store_ids_in(text)


def has_play_link(text, play_url):
    wanted = play_package(play_url)
    return bool(wanted) and wanted in play_packages_in(text)


def has_download_link(text, app_store_url, play_url=None):
    """The App Store link of this app (and its Google Play link when the app has one) is in the text."""
    if not has_app_store_link(text, app_store_url):
        return False
    return not play_url or has_play_link(text, play_url)


def link_problems(text, app_store_url, play_url=None, label="text"):
    """What is missing, as QA-gate problem strings (empty list = the text carries the link)."""
    out = []
    if not app_store_id(app_store_url):
        out.append(f"{label}: no App Store link known for this app (cannot attach the download link)")
    elif not has_app_store_link(text, app_store_url):
        out.append(f"{label}: no direct App Store download link (id{app_store_id(app_store_url)}) in the text")
    if play_url and not has_play_link(text, play_url):
        out.append(f"{label}: app is on Google Play but the text has no Google Play link")
    return out


def _link_block(text, app_store_url, play_url, app_store_label, play_label):
    lines = []
    if not has_app_store_link(text, app_store_url):
        lines.append(f"{app_store_label}: {app_store_url}")
    if play_url and not has_play_link(text, play_url):
        lines.append(f"{play_label}: {play_url}")
    return "\n".join(lines)


def _cut(text, room):
    """`text` cut to `room` characters at a line or word boundary, ending in an ellipsis."""
    if len(text) <= room:
        return text
    cut = text[:max(room - 1, 0)]
    for sep in ("\n", " "):
        pos = cut.rfind(sep)
        if pos >= len(cut) // 2:
            cut = cut[:pos]
            break
    cut = re.sub(r"https?://\S*$", "", cut)  # never leave half a URL behind
    return cut.rstrip() + "…"


def _without_own_links(text, app_store_url, play_url):
    """`text` minus the lines that carry this app's own store links (the full link block is rebuilt after a trim)."""
    wanted_id, wanted_pkg = app_store_id(app_store_url), play_package(play_url)
    keep = []
    for line in (text or "").split("\n"):
        own = (wanted_id and wanted_id in store_ids_in(line)) or (wanted_pkg and wanted_pkg in play_packages_in(line))
        if not own:
            keep.append(line)
    return "\n".join(keep)


def ensure_download_link(text, app_store_url, play_url=None, *, max_len=None, app_store_label="App Store",
                         play_label="Google Play", measure=len, label="post"):
    """`text` with the app's direct download link(s), appended when missing.

    Raises MissingDownloadLink when the App Store link is not a valid apps.apple.com app link, or when
    the links do not fit `max_len` even after the body is trimmed (hashtag lines go first). `measure`
    counts length the platform's way (graphemes, URL weights); default is len().
    """
    text = text or ""
    if not app_store_id(app_store_url):
        raise MissingDownloadLink(f"{label}: no App Store link known for this app: {app_store_url!r}")
    block = _link_block(text, app_store_url, play_url, app_store_label, play_label)
    if not block:
        return text
    sep = "\n\n"
    out = f"{text.rstrip()}{sep}{block}" if text.strip() else block
    if max_len is None or measure(out) <= max_len:
        return out
    # Over the limit: rebuild with the FULL link block (App Store + Play) and a trimmed body, so a trim can
    # never cut away a link the text already had; the result is verified before it is returned.
    block = "\n".join(filter(None, [f"{app_store_label}: {app_store_url}",
                                    f"{play_label}: {play_url}" if play_url else ""]))
    lines = _without_own_links(text, app_store_url, play_url).rstrip().split("\n")
    candidates = []

    def with_block():
        body = "\n".join(lines).rstrip()
        candidates.append(f"{body}{sep}{block}" if body else block)

    with_block()  # the whole body first
    while lines and (not lines[-1].strip() or HASHTAG_LINE.match(lines[-1])):  # then without the hashtag tail
        lines.pop()
        with_block()
    body = "\n".join(lines).rstrip()
    for out in candidates:
        if measure(out) <= max_len:
            return _verified(out, app_store_url, play_url, label)
    room = max_len - measure(sep + block) - 1
    while room > 0:
        trimmed = _cut(body, room)
        out = f"{trimmed}{sep}{block}"
        if measure(out) <= max_len:
            return _verified(out, app_store_url, play_url, label)
        room -= max(1, measure(out) - max_len)
    if measure(block) <= max_len:  # only the link itself fits: still a post with a download link
        return _verified(block, app_store_url, play_url, label)
    raise MissingDownloadLink(f"{label}: the download link ({measure(block)} chars) does not fit {max_len}")


def _verified(out, app_store_url, play_url, label):
    problems = link_problems(out, app_store_url, play_url, label)
    if problems:
        raise MissingDownloadLink("; ".join(problems))
    return out


def threads_reply_problems(reply_text, app_store_url, play_url=None):
    """Threads posts keep links out of the main text; the first reply must carry them."""
    return link_problems(reply_text, app_store_url, play_url, label="Threads link reply")


def refuse(label, problems, log_path=None):
    """Print the QA refusal as workflow errors and append one JSON line to the link-guard log
    (LINK_GUARD_LOG, or the given path) so the pipeline's alert/action log shows what was held back."""
    for p in problems:
        print(f"::error::{label}: download link guard refused: {p}")
    path = log_path or os.environ.get("LINK_GUARD_LOG")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"label": label, "problems": list(problems)}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return False


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Check that a text carries the app's download link")
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("text")
    ap.add_argument("--app-store", required=True)
    ap.add_argument("--play")
    args = ap.parse_args(argv)
    problems = link_problems(args.text, args.app_store, args.play)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
