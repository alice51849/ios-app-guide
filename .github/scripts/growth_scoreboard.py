#!/usr/bin/env python3
"""Daily public App Store scoreboard for every live App in all 50 locales.

Measures, per localized storefront, the three outcomes external promotion is
meant to move: rating counts, search rank for the App's own native-language
keywords, and position in its category top chart. It also records how many
ratings the current #1 search result has, so the report can point promotion
at the language/storefront pairs where #1 is actually within reach.

Read-only by design: it only calls Apple's public iTunes Lookup/Search API and
the public top-chart RSS feed. It never touches App Store Connect or the Apps.
Requests are paced and the run stops early (keeping its progress) as soon as
Apple signals rate limiting, so the next scheduled run simply continues.
"""

import argparse
import ast
import hashlib
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import portfolio_daily  # noqa: E402

DATA_DIR = REPO_ROOT / "_engine" / "data"
STOREFRONTS_PATH = REPO_ROOT / "_engine" / "geo" / "locale_storefronts.json"
KEY2DATA_SOURCE = REPO_ROOT / "_engine" / "geo" / "build_pages_i18n.py"
# Reviewed "what users really type" terms per App and locale; measured first.
CHALLENGE_TERMS_PATH = REPO_ROOT / ".github" / "growth" / "challenge-terms.json"
# Chart-push targets: every storefront's category chart, measured daily.
FOCUS_PATH = REPO_ROOT / ".github" / "growth" / "focus.json"
FOCUS_KINDS = frozenset(("free", "paid", "grossing"))
REPOSITORY = "alice51849/ios-app-guide"
ISSUE_TITLE = "growth-scoreboard"
ISSUE_LABEL = "growth-scoreboard"
SCHEMA_VERSION = 1
KEYWORDS_PER_LOCALE = 3
SEARCH_LIMIT = 200
CHART_LIMIT = 200
HISTORY_DAYS = 180
ISSUE_BODY_LIMIT = 60000
USER_AGENT = (
    "LumiStudio-growth-scoreboard/1.0 "
    "(+https://open.cait518.cc/ios-app-guide)"
)
LOOKUP_URL = "https://itunes.apple.com/lookup"
SEARCH_URL = "https://itunes.apple.com/search"
CHART_URL = "https://itunes.apple.com/{cc}/rss/top{kind}applications/limit={limit}/genre={genre}/json"
KEYWORD_SPLIT = re.compile(r"[,，、;；]+")
APP_ID_RE = re.compile(r"[0-9]{6,12}")
RATE_LIMIT_STATUSES = frozenset((403, 429))
TRANSIENT_STATUSES = frozenset((408, 500, 502, 503, 504))


class RateLimited(RuntimeError):
    """Apple asked us to slow down; stop this run and keep progress."""


class FetchError(RuntimeError):
    """A single request failed after bounded retries."""


# ---------------------------------------------------------------- sources


def load_key2data(path=KEY2DATA_SOURCE):
    """Read the engine's registry-key → data-file map without importing it."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "KEY2DATA"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict):
                return {str(k): str(v) for k, v in value.items()}
    raise ValueError("KEY2DATA mapping not found in engine source")


def load_storefronts(path=STOREFRONTS_PATH):
    with open(path, encoding="utf-8") as handle:
        mapping = json.load(handle)
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("locale storefront map is empty")
    for locale, country in mapping.items():
        if not re.fullmatch(r"[a-z]{2}", str(country)):
            raise ValueError(f"invalid storefront for {locale}: {country!r}")
    return {str(k): str(v) for k, v in mapping.items()}


def split_keywords(raw, limit=KEYWORDS_PER_LOCALE):
    seen = []
    for part in KEYWORD_SPLIT.split(str(raw or "")):
        term = " ".join(part.split())
        if term and term.casefold() not in {item.casefold() for item in seen}:
            seen.append(term)
        if len(seen) >= limit:
            break
    return seen


def load_keywords(app_key, key2data, data_dir=DATA_DIR, limit=KEYWORDS_PER_LOCALE):
    """Return {locale: [keyword, ...]} from the App's curated 50-locale copy."""
    path = Path(data_dir) / (key2data.get(app_key) or f"{app_key}_full.json")
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    keywords = {}
    for locale, copy in document.items():
        if isinstance(copy, dict):
            terms = split_keywords(copy.get("keywords"), limit)
            if terms:
                keywords[str(locale)] = terms
    return keywords


