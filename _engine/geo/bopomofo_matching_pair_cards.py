#!/usr/bin/env python3
"""Generate a nine-locale private Bopomofo matching-pair cut-card tool."""

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
SLUG = "private-bopomofo-matching-pair-cards"
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
CONTENT_DATE = "2026-07-15"

MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_STROKE_ORDER = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=1"
UNICODE_NAMES_LIST = "https://www.unicode.org/charts/nameslist/n_3100.html"
UNICODE_CHART_PDF = "https://www.unicode.org/charts/PDF/U3100.pdf"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

ALT_LOCALES = (
    "en",
    "es-ES",
    "pt-BR",
    "de-DE",
    "fr-FR",
    "ja",
    "ko",
    "zh-Hant",
    "zh-Hans",
)

# The 37 basic Mandarin Bopomofo letters: the exact consecutive Unicode code
# points U+3105 (BOPOMOFO LETTER B / ㄅ) through U+3129 (BOPOMOFO LETTER IU /
# ㄩ). Dialect letters after U+3129 are intentionally excluded.
SYMBOLS = (
    ("ㄅ", "U+3105", "BOPOMOFO LETTER B"),
    ("ㄆ", "U+3106", "BOPOMOFO LETTER P"),
    ("ㄇ", "U+3107", "BOPOMOFO LETTER M"),
    ("ㄈ", "U+3108", "BOPOMOFO LETTER F"),
    ("ㄉ", "U+3109", "BOPOMOFO LETTER D"),
    ("ㄊ", "U+310A", "BOPOMOFO LETTER T"),
    ("ㄋ", "U+310B", "BOPOMOFO LETTER N"),
    ("ㄌ", "U+310C", "BOPOMOFO LETTER L"),
    ("ㄍ", "U+310D", "BOPOMOFO LETTER G"),
    ("ㄎ", "U+310E", "BOPOMOFO LETTER K"),
    ("ㄏ", "U+310F", "BOPOMOFO LETTER H"),
    ("ㄐ", "U+3110", "BOPOMOFO LETTER J"),
    ("ㄑ", "U+3111", "BOPOMOFO LETTER Q"),
    ("ㄒ", "U+3112", "BOPOMOFO LETTER X"),
    ("ㄓ", "U+3113", "BOPOMOFO LETTER ZH"),
    ("ㄔ", "U+3114", "BOPOMOFO LETTER CH"),
    ("ㄕ", "U+3115", "BOPOMOFO LETTER SH"),
    ("ㄖ", "U+3116", "BOPOMOFO LETTER R"),
    ("ㄗ", "U+3117", "BOPOMOFO LETTER Z"),
    ("ㄘ", "U+3118", "BOPOMOFO LETTER C"),
    ("ㄙ", "U+3119", "BOPOMOFO LETTER S"),
    ("ㄚ", "U+311A", "BOPOMOFO LETTER A"),
    ("ㄛ", "U+311B", "BOPOMOFO LETTER O"),
    ("ㄜ", "U+311C", "BOPOMOFO LETTER E"),
    ("ㄝ", "U+311D", "BOPOMOFO LETTER EH"),
    ("ㄞ", "U+311E", "BOPOMOFO LETTER AI"),
    ("ㄟ", "U+311F", "BOPOMOFO LETTER EI"),
    ("ㄠ", "U+3120", "BOPOMOFO LETTER AU"),
    ("ㄡ", "U+3121", "BOPOMOFO LETTER OU"),
    ("ㄢ", "U+3122", "BOPOMOFO LETTER AN"),
    ("ㄣ", "U+3123", "BOPOMOFO LETTER EN"),
    ("ㄤ", "U+3124", "BOPOMOFO LETTER ANG"),
    ("ㄥ", "U+3125", "BOPOMOFO LETTER ENG"),
    ("ㄦ", "U+3126", "BOPOMOFO LETTER ER"),
    ("ㄧ", "U+3127", "BOPOMOFO LETTER I"),
    ("ㄨ", "U+3128", "BOPOMOFO LETTER U"),
    ("ㄩ", "U+3129", "BOPOMOFO LETTER IU"),
)
SYMBOL_VALUES = tuple(symbol for symbol, _code_point, _name in SYMBOLS)
SYMBOL_CODE_POINTS = {symbol: code_point for symbol, code_point, _name in SYMBOLS}
SYMBOL_UNICODE_NAMES = {symbol: name for symbol, _code_point, name in SYMBOLS}
CARD_SIZES = ("compact", "large")
PAIR_COUNT_MIN = 4
PAIR_COUNT_MAX = 12
SET_NUMBER_MIN = 1
SET_NUMBER_MAX = 99
DEFAULT_PAIR_COUNT = 6
DEFAULT_SET_NUMBER = 1
DEFAULT_CARD_SIZE = "compact"

# Deterministic linear congruential generator constants (the classic MSVC
# rand() recurrence). state * LCG_MULTIPLIER never exceeds roughly 4.6e14,
# far below Number.MAX_SAFE_INTEGER (2**53), so Python and JavaScript
# compute byte-identical results using only non-negative integer
# multiplication, addition, floor-division, and modulo -- no bitwise
# operators, no negative numbers, and no Math.random.
LCG_MULTIPLIER = 214013
LCG_INCREMENT = 2531011
LCG_MODULUS = 2 ** 31


def _lcg_next(state: int) -> int:
    return (state * LCG_MULTIPLIER + LCG_INCREMENT) % LCG_MODULUS


