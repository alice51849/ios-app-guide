#!/usr/bin/env python3
"""Generate deterministic, private Zhuyin blending practice cards."""

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

from appstore_live import live_app_keys # noqa: E402
from bopomofo_flashcards import ( # noqa: E402
  ALT_LOCALES,
  APP_ID,
  APP_KEY,
  MOE_HANDBOOK,
  MOE_STROKE_ORDER,
  UNICODE_CHART_PDF,
)
from gen_calculator import write_tools_sitemap # noqa: E402
from gen_feed import feed_discovery_links # noqa: E402
from videogen.registry import APPSTORE, appstore_url # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
  "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-blending-card-generator"
CONTENT_DATE = "2026-07-15"
MODE_VALUES = ("two", "three", "tones")
CARD_COUNTS = (4, 8, 12)
SET_NUMBER_MIN = 1
SET_NUMBER_MAX = 999
DEFAULT_CARD_COUNT = 8
DEFAULT_SET_NUMBER = 1

BLENDS = {
  "two": [
    {"parts": ["ㄅ", "ㄚ"], "blend": "ㄅㄚ", "word": "爸", "reading": "ㄅㄚˋ"},
    {"parts": ["ㄆ", "ㄛ"], "blend": "ㄆㄛ", "word": "坡", "reading": "ㄆㄛ"},
    {"parts": ["ㄇ", "ㄧ"], "blend": "ㄇㄧ", "word": "米", "reading": "ㄇㄧˇ"},
    {"parts": ["ㄈ", "ㄟ"], "blend": "ㄈㄟ", "word": "飛", "reading": "ㄈㄟ"},
    {"parts": ["ㄉ", "ㄚ"], "blend": "ㄉㄚ", "word": "大", "reading": "ㄉㄚˋ"},
    {"parts": ["ㄊ", "ㄨ"], "blend": "ㄊㄨ", "word": "兔", "reading": "ㄊㄨˋ"},
    {"parts": ["ㄋ", "ㄧ"], "blend": "ㄋㄧ", "word": "你", "reading": "ㄋㄧˇ"},
    {"parts": ["ㄌ", "ㄧ"], "blend": "ㄌㄧ", "word": "梨", "reading": "ㄌㄧˊ"},
    {"parts": ["ㄍ", "ㄡ"], "blend": "ㄍㄡ", "word": "狗", "reading": "ㄍㄡˇ"},
    {"parts": ["ㄎ", "ㄢ"], "blend": "ㄎㄢ", "word": "看", "reading": "ㄎㄢˋ"},
    {"parts": ["ㄏ", "ㄠ"], "blend": "ㄏㄠ", "word": "好", "reading": "ㄏㄠˇ"},
    {"parts": ["ㄓ", "ㄨ"], "blend": "ㄓㄨ", "word": "豬", "reading": "ㄓㄨ"},
    {"parts": ["ㄔ", "ㄜ"], "blend": "ㄔㄜ", "word": "車", "reading": "ㄔㄜ"},
    {"parts": ["ㄕ", "ㄨ"], "blend": "ㄕㄨ", "word": "書", "reading": "ㄕㄨ"},
    {"parts": ["ㄖ", "ㄣ"], "blend": "ㄖㄣ", "word": "人", "reading": "ㄖㄣˊ"},
    {"parts": ["ㄙ", "ㄢ"], "blend": "ㄙㄢ", "word": "三", "reading": "ㄙㄢ"},
  ],
  "three": [
    {
      "parts": ["ㄐ", "ㄧ", "ㄚ"],
      "blend": "ㄐㄧㄚ",
      "word": "家",
      "reading": "ㄐㄧㄚ",
    },
    {
      "parts": ["ㄑ", "ㄧ", "ㄡ"],
      "blend": "ㄑㄧㄡ",
      "word": "球",
      "reading": "ㄑㄧㄡˊ",
    },
    {
      "parts": ["ㄒ", "ㄧ", "ㄠ"],
      "blend": "ㄒㄧㄠ",
      "word": "小",
      "reading": "ㄒㄧㄠˇ",
    },
    {
      "parts": ["ㄉ", "ㄧ", "ㄢ"],
      "blend": "ㄉㄧㄢ",
      "word": "電",
      "reading": "ㄉㄧㄢˋ",
    },
    {
      "parts": ["ㄊ", "ㄧ", "ㄢ"],
      "blend": "ㄊㄧㄢ",
      "word": "天",
      "reading": "ㄊㄧㄢ",
    },
    {
      "parts": ["ㄋ", "ㄧ", "ㄠ"],
      "blend": "ㄋㄧㄠ",
      "word": "鳥",
      "reading": "ㄋㄧㄠˇ",
    },
    {
      "parts": ["ㄌ", "ㄧ", "ㄥ"],
      "blend": "ㄌㄧㄥ",
      "word": "零",
      "reading": "ㄌㄧㄥˊ",
    },
    {
      "parts": ["ㄍ", "ㄨ", "ㄚ"],
      "blend": "ㄍㄨㄚ",
      "word": "瓜",
      "reading": "ㄍㄨㄚ",
    },
    {
      "parts": ["ㄎ", "ㄨ", "ㄞ"],
      "blend": "ㄎㄨㄞ",
      "word": "快",
      "reading": "ㄎㄨㄞˋ",
    },
    {
      "parts": ["ㄏ", "ㄨ", "ㄚ"],
      "blend": "ㄏㄨㄚ",
      "word": "花",
      "reading": "ㄏㄨㄚ",
    },
    {
      "parts": ["ㄓ", "ㄨ", "ㄥ"],
      "blend": "ㄓㄨㄥ",
      "word": "中",
      "reading": "ㄓㄨㄥ",
    },
    {
      "parts": ["ㄔ", "ㄨ", "ㄤ"],
      "blend": "ㄔㄨㄤ",
      "word": "床",
      "reading": "ㄔㄨㄤˊ",
    },
    {
      "parts": ["ㄕ", "ㄨ", "ㄟ"],
      "blend": "ㄕㄨㄟ",
      "word": "水",
      "reading": "ㄕㄨㄟˇ",
    },
    {
      "parts": ["ㄖ", "ㄨ", "ㄢ"],
      "blend": "ㄖㄨㄢ",
      "word": "軟",
      "reading": "ㄖㄨㄢˇ",
    },
    {
      "parts": ["ㄗ", "ㄨ", "ㄟ"],
      "blend": "ㄗㄨㄟ",
      "word": "嘴",
      "reading": "ㄗㄨㄟˇ",
    },
    {
      "parts": ["ㄙ", "ㄨ", "ㄢ"],
      "blend": "ㄙㄨㄢ",
      "word": "酸",
      "reading": "ㄙㄨㄢ",
    },
  ],
  "tones": [
    {
      "base": "ㄇㄚ",
      "items": [
        {"word": "媽", "reading": "ㄇㄚ"},
        {"word": "麻", "reading": "ㄇㄚˊ"},
        {"word": "馬", "reading": "ㄇㄚˇ"},
        {"word": "罵", "reading": "ㄇㄚˋ"},
      ],
    },
    {
      "base": "ㄅㄚ",
      "items": [
        {"word": "八", "reading": "ㄅㄚ"},
        {"word": "拔", "reading": "ㄅㄚˊ"},
        {"word": "把", "reading": "ㄅㄚˇ"},
        {"word": "爸", "reading": "ㄅㄚˋ"},
      ],
    },
    {
      "base": "ㄉㄚ",
      "items": [
        {"word": "搭", "reading": "ㄉㄚ"},
        {"word": "達", "reading": "ㄉㄚˊ"},
        {"word": "打", "reading": "ㄉㄚˇ"},
        {"word": "大", "reading": "ㄉㄚˋ"},
      ],
    },
    {
      "base": "ㄊㄤ",
      "items": [
        {"word": "湯", "reading": "ㄊㄤ"},
        {"word": "糖", "reading": "ㄊㄤˊ"},
        {"word": "躺", "reading": "ㄊㄤˇ"},
        {"word": "燙", "reading": "ㄊㄤˋ"},
      ],
    },
  ],
}


def validate_blends() -> None:
  for mode, part_count in (("two", 2), ("three", 3)):
    for item in BLENDS[mode]:
      if len(item["parts"]) != part_count:
        raise ValueError(f"{mode} card has the wrong part count: {item}")
      if "".join(item["parts"]) != item["blend"]:
        raise ValueError(f"{mode} card parts do not form its blend: {item}")
      if item["reading"].rstrip("ˊˇˋ˙") != item["blend"]:
        raise ValueError(f"{mode} card reading does not match its blend: {item}")
  for ladder in BLENDS["tones"]:
    if len(ladder["items"]) != 4:
      raise ValueError(f"tone ladder must contain four examples: {ladder}")
    for item in ladder["items"]:
      if item["reading"].rstrip("ˊˇˋ˙") != ladder["base"]:
        raise ValueError(f"tone example does not match its base: {item}")


def _coprime_step(length: int, set_number: int) -> int:
  candidate = 1 + ((set_number * 5 + length) % (length - 1))
  while True:
    left, right = candidate, length
    while right:
      left, right = right, left % right
    if left == 1:
      return candidate
    candidate = candidate % (length - 1) + 1


def build_card_set(
  mode: str,
  card_count: int,
  set_number: int,
) -> dict[str, object]:
  if not isinstance(mode, str):
    raise TypeError("mode must be a string")
  if mode not in MODE_VALUES:
    raise ValueError("unsupported mode")
  for name, value in (("card_count", card_count), ("set_number", set_number)):
    if not isinstance(value, int) or isinstance(value, bool):
      raise TypeError(f"{name} must be an integer")
  if card_count not in CARD_COUNTS:
    raise ValueError("unsupported card_count")
  if not SET_NUMBER_MIN <= set_number <= SET_NUMBER_MAX:
    raise ValueError("unsupported set_number")
  if mode == "tones" and card_count != 4:
    raise ValueError("tone mode requires exactly four cards")
  source = BLENDS[mode]
  count = min(card_count, len(source))
  offset = (set_number - 1) % len(source)
  step = _coprime_step(len(source), set_number)
  cards = [
    source[(offset + index * step) % len(source)]
    for index in range(count)
  ]
  return {
    "selected_inputs": {
      "mode": mode,
      "card_count": card_count,
      "set_number": set_number,
    },
    "cards": cards,
  }


validate_blends()