def load_challenge_terms(path=CHALLENGE_TERMS_PATH, limit=5):
    """{app_key: {locale: [term, ...]}} from the reviewed challenge-term file."""
    path = Path(path)
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    terms = {}
    for app_key, per_locale in (document.get("apps") or {}).items():
        if not isinstance(per_locale, dict):
            continue
        for locale, values in per_locale.items():
            cleaned = split_keywords(",".join(str(v) for v in values or []), limit)
            if cleaned:
                terms.setdefault(str(app_key), {})[str(locale)] = cleaned
    return terms


def load_focus(path=FOCUS_PATH, today=None, app_ids=None):
    """Active chart-push targets from focus.json (expired or unknown ones dropped)."""
    path = Path(path)
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    today = today or dt.date.today().isoformat()
    focus = []
    for row in document.get("apps") or []:
        app_id = str(row.get("app_id") or "")
        genre_id = str(row.get("genre_id") or "")
        if not APP_ID_RE.fullmatch(app_id) or not genre_id.isdigit():
            continue
        if app_ids is not None and app_id not in app_ids:
            continue
        if str(row.get("until") or "9999-12-31") < today:
            continue
        kinds = [kind for kind in row.get("kinds") or ["free"] if kind in FOCUS_KINDS]
        focus.append({
            "app_id": app_id,
            "genre_id": genre_id,
            "genre": str(row.get("genre") or ""),
            "kinds": kinds or ["free"],
            "goal": int(row.get("goal") or 3),
        })
    return focus


def build_tasks(apps, storefronts, keywords_by_app, challenge_terms=None):
    """Search tasks: reviewed challenge terms first, then a first pass over each
    App's top listing keyword in every locale before any second keyword."""
    depth = max(
        (len(terms) for per_locale in keywords_by_app.values() for terms in per_locale.values()),
        default=0,
    )
    tasks = []
    seen = set()
    for app in apps:
        for locale, terms in sorted((challenge_terms or {}).get(app.key, {}).items()):
            if locale not in storefronts:
                continue
            for term in terms:
                task = {
                    "app_id": app.app_id,
                    "app_key": app.key,
                    "locale": locale,
                    "country": storefronts[locale],
                    "keyword": term,
                    "source": "challenge",
                }
                if task_id(task) not in seen:
                    seen.add(task_id(task))
                    tasks.append(task)
    for index in range(depth):
        for locale in sorted(storefronts):
            for app in apps:
                terms = keywords_by_app.get(app.key, {}).get(locale, [])
                if index < len(terms):
                    task = {
                        "app_id": app.app_id,
                        "app_key": app.key,
                        "locale": locale,
                        "country": storefronts[locale],
                        "keyword": terms[index],
                        "source": "listing",
                    }
                    if task_id(task) not in seen:
                        seen.add(task_id(task))
                        tasks.append(task)
    return tasks


def task_id(task):
    return f"{task['app_id']}|{task['locale']}|{task['keyword']}"


def tasks_digest(tasks):
    return hashlib.sha256("\n".join(task_id(task) for task in tasks).encode("utf-8")).hexdigest()


def take_rotation(items, cursor, budget):
    """Return (slice, next_cursor) walking a ring of items from cursor."""
    if not items or budget <= 0:
        return [], cursor
    start = cursor % len(items)
    count = min(budget, len(items))
    picked = [items[(start + offset) % len(items)] for offset in range(count)]
    return picked, (start + count) % len(items)


# ---------------------------------------------------------------- network


