#!/usr/bin/env python3
"""Generate a 50-locale, local-only family outing weather planner."""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
I18N_PATH = HERE / "family_outing_weather_planner_i18n.json"
WEATHER_META_PATH = ROOT / "data" / "weather_full.json"
SLUG = "family-outing-weather-planner"
APP_KEY = "lumiweather"
APP_ID = "6779552704"
CONTENT_DATE = "2026-07-16"
CONTENT_MODIFIED = "2026-07-16T22:28:00Z"

WHO_UV = (
    "https://www.who.int/news-room/questions-and-answers/item/"
    "radiation-the-ultraviolet-(uv)-index"
)
CDC_OUTDOOR = (
    "https://www.cdc.gov/early-care/communication-resources/"
    "outdoor-play-and-safety-for-children-in-ece.html"
)
AAP_WINTER = (
    "https://www.healthychildren.org/English/safety-prevention/at-play/"
    "Pages/Winter-Safety.aspx"
)
NWS_WIND_CHILL = "https://www.weather.gov/safety/cold-wind-chill-chart"
NWS_LIGHTNING = "https://www.weather.gov/safety/lightning"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"
SOURCES = (WHO_UV, CDC_OUTDOOR, AAP_WINTER, NWS_WIND_CHILL, NWS_LIGHTNING)

LOCALE_TO_LANGUAGE = {
    "ar-SA": "ar",
    "bn-BD": "bn",
    "ca": "ca",
    "cs": "cs",
    "da": "da",
    "de-DE": "de",
    "el": "el",
    "en-AU": "en",
    "en-CA": "en",
    "en-GB": "en",
    "en-US": "en",
    "es-ES": "es",
    "es-MX": "es",
    "fi": "fi",
    "fr-CA": "fr",
    "fr-FR": "fr",
    "gu-IN": "gu",
    "he": "he",
    "hi": "hi",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "kn-IN": "kn",
    "ko": "ko",
    "ml-IN": "ml",
    "mr-IN": "mr",
    "ms": "ms",
    "nl-NL": "nl",
    "no": "no",
    "or-IN": "or",
    "pa-IN": "pa",
    "pl": "pl",
    "pt-BR": "pt",
    "pt-PT": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl-SI": "sl",
    "sv": "sv",
    "ta-IN": "ta",
    "te-IN": "te",
    "th": "th",
    "tr": "tr",
    "uk": "uk",
    "ur-PK": "ur",
    "vi": "vi",
    "zh-Hans": "zh-Hans",
    "zh-Hant": "zh",
}
LOCALES = tuple(LOCALE_TO_LANGUAGE)
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
INDEX_LOCALES = (
    "en-US",
    "de-DE",
    "es-ES",
    "fr-FR",
    "ja",
    "ko",
    "pt-BR",
    "zh-Hans",
    "zh-Hant",
)
ANSWER_SLUGS = (
    "best-family-weather-app.html",
    "how-do-i-know-if-today-s-weather-is-suitable-for-taking-my-toddler-to-the-playground.html",
    "how-to-plan-outdoor-activities-with-kids-around-the-weather.html",
    "is-there-an-app-that-tells-me-if-today-s-weather-is-suitable-for-taking-my-toddler-to-the-park.html",
    "simple-family-weather-app-to-plan-outings-with-kids.html",
)
INBOUND_LINK_CLASS = "family-outing-weather-planner-link"