COPY = {
  "en": {
    "title": "Free Zhuyin Blending Practice Card Generator",
    "description": (
      "Make private, printable Zhuyin practice cards for two-symbol joins, "
      "three-symbol joins and Mandarin tones. No score, login, upload or profile."
    ),
    "tools": "Free tools",
    "switch": "繁體中文",
    "eyebrow": "Free · private · no score",
    "heading": "Zhuyin blending practice cards",
    "lead": (
      "For a child who can recognise ㄅㄆㄇ but pauses when symbols need to "
      "be joined. Build a short set, say each part slowly, slide the sounds "
      "together, then reveal a familiar word."
    ),
    "privacy": "No name, account, score, upload or saved profile",
    "scope": "Original practice activity; not a test or diagnosis",
    "builder": "Build a short practice set",
    "mode_label": "Choose one step",
    "mode_two": "Two-symbol joins",
    "mode_three": "Three-symbol joins",
    "mode_tones": "Tone ladder",
    "count": "Cards",
    "set_number": "Set number",
    "set_help": "Same mode, count, and set number always return the same ordered cards.",
    "new_set": "Next set",
    "reveal_all": "Reveal all",
    "hide_all": "Hide all",
    "print": "Print cards",
    "share": "Share tool",
    "tap": "Tap to reveal",
    "hide": "Tap to hide",
    "prompt": "Say each part, then join",
    "tone_prompt": "Blend the base, then try four tones",
    "ready": "Tap any card to reveal its joined syllable and familiar word.",
    "shared": "Share sheet opened.",
    "cancelled": "Sharing was cancelled.",
    "copied": "Tool link copied.",
    "copy_failed": "Copy was unavailable. Use this link:",
    "two_help": (
      "Point to the first symbol, pause, say the second, then slide your "
      "finger toward the joined syllable."
    ),
    "three_help": (
      "Keep the middle ㄧ, ㄨ or ㄩ connected like a bridge. Join all three "
      "without turning the activity into a speed test."
    ),
    "tones_help": (
      "Blend the unmarked base first. Reveal the familiar words only when "
      "the base is comfortable."
    ),
    "why_title": "Recognition and blending are different steps",
    "why_text": (
      "A symbol flashcard asks “what is this?” These cards ask the next "
      "question: “how do these sounds become one syllable?” The generator "
      "uses a small curated set of familiar Mandarin examples, not every "
      "possible syllable."
    ),
    "routine_title": "A calm four-step routine",
    "routine": [
      "Point to each visible symbol without asking for speed.",
      "Say the parts with a short pause between them.",
      "Move a finger across the card while shortening the pause.",
      "Reveal the joined syllable and connect it to the familiar word.",
    ],
    "gentle_title": "Keep it low-pressure",
    "gentle_text": (
      "Use only a few cards at a time. Repeat, switch sets or stop whenever "
      "the child wants. This tool records no answers and cannot measure "
      "mastery, readiness or a learning difficulty."
    ),
    "print_note": (
      "Printing reveals every answer and removes the controls. Cut the cards "
      "apart or keep them on one sheet for finger-sliding practice."
    ),
    "app_title": "Want guided audio after the paper activity?",
    "app_text": (
      "Lumi Bopomofo is an optional next step with guided listening, tracing, "
      "tones and syllable-blending games. It uses a one-time unlock "
      "with no ads, subscription or account."
    ),
    "app_cta": "See Lumi Bopomofo on the App Store",
    "sources": "Sources and scope",
    "source_labels": [
      "Taiwan Ministry of Education: Mandarin Phonetic Symbols handbook",
      "Taiwan Ministry of Education: standard character and Zhuyin forms",
      "Unicode: official Bopomofo character chart",
    ],
    "source_note": (
      "The official references support standard symbols, notation and forms. "
      "They do not prescribe, evaluate or endorse this original card activity. "
      "No Ministry images, audio, animations or worksheets are reproduced."
    ),
    "faq": [
      (
        "Does this tool score my child?",
        "No. It has no correct/wrong buttons, timer, score, level or saved progress.",
      ),
      (
        "Is this a complete Mandarin syllable table?",
        "No. It is a short practice generator using familiar examples for joining sounds and comparing four tones.",
      ),
      (
        "Does the tool diagnose a learning difficulty or school readiness?",
        "No. It is a parent-guided practice activity, not an assessment, diagnosis or readiness measure.",
      ),
      (
        "Does any practice data leave the browser?",
        "No practice answers are collected. Selections stay in page memory and reset when the page closes.",
      ),
    ],
    "index_title": "Zhuyin Blending Practice Cards",
    "index_description": (
      "Printable two-symbol, three-symbol and tone practice with no scores or profiles."
    ),
    "inline_link": "Open the free deterministic Zhuyin blending-card maker",
    "webmcp_description": (
      "Return one reproducible set of curated two-symbol, three-symbol, or "
      "four-tone Zhuyin cards from fixed mode, count, and set-number choices. "
      "Read-only: accepts no child data, name, free text, file, audio, answer, "
      "score, assessment, diagnosis, or learning-outcome claim."
    ),
  },
  "zh-Hant": {
    "title": "免費注音拼讀練習卡產生器｜二拼、三拼與聲調",
    "description": (
      "免費產生可列印的注音拼讀練習卡：練二符拼讀、三符拼讀與四聲。"
      "不計分、免登入、不上傳、不建立兒童檔案。"
    ),
    "tools": "免費工具",
    "switch": "English",
    "eyebrow": "免費・私密・不計分",
    "heading": "注音拼讀練習卡產生器",
    "lead": (
      "孩子會認 ㄅㄆㄇ，合起來卻常停住時，可先做短短一組拼讀卡："
      "慢慢念每個符號、用手指把聲音滑近，再翻卡看熟悉的例字。"
    ),
    "privacy": "不填姓名、免帳號、不計分、不上傳、不儲存個人檔案",
    "scope": "原創練習活動；不是測驗、診斷或入學準備度判定",
    "builder": "建立一組短練習",
    "mode_label": "選一個練習步驟",
    "mode_two": "二符拼讀",
    "mode_three": "三符拼讀",
    "mode_tones": "四聲階梯",
    "count": "卡片張數",
    "set_number": "組別編號",
    "set_help": "練習類型、張數與組別編號相同時，卡片與順序一定相同。",
    "new_set": "下一組",
    "reveal_all": "全部翻開",
    "hide_all": "全部蓋回",
    "print": "列印練習卡",
    "share": "分享工具",
    "tap": "點卡看答案",
    "hide": "點卡蓋回",
    "prompt": "分開念，再合起來",
    "tone_prompt": "先拼底音，再試四聲",
    "ready": "點任何卡片，即可翻開拼讀結果與熟悉例字。",
    "shared": "已開啟分享選單。",
    "cancelled": "已取消分享。",
    "copied": "已複製工具連結。",
    "copy_failed": "無法自動複製，請使用這個連結：",
    "two_help": (
      "先指第一個符號，停一下再念第二個；接著用手指往右滑，"
      "把停頓慢慢縮短。"
    ),
    "three_help": (
      "把中間的 ㄧ、ㄨ 或 ㄩ 當成橋，三個聲音連在一起即可；"
      "不需要計時，也不用比速度。"
    ),
    "tones_help": (
      "先把沒有聲調記號的底音拼順，再翻卡連結四個熟悉例字。"
    ),
    "why_title": "認得符號，和把聲音拼起來是不同步驟",
    "why_text": (
      "一般符號字卡問的是「這是什麼？」；這組卡接著練「這些聲音怎麼合成"
      "一個音節？」工具只使用一小組熟悉的華語例字，不是完整音節表。"
    ),
    "routine_title": "低壓力四步驟",
    "routine": [
      "先指每個看得到的符號，不催速度。",
      "把每個聲音分開念，中間留一點停頓。",
      "手指沿著卡片往右滑，同時慢慢縮短停頓。",
      "翻開完整拼音，再連到下方的熟悉例字。",
    ],
    "gentle_title": "一次幾張就好",
    "gentle_text": (
      "可以重複、換組，或在孩子不想繼續時停下來。工具不記錄答案，"
      "也不能衡量熟練度、入學準備度或判定任何學習困難。"
    ),
    "print_note": (
      "列印時會自動顯示全部答案並隱藏操作按鈕。可剪成小卡，"
      "也可保留整張做手指滑讀。"
    ),
    "app_title": "紙卡之後想要有引導音檔？",
    "app_text": (
      "Lumi 注音星球是選配的下一步，提供聽音、描寫、聲調與拼讀遊戲。"
      "一次付費永久解鎖，無廣告、無訂閱、免帳號。"
    ),
    "app_cta": "前往 App Store 查看 Lumi 注音星球",
    "sources": "資料來源與適用範圍",
    "source_labels": [
      "教育部《國語注音符號手冊》",
      "教育部常用國字標準字體筆順學習網",
      "Unicode 官方注音符號圖表",
    ],
    "source_note": (
      "官方資料只用來核對標準符號、標音與字形；教育部沒有設計、測試或"
      "推薦本練習卡。本站未重製教育部圖片、音檔、動畫或練習單。"
    ),
    "faq": [
      (
        "這個工具會替孩子打分數嗎？",
        "不會。沒有答對答錯按鈕、計時、分數、等級或儲存進度。",
      ),
      (
        "這是完整的國語音節表嗎？",
        "不是。這是用熟悉例字練習合音與四聲的小型產生器。",
      ),
      (
        "它能判斷學習困難或入學準備度嗎？",
        "不能。這是家長陪伴的練習活動，不是評量、診斷或準備度測驗。",
      ),
      (
        "練習資料會離開瀏覽器嗎？",
        "不會收集練習答案；選項只留在目前頁面的記憶體，關閉後即重設。",
      ),
    ],
    "index_title": "注音拼讀練習卡產生器",
    "index_description": "免費建立二符、三符與四聲練習卡；不計分、不建立兒童檔案。",
    "inline_link": "開啟免費固定可重現的注音拼讀練習卡",
    "webmcp_description": (
      "依固定的練習類型、張數與組別編號，回傳可重現的二符、三符或四聲注音練習卡。"
      "唯讀工具：不接收兒童資料、姓名、自由文字、檔案、錄音、答案、分數、評量、"
      "診斷或學習成效聲明。"
    ),
  },
  "es-ES": {
    "title": "Tarjetas imprimibles para combinar Zhuyin",
    "description": (
      "Crea tarjetas privadas e imprimibles para unir dos o tres símbolos "
      "Zhuyin y comparar los cuatro tonos. Sin puntuación, cuenta ni subida."
    ),
    "tools": "Herramientas gratis",
    "switch": "English",
    "eyebrow": "Gratis · privado · reproducible",
    "heading": "Tarjetas para combinar sonidos Zhuyin",
    "lead": (
      "Para quien reconoce ㄅㄆㄇ pero se detiene al unir los sonidos. Elige "
      "un conjunto corto, pronuncia cada parte y descubre después la sílaba."
    ),
    "privacy": "Sin nombre, cuenta, respuestas, subida ni perfil infantil",
    "scope": "Actividad original; no es una prueba ni un diagnóstico",
    "builder": "Prepara un conjunto breve",
    "mode_label": "Elige un paso",
    "mode_two": "Uniones de dos símbolos",
    "mode_three": "Uniones de tres símbolos",
    "mode_tones": "Escalera de cuatro tonos",
    "count": "Tarjetas",
    "set_number": "Número de conjunto",
    "set_help": "El mismo modo, cantidad y número siempre devuelve las mismas tarjetas.",
    "new_set": "Conjunto siguiente",
    "reveal_all": "Mostrar todo",
    "hide_all": "Ocultar todo",
    "print": "Imprimir tarjetas",
    "share": "Compartir herramienta",
    "tap": "Toca para mostrar",
    "hide": "Toca para ocultar",
    "prompt": "Di cada parte y luego únelas",
    "tone_prompt": "Une la base y prueba cuatro tonos",
    "ready": "Toca una tarjeta para ver la sílaba unida y una palabra conocida.",
    "shared": "Se abrió el menú para compartir.",
    "cancelled": "Se canceló la acción de compartir.",
    "copied": "Se copió el enlace.",
    "copy_failed": "No se pudo copiar. Usa este enlace:",
    "two_help": (
      "Señala el primer símbolo, haz una pausa, di el segundo y desliza el "
      "dedo hacia la sílaba unida."
    ),
    "three_help": (
      "Mantén ㄧ, ㄨ o ㄩ como puente y une las tres partes sin convertirlo "
      "en una prueba de velocidad."
    ),
    "tones_help": (
      "Une primero la base sin marca. Muestra las palabras solo cuando la "
      "base resulte cómoda."
    ),
    "why_title": "Reconocer y combinar son pasos distintos",
    "why_text": (
      "Una tarjeta de símbolos pregunta qué es cada signo; estas tarjetas "
      "practican cómo varias partes forman una sílaba. Incluyen solo ejemplos "
      "seleccionados, no todas las sílabas posibles."
    ),
    "routine_title": "Rutina tranquila en cuatro pasos",
    "routine": [
      "Señala cada símbolo sin pedir rapidez.",
      "Pronuncia las partes con una pausa breve.",
      "Desliza un dedo mientras acortas la pausa.",
      "Muestra la sílaba y relaciónala con la palabra conocida.",
    ],
    "gentle_title": "Sin presión",
    "gentle_text": (
      "Usa pocas tarjetas y para cuando el niño quiera. La herramienta no "
      "registra respuestas ni mide dominio, preparación o dificultad."
    ),
    "print_note": (
      "Al imprimir se muestran todas las respuestas y se ocultan los controles. "
      "Recorta las tarjetas o conserva la hoja para deslizar el dedo."
    ),
    "app_title": "¿Quieres audio guiado después del papel?",
    "app_text": (
      "Lumi Bopomofo es un paso opcional con escucha, trazado, tonos y juegos "
      "de combinación. Desbloqueo permanente de pago único, sin anuncios ni cuenta."
    ),
    "app_cta": "Ver Lumi Bopomofo en App Store",
    "sources": "Fuentes y alcance",
    "source_labels": [
      "Ministerio de Educación de Taiwán: manual de símbolos fonéticos",
      "Ministerio de Educación de Taiwán: referencia de trazos Zhuyin",
      "Unicode: tabla oficial de Bopomofo",
    ],
    "source_note": (
      "Las fuentes oficiales respaldan los símbolos y la notación, pero no "
      "diseñan, evalúan ni recomiendan esta actividad. No se reproducen sus materiales."
    ),
    "faq": [
      ("¿Puntúa a mi hijo?", "No. No hay aciertos, errores, tiempo, nivel ni progreso guardado."),
      ("¿Es una tabla completa de sílabas?", "No. Es un conjunto breve de ejemplos para combinar sonidos y comparar tonos."),
      ("¿Diagnostica una dificultad?", "No. Es práctica acompañada, no evaluación, diagnóstico ni medida escolar."),
      ("¿Salen datos del navegador?", "No se recogen respuestas; los ajustes se reinician al cerrar la página."),
    ],
    "index_title": "Tarjetas para combinar Zhuyin",
    "index_description": "Tarjetas reproducibles de dos y tres símbolos y cuatro tonos, sin perfiles ni puntuación.",
    "inline_link": "Abrir el creador gratuito de tarjetas para combinar Zhuyin",
    "webmcp_description": (
      "Devuelve un conjunto reproducible de tarjetas Zhuyin de dos símbolos, "
      "tres símbolos o cuatro tonos a partir de opciones fijas. Solo lectura: "
      "no acepta datos infantiles, texto libre, archivos, respuestas ni evaluaciones."
    ),
  },
  "pt-BR": {
    "title": "Cartões imprimíveis para combinar Zhuyin",
    "description": (
      "Crie cartões privados e imprimíveis para unir dois ou três símbolos "
      "Zhuyin e comparar os quatro tons. Sem pontuação, conta ou envio."
    ),
    "tools": "Ferramentas grátis",
    "switch": "English",
    "eyebrow": "Grátis · privado · reproduzível",
    "heading": "Cartões para combinar sons em Zhuyin",
    "lead": (
      "Para quem reconhece ㄅㄆㄇ, mas pausa ao juntar os sons. Escolha um "
      "conjunto curto, diga cada parte e só depois revele a sílaba."
    ),
    "privacy": "Sem nome, conta, respostas, envio ou perfil infantil",
    "scope": "Atividade original; não é teste nem diagnóstico",
    "builder": "Monte um conjunto curto",
    "mode_label": "Escolha uma etapa",
    "mode_two": "Junções de dois símbolos",
    "mode_three": "Junções de três símbolos",
    "mode_tones": "Escada dos quatro tons",
    "count": "Cartões",
    "set_number": "Número do conjunto",
    "set_help": "O mesmo modo, quantidade e número sempre gera os mesmos cartões.",
    "new_set": "Próximo conjunto",
    "reveal_all": "Revelar tudo",
    "hide_all": "Ocultar tudo",
    "print": "Imprimir cartões",
    "share": "Compartilhar ferramenta",
    "tap": "Toque para revelar",
    "hide": "Toque para ocultar",
    "prompt": "Diga cada parte e depois junte",
    "tone_prompt": "Junte a base e experimente quatro tons",
    "ready": "Toque em um cartão para revelar a sílaba e uma palavra conhecida.",
    "shared": "O menu de compartilhamento foi aberto.",
    "cancelled": "O compartilhamento foi cancelado.",
    "copied": "Link copiado.",
    "copy_failed": "Não foi possível copiar. Use este link:",
    "two_help": (
      "Aponte o primeiro símbolo, faça uma pausa, diga o segundo e deslize o "
      "dedo até a sílaba unida."
    ),
    "three_help": (
      "Use ㄧ, ㄨ ou ㄩ como ponte e una as três partes sem transformar a "
      "atividade em teste de velocidade."
    ),
    "tones_help": (
      "Combine primeiro a base sem marca. Revele as palavras apenas quando "
      "a base estiver confortável."
    ),
    "why_title": "Reconhecer e combinar são etapas diferentes",
    "why_text": (
      "Um cartão de símbolos pergunta o que cada sinal é; estes cartões "
      "praticam como as partes formam uma sílaba. Há apenas exemplos "
      "selecionados, não todas as sílabas possíveis."
    ),
    "routine_title": "Rotina tranquila em quatro etapas",
    "routine": [
      "Aponte cada símbolo sem cobrar rapidez.",
      "Diga as partes com uma pausa curta.",
      "Deslize o dedo enquanto reduz a pausa.",
      "Revele a sílaba e conecte-a à palavra conhecida.",
    ],
    "gentle_title": "Sem pressão",
    "gentle_text": (
      "Use poucos cartões e pare quando a criança quiser. A ferramenta não "
      "registra respostas nem mede domínio, prontidão ou dificuldade."
    ),
    "print_note": (
      "Na impressão, todas as respostas aparecem e os controles somem. "
      "Recorte os cartões ou mantenha a folha para deslizar o dedo."
    ),
    "app_title": "Quer áudio guiado depois da atividade no papel?",
    "app_text": (
      "Lumi Bopomofo é uma etapa opcional com escuta, traçado, tons e jogos "
      "de combinação. Desbloqueio com pagamento único, sem anúncios ou conta."
    ),
    "app_cta": "Ver Lumi Bopomofo na App Store",
    "sources": "Fontes e escopo",
    "source_labels": [
      "Ministério da Educação de Taiwan: manual de símbolos fonéticos",
      "Ministério da Educação de Taiwan: referência de traços Zhuyin",
      "Unicode: tabela oficial de Bopomofo",
    ],
    "source_note": (
      "As fontes oficiais sustentam os símbolos e a notação, mas não criaram, "
      "avaliaram nem recomendam esta atividade. Nenhum material oficial é reproduzido."
    ),
    "faq": [
      ("A ferramenta dá nota à criança?", "Não. Não há certo ou errado, tempo, nível ou progresso salvo."),
      ("É uma tabela completa de sílabas?", "Não. É um conjunto curto para juntar sons e comparar tons."),
      ("Diagnostica alguma dificuldade?", "Não. É prática acompanhada, não avaliação, diagnóstico ou medida escolar."),
      ("Algum dado sai do navegador?", "Nenhuma resposta é coletada; as escolhas são redefinidas ao fechar a página."),
    ],
    "index_title": "Cartões para combinar Zhuyin",
    "index_description": "Cartões reproduzíveis de dois e três símbolos e quatro tons, sem perfil ou nota.",
    "inline_link": "Abrir o criador gratuito de cartões para combinar Zhuyin",
    "webmcp_description": (
      "Retorna um conjunto reproduzível de cartões Zhuyin de dois símbolos, "
      "três símbolos ou quatro tons com opções fixas. Somente leitura: não "
      "aceita dados infantis, texto livre, arquivos, respostas ou avaliações."
    ),
  },
  "de-DE": {
    "title": "Druckbare Karten zum Verbinden von Zhuyin-Lauten",
    "description": (
      "Erstelle private, druckbare Karten für Verbindungen aus zwei oder drei "
      "Zhuyin-Zeichen und zum Vergleich der vier Töne. Ohne Konto oder Bewertung."
    ),
    "tools": "Kostenlose Tools",
    "switch": "English",
    "eyebrow": "Kostenlos · privat · reproduzierbar",
    "heading": "Übungskarten zum Verbinden von Zhuyin-Lauten",
    "lead": (
      "Für Lernende, die ㄅㄆㄇ erkennen, beim Verbinden aber stocken. Wähle "
      "ein kurzes Set, sprich jeden Teil und decke erst danach die Silbe auf."
    ),
    "privacy": "Kein Name, Konto, Upload, Ergebnis oder Kinderprofil",
    "scope": "Eigene Übung; kein Test und keine Diagnose",
    "builder": "Kurzes Übungsset erstellen",
    "mode_label": "Einen Schritt wählen",
    "mode_two": "Zwei Zeichen verbinden",
    "mode_three": "Drei Zeichen verbinden",
    "mode_tones": "Vier-Töne-Leiter",
    "count": "Karten",
    "set_number": "Set-Nummer",
    "set_help": "Gleicher Modus, gleiche Anzahl und Set-Nummer ergeben stets dieselben Karten.",
    "new_set": "Nächstes Set",
    "reveal_all": "Alle aufdecken",
    "hide_all": "Alle verdecken",
    "print": "Karten drucken",
    "share": "Tool teilen",
    "tap": "Zum Aufdecken tippen",
    "hide": "Zum Verdecken tippen",
    "prompt": "Teile sprechen, dann verbinden",
    "tone_prompt": "Grundsilbe verbinden, dann vier Töne",
    "ready": "Tippe auf eine Karte, um Silbe und Beispielwort aufzudecken.",
    "shared": "Das Teilen-Menü wurde geöffnet.",
    "cancelled": "Teilen wurde abgebrochen.",
    "copied": "Link wurde kopiert.",
    "copy_failed": "Kopieren war nicht möglich. Nutze diesen Link:",
    "two_help": (
      "Zeige auf das erste Zeichen, pausiere, sprich das zweite und gleite "
      "mit dem Finger zur verbundenen Silbe."
    ),
    "three_help": (
      "Nutze ㄧ, ㄨ oder ㄩ als Brücke und verbinde alle drei Teile ohne "
      "Zeitdruck."
    ),
    "tones_help": (
      "Verbinde zuerst die unmarkierte Grundsilbe. Decke die Wörter erst auf, "
      "wenn sich die Basis sicher anfühlt."
    ),
    "why_title": "Erkennen und Verbinden sind verschiedene Schritte",
    "why_text": (
      "Zeichenkarten fragen nach einem einzelnen Symbol; diese Karten üben, "
      "wie Teile eine Silbe bilden. Sie enthalten ausgewählte Beispiele, "
      "keine vollständige Mandarin-Silbentabelle."
    ),
    "routine_title": "Ruhige Routine in vier Schritten",
    "routine": [
      "Auf jedes sichtbare Zeichen zeigen, ohne Tempo zu verlangen.",
      "Die Teile mit einer kurzen Pause sprechen.",
      "Mit dem Finger gleiten und die Pause verkürzen.",
      "Die Silbe aufdecken und mit dem Beispielwort verbinden.",
    ],
    "gentle_title": "Ohne Druck üben",
    "gentle_text": (
      "Nutze wenige Karten und höre jederzeit auf. Das Tool speichert keine "
      "Antworten und misst weder Können noch Schulreife oder Schwierigkeiten."
    ),
    "print_note": (
      "Beim Drucken werden alle Antworten sichtbar und Bedienelemente "
      "ausgeblendet. Karten ausschneiden oder als Gleitblatt verwenden."
    ),
    "app_title": "Nach der Papierübung geführtes Audio nutzen?",
    "app_text": (
      "Lumi Bopomofo ist eine optionale Ergänzung mit Hören, Nachspuren, Tönen "
      "und Verbindungsübungen. Einmalige Freischaltung, ohne Werbung oder Konto."
    ),
    "app_cta": "Lumi Bopomofo im App Store ansehen",
    "sources": "Quellen und Grenzen",
    "source_labels": [
      "Taiwans Bildungsministerium: Handbuch der Lautzeichen",
      "Taiwans Bildungsministerium: Zhuyin-Strichreferenz",
      "Unicode: offizielle Bopomofo-Tabelle",
    ],
    "source_note": (
      "Die offiziellen Quellen belegen Zeichen und Notation, haben diese "
      "Übung aber weder gestaltet noch geprüft oder empfohlen. Inhalte werden nicht kopiert."
    ),
    "faq": [
      ("Bewertet das Tool mein Kind?", "Nein. Es gibt kein Richtig oder Falsch, keinen Timer, Rang oder Speicherstand."),
      ("Ist dies eine vollständige Silbentabelle?", "Nein. Es ist eine kurze Auswahl zum Verbinden und Vergleichen von Tönen."),
      ("Diagnostiziert es Schwierigkeiten?", "Nein. Es ist begleitete Übung, keine Bewertung, Diagnose oder Schulreifeprüfung."),
      ("Verlassen Übungsdaten den Browser?", "Nein. Antworten werden nicht erfasst; Einstellungen verfallen beim Schließen."),
    ],
    "index_title": "Zhuyin-Laute verbinden",
    "index_description": "Reproduzierbare Karten für zwei und drei Zeichen sowie vier Töne, ohne Profil oder Bewertung.",
    "inline_link": "Kostenlose Zhuyin-Verbindungskarten öffnen",
    "webmcp_description": (
      "Gibt mit festen Optionen ein reproduzierbares Set aus zwei Zeichen, "
      "drei Zeichen oder vier Zhuyin-Tönen zurück. Schreibgeschützt: keine "
      "Kinderdaten, Freitexte, Dateien, Antworten, Bewertungen oder Diagnosen."
    ),
  },
  "fr-FR": {
    "title": "Cartes imprimables pour combiner les sons Zhuyin",
    "description": (
      "Créez des cartes privées et imprimables pour unir deux ou trois signes "
      "Zhuyin et comparer les quatre tons. Sans score, compte ni envoi."
    ),
    "tools": "Outils gratuits",
    "switch": "English",
    "eyebrow": "Gratuit · privé · reproductible",
    "heading": "Cartes pour combiner les sons Zhuyin",
    "lead": (
      "Pour l’enfant qui reconnaît ㄅㄆㄇ mais hésite à unir les sons. Choisissez "
      "un petit lot, prononcez chaque partie, puis révélez la syllabe."
    ),
    "privacy": "Sans nom, compte, réponse, envoi ni profil d’enfant",
    "scope": "Activité originale, ni test ni diagnostic",
    "builder": "Créer un petit lot",
    "mode_label": "Choisir une étape",
    "mode_two": "Unions de deux signes",
    "mode_three": "Unions de trois signes",
    "mode_tones": "Échelle des quatre tons",
    "count": "Cartes",
    "set_number": "Numéro du lot",
    "set_help": "Le même mode, nombre et numéro donne toujours les mêmes cartes.",
    "new_set": "Lot suivant",
    "reveal_all": "Tout révéler",
    "hide_all": "Tout masquer",
    "print": "Imprimer les cartes",
    "share": "Partager l’outil",
    "tap": "Touchez pour révéler",
    "hide": "Touchez pour masquer",
    "prompt": "Prononcez chaque partie, puis unissez",
    "tone_prompt": "Unissez la base, puis essayez quatre tons",
    "ready": "Touchez une carte pour révéler la syllabe et un mot familier.",
    "shared": "Le menu de partage est ouvert.",
    "cancelled": "Le partage a été annulé.",
    "copied": "Lien copié.",
    "copy_failed": "Copie indisponible. Utilisez ce lien :",
    "two_help": (
      "Pointez le premier signe, marquez une pause, dites le second, puis "
      "faites glisser le doigt vers la syllabe réunie."
    ),
    "three_help": (
      "Gardez ㄧ, ㄨ ou ㄩ comme pont et unissez les trois parties sans en "
      "faire un test de vitesse."
    ),
    "tones_help": (
      "Combinez d’abord la base sans marque. Ne révélez les mots que lorsque "
      "la base devient confortable."
    ),
    "why_title": "Reconnaître et combiner sont deux étapes",
    "why_text": (
      "Une carte de signe demande de reconnaître un symbole ; celles-ci "
      "montrent comment les parties forment une syllabe. Les exemples sont "
      "sélectionnés et ne constituent pas une table complète."
    ),
    "routine_title": "Routine calme en quatre étapes",
    "routine": [
      "Pointez chaque signe sans demander de vitesse.",
      "Prononcez les parties avec une courte pause.",
      "Faites glisser le doigt en réduisant la pause.",
      "Révélez la syllabe et reliez-la au mot familier.",
    ],
    "gentle_title": "Sans pression",
    "gentle_text": (
      "Utilisez peu de cartes et arrêtez dès que l’enfant le souhaite. "
      "L’outil n’enregistre rien et ne mesure ni niveau ni difficulté."
    ),
    "print_note": (
      "À l’impression, toutes les réponses sont visibles et les commandes "
      "disparaissent. Découpez les cartes ou gardez la feuille entière."
    ),
    "app_title": "Besoin d’un audio guidé après le papier ?",
    "app_text": (
      "Lumi Bopomofo est une suite facultative avec écoute, tracé, tons et "
      "jeux de combinaison. Déblocage définitif en un achat, sans publicité ni compte."
    ),
    "app_cta": "Voir Lumi Bopomofo sur l’App Store",
    "sources": "Sources et limites",
    "source_labels": [
      "Ministère taïwanais de l’Éducation : manuel des signes phonétiques",
      "Ministère taïwanais de l’Éducation : référence des tracés Zhuyin",
      "Unicode : tableau Bopomofo officiel",
    ],
    "source_note": (
      "Les sources officielles étayent les signes et la notation, mais n’ont "
      "ni conçu, ni évalué, ni recommandé cette activité. Aucun contenu n’est reproduit."
    ),
    "faq": [
      ("L’outil note-t-il mon enfant ?", "Non. Aucun bouton vrai ou faux, minuteur, niveau ou progrès enregistré."),
      ("Est-ce une table complète des syllabes ?", "Non. C’est un petit choix d’exemples pour unir les sons et comparer les tons."),
      ("Diagnostique-t-il une difficulté ?", "Non. C’est une pratique accompagnée, pas une évaluation ou un diagnostic."),
      ("Des données quittent-elles le navigateur ?", "Non. Aucune réponse n’est recueillie et les réglages disparaissent à la fermeture."),
    ],
    "index_title": "Cartes de combinaison Zhuyin",
    "index_description": "Cartes reproductibles à deux ou trois signes et quatre tons, sans profil ni score.",
    "inline_link": "Ouvrir le créateur gratuit de cartes de combinaison Zhuyin",
    "webmcp_description": (
      "Renvoie un lot reproductible de cartes Zhuyin à deux signes, trois "
      "signes ou quatre tons avec des choix fixes. Lecture seule : aucune "
      "donnée d’enfant, texte libre, fichier, réponse, évaluation ou diagnostic."
    ),
  },
  "ja": {
    "title": "印刷できる注音の音節結合カード",
    "description": (
      "2 記号・3 記号の結合と四声を練習する、非公開で印刷可能な注音カードを作成。"
      "採点・アカウント・アップロードなし。"
    ),
    "tools": "無料ツール",
    "switch": "English",
    "eyebrow": "無料・非公開・再現可能",
    "heading": "注音の音をつなぐ練習カード",
    "lead": (
      "ㄅㄆㄇ は分かっても、音をつなぐと止まってしまう学習者向け。短い組を選び、"
      "各部分を発音してから音節と身近な語を確認します。"
    ),
    "privacy": "氏名・アカウント・回答・送信・子どものプロフィールなし",
    "scope": "独自の練習活動であり、テストや診断ではありません",
    "builder": "短い練習セットを作る",
    "mode_label": "練習段階を選ぶ",
    "mode_two": "2 記号をつなぐ",
    "mode_three": "3 記号をつなぐ",
    "mode_tones": "四声の階段",
    "count": "カード枚数",
    "set_number": "セット番号",
    "set_help": "種類・枚数・番号が同じなら、同じ順序のカードが表示されます。",
    "new_set": "次のセット",
    "reveal_all": "すべて表示",
    "hide_all": "すべて隠す",
    "print": "カードを印刷",
    "share": "ツールを共有",
    "tap": "タップして表示",
    "hide": "タップして隠す",
    "prompt": "各部分を発音してからつなぐ",
    "tone_prompt": "基本音節をつなぎ、四声を試す",
    "ready": "カードをタップすると、結合した音節と身近な語を確認できます。",
    "shared": "共有画面を開きました。",
    "cancelled": "共有をキャンセルしました。",
    "copied": "リンクをコピーしました。",
    "copy_failed": "コピーできませんでした。このリンクを使ってください：",
    "two_help": (
      "最初の記号を指し、少し間を置いて次を発音し、指を結合後の音節へ滑らせます。"
    ),
    "three_help": (
      "ㄧ・ㄨ・ㄩ を橋として 3 つをつなぎます。速さを競う活動にはしません。"
    ),
    "tones_help": (
      "まず声調記号のない基本音節をつなぎ、慣れてから身近な語を表示します。"
    ),
    "why_title": "記号の認識と音の結合は別の段階",
    "why_text": (
      "記号カードは一つの記号を問いますが、このカードは複数の部分から音節を作る "
      "練習です。厳選した例のみで、完全な中国語音節表ではありません。"
    ),
    "routine_title": "落ち着いた 4 ステップ",
    "routine": [
      "速さを求めず、見えている記号を指す。",
      "部分ごとに短い間を置いて発音する。",
      "指を滑らせながら間を短くする。",
      "音節を表示し、身近な語と結び付ける。",
    ],
    "gentle_title": "無理なく少しずつ",
    "gentle_text": (
      "一度に数枚だけ使い、いつでもやめられます。回答を保存せず、習熟度・就学準備・"
      "学習上の困難を測定しません。"
    ),
    "print_note": (
      "印刷時は全回答を表示し、操作部分を隠します。切り分けても、一枚のままでも使えます。"
    ),
    "app_title": "紙の活動後に音声ガイドも使いますか？",
    "app_text": (
      "Lumi Bopomofo は、聞き取り・なぞり・声調・音節結合ゲームを含む任意の次の段階です。"
      "買い切りの永久解除で、広告・サブスクリプション・アカウントはありません。"
    ),
    "app_cta": "App Store で Lumi Bopomofo を見る",
    "sources": "出典と範囲",
    "source_labels": [
      "台湾教育部：国語注音符号手冊",
      "台湾教育部：注音の筆順資料",
      "Unicode：公式 Bopomofo 文字表",
    ],
    "source_note": (
      "公式資料は記号と表記の確認に使用していますが、本活動を設計・評価・推奨していません。"
      "公式の画像・音声・教材は転載していません。"
    ),
    "faq": [
      ("子どもを採点しますか？", "いいえ。正誤、時間、得点、段階、保存された進捗はありません。"),
      ("完全な中国語音節表ですか？", "いいえ。音の結合と四声を試すための短い厳選例です。"),
      ("学習上の困難を診断しますか？", "いいえ。保護者と行う練習であり、評価・診断・就学準備判定ではありません。"),
      ("練習データはブラウザ外へ出ますか？", "いいえ。回答を収集せず、設定はページを閉じると消えます。"),
    ],
    "index_title": "注音の音節結合カード",
    "index_description": "2・3 記号と四声の再現可能なカード。プロフィールも採点もありません。",
    "inline_link": "無料の注音結合カード作成ツールを開く",
    "webmcp_description": (
      "固定した種類・枚数・セット番号から、2 記号、3 記号、または四声の再現可能な "
      "注音カードを返します。読み取り専用で、子どもの情報、自由文、ファイル、回答、"
      "評価、診断を受け取りません。"
    ),
  },
  "ko": {
    "title": "인쇄용 주음 결합 연습 카드",
    "description": (
      "두 기호·세 기호 결합과 네 성조를 연습하는 비공개 인쇄용 주음 카드를 만드세요. "
      "채점, 계정, 업로드가 없습니다."
    ),
    "tools": "무료 도구",
    "switch": "English",
    "eyebrow": "무료 · 비공개 · 재현 가능",
    "heading": "주음 소리 결합 연습 카드",
    "lead": (
      "ㄅㄆㄇ은 알아도 소리를 합칠 때 멈추는 학습자를 위한 카드입니다. 짧은 세트를 "
      "고르고 각 부분을 말한 뒤 합쳐진 음절과 익숙한 낱말을 확인하세요."
    ),
    "privacy": "이름, 계정, 답변, 업로드, 아동 프로필 없음",
    "scope": "독자적인 연습 활동이며 시험이나 진단이 아닙니다",
    "builder": "짧은 연습 세트 만들기",
    "mode_label": "연습 단계 선택",
    "mode_two": "두 기호 결합",
    "mode_three": "세 기호 결합",
    "mode_tones": "네 성조 단계",
    "count": "카드 수",
    "set_number": "세트 번호",
    "set_help": "유형, 카드 수, 세트 번호가 같으면 항상 같은 순서가 나옵니다.",
    "new_set": "다음 세트",
    "reveal_all": "모두 보기",
    "hide_all": "모두 가리기",
    "print": "카드 인쇄",
    "share": "도구 공유",
    "tap": "눌러서 보기",
    "hide": "눌러서 가리기",
    "prompt": "각 부분을 말한 뒤 합치기",
    "tone_prompt": "기본 음절을 합친 뒤 네 성조 시도",
    "ready": "카드를 누르면 합쳐진 음절과 익숙한 낱말을 볼 수 있습니다.",
    "shared": "공유 메뉴를 열었습니다.",
    "cancelled": "공유를 취소했습니다.",
    "copied": "도구 링크를 복사했습니다.",
    "copy_failed": "복사할 수 없습니다. 이 링크를 사용하세요:",
    "two_help": (
      "첫 기호를 가리키고 잠시 쉰 뒤 두 번째를 말하며, 손가락을 합쳐진 음절로 움직이세요."
    ),
    "three_help": (
      "ㄧ, ㄨ, ㄩ를 다리처럼 이어 세 부분을 합치되 속도 시험으로 만들지 마세요."
    ),
    "tones_help": (
      "성조 표시가 없는 기본 음절부터 합치고, 익숙해진 뒤 낱말을 보여 주세요."
    ),
    "why_title": "기호 인식과 소리 결합은 다른 단계입니다",
    "why_text": (
      "기호 카드는 하나의 기호를 묻지만, 이 카드는 여러 부분이 한 음절이 되는 과정을 "
      "연습합니다. 엄선한 예시만 있으며 전체 중국어 음절표가 아닙니다."
    ),
    "routine_title": "차분한 네 단계",
    "routine": [
      "속도를 재촉하지 않고 각 기호를 가리킵니다.",
      "부분 사이에 짧은 간격을 두고 말합니다.",
      "손가락을 움직이며 간격을 줄입니다.",
      "음절을 공개하고 익숙한 낱말과 연결합니다.",
    ],
    "gentle_title": "부담 없이 연습하세요",
    "gentle_text": (
      "한 번에 몇 장만 사용하고 언제든 멈추세요. 답변을 기록하지 않으며 숙련도, "
      "취학 준비도, 학습 어려움을 측정하지 않습니다."
    ),
    "print_note": (
      "인쇄하면 모든 답이 보이고 조작 버튼은 숨겨집니다. 카드를 자르거나 한 장으로 사용하세요."
    ),
    "app_title": "종이 활동 뒤 안내 음성을 사용하고 싶나요?",
    "app_text": (
      "Lumi Bopomofo는 듣기, 따라 쓰기, 성조, 음절 결합 게임을 제공하는 선택 단계입니다. "
      "일회성 영구 잠금 해제이며 광고, 구독, 계정이 없습니다."
    ),
    "app_cta": "App Store에서 Lumi Bopomofo 보기",
    "sources": "출처와 범위",
    "source_labels": [
      "대만 교육부: 국어 주음부호 안내서",
      "대만 교육부: 주음 획순 자료",
      "Unicode: 공식 Bopomofo 문자표",
    ],
    "source_note": (
      "공식 자료는 기호와 표기 확인에만 사용했습니다. 공식 기관은 이 활동을 설계, "
      "평가, 추천하지 않았으며 공식 이미지·음성·학습지를 복제하지 않았습니다."
    ),
    "faq": [
      ("아이를 채점하나요?", "아니요. 정오답, 타이머, 점수, 단계, 저장된 진도가 없습니다."),
      ("전체 중국어 음절표인가요?", "아니요. 소리 결합과 네 성조 비교를 위한 짧은 엄선 예시입니다."),
      ("학습 어려움을 진단하나요?", "아니요. 보호자와 하는 연습이며 평가, 진단, 취학 준비도 검사가 아닙니다."),
      ("연습 데이터가 브라우저를 벗어나나요?", "아니요. 답변을 수집하지 않으며 설정은 페이지를 닫으면 초기화됩니다."),
    ],
    "index_title": "주음 소리 결합 카드",
    "index_description": "두·세 기호와 네 성조를 위한 재현 가능한 카드. 프로필과 채점이 없습니다.",
    "inline_link": "무료 주음 결합 카드 만들기 열기",
    "webmcp_description": (
      "고정된 유형, 카드 수, 세트 번호로 두 기호, 세 기호 또는 네 성조의 재현 가능한 "
      "주음 카드를 반환합니다. 읽기 전용이며 아동 정보, 자유문, 파일, 답변, 평가, "
      "진단을 받지 않습니다."
    ),
  },
  "zh-Hans": {
    "title": "免费可打印注音拼读练习卡",
    "description": (
      "生成二符拼读、三符拼读与四声比较的私密可打印注音卡。"
      "不计分、免账号、不上传、不建立儿童档案。"
    ),
    "tools": "免费工具",
    "switch": "English",
    "eyebrow": "免费・私密・可复现",
    "heading": "注音拼读练习卡生成器",
    "lead": (
      "孩子会认 ㄅㄆㄇ，合起来却常停住时，可先练一小组：慢慢读每个符号，"
      "用手指把声音拉近，再翻卡看完整音节与熟悉例字。"
    ),
    "privacy": "不填姓名、免账号、不收答案、不上传、不存儿童档案",
    "scope": "原创练习活动，不是测验、评估或诊断",
    "builder": "生成一组短练习",
    "mode_label": "选择练习步骤",
    "mode_two": "二符拼读",
    "mode_three": "三符拼读",
    "mode_tones": "四声阶梯",
    "count": "卡片数量",
    "set_number": "组别编号",
    "set_help": "练习类型、数量与组别编号相同时，卡片及顺序一定相同。",
    "new_set": "下一组",
    "reveal_all": "全部翻开",
    "hide_all": "全部盖回",
    "print": "打印练习卡",
    "share": "分享工具",
    "tap": "点卡看答案",
    "hide": "点卡盖回",
    "prompt": "分开读，再合起来",
    "tone_prompt": "先拼底音，再试四声",
    "ready": "点任意卡片，即可查看拼读结果与熟悉例字。",
    "shared": "已打开分享菜单。",
    "cancelled": "已取消分享。",
    "copied": "已复制工具链接。",
    "copy_failed": "无法自动复制，请使用这个链接：",
    "two_help": (
      "先指第一个符号，停一下再读第二个；接着用手指滑向完整音节，逐渐缩短停顿。"
    ),
    "three_help": (
      "把中间的 ㄧ、ㄨ 或 ㄩ 当作桥，连起三个声音；不用计时，也不比速度。"
    ),
    "tones_help": (
      "先把没有声调符号的底音拼顺，再翻卡连接四个熟悉例字。"
    ),
    "why_title": "认得符号与拼成音节是两个步骤",
    "why_text": (
      "一般符号卡练“这是什么”，这组卡练“这些声音怎样合成一个音节”。"
      "这里只使用少量精选华语例字，不是完整音节表。"
    ),
    "routine_title": "轻松四步骤",
    "routine": [
      "先指每个符号，不催速度。",
      "分开读每个声音，中间稍停。",
      "手指沿卡片滑动，同时缩短停顿。",
      "翻开完整音节，再连接熟悉例字。",
    ],
    "gentle_title": "一次几张就好",
    "gentle_text": (
      "可以重复、换组，或随时停止。工具不记录答案，也不能衡量熟练度、"
      "入学准备度或判断学习困难。"
    ),
    "print_note": (
      "打印时会显示全部答案并隐藏操作按钮。可剪成小卡，也可保留整张做滑读练习。"
    ),
    "app_title": "纸卡之后想要引导音频？",
    "app_text": (
      "Lumi 注音星球是选用的下一步，提供听音、描写、声调与拼读游戏。"
      "一次付费永久解锁，无广告、无订阅、免账号。"
    ),
    "app_cta": "前往 App Store 查看 Lumi 注音星球",
    "sources": "资料来源与范围",
    "source_labels": [
      "台湾教育部《国语注音符号手册》",
      "台湾教育部注音符号笔顺资料",
      "Unicode 官方注音符号图表",
    ],
    "source_note": (
      "官方资料仅用于核对标准符号与标音；教育部没有设计、测试或推荐本活动。"
      "本站未复制官方图片、音频、动画或练习单。"
    ),
    "faq": [
      ("这个工具会给孩子打分吗？", "不会。没有对错按钮、计时、分数、等级或储存进度。"),
      ("这是完整的国语音节表吗？", "不是。这是用精选例字练习合音与四声的小型工具。"),
      ("它能判断学习困难吗？", "不能。这是家长陪伴的练习，不是评估、诊断或入学准备度测验。"),
      ("练习数据会离开浏览器吗？", "不会收集答案；设置仅留在当前页面，关闭后即重置。"),
    ],
    "index_title": "注音拼读练习卡",
    "index_description": "可复现的二符、三符与四声练习卡；不计分、不建立儿童档案。",
    "inline_link": "打开免费可复现的注音拼读练习卡",
    "webmcp_description": (
      "按固定练习类型、数量与组别编号，返回可复现的二符、三符或四声注音练习卡。"
      "只读工具：不接收儿童资料、姓名、自由文本、文件、录音、答案、分数、评估、"
      "诊断或学习成效声明。"
    ),
  },
}

