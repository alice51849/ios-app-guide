#!/usr/bin/env python3
"""Generate private deterministic Bopomofo flashcards in nine locales."""

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
from bopomofo_matching_pair_cards import (  # noqa: E402
    COPY as BASE_COPY,
    MOE_HANDBOOK,
    MOE_STROKE_ORDER,
    SYMBOL_VALUES as SOURCE_SYMBOL_VALUES,
    UNICODE_CHART_PDF,
    WEBMCP_SOURCE,
)
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-flashcards"
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
CONTENT_DATE = "2026-07-15"
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
CARD_DENSITIES = (4, 6, 8)
DEFAULT_DENSITY = 6
OFFICIAL_SYMBOLS = (
    "ㄅ",
    "ㄆ",
    "ㄇ",
    "ㄈ",
    "ㄉ",
    "ㄊ",
    "ㄋ",
    "ㄌ",
    "ㄍ",
    "ㄎ",
    "ㄏ",
    "ㄐ",
    "ㄑ",
    "ㄒ",
    "ㄓ",
    "ㄔ",
    "ㄕ",
    "ㄖ",
    "ㄗ",
    "ㄘ",
    "ㄙ",
    "ㄧ",
    "ㄨ",
    "ㄩ",
    "ㄚ",
    "ㄛ",
    "ㄜ",
    "ㄝ",
    "ㄞ",
    "ㄟ",
    "ㄠ",
    "ㄡ",
    "ㄢ",
    "ㄣ",
    "ㄤ",
    "ㄥ",
    "ㄦ",
)
if set(OFFICIAL_SYMBOLS) != set(SOURCE_SYMBOL_VALUES):
    raise RuntimeError("official and source Bopomofo symbol sets differ")
INITIALS = OFFICIAL_SYMBOLS[:21]
MEDIALS = OFFICIAL_SYMBOLS[21:24]
FINALS = OFFICIAL_SYMBOLS[24:]
CATEGORY_BY_SYMBOL = {
    **{symbol: "initial" for symbol in INITIALS},
    **{symbol: "medial" for symbol in MEDIALS},
    **{symbol: "final" for symbol in FINALS},
}
SYMBOL_ORDER = {symbol: index for index, symbol in enumerate(OFFICIAL_SYMBOLS)}
SOURCE_LABEL_INDEXES = (0, 1, 3)