class Fetcher:
    def __init__(self, *, delay=3.1, opener=None, sleeper=None, attempts=3):
        self.delay = delay
        self.opener = opener or urllib.request.urlopen
        self.sleeper = sleeper or time.sleep
        self.attempts = attempts
        self.requests = 0
        self._last = None

    def _pace(self):
        if self._last is not None and self.delay > 0:
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                self.sleeper(wait)
        self._last = time.monotonic()

    def get_json(self, url):
        last_error = None
        for attempt in range(self.attempts):
            self._pace()
            self.requests += 1
            request = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            try:
                with self.opener(request, timeout=30) as response:
                    raw = response.read()
                return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            except urllib.error.HTTPError as error:
                if error.code in RATE_LIMIT_STATUSES:
                    raise RateLimited(f"HTTP {error.code} from Apple") from error
                last_error = error
                if error.code not in TRANSIENT_STATUSES:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError) as error:
                last_error = error
            self.sleeper(min(30, 5 * (attempt + 1)))
        raise FetchError(f"{url}: {last_error}")


def lookup_storefront(fetcher, app_ids, country):
    """{app_id: {count, rating, genre_id, genre, price}} for one storefront."""
    found = {}
    ids = sorted(app_ids)
    for start in range(0, len(ids), 100):
        query = urllib.parse.urlencode({
            "id": ",".join(ids[start:start + 100]),
            "country": country,
            "entity": "software",
        })
        payload = fetcher.get_json(f"{LOOKUP_URL}?{query}")
        for row in payload.get("results", []):
            app_id = str(row.get("trackId") or "")
            if app_id not in app_ids:
                continue
            found[app_id] = {
                "count": int(row.get("userRatingCount") or 0),
                "rating": round(float(row.get("averageUserRating") or 0), 2),
                "genre_id": str(row.get("primaryGenreId") or ""),
                "genre": str(row.get("primaryGenreName") or ""),
                "price": float(row.get("price") or 0),
            }
    return found


def search_storefront(fetcher, term, country, app_ids):
    """Our ranks for a native-language search plus the current #1 result."""
    query = urllib.parse.urlencode({
        "term": term,
        "country": country,
        "entity": "software",
        "limit": SEARCH_LIMIT,
    })
    payload = fetcher.get_json(f"{SEARCH_URL}?{query}")
    results = payload.get("results", [])
    ranks = {}
    for position, row in enumerate(results, start=1):
        app_id = str(row.get("trackId") or "")
        if app_id in app_ids and app_id not in ranks:
            ranks[app_id] = position
    top = None
    if results:
        first = results[0]
        top = {
            "id": str(first.get("trackId") or ""),
            "name": str(first.get("trackName") or "")[:80],
            "ratings": int(first.get("userRatingCount") or 0),
        }
    return {"ranks": ranks, "top": top, "result_count": len(results)}


def chart_storefront(fetcher, country, genre_id, kind):
    """Ordered App IDs of one storefront's category top chart."""
    url = CHART_URL.format(cc=country, kind=kind, limit=CHART_LIMIT, genre=genre_id)
    payload = fetcher.get_json(url)
    entries = payload.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    ordered = []
    for entry in entries:
        app_id = str(
            entry.get("id", {}).get("attributes", {}).get("im:id") or ""
        )
        # Keep a placeholder so one malformed entry never shifts later ranks.
        ordered.append(app_id if APP_ID_RE.fullmatch(app_id) else None)
    return ordered


# ---------------------------------------------------------------- state


def empty_state():
    return {
        "schema_version": SCHEMA_VERSION,
        "cursor": 0,
        "chart_cursor": 0,
        "ratings": {},
        "ratings_history": [],
        "search": {},
        "charts": {},
        "focus": {},
    }


