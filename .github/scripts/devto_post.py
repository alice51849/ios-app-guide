#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev.to 自動發文 — 防重複且嚴格遵守每篇至少間隔 72 小時。"""
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from social_post_common import (
    HTTPStatusError,
    RequestError,
    request_json,
    validate_url,
)

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Lumi Apps poster)"
MIN_PUBLISH_INTERVAL = _dt.timedelta(hours=72)
PAGE_SIZE = 100
BUYER_GUIDE_POOL = "devto_buyer_job_articles.json"


def _validate_buyer_guide(article):
    url = article.get("canonical_url", "")
    if not all(isinstance(article.get(field), str) for field in (
        "canonical_url", "source_sha256", "title", "body"
    )):
        raise ValueError("Buyer guide fields must be strings")
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in {"open.cait518.cc", "alice51849.github.io"}
        or not re.fullmatch(
            r"/ios-app-guide/buyer-guides/en-US/[a-z0-9-]+\.html", parsed.path
        )
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"[0-9a-f]{64}", article.get("source_sha256", ""))
        or not article.get("title", "").strip()
        or not article.get("body", "").strip()
    ):
        raise ValueError("Buyer guide needs an exact first-party canonical and source digest")


def load_pool():
    with open(os.path.join(HERE, "devto_articles.json"), encoding="utf-8") as pool_file:
        pool = json.load(pool_file)
    candidate_path = os.path.join(HERE, BUYER_GUIDE_POOL)
    if os.path.isfile(candidate_path):
        with open(candidate_path, encoding="utf-8") as candidate_file:
            candidates = json.load(candidate_file)
        if not isinstance(candidates, list):
            raise ValueError("Buyer guide queue must be a list")
        for article in candidates:
            if not isinstance(article, dict):
                raise ValueError("Malformed buyer guide")
            _validate_buyer_guide(article)
        pool = [*pool, *candidates]
    return pool


def _same_article(candidate, published):
    if candidate["title"].strip() == (published.get("title") or "").strip():
        return True
    canonical = candidate.get("canonical_url")
    return bool(canonical and canonical == published.get("canonical_url"))


def buyer_guide_source_is_live(article):
    if "source_sha256" not in article:
        return True
    _validate_buyer_guide(article)
    url = article["canonical_url"]
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200 or response.geturl() != url:
                return False
            body = response.read(1_048_577)
        return (
            len(body) <= 1_048_576
            and hashlib.sha256(body).hexdigest() == article["source_sha256"]
        )
    except (OSError, urllib.error.URLError):
        return False


def published_articles(key):
    articles = []
    for page in range(1, 21):
        query = urllib.parse.urlencode({
            "per_page": PAGE_SIZE,
            "page": page,
        })
        req = urllib.request.Request(
            f"https://dev.to/api/articles/me/published?{query}",
            headers={"api-key": key, "User-Agent": UA},
        )
        data = request_json(
            req,
            label=f"Dev.to authenticated articles read (page {page})",
            timeout=25,
            attempts=3,
        )
        if not isinstance(data, list):
            raise RequestError("Dev.to articles read returned a non-list response")
        if not all(isinstance(article, dict) for article in data):
            raise RequestError("Dev.to articles read returned a malformed article")
        articles.extend(data)
        if len(data) < PAGE_SIZE:
            return articles
    raise RequestError("Dev.to article pagination exceeded 20 full pages")


def existing_titles(key):
    return {
        article.get("title", "").strip()
        for article in published_articles(key)
    }


def _published_at(article):
    value = article.get("published_timestamp") or article.get("published_at")
    if not value:
        raise RequestError(
            f"Dev.to article has no publication timestamp: "
            f"{article.get('title', '<untitled>')}"
        )
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        timestamp = _dt.datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise RequestError(
            f"Dev.to returned an invalid publication timestamp: {value!r}"
        ) from error
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=_dt.timezone.utc)
    return timestamp.astimezone(_dt.timezone.utc)


