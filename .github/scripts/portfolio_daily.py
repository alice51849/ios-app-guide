#!/usr/bin/env python3
"""Publish an auditable daily digest covering every publicly available app."""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import dataclasses
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from social_post_common import (
    HTTPStatusError,
    RequestError,
    campaign_app_store_url,
    canonical_app_store_url,
    play_store_url,
    request_json,
    validate_url,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ENGINE_SOCIAL = REPO_ROOT / "_engine" / "social"
if str(ENGINE_SOCIAL) not in sys.path:
    sys.path.insert(0, str(ENGINE_SOCIAL))

from videogen.registry import APPS, APPSTORE  # noqa: E402

import telegram_post  # noqa: E402
import threads_post  # noqa: E402

DEVELOPER_URL = "https://apps.apple.com/developer/id1136144960"
SITE_URL = "https://open.cait518.cc/ios-app-guide"
LINKSET_PATH = REPO_ROOT / "linkset.json"
TELEGRAM_LIMIT = 3900
# The portfolio's one real differentiator, stated in every daily digest.
TELEGRAM_LANGUAGE_PITCH = (
    "🌏 每款都支援 50 種語言，App 內一鍵切換、不必改手機語言："
    "家人用中文、看護用印尼文或越南文、孩子用英文，同一支手機各用各的。\n\n"
)
PLAY_LINK_RE = re.compile(r"https://play\.google\.com/store/apps/details\?\S+")
THREADS_LIMIT = threads_post.MAX_POST_CHARS
THREADS_LINK_LIMIT = 5
PORTFOLIO_WORKFLOW = "portfolio-daily.yml"
# The Telegram digest also runs as the `catalog` job of every telegram-daily
# slot (01/09/15 UTC), so a missed or failed run is caught up the same day.
# A successful job of either workflow today means today's digest is out.
TELEGRAM_DAILY_WORKFLOW = "telegram-daily.yml"
TELEGRAM_CATALOG_JOB = "catalog"
DIGEST_JOBS = {
    "telegram": (
        (PORTFOLIO_WORKFLOW, "telegram"),
        (TELEGRAM_DAILY_WORKFLOW, TELEGRAM_CATALOG_JOB),
    ),
    "threads": ((PORTFOLIO_WORKFLOW, "threads"),),
}
# The digest has its own token so its clicks/downloads are not mixed with the
# single-App Telegram posts (soc_tg_guide) in App Store Connect Campaigns.
PLATFORM_CAMPAIGNS = {
    "telegram": "soc_tg_digest",
    "threads": "soc_th_guide",
}

CATEGORY_ORDER = {
    "kids": 0,
    "education": 0,
    "photo-utility": 1,
    "productivity": 2,
    "finance": 3,
    "health": 4,
    "sleep-sound": 4,
    "travel": 5,
    "lifestyle": 6,
    "other": 7,
}
CATEGORY_ZH = {
    "kids": "親子學習",
    "education": "學習進修",
    "utility": "實用工具",
    "photo-utility": "相片工具",
    "productivity": "效率工具",
    "finance": "財務管理",
    "health": "健康生活",
    "sleep-sound": "健康生活",
    "travel": "旅行規劃",
    "lifestyle": "生活工具",
    "other": "更多工具",
}

# One pain-first app story leads each Telegram digest, rotating daily through
# the reviewed zh-Hant posts in .github/growth (own channel, one post a day).
GROWTH_DIR = REPO_ROOT / ".github" / "growth"
SPOTLIGHT_SOURCES = ("fifty-languages-campaign.json", "app-posts.json")
SPOTLIGHT_LANG = "zh-Hant"
SPOTLIGHT_TEXT_LIMIT = 600
# Chart-push targets; while spotlight_until has not passed, they own the spotlight.
FOCUS_FILE = "focus.json"

# Digest-only display fixes for linkset categories that send readers to the
# wrong shelf (adult travel/vocabulary Apps listed as kids' learning, a Wi-Fi
# diagnostic listed as a photo tool). The linkset itself is engine-owned.
DISPLAY_CATEGORY_OVERRIDES = {
    "dailymate": "travel",
    "dailymatelite": "travel",
    "wordmatelite": "education",
    "wifiaid": "utility",
}


class CoverageError(RuntimeError):
    """Raised when a daily digest cannot prove complete public-app coverage."""


@dataclasses.dataclass(frozen=True)
class PublicApp:
    key: str
    app_id: str
    name: str
    category: str

    def appstore_url(self, campaign=None):
        canonical = canonical_app_store_url(
            f"https://apps.apple.com/app/id{self.app_id}"
        )
        return (
            canonical
            if campaign is None
            else campaign_app_store_url(canonical, campaign)
        )

    def play_url(self, campaign):
        """Tracked Google Play link (same ct as the App Store link), or None off Android."""
        return play_store_url(self.app_id, campaign)


@dataclasses.dataclass(frozen=True)
class DigestMessage:
    text: str
    app_ids: tuple[str, ...]


def _title(item):
    titles = item.get("title*") if isinstance(item, dict) else None
    if not isinstance(titles, list):
        raise CoverageError("Live guide is missing title metadata")
    values = [
        str(title.get("value") or "").strip()
        for title in titles
        if isinstance(title, dict)
    ]
    values = [value for value in values if value]
    if not values:
        raise CoverageError("Live guide has an empty title")
    return values[0]


def _guide_slug(href):
    parsed = urllib.parse.urlsplit(href) if isinstance(href, str) else None
    prefix = "/ios-app-guide/guides/"
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.netloc != "open.cait518.cc"
        or not parsed.path.startswith(prefix)
        or parsed.query
        or parsed.fragment
    ):
        raise CoverageError(f"Invalid live guide URL: {href!r}")
    relative = parsed.path[len(prefix) :]
    if "/" in relative or not re.fullmatch(r"[a-z0-9-]+\.html", relative):
        raise CoverageError(f"Invalid live guide path: {href}")
    return relative[:-5]


