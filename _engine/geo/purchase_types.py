#!/usr/bin/env python3
"""每款 App 已證實的購買類型（買斷／一次解鎖／訂閱／免費／不知道）。

為什麼要有這支：指南站各種版型會依登錄檔的 ``purchase_model`` 寫
「Pay once」「No subscription」「一次買斷」「終生」「買い切り」這類價格字樣。
登錄檔是人填的；這些字樣必須有證據才能寫，否則就是不實價格字樣。

正本資料是 ``geo/data/verified_purchase_types.json``（已提交，指南站鏡像
``_engine/geo/data`` 也讀得到）。它由本機才有的三份資料重建：

1. ``support_network/monetization_cache.json``：App Store Connect 唯讀 GET
   （inAppPurchasesV2 的 inAppPurchaseType＋state、subscriptionGroups）。
   有核准的 NON_CONSUMABLE 而且沒有任何訂閱群組 → 一次解鎖。
2. ``shorts/store_prices.json``：商店售價；沒有內購、售價大於 0 → 付費下載。
3. ``data/<key>_full.json`` 的 en-US 商店描述：快照裡沒有的款，只有在商店
   文案自己寫明一次購買（one-time／one-off／lifetime／buy … once）而且沒有
   訂閱字樣時才算一次解鎖。

其餘一律「unknown」，各產生器對 unknown 與 subscription 的款不寫任何買斷字樣。

    python3 geo/purchase_types.py --build   # 從上述資料重建 json（只在 00_GrowthEngine）
    python3 geo/purchase_types.py           # 列出各類型款數
"""

from __future__ import annotations

import argparse
import json
import re
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data" / "verified_purchase_types.json"

ONE_TIME_UNLOCK = "one_time_unlock"
PAID_UPFRONT = "paid_upfront"
SUBSCRIPTION = "subscription"
FREE = "free"
UNKNOWN = "unknown"
TYPES = {ONE_TIME_UNLOCK, PAID_UPFRONT, SUBSCRIPTION, FREE, UNKNOWN}

# 版型裡會出現的買斷／無訂閱字樣（各語系）。非證實買斷款的頁面不得出現。
PURCHASE_CLAIM_RE = re.compile(
    r"pay once|paid once|one[- ]time (?:purchase|unlock|payment)|one-off purchase"
    r"|no subscription|without (?:a )?subscription|lifetime (?:pro|unlock|purchase)"
    r"|一次買斷|一次买断|買斷|买断|終生|终生|一次付費|一次付费|永久解鎖|永久解锁"
    r"|免訂閱|無訂閱|无订阅|不用訂閱|買い切り|サブスクなし|サブスク不要"
    r"|평생|일회성|구독\s?없",
    re.IGNORECASE,
)

_STORE_ONE_TIME = re.compile(
    r"one-time|one-off|lifetime|non-consumable|single purchase|pay once"
    r"|buy [\w ]{1,20} once|never a subscription|one purchase includes|no in-app purchases",
    re.IGNORECASE,
)
_STORE_SUBSCRIPTION_OFFER = re.compile(
    r"auto-renew|per month|per year|/month|/year|monthly subscription"
    r"|yearly subscription|annual subscription|weekly subscription"
    r"|subscription (?:plan|price|renews)",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    apps = payload.get("apps") if isinstance(payload, dict) else None
    return apps if isinstance(apps, dict) else {}


def purchase_type(key: str) -> str:
    value = (load().get(key) or {}).get("type", UNKNOWN)
    return value if value in TYPES else UNKNOWN


def one_time_verified(key: str) -> bool:
    """有證據是一次購買（一次解鎖內購或付費下載）才回 True。"""
    return purchase_type(key) in {ONE_TIME_UNLOCK, PAID_UPFRONT}


def no_subscription_verified(key: str) -> bool:
    return purchase_type(key) in {ONE_TIME_UNLOCK, PAID_UPFRONT, FREE}


def is_purchase_claim(text: str) -> bool:
    return bool(PURCHASE_CLAIM_RE.search(str(text or "")))


def _store_description(key: str) -> str:
    path = ROOT / "data" / f"{key}_full.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    loc = data.get("en-US") if isinstance(data, dict) else None
    return str((loc or {}).get("description") or "")


def _en_price(prices: dict, key: str):
    entry = (prices.get(key) or {}).get("en") or {}
    return entry.get("price")


def classify(key: str, cache: dict, prices: dict, fetched: str) -> dict[str, str]:
    entry = cache.get(key)
    price = _en_price(prices, key)
    if isinstance(entry, dict):
        if entry.get("subscription"):
            return {"type": SUBSCRIPTION, "evidence": f"ASC 有訂閱群組或非一次性內購（{fetched}）"}
        if entry.get("unlock_iap"):
            products = ",".join(entry.get("products") or [])
            return {
                "type": ONE_TIME_UNLOCK,
                "evidence": f"ASC 核准 NON_CONSUMABLE（{products}）、0 個訂閱群組（{fetched}）",
            }
        if not entry.get("products"):
            if isinstance(price, (int, float)) and price > 0:
                return {"type": PAID_UPFRONT, "evidence": f"ASC 0 內購＋商店售價 USD {price}（{fetched}）"}
            if price == 0:
                return {"type": FREE, "evidence": f"ASC 0 內購＋商店免費（{fetched}）"}
        return {"type": UNKNOWN, "evidence": "ASC 快照內購資料無法判定"}
    desc = _store_description(key)
    if desc and _STORE_ONE_TIME.search(desc) and not _STORE_SUBSCRIPTION_OFFER.search(desc):
        if isinstance(price, (int, float)) and price > 0:
            return {"type": PAID_UPFRONT, "evidence": f"商店售價 USD {price}＋en-US 商店描述寫明一次購買"}
        return {"type": ONE_TIME_UNLOCK, "evidence": "en-US 商店描述寫明一次購買解鎖、無訂閱字樣"}
    return {"type": UNKNOWN, "evidence": "沒有 ASC 快照，商店描述也沒寫明一次購買"}


def build() -> dict:
    import sys

    sys.path.insert(0, str(ROOT / "social"))
    from videogen.registry import APPSTORE  # noqa: E402

    monet = json.loads((ROOT / "support_network" / "monetization_cache.json").read_text(encoding="utf-8"))
    prices = json.loads((ROOT / "shorts" / "store_prices.json").read_text(encoding="utf-8")).get("prices", {})
    fetched = time.strftime("%Y-%m-%d", time.gmtime(float(monet.get("fetched_at") or 0)))
    cache = monet.get("apps") or {}
    apps = {key: classify(key, cache, prices, fetched) for key in sorted(APPSTORE)}
    return {
        "_doc": "由 geo/purchase_types.py --build 產生；只有 one_time_unlock／paid_upfront 可寫買斷字樣",
        "sources": {
            "monetization_cache_fetched": fetched,
            "store_prices_fetched": json.loads(
                (ROOT / "shorts" / "store_prices.json").read_text(encoding="utf-8")
            ).get("fetched", ""),
        },
        "apps": apps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.build:
        payload = build()
        DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        load.cache_clear()
    counts: dict[str, int] = {}
    for value in load().values():
        counts[value.get("type", UNKNOWN)] = counts.get(value.get("type", UNKNOWN), 0) + 1
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