COPY = {
    "en": {
        "title": "Printable Bopomofo Flashcard Generator | 37 Zhuyin Symbols",
        "description": (
            "Select any of the 37 official Bopomofo symbols and make free "
            "printable Zhuyin flashcards in a fixed official order. No account, "
            "child data, saved results, scoring, Pinyin guesses, or live shuffle."
        ),
        "eyebrow": "Free printable · official symbol order · no account",
        "heading": "Printable Bopomofo flashcards",
        "lead": (
            "Choose all 37 symbols, one official category, or an exact custom "
            "set. The same selection always creates the same clean cutting pages."
        ),
        "planner": "Choose the exact symbol set",
        "planner_intro": (
            "This page accepts only official Bopomofo symbols and print settings. "
            "It never asks for a child's name, age, school, voice, handwriting, "
            "answers, score, or progress."
        ),
        "labels": {
            "presets": "Quick symbol sets",
            "all": "All 37",
            "initials": "Initials 21",
            "medials": "Medials 3",
            "finals": "Finals 13",
            "symbols": "Tap symbols to include or remove",
            "density": "Cards per printed page",
            "category": "Category label on each card",
            "show": "Show",
            "hide": "Hide",
            "generate": "Build flashcards",
            "print": "Print these flashcards",
            "result": "{count} flashcards · {pages} print pages",
            "page": "Print page",
            "invalid": "Choose 1–37 official symbols and a supported print layout.",
            "toggle": "Toggle",
        },
        "categories": {
            "initial": "Initial",
            "medial": "Medial",
            "final": "Final",
        },
        "badges": (
            "All 37 official basic symbols",
            "Same selection, same ordered cards",
            "No child data, score, or diagnosis",
        ),
        "boundary": (
            "What these flashcards do—and do not do",
            (
                "They place selected official Bopomofo symbols on printable "
                "cutting cards. They do not supply Pinyin or example-word "
                "equivalents, play audio, listen, grade pronunciation, track "
                "answers, diagnose a need, or promise a learning result."
            ),
        ),
        "how": (
            "How the fixed card set is created",
            (
                "Choose a preset or tap the exact symbols you want.",
                "Selected symbols are returned once each in the official "
                "Ministry of Education order, never a live random shuffle.",
                "Choose 4, 6, or 8 cards per A4 page and decide whether the "
                "official category label should appear.",
            ),
        ),
        "use": (
            "A low-pressure adult-led way to use them",
            (
                "Print and cut only the symbols needed for the current activity.",
                "An adult can name a symbol using an official pronunciation "
                "source while the learner points, matches, or sorts.",
                "Keep the cards as an activity, not a score, rank, assessment, "
                "or diagnosis; stop when the learner wants to stop.",
            ),
        ),
        "webmcp_description": (
            "Return deterministic printable flashcard pages from 1–37 official "
            "Bopomofo symbols, page density, and category-label preference. "
            "Read-only: accepts no child profile, free text, answer, score, "
            "recording, assessment, diagnosis, or learning-outcome claim."
        ),
        "faq_title": "Printable Bopomofo flashcard questions",
        "faq": (
            (
                "Are all 37 basic Bopomofo symbols available?",
                "Yes. The presets use the 21 initials, 3 medials, and 13 finals "
                "in the official Ministry of Education order.",
            ),
            (
                "Does this page collect or save information about a child?",
                "No. It accepts only a fixed symbol list and print settings in "
                "the current page; nothing is uploaded or stored.",
            ),
            (
                "Why are there no Pinyin or example-word answers on the cards?",
                "A single Latin spelling or example word can mislead across "
                "contexts. These cards stay within the verified official symbol "
                "set and link to official sources for pronunciation and strokes.",
            ),
        ),
        "index": (
            "Printable Bopomofo Flashcards",
            (
                "Choose any of the 37 official Zhuyin symbols and print fixed, "
                "private cutting cards with no account, score, or live shuffle."
            ),
        ),
        "inline_link": "Make free printable Bopomofo flashcards",
        "footer": (
            "Official symbol set · no child data · no score · no pronunciation claim"
        ),
    },
    "es-ES": {
        "title": "Tarjetas Bopomofo para imprimir | 37 símbolos Zhuyin",
        "description": (
            "Selecciona cualquiera de los 37 símbolos Bopomofo oficiales y crea "
            "tarjetas Zhuyin gratis para imprimir en orden fijo. Sin cuenta, "
            "datos infantiles, resultados guardados, puntuación ni mezcla aleatoria."
        ),
        "eyebrow": "Gratis para imprimir · orden oficial · sin cuenta",
        "heading": "Tarjetas Bopomofo (Zhuyin) para imprimir",
        "lead": (
            "Elige los 37 símbolos, una categoría oficial o una selección exacta. "
            "La misma selección crea siempre las mismas hojas de recorte."
        ),
        "planner": "Elige el conjunto exacto de símbolos",
        "planner_intro": (
            "La página solo acepta símbolos Bopomofo oficiales y ajustes de "
            "impresión. Nunca pide nombre, edad, colegio, voz, escritura, "
            "respuestas, puntuación ni progreso de un menor."
        ),
        "labels": {
            "presets": "Conjuntos rápidos",
            "all": "Los 37",
            "initials": "Iniciales 21",
            "medials": "Mediales 3",
            "finals": "Finales 13",
            "symbols": "Toca para incluir o quitar símbolos",
            "density": "Tarjetas por página impresa",
            "category": "Categoría visible en cada tarjeta",
            "show": "Mostrar",
            "hide": "Ocultar",
            "generate": "Crear tarjetas",
            "print": "Imprimir estas tarjetas",
            "result": "{count} tarjetas · {pages} páginas",
            "page": "Página impresa",
            "invalid": "Elige entre 1 y 37 símbolos oficiales y un formato válido.",
            "toggle": "Alternar",
        },
        "categories": {
            "initial": "Inicial",
            "medial": "Medial",
            "final": "Final",
        },
        "badges": (
            "Los 37 símbolos básicos oficiales",
            "Misma selección, mismo orden",
            "Sin datos infantiles, nota ni diagnóstico",
        ),
        "boundary": (
            "Qué hacen estas tarjetas y qué no",
            (
                "Colocan los símbolos Bopomofo oficiales elegidos en tarjetas "
                "recortables. No añaden equivalencias Pinyin ni palabras de "
                "ejemplo, reproducen audio, escuchan, califican pronunciación, "
                "registran respuestas, diagnostican ni prometen resultados."
            ),
        ),
        "how": (
            "Cómo se crea el conjunto fijo",
            (
                "Elige un conjunto rápido o toca los símbolos exactos.",
                "Cada símbolo aparece una vez en el orden oficial del Ministerio "
                "de Educación de Taiwán, sin mezcla aleatoria en vivo.",
                "Elige 4, 6 u 8 tarjetas por hoja A4 y si aparece la categoría.",
            ),
        ),
        "use": (
            "Una actividad tranquila guiada por un adulto",
            (
                "Imprime y recorta solo los símbolos necesarios.",
                "Un adulto puede nombrar un símbolo con una fuente oficial "
                "mientras el alumno señala, empareja o clasifica.",
                "Úsalas como actividad, no como nota, clasificación, evaluación "
                "o diagnóstico; detente cuando el alumno quiera.",
            ),
        ),
        "webmcp_description": (
            "Devuelve páginas deterministas de tarjetas imprimibles a partir de "
            "1–37 símbolos Bopomofo oficiales, densidad y categoría. Solo lectura: "
            "sin perfiles infantiles, texto libre, respuestas, notas, grabaciones, "
            "evaluaciones, diagnósticos ni promesas de aprendizaje."
        ),
        "faq_title": "Preguntas sobre las tarjetas Bopomofo",
        "faq": (
            (
                "¿Están disponibles los 37 símbolos Bopomofo básicos?",
                "Sí. Los conjuntos incluyen 21 iniciales, 3 mediales y 13 finales "
                "en el orden oficial del Ministerio de Educación de Taiwán.",
            ),
            (
                "¿Se recopila o guarda información de un menor?",
                "No. Solo se usan la lista fija de símbolos y los ajustes de "
                "impresión en esta página; nada se sube ni se guarda.",
            ),
            (
                "¿Por qué no hay Pinyin ni palabras de ejemplo?",
                "Una única escritura latina o palabra puede resultar engañosa "
                "según el contexto. Las tarjetas se limitan al conjunto oficial "
                "verificado y enlazan fuentes oficiales.",
            ),
        ),
        "index": (
            "Tarjetas Bopomofo para imprimir",
            (
                "Elige cualquiera de los 37 símbolos Zhuyin oficiales e imprime "
                "tarjetas fijas y privadas, sin cuenta ni puntuación."
            ),
        ),
        "inline_link": "Crear tarjetas Bopomofo gratis para imprimir",
        "footer": (
            "Símbolos oficiales · sin datos infantiles · sin nota · sin afirmar pronunciación"
        ),
    },
    "pt-BR": {
        "title": "Cartões Bopomofo para imprimir | 37 símbolos Zhuyin",
        "description": (
            "Selecione qualquer um dos 37 símbolos Bopomofo oficiais e crie "
            "cartões Zhuyin gratuitos para imprimir em ordem fixa. Sem conta, "
            "dados infantis, resultados salvos, pontuação ou embaralhamento."
        ),
        "eyebrow": "Grátis para imprimir · ordem oficial · sem conta",
        "heading": "Cartões Bopomofo (Zhuyin) para imprimir",
        "lead": (
            "Escolha os 37 símbolos, uma categoria oficial ou uma seleção exata. "
            "A mesma seleção sempre gera as mesmas folhas para recortar."
        ),
        "planner": "Escolha o conjunto exato de símbolos",
        "planner_intro": (
            "A página aceita apenas símbolos Bopomofo oficiais e configurações "
            "de impressão. Nunca pede nome, idade, escola, voz, escrita, "
            "respostas, pontuação ou progresso de uma criança."
        ),
        "labels": {
            "presets": "Conjuntos rápidos",
            "all": "Todos os 37",
            "initials": "Iniciais 21",
            "medials": "Mediais 3",
            "finals": "Finais 13",
            "symbols": "Toque para incluir ou remover símbolos",
            "density": "Cartões por página impressa",
            "category": "Categoria em cada cartão",
            "show": "Mostrar",
            "hide": "Ocultar",
            "generate": "Criar cartões",
            "print": "Imprimir estes cartões",
            "result": "{count} cartões · {pages} páginas",
            "page": "Página impressa",
            "invalid": "Escolha de 1 a 37 símbolos oficiais e um formato válido.",
            "toggle": "Alternar",
        },
        "categories": {
            "initial": "Inicial",
            "medial": "Medial",
            "final": "Final",
        },
        "badges": (
            "Os 37 símbolos básicos oficiais",
            "Mesma seleção, mesma ordem",
            "Sem dados infantis, nota ou diagnóstico",
        ),
        "boundary": (
            "O que estes cartões fazem — e não fazem",
            (
                "Eles colocam os símbolos Bopomofo oficiais escolhidos em cartões "
                "recortáveis. Não fornecem equivalências em Pinyin nem palavras "
                "de exemplo, áudio, escuta, nota de pronúncia, registro de "
                "respostas, diagnóstico ou promessa de aprendizagem."
            ),
        ),
        "how": (
            "Como o conjunto fixo é criado",
            (
                "Escolha um conjunto rápido ou toque nos símbolos exatos.",
                "Cada símbolo aparece uma vez na ordem oficial do Ministério da "
                "Educação de Taiwan, sem embaralhamento aleatório.",
                "Escolha 4, 6 ou 8 cartões por folha A4 e se a categoria aparece.",
            ),
        ),
        "use": (
            "Uma atividade leve guiada por um adulto",
            (
                "Imprima e recorte somente os símbolos necessários.",
                "Um adulto pode nomear o símbolo com uma fonte oficial enquanto "
                "o aluno aponta, combina ou separa.",
                "Use como atividade, não como nota, ranking, avaliação ou "
                "diagnóstico; pare quando o aluno quiser.",
            ),
        ),
        "webmcp_description": (
            "Retorna páginas determinísticas de cartões imprimíveis usando 1–37 "
            "símbolos Bopomofo oficiais, densidade e categoria. Somente leitura: "
            "sem perfil infantil, texto livre, respostas, notas, gravações, "
            "avaliação, diagnóstico ou promessa de aprendizagem."
        ),
        "faq_title": "Dúvidas sobre cartões Bopomofo",
        "faq": (
            (
                "Os 37 símbolos Bopomofo básicos estão disponíveis?",
                "Sim. Os conjuntos usam 21 iniciais, 3 mediais e 13 finais na "
                "ordem oficial do Ministério da Educação de Taiwan.",
            ),
            (
                "A página coleta ou salva dados de uma criança?",
                "Não. Apenas a lista fixa de símbolos e as configurações de "
                "impressão são usadas nesta página; nada é enviado ou salvo.",
            ),
            (
                "Por que não há Pinyin nem palavras de exemplo?",
                "Uma única grafia latina ou palavra pode induzir ao erro conforme "
                "o contexto. Os cartões ficam no conjunto oficial verificado e "
                "indicam fontes oficiais.",
            ),
        ),
        "index": (
            "Cartões Bopomofo para imprimir",
            (
                "Escolha qualquer um dos 37 símbolos Zhuyin oficiais e imprima "
                "cartões fixos e privados, sem conta ou pontuação."
            ),
        ),
        "inline_link": "Criar cartões Bopomofo gratuitos para imprimir",
        "footer": (
            "Símbolos oficiais · sem dados infantis · sem nota · sem alegação de pronúncia"
        ),
    },
    "de-DE": {
        "title": "Bopomofo-Lernkarten zum Ausdrucken | 37 Zhuyin-Zeichen",
        "description": (
            "Wähle aus allen 37 offiziellen Bopomofo-Zeichen und erstelle "
            "kostenlose Zhuyin-Lernkarten in fester Reihenfolge. Ohne Konto, "
            "Kinderdaten, gespeicherte Ergebnisse, Bewertung oder Zufallsmischung."
        ),
        "eyebrow": "Kostenlos drucken · offizielle Reihenfolge · ohne Konto",
        "heading": "Bopomofo-(Zhuyin-)Lernkarten zum Ausdrucken",
        "lead": (
            "Wähle alle 37 Zeichen, eine offizielle Gruppe oder genau die "
            "gewünschten Zeichen. Dieselbe Auswahl erzeugt stets dieselben Bögen."
        ),
        "planner": "Genauen Zeichensatz auswählen",
        "planner_intro": (
            "Die Seite akzeptiert nur offizielle Bopomofo-Zeichen und "
            "Druckeinstellungen. Sie fragt nie nach Name, Alter, Schule, Stimme, "
            "Handschrift, Antworten, Punktzahl oder Fortschritt eines Kindes."
        ),
        "labels": {
            "presets": "Schnellauswahl",
            "all": "Alle 37",
            "initials": "Anlaute 21",
            "medials": "Mediale 3",
            "finals": "Auslaute 13",
            "symbols": "Zeichen antippen oder entfernen",
            "density": "Karten pro Druckseite",
            "category": "Gruppenname auf jeder Karte",
            "show": "Anzeigen",
            "hide": "Ausblenden",
            "generate": "Lernkarten erstellen",
            "print": "Diese Lernkarten drucken",
            "result": "{count} Karten · {pages} Druckseiten",
            "page": "Druckseite",
            "invalid": "Wähle 1–37 offizielle Zeichen und ein gültiges Layout.",
            "toggle": "Umschalten",
        },
        "categories": {
            "initial": "Anlaut",
            "medial": "Medial",
            "final": "Auslaut",
        },
        "badges": (
            "Alle 37 offiziellen Grundzeichen",
            "Gleiche Auswahl, gleiche Reihenfolge",
            "Keine Kinderdaten, Bewertung oder Diagnose",
        ),
        "boundary": (
            "Was diese Karten leisten — und was nicht",
            (
                "Sie setzen ausgewählte offizielle Bopomofo-Zeichen auf "
                "ausschneidbare Karten. Sie liefern keine Pinyin- oder "
                "Beispielwort-Entsprechungen, kein Audio, keine Ausspracheprüfung, "
                "keine Antwortspeicherung, Diagnose oder Lernerfolgszusage."
            ),
        ),
        "how": (
            "So entsteht der feste Kartensatz",
            (
                "Nutze die Schnellauswahl oder tippe die gewünschten Zeichen an.",
                "Jedes Zeichen erscheint einmal in der offiziellen Reihenfolge "
                "des taiwanischen Bildungsministeriums, ohne Zufallsmischung.",
                "Wähle 4, 6 oder 8 Karten je A4-Seite und den Gruppennamen.",
            ),
        ),
        "use": (
            "Eine entspannte, erwachsenengeleitete Nutzung",
            (
                "Drucke und schneide nur die aktuell benötigten Zeichen aus.",
                "Ein Erwachsener kann mit einer offiziellen Quelle vorsprechen, "
                "während der Lernende zeigt, zuordnet oder sortiert.",
                "Nutze die Karten als Aktivität, nicht als Note, Rang, Test oder "
                "Diagnose; beende sie auf Wunsch des Lernenden.",
            ),
        ),
        "webmcp_description": (
            "Gibt deterministische Druckseiten aus 1–37 offiziellen "
            "Bopomofo-Zeichen, Seitendichte und Gruppenanzeige zurück. Nur lesend: "
            "keine Kinderprofile, Freitexte, Antworten, Bewertungen, Aufnahmen, "
            "Tests, Diagnosen oder Lernversprechen."
        ),
        "faq_title": "Fragen zu Bopomofo-Lernkarten",
        "faq": (
            (
                "Sind alle 37 Bopomofo-Grundzeichen enthalten?",
                "Ja. Die Gruppen enthalten 21 Anlaute, 3 Mediale und 13 Auslaute "
                "in der offiziellen Reihenfolge des Bildungsministeriums.",
            ),
            (
                "Werden Informationen über ein Kind erfasst oder gespeichert?",
                "Nein. Nur die feste Zeichenliste und Druckeinstellungen werden "
                "auf dieser Seite genutzt; nichts wird hochgeladen oder gespeichert.",
            ),
            (
                "Warum fehlen Pinyin und Beispielwörter?",
                "Eine einzelne lateinische Schreibweise oder ein Beispielwort "
                "kann je nach Kontext irreführen. Die Karten bleiben beim "
                "verifizierten offiziellen Zeichensatz und verlinken Quellen.",
            ),
        ),
        "index": (
            "Bopomofo-Lernkarten zum Ausdrucken",
            (
                "Wähle aus 37 offiziellen Zhuyin-Zeichen und drucke feste, private "
                "Karten ohne Konto, Bewertung oder Zufallsmischung."
            ),
        ),
        "inline_link": "Kostenlose Bopomofo-Lernkarten erstellen",
        "footer": (
            "Offizielle Zeichen · keine Kinderdaten · keine Note · keine Aussprachebehauptung"
        ),
    },
    "fr-FR": {
        "title": "Cartes mémo Bopomofo à imprimer | 37 symboles Zhuyin",
        "description": (
            "Choisissez parmi les 37 symboles Bopomofo officiels et créez "
            "gratuitement des cartes Zhuyin à imprimer dans un ordre fixe. "
            "Sans compte, données d'enfant, résultat enregistré, note ni mélange."
        ),
        "eyebrow": "Impression gratuite · ordre officiel · sans compte",
        "heading": "Cartes mémo Bopomofo (Zhuyin) à imprimer",
        "lead": (
            "Choisissez les 37 symboles, une catégorie officielle ou une "
            "sélection précise. La même sélection recrée toujours les mêmes pages."
        ),
        "planner": "Choisir le jeu exact de symboles",
        "planner_intro": (
            "La page n'accepte que des symboles Bopomofo officiels et des "
            "réglages d'impression. Elle ne demande jamais le nom, l'âge, "
            "l'école, la voix, l'écriture, les réponses, la note ou les progrès."
        ),
        "labels": {
            "presets": "Sélections rapides",
            "all": "Les 37",
            "initials": "Initiales 21",
            "medials": "Médianes 3",
            "finals": "Finales 13",
            "symbols": "Touchez pour ajouter ou retirer",
            "density": "Cartes par page imprimée",
            "category": "Catégorie sur chaque carte",
            "show": "Afficher",
            "hide": "Masquer",
            "generate": "Créer les cartes",
            "print": "Imprimer ces cartes",
            "result": "{count} cartes · {pages} pages",
            "page": "Page imprimée",
            "invalid": "Choisissez 1 à 37 symboles officiels et un format valide.",
            "toggle": "Basculer",
        },
        "categories": {
            "initial": "Initiale",
            "medial": "Médiane",
            "final": "Finale",
        },
        "badges": (
            "Les 37 symboles de base officiels",
            "Même sélection, même ordre",
            "Sans données d'enfant, note ni diagnostic",
        ),
        "boundary": (
            "Ce que font ces cartes — et leurs limites",
            (
                "Elles placent les symboles Bopomofo officiels choisis sur des "
                "cartes à découper. Elles ne donnent ni équivalent Pinyin ni "
                "mot-exemple, ne diffusent ni n'écoutent d'audio, ne notent pas "
                "la prononciation, n'enregistrent rien et ne diagnostiquent pas."
            ),
        ),
        "how": (
            "Comment le jeu fixe est créé",
            (
                "Choisissez une sélection rapide ou touchez les symboles voulus.",
                "Chaque symbole apparaît une fois dans l'ordre officiel du "
                "ministère taïwanais de l'Éducation, sans mélange aléatoire.",
                "Choisissez 4, 6 ou 8 cartes par feuille A4 et la catégorie.",
            ),
        ),
        "use": (
            "Une activité détendue guidée par un adulte",
            (
                "Imprimez et découpez uniquement les symboles utiles.",
                "Un adulte peut nommer un symbole avec une source officielle "
                "pendant que l'apprenant pointe, associe ou trie.",
                "Gardez une activité sans note, classement, évaluation ni "
                "diagnostic et arrêtez si l'apprenant le souhaite.",
            ),
        ),
        "webmcp_description": (
            "Renvoie des pages déterministes à imprimer avec 1–37 symboles "
            "Bopomofo officiels, densité et catégorie. Lecture seule : aucun "
            "profil d'enfant, texte libre, réponse, note, enregistrement, "
            "évaluation, diagnostic ou promesse d'apprentissage."
        ),
        "faq_title": "Questions sur les cartes Bopomofo",
        "faq": (
            (
                "Les 37 symboles Bopomofo de base sont-ils disponibles ?",
                "Oui. Les sélections comprennent 21 initiales, 3 médianes et "
                "13 finales dans l'ordre officiel du ministère taïwanais.",
            ),
            (
                "La page collecte-t-elle des informations sur un enfant ?",
                "Non. Seuls la liste fixe de symboles et les réglages d'impression "
                "sont utilisés sur cette page ; rien n'est envoyé ni conservé.",
            ),
            (
                "Pourquoi n'y a-t-il ni Pinyin ni mot-exemple ?",
                "Une seule graphie latine ou un seul mot peut être trompeur selon "
                "le contexte. Les cartes restent dans le jeu officiel vérifié et "
                "renvoient vers les sources officielles.",
            ),
        ),
        "index": (
            "Cartes mémo Bopomofo à imprimer",
            (
                "Choisissez parmi les 37 symboles Zhuyin officiels et imprimez "
                "des cartes fixes et privées, sans compte ni note."
            ),
        ),
        "inline_link": "Créer gratuitement des cartes Bopomofo à imprimer",
        "footer": (
            "Symboles officiels · aucune donnée d'enfant · aucune note · aucune affirmation phonétique"
        ),
    },
    "ja": {
        "title": "注音符号フラッシュカード作成 | 37字を無料印刷",
        "description": (
            "台湾教育部の基本37注音符号から必要な字だけを選び、固定順の印刷用カードを無料作成。"
            "アカウント、子どもの情報、保存、採点、ピンイン推測、ランダム並べ替えはありません。"
        ),
        "eyebrow": "無料印刷 · 公式順 · アカウント不要",
        "heading": "注音符号（ボポモフォ）フラッシュカード",
        "lead": (
            "基本37字、公式分類、または必要な字だけを選択。同じ選択からは、毎回同じ切り取り用ページを作成します。"
        ),
        "planner": "印刷する注音符号を選ぶ",
        "planner_intro": (
            "入力できるのは公式の注音符号と印刷設定だけです。子どもの氏名、年齢、学校、音声、"
            "手書き、回答、点数、進度は一切求めません。"
        ),
        "labels": {
            "presets": "すぐ選べるセット",
            "all": "基本37字",
            "initials": "声母21字",
            "medials": "介音3字",
            "finals": "韻母13字",
            "symbols": "タップして追加・解除",
            "density": "印刷1ページの枚数",
            "category": "カードの分類表示",
            "show": "表示",
            "hide": "非表示",
            "generate": "カードを作成",
            "print": "このカードを印刷",
            "result": "{count}枚 · 印刷{pages}ページ",
            "page": "印刷ページ",
            "invalid": "公式記号を1〜37字選び、対応する印刷形式を指定してください。",
            "toggle": "切り替え",
        },
        "categories": {
            "initial": "声母",
            "medial": "介音",
            "final": "韻母",
        },
        "badges": (
            "公式の基本37注音符号",
            "同じ選択なら同じ順序",
            "子どもの情報・採点・診断なし",
        ),
        "boundary": (
            "このカードでできること・できないこと",
            (
                "選んだ公式注音符号を切り取り用カードに配置します。ピンインや例語との一対一対応、"
                "音声再生・録音、発音採点、回答記録、診断、学習効果の保証は行いません。"
            ),
        ),
        "how": (
            "固定カードの作り方",
            (
                "セットを選ぶか、必要な記号だけをタップします。",
                "各記号は台湾教育部の公式順で1回ずつ並び、ランダムに入れ替えません。",
                "A4用紙1枚あたり4・6・8枚と、分類名の表示を選びます。",
            ),
        ),
        "use": (
            "大人と行う負担の少ない使い方",
            (
                "その日に必要な記号だけを印刷して切り取ります。",
                "大人が公式資料で発音を確認しながら読み、学習者は指差し・組み合わせ・分類をします。",
                "点数・順位・評価・診断にはせず、本人がやめたいときに終えます。",
            ),
        ),
        "webmcp_description": (
            "公式の注音符号1〜37字、ページ枚数、分類表示から固定の印刷カードを返す読み取り専用ツール。"
            "子どものプロフィール、自由文、回答、点数、録音、評価、診断、学習効果の主張は受け付けません。"
        ),
        "faq_title": "注音符号カードのよくある質問",
        "faq": (
            (
                "基本37注音符号をすべて選べますか？",
                "はい。声母21字、介音3字、韻母13字を台湾教育部の公式順で選べます。",
            ),
            (
                "子どもの情報を収集・保存しますか？",
                "いいえ。このページ内で固定記号リストと印刷設定だけを使い、送信も保存もしません。",
            ),
            (
                "ピンインや例語を載せないのはなぜですか？",
                "ラテン文字表記や単一の例語は文脈によって誤解を招くためです。カードは検証済みの"
                "公式記号に限定し、発音と筆順は公式資料へ案内します。",
            ),
        ),
        "index": (
            "印刷用・注音符号フラッシュカード",
            (
                "公式の基本37字から選び、アカウントや採点なしで固定順の切り取りカードを作成します。"
            ),
        ),
        "inline_link": "無料の注音符号フラッシュカードを作成",
        "footer": "公式記号 · 子どもの情報なし · 採点なし · 発音の断定なし",
    },
    "ko": {
        "title": "주음부호 플래시카드 만들기 | 37개 기호 무료 인쇄",
        "description": (
            "대만 교육부의 기본 주음부호 37개 중 필요한 기호를 골라 고정 순서의 인쇄용 카드를 만드세요. "
            "계정, 아동 정보, 저장, 채점, 병음 추측, 무작위 섞기가 없습니다."
        ),
        "eyebrow": "무료 인쇄 · 공식 순서 · 계정 불필요",
        "heading": "주음부호(보포모포) 인쇄용 플래시카드",
        "lead": (
            "37개 전체, 공식 분류 또는 정확히 필요한 기호만 선택하세요. 같은 선택은 언제나 같은 재단용 페이지를 만듭니다."
        ),
        "planner": "인쇄할 기호를 정확히 선택",
        "planner_intro": (
            "공식 주음부호와 인쇄 설정만 입력할 수 있습니다. 아동의 이름, 나이, 학교, 음성, 필기, "
            "답변, 점수 또는 진도를 묻지 않습니다."
        ),
        "labels": {
            "presets": "빠른 기호 세트",
            "all": "기본 37개",
            "initials": "성모 21개",
            "medials": "개음 3개",
            "finals": "운모 13개",
            "symbols": "눌러서 포함 또는 제외",
            "density": "인쇄 페이지당 카드",
            "category": "카드의 분류 이름",
            "show": "표시",
            "hide": "숨기기",
            "generate": "카드 만들기",
            "print": "이 카드 인쇄",
            "result": "카드 {count}장 · 인쇄 {pages}쪽",
            "page": "인쇄 페이지",
            "invalid": "공식 기호 1–37개와 지원되는 인쇄 형식을 선택하세요.",
            "toggle": "전환",
        },
        "categories": {
            "initial": "성모",
            "medial": "개음",
            "final": "운모",
        },
        "badges": (
            "공식 기본 주음부호 37개",
            "같은 선택, 같은 공식 순서",
            "아동 정보·점수·진단 없음",
        ),
        "boundary": (
            "이 카드가 하는 일과 하지 않는 일",
            (
                "선택한 공식 주음부호를 재단용 카드에 배치합니다. 병음이나 예시 단어의 일대일 대응, "
                "음성 재생·녹음, 발음 채점, 답변 기록, 진단 또는 학습 결과 보장은 제공하지 않습니다."
            ),
        ),
        "how": (
            "고정 카드 세트를 만드는 방법",
            (
                "빠른 세트를 고르거나 필요한 기호만 누릅니다.",
                "각 기호는 대만 교육부 공식 순서로 한 번씩 나오며 무작위로 섞이지 않습니다.",
                "A4 한 장당 4·6·8장과 분류 이름 표시 여부를 고릅니다.",
            ),
        ),
        "use": (
            "성인이 함께하는 부담 없는 활용법",
            (
                "현재 활동에 필요한 기호만 인쇄해 자릅니다.",
                "성인이 공식 자료로 발음을 확인해 읽고 학습자는 가리키기, 짝짓기 또는 분류를 합니다.",
                "점수, 순위, 평가 또는 진단으로 사용하지 말고 학습자가 원하면 멈춥니다.",
            ),
        ),
        "webmcp_description": (
            "공식 주음부호 1–37개, 페이지 밀도와 분류 표시로 고정 인쇄 카드를 반환하는 읽기 전용 도구입니다. "
            "아동 프로필, 자유 문장, 답변, 점수, 녹음, 평가, 진단 또는 학습 효과 주장을 받지 않습니다."
        ),
        "faq_title": "주음부호 카드 자주 묻는 질문",
        "faq": (
            (
                "기본 주음부호 37개를 모두 사용할 수 있나요?",
                "네. 성모 21개, 개음 3개, 운모 13개를 대만 교육부 공식 순서로 제공합니다.",
            ),
            (
                "아동 정보를 수집하거나 저장하나요?",
                "아니요. 고정 기호 목록과 인쇄 설정만 현재 페이지에서 사용하며 업로드하거나 저장하지 않습니다.",
            ),
            (
                "병음이나 예시 단어가 없는 이유는 무엇인가요?",
                "하나의 로마자 표기나 예시는 문맥에 따라 오해를 만들 수 있습니다. 카드는 검증된 공식 기호만 "
                "사용하며 발음과 필순은 공식 자료를 안내합니다.",
            ),
        ),
        "index": (
            "인쇄용 주음부호 플래시카드",
            (
                "공식 37개 기호에서 골라 계정, 채점, 무작위 섞기 없이 고정 순서의 카드를 인쇄합니다."
            ),
        ),
        "inline_link": "무료 인쇄용 주음부호 플래시카드 만들기",
        "footer": "공식 기호 · 아동 정보 없음 · 채점 없음 · 발음 단정 없음",
    },
    "zh-Hant": {
        "title": "注音符號字卡產生器｜37 個注音免費列印",
        "description": (
            "從台灣教育部 37 個基本注音符號中選取任意符號，免費產生固定官方順序的可列印字卡；"
            "免登入、不收兒童資料、不儲存結果、不計分、不附未驗證拼音或例字。"
        ),
        "eyebrow": "免費列印 · 教育部順序 · 免登入",
        "heading": "可列印注音符號字卡產生器",
        "lead": (
            "選全部 37 個、教育部分類，或只選今天需要的符號；相同選擇永遠產生相同順序的裁切頁。"
        ),
        "planner": "精準選擇要列印的注音",
        "planner_intro": (
            "本頁只接受官方注音符號與列印設定，不會要求孩子的姓名、年齡、學校、聲音、書寫、"
            "答案、分數或學習進度。"
        ),
        "labels": {
            "presets": "快速選擇",
            "all": "全部 37 個",
            "initials": "聲母 21 個",
            "medials": "介音 3 個",
            "finals": "韻母 13 個",
            "symbols": "點選要加入或移除的符號",
            "density": "每張列印頁的字卡數",
            "category": "字卡是否顯示分類",
            "show": "顯示",
            "hide": "隱藏",
            "generate": "產生注音字卡",
            "print": "列印這些字卡",
            "result": "共 {count} 張字卡 · {pages} 張列印頁",
            "page": "列印頁",
            "invalid": "請選 1–37 個官方注音符號與支援的列印版型。",
            "toggle": "切換",
        },
        "categories": {
            "initial": "聲母",
            "medial": "介音",
            "final": "韻母",
        },
        "badges": (
            "完整 37 個基本注音符號",
            "相同選擇、相同官方順序",
            "不收兒童資料、不計分、不診斷",
        ),
        "boundary": (
            "這份字卡會做什麼、不會做什麼",
            (
                "工具只把選取的官方注音符號排成可裁切字卡；不提供拼音或例字的一對一對照、"
                "不播放或收錄聲音、不評分發音、不記錄答案、不診斷，也不承諾任何學習成效。"
            ),
        ),
        "how": (
            "固定字卡如何產生",
            (
                "使用快速分類，或逐一點選真正需要的符號。",
                "每個符號只出現一次，並依台灣教育部官方順序排列，不做即時隨機洗牌。",
                "選擇每張 A4 紙放 4、6 或 8 張，以及是否顯示官方分類。",
            ),
        ),
        "use": (
            "由成人陪同、低壓力的使用方式",
            (
                "只列印並裁切目前活動真正需要的符號。",
                "成人可先用官方資料確認讀音，再讓學習者指認、配對或分類。",
                "把字卡當作活動，不當成分數、排名、測驗或診斷；孩子想停就停止。",
            ),
        ),
        "webmcp_description": (
            "依 1–37 個官方注音符號、頁面張數與分類顯示設定，回傳可重現的列印字卡。"
            "唯讀工具：不接收兒童檔案、自由文字、答案、分數、錄音、評量、診斷或成效宣稱。"
        ),
        "faq_title": "注音符號字卡常見問題",
        "faq": (
            (
                "有包含完整 37 個基本注音符號嗎？",
                "有。快速分類包含 21 個聲母、3 個介音與 13 個韻母，並依台灣教育部官方順序排列。",
            ),
            (
                "會收集或儲存孩子的資料嗎？",
                "不會。固定符號清單與列印設定只在目前頁面使用，不會上傳或儲存。",
            ),
            (
                "為什麼字卡不附漢語拼音與例字？",
                "單一拉丁拼寫或例字可能因語境造成誤解。本工具只呈現已核對的官方符號，"
                "讀音與筆順則連結教育部官方資料。",
            ),
        ),
        "index": (
            "可列印注音符號字卡",
            (
                "從官方 37 個注音中自由選擇，免登入、不計分、不隨機，產生固定順序的裁切字卡。"
            ),
        ),
        "inline_link": "免費產生可列印注音符號字卡",
        "footer": "官方符號 · 不收兒童資料 · 不計分 · 不臆測發音",
    },
    "zh-Hans": {
        "title": "注音符号卡片生成器｜37 个符号免费打印",
        "description": (
            "从台湾教育部 37 个基本注音符号中任选符号，免费生成固定官方顺序的可打印卡片；"
            "无需登录、不收集儿童数据、不保存结果、不计分、不附未经验证的拼音或例字。"
        ),
        "eyebrow": "免费打印 · 教育部顺序 · 无需登录",
        "heading": "可打印注音符号卡片生成器",
        "lead": (
            "选择全部 37 个、官方分类，或只选今天需要的符号；相同选择始终生成相同顺序的裁切页。"
        ),
        "planner": "准确选择要打印的注音符号",
        "planner_intro": (
            "本页只接受官方注音符号与打印设置，不会要求儿童的姓名、年龄、学校、声音、书写、"
            "答案、分数或学习进度。"
        ),
        "labels": {
            "presets": "快速选择",
            "all": "全部 37 个",
            "initials": "声母 21 个",
            "medials": "介音 3 个",
            "finals": "韵母 13 个",
            "symbols": "点击要加入或移除的符号",
            "density": "每张打印页的卡片数",
            "category": "卡片是否显示分类",
            "show": "显示",
            "hide": "隐藏",
            "generate": "生成注音卡片",
            "print": "打印这些卡片",
            "result": "共 {count} 张卡片 · {pages} 张打印页",
            "page": "打印页",
            "invalid": "请选择 1–37 个官方注音符号与支持的打印版式。",
            "toggle": "切换",
        },
        "categories": {
            "initial": "声母",
            "medial": "介音",
            "final": "韵母",
        },
        "badges": (
            "完整 37 个基本注音符号",
            "相同选择、相同官方顺序",
            "不收集儿童数据、不计分、不诊断",
        ),
        "boundary": (
            "这些卡片会做什么、不会做什么",
            (
                "工具只把选择的官方注音符号排成可裁切卡片；不提供拼音或例字的一对一对应、"
                "不播放或录制声音、不评判发音、不记录答案、不诊断，也不承诺学习效果。"
            ),
        ),
        "how": (
            "固定卡片如何生成",
            (
                "使用快速分类，或逐一点击真正需要的符号。",
                "每个符号只出现一次，并按台湾教育部官方顺序排列，不进行即时随机洗牌。",
                "选择每张 A4 纸放 4、6 或 8 张，以及是否显示官方分类。",
            ),
        ),
        "use": (
            "成人陪同的低压力用法",
            (
                "只打印并裁切当前活动真正需要的符号。",
                "成人可先用官方资料确认读音，再让学习者指认、配对或分类。",
                "把卡片当作活动，不作为分数、排名、测验或诊断；儿童想停就停止。",
            ),
        ),
        "webmcp_description": (
            "按 1–37 个官方注音符号、页面张数与分类显示设置，返回可复现的打印卡片。"
            "只读工具：不接收儿童档案、自由文本、答案、分数、录音、评估、诊断或效果声明。"
        ),
        "faq_title": "注音符号卡片常见问题",
        "faq": (
            (
                "包含完整 37 个基本注音符号吗？",
                "包含。快速分类有 21 个声母、3 个介音与 13 个韵母，并按台湾教育部官方顺序排列。",
            ),
            (
                "会收集或保存儿童数据吗？",
                "不会。固定符号列表与打印设置只在当前页面使用，不会上载或保存。",
            ),
            (
                "为什么卡片不附汉语拼音与例字？",
                "单一拉丁拼写或例字可能因语境造成误解。本工具只呈现已核对的官方符号，"
                "读音与笔顺则链接教育部官方资料。",
            ),
        ),
        "index": (
            "可打印注音符号卡片",
            (
                "从官方 37 个注音中自由选择，无需登录、不计分、不随机，生成固定顺序的裁切卡片。"
            ),
        ),
        "inline_link": "免费生成可打印注音符号卡片",
        "footer": "官方符号 · 不收集儿童数据 · 不计分 · 不臆测发音",
    },
}