def _related_app_url(entry):
    related = entry.get("related") if isinstance(entry, dict) else None
    if not isinstance(related, list):
        raise CoverageError("Live guide is missing related links")
    app_urls = []
    for relation in related:
        href = relation.get("href") if isinstance(relation, dict) else None
        parsed = urllib.parse.urlsplit(href) if isinstance(href, str) else None
        if not parsed or parsed.netloc != "apps.apple.com":
            continue
        if parsed.scheme != "https" or parsed.fragment:
            raise CoverageError(f"Invalid App Store relation: {href}")
        bare_url = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, "", "")
        )
        try:
            app_urls.append(canonical_app_store_url(bare_url))
        except ValueError as error:
            raise CoverageError(f"Invalid App Store relation: {href}") from error
    if len(app_urls) != 1:
        raise CoverageError(
            "Each live guide must have exactly one App Store related link"
        )
    return app_urls[0]


def parse_public_apps(payload, apps=APPS, appstore=APPSTORE):
    entries = payload.get("linkset") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise CoverageError("linkset.json has an invalid top-level structure")
    root_anchors = {f"{SITE_URL}/", f"{SITE_URL}/index.html"}
    roots = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("anchor") in root_anchors
        and isinstance(entry.get("item"), list)
    ]
    if len(roots) != 1:
        raise CoverageError("linkset.json must contain one portfolio guide entry")

    registry_by_id = collections.defaultdict(list)
    for key, app_id in appstore.items():
        registry_by_id[str(app_id)].append(key)
    guide_entries = collections.defaultdict(list)
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("anchor"), str):
            guide_entries[entry["anchor"]].append(entry)

    selected = []
    seen_slugs = set()
    seen_ids = set()
    for item in roots[0]["item"]:
        href = item.get("href") if isinstance(item, dict) else None
        slug = _guide_slug(href)
        if slug in seen_slugs:
            raise CoverageError(f"Duplicate live guide slug: {slug}")
        matches = guide_entries[href]
        if len(matches) != 1:
            raise CoverageError(
                f"Live guide must have exactly one linkset context: {href}"
            )
        app_url = _related_app_url(matches[0])
        app_id = urllib.parse.urlsplit(app_url).path.rsplit("id", 1)[1]
        if app_id in seen_ids:
            raise CoverageError(f"Duplicate live App Store ID: {app_id}")
        registry_keys = registry_by_id.get(app_id, [])
        key = slug if slug in apps else (registry_keys[0] if registry_keys else slug)
        metadata = apps.get(key, {})
        selected.append(
            PublicApp(
                key=key,
                app_id=app_id,
                name=_title(item),
                category=str(metadata.get("category") or "other"),
            )
        )
        seen_slugs.add(slug)
        seen_ids.add(app_id)
    if not selected:
        raise CoverageError("linkset.json contains no live apps")
    return sorted(
        selected,
        key=lambda app: (
            CATEGORY_ORDER.get(app.category, CATEGORY_ORDER["other"]),
            app.name.casefold(),
            app.app_id,
        ),
    )


