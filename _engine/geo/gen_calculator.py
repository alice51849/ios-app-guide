#!/usr/bin/env python3
"""互動式「訂閱成本計算機」工具頁生成器(2026-07-08 新方法)。

為何新:過去都是靜態答案/榜單/成本比較頁;這是第一個「互動工具」——使用者輸入自己
每月訂閱費 × App 數 × 年數,vanilla JS 即時算出「一輩子要付多少」,再對比一次性付費。
互動工具天生可獲外部連結、可分享、常青,且被 AI 引擎當「有用資源」引用。誠實:不編造
任何競品價格(使用者自己輸入),揭露自家開發者。純本機、免任何 key。

用法:python3 gen_calculator.py
"""
import os, sys, html, json, time
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
from site_config import PUBLIC_SITE  # noqa: E402
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
sys.path.insert(0, str(HERE.parent / "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_pages import has_one_time_access  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

# 精選要在計算機下方展示的一次性付費 App(有 App Store 連結者)
FEATURED = ["sereno", "cyca", "gmoney", "hourstag", "lockhour", "scanto",
            "picclear", "photocream", "snapport", "cvdesk", "sononote", "unblurry"]
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"
FINDER_URL = f"{SITE}/tools/private-pay-once-iphone-app-finder.html"
PORTFOLIO_CALCULATOR_MARKER = "name:'calculate_recurring_app_cost'"

CSS = ("body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
       "background:linear-gradient(180deg,#fff,#f4f7fc);color:#15202e;line-height:1.62}a{color:#2f47c4}"
       ".wrap{width:min(880px,100% - 32px);margin:auto}.hero{padding:44px 0 6px}"
       ".eyebrow{color:#2f8f5f;font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}"
       "h1{font-size:clamp(1.9rem,4.8vw,3rem);line-height:1.06;margin:.2em 0}h2{font-size:1.4rem;margin:1.5em 0 .5em}"
       "p.lead{font-size:1.15rem;color:#495468}"
       ".calc{background:#fff;border:1px solid #e4e8f0;border-radius:20px;padding:22px;box-shadow:0 12px 40px rgba(20,32,60,.09);margin:18px 0}"
       ".row{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;margin:6px 0 14px}"
       ".fld{flex:1 1 150px;min-width:140px}.fld label{display:block;font-weight:700;font-size:.9rem;color:#3a4658;margin-bottom:5px}"
       ".fld input{width:100%;box-sizing:border-box;font-size:1.15rem;font-weight:800;padding:11px 12px;border:1px solid #d7deea;border-radius:12px;background:#fbfcfe;color:#15202e}"
       ".out{background:linear-gradient(135deg,#eef3ff,#f6f0ff);border:1px solid #dfe4f2;border-radius:16px;padding:18px;text-align:center;margin-top:6px}"
       ".out .num{font-size:clamp(2.1rem,7vw,3.4rem);font-weight:900;color:#c0392b;line-height:1;letter-spacing:-.01em}"
       ".out .sub{color:#4a5566;font-weight:700;margin-top:6px}.out .save{color:#1f8f5f;font-weight:800;margin-top:10px;font-size:1.05rem}"
       ".apps{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin:14px 0}"
       ".app{display:block;background:#fff;border:1px solid #e4e8f0;border-radius:16px;padding:14px 16px;text-decoration:none;color:inherit;box-shadow:0 6px 20px rgba(20,32,60,.05)}"
       ".app b{display:block;font-size:1.05rem;color:#15202e}.app span{color:#5a6472;font-size:.92rem}"
       ".cta{display:inline-flex;align-items:center;border-radius:999px;background:linear-gradient(135deg,#2f47c4,#7b5cf0);color:#fff!important;text-decoration:none;font-weight:850;padding:12px 18px;margin-top:8px}"
       ".notice{font-size:.92rem;color:#5a6472;background:#eef3ff;border:1px solid #e4e8f0;border-radius:14px;padding:13px 15px;margin-top:14px}"
       ".footer{margin-top:34px;padding:22px 0;border-top:1px solid #e4e8f0;color:#5a6472;font-size:.9rem}")

JS = """
(function(){
 function n(id){var v=parseFloat(document.getElementById(id).value);return isFinite(v)&&v>0?v:0;}
 function money(x){return '$'+x.toLocaleString(undefined,{maximumFractionDigits:0});}
 function calc(){
  var m=n('mprice'),apps=n('napps'),yrs=n('years');
  var perYear=m*12*apps, life=perYear*yrs;
  document.getElementById('lifecost').textContent=money(life);
  document.getElementById('lifesub').textContent=apps+' subscription'+(apps>1?'s':'')+' \\u00d7 '+money(m)+'/mo \\u00d7 '+yrs+' years';
  // 假設一次性 App 平均一次 $5(僅示意,實際以各 App 商店頁為準)
  var payonce=apps*5;
  var saved=life-payonce;
  var el=document.getElementById('save');
  if(saved>0){el.textContent='Pay-once apps at ~'+money(payonce)+' total could save you about '+money(saved)+' over '+yrs+' years.';}
  else{el.textContent='';}
 }
 ['mprice','napps','years'].forEach(function(id){var e=document.getElementById(id);if(e){e.addEventListener('input',calc);}});
 calc();
})();
"""


def webmcp_input_schema():
    return {
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
                "description": (
                    "User-entered monthly price for one app, in the user's "
                    "chosen currency units."
                ),
            },
            "subscription_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10_000,
                "description": "Number of recurring app subscriptions.",
            },
            "years": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 100,
                "description": "How many years the subscriptions continue.",
            },
        },
    }