def build_flashcards(
    symbols: list[str], cards_per_page: int, show_category: bool
) -> dict[str, object]:
    if not isinstance(symbols, list):
        raise TypeError("symbols must be an array")
    if not isinstance(cards_per_page, int) or isinstance(cards_per_page, bool):
        raise TypeError("cards_per_page must be an integer")
    if not isinstance(show_category, bool):
        raise TypeError("show_category must be a boolean")
    if not 1 <= len(symbols) <= len(OFFICIAL_SYMBOLS):
        raise ValueError("choose between 1 and 37 symbols")
    if cards_per_page not in CARD_DENSITIES:
        raise ValueError("unsupported cards_per_page")
    if any(not isinstance(symbol, str) for symbol in symbols):
        raise TypeError("each symbol must be a string")
    if len(symbols) != len(set(symbols)):
        raise ValueError("symbols must be unique")
    if any(symbol not in SYMBOL_ORDER for symbol in symbols):
        raise ValueError("unsupported Bopomofo symbol")
    ordered = sorted(symbols, key=SYMBOL_ORDER.__getitem__)
    cards = [
        {"symbol": symbol, "category": CATEGORY_BY_SYMBOL[symbol]}
        for symbol in ordered
    ]
    pages = [
        cards[start : start + cards_per_page]
        for start in range(0, len(cards), cards_per_page)
    ]
    return {
        "selected_inputs": {
            "symbols": ordered,
            "cards_per_page": cards_per_page,
            "show_category": show_category,
        },
        "pages": [
            {"page_number": index + 1, "cards": page}
            for index, page in enumerate(pages)
        ],
    }


