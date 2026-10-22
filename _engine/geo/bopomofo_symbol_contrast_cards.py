#!/usr/bin/env python3
"""Generate a nine-locale private Bopomofo symbol-contrast practice-card tool."""

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
SLUG = "private-bopomofo-symbol-contrast-cards"
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
CONTENT_DATE = "2026-07-15"

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
ACTIVITY_MODES = ("visual", "trace", "mixed")
# Fixed, deterministic six-slot row used by every visual card: three
# occurrences of each chosen symbol, always in the same interleaved order.
ROW_PATTERN = ("A", "B", "B", "A", "B", "A")
DEFAULT_SYMBOL_A = SYMBOL_VALUES[0]
DEFAULT_SYMBOL_B = SYMBOL_VALUES[-1]

COPY = {
    "en": {
        "title": "Private Bopomofo Symbol Contrast Cards | Free Printable Zhuyin Tool",
        "description": (
            "Pick any two Bopomofo (Zhuyin) symbols and generate free printable "
            "practice cards for finding, pointing to, and tracing them — no "
            "account, no child data, no assessment or common-confusion claim."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no account · no assessment",
        "heading": "Private Bopomofo symbol contrast cards",
        "lead": (
            "Choose any two Zhuyin symbols you want your family to compare, then "
            "generate printable practice cards that ask your child to find, point "
            "to, or trace each one. This tool never claims the pair you pick is "
            "commonly confused, and it never scores, diagnoses, or profiles a "
            "child."
        ),
        "badges": (
            "No child name, age, school, or account collected",
            "No score, grade, or diagnosis of any kind",
            "Your chosen pair is never called commonly confused",
            "Official stroke order stays on Taiwan's MOE site",
        ),
        "planner": "Build your printable contrast cards",
        "planner_intro": (
            "Choose two different symbols, an activity mode, and how many cards "
            "to print. This page never asks for your child's name, age, school, "
            "photo, handwriting, voice, or any other personal detail."
        ),
        "symbol_a_label": "First Zhuyin symbol to contrast",
        "symbol_b_label": "Second Zhuyin symbol to contrast",
        "activity_mode_label": "Activity mode",
        "activity_mode_options": {
            "visual": "Find & point (visual)",
            "trace": "Trace & compare",
            "mixed": "Mixed (alternating)",
        },
        "card_count_label": "Number of cards to generate (4–12)",
        "update": "Update printable cards",
        "invalid_input": (
            "Choose two different symbols and values within the supported "
            "ranges shown above."
        ),
        "result_count_label": "Cards generated",
        "print_label": "Print these cards",
        "prompt_visual": (
            "Find and point to every {target} in this row (it also contains "
            "{other})."
        ),
        "prompt_trace": (
            "Trace {target} carefully, then compare it with {other} next to it."
        ),
        "compare_label": "Compare with:",
        "card_label": "Card",
        "boundary_title": "What this tool does not do",
        "boundary_text": (
            "This tool does not assess, score, grade, or diagnose a child, and "
            "it never claims that the two symbols you chose are commonly "
            "confused. It only turns your own selected pair into printable "
            "finding, pointing, and tracing prompts."
        ),
        "independence_notice": (
            "This is a free, independent web tool. It is not the Lumi Bopomofo "
            "app, and it is not a diagnostic tool or assessment of any kind."
        ),
        "sources_title": "Official Bopomofo sources",
        "sources_intro": (
            "These facts and links come from Taiwan's Ministry of Education and "
            "the Unicode Consortium, not from this site."
        ),
        "source_labels": (
            "Taiwan MOE official Bopomofo stroke-order portal",
            "Unicode official Bopomofo names list",
            "Unicode official Bopomofo chart (PDF)",
        ),
        "moe_check_label": "Check official stroke order for your chosen symbols",
        "moe_check_note": (
            "This tool links to the official Ministry of Education portal "
            "instead of reproducing stroke-order animations itself."
        ),
        "unicode_note": (
            "Unicode character names, such as BOPOMOFO LETTER B, are technical "
            "identifiers used to tell symbols apart; they are not pronunciation "
            "guides."
        ),
        "how_it_works_title": "How these cards are generated",
        "how_it_works_intro": (
            "Card generation is a fixed, deterministic layout created by this "
            "site, not an adaptive or AI-personalized activity."
        ),
        "how_it_works_list": (
            "Pick any two of the 37 basic Bopomofo letters (ㄅ through ㄩ); the "
            "pair is only the one you selected, never a suggestion from this "
            "site.",
            "Choose visual cards to find and point to the target symbol, trace "
            "cards to trace the target and compare it with the other symbol, or "
            "mixed to alternate both activities.",
            "Set how many cards to generate, from 4 to 12; the target symbol "
            "alternates between your two chosen symbols on every card.",
            "Print the cards and practice offline; nothing about your practice "
            "session is sent anywhere or stored by this tool.",
            "For official stroke order, use Taiwan's Ministry of Education "
            "portal linked below instead of relying on any app or website "
            "animation.",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Build private, deterministic Bopomofo symbol-contrast practice "
            "cards from two chosen symbols, an activity mode, and a card count. "
            "Never receive a child's name, age, grade, school, location, photo, "
            "handwriting, voice, answer history, score, or account; never claim "
            "the chosen pair is commonly confused; never score, grade, or "
            "diagnose a child."
        ),
        "app_title": "Want an optional guided Bopomofo app?",
        "app_text": (
            "Lumi Bopomofo is optional. Its current App Store listing describes "
            "an app designed for roughly ages 4–7 with four play modes — "
            "listening and choosing the symbol, finger tracing, tones, and "
            "initial+medial+final blending — 37 collectible Bopomofo friends, a "
            "free download with in-app purchases, no ads, no subscription, no "
            "signup, and progress stored on-device with a Chinese/English "
            "interface. Verify the current listing before deciding, since "
            "features can change. These printable cards work fully without the "
            "app."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "faq_title": "Bopomofo symbol contrast card questions",
        "faq": (
            (
                "Does this tool assess, score, or diagnose my child?",
                "No. It only turns two symbols you choose into printable "
                "finding, pointing, and tracing prompts; it never scores, "
                "grades, or diagnoses anyone.",
            ),
            (
                "Does picking a pair mean those symbols are commonly confused?",
                "No. This tool never makes that claim. It only uses whichever "
                "two symbols you personally selected.",
            ),
            (
                "Does this page collect my child's name, age, school, or any "
                "personal data?",
                "No. It only accepts your two chosen symbols, an activity mode, "
                "and a card count; nothing is sent anywhere or stored.",
            ),
            (
                "Where can I check official Bopomofo stroke order?",
                "Use Taiwan's Ministry of Education stroke-order portal linked "
                "on this page; this tool does not reproduce official stroke "
                "order itself.",
            ),
            (
                "Is this the Lumi Bopomofo app?",
                "No. This is a free, independent web tool. Lumi Bopomofo is a "
                "separate, optional app you can check on the App Store.",
            ),
        ),
        "footer": (
            "Private chosen symbols only · no child data · no assessment · no "
            "common-confusion claim"
        ),
        "index_title": "Private Bopomofo Symbol Contrast Cards",
        "index_description": (
            "Pick any two Zhuyin symbols and generate free printable finding, "
            "pointing, and tracing cards — no account, no child data, no "
            "assessment."
        ),
        "inline_link_label": (
            "Free Bopomofo symbol contrast card generator (no assessment)"
        ),
    },
    "es-ES": {
        "title": (
            "Tarjetas privadas de contraste de símbolos Bopomofo | Herramienta "
            "Zhuyin gratis para imprimir"
        ),
        "description": (
            "Elige dos símbolos Bopomofo (Zhuyin) cualquiera y genera tarjetas "
            "de práctica gratis para imprimir, pensadas para encontrarlos, "
            "señalarlos y trazarlos — sin cuenta, sin datos del menor, sin "
            "evaluación ni afirmación de confusión habitual."
        ),
        "tools": "Herramientas gratis",
        "switch": "English",
        "eyebrow": "Gratis · sin cuenta · sin evaluación",
        "heading": "Tarjetas privadas de contraste de símbolos Bopomofo",
        "lead": (
            "Elige dos símbolos Zhuyin cualquiera que tu familia quiera "
            "comparar y genera tarjetas de práctica para imprimir que piden a "
            "tu hijo/a encontrar, señalar o trazar cada uno. Esta herramienta "
            "nunca afirma que el par elegido se confunde habitualmente, y "
            "nunca puntúa, diagnostica ni perfila a ningún niño."
        ),
        "badges": (
            "Sin nombre, edad, colegio ni cuenta del menor",
            "Sin puntuación, nota ni diagnóstico de ningún tipo",
            "Tu par elegido nunca se llama «confusión habitual»",
            "El trazo oficial permanece en el sitio del MOE de Taiwán",
        ),
        "planner": "Crea tus tarjetas de contraste para imprimir",
        "planner_intro": (
            "Elige dos símbolos distintos, un modo de actividad y cuántas "
            "tarjetas imprimir. Esta página nunca pide el nombre, la edad, el "
            "colegio, una foto, la caligrafía, la voz ni ningún otro dato "
            "personal de tu hijo/a."
        ),
        "symbol_a_label": "Primer símbolo Zhuyin a contrastar",
        "symbol_b_label": "Segundo símbolo Zhuyin a contrastar",
        "activity_mode_label": "Modo de actividad",
        "activity_mode_options": {
            "visual": "Buscar y señalar (visual)",
            "trace": "Trazar y comparar",
            "mixed": "Mixto (alternando)",
        },
        "card_count_label": "Número de tarjetas a generar (4 a 12)",
        "update": "Actualizar tarjetas para imprimir",
        "invalid_input": (
            "Elige dos símbolos distintos y valores dentro de los rangos "
            "admitidos indicados arriba."
        ),
        "result_count_label": "Tarjetas generadas",
        "print_label": "Imprimir estas tarjetas",
        "prompt_visual": (
            "Encuentra y señala cada {target} en esta fila (también contiene "
            "{other})."
        ),
        "prompt_trace": (
            "Traza {target} con cuidado y luego compáralo con {other}, que "
            "está justo al lado."
        ),
        "compare_label": "Comparar con:",
        "card_label": "Tarjeta",
        "boundary_title": "Lo que esta herramienta no hace",
        "boundary_text": (
            "Esta herramienta no evalúa, puntúa, califica ni diagnostica a "
            "ningún niño, y nunca afirma que los dos símbolos que elegiste se "
            "confundan habitualmente. Solo convierte el par que tú mismo/a "
            "elegiste en indicaciones imprimibles para buscar, señalar y "
            "trazar."
        ),
        "independence_notice": (
            "Esta es una herramienta web gratuita e independiente. No es la "
            "app Lumi Bopomofo ni una herramienta de diagnóstico o evaluación "
            "de ningún tipo."
        ),
        "sources_title": "Fuentes oficiales sobre Bopomofo",
        "sources_intro": (
            "Estos datos y enlaces proceden del Ministerio de Educación de "
            "Taiwán y del Consorcio Unicode, no de este sitio."
        ),
        "source_labels": (
            "Portal oficial de trazo de Bopomofo del MOE de Taiwán",
            "Lista oficial de nombres Bopomofo de Unicode",
            "Tabla oficial de Bopomofo de Unicode (PDF)",
        ),
        "moe_check_label": "Consulta el trazo oficial de tus símbolos elegidos",
        "moe_check_note": (
            "Esta herramienta enlaza con el portal oficial del Ministerio de "
            "Educación en lugar de reproducir animaciones de trazo por sí "
            "misma."
        ),
        "unicode_note": (
            "Los nombres de carácter Unicode, como BOPOMOFO LETTER B, son "
            "identificadores técnicos para distinguir símbolos; no son guías "
            "de pronunciación."
        ),
        "how_it_works_title": "Cómo se generan estas tarjetas",
        "how_it_works_intro": (
            "La generación de tarjetas es un diseño fijo y determinista "
            "creado por este sitio, no una actividad adaptativa ni "
            "personalizada por IA."
        ),
        "how_it_works_list": (
            "Elige dos cualesquiera de las 37 letras Bopomofo básicas (de ㄅ a "
            "ㄩ); el par es únicamente el que tú elegiste, nunca una "
            "sugerencia de este sitio.",
            "Elige tarjetas visuales para buscar y señalar el símbolo "
            "objetivo, tarjetas de trazo para trazarlo y compararlo con el "
            "otro símbolo, o el modo mixto para alternar ambas actividades.",
            "Define cuántas tarjetas generar, de 4 a 12; el símbolo objetivo "
            "alterna entre tus dos símbolos elegidos en cada tarjeta.",
            "Imprime las tarjetas y practica sin conexión; nada de tu sesión "
            "de práctica se envía a ningún sitio ni se guarda en esta "
            "herramienta.",
            "Para el trazo oficial, usa el portal del Ministerio de Educación "
            "de Taiwán enlazado abajo en lugar de confiar en la animación de "
            "cualquier app o sitio web.",
        ),
        "webmcp_source": (
            "Vista previa de la API imperativa Chrome WebMCP (sujeta a "
            "cambios)"
        ),
        "webmcp_description": (
            "Crea tarjetas privadas y deterministas de contraste de símbolos "
            "Bopomofo a partir de dos símbolos elegidos, un modo de actividad "
            "y un número de tarjetas. Nunca recibe el nombre, la edad, el "
            "curso, el colegio, la ubicación, una foto, la caligrafía, la voz, "
            "el historial de respuestas, una puntuación o una cuenta de un "
            "menor; nunca afirma que el par elegido se confunda "
            "habitualmente; nunca puntúa, califica ni diagnostica a un niño."
        ),
        "app_title": "¿Quieres una app Bopomofo guiada opcional?",
        "app_text": (
            "Lumi Bopomofo es opcional. Su ficha actual de App Store describe "
            "una app pensada para edades de entre 4 y 7 años aproximadamente, "
            "con cuatro modos de juego —escuchar y elegir el símbolo, trazado "
            "con el dedo, tonos, y combinación de inicial+medial+final—, 37 "
            "amigos Bopomofo coleccionables, descarga gratuita con compras "
            "integradas, sin anuncios, sin suscripción, sin registro, y "
            "progreso guardado en el dispositivo con interfaz en chino/inglés. "
            "Verifica la ficha actual antes de decidir, ya que las funciones "
            "pueden cambiar. Estas tarjetas para imprimir funcionan por "
            "completo sin la app."
        ),
        "app_cta": "Ver Lumi Bopomofo en la App Store",
        "faq_title": "Preguntas sobre las tarjetas de contraste de Bopomofo",
        "faq": (
            (
                "¿Esta herramienta evalúa, puntúa o diagnostica a mi hijo/a?",
                "No. Solo convierte dos símbolos que elijas en indicaciones "
                "imprimibles para buscar, señalar y trazar; nunca puntúa, "
                "califica ni diagnostica a nadie.",
            ),
            (
                "¿Elegir un par significa que esos símbolos se confunden "
                "habitualmente?",
                "No. Esta herramienta nunca hace esa afirmación. Solo usa los "
                "dos símbolos que tú mismo/a hayas seleccionado.",
            ),
            (
                "¿Esta página recopila el nombre, la edad, el colegio o "
                "cualquier dato personal de mi hijo/a?",
                "No. Solo acepta tus dos símbolos elegidos, un modo de "
                "actividad y un número de tarjetas; nada se envía ni se "
                "guarda en ningún sitio.",
            ),
            (
                "¿Dónde puedo consultar el trazo oficial de Bopomofo?",
                "Usa el portal de trazo oficial del Ministerio de Educación "
                "de Taiwán enlazado en esta página; esta herramienta no "
                "reproduce el trazo oficial por sí misma.",
            ),
            (
                "¿Es esta la app Lumi Bopomofo?",
                "No. Esta es una herramienta web gratuita e independiente. "
                "Lumi Bopomofo es una app aparte y opcional que puedes "
                "consultar en la App Store.",
            ),
        ),
        "footer": (
            "Solo símbolos elegidos privados · sin datos del menor · sin "
            "evaluación · sin afirmación de confusión habitual"
        ),
        "index_title": "Tarjetas privadas de contraste de símbolos Bopomofo",
        "index_description": (
            "Elige dos símbolos Zhuyin cualquiera y genera tarjetas gratis "
            "para imprimir, pensadas para encontrarlos, señalarlos y "
            "trazarlos — sin cuenta, sin datos del menor, sin evaluación."
        ),
        "inline_link_label": (
            "Generador gratis de tarjetas de contraste Bopomofo (sin "
            "evaluación)"
        ),
    },
    "pt-BR": {
        "title": (
            "Cartões privados de contraste de símbolos Bopomofo | Ferramenta "
            "Zhuyin grátis para imprimir"
        ),
        "description": (
            "Escolha dois símbolos Bopomofo (Zhuyin) quaisquer e gere cartões "
            "de prática grátis para imprimir, para encontrar, apontar e "
            "traçar cada um — sem conta, sem dados da criança, sem avaliação "
            "nem afirmação de confusão comum."
        ),
        "tools": "Ferramentas grátis",
        "switch": "English",
        "eyebrow": "Grátis · sem conta · sem avaliação",
        "heading": "Cartões privados de contraste de símbolos Bopomofo",
        "lead": (
            "Escolha dois símbolos Zhuyin quaisquer que sua família queira "
            "comparar e gere cartões de prática para imprimir que pedem para "
            "seu filho(a) encontrar, apontar ou traçar cada um. Esta "
            "ferramenta nunca afirma que o par escolhido é comumente "
            "confundido, e nunca pontua, diagnostica ou perfila uma criança."
        ),
        "badges": (
            "Sem nome, idade, escola ou conta da criança",
            "Sem pontuação, nota ou diagnóstico de qualquer tipo",
            "Seu par escolhido nunca é chamado de confusão comum",
            "O traçado oficial permanece no site do MOE de Taiwan",
        ),
        "planner": "Crie seus cartões de contraste para imprimir",
        "planner_intro": (
            "Escolha dois símbolos diferentes, um modo de atividade e "
            "quantos cartões imprimir. Esta página nunca pede o nome, a "
            "idade, a escola, uma foto, a caligrafia, a voz nem qualquer "
            "outro dado pessoal do seu filho(a)."
        ),
        "symbol_a_label": "Primeiro símbolo Zhuyin para contrastar",
        "symbol_b_label": "Segundo símbolo Zhuyin para contrastar",
        "activity_mode_label": "Modo de atividade",
        "activity_mode_options": {
            "visual": "Encontrar e apontar (visual)",
            "trace": "Traçar e comparar",
            "mixed": "Misto (alternando)",
        },
        "card_count_label": "Número de cartões a gerar (4 a 12)",
        "update": "Atualizar cartões para imprimir",
        "invalid_input": (
            "Escolha dois símbolos diferentes e valores dentro dos limites "
            "aceitos indicados acima."
        ),
        "result_count_label": "Cartões gerados",
        "print_label": "Imprimir estes cartões",
        "prompt_visual": (
            "Encontre e aponte para cada {target} nesta fileira (ela também "
            "contém {other})."
        ),
        "prompt_trace": (
            "Trace {target} com cuidado e depois compare com {other}, que "
            "está logo ao lado."
        ),
        "compare_label": "Comparar com:",
        "card_label": "Cartão",
        "boundary_title": "O que esta ferramenta não faz",
        "boundary_text": (
            "Esta ferramenta não avalia, pontua, classifica nem diagnostica "
            "uma criança, e nunca afirma que os dois símbolos escolhidos são "
            "comumente confundidos. Ela apenas transforma o par que você "
            "mesmo(a) escolheu em instruções imprimíveis de encontrar, "
            "apontar e traçar."
        ),
        "independence_notice": (
            "Esta é uma ferramenta web gratuita e independente. Ela não é o "
            "app Lumi Bopomofo, nem uma ferramenta de diagnóstico ou "
            "avaliação de qualquer tipo."
        ),
        "sources_title": "Fontes oficiais sobre Bopomofo",
        "sources_intro": (
            "Estes dados e links vêm do Ministério da Educação de Taiwan e "
            "do Consórcio Unicode, não deste site."
        ),
        "source_labels": (
            "Portal oficial de traçado Bopomofo do MOE de Taiwan",
            "Lista oficial de nomes Bopomofo da Unicode",
            "Tabela oficial de Bopomofo da Unicode (PDF)",
        ),
        "moe_check_label": "Confira o traçado oficial dos símbolos escolhidos",
        "moe_check_note": (
            "Esta ferramenta apenas cria um link para o portal oficial do "
            "Ministério da Educação em vez de reproduzir animações de "
            "traçado."
        ),
        "unicode_note": (
            "Os nomes de caractere Unicode, como BOPOMOFO LETTER B, são "
            "identificadores técnicos usados para diferenciar símbolos; não "
            "são guias de pronúncia."
        ),
        "how_it_works_title": "Como estes cartões são gerados",
        "how_it_works_intro": (
            "A geração de cartões é um layout fixo e determinístico criado "
            "por este site, não uma atividade adaptativa ou personalizada "
            "por IA."
        ),
        "how_it_works_list": (
            "Escolha duas quaisquer das 37 letras Bopomofo básicas (de ㄅ a "
            "ㄩ); o par é apenas o que você escolheu, nunca uma sugestão "
            "deste site.",
            "Escolha cartões visuais para encontrar e apontar o símbolo "
            "alvo, cartões de traçado para traçá-lo e compará-lo com o "
            "outro símbolo, ou o modo misto para alternar as duas "
            "atividades.",
            "Defina quantos cartões gerar, de 4 a 12; o símbolo alvo alterna "
            "entre seus dois símbolos escolhidos em cada cartão.",
            "Imprima os cartões e pratique offline; nada da sua sessão de "
            "prática é enviado a qualquer lugar nem armazenado por esta "
            "ferramenta.",
            "Para o traçado oficial, use o portal do Ministério da Educação "
            "de Taiwan vinculado abaixo em vez de confiar na animação de "
            "qualquer app ou site.",
        ),
        "webmcp_source": (
            "Prévia da API imperativa Chrome WebMCP (sujeita a mudanças)"
        ),
        "webmcp_description": (
            "Crie cartões privados e determinísticos de contraste de "
            "símbolos Bopomofo a partir de dois símbolos escolhidos, um modo "
            "de atividade e um número de cartões. Nunca recebe o nome, a "
            "idade, a série, a escola, a localização, uma foto, a "
            "caligrafia, a voz, o histórico de respostas, uma pontuação ou "
            "uma conta de uma criança; nunca afirma que o par escolhido é "
            "comumente confundido; nunca pontua, classifica ou diagnostica "
            "uma criança."
        ),
        "app_title": "Quer um app Bopomofo guiado opcional?",
        "app_text": (
            "O Lumi Bopomofo é opcional. Sua ficha atual na App Store "
            "descreve um app pensado para idades de cerca de 4 a 7 anos, com "
            "quatro modos de jogo — ouvir e escolher o símbolo, traçado com "
            "o dedo, tons, e combinação de inicial+medial+final —, 37 amigos "
            "Bopomofo colecionáveis, download grátis com compras no app, sem "
            "anúncios, sem assinatura, sem cadastro, e progresso salvo no "
            "aparelho com interface em chinês/inglês. Confira a ficha atual "
            "antes de decidir, pois os recursos podem mudar. Estes cartões "
            "para imprimir funcionam totalmente sem o app."
        ),
        "app_cta": "Ver Lumi Bopomofo na App Store",
        "faq_title": "Perguntas sobre os cartões de contraste Bopomofo",
        "faq": (
            (
                "Esta ferramenta avalia, pontua ou diagnostica meu filho(a)?",
                "Não. Ela apenas transforma dois símbolos que você escolher "
                "em instruções imprimíveis de encontrar, apontar e traçar; "
                "nunca pontua, classifica ou diagnostica ninguém.",
            ),
            (
                "Escolher um par significa que esses símbolos são comumente "
                "confundidos?",
                "Não. Esta ferramenta nunca faz essa afirmação. Ela apenas "
                "usa os dois símbolos que você mesmo(a) selecionou.",
            ),
            (
                "Esta página coleta o nome, a idade, a escola ou qualquer "
                "dado pessoal do meu filho(a)?",
                "Não. Ela só aceita seus dois símbolos escolhidos, um modo "
                "de atividade e um número de cartões; nada é enviado nem "
                "armazenado em lugar algum.",
            ),
            (
                "Onde posso conferir o traçado oficial do Bopomofo?",
                "Use o portal de traçado oficial do Ministério da Educação "
                "de Taiwan vinculado nesta página; esta ferramenta não "
                "reproduz o traçado oficial por si mesma.",
            ),
            (
                "Este é o app Lumi Bopomofo?",
                "Não. Esta é uma ferramenta web gratuita e independente. O "
                "Lumi Bopomofo é um app separado e opcional que você pode "
                "conferir na App Store.",
            ),
        ),
        "footer": (
            "Apenas símbolos escolhidos privadamente · sem dados da criança "
            "· sem avaliação · sem afirmação de confusão comum"
        ),
        "index_title": "Cartões privados de contraste de símbolos Bopomofo",
        "index_description": (
            "Escolha dois símbolos Zhuyin quaisquer e gere cartões grátis "
            "para imprimir, para encontrar, apontar e traçar — sem conta, "
            "sem dados da criança, sem avaliação."
        ),
        "inline_link_label": (
            "Gerador grátis de cartões de contraste Bopomofo (sem avaliação)"
        ),
    },
    "de-DE": {
        "title": (
            "Private Bopomofo-Symbolkontrast-Karten | Kostenloses "
            "Zhuyin-Ausdrucktool"
        ),
        "description": (
            "Wähle zwei beliebige Bopomofo-(Zhuyin-)Symbole und erstelle "
            "kostenlose ausdruckbare Übungskarten zum Finden, Zeigen und "
            "Nachzeichnen — ohne Konto, ohne Kinderdaten, ohne Bewertung "
            "oder Behauptung häufiger Verwechslung."
        ),
        "tools": "Kostenlose Tools",
        "switch": "English",
        "eyebrow": "Kostenlos · kein Konto · keine Bewertung",
        "heading": "Private Bopomofo-Symbolkontrast-Karten",
        "lead": (
            "Wähle zwei beliebige Zhuyin-Symbole, die deine Familie "
            "vergleichen möchte, und erstelle ausdruckbare Übungskarten, die "
            "dein Kind bitten, jedes Symbol zu finden, darauf zu zeigen oder "
            "es nachzuzeichnen. Dieses Tool behauptet nie, dass das gewählte "
            "Paar häufig verwechselt wird, und es bewertet, diagnostiziert "
            "oder profiliert nie ein Kind."
        ),
        "badges": (
            "Kein Name, Alter, keine Schule oder Konto des Kindes",
            "Keine Punktzahl, Note oder Diagnose jeglicher Art",
            "Dein gewähltes Paar wird nie als häufig verwechselt bezeichnet",
            "Der offizielle Strichfolge bleibt auf der Seite des MOE Taiwan",
        ),
        "planner": "Erstelle deine ausdruckbaren Kontrastkarten",
        "planner_intro": (
            "Wähle zwei unterschiedliche Symbole, einen Aktivitätsmodus und "
            "wie viele Karten gedruckt werden sollen. Diese Seite fragt nie "
            "nach Name, Alter, Schule, Foto, Handschrift, Stimme oder "
            "anderen persönlichen Angaben deines Kindes."
        ),
        "symbol_a_label": "Erstes Zhuyin-Symbol zum Kontrastieren",
        "symbol_b_label": "Zweites Zhuyin-Symbol zum Kontrastieren",
        "activity_mode_label": "Aktivitätsmodus",
        "activity_mode_options": {
            "visual": "Finden & zeigen (visuell)",
            "trace": "Nachzeichnen & vergleichen",
            "mixed": "Gemischt (abwechselnd)",
        },
        "card_count_label": "Anzahl der zu erstellenden Karten (4–12)",
        "update": "Druckbare Karten aktualisieren",
        "invalid_input": (
            "Wähle zwei unterschiedliche Symbole und Werte innerhalb der "
            "oben angegebenen unterstützten Bereiche."
        ),
        "result_count_label": "Erstellte Karten",
        "print_label": "Diese Karten drucken",
        "prompt_visual": (
            "Finde und zeige auf jedes {target} in dieser Reihe (sie enthält "
            "auch {other})."
        ),
        "prompt_trace": (
            "Zeichne {target} sorgfältig nach und vergleiche es dann mit "
            "{other} daneben."
        ),
        "compare_label": "Vergleichen mit:",
        "card_label": "Karte",
        "boundary_title": "Was dieses Tool nicht tut",
        "boundary_text": (
            "Dieses Tool bewertet, benotet oder diagnostiziert kein Kind und "
            "behauptet nie, dass die beiden von dir gewählten Symbole häufig "
            "verwechselt werden. Es wandelt nur das von dir gewählte Paar in "
            "druckbare Finde-, Zeige- und Nachzeichenaufgaben um."
        ),
        "independence_notice": (
            "Dies ist ein kostenloses, unabhängiges Web-Tool. Es ist nicht "
            "die Lumi-Bopomofo-App und kein Diagnose- oder Bewertungswerkzeug "
            "jeglicher Art."
        ),
        "sources_title": "Offizielle Bopomofo-Quellen",
        "sources_intro": (
            "Diese Fakten und Links stammen vom taiwanischen "
            "Bildungsministerium und dem Unicode-Konsortium, nicht von "
            "dieser Website."
        ),
        "source_labels": (
            "Offizielles Bopomofo-Strichfolge-Portal des MOE Taiwan",
            "Offizielle Bopomofo-Namensliste von Unicode",
            "Offizielle Bopomofo-Zeichentabelle von Unicode (PDF)",
        ),
        "moe_check_label": (
            "Offizielle Strichfolge für deine gewählten Symbole prüfen"
        ),
        "moe_check_note": (
            "Dieses Tool verlinkt auf das offizielle Portal des "
            "Bildungsministeriums, statt Strichfolge-Animationen selbst "
            "nachzubilden."
        ),
        "unicode_note": (
            "Unicode-Zeichennamen wie BOPOMOFO LETTER B sind technische "
            "Bezeichner zur Unterscheidung von Symbolen; sie sind keine "
            "Ausspracheanleitung."
        ),
        "how_it_works_title": "Wie diese Karten erstellt werden",
        "how_it_works_intro": (
            "Die Kartenerstellung folgt einem festen, deterministischen "
            "Layout dieser Website, keiner adaptiven oder KI-personalisierten "
            "Aktivität."
        ),
        "how_it_works_list": (
            "Wähle zwei beliebige der 37 grundlegenden Bopomofo-Buchstaben "
            "(ㄅ bis ㄩ); das Paar ist nur das von dir gewählte, nie ein "
            "Vorschlag dieser Website.",
            "Wähle visuelle Karten, um das Zielsymbol zu finden und darauf "
            "zu zeigen, Nachzeichenkarten, um es nachzuzeichnen und mit dem "
            "anderen Symbol zu vergleichen, oder gemischt, um beide "
            "Aktivitäten abzuwechseln.",
            "Lege fest, wie viele Karten erstellt werden, von 4 bis 12; das "
            "Zielsymbol wechselt bei jeder Karte zwischen deinen beiden "
            "gewählten Symbolen.",
            "Drucke die Karten aus und übe offline; nichts aus deiner "
            "Übungssitzung wird irgendwohin gesendet oder von diesem Tool "
            "gespeichert.",
            "Nutze für die offizielle Strichfolge das unten verlinkte Portal "
            "des taiwanischen Bildungsministeriums, statt dich auf die "
            "Animation einer App oder Website zu verlassen.",
        ),
        "webmcp_source": (
            "Vorschau der Chrome-WebMCP-Imperative-API (kann sich noch "
            "ändern)"
        ),
        "webmcp_description": (
            "Erstellt private, deterministische Bopomofo-Symbolkontrast-"
            "Übungskarten aus zwei gewählten Symbolen, einem Aktivitätsmodus "
            "und einer Kartenanzahl. Erhält nie Name, Alter, Klasse, Schule, "
            "Standort, Foto, Handschrift, Stimme, Antwortverlauf, Punktzahl "
            "oder Konto eines Kindes; behauptet nie, dass das gewählte Paar "
            "häufig verwechselt wird; bewertet, benotet oder diagnostiziert "
            "nie ein Kind."
        ),
        "app_title": "Möchtest du eine optionale geführte Bopomofo-App?",
        "app_text": (
            "Lumi Bopomofo ist optional. Der aktuelle App-Store-Eintrag "
            "beschreibt eine App für etwa 4 bis 7 Jahre mit vier Spielmodi — "
            "Hören und Symbol wählen, Fingernachzeichnen, Töne sowie "
            "Anlaut+Medial+Endlaut-Verschmelzung —, 37 sammelbare "
            "Bopomofo-Freunde, kostenlosen Download mit In-App-Käufen, keine "
            "Werbung, kein Abo, keine Registrierung, und Fortschritt wird "
            "auf dem Gerät gespeichert mit chinesisch/englischer Oberfläche. "
            "Prüfe den aktuellen Eintrag vor der Entscheidung, da sich "
            "Funktionen ändern können. Diese Druckkarten funktionieren auch "
            "vollständig ohne die App."
        ),
        "app_cta": "Lumi Bopomofo im App Store ansehen",
        "faq_title": "Fragen zu Bopomofo-Symbolkontrast-Karten",
        "faq": (
            (
                "Bewertet, benotet oder diagnostiziert dieses Tool mein "
                "Kind?",
                "Nein. Es wandelt nur zwei von dir gewählte Symbole in "
                "druckbare Finde-, Zeige- und Nachzeichenaufgaben um; es "
                "bewertet, benotet oder diagnostiziert niemanden.",
            ),
            (
                "Bedeutet die Auswahl eines Paares, dass diese Symbole "
                "häufig verwechselt werden?",
                "Nein. Dieses Tool behauptet das nie. Es nutzt nur die "
                "beiden Symbole, die du selbst ausgewählt hast.",
            ),
            (
                "Sammelt diese Seite Name, Alter, Schule oder andere "
                "persönliche Daten meines Kindes?",
                "Nein. Sie akzeptiert nur deine beiden gewählten Symbole, "
                "einen Aktivitätsmodus und eine Kartenanzahl; nichts wird "
                "irgendwohin gesendet oder gespeichert.",
            ),
            (
                "Wo kann ich die offizielle Bopomofo-Strichfolge prüfen?",
                "Nutze das auf dieser Seite verlinkte offizielle "
                "Strichfolge-Portal des taiwanischen Bildungsministeriums; "
                "dieses Tool bildet die offizielle Strichfolge nicht selbst "
                "nach.",
            ),
            (
                "Ist das die Lumi-Bopomofo-App?",
                "Nein. Dies ist ein kostenloses, unabhängiges Web-Tool. Lumi "
                "Bopomofo ist eine separate, optionale App, die du im App "
                "Store ansehen kannst.",
            ),
        ),
        "footer": (
            "Nur privat gewählte Symbole · keine Kinderdaten · keine "
            "Bewertung · keine Behauptung häufiger Verwechslung"
        ),
        "index_title": "Private Bopomofo-Symbolkontrast-Karten",
        "index_description": (
            "Wähle zwei beliebige Zhuyin-Symbole und erstelle kostenlose "
            "ausdruckbare Karten zum Finden, Zeigen und Nachzeichnen — ohne "
            "Konto, ohne Kinderdaten, ohne Bewertung."
        ),
        "inline_link_label": (
            "Kostenloser Bopomofo-Symbolkontrast-Kartengenerator (keine "
            "Bewertung)"
        ),
    },
    "fr-FR": {
        "title": (
            "Cartes privées de contraste de symboles Bopomofo | Outil Zhuyin "
            "gratuit à imprimer"
        ),
        "description": (
            "Choisissez deux symboles Bopomofo (Zhuyin) et générez des "
            "cartes d'entraînement gratuites à imprimer pour les trouver, "
            "les montrer du doigt et les tracer — sans compte, sans donnée "
            "sur l'enfant, sans évaluation ni affirmation de confusion "
            "fréquente."
        ),
        "tools": "Outils gratuits",
        "switch": "English",
        "eyebrow": "Gratuit · sans compte · sans évaluation",
        "heading": "Cartes privées de contraste de symboles Bopomofo",
        "lead": (
            "Choisissez deux symboles Zhuyin que votre famille souhaite "
            "comparer, puis générez des cartes d'entraînement à imprimer qui "
            "demandent à votre enfant de trouver, montrer du doigt ou tracer "
            "chacun d'eux. Cet outil n'affirme jamais que la paire choisie "
            "est fréquemment confondue, et il ne note, ne diagnostique ni "
            "ne profile jamais un enfant."
        ),
        "badges": (
            "Aucun nom, âge, établissement ni compte de l'enfant",
            "Aucune note, évaluation ni diagnostic d'aucune sorte",
            "Votre paire choisie n'est jamais qualifiée de confusion "
            "fréquente",
            "Le tracé officiel reste sur le site du MOE de Taïwan",
        ),
        "planner": "Créez vos cartes de contraste à imprimer",
        "planner_intro": (
            "Choisissez deux symboles différents, un mode d'activité et le "
            "nombre de cartes à imprimer. Cette page ne demande jamais le "
            "nom, l'âge, l'établissement, une photo, l'écriture, la voix ni "
            "aucune autre donnée personnelle de votre enfant."
        ),
        "symbol_a_label": "Premier symbole Zhuyin à contraster",
        "symbol_b_label": "Second symbole Zhuyin à contraster",
        "activity_mode_label": "Mode d'activité",
        "activity_mode_options": {
            "visual": "Trouver et montrer (visuel)",
            "trace": "Tracer et comparer",
            "mixed": "Mixte (alterné)",
        },
        "card_count_label": "Nombre de cartes à générer (4 à 12)",
        "update": "Actualiser les cartes à imprimer",
        "invalid_input": (
            "Choisissez deux symboles différents et des valeurs dans les "
            "limites admises indiquées ci-dessus."
        ),
        "result_count_label": "Cartes générées",
        "print_label": "Imprimer ces cartes",
        "prompt_visual": (
            "Trouvez et montrez du doigt chaque {target} dans cette rangée "
            "(elle contient aussi {other})."
        ),
        "prompt_trace": (
            "Tracez {target} avec soin, puis comparez-le avec {other} juste "
            "à côté."
        ),
        "compare_label": "Comparer avec :",
        "card_label": "Carte",
        "boundary_title": "Ce que cet outil ne fait pas",
        "boundary_text": (
            "Cet outil n'évalue, ne note, ne classe ni ne diagnostique un "
            "enfant, et il n'affirme jamais que les deux symboles choisis "
            "sont fréquemment confondus. Il se contente de transformer la "
            "paire que vous avez vous-même choisie en consignes imprimables "
            "à trouver, montrer et tracer."
        ),
        "independence_notice": (
            "Ceci est un outil web gratuit et indépendant. Ce n'est pas "
            "l'application Lumi Bopomofo, ni un outil de diagnostic ou "
            "d'évaluation d'aucune sorte."
        ),
        "sources_title": "Sources officielles sur le Bopomofo",
        "sources_intro": (
            "Ces informations et liens proviennent du ministère de "
            "l'Éducation de Taïwan et du Consortium Unicode, pas de ce site."
        ),
        "source_labels": (
            "Portail officiel du tracé Bopomofo du MOE de Taïwan",
            "Liste officielle des noms Bopomofo d'Unicode",
            "Table officielle Bopomofo d'Unicode (PDF)",
        ),
        "moe_check_label": (
            "Vérifier le tracé officiel de vos symboles choisis"
        ),
        "moe_check_note": (
            "Cet outil renvoie vers le portail officiel du ministère de "
            "l'Éducation au lieu de reproduire lui-même les animations de "
            "tracé."
        ),
        "unicode_note": (
            "Les noms de caractères Unicode, comme BOPOMOFO LETTER B, sont "
            "des identifiants techniques servant à distinguer les symboles ; "
            "ce ne sont pas des guides de prononciation."
        ),
        "how_it_works_title": "Comment ces cartes sont générées",
        "how_it_works_intro": (
            "La génération des cartes suit une disposition fixe et "
            "déterministe créée par ce site, pas une activité adaptative ou "
            "personnalisée par IA."
        ),
        "how_it_works_list": (
            "Choisissez deux des 37 lettres Bopomofo de base (de ㄅ à ㄩ) ; "
            "la paire n'est que celle que vous avez choisie, jamais une "
            "suggestion de ce site.",
            "Choisissez les cartes visuelles pour trouver et montrer le "
            "symbole cible, les cartes de tracé pour le tracer et le "
            "comparer avec l'autre symbole, ou le mode mixte pour alterner "
            "les deux activités.",
            "Définissez le nombre de cartes à générer, de 4 à 12 ; le "
            "symbole cible alterne entre vos deux symboles choisis à chaque "
            "carte.",
            "Imprimez les cartes et entraînez-vous hors ligne ; rien de "
            "votre session d'entraînement n'est envoyé où que ce soit ni "
            "stocké par cet outil.",
            "Pour le tracé officiel, utilisez le portail du ministère de "
            "l'Éducation de Taïwan lié ci-dessous plutôt que de vous fier à "
            "l'animation d'une application ou d'un site quelconque.",
        ),
        "webmcp_source": (
            "Aperçu de l'API impérative Chrome WebMCP (susceptible de "
            "changer)"
        ),
        "webmcp_description": (
            "Crée des cartes privées et déterministes de contraste de "
            "symboles Bopomofo à partir de deux symboles choisis, d'un mode "
            "d'activité et d'un nombre de cartes. Ne reçoit jamais le nom, "
            "l'âge, la classe, l'établissement, la localisation, une photo, "
            "l'écriture, la voix, l'historique de réponses, une note ou un "
            "compte d'un enfant ; n'affirme jamais que la paire choisie est "
            "fréquemment confondue ; ne note, ne classe ni ne diagnostique "
            "jamais un enfant."
        ),
        "app_title": "Vous voulez une application Bopomofo guidée en option ?",
        "app_text": (
            "Lumi Bopomofo est optionnelle. Sa fiche actuelle sur l'App "
            "Store décrit une application conçue pour des enfants d'environ "
            "4 à 7 ans avec quatre modes de jeu — écouter et choisir le "
            "symbole, traçage au doigt, tons, et fusion "
            "initiale+médiane+finale —, 37 amis Bopomofo à collectionner, "
            "un téléchargement gratuit avec achats intégrés, sans publicité, "
            "sans abonnement, sans inscription, et une progression "
            "enregistrée sur l'appareil avec une interface chinois/anglais. "
            "Vérifiez la fiche actuelle avant de décider, car les "
            "fonctionnalités peuvent changer. Ces cartes à imprimer "
            "fonctionnent entièrement sans l'application."
        ),
        "app_cta": "Voir Lumi Bopomofo sur l'App Store",
        "faq_title": "Questions sur les cartes de contraste Bopomofo",
        "faq": (
            (
                "Cet outil évalue-t-il, note-t-il ou diagnostique-t-il mon "
                "enfant ?",
                "Non. Il se contente de transformer deux symboles que vous "
                "choisissez en consignes imprimables à trouver, montrer et "
                "tracer ; il ne note, ne classe ni ne diagnostique jamais "
                "personne.",
            ),
            (
                "Choisir une paire signifie-t-il que ces symboles sont "
                "fréquemment confondus ?",
                "Non. Cet outil n'affirme jamais cela. Il utilise "
                "uniquement les deux symboles que vous avez vous-même "
                "sélectionnés.",
            ),
            (
                "Cette page collecte-t-elle le nom, l'âge, l'établissement "
                "ou toute donnée personnelle de mon enfant ?",
                "Non. Elle n'accepte que vos deux symboles choisis, un mode "
                "d'activité et un nombre de cartes ; rien n'est envoyé où "
                "que ce soit ni stocké.",
            ),
            (
                "Où puis-je vérifier le tracé officiel du Bopomofo ?",
                "Utilisez le portail officiel du tracé du ministère de "
                "l'Éducation de Taïwan lié sur cette page ; cet outil ne "
                "reproduit pas lui-même le tracé officiel.",
            ),
            (
                "Est-ce l'application Lumi Bopomofo ?",
                "Non. Ceci est un outil web gratuit et indépendant. Lumi "
                "Bopomofo est une application distincte et optionnelle que "
                "vous pouvez consulter sur l'App Store.",
            ),
        ),
        "footer": (
            "Uniquement des symboles choisis en privé · aucune donnée sur "
            "l'enfant · aucune évaluation · aucune affirmation de confusion "
            "fréquente"
        ),
        "index_title": "Cartes privées de contraste de symboles Bopomofo",
        "index_description": (
            "Choisissez deux symboles Zhuyin et générez des cartes gratuites "
            "à imprimer pour les trouver, les montrer du doigt et les "
            "tracer — sans compte, sans donnée sur l'enfant, sans "
            "évaluation."
        ),
        "inline_link_label": (
            "Générateur gratuit de cartes de contraste Bopomofo (sans "
            "évaluation)"
        ),
    },
    "ja": {
        "title": "プライベートな注音記号対比カード | 無料の印刷用ジューイン(注音)ツール",
        "description": (
            "好きな注音記号(ジューイン)を2つ選ぶだけで、見つけて指さす練習と"
            "なぞり書き練習ができる無料の印刷用カードを作成できます。アカウン"
            "ト登録不要、お子さまの情報は一切収集せず、評価や「よく間違え"
            "る」といった主張も行いません。"
        ),
        "tools": "無料ツール",
        "switch": "繁體中文",
        "eyebrow": "無料 · アカウント不要 · 評価なし",
        "heading": "プライベートな注音記号対比カード",
        "lead": (
            "ご家族が比べたい注音記号を2つ選ぶと、それぞれを見つけて指さした"
            "り、なぞり書きしたりする印刷用の練習カードを作成できます。この"
            "ツールは選んだ組み合わせを「よく混同される」と主張することは決"
            "してなく、お子さまを採点したり診断したりプロファイリングしたり"
            "することもありません。"
        ),
        "badges": (
            "お子さまの氏名・年齢・学校名・アカウントは収集しません",
            "採点・成績評価・診断はいっさい行いません",
            "選んだ組み合わせを「よく混同される」とは表現しません",
            "公式の筆順は台湾MOE公式サイトにのみ掲載されています",
        ),
        "planner": "印刷用の対比カードを作成する",
        "planner_intro": (
            "異なる2つの記号、活動モード、印刷するカード枚数を選んでくださ"
            "い。このページはお子さまの氏名・年齢・学校名・写真・筆跡・音声"
            "など、いかなる個人情報も尋ねません。"
        ),
        "symbol_a_label": "対比する1つ目の注音記号",
        "symbol_b_label": "対比する2つ目の注音記号",
        "activity_mode_label": "活動モード",
        "activity_mode_options": {
            "visual": "見つけて指さす(視覚)",
            "trace": "なぞって比べる",
            "mixed": "ミックス(交互)",
        },
        "card_count_label": "作成するカード枚数(4〜12)",
        "update": "印刷用カードを更新",
        "invalid_input": (
            "異なる2つの記号と、上記の対応範囲内の値を選んでください。"
        ),
        "result_count_label": "作成されたカード枚数",
        "print_label": "このカードを印刷する",
        "prompt_visual": (
            "この列の中から{target}をすべて見つけて指さしましょう(この列に"
            "は{other}も含まれています)。"
        ),
        "prompt_trace": (
            "{target}を丁寧になぞってから、隣にある{other}と見比べてみまし"
            "ょう。"
        ),
        "compare_label": "比べる相手:",
        "card_label": "カード",
        "boundary_title": "このツールが行わないこと",
        "boundary_text": (
            "このツールはお子さまを評価・採点・成績評価・診断することはあ"
            "りません。また、選んだ2つの記号が「よく混同される」と主張する"
            "こともありません。あなた自身が選んだ組み合わせを、見つける・指"
            "さす・なぞるという印刷用の課題に変換するだけです。"
        ),
        "independence_notice": (
            "これは無料の独立したウェブツールです。Lumi注音星球アプリでは"
            "なく、いかなる種類の診断・評価ツールでもありません。"
        ),
        "sources_title": "注音に関する公式情報源",
        "sources_intro": (
            "これらの事実とリンクは台湾教育部(MOE)とUnicodeコンソーシア"
            "ムによるもので、当サイトによるものではありません。"
        ),
        "source_labels": (
            "台湾MOE公式の注音筆順ポータル",
            "Unicode公式の注音記号名一覧",
            "Unicode公式の注音記号表(PDF)",
        ),
        "moe_check_label": "選んだ記号の公式筆順を確認する",
        "moe_check_note": (
            "このツールは筆順アニメーションを自ら再現するのではなく、教育"
            "部の公式ポータルへのリンクを提供します。"
        ),
        "unicode_note": (
            "「BOPOMOFO LETTER B」のようなUnicode文字名は記号を区別する"
            "ための技術的な識別子であり、発音の指針ではありません。"
        ),
        "how_it_works_title": "このカードの作成方法",
        "how_it_works_intro": (
            "カードの作成は当サイトが定めた固定的で決定的なレイアウトによ"
            "るもので、適応型やAIによる個別最適化ではありません。"
        ),
        "how_it_works_list": (
            "37個の基本注音記号(ㄅからㄩまで)から任意の2つを選んでくださ"
            "い。組み合わせはあなたが選んだものだけであり、当サイトからの"
            "提案では決してありません。",
            "視覚カードでは対象記号を見つけて指さし、なぞりカードでは対象"
            "記号をなぞってもう一方の記号と見比べ、ミックスでは両方の活動"
            "を交互に行います。",
            "作成するカード枚数を4〜12枚の範囲で設定します。対象記号は毎"
            "枚、選んだ2つの記号の間で交互に切り替わります。",
            "カードを印刷してオフラインで練習してください。練習内容がど"
            "こかに送信されたり、このツールに保存されたりすることはありま"
            "せん。",
            "公式の筆順については、アプリやサイトのアニメーションに頼ら"
            "ず、下記の台湾教育部の公式ポータルをご利用ください。",
        ),
        "webmcp_source": (
            "Chrome WebMCP命令型APIのプレビュー(仕様は変更される可能性が"
            "あります)"
        ),
        "webmcp_description": (
            "選んだ2つの記号、活動モード、カード枚数から、プライベートで"
            "決定的な注音記号対比練習カードを作成します。子どもの氏名・年"
            "齢・学年・学校名・所在地・写真・筆跡・音声・回答履歴・スコア"
            "・アカウントを受け取ることは決してなく、選んだ組み合わせを"
            "「よく混同される」と主張することもなく、子どもを採点・評価・"
            "診断することもありません。"
        ),
        "app_title": "ガイド付きの注音アプリもオプションで利用しますか?",
        "app_text": (
            "Lumi注音星球はオプションです。現在のApp Store掲載情報による"
            "と、対象年齢はおおむね4〜7歳で、記号を聞いて選ぶ・指でなぞる"
            "・声調・声母+介母+韻母の組み合わせという4つの遊びモードがあ"
            "り、37体の集められる注音の仲間、アプリ内課金付きの無料ダウン"
            "ロード、広告なし、サブスクリプションなし、登録不要、進捗はデ"
            "バイス内に保存され、インターフェースは中国語/英語です。機能"
            "は変更される可能性があるため、決める前に最新の掲載情報をご確"
            "認ください。この印刷用カードはアプリなしでも完全に利用できま"
            "す。"
        ),
        "app_cta": "App StoreでLumi注音星球を見る",
        "faq_title": "注音記号対比カードに関するよくある質問",
        "faq": (
            (
                "このツールは子どもを評価・採点・診断しますか?",
                "いいえ。選んだ2つの記号を、見つける・指さす・なぞるとい"
                "う印刷用の課題に変換するだけで、誰かを採点・評価・診断す"
                "ることは決してありません。",
            ),
            (
                "組み合わせを選ぶことは、その記号がよく混同されるという意"
                "味ですか?",
                "いいえ。このツールがそのような主張をすることは決してあり"
                "ません。あなた自身が選んだ2つの記号を使うだけです。",
            ),
            (
                "このページは子どもの氏名・年齢・学校名などの個人情報を収"
                "集しますか?",
                "いいえ。選んだ2つの記号、活動モード、カード枚数だけを受"
                "け付けます。どこにも送信・保存されません。",
            ),
            (
                "注音の公式筆順はどこで確認できますか?",
                "このページにリンクされている台湾教育部の公式筆順ポータル"
                "をご利用ください。このツール自体が公式筆順を再現すること"
                "はありません。",
            ),
            (
                "これはLumi注音星球アプリですか?",
                "いいえ。これは無料の独立したウェブツールです。Lumi注音星"
                "球は別のオプションのアプリで、App Storeでご確認いただけ"
                "ます。",
            ),
        ),
        "footer": (
            "プライベートに選んだ記号のみ · 子どもの情報なし · 評価なし ·"
            " 「よく混同される」という主張なし"
        ),
        "index_title": "プライベートな注音記号対比カード",
        "index_description": (
            "好きな注音記号を2つ選び、見つけて指さす・なぞる練習ができる無"
            "料の印刷用カードを作成。アカウント不要、お子さまの情報収集な"
            "し、評価なし。"
        ),
        "inline_link_label": "無料の注音記号対比カード生成ツール(評価なし)",
    },
    "ko": {
        "title": "개인용 주음부호 대비 카드 | 무료 인쇄용 주음(注音) 도구",
        "description": (
            "원하는 주음부호(注音, Zhuyin) 두 개를 선택하면 찾기·가리키"
            "기·따라 쓰기 연습을 위한 무료 인쇄용 카드를 만들 수 있습니다. "
            "계정이 필요 없고 자녀 정보를 수집하지 않으며, 평가나 '자주 헷"
            "갈리는 조합'이라는 주장도 하지 않습니다."
        ),
        "tools": "무료 도구",
        "switch": "繁體中文",
        "eyebrow": "무료 · 계정 불필요 · 평가 없음",
        "heading": "개인용 주음부호 대비 카드",
        "lead": (
            "가족이 비교하고 싶은 주음부호 두 개를 선택하면, 자녀가 각 기호"
            "를 찾고 가리키거나 따라 쓰도록 요청하는 인쇄용 연습 카드를 만"
            "들 수 있습니다. 이 도구는 선택한 조합이 자주 헷갈린다고 주장하"
            "지 않으며, 자녀를 채점하거나 진단하거나 프로파일링하지 않습니"
            "다."
        ),
        "badges": (
            "자녀의 이름·나이·학교·계정 정보를 수집하지 않습니다",
            "어떤 형태의 점수·등급·진단도 없습니다",
            "선택한 조합을 '자주 헷갈림'이라고 표현하지 않습니다",
            "공식 필순은 대만 교육부(MOE) 사이트에만 있습니다",
        ),
        "planner": "인쇄용 대비 카드 만들기",
        "planner_intro": (
            "서로 다른 두 기호, 활동 모드, 인쇄할 카드 수를 선택하세요. 이 "
            "페이지는 자녀의 이름, 나이, 학교, 사진, 필적, 음성 등 어떤 개"
            "인정보도 요청하지 않습니다."
        ),
        "symbol_a_label": "대비할 첫 번째 주음부호",
        "symbol_b_label": "대비할 두 번째 주음부호",
        "activity_mode_label": "활동 모드",
        "activity_mode_options": {
            "visual": "찾아서 가리키기(시각)",
            "trace": "따라 쓰고 비교하기",
            "mixed": "혼합(번갈아 진행)",
        },
        "card_count_label": "생성할 카드 수(4~12)",
        "update": "인쇄용 카드 업데이트",
        "invalid_input": (
            "서로 다른 두 기호와 위에 표시된 지원 범위 내의 값을 선택하세"
            "요."
        ),
        "result_count_label": "생성된 카드 수",
        "print_label": "이 카드 인쇄하기",
        "prompt_visual": (
            "이 줄에서 {target}을(를) 모두 찾아 가리켜 보세요(이 줄에는 "
            "{other}도 포함되어 있습니다)."
        ),
        "prompt_trace": (
            "{target}을(를) 정성껏 따라 쓴 다음, 옆에 있는 {other}과(와) 비"
            "교해 보세요."
        ),
        "compare_label": "비교 대상:",
        "card_label": "카드",
        "boundary_title": "이 도구가 하지 않는 것",
        "boundary_text": (
            "이 도구는 자녀를 평가·채점·등급 매기기·진단하지 않으며, 선택"
            "한 두 기호가 자주 헷갈린다고 주장하지도 않습니다. 오직 사용자"
            "가 직접 선택한 조합을 찾기·가리키기·따라 쓰기용 인쇄 자료로 "
            "바꿀 뿐입니다."
        ),
        "independence_notice": (
            "이것은 무료의 독립적인 웹 도구입니다. Lumi 주음별(Lumi "
            "Bopomofo) 앱이 아니며, 어떤 종류의 진단 또는 평가 도구도 아닙"
            "니다."
        ),
        "sources_title": "주음부호 공식 출처",
        "sources_intro": (
            "이 정보와 링크는 대만 교육부(MOE)와 유니코드 컨소시엄에서 제"
            "공한 것이며, 이 사이트에서 만든 것이 아닙니다."
        ),
        "source_labels": (
            "대만 교육부(MOE) 공식 주음부호 필순 포털",
            "유니코드 공식 주음부호 이름 목록",
            "유니코드 공식 주음부호 표(PDF)",
        ),
        "moe_check_label": "선택한 기호의 공식 필순 확인하기",
        "moe_check_note": (
            "이 도구는 필순 애니메이션을 자체적으로 재현하지 않고, 교육부 "
            "공식 포털로 연결되는 링크만 제공합니다."
        ),
        "unicode_note": (
            "BOPOMOFO LETTER B와 같은 유니코드 문자 이름은 기호를 구분하"
            "기 위한 기술적 식별자이며, 발음 안내가 아닙니다."
        ),
        "how_it_works_title": "이 카드가 만들어지는 방식",
        "how_it_works_intro": (
            "카드 생성은 이 사이트가 정한 고정적이고 결정적인 레이아웃을 "
            "따르며, 적응형 활동이나 AI 개인화 활동이 아닙니다."
        ),
        "how_it_works_list": (
            "37개의 기본 주음부호(ㄅ부터 ㄩ까지) 중 아무 두 개나 선택하세"
            "요. 조합은 오직 사용자가 선택한 것일 뿐, 이 사이트가 제안하는 "
            "것이 아닙니다.",
            "시각 카드는 목표 기호를 찾아 가리키게 하고, 따라 쓰기 카드는 "
            "목표 기호를 따라 쓰고 다른 기호와 비교하게 하며, 혼합 모드는 "
            "두 활동을 번갈아 진행합니다.",
            "생성할 카드 수를 4~12 사이에서 설정하세요. 목표 기호는 카드마"
            "다 선택한 두 기호 사이에서 번갈아 나타납니다.",
            "카드를 인쇄해 오프라인으로 연습하세요. 연습 세션에 대한 어떤 "
            "정보도 어디로도 전송되거나 이 도구에 저장되지 않습니다.",
            "공식 필순은 앱이나 웹사이트의 애니메이션에 의존하지 말고 아래"
            "에 연결된 대만 교육부 포털을 이용하세요.",
        ),
        "webmcp_source": (
            "Chrome WebMCP 명령형 API 미리보기(변경될 수 있음)"
        ),
        "webmcp_description": (
            "선택한 두 기호, 활동 모드, 카드 수로 개인용 결정론적 주음부호 "
            "대비 연습 카드를 만듭니다. 자녀의 이름, 나이, 학년, 학교, 위"
            "치, 사진, 필적, 음성, 답변 기록, 점수, 계정 정보를 절대 받지 "
            "않으며, 선택한 조합이 자주 헷갈린다고 주장하지 않고, 자녀를 "
            "채점·등급 매기기·진단하지 않습니다."
        ),
        "app_title": "선택형 가이드 주음 앱도 함께 사용하시겠어요?",
        "app_text": (
            "Lumi 주음별은 선택 사항입니다. 현재 App Store 등록 정보에 따"
            "르면 대략 만 4~7세를 대상으로 하며, 듣고 기호 고르기·손가락으"
            "로 따라 쓰기·성조·초성+개음+운모 결합의 네 가지 놀이 모드, 수"
            "집 가능한 37개의 주음 친구, 인앱 구매가 있는 무료 다운로드, "
            "광고 없음, 구독 없음, 가입 없음, 기기에 저장되는 진행 상황과 "
            "중국어/영어 인터페이스를 제공합니다. 기능은 변경될 수 있으므"
            "로 결정하기 전에 최신 등록 정보를 확인하세요. 이 인쇄용 카드"
            "는 앱 없이도 완전히 사용할 수 있습니다."
        ),
        "app_cta": "App Store에서 Lumi 주음별 보기",
        "faq_title": "주음부호 대비 카드 관련 질문",
        "faq": (
            (
                "이 도구가 우리 아이를 평가·채점·진단하나요?",
                "아닙니다. 사용자가 선택한 두 기호를 찾기·가리키기·따라 쓰"
                "기용 인쇄 자료로 바꿀 뿐이며, 누구도 채점·등급 매기기·진"
                "단하지 않습니다.",
            ),
            (
                "조합을 선택하면 그 기호들이 자주 헷갈린다는 뜻인가요?",
                "아닙니다. 이 도구는 그런 주장을 절대 하지 않습니다. 사용"
                "자가 직접 선택한 두 기호만 사용할 뿐입니다.",
            ),
            (
                "이 페이지가 우리 아이의 이름, 나이, 학교 등 개인정보를 수"
                "집하나요?",
                "아닙니다. 선택한 두 기호, 활동 모드, 카드 수만 받으며, 어"
                "디에도 전송되거나 저장되지 않습니다.",
            ),
            (
                "주음부호의 공식 필순은 어디에서 확인할 수 있나요?",
                "이 페이지에 연결된 대만 교육부의 공식 필순 포털을 이용하"
                "세요. 이 도구 자체는 공식 필순을 재현하지 않습니다.",
            ),
            (
                "이것이 Lumi 주음별 앱인가요?",
                "아닙니다. 이것은 무료의 독립적인 웹 도구입니다. Lumi 주음"
                "별은 별도의 선택형 앱으로, App Store에서 확인할 수 있습니"
                "다.",
            ),
        ),
        "footer": (
            "개인적으로 선택한 기호만 사용 · 자녀 정보 없음 · 평가 없음 · "
            "'자주 헷갈림' 주장 없음"
        ),
        "index_title": "개인용 주음부호 대비 카드",
        "index_description": (
            "원하는 주음부호 두 개를 선택해 찾기·가리키기·따라 쓰기 연습"
            "용 무료 인쇄 카드를 만드세요 — 계정 불필요, 자녀 정보 없음, "
            "평가 없음."
        ),
        "inline_link_label": "무료 주음부호 대비 카드 생성기(평가 없음)",
    },
    "zh-Hant": {
        "title": "私人注音符號對比練習卡 | 免費可列印的注音工具",
        "description": (
            "自選任兩個注音符號,產生免費可列印的練習卡,協助尋找、指認與"
            "描寫每個符號——不需帳號、不收集孩子的個人資料,也不會宣稱這"
            "組符號「常被搞混」或進行任何評估。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 免帳號 · 不做評估",
        "heading": "私人注音符號對比練習卡",
        "lead": (
            "自選任兩個你家想要比較的注音符號,即可產生可列印的練習卡,讓"
            "孩子練習尋找、指認或描寫每一個符號。這個工具不會宣稱你選的這"
            "組符號「常被搞混」,也不會為孩子評分、診斷或建立任何檔案。"
        ),
        "badges": (
            "不收集孩子的姓名、年齡、學校或帳號",
            "不做任何形式的評分、等第或診斷",
            "不會把你選的組合說成「常見混淆組合」",
            "官方筆順只連結到台灣教育部官方網站",
        ),
        "planner": "建立你的可列印對比練習卡",
        "planner_intro": (
            "選擇兩個不同的符號、一種練習模式,以及要列印的張數。這個頁面"
            "永遠不會詢問孩子的姓名、年齡、學校、照片、筆跡、聲音或任何其"
            "他個人資料。"
        ),
        "symbol_a_label": "要對比的第一個注音符號",
        "symbol_b_label": "要對比的第二個注音符號",
        "activity_mode_label": "練習模式",
        "activity_mode_options": {
            "visual": "尋找與指認(視覺)",
            "trace": "描寫與比較",
            "mixed": "混合(輪流交替)",
        },
        "card_count_label": "要產生的卡片張數(4 到 12)",
        "update": "更新可列印練習卡",
        "invalid_input": "請選擇兩個不同的符號,並填入上方支援範圍內的數值。",
        "result_count_label": "已產生卡片數",
        "print_label": "列印這些卡片",
        "prompt_visual": "在這一排中找出並指認每一個「{target}」(這排也包含「{other}」)。",
        "prompt_trace": "仔細描寫「{target}」,再和旁邊的「{other}」比較看看有何不同。",
        "compare_label": "對照對象:",
        "card_label": "卡片",
        "boundary_title": "這個工具不會做的事",
        "boundary_text": (
            "這個工具不會為孩子做評估、評分、打等第或診斷,也絕不會宣稱你"
            "選的這兩個符號是「常見混淆組合」。它只會把你自己選的這組符號"
            "轉換成可列印的尋找、指認與描寫練習題。"
        ),
        "independence_notice": (
            "這是一個免費、獨立的網頁工具,並非 Lumi注音星球 App,也不是"
            "任何形式的診斷或評估工具。"
        ),
        "sources_title": "注音符號官方資料來源",
        "sources_intro": (
            "以下事實與連結來自台灣教育部與 Unicode 聯盟,並非本站自行提"
            "供。"
        ),
        "source_labels": (
            "台灣教育部官方注音筆順入口網站",
            "Unicode 官方注音符號名稱表",
            "Unicode 官方注音符號圖表(PDF)",
        ),
        "moe_check_label": "查詢你所選符號的官方筆順",
        "moe_check_note": (
            "本工具僅連結至教育部官方入口網站,並不會自行重製筆順動畫。"
        ),
        "unicode_note": (
            "像「BOPOMOFO LETTER B」這樣的 Unicode 字元名稱,只是用來區分"
            "符號的技術性識別碼,並非發音指引。"
        ),
        "how_it_works_title": "這些練習卡如何產生",
        "how_it_works_intro": (
            "卡片產生方式是本站設定的固定、決定性排版,並非會自我調整或以"
            "AI 個人化的活動。"
        ),
        "how_it_works_list": (
            "從 37 個基本注音符號(ㄅ到ㄩ)中任選兩個;這組符號只會是你自己"
            "選的,絕不是本站的建議。",
            "選擇視覺卡讓孩子尋找並指認目標符號,選擇描寫卡讓孩子描寫目標"
            "符號並與另一個符號比較,或選擇混合模式輪流交替兩種練習。",
            "設定要產生 4 到 12 張卡片;目標符號會在每張卡片上,於你選的兩"
            "個符號之間輪流交替。",
            "列印卡片後可離線練習;練習過程不會被傳送到任何地方,也不會被"
            "本工具儲存。",
            "官方筆順請使用下方連結的台灣教育部入口網站,而不要依賴任何"
            "App 或網站的動畫。",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽版(未來可能變動)",
        "webmcp_description": (
            "根據你選的兩個符號、練習模式與卡片張數,產生私人、可預測結果"
            "的注音符號對比練習卡。絕不接收孩子的姓名、年齡、年級、學校、"
            "所在地、照片、筆跡、聲音、作答紀錄、分數或帳號;絕不宣稱所選"
            "組合是常見混淆組合;絕不為孩子評分、打等第或診斷。"
        ),
        "app_title": "想搭配使用引導式的注音 App 嗎?",
        "app_text": (
            "Lumi注音星球是可有可無的選擇。目前 App Store 頁面說明,這款"
            "App 大約設計給 4 到 7 歲的孩子使用,提供聽音選符號、手指描寫、"
            "聲調練習,以及聲母+介音+韻母拼讀等四種遊戲模式,可收集 37 位"
            "注音好朋友,免費下載並提供App內購買,沒有廣告、沒有訂閱、不"
            "需註冊,進度儲存在裝置上,介面提供中文/英文。功能可能會調"
            "整,決定前請先確認目前的頁面內容。這份可列印練習卡完全不需要"
            "這款 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Lumi注音星球",
        "faq_title": "注音符號對比練習卡常見問題",
        "faq": (
            (
                "這個工具會為我的孩子做評估、評分或診斷嗎?",
                "不會。它只會把你選的兩個符號轉換成可列印的尋找、指認與描"
                "寫練習題,絕不會為任何人評分、打等第或診斷。",
            ),
            (
                "選了一組符號,是不是代表這兩個符號很常被搞混?",
                "不是。這個工具絕不會這樣宣稱,它只會使用你自己選擇的兩個"
                "符號。",
            ),
            (
                "這個頁面會收集我孩子的姓名、年齡、學校或其他個人資料嗎?",
                "不會。它只接受你選的兩個符號、練習模式與卡片張數;不會把"
                "任何資料傳送或儲存到任何地方。",
            ),
            (
                "哪裡可以查詢注音符號的官方筆順?",
                "請使用本頁連結的台灣教育部官方筆順入口網站;本工具本身不"
                "會重製官方筆順。",
            ),
            (
                "這是 Lumi注音星球 App 嗎?",
                "不是。這是一個免費、獨立的網頁工具。Lumi注音星球是另一款"
                "可自由選擇的 App,可在 App Store 查看。",
            ),
        ),
        "footer": "僅使用你私人選擇的符號 · 不收集孩子資料 · 不做評估 · 不宣稱常見混淆",
        "index_title": "私人注音符號對比練習卡",
        "index_description": (
            "自選任兩個注音符號,產生免費可列印的尋找、指認與描寫練習"
            "卡——不需帳號、不收集孩子資料、不做評估。"
        ),
        "inline_link_label": "免費注音符號對比練習卡產生器(不做評估)",
    },
    "zh-Hans": {
        "title": "私人注音符号对比练习卡 | 免费可打印的注音工具",
        "description": (
            "自选任意两个注音符号,即可生成免费可打印的练习卡,帮助寻"
            "找、指认与描摹每个符号——无需账号,不收集孩子的个人信息,也"
            "不会宣称这组符号「常被混淆」或进行任何评估。"
        ),
        "tools": "免费工具",
        "switch": "English",
        "eyebrow": "免费 · 无需账号 · 不做评估",
        "heading": "私人注音符号对比练习卡",
        "lead": (
            "自选任意两个你家想要比较的注音符号,即可生成可打印的练习"
            "卡,让孩子练习寻找、指认或描摹每一个符号。这个工具不会宣称你"
            "选的这组符号「常被混淆」,也不会为孩子评分、诊断或建立任何画"
            "像。"
        ),
        "badges": (
            "不收集孩子的姓名、年龄、学校或账号",
            "不做任何形式的评分、等级或诊断",
            "不会把你选的组合说成「常见混淆组合」",
            "官方笔顺仅链接到台湾教育部官方网站",
        ),
        "planner": "创建你的可打印对比练习卡",
        "planner_intro": (
            "选择两个不同的符号、一种练习模式,以及要打印的张数。此页面"
            "从不询问孩子的姓名、年龄、学校、照片、笔迹、声音或任何其他个"
            "人信息。"
        ),
        "symbol_a_label": "要对比的第一个注音符号",
        "symbol_b_label": "要对比的第二个注音符号",
        "activity_mode_label": "练习模式",
        "activity_mode_options": {
            "visual": "寻找与指认(视觉)",
            "trace": "描摹与比较",
            "mixed": "混合(轮流交替)",
        },
        "card_count_label": "要生成的卡片张数(4 到 12)",
        "update": "更新可打印练习卡",
        "invalid_input": "请选择两个不同的符号,并填入上方支持范围内的数值。",
        "result_count_label": "已生成卡片数",
        "print_label": "打印这些卡片",
        "prompt_visual": "在这一排中找出并指认每一个「{target}」(这排也包含「{other}」)。",
        "prompt_trace": "仔细描摹「{target}」,再和旁边的「{other}」比较看看有何不同。",
        "compare_label": "对照对象:",
        "card_label": "卡片",
        "boundary_title": "这个工具不会做的事",
        "boundary_text": (
            "这个工具不会为孩子做评估、评分、打等级或诊断,也绝不会宣称"
            "你选的这两个符号是「常见混淆组合」。它只会把你自己选的这组符"
            "号转换成可打印的寻找、指认与描摹练习题。"
        ),
        "independence_notice": (
            "这是一个免费、独立的网页工具,并非 Lumi注音星球 App,也不是"
            "任何形式的诊断或评估工具。"
        ),
        "sources_title": "注音符号官方资料来源",
        "sources_intro": (
            "以下事实与链接来自台湾教育部与 Unicode 联盟,并非本站自行提"
            "供。"
        ),
        "source_labels": (
            "台湾教育部官方注音笔顺门户网站",
            "Unicode 官方注音符号名称表",
            "Unicode 官方注音符号图表(PDF)",
        ),
        "moe_check_label": "查询你所选符号的官方笔顺",
        "moe_check_note": (
            "本工具仅链接至教育部官方门户网站,并不会自行重现笔顺动画。"
        ),
        "unicode_note": (
            "像「BOPOMOFO LETTER B」这样的 Unicode 字符名称,只是用来区分"
            "符号的技术性标识符,并非发音指南。"
        ),
        "how_it_works_title": "这些练习卡是如何生成的",
        "how_it_works_intro": (
            "卡片生成方式是本站设定的固定、确定性排版,并非会自我调整或以"
            "AI 个性化的活动。"
        ),
        "how_it_works_list": (
            "从 37 个基本注音符号(ㄅ到ㄩ)中任选两个;这组符号只会是你自己"
            "选的,绝不是本站的建议。",
            "选择视觉卡让孩子寻找并指认目标符号,选择描摹卡让孩子描摹目标"
            "符号并与另一个符号比较,或选择混合模式轮流交替两种练习。",
            "设置要生成 4 到 12 张卡片;目标符号会在每张卡片上,于你选的两"
            "个符号之间轮流交替。",
            "打印卡片后即可离线练习;练习过程不会被发送到任何地方,也不会"
            "被本工具存储。",
            "官方笔顺请使用下方链接的台湾教育部门户网站,而不要依赖任何"
            "App 或网站的动画。",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览版(未来可能变动)",
        "webmcp_description": (
            "根据你选的两个符号、练习模式与卡片张数,生成私人、结果可预测"
            "的注音符号对比练习卡。绝不接收孩子的姓名、年龄、年级、学校、"
            "所在地、照片、笔迹、声音、作答记录、分数或账号;绝不宣称所选"
            "组合是常见混淆组合;绝不为孩子评分、打等级或诊断。"
        ),
        "app_title": "想搭配使用引导式的注音 App 吗?",
        "app_text": (
            "Lumi注音星球是可选的搭配工具。目前 App Store 页面说明,这款"
            "App 大约面向 4 到 7 岁的孩子,提供听音选符号、手指描摹、声调"
            "练习,以及声母+介音+韵母拼读等四种游戏模式,可收集 37 位注音"
            "好朋友,免费下载并提供应用内购买,没有广告、没有订阅、无需注"
            "册,进度保存在设备上,界面提供中文/英文。功能可能会调整,决定"
            "前请先确认当前的页面内容。这份可打印练习卡完全不需要这款 "
            "App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Lumi注音星球",
        "faq_title": "注音符号对比练习卡常见问题",
        "faq": (
            (
                "这个工具会为我的孩子做评估、评分或诊断吗?",
                "不会。它只会把你选的两个符号转换成可打印的寻找、指认与描"
                "摹练习题,绝不会为任何人评分、打等级或诊断。",
            ),
            (
                "选了一组符号,是不是代表这两个符号很常被混淆?",
                "不是。这个工具绝不会这样宣称,它只会使用你自己选择的两个"
                "符号。",
            ),
            (
                "这个页面会收集我孩子的姓名、年龄、学校或其他个人信息吗?",
                "不会。它只接受你选的两个符号、练习模式与卡片张数;不会把"
                "任何信息发送或存储到任何地方。",
            ),
            (
                "哪里可以查询注音符号的官方笔顺?",
                "请使用本页链接的台湾教育部官方笔顺门户网站;本工具本身不"
                "会重现官方笔顺。",
            ),
            (
                "这是 Lumi注音星球 App 吗?",
                "不是。这是一个免费、独立的网页工具。Lumi注音星球是另一款"
                "可自由选择的 App,可在 App Store 查看。",
            ),
        ),
        "footer": "仅使用你私人选择的符号 · 不收集孩子信息 · 不做评估 · 不宣称常见混淆",
        "index_title": "私人注音符号对比练习卡",
        "index_description": (
            "自选任意两个注音符号,生成免费可打印的寻找、指认与描摹练习"
            "卡——无需账号、不收集孩子信息、不做评估。"
        ),
        "inline_link_label": "免费注音符号对比练习卡生成器(不做评估)",
    },
}


STYLE = r"""
:root{--ink:#21314a;--muted:#67738a;--line:#dfe5f0;--paper:#fff;--bg:#f3f6fb;--deep:#3949a3;--violet:#7566c8;--soft:#edf0ff;--warn:#fff6d8;--shadow:0 22px 60px rgba(47,57,108,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e9edf7 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--deep)}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cad2e4;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}.button.ghost{background:#fff;color:var(--deep);border:1px solid var(--line);box-shadow:none}
.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:18px}.print-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px;break-inside:avoid}.print-card header{font-weight:850;color:var(--deep);font-size:13px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;overflow-x:auto}.print-card .prompt{color:var(--ink);margin:8px 0 14px;white-space:nowrap;overflow-x:auto}
.symbol-row{display:flex;gap:8px;flex-wrap:wrap}.symbol-tile{display:inline-flex;align-items:center;justify-content:center;min-width:56px;min-height:56px;font-size:34px;border:2px solid #cad2e4;border-radius:14px;background:#fff}
.trace-box{display:flex;align-items:center;justify-content:center;min-height:150px;font-size:120px;border:3px dashed #9aa6c9;border-radius:20px;color:var(--ink)}.compare-note{display:flex;align-items:center;gap:10px;margin-top:10px;font-weight:760;white-space:nowrap;overflow-x:auto}.compare-tile{min-width:46px;min-height:46px;font-size:26px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#f4f5ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:720px){.card-grid{grid-template-columns:1fr}}
@media(max-width:560px){.controls{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.planner form,.planner .intro,.button,.app-card,.footer,.card,.faq{display:none!important}body{background:#fff}.planner{box-shadow:none;border:0;padding:0}.card-grid{box-shadow:none}.print-card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(
    document.getElementById("bopomofo-contrast-config").textContent);
  const form = document.getElementById("bopomofo-contrast-planner");
  const fields = {
    symbol_a: document.getElementById("symbol-a"),
    symbol_b: document.getElementById("symbol-b"),
    activity_mode: document.getElementById("activity-mode"),
    card_count: document.getElementById("card-count")
  };
  const summary = document.getElementById("result-summary");
  const grid = document.getElementById("card-grid");
  const printButton = document.getElementById("print-cards");

  const ROW_PATTERN = ["A", "B", "B", "A", "B", "A"];

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

  function fillPrompt(template, target, other) {
    return template.replace(/\{target\}/g, target).replace(/\{other\}/g, other);
  }

  function buildCards(input) {
    const symbolA = enumValue(input, "symbol_a");
    const symbolB = enumValue(input, "symbol_b");
    const mode = enumValue(input, "activity_mode");
    const count = integerValue(input, "card_count");
    if (symbolA === symbolB) {
      throw new RangeError(
        "symbol_a and symbol_b must be different symbols.");
    }
    const cards = [];
    for (let i = 0; i < count; i += 1) {
      const targetIsA = i % 2 === 0;
      const target = targetIsA ? symbolA : symbolB;
      const other = targetIsA ? symbolB : symbolA;
      const activity = mode === "mixed" ?
        (i % 2 === 0 ? "visual" : "trace") :
        mode;
      const card = {
        card_number: i + 1,
        activity,
        target_symbol: target,
        target_code_point: config.codePoints[target],
        target_unicode_name: config.unicodeNames[target],
        other_symbol: other,
        other_code_point: config.codePoints[other],
        other_unicode_name: config.unicodeNames[other],
        prompt: activity === "visual" ?
          fillPrompt(config.prompts.visual, target, other) :
          fillPrompt(config.prompts.trace, target, other)
      };
      if (activity === "visual") {
        card.row = ROW_PATTERN.map(
          (slot) => (slot === "A" ? symbolA : symbolB));
      }
      cards.push(card);
    }
    return {
      selected_inputs: {
        symbol_a: symbolA,
        symbol_a_code_point: config.codePoints[symbolA],
        symbol_a_unicode_name: config.unicodeNames[symbolA],
        symbol_b: symbolB,
        symbol_b_code_point: config.codePoints[symbolB],
        symbol_b_unicode_name: config.unicodeNames[symbolB],
        activity_mode: mode,
        activity_mode_label: config.labels.activityMode[mode],
        card_count: count
      },
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
    return buildCards(input);
  }

  function humanCardCount() {
    const raw = String(fields.card_count.value).trim();
    const value = raw === "" ? Number.NaN : Number(raw);
    const schema = config.inputSchema.properties.card_count;
    if (!Number.isInteger(value) ||
        value < schema.minimum ||
        value > schema.maximum) {
      throw new RangeError("card_count is outside the supported range.");
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
    const header = document.createElement("header");
    header.textContent = `${config.labels.card} ${card.card_number}`;
    const prompt = document.createElement("p");
    prompt.className = "prompt";
    prompt.textContent = card.prompt;
    article.appendChild(header);
    article.appendChild(prompt);
    if (card.activity === "visual") {
      const row = document.createElement("div");
      row.className = "symbol-row";
      for (const symbol of card.row) {
        const tile = document.createElement("span");
        tile.className = "symbol-tile";
        tile.textContent = symbol;
        row.appendChild(tile);
      }
      article.appendChild(row);
    } else {
      const traceBox = document.createElement("div");
      traceBox.className = "trace-box";
      traceBox.textContent = card.target_symbol;
      const compare = document.createElement("div");
      compare.className = "compare-note";
      const compareLabel = document.createElement("span");
      compareLabel.textContent = config.labels.compare;
      const compareSymbol = document.createElement("span");
      compareSymbol.className = "symbol-tile compare-tile";
      compareSymbol.textContent = card.other_symbol;
      compare.appendChild(compareLabel);
      compare.appendChild(compareSymbol);
      article.appendChild(traceBox);
      article.appendChild(compare);
    }
    return article;
  }

  function render() {
    let result;
    try {
      result = buildCards({
        symbol_a: fields.symbol_a.value,
        symbol_b: fields.symbol_b.value,
        activity_mode: fields.activity_mode.value,
        card_count: humanCardCount()
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        renderInvalid(config.invalidInput);
        return;
      }
      throw error;
    }
    summary.textContent = `${config.labels.resultCount}: ${result.cards.length}`;
    const fragment = document.createDocumentFragment();
    for (const card of result.cards) {
      fragment.appendChild(makeCardElement(card));
    }
    grid.replaceChildren(fragment);
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "create_private_bopomofo_symbol_contrast_cards",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_bopomofo_symbol_contrast_cards",
          is_not_assessment: true,
          no_score_grade_or_diagnosis: true,
          chosen_pair_not_claimed_common: true,
          no_child_data_received: true,
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


def symbol_options(selected: str) -> str:
    return "".join(
        '<option value="{value}"{chosen}>{value} ({code_point})</option>'.format(
            value=html.escape(symbol, quote=True),
            code_point=html.escape(code_point),
            chosen=" selected" if symbol == selected else "",
        )
        for symbol, code_point, _name in SYMBOLS
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    return {
        "type": "object",
        "properties": {
            "symbol_a": {
                "type": "string",
                "enum": list(SYMBOL_VALUES),
                "description": t["symbol_a_label"],
            },
            "symbol_b": {
                "type": "string",
                "enum": list(SYMBOL_VALUES),
                "description": t["symbol_b_label"],
            },
            "activity_mode": {
                "type": "string",
                "enum": list(ACTIVITY_MODES),
                "description": t["activity_mode_label"],
            },
            "card_count": {
                "type": "integer",
                "minimum": 4,
                "maximum": 12,
                "description": t["card_count_label"],
            },
        },
        "required": ["symbol_a", "symbol_b", "activity_mode", "card_count"],
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
    sources = (MOE_STROKE_ORDER, UNICODE_NAMES_LIST, UNICODE_CHART_PDF)
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
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_bopomofo_contrast_{locale.lower()}")
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
        "codePoints": dict(SYMBOL_CODE_POINTS),
        "unicodeNames": dict(SYMBOL_UNICODE_NAMES),
        "prompts": {
            "visual": t["prompt_visual"],
            "trace": t["prompt_trace"],
        },
        "labels": {
            "activityMode": dict(t["activity_mode_options"]),
            "card": t["card_label"],
            "compare": t["compare_label"],
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
        "applicationCategory": "EducationApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [*t["badges"], t["boundary_text"]],
        "citation": list(sources),
    }
    howto_schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": t["heading"],
        "description": t["how_it_works_intro"],
        "step": [
            {
                "@type": "HowToStep",
                "position": index + 1,
                "text": step,
            }
            for index, step in enumerate(t["how_it_works_list"])
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
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="bopomofo-contrast-planner"><div class="controls">
<div class="field"><label for="symbol-a">{html.escape(t["symbol_a_label"])}</label><select id="symbol-a">{symbol_options(DEFAULT_SYMBOL_A)}</select></div>
<div class="field"><label for="symbol-b">{html.escape(t["symbol_b_label"])}</label><select id="symbol-b">{symbol_options(DEFAULT_SYMBOL_B)}</select></div>
<div class="field"><label for="activity-mode">{html.escape(t["activity_mode_label"])}</label><select id="activity-mode">{options(t["activity_mode_options"])}</select></div>
<div class="field"><label for="card-count">{html.escape(t["card_count_label"])}</label><input id="card-count" type="number" min="4" max="12" step="1" value="6" required></div>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button> <button class="button ghost" type="button" id="print-cards">{html.escape(t["print_label"])}</button></p></form>
<p id="result-summary" class="note"></p>
<div id="card-grid" class="card-grid"></div>
</section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p>{html.escape(t["boundary_text"])}</p><p>{html.escape(t["independence_notice"])}</p></article><article class="card"><h2>{html.escape(t["moe_check_label"])}</h2><p>{html.escape(t["moe_check_note"])}</p><p><a href="{MOE_STROKE_ORDER}" rel="noopener">{html.escape(t["moe_check_label"])}</a></p></article><article class="card wide"><h2>{html.escape(t["how_it_works_title"])}</h2><p>{html.escape(t["how_it_works_intro"])}</p><ol>{how_it_works_items}</ol></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p>{html.escape(t["unicode_note"])}</p><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="bopomofo-contrast-config">{config_json}</script>
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
    "my-child-confuses-similar-looking-bopomofo-symbols-like-and-how-do-i-help.html",
    "my-child-learns-the-bopomofo-symbols-but-keeps-forgetting-them-how-do-i-help.html",
    "bopomofo-tracing-app-for-kids.html",
    "zhuyin-tracing-app-for-taiwanese-children.html",
    "how-to-learn-the-37-zhuyin-symbols-and-mandarin-tones-as-a-beginner.html",
    "how-can-i-check-my-child-s-zhuyin-skills-at-home-in-three-minutes.html",
)

INBOUND_LINK_CLASS = "bopomofo-contrast-cards-inline-link"
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

    Narrowly scoped to the exact 6 target slugs (`TARGET_ANSWER_SLUGS`)
    times the 9 supported locales -- exactly 19 real files are expected to
    exist. Any locale/slug combination whose file does not exist is
    skipped. Insertion is idempotent (skips files that already carry the
    marker class) and safe (skips files where no recognizable pre-CTA
    anchor can be found, rather than risking corrupt HTML). Broader
    Bopomofo pages, unsupported locales, and files without the exact CTA
    are never touched.
    """
    changed = 0
    for locale in ALT_LOCALES:
        directory = _answer_directory(pages, locale)
        t = COPY[locale]
        link_html = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-bopomofo-contrast-link="1" href="{canonical(locale)}" '
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
        print(f"bopomofo symbol contrast cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
