#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市場可用性單一權威:哪些 locale 根本沒有可驗證的可購買 App Store 頁面。

## 為什麼需要這一份

`app_store_storefronts.REQUIRED_LOCALE_STOREFRONTS` 的註解寫得很對:

    Routing is separate from availability/price evidence. A missing lookup may
    not silently move Bangladesh readers to India or a countryless URL.

意圖正確 —— 不可以把孟加拉讀者悄悄送去別的市場。問題出在它挑的目的地:
`bn-BD` 被對應到 `bd`,而 **Apple 在孟加拉沒有 Apple Media Services**。
結果 `/bd/` 連結會 301 到 **`/us/`**,正是那段註解想避免的事,而且更糟——
使用者看到的是美國商店的幣值與可用性。

## 一手證據(2026-09-12 實測,全部可重跑)

1. **Apple 官方可用性頁**(`https://support.apple.com/en-us/118205`):
   以 `<h3>` 列出 **174 個**國家/地區,**沒有 Bangladesh**。
   同區域的 India、Pakistan、Nepal、Sri Lanka、Bhutan、Myanmar 全部在列;
   B 開頭依序是 Bahamas、Bahrain、Barbados、Belarus…,Bangladesh 該在
   Bahrain 與 Barbados 之間卻不存在。
2. **iTunes lookup,47 個 live app id,`country=BD`**:HTTP 200,`resultCount=0/47`;
   同一批在 `IN`、`US` 都是 47/47。
3. **第三方廣泛可得 App**(WhatsApp / Gmail / Messenger)`country=BD`:0/3;`IN`:3/3。
   → 不是「我們的 App 沒在 BD 上架」,是整個目錄都取不到。
4. **iTunes search `term=whatsapp&country=BD`**:`resultCount=0`;`IN`:3。
5. **無效代碼對照**:`country=XX` 回 **HTTP 400**,而 `BD` 回 **HTTP 200**。
   → `BD` 在語法上被接受,語意上沒有目錄;不是「lookup 不支援這個參數」。
6. **Web storefront**:`https://apps.apple.com/bd/` → 301 → `https://apps.apple.com/us/iphone/today`;
   `https://apps.apple.com/bd/app/id…` → 301 → `https://apps.apple.com/us/app/…`。
   對照 `https://apps.apple.com/in/` → 301 → `/in/iphone/today`(留在原市場)。

## 三種狀態必須分開,不可混為一談

- `MARKET_NOT_IN_APPLE_MEDIA_SERVICES` —— Apple 官方清單沒有這個國家/地區。
- `MARKET_APP_NOT_SOLD` —— 國家在清單上,但這支 App 沒在那裡販售。
- `LOOKUP_UNSUPPORTED` —— 端點不接受該參數(例如回 400)。
`bn-BD` 屬第一種:證據 1 與 6 指向國家層級不存在,證據 3 排除了 App 層級解釋,
證據 5 排除了參數層級解釋。

## 決策

`bn-BD` 一律 `MARKET_UNAVAILABLE_OR_UNVERIFIED`,**App Store URL 為 None**。

硬性禁止(寫死在程式與測試裡):
- **不得**導向 US;**不得**導向 India;**不得**硬編任何替代國家。
- **不得**使用 countryless URL:它從本地實測也是 301 到 `/us/`,而且那是依請求端
  IP 的地理導流 —— 我們沒有任何 Apple 一手文件能證明孟加拉使用者點下去會到正確的
  地方。證據不足就是 `UNVERIFIED`,不是「應該沒問題」。
- **不得**刪內容:47 支 App 的 bn-BD 頁面、全部 50 個 locale 的覆蓋都照留。
  受影響的只有 CTA 連結、價格 facts 與發佈分母。

## Consumer 契約

- Publisher、API、alternatives、decision、visuals 與其他 loader 的 null URL
  必須伴隨 `market_availability` 的精確 state/reason/evidence；缺欄、假原因、
  非布林旗標及其他 locale 的 null 均拒絕。
- 不可用缺少 URL 推斷「沒有 App」：保留 47 支內容與完整 50 locale，
  分發格為 N/A、publishable=false、facts_allowed=false、outbox_count=0。
- `localized_app_store_url` 等低階路由解析不是市場可用性證據；
  發佈 consumer 必須先驗此契約，不能自行補 US、IN 或無國別 URL。
- 原生 App Store 商業控制與 facts 關閉；網站工具、內容導覽、MCP／Skill
  安裝等非 App Store 功能保留。最後由 gen_market_availability 與歸因
  audit 封住舊頁殘留，不能用清理程序代替 loader 的 fail-closed 驗證。