STYLE = r"""
:root{--ink:#20283c;--muted:#667087;--line:#dce2ef;--paper:#fff;--bg:#f4f7fc;--indigo:#3949a3;--violet:#8067d8;--peach:#f3a36b;--soft:#eef1ff;--shadow:0 22px 60px rgba(48,57,110,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 58%,#e9eef9 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--indigo)}.wrap{width:min(1140px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--indigo);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.control-title{display:block;font-size:13px;font-weight:850;color:var(--indigo);margin:20px 0 7px;white-space:nowrap;overflow-x:auto}.presets,.picker,.actions{display:flex;gap:8px;flex-wrap:wrap}.preset,.symbol-button{border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;font:inherit}.preset{border-radius:999px;padding:9px 14px;font-weight:800;white-space:nowrap}.preset.active,.symbol-button.selected{color:#fff;border-color:transparent;background:linear-gradient(135deg,var(--indigo),var(--violet))}.picker{margin-top:9px}.symbol-button{width:48px;height:48px;border-radius:14px;font-size:25px;font-weight:900;line-height:1}.controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--indigo);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,button{font:inherit}select{width:100%;min-height:46px;border:1px solid #c9d1e3;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.actions{margin-top:18px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--indigo),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}.button.ghost{background:#fff;color:var(--indigo);border:1px solid var(--line);box-shadow:none}.note{background:#fff7dc;border:1px solid #ead7a0;border-radius:16px;padding:13px 15px;white-space:nowrap;overflow-x:auto}
.flash-pages{display:grid;grid-template-columns:1fr;gap:20px;margin-top:20px}.flash-page{background:#fff;border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 14px 34px rgba(48,57,110,.09);break-inside:avoid;page-break-inside:avoid}.page-head{display:flex;justify-content:space-between;gap:12px;border-bottom:2px solid var(--ink);padding-bottom:8px;margin-bottom:12px;font-size:13px;font-weight:850;color:var(--muted);white-space:nowrap}.flash-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.flashcard{min-height:210px;border:2px dashed #c9d1e3;border-radius:18px;background:linear-gradient(180deg,#fff,#fafbff);display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;overflow:hidden}.flash-symbol{font-size:clamp(72px,13vw,112px);font-weight:900;line-height:1;white-space:nowrap}.flash-category{position:absolute;right:12px;top:10px;color:var(--muted);font-size:12px;font-weight:850;white-space:nowrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ol,.card ul{padding-left:22px}.card li{margin:8px 0}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}.footer{background:var(--indigo);color:#f5f6ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:850px){.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}@media(max-width:680px){.controls{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1140px)}.flashcard{min-height:170px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.planner>h2,.planner form,.planner>.intro,.note,.button,.app-card,.footer,.grid,.faq{display:none!important}body{background:#fff}.wrap{width:100%}.planner{box-shadow:none;border:0;padding:0;margin:0}.flash-pages{display:block;margin:0}.flash-page{border:0;border-radius:0;box-shadow:none;padding:0;margin:0;page-break-after:always}.flash-page:last-child{page-break-after:auto}.page-head{font-size:9pt;margin-bottom:4mm}.flash-grid{gap:4mm}.flash-page.density-4 .flashcard{height:125mm}.flash-page.density-6 .flashcard{height:80mm}.flash-page.density-8 .flashcard{height:58mm}.flashcard{border:1pt dashed #777;border-radius:3mm;background:#fff}.flash-symbol{font-size:58pt}.flash-category{font-size:9pt;color:#444}@page{size:A4;margin:10mm}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("bopomofo-flashcard-config").textContent);
  const form = document.getElementById("bopomofo-flashcard-planner");
  const picker = document.getElementById("symbol-picker");
  const density = document.getElementById("cards-per-page");
  const category = document.getElementById("show-category");
  const summary = document.getElementById("result-summary");
  const pageList = document.getElementById("flash-pages");
  const printButton = document.getElementById("print-cards");
  const presets = [...document.querySelectorAll("[data-preset]")];
  let selected = new Set(config.symbols.map((item) => item.symbol));

  function validateInput(input) {
    if (input === null || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("WebMCP input must be an object.");
    }
    const allowed = new Set(Object.keys(config.inputSchema.properties));
    for (const name of Object.keys(input)) {
      if (!allowed.has(name)) throw new RangeError(`${name} is not supported.`);
    }
    for (const name of config.inputSchema.required) {
      if (!Object.prototype.hasOwnProperty.call(input, name)) {
        throw new TypeError(`${name} is required.`);
      }
    }
    if (!Array.isArray(input.symbols) ||
        input.symbols.length < 1 ||
        input.symbols.length > config.symbols.length) {
      throw new RangeError("symbols must contain 1–37 items.");
    }
    const official = new Set(config.symbols.map((item) => item.symbol));
    const seen = new Set();
    for (const symbol of input.symbols) {
      if (typeof symbol !== "string" || !official.has(symbol) || seen.has(symbol)) {
        throw new RangeError("symbols must be unique official Bopomofo symbols.");
      }
      seen.add(symbol);
    }
    if (typeof input.cards_per_page !== "number" ||
        !Number.isInteger(input.cards_per_page) ||
        !config.inputSchema.properties.cards_per_page.enum.includes(input.cards_per_page)) {
      throw new RangeError("cards_per_page is not supported.");
    }
    if (typeof input.show_category !== "boolean") {
      throw new TypeError("show_category must be a boolean.");
    }
    return buildFlashcards(input);
  }

  function buildFlashcards(input) {
    const wanted = new Set(input.symbols);
    const cards = config.symbols.filter((item) => wanted.has(item.symbol));
    const pages = [];
    for (let start = 0; start < cards.length; start += input.cards_per_page) {
      pages.push({
        page_number: pages.length + 1,
        cards: cards.slice(start, start + input.cards_per_page)
      });
    }
    return {
      selected_inputs: {
        symbols: cards.map((item) => item.symbol),
        cards_per_page: input.cards_per_page,
        show_category: input.show_category
      },
      pages
    };
  }

  function selectedPreset() {
    const values = [...selected];
    const same = (target) =>
      values.length === target.length && target.every((symbol) => selected.has(symbol));
    if (same(config.presets.all)) return "all";
    if (same(config.presets.initials)) return "initials";
    if (same(config.presets.medials)) return "medials";
    if (same(config.presets.finals)) return "finals";
    return "";
  }

  function syncButtons() {
    const preset = selectedPreset();
    for (const button of presets) {
      const active = button.dataset.preset === preset;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    for (const button of picker.querySelectorAll("button")) {
      const active = selected.has(button.dataset.symbol);
      button.classList.toggle("selected", active);
      button.setAttribute("aria-pressed", String(active));
    }
  }

  function makePicker() {
    const fragment = document.createDocumentFragment();
    for (const item of config.symbols) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "symbol-button selected";
      button.dataset.symbol = item.symbol;
      button.textContent = item.symbol;
      button.setAttribute("aria-label", `${config.labels.toggle} ${item.symbol}`);
      button.setAttribute("aria-pressed", "true");
      button.addEventListener("click", () => {
        if (selected.has(item.symbol)) selected.delete(item.symbol);
        else selected.add(item.symbol);
        syncButtons();
        render();
      });
      fragment.appendChild(button);
    }
    picker.replaceChildren(fragment);
  }

  function makeCard(card, showCategory) {
    const element = document.createElement("article");
    element.className = "flashcard";
    const symbol = document.createElement("div");
    symbol.className = "flash-symbol";
    symbol.textContent = card.symbol;
    element.appendChild(symbol);
    if (showCategory) {
      const label = document.createElement("div");
      label.className = "flash-category";
      label.textContent = config.categoryLabels[card.category];
      element.appendChild(label);
    }
    return element;
  }

  function makePage(page, result) {
    const section = document.createElement("section");
    section.className = `flash-page density-${result.selected_inputs.cards_per_page}`;
    const header = document.createElement("div");
    header.className = "page-head";
    const title = document.createElement("span");
    title.textContent = `${config.labels.page} ${page.page_number}`;
    const count = document.createElement("span");
    count.textContent = `${page.cards.length} / ${result.selected_inputs.cards_per_page}`;
    header.append(title, count);
    const grid = document.createElement("div");
    grid.className = "flash-grid";
    for (const card of page.cards) {
      grid.appendChild(makeCard(card, result.selected_inputs.show_category));
    }
    section.append(header, grid);
    return section;
  }

  function currentInput() {
    return {
      symbols: [...selected],
      cards_per_page: Number(density.value),
      show_category: category.value === "show"
    };
  }

  function render() {
    let result;
    try {
      result = validateInput(currentInput());
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        summary.textContent = config.labels.invalid;
        pageList.replaceChildren();
        return;
      }
      throw error;
    }
    summary.textContent = config.labels.result
      .replace("{count}", String(result.selected_inputs.symbols.length))
      .replace("{pages}", String(result.pages.length));
    const fragment = document.createDocumentFragment();
    for (const page of result.pages) fragment.appendChild(makePage(page, result));
    pageList.replaceChildren(fragment);
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "create_private_bopomofo_flashcards",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const cards = validateInput(input);
        const result = {
          result_type: "private_bopomofo_flashcards",
          deterministic: true,
          official_symbol_order: true,
          is_not_assessment: true,
          no_score_grade_rank_or_diagnosis: true,
          no_child_data_received: true,
          no_pronunciation_or_learning_outcome_claim: true,
          flashcards: cards,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) result.optional_lumibopomofo = config.optionalApp;
        return JSON.stringify(result);
      }
    });
  }

  for (const button of presets) {
    button.addEventListener("click", () => {
      selected = new Set(config.presets[button.dataset.preset]);
      syncButtons();
      render();
    });
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  density.addEventListener("change", render);
  category.addEventListener("change", render);
  printButton.addEventListener("click", () => window.print());
  makePicker();
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


def webmcp_input_schema(locale: str) -> dict[str, object]:
    labels = COPY[locale]["labels"]
    return {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "description": labels["symbols"],
                "items": {"type": "string", "enum": list(OFFICIAL_SYMBOLS)},
                "minItems": 1,
                "maxItems": len(OFFICIAL_SYMBOLS),
                "uniqueItems": True,
            },
            "cards_per_page": {
                "type": "integer",
                "enum": list(CARD_DENSITIES),
                "description": labels["density"],
            },
            "show_category": {
                "type": "boolean",
                "description": labels["category"],
            },
        },
        "required": ["symbols", "cards_per_page", "show_category"],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    base = BASE_COPY[locale]
    labels = t["labels"]
    url = canonical(locale)
    other = "zh-Hant" if locale == "en" else "en"
    prefix = "" if locale == "en" else f"{locale}/"
    tools = f"{SITE}/{prefix}tools/index.html"
    home = f"{SITE}/{prefix}index.html"
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{alt}" href="{canonical(alt)}">'
        for alt in ALT_LOCALES
    )
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    how_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["how"][1]
    )
    use_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["use"][1]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    sources = (MOE_HANDBOOK, MOE_STROKE_ORDER, UNICODE_CHART_PDF)
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(
            (base["source_labels"][index] for index in SOURCE_LABEL_INDEXES),
            sources,
            strict=True,
        )
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_bopomofo_flashcards_{locale.lower()}")
        if app_public
        else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            '<section class="app-card wrap"><h2>'
            f'{html.escape(base["app_title"])}</h2>'
            f'<p>{html.escape(base["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(base["app_cta"])}</a></section>'
        )
    symbol_items = [
        {"symbol": symbol, "category": CATEGORY_BY_SYMBOL[symbol]}
        for symbol in OFFICIAL_SYMBOLS
    ]
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "symbols": symbol_items,
        "presets": {
            "all": list(OFFICIAL_SYMBOLS),
            "initials": list(INITIALS),
            "medials": list(MEDIALS),
            "finals": list(FINALS),
        },
        "labels": {
            "result": labels["result"],
            "page": labels["page"],
            "invalid": labels["invalid"],
            "toggle": labels["toggle"],
        },
        "categoryLabels": t["categories"],
        "toolDescription": t["webmcp_description"],
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(
                (
                    base["source_labels"][index]
                    for index in SOURCE_LABEL_INDEXES
                ),
                sources,
                strict=True,
            )
        ],
        "webmcpSource": WEBMCP_SOURCE,
        "optionalApp": (
            {
                "label": base["app_cta"],
                "boundary": base["app_text"],
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
        "featureList": list(t["badges"]),
        "citation": list(sources),
    }
    howto_schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": t["use"][0],
        "step": [
            {"@type": "HowToStep", "position": index + 1, "text": step}
            for index, step in enumerate(t["use"][1])
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
            {
                "@type": "ListItem",
                "position": 1,
                "name": base["tools"],
                "item": tools,
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": t["heading"],
                "item": url,
            },
        ],
    }
    density_options = "".join(
        f'<option value="{value}"'
        f'{" selected" if value == DEFAULT_DENSITY else ""}>{value}</option>'
        for value in CARD_DENSITIES
    )
    preset_buttons = "".join(
        f'<button class="preset{" active" if key == "all" else ""}" '
        f'type="button" data-preset="{key}" '
        f'aria-pressed="{"true" if key == "all" else "false"}">'
        f'{html.escape(labels[key])}</button>'
        for key in ("all", "initials", "medials", "finals")
    )
    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"], quote=True)}">
<link rel="canonical" href="{url}">
{alternate_links}
<link rel="alternate" hreflang="x-default" href="{canonical("en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"], quote=True)}">
<meta property="og:description" content="{html.escape(t["description"], quote=True)}">
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
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(base["tools"])}</a><a href="{canonical(other)}">{html.escape(base["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="bopomofo-flashcard-planner"><span class="control-title">{html.escape(labels["presets"])}</span><div class="presets">{preset_buttons}</div><span class="control-title">{html.escape(labels["symbols"])}</span><div class="picker" id="symbol-picker"></div>
<div class="controls"><div class="field"><label for="cards-per-page">{html.escape(labels["density"])}</label><select id="cards-per-page">{density_options}</select></div><div class="field"><label for="show-category">{html.escape(labels["category"])}</label><select id="show-category"><option value="show" selected>{html.escape(labels["show"])}</option><option value="hide">{html.escape(labels["hide"])}</option></select></div></div>
<div class="actions"><button class="button" type="submit">{html.escape(labels["generate"])}</button><button class="button ghost" type="button" id="print-cards">{html.escape(labels["print"])}</button></div></form>
<p id="result-summary" class="note" role="status" aria-live="polite"></p><div id="flash-pages" class="flash-pages"></div>
</section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["boundary"][0])}</h2><p>{html.escape(t["boundary"][1])}</p></article><article class="card"><h2>{html.escape(t["how"][0])}</h2><ol>{how_items}</ol></article><article class="card wide"><h2>{html.escape(t["use"][0])}</h2><ol>{use_items}</ol></article><article class="card wide"><h2>{html.escape(base["sources_title"])}</h2><p>{html.escape(base["sources_intro"])}</p><ul>{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(base["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="bopomofo-flashcard-config">{config_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def index_card(locale: str) -> str:
    title, description = COPY[locale]["index"]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(title)}</a></h2>'
        f"<p>{html.escape(description)}</p></article>"
    )


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    card = index_card(locale)
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{SLUG}")?>'
        rf'<h2><a href="{SLUG}\.html">.*?</article>',
        re.S,
    )
    if existing.search(text):
        updated = existing.sub(card, text, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in text:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = text.replace(marker, marker + card, 1)
    return write_text_if_changed(path, updated)


TARGET_ANSWER_SLUG = "best-app-to-learn-zhuyin-bopomofo-for-kids.html"
INBOUND_LINK_CLASS = "bopomofo-flashcards-inline-link"
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
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
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
            f'data-bopomofo-flashcards-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        if write_text_if_changed(
            path, text[: match.start()] + link + text[match.start() :]
        ):
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
            pages / relative, render_page(locale, app_public=app_public)
        )
        index = pages / ("tools" if locale == "en" else f"{locale}/tools")
        update_one_index(index / "index.html", locale)
        outputs.append(canonical(locale))
    insert_answer_links(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"bopomofo flashcards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