PHRASE_KEYS = {
    "heading": "Is today kid-friendly?",
    "lead": "Based on today's weather & your child's age",
    "intro": "Pick the right window & prep",
    "age": "Child's age",
    "age_0_2": "0–2 yrs",
    "age_3_5": "3–5 yrs",
    "age_6_12": "6–12 yrs",
    "temperature": "Feels like",
    "rain": "Rain chance",
    "wind": "Wind",
    "uv": "UV index",
    "submit": "Get Ready",
    "result_good": "A great day to go out!",
    "result_check": "Check the tips below first",
    "result_short": "Keep outings short today",
    "result_indoor": "An indoor day is best",
    "checklist": "Going-out checklist",
    "rain_gear": "Rain gear",
    "rain_heavy": "Raincoat + spare clothes",
    "water": "Water bottle",
    "sun_hat": "Sun hat",
    "sunscreen": "Sunscreen",
    "layers": "Thin layers",
    "warm_hat": "Warm hat",
    "cold": "Feels cold — dress in layers",
    "hot": "Feels hot — keep kids hydrated",
    "strong_uv": "Strong UV — avoid midday, reapply sunscreen",
    "windy": "Very windy — keep little ones covered",
    "calm_wind": "Calm winds",
    "no_rain": "No rain gear needed",
    "age_note": (
        "Ages 0–2 use more conservative temperature prompts; ages 3–12 use "
        "the standard weather thresholds. This changes preparation tips only "
        "and is not a child safety assessment."
    ),
    "uv_note": (
        "UV index: sun strength — 3+ use sun care, 8+ avoid midday"
    ),
    "rain_note": (
        "Rain chance: higher means more likely to rain — bring rain gear or stay in"
    ),
    "wind_note": (
        "Wind (km/h): stronger feels colder — pack a jacket for little ones"
    ),
}