def next_unpublished(pool, published):
    return next(
        (article for article in pool
         if not any(_same_article(article, item) for item in published)),
        None,
    )


def article_urls(article):
    return list(dict.fromkeys(
        match.rstrip(".,;:")
        for match in re.findall(r"https?://[^\s)\]>]+", article.get("body", ""))
    ))


def next_publishable(pool, published):
    for article in pool:
        if any(_same_article(article, item) for item in published):
            continue
        if not buyer_guide_source_is_live(article):
            print(
                f"Dev.to: buyer guide is not the exact live source yet: {article['title']}",
                file=sys.stderr,
            )
            continue
        dead = [url for url in article_urls(article) if not validate_url(url)]
        if dead:
            print(
                f"Dev.to: skipping article with unavailable URL: "
                f"{article['title']} ({', '.join(dead)})",
                file=sys.stderr,
            )
            continue
        return article
    return None


def latest_pool_publication(pool, published):
    matches = [
        article
        for article in published
        if any(_same_article(candidate, article) for candidate in pool)
    ]
    return max((_published_at(article) for article in matches), default=None)


def publication_due(pool, published, now=None):
    latest = latest_pool_publication(pool, published)
    if latest is None:
        return True
    now = (
        _dt.datetime.now(_dt.timezone.utc)
        if now is None
        else now
    )
    if now.tzinfo is None:
        now = now.replace(tzinfo=_dt.timezone.utc)
    else:
        now = now.astimezone(_dt.timezone.utc)
    return now - latest >= MIN_PUBLISH_INTERVAL


def _publish(key, article):
    payload = {
        "article": {
            "title": article["title"],
            "published": True,
            "body_markdown": article["body"],
            "tags": article.get("tags", [])[:4],
        }
    }
    if article.get("canonical_url"):
        payload["article"]["canonical_url"] = article["canonical_url"]
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=json.dumps(payload).encode(),
        headers={
            "api-key": key,
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
    )
    return request_json(
        req,
        label="Dev.to publish",
        timeout=40,
        attempts=3,
    )


def main():
    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        print(
            "::error title=Dev.to authorization unavailable::"
            "DEVTO_API_KEY is missing; queue preserved and this run is deferred.",
            file=sys.stderr,
        )
        return 1
    try:
        pool = load_pool()
        published = published_articles(key)
        print(f"Dev.to authenticated history: {len(published)} articles")
        if not next_unpublished(pool, published):
            print("all pool articles already published — nothing to do.")
            return 0
        latest = latest_pool_publication(pool, published)
        now = _dt.datetime.now(_dt.timezone.utc)
        if latest is not None and now - latest < MIN_PUBLISH_INTERVAL:
            remaining = MIN_PUBLISH_INTERVAL - (
                now - latest
            )
            hours = max(0.0, remaining.total_seconds() / 3600)
            print(
                f"72-hour gate active ({hours:.1f}h remaining) — nothing to do."
            )
            return 0
        nxt = next_publishable(pool, published)
        if not nxt:
            print("no unpublished article currently has fully live URLs.")
            return 0
        result = _publish(key, nxt)
        url = result.get("url") if isinstance(result, dict) else None
        if not url:
            raise RequestError("Dev.to publish returned no article URL")
        print("published ok:", url)
        return 0
    except HTTPStatusError as error:
        if error.status == 401 and (
            error.label == "Dev.to publish"
            or error.label.startswith("Dev.to authenticated articles read")
        ):
            print(
                "::error title=Dev.to authorization unavailable::"
                "API key rejected (HTTP 401); queue preserved and future "
                "scheduled runs will retry.",
                file=sys.stderr,
            )
            return 1
        if error.status == 403 and error.label == "Dev.to publish":
            print(
                "::error title=Dev.to publish blocked::"
                "Dev.to API returned HTTP 403 (account-age anti-spam); "
                "this run did not publish anything.",
                file=sys.stderr,
            )
            return 1
        print(f"Dev.to post failed: {error}", file=sys.stderr)
        return 1
    except (RequestError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Dev.to post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