def load_state(path):
    path = Path(path)
    if not path.is_file():
        return empty_state()
    with path.open(encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("schema_version") != SCHEMA_VERSION:
        return empty_state()
    base = empty_state()
    base.update(state)
    return base


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(path.suffix + ".writing")
    staging.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(staging, path)


def total_ratings(state, app_ids=None):
    return sum(
        cell.get("count", 0)
        for app_id, per_country in state["ratings"].items()
        if app_ids is None or app_id in app_ids
        for cell in per_country.values()
    )


def record_history(state, today, total):
    history = [row for row in state["ratings_history"] if row.get("date") != today]
    history.append({"date": today, "total": total})
    state["ratings_history"] = sorted(history, key=lambda row: row["date"])[-HISTORY_DAYS:]


def previous_total(state, today):
    earlier = [row for row in state["ratings_history"] if row.get("date") < today]
    return earlier[-1]["total"] if earlier else None


# ---------------------------------------------------------------- run


def measure_focus(focus, countries, state, fetcher, outcome, date, note_error):
    """Today's position of each focus App in every storefront's category chart."""
    for target in focus:
        positions = {}
        for country in countries:
            for kind in target["kinds"]:
                try:
                    ordered = chart_storefront(fetcher, country, target["genre_id"], kind)
                except FetchError as error:
                    note_error(error)
                    continue
                outcome["focus_charts"] += 1
                if target["app_id"] in ordered:
                    positions[f"{country}|{kind}"] = ordered.index(target["app_id"]) + 1
        history = state.setdefault("focus", {}).setdefault(target["app_id"], [])
        history[:] = [row for row in history if row.get("date") != date]
        history.append({"date": date, "positions": positions})
        history.sort(key=lambda row: row["date"])
        del history[:-HISTORY_DAYS]


def run(apps, storefronts, keywords_by_app, state, fetcher, *, now,
        search_budget, chart_budget, log=print, challenge_terms=None, focus=None):
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    app_ids = {app.app_id for app in apps}
    countries = sorted(set(storefronts.values()))
    outcome = {"lookups": 0, "searches": 0, "charts": 0, "focus_charts": 0,
               "rate_limited": None, "errors": 0, "charts_unavailable": False}
    genre_by_app = {}
    tasks = build_tasks(apps, storefronts, keywords_by_app, challenge_terms)
    # A changed task list (new challenge terms, roster or keywords) restarts the
    # rotation so newly reviewed terms are measured first instead of weeks later.
    digest = tasks_digest(tasks)
    if state.get("tasks_digest") != digest:
        state["cursor"] = 0
        state["tasks_digest"] = digest
    search_start = state.get("cursor", 0)
    searched = None  # becomes a count once the search phase starts

    def note_error(error):
        outcome["errors"] += 1
        log(f"scoreboard: {error}")

    try:
        for country in countries:
            try:
                rows = lookup_storefront(fetcher, app_ids, country)
            except FetchError as error:
                note_error(error)
                continue
            outcome["lookups"] += 1
            for app_id, row in rows.items():
                state["ratings"].setdefault(app_id, {})[country] = {
                    "count": row["count"], "rating": row["rating"], "observed_at": stamp,
                }
                if row["genre_id"]:
                    kind = "free" if row["price"] == 0 else "paid"
                    genre_by_app.setdefault(app_id, (row["genre_id"], row["genre"], kind))

        measure_focus(focus or [], countries, state, fetcher, outcome,
                      now.date().isoformat(), note_error)

        chart_keys = sorted({
            (country, genre_id, genre, kind)
            for app_id, (genre_id, genre, kind) in genre_by_app.items()
            for country in countries
        })
        picked, state["chart_cursor"] = take_rotation(
            chart_keys, state.get("chart_cursor", 0), chart_budget
        )
        consecutive_failures = 0
        for country, genre_id, genre, kind in picked:
            try:
                ordered = chart_storefront(fetcher, country, genre_id, kind)
            except FetchError as error:
                note_error(error)
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    outcome["charts_unavailable"] = True
                    break
                continue
            consecutive_failures = 0
            outcome["charts"] += 1
            state["charts"][f"{country}|{genre_id}|{kind}"] = {
                "genre": genre,
                "positions": {
                    app_id: position
                    for position, app_id in enumerate(ordered, start=1)
                    if app_id in app_ids
                },
                "observed_at": stamp,
            }

        picked, next_cursor = take_rotation(tasks, search_start, search_budget)
        searched = 0
        for task in picked:
            try:
                result = search_storefront(fetcher, task["keyword"], task["country"], app_ids)
            except FetchError as error:
                note_error(error)
                searched += 1
                continue
            searched += 1
            outcome["searches"] += 1
            state["search"][task_id(task)] = {
                "app_id": task["app_id"],
                "locale": task["locale"],
                "country": task["country"],
                "keyword": task["keyword"],
                "rank": result["ranks"].get(task["app_id"]),
                "top": result["top"],
                "observed_at": stamp,
            }
        state["cursor"] = next_cursor
    except RateLimited as error:
        outcome["rate_limited"] = str(error)
        log(f"scoreboard: stopped early, progress kept ({error})")
        if searched is not None and tasks:
            state["cursor"] = (search_start + searched) % len(tasks)
    outcome["tasks_total"] = len(tasks)
    record_history(state, now.date().isoformat(), total_ratings(state, app_ids))
    return outcome


# ---------------------------------------------------------------- report


def _cell(text):
    return str(text).replace("|", "／").replace("\n", " ")


def opportunities(state, names, limit=25):
    """Pairs where #1 looks reachable: we already rank, the leader is small."""
    rows = []
    for entry in state["search"].values():
        rank = entry.get("rank")
        top = entry.get("top") or {}
        if not rank or rank == 1 or rank > 30:
            continue
        leader = int(top.get("ratings") or 0)
        score = (31 - rank) * 10 + max(0, 300 - min(leader, 300)) / 10
        rows.append((score, entry, leader))
    rows.sort(key=lambda row: (-row[0], row[1]["country"], row[1]["keyword"]))
    return rows[:limit]


KIND_ZH = {"free": "免費", "paid": "付費", "grossing": "營收"}


def focus_lines(focus, names, state, date):
    """Chart-push section: where each focus App stands versus its goal."""
    lines = []
    for target in focus:
        history = state.get("focus", {}).get(target["app_id"]) or []
        today = next((row["positions"] for row in history if row["date"] == date), None)
        if today is None:
            continue
        earlier = [row for row in history if row["date"] < date]
        before = earlier[-1]["positions"] if earlier else {}
        goal = target["goal"]
        name = names.get(target["app_id"], target["app_id"])
        reached = sorted(key for key, position in today.items() if position <= goal)
        lines += [
            f"## 衝榜目標：{_cell(name)}（{_cell(target['genre'])} 榜前 {goal} 名）",
            "",
            f"- 今天上榜：**{len(today)}** 個店面榜；達標（前 {goal} 名）：**{len(reached)}** 個"
            + (f"（{'、'.join(k.split('|')[0].upper() + KIND_ZH.get(k.split('|')[1], '') for k in reached)}）" if reached else ""),
            "",
        ]
        if today:
            lines += ["| 店面 | 榜 | 今天 | 前次 | 變化 |", "|---|---|---|---|---|"]
            for key, position in sorted(today.items(), key=lambda item: (item[1], item[0]))[:25]:
                country, kind = key.split("|")
                prior = before.get(key)
                change = "新上榜" if prior is None else (f"{prior - position:+d}" if prior != position else "—")
                lines.append(f"| {country.upper()} | {KIND_ZH.get(kind, kind)} | {position} | {prior or '—'} | {change} |")
        else:
            lines.append(f"今天所有店面的 {_cell(target['genre'])} 榜前 100 名都還沒有它。")
        lines.append("")
    return lines


def build_report(apps, state, outcome, *, now, focus=None):
    names = {app.app_id: app.name for app in apps}
    app_ids = set(names)
    total = total_ratings(state, app_ids)
    before = previous_total(state, now.date().isoformat())
    delta = "首次量測" if before is None else f"{total - before:+d}"
    measured = [e for e in state["search"].values() if e.get("app_id") in app_ids]
    firsts = sorted(
        (e for e in measured if e.get("rank") == 1),
        key=lambda e: (names[e["app_id"]], e["country"], e["keyword"]),
    )
    top10 = [e for e in measured if e.get("rank") and e["rank"] <= 10]
    chart_rows = sorted(
        (
            (position, app_id, key.split("|")[0], cell.get("genre", ""), key.split("|")[2])
            for key, cell in state["charts"].items()
            for app_id, position in cell.get("positions", {}).items()
            if app_id in app_ids
        ),
    )
    lines = [
        "# 成長成績單（每天自動更新）",
        "",
        f"更新：{now.strftime('%Y-%m-%d %H:%M')} UTC。資料來源為 Apple 公開的 iTunes Lookup/Search API 與排行榜 RSS，"
        "全程唯讀，不碰 App Store Connect、也不碰 App 本身。",
        "",
        "## 總覽",
        "",
        f"- {len(apps)} 款 App、{len({c for per in state['ratings'].values() for c in per})} 個店面的評分總數：**{total}**（較上次 {delta}）",
        f"- 母語關鍵字排名已量測 {len(measured)}／{outcome.get('tasks_total', 0)} 組（本次 {outcome['searches']} 組，每天接續輪替）",
        f"- 搜尋第 1 名：**{len(firsts)}** 組；前 10 名：**{len(top10)}** 組；類別排行榜前 {CHART_LIMIT} 名上榜：**{len(chart_rows)}** 次",
    ]
    if outcome.get("rate_limited"):
        lines.append(f"- 本次因 Apple 限流提前停止，進度已保存，下次自動接續（{_cell(outcome['rate_limited'])}）")
    if outcome.get("charts_unavailable"):
        lines.append("- 排行榜 RSS 本次無法取得，下次自動重試")
    if focus:
        lines += [""] + focus_lines(focus, names, state, now.date().isoformat())
    lines += ["", "## 已拿到搜尋第 1 名", ""]
    if firsts:
        lines += ["| App | 店面 | 語系 | 關鍵字 |", "|---|---|---|---|"]
        lines += [
            f"| {_cell(names[e['app_id']])} | {e['country'].upper()} | {e['locale']} | {_cell(e['keyword'])} |"
            for e in firsts[:60]
        ]
    else:
        lines.append("目前還沒有。下面的「最接近第 1 名」就是最該集中火力的地方。")
    lines += [
        "",
        "## 最接近第 1 名的機會（外宣優先投放這些語言／國家）",
        "",
        "我們已經排進前 30 名，而且第 1 名的評分數不多。這類組合只要從該語言社群導入少量真實下載，就有機會登頂。",
        "",
    ]
    rows = opportunities(state, names)
    if rows:
        lines += ["| App | 店面 | 關鍵字 | 我們名次 | 目前第 1 名 | 第 1 名評分數 |", "|---|---|---|---|---|---|"]
        lines += [
            f"| {_cell(names[e['app_id']])} | {e['country'].upper()} ({e['locale']}) | {_cell(e['keyword'])} | {e['rank']} "
            f"| {_cell((e.get('top') or {}).get('name', ''))} | {leader} |"
            for _, e, leader in rows
        ]
    else:
        lines.append("量測累積中。")
    lines += ["", "## 類別排行榜", ""]
    if chart_rows:
        lines += ["| App | 店面 | 類別 | 榜單 | 名次 |", "|---|---|---|---|---|"]
        lines += [
            f"| {_cell(names[app_id])} | {country.upper()} | {_cell(genre)} | {'免費' if kind == 'free' else '付費'} | {position} |"
            for position, app_id, country, genre, kind in chart_rows[:80]
        ]
    else:
        lines.append(f"目前沒有 App 進入已量測類別的前 {CHART_LIMIT} 名。")
    lines += ["", "## 每款 App", "", "| App | 評分總數 | 有評分的店面 | 最佳搜尋名次 | 最佳類別名次 |", "|---|---|---|---|---|"]
    per_app = []
    for app in apps:
        per_country = state["ratings"].get(app.app_id, {})
        count = sum(cell.get("count", 0) for cell in per_country.values())
        rated = sum(1 for cell in per_country.values() if cell.get("count", 0) > 0)
        ranks = [
            (e["rank"], e["country"], e["keyword"])
            for e in measured if e["app_id"] == app.app_id and e.get("rank")
        ]
        best = min(ranks) if ranks else None
        charts = [row for row in chart_rows if row[1] == app.app_id]
        per_app.append((
            -count, app.name,
            f"| {_cell(app.name)} | {count} | {rated} "
            f"| {f'{best[0]}（{best[1].upper()}「{_cell(best[2])}」）' if best else '—'} "
            f"| {f'{charts[0][0]}（{charts[0][2].upper()}）' if charts else '—'} |",
        ))
    lines += [row[2] for row in sorted(per_app)]
    lines += [
        "",
        "---",
        "由 `.github/workflows/growth-scoreboard.yml` 產生。完整數據在該次執行的 artifact。",
    ]
    report = "\n".join(lines) + "\n"
    if len(report) > ISSUE_BODY_LIMIT:
        report = report[:ISSUE_BODY_LIMIT - 40].rsplit("\n", 1)[0] + "\n\n（內容過長，已截斷）\n"
    return report


# ---------------------------------------------------------------- GitHub issue


def _github(method, path, token, body=None, opener=None):
    opener = opener or urllib.request.urlopen
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    with opener(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8") or "null")


def publish_issue(report, token, opener=None):
    issues = _github(
        "GET", f"issues?state=open&labels={ISSUE_LABEL}&per_page=10", token, opener=opener
    )
    for issue in issues or []:
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            _github("PATCH", f"issues/{issue['number']}", token, {"body": report}, opener=opener)
            return issue["number"]
    created = _github(
        "POST", "issues", token,
        {"title": ISSUE_TITLE, "body": report, "labels": [ISSUE_LABEL]},
        opener=opener,
    )
    return created["number"]


# ---------------------------------------------------------------- CLI


def load_inputs():
    apps = sorted(portfolio_daily.load_public_apps(), key=lambda app: app.key)
    if not apps:
        raise ValueError("no public Apps in the deployed linkset")
    storefronts = load_storefronts()
    key2data = load_key2data()
    keywords = {app.key: load_keywords(app.key, key2data) for app in apps}
    return apps, storefronts, keywords, load_challenge_terms()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--search-budget", type=int, default=600)
    parser.add_argument("--chart-budget", type=int, default=150)
    parser.add_argument("--delay", type=float, default=3.1)
    parser.add_argument("--issue", action="store_true",
                        help="update the growth-scoreboard issue (needs GITHUB_TOKEN)")
    parser.add_argument("--plan-only", action="store_true",
                        help="print the measurement plan without any network call")
    args = parser.parse_args(argv)

    apps, storefronts, keywords, challenge = load_inputs()
    tasks = build_tasks(apps, storefronts, keywords, challenge)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    focus = load_focus(today=now.date().isoformat(), app_ids={app.app_id for app in apps})
    if args.plan_only:
        missing = sorted(app.key for app in apps if not keywords.get(app.key))
        print(json.dumps({
            "apps": len(apps),
            "locales": len(storefronts),
            "storefronts": len(set(storefronts.values())),
            "search_tasks": len(tasks),
            "challenge_tasks": sum(1 for task in tasks if task["source"] == "challenge"),
            "focus_charts": sum(len(target["kinds"]) for target in focus) * len(set(storefronts.values())),
            "apps_without_keywords": missing,
            "first_tasks": tasks[:5],
        }, ensure_ascii=False, indent=2))
        return 0

    state = load_state(args.state)
    fetcher = Fetcher(delay=args.delay)
    outcome = run(apps, storefronts, keywords, state, fetcher, now=now,
                  search_budget=args.search_budget, chart_budget=args.chart_budget,
                  challenge_terms=challenge, focus=focus)
    save_state(args.state, state)
    report = build_report(apps, state, outcome, now=now, focus=focus)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps({"outcome": outcome, "state": state}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    print(json.dumps({**outcome, "requests": fetcher.requests}, ensure_ascii=False))
    if args.issue:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required with --issue")
        number = publish_issue(report, token)
        print(f"scoreboard issue #{number} updated")
    if outcome["lookups"] == 0 and outcome["searches"] == 0 and not outcome["rate_limited"]:
        print("scoreboard: no Apple endpoint answered", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