def load_public_apps(path=LINKSET_PATH):
    with open(path, encoding="utf-8") as linkset_file:
        return parse_public_apps(json.load(linkset_file))


def _github_json(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ios-app-guide-portfolio-coverage",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return request_json(
        urllib.request.Request(url, headers=headers),
        label="GitHub Actions coverage history",
        timeout=30,
        attempts=3,
        retry_delays=(1, 2),
    )


def _github_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(dt.timezone.utc)


def already_published_today(
    platform,
    *,
    now=None,
    repository=None,
    current_run_id=None,
    token=None,
    fetcher=_github_json,
):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    today = now.astimezone(dt.timezone.utc).date()
    repository = (
        os.environ.get("GITHUB_REPOSITORY", "")
        if repository is None
        else repository
    )
    current_run_id = (
        os.environ.get("GITHUB_RUN_ID", "")
        if current_run_id is None
        else current_run_id
    )
    token = (
        os.environ.get("GITHUB_TOKEN", "")
        if token is None
        else token
    )
    if not repository or not current_run_id:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise CoverageError(f"Invalid GITHUB_REPOSITORY: {repository!r}")

    base = f"https://api.github.com/repos/{repository}"
    # No status filter: a run still finishing another job (e.g. the market
    # SLA check) may already hold today's successful digest job.
    query = urllib.parse.urlencode({"per_page": "30"})
    jobs_by_workflow = collections.defaultdict(set)
    for workflow, job_name in DIGEST_JOBS.get(
        platform, ((PORTFOLIO_WORKFLOW, platform),)
    ):
        jobs_by_workflow[workflow].add(job_name.casefold())
    for workflow, job_names in jobs_by_workflow.items():
        history = fetcher(
            f"{base}/actions/workflows/{workflow}/runs?{query}",
            token,
        )
        runs = history.get("workflow_runs") if isinstance(history, dict) else None
        if not isinstance(runs, list):
            raise CoverageError("GitHub Actions history has no workflow_runs")
        for run in runs:
            if not isinstance(run, dict) or str(run.get("id")) == str(
                current_run_id
            ):
                continue
            created = _github_time(run.get("created_at"))
            if created and created.date() < today - dt.timedelta(days=1):
                continue
            run_id = run.get("id")
            if not isinstance(run_id, int):
                continue
            jobs_payload = fetcher(
                f"{base}/actions/runs/{run_id}/jobs?filter=all&per_page=100",
                token,
            )
            jobs = (
                jobs_payload.get("jobs")
                if isinstance(jobs_payload, dict)
                else None
            )
            if not isinstance(jobs, list):
                raise CoverageError(
                    f"GitHub Actions run {run_id} has no jobs array"
                )
            for job in jobs:
                if (
                    isinstance(job, dict)
                    and str(job.get("name") or "").casefold() in job_names
                    and job.get("conclusion") == "success"
                ):
                    completed = _github_time(job.get("completed_at"))
                    if completed is None:
                        raise CoverageError(
                            f"Successful {platform} job in run {run_id} "
                            "has no valid completed_at"
                        )
                    if completed.date() == today:
                        print(
                            f"{platform} portfolio already published today "
                            f"by {workflow} run {run_id}; skipping"
                        )
                        return True
    return False