def _lcg_draw(state: int) -> int:
    return (state // 65536) % 32768


def select_symbols(pair_count: int, set_number: int) -> list[str]:
    """Return the deterministic contiguous rotation of selected symbols."""
    offset = ((set_number - 1) * pair_count) % 37
    return [SYMBOL_VALUES[(offset + k) % 37] for k in range(pair_count)]


def shuffle_order(pair_count: int, set_number: int) -> list[int]:
    """Return a deterministic Fisher-Yates shuffle of pair indices.

    The base sequence lists every pair index (0..pair_count-1) exactly
    twice. It is shuffled in place with an LCG-driven Fisher-Yates pass
    seeded purely from pair_count and set_number, so the same two inputs
    always reproduce the same card order -- never a live random shuffle.
    """
    total = pair_count * 2
    order = [index % pair_count for index in range(total)]
    state = pair_count * 10000 + set_number
    for i in range(total - 1, 0, -1):
        state = _lcg_next(state)
        j = _lcg_draw(state) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def build_cards(pair_count: int, set_number: int, card_size: str) -> dict[str, object]:
    """Reference (Python) implementation shared conceptually with SCRIPT."""
    symbols = select_symbols(pair_count, set_number)
    order = shuffle_order(pair_count, set_number)
    cards = []
    for index, pair_index in enumerate(order):
        symbol = symbols[pair_index]
        cards.append(
            {
                "card_number": index + 1,
                "pair_index": pair_index,
                "symbol": symbol,
                "code_point": SYMBOL_CODE_POINTS[symbol],
                "unicode_name": SYMBOL_UNICODE_NAMES[symbol],
                "card_size": card_size,
            }
        )
    return {
        "selected_inputs": {
            "pair_count": pair_count,
            "set_number": set_number,
            "card_size": card_size,
        },
        "selected_symbols": symbols,
        "cards": cards,
    }


COPY = {
    "en": {
        "title": (
            "Private Bopomofo Matching-Pair Cut Cards | Free Printable "
            "Zhuyin Tool"
        ),
        "description": (
            "Generate free printable Bopomofo (Zhuyin) matching-pair cut "
            "cards for a private, offline matching game — choose how many "
            "pairs and which set, then print, cut, and match identical "
            "symbols. No account, no child data, no scoring."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no account · no scoring",
        "heading": "Private Bopomofo matching-pair cut cards",
        "lead": (
            "Choose how many symbol pairs to include and which numbered "
            "set to generate, then print a deterministic sheet of cut "
            "cards for a private, offline matching game. This tool never "
            "scores, ranks, or assesses a child, and it never claims to "
            "improve memory."
        ),
        "badges": (
            "No child name, age, school, or account collected",
            "No score, grade, ranking, or memory-improvement claim",
            "Same set number always reproduces the same cards",
            "Official stroke order stays on Taiwan's MOE site",
        ),
        "planner": "Build your printable matching-pair cards",
        "planner_intro": (
            "Choose how many pairs, which set number, and a card size, "
            "then generate a printable sheet. This page never asks for "
            "your child's name, age, school, photo, handwriting, voice, "
            "or any other personal detail."
        ),
        "pair_count_label": "Number of symbol pairs (4–12)",
        "set_number_label": "Set number (1–99)",
        "card_size_label": "Card size",
        "card_size_options": {
            "compact": "Compact (more per sheet)",
            "large": "Large (easier to cut)",
        },
        "update": "Generate printable cards",
        "reset_label": "Reset to defaults",
        "invalid_input": (
            "Choose a pair count, set number, and card size within the "
            "supported ranges shown above."
        ),
        "result_count_label": "Cards generated",
        "print_label": "Print these cards",
        "reproducibility_note": (
            "The same pair count and set number always produce the same "
            "selected symbols and the same card order. Choosing a new set "
            "number rotates which symbols are covered."
        ),
        "card_label": "Card",
        "cards_region_label": "Matching-pair cut cards",
        "boundary_title": "What this tool does not do",
        "boundary_text": (
            "This tool does not assess, score, grade, rank, or diagnose a "
            "child, and it does not claim that playing this matching game "
            "improves memory or any other skill. It only turns your "
            "chosen pair count and set number into printable cut cards."
        ),
        "independence_notice": (
            "This is a free, independent web tool. It is not the Lumi "
            "Bopomofo app, and it is not a diagnostic tool, assessment, "
            "or memory-training program of any kind."
        ),
        "sources_title": "Official Bopomofo sources",
        "sources_intro": (
            "These facts and links come from Taiwan's Ministry of "
            "Education and the Unicode Consortium, not from this site."
        ),
        "source_labels": (
            "Taiwan MOE official Bopomofo handbook",
            "Taiwan MOE official Bopomofo stroke-order portal",
            "Unicode official Bopomofo names list",
            "Unicode official Bopomofo chart (PDF)",
        ),
        "moe_check_label": "Check official stroke order for these symbols",
        "moe_check_note": (
            "This tool links to the official Ministry of Education "
            "portal instead of reproducing stroke-order animations "
            "itself."
        ),
        "unicode_note": (
            "Unicode character names, such as BOPOMOFO LETTER B, are "
            "technical identifiers used to tell symbols apart; they are "
            "not pronunciation guides."
        ),
        "no_pronunciation_note": (
            "This tool does not provide pronunciation or romanization "
            "for any symbol; use official Taiwan MOE resources for that."
        ),
        "how_it_works_title": "How these cards are generated",
        "how_it_works_intro": (
            "Card selection and order are a fixed, documented algorithm "
            "run by this site, not a random shuffle or adaptive activity."
        ),
        "how_it_works_list": (
            "Pick a pair count from 4 to 12; that many of the 37 basic "
            "Bopomofo letters (ㄅ through ㄩ) are selected in a fixed "
            "rotation based on your set number.",
            "Pick a set number from 1 to 99; each set number rotates "
            "which symbols are selected, so different sets cover "
            "different parts of the 37-symbol range over time.",
            "Every selected symbol appears on exactly two cards, and the "
            "card order is deterministically arranged from your pair "
            "count and set number — never a live random shuffle.",
            "Card size only changes how big the cards print; it never "
            "changes which symbols are selected or their order.",
            "Print the cards and play offline; nothing about your "
            "session is sent anywhere or stored by this tool.",
        ),
        "instructions_title": "How to play",
        "instructions_intro": (
            "This is an offline, print-and-cut matching game."
        ),
        "instructions_list": (
            "Print the sheet of cards at full size.",
            "Cut along each card border to make individual matching-pair "
            "cut cards.",
            "Shuffle the cut cards and place them face down in rows.",
            "Take turns flipping two cards at a time, looking for two "
            "cards with the identical Bopomofo symbol.",
            "Keep matched pairs and continue until every card has been "
            "matched.",
        ),
        "webmcp_source": (
            "Chrome WebMCP imperative API preview (subject to change)"
        ),
        "webmcp_description": (
            "Build private, deterministic Bopomofo matching-pair cut "
            "cards from a pair count, set number, and card size. Never "
            "receive a child's name, age, grade, school, location, "
            "photo, handwriting, voice, answer history, score, or "
            "account; never claim the activity improves memory or "
            "assesses a child."
        ),
        "app_title": "Want an optional guided Bopomofo app?",
        "app_text": (
            "Lumi Bopomofo is optional. Its current App Store listing "
            "describes playful Zhuyin symbol, sound, and combination "
            "activities plus tracing and tone games, free to download "
            "with a one-time in-app unlock, that works offline, has no "
            "ads, no subscription, and lists Data Not Collected. Verify "
            "the current listing before deciding, since features can "
            "change. These printable cards work fully without the app."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "faq_title": "Bopomofo matching-pair card questions",
        "faq": (
            (
                "Does this tool score, rank, or diagnose my child?",
                "No. It only turns your chosen pair count and set number "
                "into printable matching-pair cut cards; it never "
                "scores, ranks, grades, or diagnoses anyone.",
            ),
            (
                "Does playing this game improve my child's memory?",
                "This tool makes no such claim. It only generates a "
                "printable matching activity; any benefit from playing "
                "is not measured or promised here.",
            ),
            (
                "Will the same set number always give the same cards?",
                "Yes. The same pair count and set number always "
                "reproduce the same selected symbols in the same card "
                "order, so you can regenerate a set you printed before.",
            ),
            (
                "Does this page collect my child's name, age, school, "
                "or any personal data?",
                "No. It only accepts a pair count, set number, and card "
                "size; nothing is sent anywhere or stored.",
            ),
            (
                "Where can I check official Bopomofo stroke order or "
                "pronunciation?",
                "Use Taiwan's Ministry of Education stroke-order portal "
                "linked on this page; this tool does not provide "
                "pronunciation, romanization, or stroke-order animations "
                "itself.",
            ),
        ),
        "footer": (
            "Private set numbers only · no child data · no scoring · no "
            "memory-improvement claim"
        ),
        "index_title": "Private Bopomofo Matching-Pair Cut Cards",
        "index_description": (
            "Generate free printable Bopomofo matching-pair cut cards "
            "from a pair count and set number — no account, no child "
            "data, no scoring."
        ),
        "inline_link_label": (
            "Free Bopomofo matching-pair cut card generator (no scoring)"
        ),
    },
    "es-ES": {
        "title": (
            "Tarjetas privadas de parejas Bopomofo para recortar | "
            "Herramienta Zhuyin gratis para imprimir"
        ),
        "description": (
            "Genera tarjetas privadas para recortar en parejas de "
            "símbolos Bopomofo (Zhuyin), gratis para imprimir — elige "
            "cuántos pares y qué número de conjunto, luego imprime, "
            "recorta y empareja los símbolos idénticos sin conexión. Sin "
            "cuenta, sin datos del menor, sin puntuación."
        ),
        "tools": "Herramientas gratis",
        "switch": "English",
        "eyebrow": "Gratis · sin cuenta · sin puntuación",
        "heading": "Tarjetas privadas de parejas Bopomofo para recortar",
        "lead": (
            "Elige cuántos pares de símbolos incluir y qué número de "
            "conjunto generar, luego imprime una hoja determinista de "
            "tarjetas para recortar y jugar a emparejar sin conexión. "
            "Esta herramienta nunca puntúa, clasifica ni evalúa a un "
            "menor, y nunca afirma mejorar la memoria."
        ),
        "badges": (
            "No se recogen nombre, edad, colegio ni cuenta del menor",
            "Sin puntuación, nota, clasificación ni afirmación de mejora "
            "de memoria",
            "El mismo número de conjunto siempre reproduce las mismas "
            "tarjetas",
            "El trazo oficial permanece en el sitio del MOE de Taiwán",
        ),
        "planner": "Crea tus tarjetas de parejas para imprimir",
        "planner_intro": (
            "Elige cuántos pares, qué número de conjunto y un tamaño de "
            "tarjeta, luego genera una hoja para imprimir. Esta página "
            "nunca pide el nombre, edad, colegio, foto, escritura, voz "
            "ni ningún otro dato personal del menor."
        ),
        "pair_count_label": "Número de parejas de símbolos (4-12)",
        "set_number_label": "Número de conjunto (1-99)",
        "card_size_label": "Tamaño de tarjeta",
        "card_size_options": {
            "compact": "Compacto (más por hoja)",
            "large": "Grande (más fácil de recortar)",
        },
        "update": "Generar tarjetas para imprimir",
        "reset_label": "Restablecer valores",
        "invalid_input": (
            "Elige un número de parejas, un número de conjunto y un "
            "tamaño de tarjeta dentro de los rangos admitidos indicados "
            "arriba."
        ),
        "result_count_label": "Tarjetas generadas",
        "print_label": "Imprimir estas tarjetas",
        "reproducibility_note": (
            "El mismo número de parejas y número de conjunto siempre "
            "producen los mismos símbolos seleccionados y el mismo orden "
            "de tarjetas. Elegir un nuevo número de conjunto rota los "
            "símbolos cubiertos."
        ),
        "card_label": "Tarjeta",
        "cards_region_label": "Tarjetas de parejas para recortar",
        "boundary_title": "Lo que esta herramienta no hace",
        "boundary_text": (
            "Esta herramienta no evalúa, puntúa, califica, clasifica ni "
            "diagnostica a un menor, y no afirma que jugar a este juego "
            "de memoria mejore la memoria ni ninguna otra habilidad. "
            "Solo convierte el número de parejas y el número de conjunto "
            "que elijas en tarjetas para recortar."
        ),
        "independence_notice": (
            "Esta es una herramienta web gratuita e independiente. No es "
            "la app Lumi Bopomofo, y no es una herramienta de "
            "diagnóstico, evaluación ni entrenamiento de memoria de "
            "ningún tipo."
        ),
        "sources_title": "Fuentes oficiales de Bopomofo",
        "sources_intro": (
            "Estos datos y enlaces provienen del Ministerio de "
            "Educación de Taiwán y del Consorcio Unicode, no de este "
            "sitio."
        ),
        "source_labels": (
            "Manual oficial de Bopomofo del MOE de Taiwán",
            "Portal oficial de trazo Bopomofo del MOE de Taiwán",
            "Lista oficial de nombres Bopomofo de Unicode",
            "Gráfico oficial Bopomofo de Unicode (PDF)",
        ),
        "moe_check_label": "Consulta el trazo oficial de estos símbolos",
        "moe_check_note": (
            "Esta herramienta enlaza al portal oficial del Ministerio de "
            "Educación en lugar de reproducir animaciones de trazo por "
            "sí misma."
        ),
        "unicode_note": (
            "Los nombres de caracteres Unicode, como BOPOMOFO LETTER B, "
            "son identificadores técnicos para distinguir símbolos; no "
            "son guías de pronunciación."
        ),
        "no_pronunciation_note": (
            "Esta herramienta no ofrece pronunciación ni romanización de "
            "ningún símbolo; usa los recursos oficiales del MOE de "
            "Taiwán para eso."
        ),
        "how_it_works_title": "Cómo se generan estas tarjetas",
        "how_it_works_intro": (
            "La selección y el orden de las tarjetas son un algoritmo "
            "fijo y documentado que ejecuta este sitio, no una mezcla "
            "aleatoria ni una actividad adaptativa."
        ),
        "how_it_works_list": (
            "Elige un número de parejas de 4 a 12; se seleccionan esas "
            "letras Bopomofo básicas (de las 37, de ㄅ a ㄩ) en una "
            "rotación fija según tu número de conjunto.",
            "Elige un número de conjunto de 1 a 99; cada número de "
            "conjunto rota qué símbolos se seleccionan, así que "
            "distintos conjuntos cubren distintas partes del rango de "
            "37 símbolos con el tiempo.",
            "Cada símbolo seleccionado aparece en exactamente dos "
            "tarjetas, y el orden de las tarjetas se organiza de forma "
            "determinista a partir de tu número de parejas y de "
            "conjunto — nunca una mezcla aleatoria en vivo.",
            "El tamaño de tarjeta solo cambia el tamaño de impresión; "
            "nunca cambia qué símbolos se seleccionan ni su orden.",
            "Imprime las tarjetas y juega sin conexión; nada de tu "
            "sesión se envía a ningún sitio ni se guarda en esta "
            "herramienta.",
        ),
        "instructions_title": "Cómo jugar",
        "instructions_intro": (
            "Este es un juego de emparejar sin conexión, para imprimir "
            "y recortar."
        ),
        "instructions_list": (
            "Imprime la hoja de tarjetas a tamaño completo.",
            "Recorta por el borde de cada tarjeta para obtener tarjetas "
            "individuales de parejas.",
            "Mezcla las tarjetas recortadas y colócalas boca abajo en "
            "filas.",
            "Túrnense para voltear dos tarjetas a la vez, buscando dos "
            "con el mismo símbolo Bopomofo.",
            "Guarden las parejas encontradas y continúen hasta emparejar "
            "todas las tarjetas.",
        ),
        "webmcp_source": (
            "Vista previa de la API imperativa Chrome WebMCP (sujeta a "
            "cambios)"
        ),
        "webmcp_description": (
            "Genera tarjetas privadas y deterministas de parejas "
            "Bopomofo para recortar a partir de un número de parejas, "
            "un número de conjunto y un tamaño de tarjeta. Nunca recibe "
            "el nombre, edad, curso, colegio, ubicación, foto, "
            "escritura, voz, historial de respuestas, puntuación ni "
            "cuenta de un menor; nunca afirma que la actividad mejora la "
            "memoria ni evalúa a un menor."
        ),
        "app_title": "¿Quieres una app guiada de Bopomofo opcional?",
        "app_text": (
            "Lumi Bopomofo es opcional. Su ficha actual en la App Store "
            "describe actividades lúdicas de símbolos, sonidos y "
            "combinaciones Zhuyin, además de juegos de trazo y tono, "
            "gratis para descargar con un desbloqueo único dentro de la "
            "app, que funciona sin conexión, sin anuncios, sin "
            "suscripción, y indica que no se recopilan datos. Verifica "
            "la ficha actual antes de decidir, ya que las funciones "
            "pueden cambiar. Estas tarjetas para imprimir funcionan por "
            "completo sin la app."
        ),
        "app_cta": "Ver Lumi Bopomofo en la App Store",
        "faq_title": "Preguntas sobre las tarjetas de parejas Bopomofo",
        "faq": (
            (
                "¿Esta herramienta puntúa, clasifica o diagnostica a mi "
                "hijo?",
                "No. Solo convierte el número de parejas y de conjunto "
                "que elijas en tarjetas de parejas para recortar; nunca "
                "puntúa, clasifica, califica ni diagnostica a nadie.",
            ),
            (
                "¿Jugar a este juego mejora la memoria de mi hijo?",
                "Esta herramienta no hace esa afirmación. Solo genera "
                "una actividad de emparejar para imprimir; cualquier "
                "beneficio de jugar no se mide ni se promete aquí.",
            ),
            (
                "¿El mismo número de conjunto siempre da las mismas "
                "tarjetas?",
                "Sí. El mismo número de parejas y de conjunto siempre "
                "reproducen los mismos símbolos seleccionados en el "
                "mismo orden de tarjetas, así que puedes regenerar un "
                "conjunto que imprimiste antes.",
            ),
            (
                "¿Esta página recoge el nombre, edad, colegio o algún "
                "dato personal de mi hijo?",
                "No. Solo acepta un número de parejas, un número de "
                "conjunto y un tamaño de tarjeta; nada se envía a ningún "
                "sitio ni se guarda.",
            ),
            (
                "¿Dónde puedo consultar el trazo oficial o la "
                "pronunciación de Bopomofo?",
                "Usa el portal oficial de trazo del Ministerio de "
                "Educación de Taiwán enlazado en esta página; esta "
                "herramienta no ofrece pronunciación, romanización ni "
                "animaciones de trazo.",
            ),
        ),
        "footer": (
            "Solo números de conjunto privados · sin datos del menor · "
            "sin puntuación · sin afirmación de mejora de memoria"
        ),
        "index_title": (
            "Tarjetas privadas de parejas Bopomofo para recortar"
        ),
        "index_description": (
            "Genera tarjetas privadas de parejas Bopomofo para "
            "recortar, gratis para imprimir, a partir de un número de "
            "parejas y de conjunto — sin cuenta, sin datos del menor, "
            "sin puntuación."
        ),
        "inline_link_label": (
            "Generador gratis de tarjetas de parejas Bopomofo para "
            "recortar (sin puntuación)"
        ),
    },
    "pt-BR": {
        "title": (
            "Cartas privadas de pares Bopomofo para recortar | "
            "Ferramenta Zhuyin gratuita para imprimir"
        ),
        "description": (
            "Gere cartas privadas de pares de símbolos Bopomofo (Zhuyin) "
            "para recortar, gratuitas para imprimir — escolha quantos "
            "pares e qual número de conjunto, depois imprima, recorte e "
            "combine os símbolos idênticos offline. Sem conta, sem dados "
            "da criança, sem pontuação."
        ),
        "tools": "Ferramentas gratuitas",
        "switch": "English",
        "eyebrow": "Grátis · sem conta · sem pontuação",
        "heading": "Cartas privadas de pares Bopomofo para recortar",
        "lead": (
            "Escolha quantos pares de símbolos incluir e qual número de "
            "conjunto gerar, depois imprima uma folha determinística de "
            "cartas para recortar e jogar o jogo da memória offline. "
            "Esta ferramenta nunca pontua, classifica ou avalia uma "
            "criança, e nunca afirma melhorar a memória."
        ),
        "badges": (
            "Nenhum nome, idade, escola ou conta da criança é coletado",
            "Sem pontuação, nota, classificação ou alegação de melhora "
            "de memória",
            "O mesmo número de conjunto sempre reproduz as mesmas "
            "cartas",
            "O traçado oficial permanece no site do MOE de Taiwan",
        ),
        "planner": "Monte suas cartas de pares para imprimir",
        "planner_intro": (
            "Escolha quantos pares, qual número de conjunto e um "
            "tamanho de carta, depois gere uma folha para imprimir. "
            "Esta página nunca pede nome, idade, escola, foto, "
            "escrita, voz nem qualquer outro dado pessoal da criança."
        ),
        "pair_count_label": "Número de pares de símbolos (4–12)",
        "set_number_label": "Número do conjunto (1–99)",
        "card_size_label": "Tamanho da carta",
        "card_size_options": {
            "compact": "Compacto (mais por folha)",
            "large": "Grande (mais fácil de recortar)",
        },
        "update": "Gerar cartas para imprimir",
        "reset_label": "Restaurar padrões",
        "invalid_input": (
            "Escolha um número de pares, um número de conjunto e um "
            "tamanho de carta dentro dos intervalos suportados acima."
        ),
        "result_count_label": "Cartas geradas",
        "print_label": "Imprimir estas cartas",
        "reproducibility_note": (
            "O mesmo número de pares e número de conjunto sempre "
            "produzem os mesmos símbolos selecionados e a mesma ordem "
            "de cartas. Escolher um novo número de conjunto roda os "
            "símbolos cobertos."
        ),
        "card_label": "Carta",
        "cards_region_label": "Cartas de pares para recortar",
        "boundary_title": "O que esta ferramenta não faz",
        "boundary_text": (
            "Esta ferramenta não avalia, pontua, classifica ou "
            "diagnostica uma criança, e não afirma que jogar este jogo "
            "da memória melhora a memória ou qualquer outra habilidade. "
            "Ela apenas transforma o número de pares e de conjunto que "
            "você escolher em cartas para recortar."
        ),
        "independence_notice": (
            "Esta é uma ferramenta web gratuita e independente. Não é o "
            "app Lumi Bopomofo, e não é uma ferramenta de diagnóstico, "
            "avaliação ou treinamento de memória de nenhum tipo."
        ),
        "sources_title": "Fontes oficiais de Bopomofo",
        "sources_intro": (
            "Estes dados e links vêm do Ministério da Educação de "
            "Taiwan e do Unicode Consortium, não deste site."
        ),
        "source_labels": (
            "Manual oficial de Bopomofo do Ministério da Educação de Taiwan",
            "Portal oficial de traçado Bopomofo do MOE de Taiwan",
            "Lista oficial de nomes Bopomofo da Unicode",
            "Gráfico oficial Bopomofo da Unicode (PDF)",
        ),
        "moe_check_label": "Confira o traçado oficial destes símbolos",
        "moe_check_note": (
            "Esta ferramenta faz link para o portal oficial do "
            "Ministério da Educação em vez de reproduzir animações de "
            "traçado por conta própria."
        ),
        "unicode_note": (
            "Os nomes de caracteres Unicode, como BOPOMOFO LETTER B, "
            "são identificadores técnicos para diferenciar símbolos; "
            "não são guias de pronúncia."
        ),
        "no_pronunciation_note": (
            "Esta ferramenta não oferece pronúncia nem romanização de "
            "nenhum símbolo; use os recursos oficiais do MOE de Taiwan "
            "para isso."
        ),
        "how_it_works_title": "Como estas cartas são geradas",
        "how_it_works_intro": (
            "A seleção e a ordem das cartas seguem um algoritmo fixo e "
            "documentado executado por este site, não um sorteio "
            "aleatório nem uma atividade adaptativa."
        ),
        "how_it_works_list": (
            "Escolha um número de pares de 4 a 12; essa quantidade das "
            "37 letras básicas de Bopomofo (de ㄅ a ㄩ) é selecionada em "
            "uma rotação fixa com base no seu número de conjunto.",
            "Escolha um número de conjunto de 1 a 99; cada número de "
            "conjunto roda quais símbolos são selecionados, então "
            "conjuntos diferentes cobrem partes diferentes do intervalo "
            "de 37 símbolos ao longo do tempo.",
            "Cada símbolo selecionado aparece em exatamente duas "
            "cartas, e a ordem das cartas é organizada de forma "
            "determinística a partir do seu número de pares e de "
            "conjunto — nunca um sorteio aleatório ao vivo.",
            "O tamanho da carta só muda o tamanho de impressão; nunca "
            "muda quais símbolos são selecionados nem sua ordem.",
            "Imprima as cartas e jogue offline; nada da sua sessão é "
            "enviado a lugar nenhum nem armazenado por esta "
            "ferramenta.",
        ),
        "instructions_title": "Como jogar",
        "instructions_intro": (
            "Este é um jogo da memória offline, para imprimir e "
            "recortar."
        ),
        "instructions_list": (
            "Imprima a folha de cartas em tamanho real.",
            "Recorte pela borda de cada carta para obter cartas "
            "individuais de pares.",
            "Embaralhe as cartas recortadas e coloque-as viradas para "
            "baixo em fileiras.",
            "Alternem virando duas cartas por vez, procurando duas com "
            "o mesmo símbolo Bopomofo.",
            "Guardem os pares encontrados e continuem até combinar "
            "todas as cartas.",
        ),
        "webmcp_source": (
            "Prévia da API imperativa Chrome WebMCP (sujeita a "
            "mudanças)"
        ),
        "webmcp_description": (
            "Gera cartas privadas e determinísticas de pares Bopomofo "
            "para recortar a partir de um número de pares, um número de "
            "conjunto e um tamanho de carta. Nunca recebe nome, idade, "
            "série, escola, localização, foto, escrita, voz, histórico "
            "de respostas, pontuação ou conta de uma criança; nunca "
            "afirma que a atividade melhora a memória nem avalia uma "
            "criança."
        ),
        "app_title": "Quer um app guiado opcional de Bopomofo?",
        "app_text": (
            "Lumi Bopomofo é opcional. Sua ficha atual na App Store "
            "descreve atividades lúdicas de símbolos, sons e "
            "combinações Zhuyin, além de jogos de traçado e tom, "
            "gratuito para baixar com um desbloqueio único dentro do "
            "app, que funciona offline, sem anúncios, sem assinatura, e "
            "indica que dados não são coletados. Verifique a ficha "
            "atual antes de decidir, pois os recursos podem mudar. "
            "Estas cartas para imprimir funcionam totalmente sem o "
            "app."
        ),
        "app_cta": "Ver Lumi Bopomofo na App Store",
        "faq_title": "Perguntas sobre as cartas de pares Bopomofo",
        "faq": (
            (
                "Esta ferramenta pontua, classifica ou diagnostica meu "
                "filho?",
                "Não. Ela apenas transforma o número de pares e de "
                "conjunto que você escolher em cartas de pares para "
                "recortar; nunca pontua, classifica ou diagnostica "
                "ninguém.",
            ),
            (
                "Jogar este jogo melhora a memória do meu filho?",
                "Esta ferramenta não faz essa afirmação. Ela apenas "
                "gera uma atividade de combinação para imprimir; "
                "qualquer benefício de jogar não é medido nem "
                "prometido aqui.",
            ),
            (
                "O mesmo número de conjunto sempre gera as mesmas "
                "cartas?",
                "Sim. O mesmo número de pares e de conjunto sempre "
                "reproduzem os mesmos símbolos selecionados na mesma "
                "ordem de cartas, então você pode regerar um conjunto "
                "que imprimiu antes.",
            ),
            (
                "Esta página coleta nome, idade, escola ou algum dado "
                "pessoal do meu filho?",
                "Não. Ela só aceita um número de pares, um número de "
                "conjunto e um tamanho de carta; nada é enviado a "
                "lugar nenhum nem armazenado.",
            ),
            (
                "Onde posso conferir o traçado oficial ou a "
                "pronúncia do Bopomofo?",
                "Use o portal oficial de traçado do Ministério da "
                "Educação de Taiwan linkado nesta página; esta "
                "ferramenta não oferece pronúncia, romanização nem "
                "animações de traçado.",
            ),
        ),
        "footer": (
            "Apenas números de conjunto privados · sem dados da "
            "criança · sem pontuação · sem alegação de melhora de "
            "memória"
        ),
        "index_title": "Cartas privadas de pares Bopomofo para recortar",
        "index_description": (
            "Gere cartas privadas de pares Bopomofo para recortar, "
            "gratuitas para imprimir, a partir de um número de pares e "
            "de conjunto — sem conta, sem dados da criança, sem "
            "pontuação."
        ),
        "inline_link_label": (
            "Gerador gratuito de cartas de pares Bopomofo para recortar "
            "(sem pontuação)"
        ),
    },
    "de-DE": {
        "title": (
            "Private Bopomofo Karten für Paarzuordnung zum Ausschneiden "
            "| Kostenloses Zhuyin-Tool zum Drucken"
        ),
        "description": (
            "Erstelle kostenlose, ausdruckbare Bopomofo-Zhuyin-"
            "Karten für ein privates Memory-Spiel zum Ausschneiden — "
            "wähle Paaranzahl und Set-Nummer, dann drucken, ausschneiden "
            "und identische Symbole offline zuordnen. Kein Konto, keine "
            "Kinddaten, keine Bewertung."
        ),
        "tools": "Kostenlose Tools",
        "switch": "English",
        "eyebrow": "Kostenlos · ohne Konto · ohne Bewertung",
        "heading": "Private Bopomofo Karten für Paarzuordnung",
        "lead": (
            "Wähle, wie viele Symbolpaare enthalten sein sollen und "
            "welche Set-Nummer erzeugt werden soll, und drucke dann ein "
            "deterministisches Blatt mit Karten zum Ausschneiden für ein "
            "privates Memory-Spiel offline. Dieses Tool bewertet, "
            "rankt oder beurteilt niemals ein Kind, und es behauptet "
            "nie, das Gedächtnis zu verbessern."
        ),
        "badges": (
            "Kein Name, Alter, Schule oder Konto des Kindes erfasst",
            "Keine Note, Bewertung, Rangfolge oder "
            "Gedächtnisverbesserungs-Behauptung",
            "Dieselbe Set-Nummer erzeugt immer dieselben Karten",
            "Offizielle Strichfolge bleibt auf der Taiwan-MOE-Seite",
        ),
        "planner": "Erstelle deine druckbaren Paarkarten",
        "planner_intro": (
            "Wähle Paaranzahl, Set-Nummer und Kartengröße, dann "
            "erzeuge ein druckbares Blatt. Diese Seite fragt nie nach "
            "Name, Alter, Schule, Foto, Handschrift, Stimme oder "
            "sonstigen persönlichen Angaben des Kindes."
        ),
        "pair_count_label": "Anzahl der Symbolpaare (4–12)",
        "set_number_label": "Set-Nummer (1–99)",
        "card_size_label": "Kartengröße",
        "card_size_options": {
            "compact": "Kompakt (mehr pro Blatt)",
            "large": "Groß (leichter auszuschneiden)",
        },
        "update": "Druckbare Karten erzeugen",
        "reset_label": "Auf Standard zurücksetzen",
        "invalid_input": (
            "Wähle Paaranzahl, Set-Nummer und Kartengröße innerhalb der "
            "oben gezeigten unterstützten Bereiche."
        ),
        "result_count_label": "Erzeugte Karten",
        "print_label": "Diese Karten drucken",
        "reproducibility_note": (
            "Dieselbe Paaranzahl und Set-Nummer erzeugen immer "
            "dieselben ausgewählten Symbole und dieselbe Kartenreihen"
            "folge. Eine neue Set-Nummer rotiert die abgedeckten "
            "Symbole."
        ),
        "card_label": "Karte",
        "cards_region_label": "Karten für Paarzuordnung zum Ausschneiden",
        "boundary_title": "Was dieses Tool nicht tut",
        "boundary_text": (
            "Dieses Tool beurteilt, bewertet, benotet oder rankt kein "
            "Kind, und es behauptet nicht, dass dieses Memory-Spiel das "
            "Gedächtnis oder eine andere Fähigkeit verbessert. Es "
            "wandelt lediglich deine gewählte Paaranzahl und Set-Nummer "
            "in druckbare Ausschneidekarten um."
        ),
        "independence_notice": (
            "Dies ist ein kostenloses, unabhängiges Web-Tool. Es ist "
            "nicht die Lumi-Bopomofo-App und kein Diagnose-, "
            "Bewertungs- oder Gedächtnistraining-Tool jeglicher Art."
        ),
        "sources_title": "Offizielle Bopomofo-Quellen",
        "sources_intro": (
            "Diese Fakten und Links stammen vom taiwanischen "
            "Bildungsministerium und dem Unicode-Konsortium, nicht von "
            "dieser Seite."
        ),
        "source_labels": (
            "Offizielles Bopomofo-Handbuch des taiwanischen Bildungsministeriums",
            "Offizielles Taiwan-MOE-Strichfolge-Portal für Bopomofo",
            "Offizielle Unicode-Namensliste für Bopomofo",
            "Offizielle Unicode-Bopomofo-Tabelle (PDF)",
        ),
        "moe_check_label": "Offizielle Strichfolge dieser Symbole prüfen",
        "moe_check_note": (
            "Dieses Tool verlinkt auf das offizielle Portal des "
            "Bildungsministeriums, statt Strichfolge-Animationen selbst "
            "nachzubilden."
        ),
        "unicode_note": (
            "Unicode-Zeichennamen wie BOPOMOFO LETTER B sind technische "
            "Bezeichner zur Unterscheidung von Symbolen; sie sind keine "
            "Aussprachehilfen."
        ),
        "no_pronunciation_note": (
            "Dieses Tool bietet keine Aussprache oder Umschrift für "
            "irgendein Symbol; nutze dafür offizielle Taiwan-MOE-"
            "Ressourcen."
        ),
        "how_it_works_title": "Wie diese Karten erzeugt werden",
        "how_it_works_intro": (
            "Auswahl und Reihenfolge der Karten folgen einem festen, "
            "dokumentierten Algorithmus dieser Seite, kein Zufalls"
            "mischen und keine adaptive Aktivität."
        ),
        "how_it_works_list": (
            "Wähle eine Paaranzahl von 4 bis 12; entsprechend viele der "
            "37 Bopomofo-Grundbuchstaben (ㄅ bis ㄩ) werden in fester "
            "Rotation basierend auf deiner Set-Nummer ausgewählt.",
            "Wähle eine Set-Nummer von 1 bis 99; jede Set-Nummer "
            "rotiert, welche Symbole ausgewählt werden, sodass "
            "verschiedene Sets über die Zeit verschiedene Teile des "
            "37-Symbol-Bereichs abdecken.",
            "Jedes ausgewählte Symbol erscheint auf genau zwei Karten, "
            "und die Kartenreihenfolge wird deterministisch aus deiner "
            "Paaranzahl und Set-Nummer bestimmt — nie ein "
            "Live-Zufallsmischen.",
            "Die Kartengröße ändert nur die Druckgröße; sie ändert nie, "
            "welche Symbole ausgewählt werden oder ihre Reihenfolge.",
            "Drucke die Karten und spiele offline; nichts von deiner "
            "Sitzung wird irgendwohin gesendet oder von diesem Tool "
            "gespeichert.",
        ),
        "instructions_title": "So wird gespielt",
        "instructions_intro": (
            "Dies ist ein Offline-Memory-Spiel zum Drucken und "
            "Ausschneiden."
        ),
        "instructions_list": (
            "Drucke das Kartenblatt in Originalgröße.",
            "Schneide jede Karte am Rand aus, um einzelne "
            "Paarzuordnungs-Karten zu erhalten.",
            "Mische die ausgeschnittenen Karten und lege sie verdeckt "
            "in Reihen aus.",
            "Deckt abwechselnd je zwei Karten auf und sucht zwei mit "
            "demselben Bopomofo-Symbol.",
            "Behaltet gefundene Paare und macht weiter, bis alle Karten "
            "zugeordnet sind.",
        ),
        "webmcp_source": (
            "Vorschau der Chrome-WebMCP-Imperative-API (kann sich "
            "ändern)"
        ),
        "webmcp_description": (
            "Erzeugt private, deterministische Bopomofo-Paarzuordnungs"
            "karten zum Ausschneiden aus Paaranzahl, Set-Nummer und "
            "Kartengröße. Erhält niemals Name, Alter, Klasse, Schule, "
            "Standort, Foto, Handschrift, Stimme, Antwortverlauf, "
            "Bewertung oder Konto eines Kindes; behauptet nie, dass die "
            "Aktivität das Gedächtnis verbessert oder ein Kind "
            "beurteilt."
        ),
        "app_title": "Eine optionale geführte Bopomofo-App gewünscht?",
        "app_text": (
            "Lumi Bopomofo ist optional. Der aktuelle App-Store-"
            "Eintrag beschreibt spielerische Zhuyin-Symbol-, Klang- und "
            "Kombinationsaktivitäten sowie Nachzeichnen- und "
            "Tonspiele, kostenlos zum Herunterladen mit einmaligem "
            "In-App-Freischalten, funktioniert offline, ohne Werbung, "
            "ohne Abo, und gibt an, dass keine Daten erhoben werden. "
            "Prüfe den aktuellen Eintrag vor einer Entscheidung, da "
            "sich Funktionen ändern können. Diese Druckkarten "
            "funktionieren vollständig ohne die App."
        ),
        "app_cta": "Lumi Bopomofo im App Store ansehen",
        "faq_title": "Fragen zu den Bopomofo-Paarzuordnungskarten",
        "faq": (
            (
                "Bewertet, rankt oder diagnostiziert dieses Tool mein "
                "Kind?",
                "Nein. Es wandelt nur deine gewählte Paaranzahl und "
                "Set-Nummer in druckbare Paarzuordnungskarten um; es "
                "bewertet, rankt, benotet oder diagnostiziert niemals "
                "jemanden.",
            ),
            (
                "Verbessert dieses Spiel das Gedächtnis meines Kindes?",
                "Dieses Tool stellt diese Behauptung nicht auf. Es "
                "erzeugt nur eine druckbare Zuordnungsaktivität; ein "
                "etwaiger Nutzen wird hier weder gemessen noch "
                "versprochen.",
            ),
            (
                "Ergibt dieselbe Set-Nummer immer dieselben Karten?",
                "Ja. Dieselbe Paaranzahl und Set-Nummer erzeugen immer "
                "dieselben ausgewählten Symbole in derselben "
                "Kartenreihenfolge, sodass du ein zuvor gedrucktes Set "
                "erneut erzeugen kannst.",
            ),
            (
                "Erfasst diese Seite Name, Alter, Schule oder "
                "persönliche Daten meines Kindes?",
                "Nein. Sie akzeptiert nur Paaranzahl, Set-Nummer und "
                "Kartengröße; nichts wird irgendwohin gesendet oder "
                "gespeichert.",
            ),
            (
                "Wo kann ich offizielle Bopomofo-Strichfolge oder "
                "-Aussprache prüfen?",
                "Nutze das auf dieser Seite verlinkte offizielle "
                "Strichfolge-Portal des taiwanischen Bildungs"
                "ministeriums; dieses Tool bietet keine Aussprache, "
                "Umschrift oder Strichfolge-Animationen.",
            ),
        ),
        "footer": (
            "Nur private Set-Nummern · keine Kinddaten · keine "
            "Bewertung · keine Gedächtnisverbesserungs-Behauptung"
        ),
        "index_title": (
            "Private Bopomofo Karten für Paarzuordnung zum Ausschneiden"
        ),
        "index_description": (
            "Erzeuge kostenlose, druckbare private Bopomofo-"
            "Paarzuordnungskarten aus Paaranzahl und Set-Nummer — ohne "
            "Konto, ohne Kinddaten, ohne Bewertung."
        ),
        "inline_link_label": (
            "Kostenloser Generator für Bopomofo-Paarzuordnungskarten "
            "(ohne Bewertung)"
        ),
    },
    "fr-FR": {
        "title": (
            "Cartes privées de paires Bopomofo à découper | Outil "
            "Zhuyin gratuit à imprimer"
        ),
        "description": (
            "Génère des cartes privées de paires de symboles Bopomofo "
            "(Zhuyin) à découper, gratuites à imprimer — choisis le "
            "nombre de paires et le numéro de série, puis imprime, "
            "découpe et associe les symboles identiques hors ligne. "
            "Sans compte, sans donnée sur l'enfant, sans notation."
        ),
        "tools": "Outils gratuits",
        "switch": "English",
        "eyebrow": "Gratuit · sans compte · sans notation",
        "heading": "Cartes privées de paires Bopomofo à découper",
        "lead": (
            "Choisis combien de paires de symboles inclure et quel "
            "numéro de série générer, puis imprime une feuille "
            "déterministe de cartes à découper pour un jeu de mémoire "
            "privé hors ligne. Cet outil ne note, ne classe ni "
            "n'évalue jamais un enfant, et n'affirme jamais d'améliorer "
            "la mémoire."
        ),
        "badges": (
            "Aucun nom, âge, école ou compte d'enfant collecté",
            "Aucune note, classement ou affirmation d'amélioration de "
            "la mémoire",
            "Le même numéro de série reproduit toujours les mêmes "
            "cartes",
            "Le tracé officiel reste sur le site du MOE de Taïwan",
        ),
        "planner": "Crée tes cartes de paires à imprimer",
        "planner_intro": (
            "Choisis le nombre de paires, le numéro de série et une "
            "taille de carte, puis génère une feuille à imprimer. "
            "Cette page ne demande jamais le nom, l'âge, l'école, la "
            "photo, l'écriture, la voix ni aucune autre donnée "
            "personnelle de l'enfant."
        ),
        "pair_count_label": "Nombre de paires de symboles (4-12)",
        "set_number_label": "Numéro de série (1-99)",
        "card_size_label": "Taille de carte",
        "card_size_options": {
            "compact": "Compacte (plus par feuille)",
            "large": "Grande (plus facile à découper)",
        },
        "update": "Générer les cartes à imprimer",
        "reset_label": "Réinitialiser",
        "invalid_input": (
            "Choisis un nombre de paires, un numéro de série et une "
            "taille de carte dans les plages prises en charge "
            "ci-dessus."
        ),
        "result_count_label": "Cartes générées",
        "print_label": "Imprimer ces cartes",
        "reproducibility_note": (
            "Le même nombre de paires et numéro de série produisent "
            "toujours les mêmes symboles sélectionnés et le même ordre "
            "de cartes. Choisir un nouveau numéro de série fait tourner "
            "les symboles couverts."
        ),
        "card_label": "Carte",
        "cards_region_label": "Cartes de paires à découper",
        "boundary_title": "Ce que cet outil ne fait pas",
        "boundary_text": (
            "Cet outil n'évalue, ne note, ne classe ni ne diagnostique "
            "jamais un enfant, et n'affirme pas que jouer à ce jeu de "
            "mémoire améliore la mémoire ou toute autre compétence. Il "
            "transforme seulement le nombre de paires et le numéro de "
            "série choisis en cartes à découper."
        ),
        "independence_notice": (
            "Ceci est un outil web gratuit et indépendant. Ce n'est pas "
            "l'application Lumi Bopomofo, et ce n'est pas un outil de "
            "diagnostic, d'évaluation ou d'entraînement de la mémoire "
            "d'aucune sorte."
        ),
        "sources_title": "Sources officielles sur le Bopomofo",
        "sources_intro": (
            "Ces faits et liens proviennent du ministère de "
            "l'Éducation de Taïwan et du Consortium Unicode, pas de ce "
            "site."
        ),
        "source_labels": (
            "Manuel officiel du Bopomofo du ministère de l’Éducation de Taïwan",
            "Portail officiel du tracé Bopomofo du MOE de Taïwan",
            "Liste officielle des noms Bopomofo d'Unicode",
            "Planche officielle Bopomofo d'Unicode (PDF)",
        ),
        "moe_check_label": "Vérifier le tracé officiel de ces symboles",
        "moe_check_note": (
            "Cet outil renvoie vers le portail officiel du ministère "
            "de l'Éducation plutôt que de reproduire lui-même des "
            "animations de tracé."
        ),
        "unicode_note": (
            "Les noms de caractères Unicode, comme BOPOMOFO LETTER B, "
            "sont des identifiants techniques pour distinguer les "
            "symboles ; ce ne sont pas des guides de prononciation."
        ),
        "no_pronunciation_note": (
            "Cet outil ne fournit ni prononciation ni romanisation "
            "pour aucun symbole ; utilise les ressources officielles "
            "du MOE de Taïwan pour cela."
        ),
        "how_it_works_title": "Comment ces cartes sont générées",
        "how_it_works_intro": (
            "La sélection et l'ordre des cartes suivent un algorithme "
            "fixe et documenté exécuté par ce site, pas un mélange "
            "aléatoire ni une activité adaptative."
        ),
        "how_it_works_list": (
            "Choisis un nombre de paires de 4 à 12 ; ce nombre parmi "
            "les 37 lettres Bopomofo de base (de ㄅ à ㄩ) est "
            "sélectionné selon une rotation fixe basée sur ton numéro "
            "de série.",
            "Choisis un numéro de série de 1 à 99 ; chaque numéro de "
            "série fait tourner les symboles sélectionnés, donc "
            "différentes séries couvrent différentes parties de la "
            "plage de 37 symboles au fil du temps.",
            "Chaque symbole sélectionné apparaît sur exactement deux "
            "cartes, et l'ordre des cartes est organisé de manière "
            "déterministe à partir de ton nombre de paires et de ton "
            "numéro de série — jamais un mélange aléatoire en direct.",
            "La taille de carte ne change que la taille d'impression ; "
            "elle ne change jamais quels symboles sont sélectionnés ni "
            "leur ordre.",
            "Imprime les cartes et joue hors ligne ; rien de ta session "
            "n'est envoyé nulle part ni stocké par cet outil.",
        ),
        "instructions_title": "Comment jouer",
        "instructions_intro": (
            "Ceci est un jeu de mémoire hors ligne, à imprimer et à "
            "découper."
        ),
        "instructions_list": (
            "Imprime la feuille de cartes en taille réelle.",
            "Découpe le long du bord de chaque carte pour obtenir des "
            "cartes de paires individuelles.",
            "Mélange les cartes découpées et place-les face cachée en "
            "rangées.",
            "Retournez chacun votre tour deux cartes à la fois, en "
            "cherchant deux cartes avec le même symbole Bopomofo.",
            "Conservez les paires trouvées et continuez jusqu'à ce que "
            "toutes les cartes soient associées.",
        ),
        "webmcp_source": (
            "Aperçu de l'API impérative Chrome WebMCP (sujet à "
            "changement)"
        ),
        "webmcp_description": (
            "Génère des cartes privées et déterministes de paires "
            "Bopomofo à découper à partir d'un nombre de paires, d'un "
            "numéro de série et d'une taille de carte. Ne reçoit "
            "jamais le nom, l'âge, la classe, l'école, la "
            "localisation, la photo, l'écriture, la voix, "
            "l'historique de réponses, la note ou le compte d'un "
            "enfant ; n'affirme jamais que l'activité améliore la "
            "mémoire ni n'évalue un enfant."
        ),
        "app_title": "Une application Bopomofo guidée optionnelle ?",
        "app_text": (
            "Lumi Bopomofo est optionnelle. Sa fiche actuelle sur "
            "l'App Store décrit des activités ludiques de symboles, "
            "sons et combinaisons Zhuyin, ainsi que des jeux de tracé "
            "et de tons, gratuite à télécharger avec un déblocage "
            "unique dans l'application, fonctionne hors ligne, sans "
            "publicité, sans abonnement, et indique qu'aucune donnée "
            "n'est collectée. Vérifie la fiche actuelle avant de "
            "décider, car les fonctionnalités peuvent changer. Ces "
            "cartes à imprimer fonctionnent entièrement sans "
            "l'application."
        ),
        "app_cta": "Voir Lumi Bopomofo sur l'App Store",
        "faq_title": "Questions sur les cartes de paires Bopomofo",
        "faq": (
            (
                "Cet outil note-t-il, classe-t-il ou diagnostique-t-il "
                "mon enfant ?",
                "Non. Il transforme seulement le nombre de paires et "
                "le numéro de série choisis en cartes de paires à "
                "découper ; il ne note, ne classe, ni ne diagnostique "
                "jamais personne.",
            ),
            (
                "Jouer à ce jeu améliore-t-il la mémoire de mon "
                "enfant ?",
                "Cet outil ne fait pas cette affirmation. Il génère "
                "seulement une activité d'association à imprimer ; "
                "aucun bénéfice de jouer n'est mesuré ni promis ici.",
            ),
            (
                "Le même numéro de série donne-t-il toujours les "
                "mêmes cartes ?",
                "Oui. Le même nombre de paires et numéro de série "
                "reproduisent toujours les mêmes symboles sélectionnés "
                "dans le même ordre de cartes, afin que tu puisses "
                "régénérer une série déjà imprimée.",
            ),
            (
                "Cette page collecte-t-elle le nom, l'âge, l'école ou "
                "des données personnelles de mon enfant ?",
                "Non. Elle n'accepte qu'un nombre de paires, un "
                "numéro de série et une taille de carte ; rien n'est "
                "envoyé nulle part ni stocké.",
            ),
            (
                "Où puis-je vérifier le tracé officiel ou la "
                "prononciation du Bopomofo ?",
                "Utilise le portail officiel de tracé du ministère de "
                "l'Éducation de Taïwan lié sur cette page ; cet outil "
                "ne fournit ni prononciation, ni romanisation, ni "
                "animations de tracé.",
            ),
        ),
        "footer": (
            "Numéros de série privés uniquement · sans donnée "
            "d'enfant · sans notation · sans affirmation d'amélioration "
            "de la mémoire"
        ),
        "index_title": "Cartes privées de paires Bopomofo à découper",
        "index_description": (
            "Génère des cartes privées de paires Bopomofo à découper, "
            "gratuites à imprimer, à partir d'un nombre de paires et "
            "d'un numéro de série — sans compte, sans donnée sur "
            "l'enfant, sans notation."
        ),
        "inline_link_label": (
            "Générateur gratuit de cartes de paires Bopomofo à "
            "découper (sans notation)"
        ),
    },
    "ja": {
        "title": (
            "非公開ボポモフォ神経衰弱カード生成（無料印刷用注音ツール）"
        ),
        "description": (
            "無料で印刷できるボポモフォ（注音）神経衰弱カードを、ペア数"
            "とセット番号から生成します。印刷して切り取り、同じ記号を"
            "オフラインで見つける遊びです。アカウント登録、子供のデー"
            "タ収集、採点は一切ありません。"
        ),
        "tools": "無料ツール",
        "switch": "English",
        "eyebrow": "無料 ・ 登録不要 ・ 採点なし",
        "heading": "非公開ボポモフォ神経衰弱カード生成",
        "lead": (
            "ペア数と生成したいセット番号を選ぶと、切り取り用のカード"
            "シートを決定的に生成します。印刷してオフラインで神経衰弱"
            "遊びができます。このツールは子供を採点・順位付け・評価す"
            "ることは一切なく、記憶力向上を主張することもありません。"
        ),
        "badges": (
            "子供の名前・年齢・学校・アカウントは収集しません",
            "採点・成績・順位付け・記憶力向上の主張はありません",
            "同じセット番号は常に同じカードを再現します",
            "公式の筆順は台湾教育部のサイトでご確認ください",
        ),
        "planner": "印刷用カードを作成する",
        "planner_intro": (
            "ペア数、セット番号、カードサイズを選ぶと、印刷用シートが"
            "生成されます。このページは子供の名前、年齢、学校、写真、"
            "筆跡、声など、いかなる個人情報も尋ねません。"
        ),
        "pair_count_label": "記号のペア数（4〜12）",
        "set_number_label": "セット番号（1〜99）",
        "card_size_label": "カードサイズ",
        "card_size_options": {
            "compact": "コンパクト（1枚に多く収録）",
            "large": "大（切り取りやすい）",
        },
        "update": "印刷用カードを生成",
        "reset_label": "初期設定に戻す",
        "invalid_input": (
            "上記の対応範囲内でペア数、セット番号、カードサイズを選ん"
            "でください。"
        ),
        "result_count_label": "生成されたカード数",
        "print_label": "このカードを印刷",
        "reproducibility_note": (
            "同じペア数とセット番号は、常に同じ選択記号と同じカード順"
            "を再現します。新しいセット番号を選ぶと、対象記号が入れ替"
            "わります。"
        ),
        "card_label": "カード",
        "cards_region_label": "神経衰弱切り取りカード",
        "boundary_title": "このツールが行わないこと",
        "boundary_text": (
            "このツールは子供を評価・採点・成績付け・順位付け・診断す"
            "ることは一切なく、この神経衰弱遊びが記憶力やその他の能力"
            "を向上させるとは主張しません。選択したペア数とセット番号"
            "を印刷用カードに変換するだけです。"
        ),
        "independence_notice": (
            "これは無料の独立したウェブツールです。Lumi Bopomofoアプ"
            "リではなく、診断・評価・記憶トレーニングのいかなるツール"
            "でもありません。"
        ),
        "sources_title": "ボポモフォの公式情報源",
        "sources_intro": (
            "これらの事実とリンクは台湾教育部およびUnicodeコンソーシ"
            "アムによるものであり、当サイトのものではありません。"
        ),
        "source_labels": (
            "台湾教育部の公式注音符号ハンドブック",
            "台湾教育部の公式ボポモフォ筆順ポータル",
            "Unicode公式ボポモフォ名称一覧",
            "Unicode公式ボポモフォチャート（PDF）",
        ),
        "moe_check_label": "これらの記号の公式筆順を確認する",
        "moe_check_note": (
            "このツールは筆順アニメーションを自ら再現せず、教育部の公"
            "式ポータルへリンクします。"
        ),
        "unicode_note": (
            "BOPOMOFO LETTER Bのような Unicode 文字名は、記号を区別す"
            "るための技術的な識別子であり、発音の手引きではありません。"
        ),
        "no_pronunciation_note": (
            "このツールはいかなる記号の発音やローマ字表記も提供しませ"
            "ん。それらは台湾教育部の公式資料をご利用ください。"
        ),
        "how_it_works_title": "カードの生成方法",
        "how_it_works_intro": (
            "カードの選択と順序は、このサイトが実行する固定の文書化さ"
            "れたアルゴリズムによるものであり、ランダムなシャッフルや"
            "適応的な活動ではありません。"
        ),
        "how_it_works_list": (
            "4から12のペア数を選ぶと、37の基本ボポモフォ文字（ㄅから"
            "ㄩ）のうちその数が、セット番号に基づく固定のローテーショ"
            "ンで選択されます。",
            "1から99のセット番号を選ぶと、選択される記号がローテーシ"
            "ョンし、異なるセットは時間とともに37記号の範囲の異なる部"
            "分をカバーします。",
            "選択された各記号は必ず2枚のカードに現れ、カードの順序は"
            "ペア数とセット番号から決定的に構成されます。ライブなラン"
            "ダムシャッフルではありません。",
            "カードサイズは印刷サイズのみを変え、選択される記号やその"
            "順序を変えることはありません。",
            "カードを印刷してオフラインで遊んでください。セッションの"
            "内容はどこにも送信・保存されません。",
        ),
        "instructions_title": "遊び方",
        "instructions_intro": (
            "これは印刷して切り取る、オフラインの神経衰弱遊びです。"
        ),
        "instructions_list": (
            "カードシートを実寸で印刷します。",
            "各カードの枠線に沿って切り取り、個々の神経衰弱カードを作"
            "ります。",
            "切り取ったカードをシャッフルし、裏向きに並べます。",
            "交代で2枚ずつめくり、同じボポモフォ記号のペアを探します。",
            "揃ったペアは取り除き、すべてのカードが揃うまで続けます。",
        ),
        "webmcp_source": (
            "Chrome WebMCP命令型APIプレビュー（変更される場合がありま"
            "す）"
        ),
        "webmcp_description": (
            "ペア数、セット番号、カードサイズから、非公開かつ決定的な"
            "ボポモフォ神経衰弱切り取りカードを生成します。子供の名"
            "前、年齢、学年、学校、位置情報、写真、筆跡、声、回答履歴"
            "、採点、アカウントを一切受け取りません。この活動が記憶力"
            "を向上させる、または子供を評価するとは主張しません。"
        ),
        "app_title": "任意の案内付きボポモフォアプリをお探しですか？",
        "app_text": (
            "Lumi Bopomofoは任意です。現在のApp Store掲載では、楽しい"
            "注音記号・音・組み合わせ活動に加え、なぞり書きと声調ゲー"
            "ムが紹介されています。無料でダウンロードでき、アプリ内で"
            "一度だけ購入すれば解除、オフラインで動作し、広告なし、サ"
            "ブスクリプションなし、データは収集されないと記載されてい"
            "ます。機能は変更される可能性があるため、決める前に最新の"
            "掲載内容をご確認ください。この印刷カードはアプリなしでも"
            "完全に機能します。"
        ),
        "app_cta": "App StoreでLumi Bopomofoを見る",
        "faq_title": "ボポモフォ神経衰弱カードに関するよくある質問",
        "faq": (
            (
                "このツールは子供を採点・順位付け・診断しますか？",
                "いいえ。選択したペア数とセット番号を印刷用の神経衰弱"
                "カードに変換するだけで、誰かを採点・順位付け・成績付"
                "け・診断することは一切ありません。",
            ),
            (
                "この遊びをすると子供の記憶力が向上しますか？",
                "このツールはそのような主張をしません。印刷用の神経衰"
                "弱活動を生成するだけで、遊びによる効果はここでは測定"
                "も約束もされません。",
            ),
            (
                "同じセット番号なら常に同じカードになりますか？",
                "はい。同じペア数とセット番号は常に同じ選択記号と同じ"
                "カード順を再現するため、以前印刷したセットを再現でき"
                "ます。",
            ),
            (
                "このページは子供の名前、年齢、学校などの個人情報を収"
                "集しますか？",
                "いいえ。ペア数、セット番号、カードサイズのみを受け付"
                "け、どこにも送信・保存されません。",
            ),
            (
                "ボポモフォの公式筆順や発音はどこで確認できますか？",
                "このページにリンクされている台湾教育部の公式筆順ポー"
                "タルをご利用ください。このツールは発音、ローマ字表"
                "記、筆順アニメーションを提供しません。",
            ),
        ),
        "footer": (
            "非公開のセット番号のみ ・ 子供のデータなし ・ 採点なし ・"
            " 記憶力向上の主張なし"
        ),
        "index_title": "非公開ボポモフォ神経衰弱カード生成",
        "index_description": (
            "ペア数とセット番号から無料で印刷できる非公開のボポモフォ"
            "神経衰弱カードを生成します。登録不要、子供のデータなし、"
            "採点なし。"
        ),
        "inline_link_label": (
            "無料のボポモフォ神経衰弱カード生成ツール（採点なし）"
        ),
    },
    "ko": {
        "title": (
            "비공개 주음부호 짝맞추기 카드 생성기 | 무료 인쇄용 "
            "Zhuyin 도구"
        ),
        "description": (
            "무료로 인쇄할 수 있는 주음부호(Zhuyin) 짝맞추기 카드를 "
            "쌍의 개수와 세트 번호로 생성하세요. 인쇄하고 오려서 오프"
            "라인으로 같은 기호를 맞추는 놀이입니다. 계정 가입, 자녀 "
            "데이터 수집, 채점이 전혀 없습니다."
        ),
        "tools": "무료 도구",
        "switch": "English",
        "eyebrow": "무료 · 계정 불필요 · 채점 없음",
        "heading": "비공개 주음부호 짝맞추기 카드 생성기",
        "lead": (
            "포함할 기호 쌍의 개수와 생성할 세트 번호를 선택하면, 오려"
            "서 오프라인 짝맞추기 놀이를 할 수 있는 결정적인 카드 시트"
            "가 만들어집니다. 이 도구는 자녀를 채점, 순위, 평가하지 않"
            "으며, 기억력을 향상시킨다고 주장하지 않습니다."
        ),
        "badges": (
            "자녀의 이름, 나이, 학교, 계정을 수집하지 않습니다",
            "채점, 등급, 순위, 기억력 향상 주장이 없습니다",
            "같은 세트 번호는 항상 같은 카드를 재현합니다",
            "공식 필순은 대만 교육부 사이트에서 확인하세요",
        ),
        "planner": "인쇄용 짝맞추기 카드 만들기",
        "planner_intro": (
            "쌍의 개수, 세트 번호, 카드 크기를 선택하면 인쇄용 시트가 "
            "생성됩니다. 이 페이지는 자녀의 이름, 나이, 학교, 사진, 필"
            "체, 목소리 등 어떤 개인정보도 묻지 않습니다."
        ),
        "pair_count_label": "기호 쌍의 개수 (4~12)",
        "set_number_label": "세트 번호 (1~99)",
        "card_size_label": "카드 크기",
        "card_size_options": {
            "compact": "콤팩트 (한 장에 더 많이)",
            "large": "큼 (자르기 더 쉬움)",
        },
        "update": "인쇄용 카드 생성",
        "reset_label": "기본값으로 재설정",
        "invalid_input": (
            "위에 표시된 지원 범위 내에서 쌍의 개수, 세트 번호, 카드 "
            "크기를 선택하세요."
        ),
        "result_count_label": "생성된 카드 수",
        "print_label": "이 카드 인쇄",
        "reproducibility_note": (
            "같은 쌍의 개수와 세트 번호는 항상 같은 선택된 기호와 같"
            "은 카드 순서를 재현합니다. 새 세트 번호를 선택하면 다루"
            "는 기호가 순환됩니다."
        ),
        "card_label": "카드",
        "cards_region_label": "짝맞추기 오리기 카드",
        "boundary_title": "이 도구가 하지 않는 것",
        "boundary_text": (
            "이 도구는 자녀를 평가, 채점, 등급 매기기, 순위, 진단하지 "
            "않으며, 이 짝맞추기 놀이가 기억력이나 다른 능력을 향상시"
            "킨다고 주장하지 않습니다. 선택한 쌍의 개수와 세트 번호를 "
            "인쇄용 카드로 바꿀 뿐입니다."
        ),
        "independence_notice": (
            "이것은 무료 독립 웹 도구입니다. Lumi Bopomofo 앱이 아니"
            "며, 어떤 종류의 진단, 평가, 기억 훈련 도구도 아닙니다."
        ),
        "sources_title": "주음부호 공식 출처",
        "sources_intro": (
            "이 사실과 링크는 이 사이트가 아니라 대만 교육부와 유니코"
            "드 컨소시엄에서 제공한 것입니다."
        ),
        "source_labels": (
            "대만 교육부 공식 주음부호 안내서",
            "대만 교육부 공식 주음부호 필순 포털",
            "유니코드 공식 주음부호 이름 목록",
            "유니코드 공식 주음부호 차트 (PDF)",
        ),
        "moe_check_label": "이 기호들의 공식 필순 확인하기",
        "moe_check_note": (
            "이 도구는 필순 애니메이션을 자체적으로 재현하지 않고 교"
            "육부 공식 포털로 연결합니다."
        ),
        "unicode_note": (
            "BOPOMOFO LETTER B와 같은 유니코드 문자 이름은 기호를 구"
            "분하기 위한 기술적 식별자이며, 발음 안내가 아닙니다."
        ),
        "no_pronunciation_note": (
            "이 도구는 어떤 기호에 대해서도 발음이나 로마자 표기를 제"
            "공하지 않습니다. 이를 위해서는 대만 교육부의 공식 자료를 "
            "이용하세요."
        ),
        "how_it_works_title": "이 카드가 생성되는 방식",
        "how_it_works_intro": (
            "카드 선택과 순서는 무작위 셔플이나 적응형 활동이 아니라, "
            "이 사이트가 실행하는 고정되고 문서화된 알고리즘을 따릅니"
            "다."
        ),
        "how_it_works_list": (
            "4에서 12 사이의 쌍의 개수를 선택하면, 37개의 기본 주음부"
            "호 문자(ㄅ부터 ㄩ까지) 중 그 개수만큼이 세트 번호에 따른 "
            "고정 순환 방식으로 선택됩니다.",
            "1에서 99 사이의 세트 번호를 선택하면, 선택되는 기호가 순"
            "환되어 서로 다른 세트가 시간이 지나면서 37개 기호 범위의 "
            "서로 다른 부분을 다루게 됩니다.",
            "선택된 각 기호는 정확히 두 장의 카드에 나타나며, 카드 순"
            "서는 쌍의 개수와 세트 번호로부터 결정적으로 구성됩니다. "
            "실시간 무작위 셔플이 아닙니다.",
            "카드 크기는 인쇄 크기만 바꿀 뿐, 선택되는 기호나 순서는 "
            "바꾸지 않습니다.",
            "카드를 인쇄해 오프라인으로 놀이하세요. 세션의 어떤 내용"
            "도 어디로도 전송되거나 이 도구에 저장되지 않습니다.",
        ),
        "instructions_title": "노는 방법",
        "instructions_intro": (
            "이것은 인쇄해서 오려 쓰는 오프라인 짝맞추기 놀이입니다."
        ),
        "instructions_list": (
            "카드 시트를 실제 크기로 인쇄하세요.",
            "각 카드 테두리를 따라 잘라 개별 짝맞추기 카드를 만드세요.",
            "자른 카드를 섞어 뒷면이 보이도록 줄지어 놓으세요.",
            "번갈아 가며 카드 두 장을 뒤집어 같은 주음부호 기호를 찾으"
            "세요.",
            "맞춘 짝은 따로 모으고, 모든 카드가 맞춰질 때까지 계속하세"
            "요.",
        ),
        "webmcp_source": (
            "Chrome WebMCP 명령형 API 미리보기 (변경될 수 있음)"
        ),
        "webmcp_description": (
            "쌍의 개수, 세트 번호, 카드 크기로부터 비공개적이고 결정"
            "적인 주음부호 짝맞추기 오리기 카드를 생성합니다. 자녀의 "
            "이름, 나이, 학년, 학교, 위치, 사진, 필체, 목소리, 응답 이"
            "력, 점수, 계정을 절대 받지 않습니다. 이 활동이 기억력을 "
            "향상시키거나 자녀를 평가한다고 주장하지 않습니다."
        ),
        "app_title": "선택적인 안내형 주음부호 앱을 찾으시나요?",
        "app_text": (
            "Lumi Bopomofo는 선택 사항입니다. 현재 App Store 등록 정"
            "보에는 재미있는 주음 기호·소리·조합 활동과 따라 쓰기 및 "
            "성조 게임이 설명되어 있습니다. 무료로 다운로드할 수 있으"
            "며 앱 내 일회성 구매로 잠금 해제되고, 오프라인에서 작동"
            "하며, 광고 없음, 구독 없음, 데이터 미수집으로 표시되어 "
            "있습니다. 기능은 변경될 수 있으니 결정하기 전에 현재 등"
            "록 정보를 확인하세요. 이 인쇄용 카드는 앱 없이도 완전히 "
            "작동합니다."
        ),
        "app_cta": "App Store에서 Lumi Bopomofo 보기",
        "faq_title": "주음부호 짝맞추기 카드에 대한 자주 묻는 질문",
        "faq": (
            (
                "이 도구가 우리 아이를 채점, 순위, 진단하나요?",
                "아니요. 선택한 쌍의 개수와 세트 번호를 인쇄용 짝맞추"
                "기 카드로 바꿀 뿐이며, 누구도 채점, 순위, 등급, 진단"
                "하지 않습니다.",
            ),
            (
                "이 놀이를 하면 아이의 기억력이 향상되나요?",
                "이 도구는 그런 주장을 하지 않습니다. 인쇄용 짝맞추기 "
                "활동을 생성할 뿐이며, 놀이의 효과는 여기서 측정되거"
                "나 약속되지 않습니다.",
            ),
            (
                "같은 세트 번호는 항상 같은 카드를 만드나요?",
                "예. 같은 쌍의 개수와 세트 번호는 항상 같은 선택된 기"
                "호를 같은 카드 순서로 재현하므로, 이전에 인쇄한 세트"
                "를 다시 만들 수 있습니다.",
            ),
            (
                "이 페이지가 아이의 이름, 나이, 학교 등 개인정보를 수"
                "집하나요?",
                "아니요. 쌍의 개수, 세트 번호, 카드 크기만 받으며, 어"
                "디로도 전송되거나 저장되지 않습니다.",
            ),
            (
                "주음부호의 공식 필순이나 발음은 어디서 확인하나요?",
                "이 페이지에 링크된 대만 교육부의 공식 필순 포털을 이"
                "용하세요. 이 도구는 발음, 로마자 표기, 필순 애니메이"
                "션을 제공하지 않습니다.",
            ),
        ),
        "footer": (
            "비공개 세트 번호만 사용 · 자녀 데이터 없음 · 채점 없음 · "
            "기억력 향상 주장 없음"
        ),
        "index_title": "비공개 주음부호 짝맞추기 카드 생성기",
        "index_description": (
            "쌍의 개수와 세트 번호로 무료 인쇄용 비공개 주음부호 짝맞"
            "추기 카드를 생성합니다. 계정 불필요, 자녀 데이터 없음, "
            "채점 없음."
        ),
        "inline_link_label": (
            "무료 주음부호 짝맞추기 카드 생성기 (채점 없음)"
        ),
    },
    "zh-Hant": {
        "title": "私人注音配對卡產生器｜免費列印版 Zhuyin 記憶配對工具",
        "description": (
            "依你選擇的配對數與組別編號，產生免費可列印的注音（Zhuyin）"
            "配對剪卡。列印、剪下後，離線玩找出相同符號的配對遊戲。不"
            "需帳號、不收集孩子的資料、不評分。"
        ),
        "tools": "免費工具",
        "switch": "简体中文",
        "eyebrow": "免費 · 免帳號 · 不評分",
        "heading": "私人注音配對卡產生器",
        "lead": (
            "選擇要包含的符號配對數量，以及要產生的組別編號，即可產生"
            "一份決定性的剪卡列印頁，供離線進行配對遊戲。這個工具絕不"
            "會為孩子評分、排名或評估，也絕不宣稱能改善記憶力。"
        ),
        "badges": (
            "不收集孩子的姓名、年齡、學校或帳號",
            "沒有評分、成績、排名或改善記憶力的宣稱",
            "相同組別編號永遠會重現相同的卡片",
            "官方筆順請至台灣教育部網站查詢",
        ),
        "planner": "建立你的可列印配對卡",
        "planner_intro": (
            "選擇配對數量、組別編號與卡片大小，即可產生可列印頁面。這"
            "個頁面絕不會詢問孩子的姓名、年齡、學校、照片、筆跡、聲音"
            "或任何其他個人資料。"
        ),
        "pair_count_label": "符號配對數量（4～12）",
        "set_number_label": "組別編號（1～99）",
        "card_size_label": "卡片大小",
        "card_size_options": {
            "compact": "精簡（每頁可放更多）",
            "large": "大張（較容易剪裁）",
        },
        "update": "產生可列印卡片",
        "reset_label": "重設為預設值",
        "invalid_input": (
            "請在上方顯示的支援範圍內選擇配對數量、組別編號與卡片大"
            "小。"
        ),
        "result_count_label": "已產生卡片數",
        "print_label": "列印這些卡片",
        "reproducibility_note": (
            "相同的配對數量與組別編號，永遠會產生相同的選定符號與相同"
            "的卡片順序。選擇新的組別編號會輪替涵蓋的符號。"
        ),
        "card_label": "卡片",
        "cards_region_label": "配對剪卡",
        "boundary_title": "這個工具不會做的事",
        "boundary_text": (
            "這個工具絕不會評估、評分、打成績、排名或診斷孩子，也不會"
            "宣稱玩這個配對遊戲能改善記憶力或任何其他能力。它只是把你"
            "選擇的配對數量與組別編號轉換成可列印的剪卡。"
        ),
        "independence_notice": (
            "這是一個免費、獨立的網頁工具。它不是 Lumi 注音 App，也不"
            "是任何形式的診斷、評估或記憶訓練工具。"
        ),
        "sources_title": "注音官方資料來源",
        "sources_intro": (
            "這些資訊與連結來自台灣教育部與 Unicode 聯盟，並非本站提"
            "供。"
        ),
        "source_labels": (
            "台灣教育部《國語注音符號手冊》",
            "台灣教育部官方注音筆順入口網站",
            "Unicode 官方注音符號名稱表",
            "Unicode 官方注音符號圖表（PDF）",
        ),
        "moe_check_label": "查詢這些符號的官方筆順",
        "moe_check_note": (
            "本工具連結至教育部官方入口網站，並未自行重現筆順動畫。"
        ),
        "unicode_note": (
            "像 BOPOMOFO LETTER B 這類 Unicode 字元名稱，是用來區分符"
            "號的技術識別碼，並非發音指南。"
        ),
        "no_pronunciation_note": (
            "本工具不提供任何符號的發音或拼音；如需發音，請使用台灣教"
            "育部的官方資源。"
        ),
        "how_it_works_title": "這些卡片如何產生",
        "how_it_works_intro": (
            "卡片的選取與順序，來自本站執行的固定、已公開說明的演算"
            "法，並非隨機洗牌或適應性活動。"
        ),
        "how_it_works_list": (
            "選擇 4 到 12 的配對數量；37 個基本注音符號（ㄅ到ㄩ）中，"
            "會依組別編號以固定輪替方式選出對應數量。",
            "選擇 1 到 99 的組別編號；每個組別編號都會輪替所選的符"
            "號，因此不同組別會隨時間涵蓋 37 個符號範圍中的不同部分。",
            "每個選定符號恰好出現在兩張卡片上，卡片順序則依配對數量與"
            "組別編號決定性地排列——絕非即時隨機洗牌。",
            "卡片大小只會改變列印呈現方式，絕不會改變所選符號或其順"
            "序。",
            "列印卡片後即可離線遊玩；你的操作內容不會被傳送到任何地"
            "方，也不會被本工具儲存。",
        ),
        "instructions_title": "怎麼玩",
        "instructions_intro": "這是一款列印、剪裁後離線進行的配對遊戲。",
        "instructions_list": (
            "以實際大小列印卡片頁。",
            "沿著每張卡片的邊框剪下，做成一張張獨立的配對卡。",
            "洗混剪下的卡片，將卡片背面朝上排成數列。",
            "輪流翻開兩張卡片，尋找兩張相同注音符號的卡片。",
            "配對成功的卡片留下，繼續進行直到所有卡片都配對完成。",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽版（內容可能變動）",
        "webmcp_description": (
            "依配對數量、組別編號與卡片大小，產生私人、決定性的注音配"
            "對剪卡。絕不接收孩子的姓名、年齡、年級、學校、位置、照"
            "片、筆跡、聲音、作答紀錄、分數或帳號；絕不宣稱此活動能改"
            "善記憶力或評估孩子。"
        ),
        "app_title": "想要選用式的注音引導 App 嗎？",
        "app_text": (
            "Lumi 注音是選用的。目前 App Store 的頁面說明其提供有趣"
            "的注音符號、發音與組合活動，以及描紅與聲調遊戲；免費下"
            "載，App 內一次性解鎖即可使用，可離線運作，無廣告、無訂"
            "閱，並標示不收集資料。功能可能會更動，決定前請確認目前"
            "頁面內容。這些可列印卡片不需要這款 App 也能完整使用。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音",
        "faq_title": "注音配對卡常見問題",
        "faq": (
            (
                "這個工具會為孩子評分、排名或診斷嗎？",
                "不會。它只會把你選擇的配對數量與組別編號轉換成可列印"
                "的配對剪卡；絕不會為任何人評分、排名、打成績或診斷。",
            ),
            (
                "玩這個遊戲會改善孩子的記憶力嗎？",
                "本工具並未做出這樣的宣稱。它只會產生可列印的配對活"
                "動；遊玩帶來的任何效果，本頁並未測量也未做出承諾。",
            ),
            (
                "同一個組別編號永遠會得到相同的卡片嗎？",
                "會。相同的配對數量與組別編號，永遠會重現相同的選定符"
                "號與相同的卡片順序，因此你可以重新產生之前列印過的組"
                "別。",
            ),
            (
                "這個頁面會收集孩子的姓名、年齡、學校或其他個人資料"
                "嗎？",
                "不會。它只接受配對數量、組別編號與卡片大小；任何內容"
                "都不會被傳送到任何地方或被儲存。",
            ),
            (
                "要去哪裡查詢注音的官方筆順或發音？",
                "請使用本頁連結的台灣教育部官方筆順入口網站；本工具不"
                "提供發音、拼音或筆順動畫。",
            ),
        ),
        "footer": "僅使用私人組別編號 · 不收集孩子資料 · 不評分 · 不宣稱改善記憶力",
        "index_title": "私人注音配對卡產生器",
        "index_description": (
            "依配對數量與組別編號，產生免費可列印的私人注音配對卡。免"
            "帳號、不收集孩子資料、不評分。"
        ),
        "inline_link_label": "免費注音配對卡產生工具（不評分）",
    },
    "zh-Hans": {
        "title": "私人注音配对卡生成器｜免费打印版 Zhuyin 记忆配对工具",
        "description": (
            "根据你选择的配对数量与组别编号，生成免费可打印的注音"
            "（Zhuyin）配对剪卡。打印、剪下后，离线进行寻找相同符号的"
            "配对游戏。不需账号、不收集孩子的数据、不评分。"
        ),
        "tools": "免费工具",
        "switch": "繁體中文",
        "eyebrow": "免费 · 免账号 · 不评分",
        "heading": "私人注音配对卡生成器",
        "lead": (
            "选择要包含的符号配对数量，以及要生成的组别编号，即可生成"
            "一份确定性的剪卡打印页，供离线进行配对游戏。这个工具绝不"
            "会为孩子评分、排名或评估，也绝不宣称能改善记忆力。"
        ),
        "badges": (
            "不收集孩子的姓名、年龄、学校或账号",
            "没有评分、成绩、排名或改善记忆力的宣称",
            "相同组别编号始终会重现相同的卡片",
            "官方笔顺请至台湾教育部网站查询",
        ),
        "planner": "创建你的可打印配对卡",
        "planner_intro": (
            "选择配对数量、组别编号与卡片大小，即可生成可打印页面。这"
            "个页面绝不会询问孩子的姓名、年龄、学校、照片、笔迹、声音"
            "或任何其他个人数据。"
        ),
        "pair_count_label": "符号配对数量（4～12）",
        "set_number_label": "组别编号（1～99）",
        "card_size_label": "卡片大小",
        "card_size_options": {
            "compact": "紧凑（每页可放更多）",
            "large": "大号（更易剪裁）",
        },
        "update": "生成可打印卡片",
        "reset_label": "重置为默认值",
        "invalid_input": (
            "请在上方显示的支持范围内选择配对数量、组别编号与卡片大"
            "小。"
        ),
        "result_count_label": "已生成卡片数",
        "print_label": "打印这些卡片",
        "reproducibility_note": (
            "相同的配对数量与组别编号，始终会生成相同的选定符号与相同"
            "的卡片顺序。选择新的组别编号会轮换所涵盖的符号。"
        ),
        "card_label": "卡片",
        "cards_region_label": "配对剪卡",
        "boundary_title": "这个工具不会做的事",
        "boundary_text": (
            "这个工具绝不会评估、评分、打分、排名或诊断孩子，也不会宣"
            "称玩这个配对游戏能改善记忆力或任何其他能力。它只是把你选"
            "择的配对数量与组别编号转换成可打印的剪卡。"
        ),
        "independence_notice": (
            "这是一个免费、独立的网页工具。它不是 Lumi 注音 App，也不"
            "是任何形式的诊断、评估或记忆训练工具。"
        ),
        "sources_title": "注音官方资料来源",
        "sources_intro": (
            "这些信息与链接来自台湾教育部与 Unicode 联盟，并非本站提"
            "供。"
        ),
        "source_labels": (
            "台湾教育部《国语注音符号手册》",
            "台湾教育部官方注音笔顺入口网站",
            "Unicode 官方注音符号名称表",
            "Unicode 官方注音符号图表（PDF）",
        ),
        "moe_check_label": "查询这些符号的官方笔顺",
        "moe_check_note": (
            "本工具链接至教育部官方入口网站，并未自行重现笔顺动画。"
        ),
        "unicode_note": (
            "像 BOPOMOFO LETTER B 这类 Unicode 字符名称，是用来区分符"
            "号的技术标识符，并非发音指南。"
        ),
        "no_pronunciation_note": (
            "本工具不提供任何符号的发音或拼音；如需发音，请使用台湾教"
            "育部的官方资源。"
        ),
        "how_it_works_title": "这些卡片如何生成",
        "how_it_works_intro": (
            "卡片的选取与顺序，来自本站执行的固定、已公开说明的算法，"
            "并非随机洗牌或自适应活动。"
        ),
        "how_it_works_list": (
            "选择 4 到 12 的配对数量；37 个基本注音符号（ㄅ到ㄩ）中，"
            "会依组别编号以固定轮换方式选出对应数量。",
            "选择 1 到 99 的组别编号；每个组别编号都会轮换所选的符号，"
            "因此不同组别会随时间涵盖 37 个符号范围中的不同部分。",
            "每个选定符号恰好出现在两张卡片上，卡片顺序则依配对数量与"
            "组别编号确定性地排列——绝非实时随机洗牌。",
            "卡片大小只会改变打印呈现方式，绝不会改变所选符号或其顺"
            "序。",
            "打印卡片后即可离线游玩；你的操作内容不会被发送到任何地"
            "方，也不会被本工具存储。",
        ),
        "instructions_title": "怎么玩",
        "instructions_intro": "这是一款打印、剪裁后离线进行的配对游戏。",
        "instructions_list": (
            "以实际大小打印卡片页。",
            "沿着每张卡片的边框剪下，制成一张张独立的配对卡。",
            "洗混剪下的卡片，将卡片背面朝上排成数列。",
            "轮流翻开两张卡片，寻找两张相同注音符号的卡片。",
            "配对成功的卡片留下，继续进行直到所有卡片都配对完成。",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览版（内容可能变动）",
        "webmcp_description": (
            "依配对数量、组别编号与卡片大小，生成私人、确定性的注音配"
            "对剪卡。绝不接收孩子的姓名、年龄、年级、学校、位置、照"
            "片、笔迹、声音、作答记录、分数或账号；绝不宣称此活动能改"
            "善记忆力或评估孩子。"
        ),
        "app_title": "想要可选的注音引导 App 吗？",
        "app_text": (
            "Lumi 注音是可选的。目前 App Store 页面说明其提供有趣的注"
            "音符号、发音与组合活动，以及描红与声调游戏；免费下载，"
            "App 内一次性解锁即可使用，可离线运行，无广告、无订阅，并"
            "标示不收集数据。功能可能会变动，决定前请确认目前页面内"
            "容。这些可打印卡片不需要这款 App 也能完整使用。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音",
        "faq_title": "注音配对卡常见问题",
        "faq": (
            (
                "这个工具会为孩子评分、排名或诊断吗？",
                "不会。它只会把你选择的配对数量与组别编号转换成可打印"
                "的配对剪卡；绝不会为任何人评分、排名、打分或诊断。",
            ),
            (
                "玩这个游戏会改善孩子的记忆力吗？",
                "本工具并未做出这样的宣称。它只会生成可打印的配对活"
                "动；游玩带来的任何效果，本页并未测量也未做出承诺。",
            ),
            (
                "同一个组别编号始终会得到相同的卡片吗？",
                "会。相同的配对数量与组别编号，始终会重现相同的选定符"
                "号与相同的卡片顺序，因此你可以重新生成之前打印过的组"
                "别。",
            ),
            (
                "这个页面会收集孩子的姓名、年龄、学校或其他个人数据"
                "吗？",
                "不会。它只接受配对数量、组别编号与卡片大小；任何内容"
                "都不会被发送到任何地方或被存储。",
            ),
            (
                "要去哪里查询注音的官方笔顺或发音？",
                "请使用本页链接的台湾教育部官方笔顺入口网站；本工具不"
                "提供发音、拼音或笔顺动画。",
            ),
        ),
        "footer": "仅使用私人组别编号 · 不收集孩子数据 · 不评分 · 不宣称改善记忆力",
        "index_title": "私人注音配对卡生成器",
        "index_description": (
            "依配对数量与组别编号，生成免费可打印的私人注音配对卡。免"
            "账号、不收集孩子数据、不评分。"
        ),
        "inline_link_label": "免费注音配对卡生成工具（不评分）",
    },
}


STYLE = r"""
:root{--ink:#21314a;--muted:#67738a;--line:#dfe5f0;--paper:#fff;--bg:#f3f6fb;--deep:#3949a3;--violet:#7566c8;--soft:#edf0ff;--warn:#fff6d8;--shadow:0 22px 60px rgba(47,57,108,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e9edf7 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--deep)}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cad2e4;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}.button.ghost{background:#fff;color:var(--deep);border:1px solid var(--line);box-shadow:none}
.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.card-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}.card-grid.large{grid-template-columns:repeat(2,minmax(0,1fr))}.print-card{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;background:#fff;border:2px solid var(--line);border-radius:16px;padding:16px;min-height:110px;break-inside:avoid}.card-grid.large .print-card{min-height:170px}.print-card .card-symbol{font-size:40px;line-height:1}.card-grid.large .print-card .card-symbol{font-size:64px}.print-card .card-number{font-size:11px;font-weight:850;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;overflow-x:auto}
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#f4f5ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}.card-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.card-grid.large{grid-template-columns:1fr 1fr}}
@media(max-width:720px){.card-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card-grid.large{grid-template-columns:1fr}}
@media(max-width:560px){.controls{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.planner form,.planner .intro,.button,.app-card,.footer,.card,.faq{display:none!important}body{background:#fff}.planner{box-shadow:none;border:0;padding:0}.card-grid{box-shadow:none}.print-card{box-shadow:none;break-inside:avoid;border-color:#000}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(
    document.getElementById("bopomofo-matchpair-config").textContent);
  const form = document.getElementById("bopomofo-matchpair-planner");
  const fields = {
    pair_count: document.getElementById("pair-count"),
    set_number: document.getElementById("set-number"),
    card_size: document.getElementById("card-size")
  };
  const summary = document.getElementById("result-summary");
  const grid = document.getElementById("card-grid");
  const printButton = document.getElementById("print-cards");

  const LCG_MULTIPLIER = 214013;
  const LCG_INCREMENT = 2531011;
  const LCG_MODULUS = 2147483648;

  function nextState(state) {
    return (state * LCG_MULTIPLIER + LCG_INCREMENT) % LCG_MODULUS;
  }

  function drawValue(state) {
    return Math.floor(state / 65536) % 32768;
  }

  function enumValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const values = config.inputSchema.properties[name].enum;
    if (typeof value !== "string" || !values.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    return value;
  }

  function integerValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const schema = config.inputSchema.properties[name];
    if (typeof value !== "number" || !Number.isInteger(value)) {
      throw new TypeError(`${name} must be an integer.`);
    }
    if (value < schema.minimum || value > schema.maximum) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function selectSymbols(pairCount, setNumber) {
    const total = config.symbols.length;
    const offset = ((setNumber - 1) * pairCount) % total;
    const symbols = [];
    for (let k = 0; k < pairCount; k += 1) {
      symbols.push(config.symbols[(offset + k) % total]);
    }
    return symbols;
  }

  function shuffleOrder(pairCount, setNumber) {
    const total = pairCount * 2;
    const order = [];
    for (let index = 0; index < total; index += 1) {
      order.push(index % pairCount);
    }
    let state = pairCount * 10000 + setNumber;
    for (let i = total - 1; i > 0; i -= 1) {
      state = nextState(state);
      const j = drawValue(state) % (i + 1);
      const temp = order[i];
      order[i] = order[j];
      order[j] = temp;
    }
    return order;
  }

  function buildCards(input) {
    const pairCount = integerValue(input, "pair_count");
    const setNumber = integerValue(input, "set_number");
    const cardSize = enumValue(input, "card_size");
    const symbols = selectSymbols(pairCount, setNumber);
    const order = shuffleOrder(pairCount, setNumber);
    const cards = order.map((pairIndex, index) => {
      const symbol = symbols[pairIndex];
      return {
        card_number: index + 1,
        pair_index: pairIndex,
        symbol,
        code_point: config.codePoints[symbol],
        unicode_name: config.unicodeNames[symbol],
        card_size: cardSize
      };
    });
    return {
      selected_inputs: {
        pair_count: pairCount,
        set_number: setNumber,
        card_size: cardSize
      },
      selected_symbols: symbols,
      cards,
      unicode_note: config.unicodeNote,
      official_sources: config.officialSources,
      moe_stroke_order_check: config.moeStrokeOrderCheck
    };
  }

  function validateInput(input) {
    if (input === null || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("WebMCP input must be an object.");
    }
    const allowed = new Set(Object.keys(config.inputSchema.properties));
    for (const name of Object.keys(input)) {
      if (!allowed.has(name)) {
        throw new RangeError(`${name} is not a supported input.`);
      }
    }
    for (const name of config.inputSchema.required) {
      if (!Object.prototype.hasOwnProperty.call(input, name)) {
        throw new TypeError(`${name} is required.`);
      }
    }
    return buildCards(input);
  }

  function humanIntegerValue(field, name) {
    const raw = String(field.value).trim();
    const value = raw === "" ? Number.NaN : Number(raw);
    const schema = config.inputSchema.properties[name];
    if (!Number.isInteger(value) ||
        value < schema.minimum ||
        value > schema.maximum) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function renderInvalid(message) {
    summary.textContent = message;
    grid.replaceChildren();
  }

  function makeCardElement(card) {
    const article = document.createElement("article");
    article.className = "print-card";
    article.setAttribute("role", "listitem");
    const header = document.createElement("div");
    header.className = "card-number";
    header.textContent = `${config.labels.card} ${card.card_number}`;
    const symbol = document.createElement("div");
    symbol.className = "card-symbol";
    symbol.textContent = card.symbol;
    const hidden = document.createElement("span");
    hidden.className = "visually-hidden";
    hidden.textContent = `${card.unicode_name} (${card.code_point})`;
    article.appendChild(header);
    article.appendChild(symbol);
    article.appendChild(hidden);
    return article;
  }

  function render() {
    let result;
    try {
      result = buildCards({
        pair_count: humanIntegerValue(fields.pair_count, "pair_count"),
        set_number: humanIntegerValue(fields.set_number, "set_number"),
        card_size: fields.card_size.value
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        renderInvalid(config.invalidInput);
        return;
      }
      throw error;
    }
    summary.textContent = `${config.labels.resultCount}: ${result.cards.length}`;
    grid.className = `card-grid ${result.selected_inputs.card_size}`;
    grid.setAttribute("role", "list");
    const fragment = document.createDocumentFragment();
    for (const card of result.cards) {
      fragment.appendChild(makeCardElement(card));
    }
    grid.replaceChildren(fragment);
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "create_private_bopomofo_matching_pair_cards",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_bopomofo_matching_pair_cards",
          is_not_assessment: true,
          no_score_grade_or_diagnosis: true,
          no_memory_improvement_claim: true,
          no_child_data_received: true,
          no_pronunciation_or_romanization: true,
          plan,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_lumibopomofo = config.optionalApp;
        }
        return JSON.stringify(result);
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  for (const field of Object.values(fields)) {
    field.addEventListener("change", render);
  }
  if (printButton) {
    printButton.addEventListener("click", () => window.print());
  }
  render();
  registerWebMcp().catch((error) =>
    console.error("WebMCP tool registration failed.", error));
})();
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        '<script type="application/ld+json">'
        + payload.replace("</", "<\\/")
        + "</script>"
    )


def options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(str(value), quote=True)}">'
        f"{html.escape(label)}</option>"
        for value, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    return {
        "type": "object",
        "properties": {
            "pair_count": {
                "type": "integer",
                "minimum": PAIR_COUNT_MIN,
                "maximum": PAIR_COUNT_MAX,
                "description": t["pair_count_label"],
            },
            "set_number": {
                "type": "integer",
                "minimum": SET_NUMBER_MIN,
                "maximum": SET_NUMBER_MAX,
                "description": t["set_number_label"],
            },
            "card_size": {
                "type": "string",
                "enum": list(CARD_SIZES),
                "description": t["card_size_label"],
            },
        },
        "required": ["pair_count", "set_number", "card_size"],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other)
    prefix = "" if locale == "en" else f"{locale}/"
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{html.escape(alt, quote=True)}" '
        f'href="{html.escape(canonical(alt), quote=True)}">'
        for alt in ALT_LOCALES
    )
    sources = (
        MOE_HANDBOOK,
        MOE_STROKE_ORDER,
        UNICODE_NAMES_LIST,
        UNICODE_CHART_PDF,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    how_it_works_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["how_it_works_list"]
    )
    instructions_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["instructions_list"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_bopomofo_matchpair_{locale.lower()}")
        if app_public
        else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            '<section class="app-card wrap"><h2>'
            f'{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
        )
    official_sources = [
        {"label": label, "url": source}
        for label, source in zip(t["source_labels"], sources, strict=True)
    ]
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "symbols": list(SYMBOL_VALUES),
        "codePoints": dict(SYMBOL_CODE_POINTS),
        "unicodeNames": dict(SYMBOL_UNICODE_NAMES),
        "labels": {
            "card": t["card_label"],
            "resultCount": t["result_count_label"],
        },
        "invalidInput": t["invalid_input"],
        "toolDescription": t["webmcp_description"],
        "unicodeNote": t["unicode_note"],
        "officialSources": official_sources,
        "moeStrokeOrderCheck": {
            "label": t["moe_check_label"],
            "url": MOE_STROKE_ORDER,
        },
        "webmcpSource": WEBMCP_SOURCE,
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
    config_json = json.dumps(
        config, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "featureList": [*t["badges"], t["boundary_text"]],
        "citation": list(sources),
    }
    howto_schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": t["instructions_title"],
        "description": t["instructions_intro"],
        "step": [
            {
                "@type": "HowToStep",
                "position": index + 1,
                "text": step,
            }
            for index, step in enumerate(t["instructions_list"])
        ],
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
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["tools"], "item": tools},
            {"@type": "ListItem", "position": 2, "name": t["heading"], "item": url},
        ],
    }
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
<style>{STYLE}</style>
{json_script(schema)}
{json_script(howto_schema)}
{json_script(faq_schema)}
{json_script(breadcrumb_schema)}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="bopomofo-matchpair-planner"><div class="controls">
<div class="field"><label for="pair-count">{html.escape(t["pair_count_label"])}</label><input id="pair-count" type="number" min="{PAIR_COUNT_MIN}" max="{PAIR_COUNT_MAX}" step="1" value="{DEFAULT_PAIR_COUNT}" required></div>
<div class="field"><label for="set-number">{html.escape(t["set_number_label"])}</label><input id="set-number" type="number" min="{SET_NUMBER_MIN}" max="{SET_NUMBER_MAX}" step="1" value="{DEFAULT_SET_NUMBER}" required></div>
<div class="field"><label for="card-size">{html.escape(t["card_size_label"])}</label><select id="card-size">{options(t["card_size_options"])}</select></div>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button> <button class="button ghost" type="button" id="print-cards">{html.escape(t["print_label"])}</button></p>
<p class="intro">{html.escape(t["reproducibility_note"])}</p></form>
<p id="result-summary" class="note" role="status" aria-live="polite"></p>
<div id="card-grid" class="card-grid {DEFAULT_CARD_SIZE}" role="list" aria-label="{html.escape(t["cards_region_label"], quote=True)}"></div>
</section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p>{html.escape(t["boundary_text"])}</p><p>{html.escape(t["independence_notice"])}</p><p>{html.escape(t["no_pronunciation_note"])}</p></article><article class="card"><h2>{html.escape(t["moe_check_label"])}</h2><p>{html.escape(t["moe_check_note"])}</p><p><a href="{MOE_STROKE_ORDER}" rel="noopener">{html.escape(t["moe_check_label"])}</a></p></article><article class="card wide"><h2>{html.escape(t["how_it_works_title"])}</h2><p>{html.escape(t["how_it_works_intro"])}</p><ol>{how_it_works_items}</ol></article><article class="card wide"><h2>{html.escape(t["instructions_title"])}</h2><p>{html.escape(t["instructions_intro"])}</p><ol>{instructions_items}</ol></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p>{html.escape(t["unicode_note"])}</p><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="bopomofo-matchpair-config">{config_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    card = index_card(locale)
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    match = existing.search(text)
    if match:
        updated = existing.sub(card, text, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in text:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = text.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


# Exactly six pre-existing answer-page slugs are eligible for the inbound
# link, and only in the locales where each file actually exists. The generic
# tracing slug exists in all nine locales; the other five exist only in
# en and zh-Hant. This explicit slug list (rather than a directory glob)
# guarantees the generator never touches broader Bopomofo pages,
# unsupported locales, or files without the exact Lumi App Store CTA.
TARGET_ANSWER_SLUGS = (
    "my-child-learns-the-bopomofo-symbols-but-keeps-forgetting-them-how-do-i-help.html",
    "bopomofo-tracing-app-for-kids.html",
    "zhuyin-tracing-app-for-taiwanese-children.html",
    "how-to-learn-the-37-zhuyin-symbols-and-mandarin-tones-as-a-beginner.html",
    "is-there-a-fun-app-to-teach-my-4-year-old-the-zhuyin-bopomofo-symbols.html",
    "should-my-child-learn-zhuyin-bopomofo-before-starting-school.html",
)

INBOUND_LINK_CLASS = "bopomofo-matchpair-cards-inline-link"
_CTA_ANCHOR_PATTERN = re.compile(
    r'<a\b[^>]*\bclass\s*=\s*(?P<q1>["\'])[^"\']*\bcta\b[^"\']*(?P=q1)[^>]*'
    r'\bhref\s*=\s*(?P<q2>["\'])[^"\']*apps\.apple\.com/app/id'
    + re.escape(APP_ID) +
    r'(?:[?#][^"\']*)?(?P=q2)[^>]*>',
    re.IGNORECASE,
)
_QR_CTA_ANCHOR_PATTERN = re.compile(
    r'<a\b[^>]*\bclass\s*=\s*(?P<q1>["\'])[^"\']*'
    r'\bapp-store-qr-card__link\b[^"\']*(?P=q1)[^>]*'
    r'\bhref\s*=\s*(?P<q2>["\'])[^"\']*apps\.apple\.com/app/id'
    + re.escape(APP_ID) +
    r'(?:[?#][^"\']*)?(?P=q2)[^>]*>',
    re.IGNORECASE,
)
_EXACT_APP_STORE_ANCHOR_PATTERN = re.compile(
    r'<a\b(?=[^>]*\shref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + re.escape(APP_ID)
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)


def _answer_directory(pages: Path, locale: str) -> Path:
    return pages / "answers" if locale == "en" else pages / locale / "answers"


def insert_answer_links(pages: Path = PAGES) -> int:
    """Insert one localized free-tool link before the first Lumi Bopomofo CTA.

    Narrowly scoped to the exact 6 target slugs (`TARGET_ANSWER_SLUGS`) times
    the 9 supported locales -- exactly 19 real files are expected to exist
    (5 slugs only in en/zh-Hant, plus the tracing slug in all 9 locales).
    Any locale/slug combination whose file does not exist is skipped.
    Insertion is idempotent (skips files that already carry the marker
    class) and safe (skips files where no recognizable pre-CTA anchor can
    be found, rather than risking corrupt HTML). Broader Bopomofo pages,
    unsupported locales, and files without the exact CTA are never touched.
    """
    changed = 0
    for locale in ALT_LOCALES:
        directory = _answer_directory(pages, locale)
        t = COPY[locale]
        link_html = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-bopomofo-matchpair-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(t["inline_link_label"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS:
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if APP_ID not in text:
                continue
            if INBOUND_LINK_CLASS in text:
                continue
            match = _CTA_ANCHOR_PATTERN.search(text)
            if not match:
                match = _QR_CTA_ANCHOR_PATTERN.search(text)
            if not match:
                match = _EXACT_APP_STORE_ANCHOR_PATTERN.search(text)
            if not match:
                continue
            updated = text[: match.start()] + link_html + text[match.start() :]
            if write_text_if_changed(path, updated):
                changed += 1
    return changed


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    if app_public is None:
        app_public = APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)
    outputs = []
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        update_one_index(
            pages / ("tools" if locale == "en" else f"{locale}/tools") / "index.html",
            locale,
        )
        outputs.append(canonical(locale))
    insert_answer_links(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"bopomofo matching-pair cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