STYLE = """
:root{--sky:#eaf7ff;--cream:#fffaf0;--ink:#17233a;--muted:#58677e;--line:rgba(75,107,145,.18);--blue:#2869d8;--violet:#7258da;--green:#187b60;--amber:#a35e08;--red:#a53643}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.58;background:radial-gradient(circle at 12% 0,#fff 0 8rem,transparent 22rem),linear-gradient(145deg,var(--sky),#f6f3ff 47%,var(--cream))}
a{color:#2459b8}
.wrap{width:min(1120px,100% - 32px);margin:auto}
.top{position:sticky;top:0;z-index:5;padding:14px 0;border-bottom:1px solid var(--line);background:rgba(255,255,255,.82);backdrop-filter:blur(18px)}
.nav{display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:800;white-space:nowrap}
.hero{padding:clamp(42px,8vw,86px) 0 26px}.eyebrow{display:inline-flex;border:1px solid rgba(40,105,216,.18);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.68);color:var(--blue);font-size:.78rem;font-weight:900;letter-spacing:.07em}
h1{max-width:850px;margin:.22em 0;font-size:clamp(2.25rem,7vw,5rem);line-height:.98;letter-spacing:-.045em}
.lead{max-width:760px;margin:0;color:var(--muted);font-size:clamp(1.05rem,2.3vw,1.3rem)}
.privacy{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}.badge{border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.72);font-size:.86rem;font-weight:760}
.layout{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,.8fr);gap:22px;align-items:start}
.card{border:1px solid var(--line);border-radius:28px;padding:clamp(19px,3vw,30px);background:rgba(255,255,255,.9);box-shadow:0 22px 70px rgba(40,69,111,.1)}
.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
.field.full{grid-column:1/-1}
label{display:block;max-width:100%;margin-bottom:6px;overflow-x:auto;font-size:clamp(.72rem,1.55vw,.88rem);font-weight:850;white-space:nowrap;scrollbar-width:none}
input,select{width:100%;min-height:48px;border:1px solid #c8d4e4;border-radius:14px;padding:10px 12px;background:#fff;color:var(--ink);font:inherit;font-weight:720}
input:focus,select:focus{outline:3px solid rgba(40,105,216,.17);border-color:var(--blue)}
.button{display:inline-flex;min-height:48px;align-items:center;justify-content:center;border:0;border-radius:999px;padding:12px 20px;background:linear-gradient(135deg,var(--blue),var(--violet));color:#fff!important;text-decoration:none;font-weight:900;box-shadow:0 13px 30px rgba(55,88,188,.25);cursor:pointer;white-space:nowrap}
.result{margin-top:22px;border:1px solid rgba(40,105,216,.18);border-radius:22px;padding:20px;background:linear-gradient(140deg,#eef7ff,#f8f4ff)}
.signal{display:flex;align-items:center;gap:11px}.signal-dot{width:14px;height:14px;border-radius:50%;background:var(--blue);box-shadow:0 0 0 7px rgba(40,105,216,.1)}.signal h2{margin:0;font-size:clamp(1.35rem,3vw,2rem)}
.result[data-level="0"] .signal-dot{background:var(--green)}.result[data-level="1"] .signal-dot{background:var(--amber)}.result[data-level="2"] .signal-dot,.result[data-level="3"] .signal-dot{background:var(--red)}
.summary{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0}.pill{border:1px solid rgba(36,89,184,.16);border-radius:999px;padding:6px 10px;background:#fff;font-size:.85rem;font-weight:800;white-space:nowrap}
.prompts{margin:12px 0 0;padding-inline-start:1.25rem}.prompts li{margin:.42em 0}
.boundary{border-inline-start:4px solid var(--amber);border-radius:9px;padding:10px 13px;background:#fff8e8;color:#674716;font-size:.9rem}
.side h2,.sources h2,.app-card h2{margin-top:0}.facts{display:grid;gap:10px}.fact{border:1px solid var(--line);border-radius:16px;padding:12px;background:#fff}.fact strong{display:block;margin-bottom:3px}
.sources,.app-card{margin-top:22px}.sources ul{columns:2;column-gap:28px}.sources li{break-inside:avoid;margin:.55em 0}
.app-card{background:linear-gradient(140deg,#172b54,#3d3277);color:#fff}.app-card p{color:#e7eaff}.app-card .button{background:#fff;color:#243c78!important;box-shadow:none}
.footer{padding:32px 0 46px;color:var(--muted);font-size:.9rem}
@media(max-width:820px){.layout{grid-template-columns:1fr}.sources ul{columns:1}.nav{overflow-x:auto}}
@media(max-width:560px){.fields{grid-template-columns:1fr}.field.full{grid-column:auto}.wrap{width:min(100% - 22px,1120px)}.card{border-radius:22px}.button{width:100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

SCRIPT = r"""
(function(){
  "use strict";
  const config = JSON.parse(document.getElementById("outing-config").textContent);
  const form = document.getElementById("outing-form");
  const result = document.getElementById("outing-result");
  const signal = document.getElementById("result-signal");
  const summary = document.getElementById("result-summary");
  const prompts = document.getElementById("result-prompts");

  function finite(value, name, minimum, maximum) {
    let number;
    if (typeof value === "number") {
      number = value;
    } else if (typeof value === "string" && value.trim() !== "") {
      number = Number(value);
    } else {
      throw new TypeError(name + " is required.");
    }
    if (!Number.isFinite(number) || number < minimum || number > maximum) {
      throw new RangeError(name + " is outside the supported range.");
    }
    return number;
  }

  function normalize(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("Planner input must be an object.");
    }
    if (!["metric", "imperial"].includes(input.units)) {
      throw new RangeError("units is unsupported.");
    }
    if (!["0-2", "3-5", "6-12"].includes(input.child_age)) {
      throw new RangeError("child_age is unsupported.");
    }
    if (typeof input.official_alert_or_poor_air !== "boolean") {
      throw new TypeError("official_alert_or_poor_air must be boolean.");
    }
    const temperature = finite(input.feels_like_temperature, "temperature", -100, 150);
    const wind = finite(input.wind_speed, "wind_speed", 0, 300);
    const temperatureC =
      input.units === "metric" ? temperature : (temperature - 32) * 5 / 9;
    const windKmh = input.units === "metric" ? wind : wind * 1.609344;
    finite(temperatureC, "temperature_c", -60, 60);
    finite(windKmh, "wind_kmh", 0, 200);
    return {
      units: input.units,
      childAge: input.child_age,
      temperatureC,
      windKmh,
      rainChance: finite(input.rain_chance, "rain_chance", 0, 100),
      uvIndex: finite(input.uv_index, "uv_index", 0, 20),
      alert: input.official_alert_or_poor_air
    };
  }

  function plan(input) {
    const value = normalize(input);
    let level = 0;
    const promptKeys = [];
    const add = (key) => {
      if (!promptKeys.includes(key)) promptKeys.push(key);
    };
    const raise = (next) => { level = Math.max(level, next); };

    if (value.alert) raise(3);
    if (value.temperatureC <= -26 || value.temperatureC >= 40) raise(3);
    else if (value.temperatureC <= 0 || value.temperatureC >= 35) raise(2);
    else if (value.temperatureC <= 5 || value.temperatureC >= 30) raise(1);
    if (value.childAge === "0-2" &&
        (value.temperatureC < 10 || value.temperatureC > 28)) raise(1);
    if (value.uvIndex >= 8) raise(2);
    else if (value.uvIndex >= 3) raise(1);
    if (value.windKmh >= 80) raise(3);
    else if (value.windKmh >= 50) raise(2);
    else if (value.windKmh >= 30) raise(1);
    if (value.rainChance >= 80) raise(1);

    if (value.temperatureC <= 10) {
      add("cold"); add("layers"); add("warm_hat");
    }
    if (value.temperatureC >= 28) {
      add("hot"); add("water"); add("sun_hat");
    }
    if (value.uvIndex >= 8) add("strong_uv");
    if (value.uvIndex >= 3) {
      add("sunscreen"); add("sun_hat");
    }
    if (value.rainChance >= 70) add("rain_heavy");
    else if (value.rainChance >= 30) add("rain_gear");
    else add("no_rain");
    if (value.windKmh >= 30) add("windy");
    else add("calm_wind");

    return {
      level,
      signalKey: ["result_good", "result_check", "result_short", "result_indoor"][level],
      promptKeys,
      normalized: {
        feels_like_c: Math.round(value.temperatureC * 10) / 10,
        wind_kmh: Math.round(value.windKmh * 10) / 10,
        rain_chance_percent: value.rainChance,
        uv_index: value.uvIndex,
        child_age: value.childAge,
        official_alert_or_poor_air: value.alert
      }
    };
  }

  function currentInput() {
    return {
      units: document.getElementById("units").value,
      child_age: document.getElementById("child-age").value,
      feels_like_temperature: document.getElementById("temperature").value,
      rain_chance: document.getElementById("rain").value,
      wind_speed: document.getElementById("wind").value,
      uv_index: document.getElementById("uv").value,
      official_alert_or_poor_air:
        document.getElementById("alerts").value !== "clear"
    };
  }

  function syncInputBounds() {
    const imperial = document.getElementById("units").value === "imperial";
    const temperature = document.getElementById("temperature");
    const wind = document.getElementById("wind");
    temperature.min = imperial ? "-76" : "-60";
    temperature.max = imperial ? "140" : "60";
    wind.max = imperial ? "124.2" : "200";
  }

  function render() {
    result.hidden = true;
    syncInputBounds();
    if (!form.checkValidity()) {
      return;
    }
    const output = plan(currentInput());
    result.hidden = false;
    result.dataset.level = String(output.level);
    signal.textContent = config.labels[output.signalKey];
    summary.replaceChildren();
    const values = output.normalized;
    const summaries = [
      config.labels.temperature + ": " + values.feels_like_c + " °C",
      config.labels.rain + ": " + values.rain_chance_percent + "%",
      config.labels.wind + ": " + values.wind_kmh + " km/h",
      config.labels.uv + ": " + values.uv_index
    ];
    for (const text of summaries) {
      const item = document.createElement("span");
      item.className = "pill";
      item.textContent = text;
      summary.appendChild(item);
    }
    prompts.replaceChildren();
    for (const key of output.promptKeys) {
      const item = document.createElement("li");
      item.textContent = config.labels[key];
      prompts.appendChild(item);
    }
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_family_outing_weather",
      description: config.webmcpDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const output = plan(input);
        const response = {
          result_type: "family_outing_weather_planning_prompt",
          planning_signal: config.labels[output.signalKey],
          planning_signal_level: output.level,
          normalized_conditions: output.normalized,
          planning_prompts: output.promptKeys.map((key) => config.labels[key]),
          boundary: config.boundary,
          no_weather_or_location_access: true,
          no_safety_or_medical_assessment: true,
          official_sources: config.sources,
          free_planner_url: config.url
        };
        if (config.optionalApp) response.optional_lumi_weather = config.optionalApp;
        return JSON.stringify(response);
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  for (const field of form.elements) {
    field.addEventListener("change", render);
    field.addEventListener("input", render);
  }
  render();
  registerWebMcp().catch((error) =>
    console.error("WebMCP tool registration failed.", error));
})();
"""


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_content() -> tuple[dict[str, object], dict[str, object]]:
    i18n = load_json(I18N_PATH)
    weather = load_json(WEATHER_META_PATH)
    if set(weather) != set(LOCALES):
        raise ValueError("weather_full.json must contain the official 50 locales")
    phrases = i18n.get("phrases")
    custom = i18n.get("custom")
    if not isinstance(phrases, dict) or not isinstance(custom, dict):
        raise ValueError("planner i18n requires phrases and custom objects")
    languages = set(LOCALE_TO_LANGUAGE.values())
    for phrase in PHRASE_KEYS.values():
        localized = phrases.get(phrase)
        if not isinstance(localized, dict) or set(localized) != languages:
            raise ValueError(f"incomplete planner phrase: {phrase}")
    if set(custom) != languages:
        raise ValueError("custom planner copy must cover every language")
    for language, copy in custom.items():
        if not isinstance(copy, dict) or set(copy) != {
            "alert_label",
            "alert_clear",
            "alert_unclear",
            "boundary",
            "local_only",
            "sources_title",
        }:
            raise ValueError(f"incomplete custom copy: {language}")
    return i18n, weather


def localized_copy(
    locale: str,
    i18n: dict[str, object],
) -> dict[str, str]:
    if locale not in LOCALE_TO_LANGUAGE:
        raise ValueError(f"unsupported locale: {locale}")
    language = LOCALE_TO_LANGUAGE[locale]
    phrases = i18n["phrases"]
    custom = i18n["custom"]
    assert isinstance(phrases, dict)
    assert isinstance(custom, dict)
    result = {}
    for alias, phrase in PHRASE_KEYS.items():
        values = phrases[phrase]
        assert isinstance(values, dict)
        result[alias] = str(values[language])
    custom_values = custom[language]
    assert isinstance(custom_values, dict)
    result.update({key: str(value) for key, value in custom_values.items()})
    return result


def canonical(locale: str) -> str:
    prefix = "" if locale == "en-US" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def relative_page(locale: str) -> Path:
    base = Path("tools") if locale == "en-US" else Path(locale) / "tools"
    return base / f"{SLUG}.html"


def page_locale(path: Path, pages: Path = PAGES) -> str:
    relative = path.relative_to(pages)
    if relative.parts[0] == "answers":
        return "en-US"
    return relative.parts[0]


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def webmcp_input_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "units": {"type": "string", "enum": ["metric", "imperial"]},
            "child_age": {
                "type": "string",
                "enum": ["0-2", "3-5", "6-12"],
            },
            "feels_like_temperature": {
                "type": "number",
                "minimum": -100,
                "maximum": 150,
            },
            "rain_chance": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "wind_speed": {
                "type": "number",
                "minimum": 0,
                "maximum": 300,
            },
            "uv_index": {
                "type": "number",
                "minimum": 0,
                "maximum": 20,
            },
            "official_alert_or_poor_air": {"type": "boolean"},
        },
        "required": [
            "units",
            "child_age",
            "feels_like_temperature",
            "rain_chance",
            "wind_speed",
            "uv_index",
            "official_alert_or_poor_air",
        ],
        "allOf": [
            {
                "if": {
                    "properties": {"units": {"const": "metric"}},
                    "required": ["units"],
                },
                "then": {
                    "properties": {
                        "feels_like_temperature": {
                            "minimum": -60,
                            "maximum": 60,
                        },
                        "wind_speed": {"minimum": 0, "maximum": 200},
                    }
                },
            },
            {
                "if": {
                    "properties": {"units": {"const": "imperial"}},
                    "required": ["units"],
                },
                "then": {
                    "properties": {
                        "feels_like_temperature": {
                            "minimum": -76,
                            "maximum": 140,
                        },
                        "wind_speed": {"minimum": 0, "maximum": 124.2},
                    }
                },
            },
        ],
        "additionalProperties": False,
    }


def render_page(
    locale: str,
    app_public: bool,
    i18n: dict[str, object] | None = None,
    weather: dict[str, object] | None = None,
) -> str:
    if i18n is None or weather is None:
        i18n, weather = load_content()
    t = localized_copy(locale, i18n)
    meta = weather[locale]
    if not isinstance(meta, dict):
        raise ValueError(f"invalid weather metadata: {locale}")
    app_name = str(meta["name"])
    app_description = str(meta["promotionalText"])
    planner_description = f'{t["heading"]} {t["local_only"]}'
    url = canonical(locale)
    prefix = "" if locale == "en-US" else f"{locale}/"
    home = f"{SITE}/{prefix}index.html"
    app_landing = f"{SITE}/{locale}/lumiweather.html"
    share_image = f"{SITE}/social/img/lumiweather-share.jpg"
    direction = "rtl" if locale in RTL_LOCALES else "ltr"
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{html.escape(other, quote=True)}" '
        f'href="{html.escape(canonical(other), quote=True)}">'
        for other in LOCALES
    )
    tracked_url = (
        appstore_url(APP_KEY, f"iag_outing_plan_{locale.lower()}")
        if app_public
        else ""
    )
    app_schema = ""
    banner = ""
    app_card = ""
    optional_app = None
    if tracked_url:
        app_schema = json_script(
            {
                "@context": "https://schema.org",
                "@type": "MobileApplication",
                "name": app_name,
                "operatingSystem": "iOS",
                "applicationCategory": "LifestyleApplication",
                "url": tracked_url,
                "installUrl": tracked_url,
                "description": app_description,
                "identifier": {
                    "@type": "PropertyValue",
                    "propertyID": "Apple App Store ID",
                    "value": APP_ID,
                },
            }
        )
        banner = f'<meta name="apple-itunes-app" content="app-id={APP_ID}">'
        app_card = (
            '<section class="app-card card wrap">'
            f"<h2>{html.escape(app_name)}</h2>"
            f"<p>{html.escape(app_description)}</p>"
            f'<a class="button" href="{html.escape(tracked_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(app_name)} · App Store →</a>'
            "</section>"
        )
        optional_app = {
            "name": app_name,
            "promotional_text": app_description,
            "app_store_url": tracked_url,
        }
    source_rows = (
        ("WHO", t["uv"]),
        ("CDC", t["checklist"]),
        ("AAP", t["cold"]),
        ("NOAA / NWS", f'{t["wind"]} · {t["result_indoor"]}'),
        ("NOAA / NWS", t["result_check"]),
    )
    sources_html = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(org)} · {html.escape(label)}</a></li>"
        for (org, label), source in zip(source_rows, SOURCES, strict=True)
    )
    facts = (
        ("uv_note", WHO_UV),
        ("rain_note", CDC_OUTDOOR),
        ("wind_note", NWS_WIND_CHILL),
        ("age_note", CDC_OUTDOOR),
    )
    facts_html = "".join(
        '<div class="fact"><strong>'
        f'{html.escape(t["result_check"])}</strong>'
        f'<span>{html.escape(t[key])}</span> '
        f'<a href="{html.escape(source, quote=True)}" rel="noopener">↗</a></div>'
        for key, source in facts
    )
    age_options = "".join(
        f'<option value="{value}">{html.escape(t[key])}</option>'
        for value, key in (
            ("0-2", "age_0_2"),
            ("3-5", "age_3_5"),
            ("6-12", "age_6_12"),
        )
    )
    web_schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": planner_description,
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_MODIFIED,
        "applicationCategory": "LifestyleApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "User-entered weather planning prompts",
            "No location, account, storage or network request",
            "Explicit official-alert and poor-air-quality check",
            "Transparent conservative prompt boundaries",
            "Progressive read-only WebMCP interface",
        ],
        "citation": list(SOURCES),
    }
    config = {
        "locale": locale,
        "url": url,
        "boundary": t["boundary"],
        "sources": list(SOURCES),
        "inputSchema": webmcp_input_schema(),
        "labels": {
            key: t[key]
            for key in (
                "temperature",
                "rain",
                "wind",
                "uv",
                "result_good",
                "result_check",
                "result_short",
                "result_indoor",
                "rain_gear",
                "rain_heavy",
                "water",
                "sun_hat",
                "sunscreen",
                "layers",
                "warm_hat",
                "cold",
                "hot",
                "strong_uv",
                "windy",
                "calm_wind",
                "no_rain",
            )
        },
        "webmcpDescription": (
            "Turn bounded user-entered feels-like temperature, rain chance, "
            "wind, UV, child age and an explicit official-alert/poor-air check "
            "into conservative planning prompts. Do not fetch weather or "
            "location, and do not provide a safety or medical assessment."
        ),
        "optionalApp": optional_app,
    }
    config_json = json.dumps(
        config, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="{html.escape(locale, quote=True)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["heading"])} | {html.escape(app_name)}</title>
<meta name="description" content="{html.escape(planner_description, quote=True)}">
<link rel="canonical" href="{html.escape(url, quote=True)}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{canonical("en-US")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"], quote=True)}">
<meta property="og:description" content="{html.escape(planner_description, quote=True)}">
<meta property="og:url" content="{html.escape(url, quote=True)}">
<meta property="og:image" content="{share_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="675">
<meta property="og:image:alt" content="{html.escape(app_name, quote=True)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{share_image}">
<meta name="theme-color" content="#eaf7ff">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<style>{STYLE}</style>
{json_script(web_schema)}
{app_schema}
{banner}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><a href="{app_landing}">{html.escape(app_name)}</a></div></header>
<main>
<section class="hero wrap"><span class="eyebrow">{html.escape(t["submit"])} · 50 locales</span><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])} · {html.escape(t["intro"])}</p><div class="privacy"><span class="badge">⌁ {html.escape(t["local_only"])}</span><span class="badge">⚠︎ {html.escape(t["boundary"])}</span></div></section>
<section class="layout wrap">
<article class="card">
<form id="outing-form">
<div class="fields">
<div class="field"><label for="units">°C · km/h / °F · mph</label><select id="units"><option value="metric">°C · km/h</option><option value="imperial">°F · mph</option></select></div>
<div class="field"><label for="child-age">{html.escape(t["age"])}</label><select id="child-age">{age_options}</select></div>
<div class="field"><label for="temperature">{html.escape(t["temperature"])}</label><input id="temperature" type="number" min="-60" max="60" step="0.1" value="18" inputmode="decimal" required></div>
<div class="field"><label for="rain">{html.escape(t["rain"])}</label><input id="rain" type="number" min="0" max="100" step="1" value="20" inputmode="numeric" required></div>
<div class="field"><label for="wind">{html.escape(t["wind"])}</label><input id="wind" type="number" min="0" max="200" step="0.1" value="8" inputmode="decimal" required></div>
<div class="field"><label for="uv">{html.escape(t["uv"])}</label><input id="uv" type="number" min="0" max="20" step="0.1" value="3" inputmode="decimal" required></div>
<div class="field full"><label for="alerts">⚠︎ {html.escape(t["alert_label"])}</label><select id="alerts"><option value="unclear">{html.escape(t["alert_unclear"])}</option><option value="clear">{html.escape(t["alert_clear"])}</option></select></div>
</div>
<p><button class="button" type="submit">{html.escape(t["submit"])}</button></p>
</form>
<section class="result" id="outing-result" data-level="3" aria-live="polite"><div class="signal"><span class="signal-dot" aria-hidden="true"></span><h2 id="result-signal"></h2></div><div class="summary" id="result-summary"></div><h3>{html.escape(t["checklist"])}</h3><ul class="prompts" id="result-prompts"></ul><p class="boundary">{html.escape(t["boundary"])}</p></section>
</article>
<aside class="card side"><h2>{html.escape(t["result_check"])}</h2><div class="facts">{facts_html}</div></aside>
</section>
<section class="sources card wrap"><h2>{html.escape(t["sources_title"])}</h2><ul>{sources_html}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">WebMCP preview specification ↗</a></p></section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["local_only"])} · {html.escape(t["boundary"])}</div></footer>
<script type="application/json" id="outing-config">{config_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def index_card(
    locale: str,
    i18n: dict[str, object],
) -> str:
    t = localized_copy(locale, i18n)
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["heading"])}</a></h2>'
        f'<p>{html.escape(t["lead"])} · {html.escape(t["local_only"])}</p>'
        "</article>"
    )


def index_path(locale: str, pages: Path = PAGES) -> Path:
    if locale == "en-US":
        return pages / "tools" / "index.html"
    return pages / locale / "tools" / "index.html"


def update_tools_indexes(
    pages: Path,
    i18n: dict[str, object],
) -> int:
    changed = 0
    for locale in INDEX_LOCALES:
        path = index_path(locale, pages)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        card = index_card(locale, i18n)
        existing = re.compile(
            rf'<article class="card third" data-tool="{re.escape(SLUG)}">'
            rf".*?</article>",
            re.S,
        )
        updated = existing.sub("", text)
        weather_anchor = re.compile(
            r'(<article class="card third"><h2><a href="'
            r'kids-weather-clothing-calculator\.html">.*?</article>)',
            re.S,
        )
        if weather_anchor.search(updated):
            updated = weather_anchor.sub(r"\1" + card, updated, count=1)
        else:
            marker = '<section class="wrap grid">'
            if marker not in updated:
                raise RuntimeError(f"{path} is missing its tools grid")
            updated = updated.replace(marker, marker + card, 1)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def update_inbound_links(
    pages: Path,
    i18n: dict[str, object],
) -> int:
    changed = 0
    for slug in ANSWER_SLUGS:
        for path in pages.glob(f"**/answers/{slug}"):
            locale = page_locale(path, pages)
            if locale not in LOCALE_TO_LANGUAGE:
                continue
            text = path.read_text(encoding="utf-8")
            t = localized_copy(locale, i18n)
            href = canonical(locale)
            item = (
                f'<li class="{INBOUND_LINK_CLASS}"><a href="'
                f'{html.escape(href, quote=True)}">'
                f'{html.escape(t["heading"])}</a></li>'
            )
            existing = re.compile(
                rf'<li class="{re.escape(INBOUND_LINK_CLASS)}">.*?</li>',
                re.S,
            )
            updated = existing.sub("", text)
            canonical_item = re.compile(
                r'<li\b[^>]*>\s*<a\b[^>]*\bhref=(["\'])'
                + re.escape(href)
                + r"\1[^>]*>.*?</a>\s*</li>",
                re.S,
            )
            updated = canonical_item.sub("", updated)
            marker = re.compile(
                r'(<section class="wrap related-tools"><h2>.*?</h2><ul>)',
                re.S,
            )
            if marker.search(updated):
                updated = marker.sub(r"\1" + item, updated, count=1)
            else:
                end_main = "</main>"
                if end_main not in updated:
                    raise RuntimeError(f"{path} is missing </main>")
                section = (
                    '<section class="wrap related-tools">'
                    f'<h2>{html.escape(t["heading"])}</h2><ul>{item}</ul>'
                    "</section>"
                )
                updated = updated.replace(end_main, section + end_main, 1)
            if updated != text:
                path.write_text(updated, encoding="utf-8")
                changed += 1
    return changed


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    i18n, weather = load_content()
    if app_public is None:
        app_public = APP_KEY in live_app_keys(
            APPSTORE, pages, refresh=False
        )
    urls = []
    for locale in LOCALES:
        write_text_if_changed(
            pages / relative_page(locale),
            render_page(locale, app_public, i18n, weather),
        )
        urls.append(canonical(locale))
    update_tools_indexes(pages, i18n)
    update_inbound_links(pages, i18n)
    return urls


def main() -> None:
    urls = build()
    sitemap_count = write_tools_sitemap()
    print(f"family outing weather planner -> {len(urls)} locale pages")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