def filter_reachable_apps(apps, validator=validate_url, max_workers=3):
    # 這一步會對 apps.apple.com 連打整個 portfolio(40+ 個 URL)。原本 8 條
    # 併發 + 3 次重試(1s、2s)對 Apple 來說是一陣突刺,GitHub-hosted runner
    # 的共用出口 IP 很容易被回 HTTP 429,整個 Telegram 日報就 fail 掉 ——
    # 2026-08-18 連續兩次都是這樣掛的,而它一天只跑一次、掛了就等於當天沒發。
    # 降低併發並改用較長的指數退避:對 Apple 更客氣,對我們更不容易整批失敗。
    # 這裡只影響「發文前的 URL 可達性檢查」,不改變任何發文頻率或配額。
    apps = list(apps)
    if not apps:
        raise CoverageError("Public app registry is empty")
    worker_count = max(1, min(max_workers, len(apps)))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        futures = {
            app.app_id: executor.submit(
                validator,
                app.appstore_url(),
                timeout=10,
                attempts=6,
                retry_delays=(2, 5, 10, 20, 40),
            )
            for app in apps
        }
        reachable = []
        for app in apps:
            if futures[app.app_id].result():
                reachable.append(app)
            else:
                print(
                    f"Daily portfolio: excluding confirmed dead URL "
                    f"{app.appstore_url()}",
                    file=sys.stderr,
                )
    if not reachable:
        raise CoverageError("Every public App Store URL returned 404/410")
    return reachable


def _pack_apps(
    apps, entry_text, separator, capacity, max_items=None
):
    batches = []
    current = []
    current_size = 0
    for app in apps:
        entry_size = len(entry_text(app))
        added_size = entry_size + (len(separator) if current else 0)
        if current and (
            current_size + added_size > capacity
            or (max_items is not None and len(current) >= max_items)
        ):
            batches.append(current)
            current = []
            current_size = 0
            added_size = entry_size
        if added_size > capacity:
            raise CoverageError(f"Digest entry is too long for {app.name}")
        current.append(app)
        current_size += added_size
    if current:
        batches.append(current)
    return batches


def load_spotlight_posts(apps, directory=None):
    """Reviewed zh-Hant posts for live Apps, in file order, without repeats."""
    names = {app.app_id: app.name for app in apps}
    posts = []
    seen = set()
    for filename in SPOTLIGHT_SOURCES:
        path = Path(directory or GROWTH_DIR) / filename
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as source:
            document = json.load(source)
        for post in document.get("posts", []):
            app_id = str(post.get("app_id") or "")
            text = str(post.get("text") or "").strip()
            if (
                post.get("lang") != SPOTLIGHT_LANG
                or app_id not in names
                or not text
                or len(text) > SPOTLIGHT_TEXT_LIMIT
                or "http" in text
                or text in seen
            ):
                continue
            seen.add(text)
            posts.append({"app_id": app_id, "name": names[app_id], "text": text})
    return posts


def spotlight_focus_ids(day, directory=None):
    path = Path(directory or GROWTH_DIR) / FOCUS_FILE
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8") as source:
        document = json.load(source)
    return {
        str(row.get("app_id") or "")
        for row in document.get("apps") or []
        if str(row.get("spotlight_until") or "") >= day.isoformat()
    }


def spotlight_block(apps, today=None, directory=None, skip_apps=frozenset()):
    # Apps failing the page-ready gate (< 3 screenshots) never take the spotlight.
    posts = [post for post in load_spotlight_posts(apps, directory) if post["app_id"] not in skip_apps]
    if not posts:
        return ""
    day = today or dt.datetime.now(dt.timezone.utc).date()
    focus_ids = spotlight_focus_ids(day, directory)
    posts = [post for post in posts if post["app_id"] in focus_ids] or posts
    post = posts[day.toordinal() % len(posts)]
    # No extra link: the digest keeps one tracked link per App and store (App Store, Google Play).
    return f"🔦 今日焦點｜{post['name']}\n{post['text']}\n（下載連結在下方清單）\n\n"


