#!/usr/bin/env python3
"""Generate a private subscription-cost calculator for all 50 Apple locales."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
import portfolio_app_finder as finder  # noqa: E402
import publisher_intent_catalog  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SLUG = "subscription-cost-calculator"
I18N_PATH = HERE / "portfolio_cost_calculator_i18n.json"
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
FEED_DISCOVERY_LINKS = "\n".join(
    (
        f'<link rel="alternate" type="application/atom+xml" '
        f'title="iOS App Guide — latest answers &amp; guides (Atom)" '
        f'href="{SITE}/feed.xml">',
        f'<link rel="alternate" type="application/rss+xml" '
        f'title="iOS App Guide — latest answers &amp; guides (RSS 2.0)" '
        f'href="{SITE}/rss.xml">',
        f'<link rel="alternate" type="application/feed+json" '
        f'title="iOS App Guide — latest answers &amp; guides (JSON Feed 1.1)" '
        f'href="{SITE}/feed.json">',
    )
)
COPY_KEYS = frozenset(
    {
        "title",
        "lead",
        "truth",
        "monthly",
        "subscriptions",
        "years",
        "total",
        "currency_note",
    }
)


CSS = """
:root{--ink:#172033;--muted:#566176;--line:#dfe5ef;--brand:#5344d8;--good:#087c58;--bg:#f5f7fc}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{width:min(1080px,100% - 28px);margin:auto;padding:38px 0 64px}
.scroll{max-width:100%;overflow-x:auto;scrollbar-width:thin}
.nowrap,h1,h2,label,.badge,.cta,.app-name,.purchase,.total-label,.formula{white-space:nowrap}
.eyebrow{color:var(--good);font-size:.78rem;font-weight:850;letter-spacing:.07em;text-transform:uppercase}
h1{font-size:clamp(1.08rem,5.2vw,2.8rem);line-height:1.08;margin:.2em 0}
.lead{font-size:clamp(.82rem,2.6vw,1.08rem);color:var(--muted);margin:.3em 0}
.calc{margin:22px 0 34px;padding:22px;border:1px solid var(--line);border-radius:22px;background:#fff;box-shadow:0 14px 44px rgba(31,42,79,.09)}
.fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
label{display:block;overflow-x:auto;color:#354056;font-size:.86rem;font-weight:750;margin-bottom:5px}
input{width:100%;border:1px solid #cfd7e5;border-radius:13px;background:#fbfcff;color:var(--ink);font-size:1.18rem;font-weight:850;padding:11px 12px}
.result{margin-top:16px;padding:18px;border:1px solid #deddf8;border-radius:17px;background:linear-gradient(135deg,#eef1ff,#f7f1ff)}
.total-label{color:#4b5570;font-size:.86rem;font-weight:750}
.total{color:var(--brand);font-size:clamp(2.1rem,8vw,4rem);font-weight:950;line-height:1.05}
.formula,.fine{color:var(--muted);font-size:.8rem}
.badges{display:flex;gap:8px;overflow-x:auto;margin:8px 0 16px}
.badge{border:1px solid var(--line);border-radius:999px;background:#fff;padding:6px 10px;color:#465168;font-size:.8rem;font-weight:750}
.apps{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.app{min-width:0;border:1px solid var(--line);border-radius:17px;background:#fff;padding:14px;box-shadow:0 6px 20px rgba(31,42,79,.05)}
.app-name{display:block;max-width:100%;overflow-x:auto;font-size:1rem;font-weight:850}
.purchase{display:block;max-width:100%;overflow-x:auto;color:var(--muted);font-size:.82rem;margin:3px 0 9px}
.cta{display:block;max-width:100%;overflow-x:auto;border-radius:11px;background:linear-gradient(135deg,#5d4ee0,#4436bc);color:#fff;text-align:center;text-decoration:none;font-size:.83rem;font-weight:850;padding:9px 11px}
.footer{border-top:1px solid var(--line);margin-top:30px;padding-top:16px}
@media(max-width:620px){.fields{grid-template-columns:1fr}.wrap{width:min(100% - 20px,1080px);padding-top:24px}.calc{padding:16px}}
"""


def load_i18n(path: Path = I18N_PATH) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("source_locale") != "en":
        raise ValueError(f"Invalid calculator i18n metadata: {path}")
    source = payload.get("source")
    localized = payload.get("localizations")
    if not isinstance(source, dict) or set(source) != COPY_KEYS:
        raise ValueError("Calculator source copy is incomplete")
    if not isinstance(localized, dict) or set(localized) != set(OFFICIAL_LOCALES):
        raise ValueError(
            "Calculator i18n must cover the official 50 locales: "
            f"missing={sorted(set(OFFICIAL_LOCALES) - set(localized))}, "
            f"extra={sorted(set(localized) - set(OFFICIAL_LOCALES))}"
        )
    result = {"en": source}
    for locale in OFFICIAL_LOCALES:
        copy = localized[locale]
        if (
            not isinstance(copy, dict)
            or set(copy) != COPY_KEYS
            or any(not isinstance(value, str) or not value.strip() for value in copy.values())
        ):
            raise ValueError(f"Invalid calculator localization: {locale}")
        result[locale] = copy
    return result


I18N = load_i18n()


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def hreflang_links() -> str:
    rows = [
        f'<link rel="alternate" hreflang="en" href="{canonical("en")}">'
    ]
    rows.extend(
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{canonical(locale)}">'
        for locale in OFFICIAL_LOCALES
    )
    rows.append(
        f'<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    )
    return "\n".join(rows)


def webmcp_script(locale: str, copy: dict[str, str]) -> str:
    input_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "monthly_price_per_app",
            "subscription_count",
            "years",
        ],
        "properties": {
            "monthly_price_per_app": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 1_000_000,
            },
            "subscription_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10_000,
            },
            "years": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 100,
            },
        },
    }
    return f"""
(async function(){{
 if(!document.modelContext?.registerTool)return;
 function finite(value,name,max){{
  if(typeof value!=='number'||!Number.isFinite(value)||value<=0||value>max)throw new RangeError(name+' is outside the supported range.');
  return value;
 }}
 await document.modelContext.registerTool({{
  name:'calculate_recurring_app_cost',
  description:{json.dumps(copy["lead"] + " " + copy["truth"], ensure_ascii=False)},
  inputSchema:{json.dumps(input_schema, separators=(",", ":"))},
  annotations:{{readOnlyHint:true,untrustedContentHint:false}},
  execute:async(value)=>{{
   if(value===null||typeof value!=='object'||Array.isArray(value))throw new TypeError('Input must be an object.');
   const monthly=finite(value.monthly_price_per_app,'monthly_price_per_app',1000000);
   const subscriptions=finite(value.subscription_count,'subscription_count',10000);
   if(!Number.isInteger(subscriptions))throw new RangeError('subscription_count must be an integer.');
   const years=finite(value.years,'years',100);
   const total=Math.round((monthly*subscriptions*12*years+Number.EPSILON)*100)/100;
   return JSON.stringify({{
    result_type:'recurring_app_cost_calculation',
    total_recurring_cost:total,
    formula:'monthly_price_per_app * subscription_count * 12 * years',
    currency_boundary:{json.dumps(copy["currency_note"], ensure_ascii=False)},
    verified_app_finder_url:{json.dumps(finder.canonical(locale), ensure_ascii=False)}
   }});
  }}
 }});
}})().catch(error=>console.error('WebMCP registration failed.',error));
"""


def calculator_script(locale: str) -> str:
    return f"""
(function(){{
 const ids=['monthly','subscriptions','years'];
 function positive(id){{
  const value=Number(document.getElementById(id).value);
  return Number.isFinite(value)&&value>0?value:0;
 }}
 function calculate(){{
  const total=positive('monthly')*positive('subscriptions')*12*positive('years');
  document.getElementById('recurring-total').textContent=new Intl.NumberFormat(
   {json.dumps(locale)},{{maximumFractionDigits:2}}
  ).format(total);
 }}
 ids.forEach(id=>document.getElementById(id).addEventListener('input',calculate));
 calculate();
}})();
"""


def item_list_schema(
    locale: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    items = []
    for position, record in enumerate(records, start=1):
        intent = finder.localized_intent(record, locale)
        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "item": {
                    "@type": "MobileApplication",
                    "name": record["name"],
                    "identifier": record["app_store_id"],
                    "operatingSystem": "iOS",
                    "url": intent["app_store_url"],
                    "description": intent["decision_context"],
                },
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": finder.UI[locale]["index_title"],
        "numberOfItems": len(items),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": items,
    }


def app_cards(
    locale: str,
    records: list[dict[str, object]],
) -> str:
    cards = []
    purchase_labels = finder.UI[locale]["purchase_labels"]
    for record in records:
        intent = finder.localized_intent(record, locale)
        purchase = purchase_labels[str(record["purchase_model"])]
        cards.append(
            '<article class="app">'
            f'<span class="app-name">{html.escape(str(record["name"]))}</span>'
            f'<span class="purchase">{html.escape(str(purchase))}</span>'
            f'<a class="cta" href="{html.escape(str(intent["app_store_url"]), quote=True)}">'
            f'{html.escape(str(intent["app_store_cta_label"]))}</a>'
            "</article>"
        )
    return "\n".join(cards)


def render_page(
    locale: str,
    records: list[dict[str, object]],
) -> str:
    copy = I18N[locale]
    finder_ui = finder.UI[locale]
    finder_answer = finder.FINDER_COPY[locale]
    direction = "rtl" if locale in RTL_LOCALES else "ltr"
    description = f'{copy["lead"]} {copy["truth"]}'
    formula = (
        f'{copy["monthly"]} × {copy["subscriptions"]} × 12 × {copy["years"]}'
    )
    web_schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": copy["title"],
        "description": description,
        "url": canonical(locale),
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Web",
        "isAccessibleForFree": True,
        "inLanguage": locale,
        "featureList": [
            copy["truth"],
            finder_ui["alphabetical"],
            finder_ui["private"],
        ],
    }
    schemas = "\n".join(
        f'<script type="application/ld+json">'
        f"{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}"
        "</script>"
        for schema in (web_schema, item_list_schema(locale, records))
    )
    disclosure = finder_answer["boundaries"][0]
    return f"""<!doctype html>
<html lang="{html.escape(locale)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy["title"])}</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{canonical(locale)}">
{hreflang_links()}
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy["title"], quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{canonical(locale)}">
<style>{CSS}</style>
{schemas}
{FEED_DISCOVERY_LINKS}
</head>
<body>
<main class="wrap">
<div class="scroll"><div class="eyebrow nowrap">{html.escape(finder_ui["private"])}</div></div>
<div class="scroll"><h1>{html.escape(copy["title"])}</h1></div>
<div class="scroll"><p class="lead nowrap">{html.escape(copy["lead"])}</p></div>
<div class="scroll"><p class="lead nowrap">{html.escape(copy["truth"])}</p></div>
<section class="calc" aria-labelledby="calculator-heading">
<div class="fields">
<div><label for="monthly">{html.escape(copy["monthly"])}</label><input id="monthly" type="number" inputmode="decimal" min="0.01" max="1000000" step="0.01" placeholder="0.00"></div>
<div><label for="subscriptions">{html.escape(copy["subscriptions"])}</label><input id="subscriptions" type="number" inputmode="numeric" min="1" max="10000" step="1" value="1"></div>
<div><label for="years">{html.escape(copy["years"])}</label><input id="years" type="number" inputmode="decimal" min="0.01" max="100" step="1" value="1"></div>
</div>
<div class="result">
<div class="scroll"><div id="calculator-heading" class="total-label">{html.escape(copy["total"])}</div></div>
<div id="recurring-total" class="total" aria-live="polite">0</div>
<div class="scroll"><div class="formula">{html.escape(formula)}</div></div>
<div class="scroll"><div class="fine nowrap">{html.escape(copy["currency_note"])}</div></div>
</div>
</section>
<div class="scroll"><h2>{html.escape(finder_ui["index_title"])}</h2></div>
<div class="badges">
<span class="badge">{html.escape(finder_ui["alphabetical"])}</span>
<span class="badge">{html.escape(finder_ui["neutral"])}</span>
</div>
<section class="apps" aria-label="{html.escape(finder_ui["index_title"], quote=True)}">
{app_cards(locale, records)}
</section>
<div class="footer">
<div class="scroll"><a class="nowrap" href="{finder.canonical(locale)}">{html.escape(finder_ui["index_title"])}</a></div>
<div class="scroll"><p class="fine nowrap">{html.escape(disclosure)}</p></div>
<div class="scroll"><p class="fine nowrap">{html.escape(finder_ui["footer"])}</p></div>
</div>
</main>
<script>{calculator_script(locale)}{webmcp_script(locale, copy)}</script>
</body>
</html>
"""


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def page_path(pages: Path, locale: str) -> Path:
    prefix = Path() if locale == "en" else Path(locale)
    return pages / prefix / "tools" / f"{SLUG}.html"


def update_tools_index(pages: Path, locale: str) -> bool:
    prefix = Path() if locale == "en" else Path(locale)
    path = pages / prefix / "tools" / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    copy = I18N[locale]
    card = (
        f'<article class="card third" data-tool="{SLUG}">'
        f'<h2><a href="{SLUG}.html" style="white-space:nowrap;overflow-x:auto">'
        f'{html.escape(copy["title"])}</a></h2>'
        f'<p style="white-space:nowrap;overflow-x:auto">{html.escape(copy["lead"])}</p>'
        "</article>"
    )
    pattern = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html".*?</article>',
        re.S,
    )
    if pattern.search(text):
        updated = pattern.sub(card, text, count=1)
    else:
        # Two tools-index layouts exist: the original finder grid closes with
        # </section></main>; the newer localized tools generator closes with
        # </div></main>. Append the card as the last grid child of whichever
        # is present.
        for marker in ("</section></main>", "</div></main>"):
            if marker in text:
                updated = text.replace(marker, card + marker, 1)
                break
        else:
            raise RuntimeError(f"{path} is missing its main grid marker")
    return write_text_if_changed(path, updated)


def build(
    pages: Path,
    records: list[dict[str, object]],
) -> list[str]:
    if not records:
        raise ValueError("Calculator requires verified live app records")
    keys = [str(record["key"]) for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Calculator records contain duplicate app keys")
    outputs = []
    for locale in ("en", *OFFICIAL_LOCALES):
        write_text_if_changed(
            page_path(pages, locale),
            render_page(locale, records),
        )
        update_tools_index(pages, locale)
        outputs.append(canonical(locale))
    return outputs


def main() -> None:
    live = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    expected = set(publisher_intent_catalog.PERSONAS)
    if set(live) != expected:
        raise RuntimeError(
            "The live portfolio and buyer-intent catalog differ: "
            f"missing={sorted(expected - set(live))}, "
            f"unexpected={sorted(set(live) - expected)}"
        )
    records = finder.catalog_records(live, PAGES)
    records = finder.localized_page_records(records, PAGES)
    outputs = build(PAGES, records)
    print(
        f"portfolio subscription calculator -> {len(outputs)} locales, "
        f"{len(records)} verified apps"
    )
    print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
