#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev.to 自動發文 — 防重複且嚴格遵守每篇至少間隔 72 小時。"""
import datetime as _dt
import json
import os
import re
import sys
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


def me(key):
    req = urllib.request.Request(
        "https://dev.to/api/users/me",
        headers={"api-key": key, "User-Agent": UA},
    )
    data = request_json(
        req,
        label="Dev.to profile read",
        timeout=25,
        attempts=3,
    )
    if not isinstance(data, dict):
        raise RequestError("Dev.to profile read returned a non-object response")
    return data


def published_articles(username):
    articles = []
    for page in range(1, 21):
        query = urllib.parse.urlencode({
            "username": username,
            "per_page": PAGE_SIZE,
            "page": page,
        })
        req = urllib.request.Request(
            f"https://dev.to/api/articles?{query}",
            headers={"User-Agent": UA},
        )
        data = request_json(
            req,
            label=f"Dev.to published articles read (page {page})",
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


def existing_titles(username):
    return {
        article.get("title", "").strip()
        for article in published_articles(username)
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
    done = {
        article.get("title", "").strip()
        for article in published
    }
    return next(
        (article for article in pool if article["title"].strip() not in done),
        None,
    )


def article_urls(article):
    return list(dict.fromkeys(
        match.rstrip(".,;:")
        for match in re.findall(r"https?://[^\s)\]>]+", article.get("body", ""))
    ))


def next_publishable(pool, published):
    done = {
        article.get("title", "").strip()
        for article in published
    }
    for article in pool:
        if article["title"].strip() in done:
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
    pool_titles = {article["title"].strip() for article in pool}
    matches = [
        article
        for article in published
        if article.get("title", "").strip() in pool_titles
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
        print("missing DEVTO_API_KEY", file=sys.stderr)
        return 1
    try:
        profile = me(key)
        username = profile.get("username", "").strip()
        if not username:
            raise RequestError("Dev.to profile response has no username")
        with open(
            os.path.join(HERE, "devto_articles.json"), encoding="utf-8"
        ) as pool_file:
            pool = json.load(pool_file)
        published = published_articles(username)
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
        if error.status == 403 and error.label == "Dev.to publish":
            print(
                "Dev.to API still gated (HTTP 403 account-age anti-spam); "
                "this run did not publish anything.",
                file=sys.stderr,
            )
            return 0
        print(f"Dev.to post failed: {error}", file=sys.stderr)
        return 1
    except (RequestError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Dev.to post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