def telegram_messages(apps, today=None, skip_spotlight_apps=frozenset()):
    total = len(apps)
    campaign = PLATFORM_CAMPAIGNS["telegram"]
    footer = f"\n\n完整開發者頁：{DEVELOPER_URL}"
    spotlight = spotlight_block(apps, today, skip_apps=skip_spotlight_apps)
    reserved_header = (
        f"✨ 每日全 App 精選｜{total} 款｜第 99/99 則\n\n"
        f"{spotlight}"
        f"{TELEGRAM_LANGUAGE_PITCH}"
        "今天已公開的 App 一次看，依需求挑選：\n"
    )

    def entry(app):
        category = CATEGORY_ZH.get(
            DISPLAY_CATEGORY_OVERRIDES.get(app.key, app.category),
            CATEGORY_ZH["other"],
        )
        play = app.play_url(campaign)
        return (
            f"• {category}｜{app.name}\n"
            f"  {app.appstore_url(campaign)}"
            + (f"\n  Google Play: {play}" if play else "")
        )

    batches = _pack_apps(
        apps,
        entry,
        "\n",
        TELEGRAM_LIMIT - len(reserved_header) - len(footer),
    )
    if len(batches) > 99:
        raise CoverageError("Telegram digest requires more than 99 messages")

    messages = []
    for index, batch in enumerate(batches, start=1):
        part = "" if len(batches) == 1 else f"｜第 {index}/{len(batches)} 則"
        header = (
            f"✨ 每日全 App 精選｜{total} 款{part}\n\n"
            f"{spotlight if index == 1 else ''}"
            f"{TELEGRAM_LANGUAGE_PITCH}"
            "今天已公開的 App 一次看，依需求挑選：\n"
        )
        text = header + "\n".join(entry(app) for app in batch) + footer
        if len(text) > TELEGRAM_LIMIT:
            raise CoverageError(f"Telegram digest is too long: {len(text)}")
        messages.append(DigestMessage(text, tuple(app.app_id for app in batch)))
    return messages


def threads_messages(apps):
    total = len(apps)
    campaign = PLATFORM_CAMPAIGNS["threads"]
    footer = ""
    reserved_header = (
        f"Daily portfolio 99/99 — {total} live apps, all included today.\n\n"
    )
    def entry(app):
        return f"{app.name}\n{app.appstore_url(campaign)}"

    batches = _pack_apps(
        apps,
        entry,
        "\n",
        THREADS_LIMIT - len(reserved_header) - len(footer),
        max_items=THREADS_LINK_LIMIT,
    )
    if len(batches) > 99:
        raise CoverageError("Threads digest requires more than 99 posts")

    messages = []
    for index, batch in enumerate(batches, start=1):
        if len(batches) == 1:
            header = (
                f"Today's complete {total}-app lineup — "
                "every live app, every day.\n\n"
            )
        else:
            header = (
                f"Daily portfolio {index}/{len(batches)} — {total} live apps, "
                "all included today.\n\n"
            )
        text = header + "\n".join(entry(app) for app in batch) + footer
        if len(text) > THREADS_LIMIT:
            raise CoverageError(f"Threads digest is too long: {len(text)}")
        messages.append(DigestMessage(text, tuple(app.app_id for app in batch)))
    return messages