"""
from __future__ import annotations

from typing import Final
import html
import json

MARKET_UNAVAILABLE_OR_UNVERIFIED: Final = "MARKET_UNAVAILABLE_OR_UNVERIFIED"
MARKET_AVAILABLE: Final = "MARKET_AVAILABLE"

REASON_NOT_IN_APPLE_MEDIA_SERVICES: Final = "MARKET_NOT_IN_APPLE_MEDIA_SERVICES"
REASON_APP_NOT_SOLD: Final = "MARKET_APP_NOT_SOLD"
REASON_LOOKUP_UNSUPPORTED: Final = "LOOKUP_UNSUPPORTED"

#: locale -> (state, reason, 證據摘要)。只放**有一手證據**的項目。
UNAVAILABLE_MARKETS: Final[dict[str, dict[str, str]]] = {
    "bn-BD": {
        "state": MARKET_UNAVAILABLE_OR_UNVERIFIED,
        "reason": REASON_NOT_IN_APPLE_MEDIA_SERVICES,
        "country": "BD",
        "observed_at": "2026-09-12",
        "evidence": (
            "Apple 官方可用性頁 support.apple.com/en-us/118205 的 174 個國家/地區"
            "沒有 Bangladesh(India/Pakistan/Nepal/Sri Lanka/Bhutan/Myanmar 皆在列);"
            "iTunes lookup country=BD 對 47 個 live id 回 HTTP 200 / resultCount=0,"
            "對 WhatsApp/Gmail/Messenger 同樣 0;search country=BD resultCount=0;"
            "無效代碼 XX 回 HTTP 400 而 BD 回 200,排除參數不支援;"
            "apps.apple.com/bd/ 與 /bd/app/id… 皆 301 到 /us/。"
        ),
    },
}

#: 這些形式永遠不得用來代替缺少的市場連結。
FORBIDDEN_SUBSTITUTIONS: Final = ("us", "in", "countryless")


class MarketUnavailable(ValueError):
    """試圖為沒有可驗證市場的 locale 產生 App Store 連結。"""


def market_state(locale: str) -> str:
    return UNAVAILABLE_MARKETS.get(locale, {}).get("state", MARKET_AVAILABLE)


def is_unavailable(locale: str) -> bool:
    return isinstance(locale, str) and locale in UNAVAILABLE_MARKETS


def unavailable_reason(locale: str) -> str | None:
    entry = UNAVAILABLE_MARKETS.get(locale)
    return entry["reason"] if entry else None


def market_evidence(locale: str) -> dict[str, str] | None:
    entry = UNAVAILABLE_MARKETS.get(locale)
    return dict(entry) if entry else None


def canonical_app_store_url_for(app_id: str, locale: str, storefront: str | None) -> str | None:
    """該 locale 的公開 canonical App Store URL;沒有可驗證市場就回 ``None``。

    ``storefront`` 由呼叫端從權威對照表傳入(``None`` 代表沒有宣告)。
    回傳 ``None`` **不是**錯誤,而是唯一誠實的答案:這個市場沒有可購買的頁面可指。
    呼叫端必須把它渲染成不可點的 ``MARKET_UNAVAILABLE_OR_UNVERIFIED`` 狀態,
    **不得**改用 US、India 或 countryless 連結補位。
    """
    if is_unavailable(locale):
        return None
    if not storefront:
        return None
    return f"https://apps.apple.com/{storefront}/app/id{app_id}"


def cta_for(app_id: str, locale: str, storefront: str | None) -> dict[str, object]:
    """發佈端該用的 CTA 決策。``url`` 為 ``None`` 時不可渲染任何連結。"""
    url = canonical_app_store_url_for(app_id, locale, storefront)
    if url is None:
        return {
            "app_id": app_id,
            "locale": locale,
            "url": None,
            "state": MARKET_UNAVAILABLE_OR_UNVERIFIED,
            "reason": unavailable_reason(locale) or REASON_LOOKUP_UNSUPPORTED,
            "renderable_link": False,
        }
    return {
        "app_id": app_id,
        "locale": locale,
        "url": url,
        "state": MARKET_AVAILABLE,
        "reason": None,
        "renderable_link": True,
    }


def distribution_cell(app_id: str, locale: str, storefront: str | None) -> dict[str, object]:
    """locale × app 的分發格子。內容照留,只有可發佈性被標記。"""
    decision = cta_for(app_id, locale, storefront)
    blocked = decision["url"] is None
    return {
        "app_id": app_id,
        "locale": locale,
        "content_retained": True,          # 內容永遠保留,不因市場問題刪頁
        "publishable": not blocked,
        "value": "N/A" if blocked else "OK",
        "blocked_reason": decision["reason"] if blocked else None,
        "facts_allowed": not blocked,      # 沒有可驗證市場就不得顯示價格 facts
    }


def publishable_locales(locales) -> list[str]:
    """發佈分母只算有可驗證市場的 locale;其餘照樣保有內容。"""
    return [locale for locale in locales if not is_unavailable(locale)]


def record_fields(locale: str) -> dict[str, object]:
    if not is_unavailable(locale):
        return {}
    evidence = market_evidence(locale)
    return {
        "market_availability": {
            "state": MARKET_UNAVAILABLE_OR_UNVERIFIED,
            "reason": unavailable_reason(locale),
            "evidence": {
                "source_url": "https://support.apple.com/en-us/118205",
                "observed_at": evidence["observed_at"],
                "country": evidence["country"],
                "apple_media_services_markets": 174,
                "country_listed": False,
                "lookup_app_results": 0,
                "lookup_control_results": 0,
                "redirect_market": "US",
            },
            "value": "N/A",
            "content_retained": True,
            "publishable": False,
            "facts_allowed": False,
            "outbox_count": 0,
        }
    }


def validate_record(record, *, url_fields=("canonical_app_store_url", "app_store_url")) -> bool:
    """Null is a verified market decision, never a missing-field fallback."""
    locale = record.get("locale")
    if is_unavailable(locale):
        actual = json.dumps(record.get("market_availability"), sort_keys=True)
        expected = json.dumps(record_fields(locale)["market_availability"], sort_keys=True)
        if actual != expected:
            raise ValueError(f"Missing or invalid market state/reason/evidence: {locale}")
        if any(field not in record or record[field] is not None for field in url_fields):
            raise ValueError(f"Unavailable market must have null App Store URLs: {locale}")
        return False
    if record.get("market_availability"):
        raise ValueError(f"Unverified market exception: {locale}")
    if any(not isinstance(record.get(field), str) or not record[field].strip() for field in url_fields):
        raise ValueError(f"Available market requires App Store URLs: {locale}")
    return True


def note(locale: str, name: str | None = None) -> str:
    if not is_unavailable(locale):
        raise ValueError(f"Market is available: {locale}")
    subject = f"{name}-এর" if name else "অ্যাপের"
    return (
        f"Apple App Store এখনো বাংলাদেশে চালু হয়নি, তাই এখান থেকে {subject} "
        "সরাসরি ডাউনলোড লিঙ্ক দেওয়া সম্ভব নয়। "
        "অ্যাপটির সব তথ্য নিচে বাংলায় দেওয়া আছে।"
    )


def note_html(locale: str, name: str | None = None) -> str:
    evidence = record_fields(locale)["market_availability"]["evidence"]
    return (
        f'<p class="market-availability" data-market-state="{market_state(locale)}" '
        f'data-market-reason="{unavailable_reason(locale)}" '
        f'data-market-evidence="{html.escape(evidence["source_url"], quote=True)}">'
        f"{html.escape(note(locale, name))}</p>"
    )


def locale_from_path(path) -> str | None:
    parts = str(path).replace("\\", "/").split("/")
    for part in parts:
        for locale in UNAVAILABLE_MARKETS:
            if part == locale or part.startswith(locale + "."):
                return locale
    return None


def add_schema_contract(schema, *, url_fields=("canonical_app_store_url", "app_store_url")):
    """Keep the available-market schema strict while describing nullable cells."""
    properties = schema["properties"]
    properties["market_availability"] = {
        "enum": [record_fields(locale)["market_availability"] for locale in UNAVAILABLE_MARKETS]
    }
    for field in url_fields:
        previous = properties[field]
        properties[field] = {"anyOf": [previous, {"type": "null"}]}
    schema.setdefault("allOf", []).append({
        "if": {
            "properties": {"locale": {"enum": list(UNAVAILABLE_MARKETS)}},
            "required": ["locale"],
        },
        "then": {
            "required": ["market_availability", *url_fields],
            "properties": {field: {"type": "null"} for field in url_fields},
        },
        "else": {
            "not": {"required": ["market_availability"]},
            "properties": {field: {"type": "string", "minLength": 1} for field in url_fields},
        },
    })
    return schema
