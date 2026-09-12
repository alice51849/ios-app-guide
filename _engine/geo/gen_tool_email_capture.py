#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Official-50, explicit new-tools-only consent. No subscriptions or sends."""
import argparse
import glob
import html
import json
import os
import re

from owned_email_contract import ENDPOINT, PRIVACY_URL, digest, load_copy
from site_config import PUBLIC_SITE
import owned_email_readiness as readiness

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
CONFIG = os.path.join(HERE, "tool_email_capture.json")
MARKER = "tool-email-capture"
BLOCK_RE = re.compile(
    r'<section class="wrap tool-email-capture".*?</section>', re.S
)
LANG_RE = re.compile(r'<html[^>]*\blang="([^"]+)"', re.I)
STYLE = (
    "border:1px solid #d8c9ff;border-radius:14px;"
    "padding:18px 20px;margin:28px 0;background:#fffafd;color:#302057;"
    "box-sizing:border-box;max-width:100%;min-width:0;overflow-wrap:anywhere"
)


def _load_config():
    with open(CONFIG, encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("copy_file") != "owned_email_copy.json":
        raise ValueError("official-50 copy source is required")
    config["copy"] = {
        locale: {
            **text, "heading": text["tools_title"], "body": text["confirmation"],
            "consent": text["tools_consent"], "placeholder": "you@example.com",
            "promise": text["privacy"] + " " + text["unsubscribe"],
        }
        for locale, text in load_copy(os.path.join(HERE, config["copy_file"])).items()
    }
    if config.get("enabled") and config.get("endpoint") and (
        config.get("provider") != "buttondown" or config["endpoint"] != ENDPOINT
        or config.get("email_field") != "email"
        or config.get("extra_fields") != {"buttondown": {"embed": "1"}}
        or config.get("sender_enabled") is not False
    ):
        raise ValueError("capture must be Buttondown-only and sender-disabled")
    return config


def _copy_for(config, lang):
    return (config.get("copy") or {}).get(_locale(lang), {})


def _locale(lang):
    return {
        "en": "en-US", "de": "de-DE", "fr": "fr-FR", "es": "es-ES",
        "nl": "nl-NL", "ar": "ar-SA", "sl": "sl-SI",
    }.get(lang, lang)


def _block(config, lang, *, preview=False):
    if config.get("endpoint") != ENDPOINT:
        raise ValueError("only the declared Buttondown capture endpoint is allowed")
    text = _copy_for(config, lang)
    if not text:
        return ""
    locale = _locale(lang)
    if not preview and not readiness.is_active(locale):
        return ""
    metadata = {
        "embed": "1", "metadata__owned_campaign": "new_free_tools_v1",
        "metadata__owned_locale": locale, "metadata__owned_consent_version": "new-tools-only-v1",
        "metadata__owned_consent_digest": digest({
            "locale": locale, "campaign": "new_free_tools_v1",
            **{key: text[key] for key in ("consent", "privacy", "unsubscribe", "disclosure")},
        }),
    }
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(str(name))}" '
        f'value="{html.escape(str(value))}">'
        for name, value in metadata.items()
    )
    return (
        f'<section class="wrap {MARKER}" style="{STYLE}">'
        f'<details><summary style="min-height:44px;padding:10px 0;cursor:pointer">'
        f'{html.escape(readiness.localized(locale)["optional"])}</summary>'
        f'<h2>{html.escape(text.get("heading", ""))}</h2>'
        f'<p>{html.escape(text.get("body", ""))}</p>'
        f'<form action="{html.escape(config["endpoint"])}" method="post" '
        f'target="_blank" rel="noopener noreferrer" '
        f'style="display:flex;gap:12px;flex-wrap:wrap" dir="{"rtl" if locale in {"ar-SA", "he", "ur-PK"} else "ltr"}">'
        f'<label for="tec-email" style="flex-basis:100%">'
        f'{html.escape(text["email_label"])}</label>'
        f'<input id="tec-email" type="email" required '
        f'name="{html.escape(config.get("email_field", "email"))}" '
        f'placeholder="{html.escape(text.get("placeholder", ""))}" '
        f'style="flex:1 1 220px;min-width:0;max-width:100%;box-sizing:border-box;'
        f'min-height:44px;padding:10px 12px;border-radius:10px;'
        f'border:1px solid rgba(120,100,70,.35)">'
        f'{hidden}<label for="tec-consent" style="flex-basis:100%;min-height:44px">'
        f'<input id="tec-consent" type="checkbox" required '
        f'name="metadata__owned_consent" value="yes" '
        f'style="width:24px;height:24px;vertical-align:middle">'
        f' {html.escape(text["consent"])}</label>'
        f'<button type="submit" style="padding:10px 18px;border-radius:10px;'
        f'min-height:44px;max-width:100%;overflow-wrap:anywhere;border:1px solid #bca4de;'
        f'background:#fff;color:#5032a4;cursor:pointer">'
        f'{html.escape(text.get("button", ""))}</button>'
        f'</form>'
        f'<p>{html.escape(text["promise"])} '
        f'<a href="{PRIVACY_URL}">Buttondown</a></p>'
        f'<p>{html.escape(text["disclosure"])}</p>'
        + (f'<p><a href="{PUBLIC_SITE}/{locale}/email/index.html">'
           f'{html.escape(text["preferences"])}</a></p>'
           if config.get("app_capture_enabled") else "")
        +
        f'</details></section>'
    )


def _tool_pages():
    """英文工具頁 + 各語系工具頁(pages/<locale>/tools/*.html)。

    2026-08-12:demand_tools.py 開始產出 ja / ko / de-DE / zh-Hant 的工具頁,
    這裡原本只掃英文目錄,那些頁面永遠拿不到訂閱區塊。`_block()` 已經會依
    `<html lang>` 挑對應語言的文案,所以直接把語系目錄納入即可。
    """
    return sorted(
        set(glob.glob(os.path.join(PAGES, "tools", "*.html")))
        | set(glob.glob(os.path.join(PAGES, "*", "tools", "*.html")))
    )


def apply_capture(page, config, *, preview=False):
    stripped = BLOCK_RE.sub("", page)
    if not config.get("enabled") or not config.get("endpoint"):
        return stripped
    match = LANG_RE.search(page)
    block = _block(config, match.group(1) if match else "en-US", preview=preview)
    if not block:
        return stripped
    stores = list(re.finditer(r'<a\b[^>]*\bhref=["\']https://(?:apps|itunes)\.apple\.com/[^"\']+["\'][^>]*>', stripped, re.I))
    for closing in ("</main>", "</body>"):
        position = stripped.rfind(closing)
        if position >= 0 and all(store.end() <= position for store in stores):
            result = stripped[:position] + block + stripped[position:]
            readiness.legacy_non_interference(page, result)
            return result
    raise ValueError("no safe post-answer/post-CTA capture insertion point")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    config = _load_config()
    active = bool(config.get("enabled")) and bool(config.get("endpoint")) and bool(readiness.active_locales())
    changed = removed = 0
    pages = _tool_pages()

    for path in pages:
        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        updated = apply_capture(page, config)
        if not active and updated != page:
            removed += 1
        if updated != page:
            changed += 1
            if not args.dry:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(updated)

    state = "on" if active else "inactive"
    print(f"{'DRY ' if args.dry else ''}tool-email-capture {state}: "
          f"{changed} / {len(pages)} 頁更新"
          + (f",移除舊區塊 {removed}" if removed else ""))
    if not active:
        print("  → 依 owned_email_rollout.json 預設 inactive；須通過 readiness 與 "
              "整合授權，不以表單 HTTP 200 當訂閱證據。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