def validate_coverage(platform, apps, messages):
    campaign = PLATFORM_CAMPAIGNS.get(platform)
    if campaign is None:
        raise CoverageError(f"Unsupported platform: {platform}")
    expected = [app.app_id for app in apps]
    observed = [
        app_id for message in messages for app_id in message.app_ids
    ]
    counts = collections.Counter(observed)
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    duplicates = sorted(app_id for app_id, count in counts.items() if count != 1)
    if missing or unexpected or duplicates:
        raise CoverageError(
            f"{platform} coverage invalid: missing={missing}, "
            f"unexpected={unexpected}, duplicate_or_repeated={duplicates}"
        )
    by_id = {app.app_id: app for app in apps}
    link_pattern = re.compile(r"https?://apps\.apple\.com/app/id\d+\S*")
    for message in messages:
        expected_urls = [
            by_id[app_id].appstore_url(campaign)
            for app_id in message.app_ids
        ]
        observed_urls = link_pattern.findall(message.text)
        if observed_urls != expected_urls:
            raise CoverageError(
                f"{platform} direct links invalid: "
                f"expected={expected_urls}, observed={observed_urls}"
            )
        for url in observed_urls:
            parsed = urllib.parse.urlsplit(url)
            bare = urllib.parse.urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, "", "")
            )
            if campaign_app_store_url(bare, campaign) != url:
                raise CoverageError(
                    f"{platform} App Store URL attribution is invalid: {url}"
                )
        if platform == "telegram":
            # Every Android-live App also carries its tracked Google Play link.
            expected_play = [
                play
                for play in (
                    by_id[app_id].play_url(campaign) for app_id in message.app_ids
                )
                if play
            ]
            observed_play = PLAY_LINK_RE.findall(message.text)
            if observed_play != expected_play:
                raise CoverageError(
                    f"{platform} Google Play links invalid: "
                    f"expected={expected_play}, observed={observed_play}"
                )


def report_coverage(platform, apps, messages):
    by_id = {app.app_id: app for app in apps}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(
        f"DAILY_COVERAGE date={today} platform={platform} "
        f"apps={len(apps)} batches={len(messages)}"
    )
    report_lines = [
        f"## Daily portfolio coverage — {today}",
        "",
        f"**Platform:** {platform} · **Public apps:** {len(apps)} · "
        f"**Batches:** {len(messages)}",
        "",
        "| Batch | App Store ID | App |",
        "|---:|---|---|",
    ]
    for batch_index, message in enumerate(messages, start=1):
        for app_id in message.app_ids:
            app = by_id[app_id]
            print(f"  batch={batch_index} app_id={app_id} app={app.name}")
            report_lines.append(f"| {batch_index} | {app_id} | {app.name} |")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("\n".join(report_lines) + "\n")


def publish(platform, messages):
    if platform == "telegram":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat:
            raise CoverageError(
                "Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID"
            )
        for message in messages:
            result = telegram_post._send_message(token, chat, message.text)
            if not result.get("ok") or not result.get("result", {}).get("message_id"):
                raise RequestError("Telegram sendMessage returned no message_id")
            print(
                "telegram portfolio posted, message_id:",
                result["result"]["message_id"],
            )
        return

    token = os.environ.get("THREADS_TOKEN", "").strip()
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    if not token or not user_id:
        raise CoverageError("Missing THREADS_TOKEN / THREADS_USER_ID")
    for message in messages:
        post_id = threads_post.publish_text(token, user_id, message.text)
        if not post_id:  # the account cap held it (threads_cap.py said why): the later batches wait too
            return
        print("threads portfolio posted, id:", post_id)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--platform", required=True, choices=("telegram", "threads")
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.dry_run and already_published_today(args.platform):
            return 0
        apps = filter_reachable_apps(load_public_apps())
        messages = (
            telegram_messages(
                apps,
                skip_spotlight_apps=telegram_post.page_unready_apps(app.app_id for app in apps),
            )
            if args.platform == "telegram"
            else threads_messages(apps)
        )
        validate_coverage(args.platform, apps, messages)
        if args.dry_run:
            report_coverage(args.platform, apps, messages)
            for index, message in enumerate(messages, start=1):
                print(f"\n--- {args.platform} batch {index} ---\n{message.text}")
        else:
            publish(args.platform, messages)
            report_coverage(args.platform, apps, messages)
        return 0
    except (
        CoverageError,
        HTTPStatusError,
        RequestError,
        json.JSONDecodeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(f"Daily portfolio coverage failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