STYLE = r"""
:root{--bg:#f5f2ec;--paper:#fffdf9;--ink:#20201f;--muted:#68645d;--line:#ded8ce;--plum:#65507b;--plum2:#8b6ba8;--sage:#6f8874;--gold:#c08a3f;--soft:#f2ebf7;--shadow:0 18px 50px rgba(63,48,38,.10)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 10% 0,#fff 0,var(--bg) 45%,#eee8df 100%);color:var(--ink);line-height:1.65}
a{color:#51406b}.wrap{width:min(1120px,100% - 30px);margin:auto}
.top{position:sticky;top:0;z-index:8;background:rgba(255,253,249,.88);border-bottom:1px solid rgba(222,216,206,.9);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px;overflow-x:auto}.nav a{text-decoration:none;font-weight:800;white-space:nowrap}.nav-links{display:flex;gap:16px;align-items:center}.nav-links a{color:var(--muted);font-size:14px;white-space:nowrap}
.hero{padding:58px 0 26px}.eyebrow{display:inline-flex;border:1px solid var(--line);background:rgba(255,255,255,.7);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:850;color:var(--plum);letter-spacing:.03em}
h1{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(38px,7vw,70px);line-height:1.02;letter-spacing:-.035em;margin:.28em 0.24em;white-space:nowrap;overflow-x:auto}
.lead{color:var(--muted);font-size:clamp(17px,2.3vw,21px);margin:0;white-space:nowrap;overflow-x:auto}
.trust{display:flex;flex-wrap:wrap;gap:9px;margin:22px 0 0}.badge{border:1px solid #d9d2c7;background:#fff;border-radius:999px;padding:8px 12px;font-size:13px;font-weight:750;color:#4f5e52}.badge.scope{color:#675774}
.workspace{background:rgba(255,253,249,.96);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}
.workspace-head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.workspace h2,.content-card h2,.cta-card h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0;white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:18px;margin:24px 0 14px;padding:18px;border-radius:22px;background:#f8f4ee;border:1px solid #e7e0d6}
.control-label{display:block;font-size:13px;font-weight:850;color:var(--muted);margin-bottom:8px;white-space:nowrap;overflow-x:auto}.seg{display:flex;flex-wrap:wrap;gap:7px}.seg button,.button,select,input{font:inherit;font-weight:800;border-radius:999px;white-space:nowrap}
.seg button{border:1px solid var(--line);background:#fff;color:var(--muted);padding:9px 13px;cursor:pointer}.seg button.on{background:linear-gradient(135deg,var(--plum),var(--plum2));border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(101,80,123,.18)}
select,input{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 13px;min-width:92px}.mode-help{color:var(--muted);margin:0 0 18px;font-size:14px;white-space:nowrap;overflow-x:auto}
.actions{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0 20px}.button{border:0;background:linear-gradient(135deg,var(--plum),var(--plum2));color:#fff;padding:11px 16px;cursor:pointer;box-shadow:0 8px 20px rgba(101,80,123,.16)}.button.secondary{background:#fff;color:var(--plum);border:1px solid var(--line);box-shadow:none}
.status{min-height:1.5em;color:var(--muted);font-size:14px;margin:0 0 14px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.practice-card{appearance:none;width:100%;min-width:0;text-align:left;background:linear-gradient(160deg,#fff,#fcfaf6);border:1px solid #dcd4c8;border-radius:24px;padding:18px;color:var(--ink);font:inherit;cursor:pointer;box-shadow:0 8px 24px rgba(52,45,38,.06);break-inside:avoid}.practice-card:focus-visible{outline:3px solid #b9a2cf;outline-offset:3px}.practice-card.revealed{border-color:#aa98bc;background:linear-gradient(160deg,#fff,#f7f1fb)}
.card-kicker{display:block;color:var(--muted);font-size:12px;font-weight:800;margin-bottom:12px;white-space:nowrap;overflow-x:auto}.equation{display:flex;align-items:center;gap:9px;flex-wrap:nowrap;overflow-x:auto}.symbol{display:inline-flex;align-items:center;justify-content:center;min-width:54px;height:58px;border:1px solid #d9d0c4;border-radius:16px;background:#fff;font-size:35px;font-weight:850;line-height:1}.join{font-size:25px;color:var(--gold);font-weight:900}.joined{font-size:37px;font-weight:900;color:var(--plum);white-space:nowrap}.mask{display:inline-flex;align-items:center;justify-content:center;min-width:64px;height:58px;border:1px dashed #baaebf;border-radius:16px;color:#988ca0;font-size:28px}.practice-card:not(.revealed).joined,.practice-card:not(.revealed).answer{display:none}.practice-card.revealed.mask{display:none}
.answer{border-top:1px solid var(--line);margin-top:14px;padding-top:12px;display:flex;align-items:baseline;gap:10px}.word{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:32px;font-weight:850}.reading{font-size:23px;font-weight:850;color:var(--sage);white-space:nowrap}.tap{display:block;color:var(--plum);font-size:12px;font-weight:800;text-align:right;margin-top:10px}
.tone-base{font-size:40px;font-weight:900;color:var(--plum);margin-bottom:12px}.tone-row{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.tone-item{border:1px solid var(--line);border-radius:14px;padding:9px 5px;text-align:center;background:#fff}.tone-num{display:block;color:var(--muted);font-size:11px;font-weight:800}.tone-word{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:25px;font-weight:850}.tone-reading{display:block;color:var(--sage);font-size:15px;font-weight:850;white-space:nowrap}.practice-card:not(.revealed).tone-word,.practice-card:not(.revealed).tone-reading{visibility:hidden}
.content-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:30px auto}.content-card{grid-column:span 6;background:rgba(255,253,249,.9);border:1px solid var(--line);border-radius:26px;padding:25px;overflow-x:auto}.content-card.full{grid-column:span 12}.content-card p{color:var(--muted);margin:.8em 0 0;white-space:nowrap}.content-card ol,.content-card ul{margin:14px 0 0;padding-left:22px;color:var(--muted)}.content-card li{margin:.55em 0;white-space:nowrap}
.cta-card{background:linear-gradient(135deg,#443651,#6c517f);color:#fff;border-radius:30px;padding:clamp(24px,5vw,40px);margin:32px auto;overflow-x:auto}.cta-card p{color:#eee5f3;white-space:nowrap}.cta-card.button{background:#fff;color:#4c3b5a;box-shadow:none;text-decoration:none;display:inline-flex;margin-top:8px}
.sources{margin:30px auto 54px;color:var(--muted);font-size:14px;overflow-x:auto}.sources h2{color:var(--ink);white-space:nowrap}.sources p,.sources li,.faq-list summary,.faq-list p{white-space:nowrap}.faq-list{display:grid;gap:10px}.faq-list details{border:1px solid var(--line);border-radius:18px;background:#fff;padding:13px 16px}.faq-list summary{font-weight:850;cursor:pointer}.faq-list p{margin:.6em 0 0;color:var(--muted)}
@media(max-width:760px){.hero{padding-top:38px}.workspace-head{display:block}.controls{grid-template-columns:1fr}.cards{grid-template-columns:1fr}.content-card{grid-column:span 12}.tone-row{gap:4px}.tone-item{padding:8px 2px}.tone-reading{font-size:13px}.nav{align-items:flex-start;padding:13px 0}}
@media print{.top,.hero,.controls,.actions,.status,.mode-help,.tap,.content-grid,.cta-card,.sources,.workspace-head{display:none!important}body{background:#fff}.wrap{width:100%}.workspace{border:0;box-shadow:none;padding:0;margin:0}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:8mm}.practice-card{border:1pt solid #777;border-radius:4mm;box-shadow:none;padding:6mm;page-break-inside:avoid}.practice-card.joined,.practice-card.answer{display:flex!important}.practice-card.mask{display:none!important}.practice-card.tone-word,.practice-card.tone-reading{visibility:visible!important}.practice-card:not(.revealed).answer{display:flex!important}@page{size:A4;margin:11mm}}
"""