def webmcp_script():
    schema = json.dumps(
        webmcp_input_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""
(async function(){{
 if(!document.modelContext?.registerTool)return;
 function finiteNumber(value,name,max){{
  if(typeof value!=='number'||!Number.isFinite(value)||value<=0||value>max)throw new RangeError(name+' is outside the supported range.');
  return value;
 }}
 function roundMoney(value){{return Math.round((value+Number.EPSILON)*100)/100;}}
 await document.modelContext.registerTool({{
  name:'calculate_app_subscription_cost',
  description:'Calculate recurring app-subscription cost from user-entered numbers. Also return a clearly labelled illustrative comparison using 5 currency units per pay-once app; this is not a claim about any current App Store price.',
  inputSchema:{schema},
  annotations:{{readOnlyHint:true,untrustedContentHint:false}},
  execute:async(value)=>{{
   if(value===null||typeof value!=='object'||Array.isArray(value))throw new TypeError('WebMCP input must be an object.');
   const monthly=finiteNumber(value.monthly_price_per_app,'monthly_price_per_app',1000000);
   const subscriptions=finiteNumber(value.subscription_count,'subscription_count',10000);
   if(!Number.isInteger(subscriptions))throw new RangeError('subscription_count must be an integer.');
   const years=finiteNumber(value.years,'years',100);
   const recurring=roundMoney(monthly*12*subscriptions*years);
   const illustrativePayOnce=roundMoney(subscriptions*5);
   return JSON.stringify({{
    result_type:'app_subscription_cost_calculation',
    currency_boundary:'All numeric outputs use the same currency units supplied by the user; no exchange rate is applied.',
    recurring_cost:recurring,
    illustrative_pay_once_total:illustrativePayOnce,
    illustrative_difference:roundMoney(recurring-illustrativePayOnce),
    assumption:'The pay-once comparison uses an illustrative 5 currency units per app, not a current price claim. Verify every real price on its App Store listing.',
    pay_once_app_finder_url:'{FINDER_URL}'
   }});
  }}
 }});
}})().catch(error=>console.error('WebMCP tool registration failed.',error));
"""


def esc(x):
    return html.escape(str(x), quote=True)


def app_cards(live_keys=None):
    out = []
    for k in FEATURED:
        if (
            k not in APPS
            or not appstore_url(k)
            or not has_one_time_access(k)
            or (live_keys is not None and k not in live_keys)
        ):
            continue
        a = APPS[k]
        url = appstore_url(k, "iag_calc") or appstore_url(k)
        out.append(f'<a class="app" href="{esc(url)}" rel="nofollow"><b>{esc(a["name"])}</b>'
                   f'<span>{esc(a.get("sub","") or "One-time purchase \\u00b7 no subscription")}</span></a>')
    return "\n".join(out)


def build(live_keys=None):
    slug = "subscription-cost-calculator"
    canon = f"{SITE}/tools/{slug}.html"
    path = PAGES / "tools" / f"{slug}.html"
    if (
        path.is_file()
        and PORTFOLIO_CALCULATOR_MARKER
        in path.read_text(encoding="utf-8")
    ):
        return canon
    title = "Subscription Cost Calculator: How Much Are Your App Subscriptions Really Costing You? (2026)"
    desc = ("Free calculator: enter your monthly app subscription price, how many apps, and how many years "
            "to see the true lifetime cost \u2014 then compare with one-time \u201cpay once\u201d apps.")
    faq = [
        ("How do I calculate the true cost of an app subscription?",
         "Multiply the monthly price by 12 to get the yearly cost, then multiply by how many years you\u2019ll keep it. "
         "For several subscriptions, add each one. This calculator does the math instantly for any number of apps and years."),
        ("Are subscriptions or one-time purchases cheaper long term?",
         "It depends on how long you use the app. A one-time (\u201cpay once\u201d) app has a single fixed price, so the "
         "longer you use it the cheaper it gets per year. A subscription keeps charging every month for as long as you keep it, "
         "so over several years the total can be many times higher."),
        ("What are pay-once alternatives to subscription apps?",
         "Across categories like white-noise and sleep, budgeting, screen-time, document scanning, photo filters and resume "
         "building, there are apps that charge one time to unlock their features. Some are listed below."),
    ]
    jsonld = [
        {"@context": "https://schema.org", "@type": "WebApplication", "name": "Subscription Cost Calculator",
         "applicationCategory": "FinanceApplication", "operatingSystem": "Web", "url": canon,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "description": desc,
         "featureList": ["Local subscription-cost calculation", "No account, storage or analytics",
                         "Progressive read-only WebMCP calculation for supporting browsers"]},
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [{"@type": "Question", "name": q,
                         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
    ]
    faq_html = "\n".join(f'<div class="card" style="background:#fff;border:1px solid #e4e8f0;border-radius:16px;padding:16px;margin:12px 0">'
                         f'<h3 style="margin:.1em 0 .3em;font-size:1.08rem">{esc(q)}</h3><p style="margin:0;color:#3f4a5c">{esc(a)}</p></div>'
                         for q, a in faq)
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in jsonld)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canon)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta name="robots" content="index,follow,max-image-preview:large">
<style>{CSS}</style>{ld}
</head><body><div class="wrap">
<div class="hero"><div class="eyebrow">Free tool \u00b7 2026</div>
<h1>How much are your app subscriptions <em>really</em> costing you?</h1>
<p class="lead">Subscription fatigue is real. Enter a few numbers to see the true multi-year cost of your monthly app subscriptions \u2014 then see quality <strong>pay-once</strong> apps that charge a single time.</p></div>

<div class="calc">
 <div class="row">
  <div class="fld"><label for="mprice">Avg price / month (per app)</label><input id="mprice" type="number" inputmode="decimal" value="4.99" min="0" step="0.5"></div>
  <div class="fld"><label for="napps">How many subscriptions</label><input id="napps" type="number" inputmode="numeric" value="3" min="1" step="1"></div>
  <div class="fld"><label for="years">Years you\u2019ll keep them</label><input id="years" type="number" inputmode="numeric" value="5" min="1" step="1"></div>
 </div>
 <div class="out"><div class="num" id="lifecost">$0</div><div class="sub" id="lifesub"></div><div class="save" id="save"></div></div>
 <div class="notice">The pay-once comparison uses an illustrative ~$5 one-time unlock per app for the estimate only. Real prices vary \u2014 always check each app\u2019s App Store page. This tool fabricates no third-party prices; you enter your own.</div>
</div>

<h2>Pay-once apps (no subscription) worth a look</h2>
<div class="apps">
{app_cards(live_keys)}
</div>

<h2>Questions people ask</h2>
{faq_html}

<div class="footer">Made by an independent iOS developer (Cait518) whose portfolio includes one-time-purchase apps. This free calculator is provided as an honest resource. Prices shown by the calculator are your own inputs plus an illustrative estimate; verify real prices on the App Store. <a href="{esc(WEBMCP_SOURCE)}">WebMCP preview specification</a>.</div>
</div>
<script>{JS}{webmcp_script()}</script>
</body></html>"""
    (PAGES / "tools").mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != doc:
        path.write_text(doc, encoding="utf-8")
    return canon


def update_tools_index():
    index = PAGES / "tools" / "index.html"
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    slug = "subscription-cost-calculator.html"
    if f'href="{slug}"' in text:
        return False
    card = (
        '<article class="card third"><h2>'
        f'<a href="{slug}">Subscription Cost Calculator</a></h2>'
        "<p>See the multi-year cost of recurring app subscriptions.</p>"
        "</article>"
    )
    marker = "</section></main>"
    if marker not in text:
        raise RuntimeError("tools/index.html is missing its main grid marker")
    index.write_text(text.replace(marker, card + marker, 1), encoding="utf-8")
    return True


def write_tools_sitemap():
    files = sorted(
        {
            *PAGES.glob("tools/*.html"),
            *PAGES.glob("*/tools/*.html"),
        }
    )
    rows = []
    for path in files:
        rel = path.relative_to(PAGES).as_posix()
        modified = time.strftime(
            "%Y-%m-%d", time.gmtime(path.stat().st_mtime)
        )
        rows.append(
            f"  <url><loc>{SITE}/{rel}</loc>"
            f"<lastmod>{modified}</lastmod></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    (PAGES / "sitemap_tools.xml").write_text(xml, encoding="utf-8")
    return len(rows)


def main():
    live_keys = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    canon = build(live_keys)
    update_tools_index()
    sitemap_count = write_tools_sitemap()
    print(f"calculator -> {canon}", flush=True)
    print(f"tools sitemap -> {sitemap_count} urls", flush=True)


if __name__ == "__main__":
    main()