def canonical(locale: str) -> str:
  prefix = "" if locale == "en" else f"{locale}/"
  return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict) -> str:
  payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
  return f'<script type="application/ld+json">{payload}</script>'


def webmcp_input_schema(locale: str) -> dict[str, object]:
  t = COPY[locale]
  return {
    "type": "object",
    "properties": {
      "mode": {
        "type": "string",
        "enum": list(MODE_VALUES),
        "description": t["mode_label"],
      },
      "card_count": {
        "type": "integer",
        "enum": list(CARD_COUNTS),
        "description": t["count"],
      },
      "set_number": {
        "type": "integer",
        "minimum": SET_NUMBER_MIN,
        "maximum": SET_NUMBER_MAX,
        "description": t["set_number"],
      },
    },
    "required": ["mode", "card_count", "set_number"],
    "additionalProperties": False,
  }


def render_page(locale: str, app_public: bool) -> str:
  if locale not in COPY:
    raise ValueError(f"unsupported locale: {locale}")
  t = COPY[locale]
  other_locale = "zh-Hant" if locale == "en" else "en"
  url = canonical(locale)
  alternate = canonical(other_locale)
  prefix = "" if locale == "en" else f"{locale}/"
  home = f"{SITE}/{prefix}index.html"
  tools = f"{SITE}/{prefix}tools/index.html"
  alternate_links = "\n".join(
    f'<link rel="alternate" hreflang="{alt}" href="{canonical(alt)}">'
    for alt in ALT_LOCALES
  )
  tracked_app_url = (
    appstore_url(APP_KEY, f"iag_zhuyin_blending_{locale.lower()}")
    if app_public
    else ""
  )
  app_card = ""
  if tracked_app_url:
    app_card = (
      '<section class="cta-card wrap"><h2>'
      f'{html.escape(t["app_title"])}</h2>'
      f'<p>{html.escape(t["app_text"])}</p>'
      f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
      f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
    )
  mode_help = {
    "two": t["two_help"],
    "three": t["three_help"],
    "tones": t["tones_help"],
  }
  client_copy = {
    "tap": t["tap"],
    "hide": t["hide"],
    "prompt": t["prompt"],
    "tonePrompt": t["tone_prompt"],
    "ready": t["ready"],
    "shared": t["shared"],
    "cancelled": t["cancelled"],
    "copied": t["copied"],
    "copyFailed": t["copy_failed"],
    "revealAll": t["reveal_all"],
    "hideAll": t["hide_all"],
    "modeHelp": mode_help,
    "shareTitle": t["heading"],
    "shareText": t["lead"],
    "setHelp": t["set_help"],
  }
  config = {
    "data": BLENDS,
    "copy": client_copy,
    "inputSchema": webmcp_input_schema(locale),
    "toolDescription": t["webmcp_description"],
    "officialSources": [
      {"label": label, "url": source}
      for label, source in zip(
        t["source_labels"],
        (MOE_HANDBOOK, MOE_STROKE_ORDER, UNICODE_CHART_PDF),
        strict=True,
      )
    ],
    "optionalApp": (
      {
        "label": t["app_cta"],
        "boundary": t["app_text"],
        "app_store_url": tracked_app_url,
      }
      if tracked_app_url
      else None
    ),
  }
  schema = {
    "@context": "https://schema.org",
    "@type": ["WebApplication", "LearningResource"],
    "name": t["heading"],
    "description": t["description"],
    "url": url,
    "inLanguage": locale,
    "datePublished": CONTENT_DATE,
    "dateModified": CONTENT_DATE,
    "applicationCategory": "EducationalApplication",
    "operatingSystem": "Any",
    "browserRequirements": "JavaScript",
    "isAccessibleForFree": True,
    "learningResourceType": "Parent-guided printable practice cards",
    "educationalUse": "Practice",
    "educationalLevel": "Beginner",
    "teaches": [
      "Zhuyin syllable blending",
      "Two-symbol Zhuyin combinations",
      "Three-symbol Zhuyin combinations",
      "Mandarin tone comparison",
    ],
    "citation": [MOE_HANDBOOK, MOE_STROKE_ORDER, UNICODE_CHART_PDF],
    "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
  }
  faq_schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "inLanguage": locale,
    "mainEntity": [
      {
        "@type": "Question",
        "name": question,
        "acceptedAnswer": {"@type": "Answer", "text": answer},
      }
      for question, answer in t["faq"]
    ],
  }
  breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": home},
      {"@type": "ListItem", "position": 2, "name": t["tools"], "item": tools},
      {"@type": "ListItem", "position": 3, "name": t["heading"], "item": url},
    ],
  }
  routine = "".join(f"<li>{html.escape(item)}</li>" for item in t["routine"])
  faq = "".join(
    (
      f"<details><summary>{html.escape(question)}</summary>"
      f"<p>{html.escape(answer)}</p></details>"
    )
    for question, answer in t["faq"]
  )
  sources = "".join(
    (
      f'<li><a href="{source}" rel="noopener noreferrer">'
      f"{html.escape(label)}</a></li>"
    )
    for source, label in zip(
      (MOE_HANDBOOK, MOE_STROKE_ORDER, UNICODE_CHART_PDF),
      t["source_labels"],
      strict=True,
    )
  )
  config_json = json.dumps(
    config, ensure_ascii=False, separators=(",", ":")
  ).replace("</", "<\\/")

  return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">
{alternate_links}
<link rel="alternate" hreflang="x-default" href="{canonical("en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
{feed_discovery_links()}
<style>{STYLE}</style>
{json_script(schema)}
{json_script(faq_schema)}
{json_script(breadcrumb)}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="nav-links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap">
<div class="eyebrow">{html.escape(t["eyebrow"])}</div>
<h1>{html.escape(t["heading"])}</h1>
<p class="lead">{html.escape(t["lead"])}</p>
<div class="trust"><span class="badge">{html.escape(t["privacy"])}</span><span class="badge scope">{html.escape(t["scope"])}</span></div>
</section>
<section class="workspace wrap" id="generator">
<div class="workspace-head"><div><h2>{html.escape(t["builder"])}</h2></div></div>
<div class="controls">
<div><span class="control-label">{html.escape(t["mode_label"])}</span><div class="seg" id="mode-buttons" role="group" aria-label="{html.escape(t["mode_label"])}"><button type="button" class="on" data-mode="two">{html.escape(t["mode_two"])}</button><button type="button" data-mode="three">{html.escape(t["mode_three"])}</button><button type="button" data-mode="tones">{html.escape(t["mode_tones"])}</button></div></div>
<label><span class="control-label">{html.escape(t["count"])}</span><select id="card-count"><option value="4">4</option><option value="8" selected>8</option><option value="12">12</option></select></label>
<label><span class="control-label">{html.escape(t["set_number"])}</span><input id="set-number" type="number" min="{SET_NUMBER_MIN}" max="{SET_NUMBER_MAX}" step="1" value="{DEFAULT_SET_NUMBER}" inputmode="numeric"></label>
</div>
<p class="mode-help" id="mode-help">{html.escape(t["two_help"])}</p>
<p class="mode-help">{html.escape(t["set_help"])}</p>
<div class="actions"><button class="button" id="new-set" type="button">{html.escape(t["new_set"])}</button><button class="button secondary" id="reveal-all" type="button">{html.escape(t["reveal_all"])}</button><button class="button secondary" id="print-cards" type="button">{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="status" id="status" aria-live="polite">{html.escape(t["ready"])}</p>
<div class="cards" id="cards"></div>
<p class="mode-help">{html.escape(t["print_note"])}</p>
</section>
<section class="content-grid wrap">
<article class="content-card"><h2>{html.escape(t["why_title"])}</h2><p>{html.escape(t["why_text"])}</p></article>
<article class="content-card"><h2>{html.escape(t["routine_title"])}</h2><ol>{routine}</ol></article>
<article class="content-card full"><h2>{html.escape(t["gentle_title"])}</h2><p>{html.escape(t["gentle_text"])}</p></article>
</section>
{app_card}
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script id="zhuyin-blending-config" type="application/json">{config_json}</script>
<script>
const CONFIG=JSON.parse(document.getElementById("zhuyin-blending-config").textContent);
const DATA=CONFIG.data;
const COPY=CONFIG.copy;
let mode="two";
let count={DEFAULT_CARD_COUNT};
let setNumber={DEFAULT_SET_NUMBER};
let batch=[];
let revealed=new Set();
const cards=document.getElementById("cards");
const countSelect=document.getElementById("card-count");
const setNumberInput=document.getElementById("set-number");
const revealButton=document.getElementById("reveal-all");
const status=document.getElementById("status");
const modeHelp=document.getElementById("mode-help");

function validateInput(input){{
 if(input===null||typeof input!=="object"||Array.isArray(input)){{
  throw new TypeError("WebMCP input must be an object.");
 }}
 const allowed=new Set(Object.keys(CONFIG.inputSchema.properties));
 for(const name of Object.keys(input)){{
  if(!allowed.has(name))throw new RangeError(`${{name}} is not supported.`);
 }}
 for(const name of CONFIG.inputSchema.required){{
  if(!Object.prototype.hasOwnProperty.call(input,name)){{
   throw new TypeError(`${{name}} is required.`);
  }}
 }}
 if(typeof input.mode!=="string"||
   !CONFIG.inputSchema.properties.mode.enum.includes(input.mode)){{
  throw new RangeError("mode is not supported.");
 }}
 for(const name of ["card_count","set_number"]){{
  if(typeof input[name]!=="number"||!Number.isInteger(input[name])){{
   throw new TypeError(`${{name}} must be an integer.`);
  }}
 }}
 if(!CONFIG.inputSchema.properties.card_count.enum.includes(input.card_count)){{
  throw new RangeError("card_count is not supported.");
 }}
 const setSchema=CONFIG.inputSchema.properties.set_number;
 if(input.set_number<setSchema.minimum||input.set_number>setSchema.maximum){{
  throw new RangeError("set_number is not supported.");
 }}
 if(input.mode==="tones"&&input.card_count!==4){{
  throw new RangeError("tone mode requires exactly four cards.");
 }}
 return buildCardSet(input);
}}

function coprimeStep(length,setNumberValue){{
 let candidate=1+((setNumberValue*5+length)%(length-1));
 while(true){{
  let left=candidate;
  let right=length;
  while(right){{
   const remainder=left%right;
   left=right;
   right=remainder;
  }}
  if(left===1)return candidate;
  candidate=candidate%(length-1)+1;
 }}
}}

function buildCardSet(input){{
 const source=DATA[input.mode];
 const amount=Math.min(input.card_count,source.length);
 const offset=(input.set_number-1)%source.length;
 const step=coprimeStep(source.length,input.set_number);
 const selected=[];
 for(let index=0;index<amount;index+=1){{
  selected.push(source[(offset+index*step)%source.length]);
 }}
 return {{
  selected_inputs:{{
   mode:input.mode,
   card_count:input.card_count,
   set_number:input.set_number
  }},
  cards:selected
 }};
}}

function makeBatch(){{
 const result=validateInput({{
  mode,
  card_count:count,
  set_number:setNumber
 }});
 batch=result.cards;
 revealed=new Set();
 render();
}}

function blendCard(item,index){{
 const isOpen=revealed.has(index);
 const symbols=item.parts.map(part=>`<span class="symbol">${{part}}</span>`).join('<span class="join">+</span>');
 return `<button class="practice-card ${{isOpen?"revealed":""}}" type="button" data-index="${{index}}" aria-expanded="${{isOpen}}"><span class="card-kicker">${{COPY.prompt}}</span><div class="equation">${{symbols}}<span class="join">→</span><span class="mask">?</span><span class="joined">${{item.blend}}</span></div><span class="answer"><span class="word">${{item.word}}</span><span class="reading">${{item.reading}}</span></span><span class="tap">${{isOpen?COPY.hide:COPY.tap}}</span></button>`;
}}

function toneCard(item,index){{
 const isOpen=revealed.has(index);
 const tones=item.items.map((tone,toneIndex)=>`<span class="tone-item"><span class="tone-num">${{toneIndex+1}}</span><span class="tone-word">${{tone.word}}</span><span class="tone-reading">${{tone.reading}}</span></span>`).join("");
 return `<button class="practice-card ${{isOpen?"revealed":""}}" type="button" data-index="${{index}}" aria-expanded="${{isOpen}}"><span class="card-kicker">${{COPY.tonePrompt}}</span><div class="tone-base">${{item.base}}</div><span class="tone-row">${{tones}}</span><span class="tap">${{isOpen?COPY.hide:COPY.tap}}</span></button>`;
}}

function render(){{
 cards.innerHTML=batch.map((item,index)=>mode==="tones"?toneCard(item,index):blendCard(item,index)).join("");
 const allOpen=batch.length>0&&revealed.size===batch.length;
 revealButton.textContent=allOpen?COPY.hideAll:COPY.revealAll;
 modeHelp.textContent=COPY.modeHelp[mode];
 countSelect.disabled=mode==="tones";
}}

async function registerWebMcp(){{
 if(!document.modelContext?.registerTool)return;
 await document.modelContext.registerTool({{
  name:"create_private_deterministic_zhuyin_blending_cards",
  description:CONFIG.toolDescription,
  inputSchema:CONFIG.inputSchema,
  annotations:{{readOnlyHint:true,untrustedContentHint:false}},
  execute:async(input)=>{{
   const cardSet=validateInput(input);
   const result={{
    result_type:"private_deterministic_zhuyin_blending_cards",
    deterministic:true,
    curated_examples_not_complete_syllable_table:true,
    is_not_assessment:true,
    no_score_grade_rank_or_diagnosis:true,
    no_child_data_received:true,
    no_learning_outcome_claim:true,
    card_set:cardSet,
    official_sources:CONFIG.officialSources
   }};
   if(CONFIG.optionalApp)result.optional_lumibopomofo=CONFIG.optionalApp;
   return JSON.stringify(result);
  }}
 }});
}}

document.getElementById("mode-buttons").addEventListener("click",event=>{{
 const button=event.target.closest("button[data-mode]");
 if(!button)return;
 mode=button.dataset.mode;
 if(mode==="tones"){{
  count=4;
  countSelect.value="4";
 }}
 document.querySelectorAll("#mode-buttons button").forEach(item=>item.classList.toggle("on",item===button));
 makeBatch();
}});
countSelect.addEventListener("change",()=>{{count=Number(countSelect.value);makeBatch();}});
setNumberInput.addEventListener("change",()=>{{
 const next=Number(setNumberInput.value);
 if(Number.isInteger(next)&&next>={SET_NUMBER_MIN}&&next<={SET_NUMBER_MAX}){{
  setNumber=next;
  makeBatch();
 }}else{{
  setNumberInput.value=String(setNumber);
 }}
}});
document.getElementById("new-set").addEventListener("click",()=>{{
 setNumber=setNumber>={SET_NUMBER_MAX}?{SET_NUMBER_MIN}:setNumber+1;
 setNumberInput.value=String(setNumber);
 makeBatch();
}});
cards.addEventListener("click",event=>{{
 const card=event.target.closest(".practice-card");
 if(!card)return;
 const index=Number(card.dataset.index);
 revealed.has(index)?revealed.delete(index):revealed.add(index);
 render();
}});
revealButton.addEventListener("click",()=>{{
 if(revealed.size===batch.length)revealed.clear();
 else revealed=new Set(batch.map((_,index)=>index));
 render();
}});
document.getElementById("print-cards").addEventListener("click",()=>window.print());
document.getElementById("share-tool").addEventListener("click",async()=>{{
 const payload={{title:COPY.shareTitle,text:COPY.shareText,url:window.location.href}};
 if(navigator.share){{
  try{{
   await navigator.share(payload);
   status.textContent=COPY.shared;
   return;
  }}catch(error){{
   if(error&&error.name==="AbortError"){{
    status.textContent=COPY.cancelled;
    return;
   }}
  }}
 }}
 try{{
  await navigator.clipboard.writeText(window.location.href);
  status.textContent=COPY.copied;
 }}catch(error){{
  status.textContent=`${{COPY.copyFailed}} ${{window.location.href}}`;
 }}
}});
makeBatch();
registerWebMcp().catch(error=>
 console.error("WebMCP tool registration failed.",error));
</script>
</body>
</html>
"""


def _index_card(locale: str) -> str:
  t = COPY[locale]
  return (
    f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
    f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
    f'<p>{html.escape(t["index_description"])}</p></article>'
  )


def write_text_if_changed(path: Path, content: str) -> bool:
  if path.exists() and path.read_text(encoding="utf-8") == content:
    return False
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")
  return True


def _update_one_index(index: Path, locale: str) -> bool:
  if not index.exists():
    return False
  text = index.read_text(encoding="utf-8")
  card = _index_card(locale)
  existing = re.compile(
    rf'<article class="card third"(?: data-tool="{SLUG}")?>'
    rf'<h2><a href="{SLUG}\.html">.*?</article>',
    re.S,
  )
  updated = existing.sub("", text)
  marker = '<section class="wrap grid">'
  if marker not in updated:
    raise RuntimeError(f"{index} is missing its tools grid")
  updated = updated.replace(marker, marker + card, 1)
  return write_text_if_changed(index, updated)


def update_tools_indexes(pages: Path = PAGES) -> int:
  return sum(
    _update_one_index(
      pages
      / ("tools" if locale == "en" else f"{locale}/tools")
      / "index.html",
      locale,
    )
    for locale in ALT_LOCALES
  )


TARGET_ANSWER_SLUG = (
  "my-child-recognises-the-bopomofo-symbols-but-can-t-blend-them-"
  "into-syllables-how-can-i-help.html"
)
INBOUND_LINK_CLASS = "zhuyin-blending-card-inline-link"
_APP_STORE_ANCHOR = re.compile(
  r'<a\b(?=[^>]*\bhref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
  r'(?:[^"\'?#]*/)*id'
  + APP_ID
  + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
  re.IGNORECASE,
)


def insert_answer_links(pages: Path = PAGES) -> int:
  changed = 0
  for locale in ALT_LOCALES:
    directory = (
      pages / "answers"
      if locale == "en"
      else pages / locale / "answers"
    )
    path = directory / TARGET_ANSWER_SLUG
    if not path.is_file():
      continue
    text = path.read_text(encoding="utf-8")
    if INBOUND_LINK_CLASS in text:
      continue
    match = _APP_STORE_ANCHOR.search(text)
    if not match:
      continue
    link = (
      f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
      f'data-zhuyin-blending-card-link="1" href="{canonical(locale)}" '
      f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
    )
    if write_text_if_changed(
      path,
      text[: match.start()] + link + text[match.start() :],
    ):
      changed += 1
  return changed


def build(
  pages: Path = PAGES,
  app_public: bool = False,
) -> list[str]:
  outputs = []
  for locale in ALT_LOCALES:
    relative = Path("tools") / f"{SLUG}.html"
    if locale != "en":
      relative = Path(locale) / relative
    target = pages / relative
    write_text_if_changed(
      target,
      render_page(locale, app_public=app_public),
    )
    outputs.append(canonical(locale))
  update_tools_indexes(pages)
  insert_answer_links(pages)
  return outputs


def main() -> None:
  app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
  outputs = build(app_public=app_public)
  sitemap_count = write_tools_sitemap()
  for output in outputs:
    print(f"zhuyin blending cards -> {output}")
  print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
  main()
