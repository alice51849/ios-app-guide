#!/usr/bin/env python3
"""Generate deterministic printable Bopomofo copy-practice sheets."""

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
from bopomofo_flashcards import (  # noqa: E402
    ALT_LOCALES,
    APP_ID,
    APP_KEY,
    BASE_COPY,
    CATEGORY_BY_SYMBOL,
    COPY as FLASHCARD_COPY,
    FINALS,
    INITIALS,
    MEDIALS,
    MOE_HANDBOOK,
    MOE_STROKE_ORDER,
    OFFICIAL_SYMBOLS,
    PAGES,
    SITE,
    SOURCE_LABEL_INDEXES,
    UNICODE_CHART_PDF,
    WEBMCP_SOURCE,
    json_script,
    write_text_if_changed,
)
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

SLUG = "zhuyin-practice-sheet"
CONTENT_DATE = "2026-07-15"
CELL_COUNTS = (2, 4, 6)
ROWS_PER_PAGE = (4, 5, 6)
DEFAULT_TRACE_CELLS = 4
DEFAULT_BLANK_CELLS = 4
DEFAULT_ROWS_PER_PAGE = 6


COPY = {
    "en": {
        "title": "Printable Bopomofo Practice Sheet | Trace and Copy Zhuyin",
        "description": (
            "Choose any of the 37 official Bopomofo symbols and make fixed A4 "
            "trace-and-copy grids. No account, child data, name field, date, "
            "saved work, scoring, handwriting assessment, or live shuffle."
        ),
        "eyebrow": "Free printable · official symbol order · no child data",
        "heading": "Printable Bopomofo trace-and-copy sheets",
        "lead": (
            "Choose all 37 symbols, one official category, or an exact custom "
            "set. Adjust the example and blank cells, then print fixed A4 pages."
        ),
        "planner": "Build the exact practice pages",
        "planner_intro": (
            "Only official Bopomofo symbols and layout settings are accepted. "
            "This page never asks for a child's name, age, school, handwriting, "
            "voice, answer, score, diagnosis, or progress."
        ),
        "labels": {
            "presets": "Quick symbol sets",
            "all": "All 37",
            "initials": "Initials 21",
            "medials": "Medials 3",
            "finals": "Finals 13",
            "symbols": "Tap symbols to include or remove",
            "trace": "Light example cells per symbol",
            "blank": "Blank copy cells per symbol",
            "rows": "Symbol rows per A4 page",
            "category": "Category label beside each symbol",
            "show": "Show",
            "hide": "Hide",
            "generate": "Build practice sheets",
            "print": "Print these sheets",
            "result": "{count} symbol rows · {pages} A4 pages",
            "page": "Practice page",
            "trace_word": "Light examples",
            "blank_word": "Blank cells",
            "invalid": "Choose 1–37 official symbols and supported layout values.",
            "toggle": "Toggle",
        },
        "badges": (
            "All 37 official basic symbols",
            "Same settings, same ordered pages",
            "No name, date, score, or handwriting assessment",
        ),
        "boundary": (
            "What this sheet does—and does not do",
            (
                "It places selected official symbols into light example cells "
                "and blank crosshair cells for adult-led pencil practice. It "
                "does not demonstrate stroke order, inspect handwriting, score "
                "a learner, diagnose a need, or promise better writing."
            ),
        ),
        "how": (
            "How the fixed worksheet is built",
            (
                "Choose a preset or tap the exact official symbols needed.",
                "Symbols appear once each in Taiwan Ministry of Education order, "
                "never in a live random sequence.",
                "Choose 2, 4, or 6 light and blank cells plus 4–6 rows per page; "
                "the same inputs always reproduce the same pages.",
            ),
        ),
        "use": (
            "A responsible way to use the grids",
            (
                "Check the official Ministry of Education stroke-order portal "
                "before modeling an unfamiliar symbol.",
                "An adult can demonstrate on separate paper; the learner may "
                "trace, copy, point, or stop without a score.",
                "Treat the sheet as optional practice, not proof of readiness, "
                "mastery, motor ability, or a learning difficulty.",
            ),
        ),
        "webmcp_description": (
            "Return deterministic A4 Bopomofo trace-and-copy page data from "
            "1–37 official symbols and fixed layout settings. Read-only: accepts "
            "no child profile, name, free text, handwriting, upload, answer, "
            "score, assessment, diagnosis, or learning-outcome claim."
        ),
        "faq_title": "Bopomofo practice-sheet questions",
        "faq": (
            (
                "Does the sheet teach official stroke order?",
                "No. The light glyph is only a visual copying cue. Use the linked "
                "Taiwan Ministry of Education portal to check official strokes.",
            ),
            (
                "Does the page collect a child's writing or personal details?",
                "No. It accepts only official symbols and layout settings in the "
                "current page; nothing is uploaded or stored.",
            ),
            (
                "Does completing a page measure Zhuyin or handwriting ability?",
                "No. The sheet has no score, grade, ranking, assessment, "
                "diagnosis, or claim that completion proves mastery.",
            ),
        ),
        "index": (
            "Printable Bopomofo Practice Sheets",
            (
                "Choose any official Zhuyin symbols and print fixed A4 "
                "trace-and-copy grids with no name field, score, or saved work."
            ),
        ),
        "inline_link": "Make a free printable Bopomofo practice sheet",
        "footer": (
            "Official symbols · no child data · no score · not stroke-order instruction"
        ),
    },
    "es-ES": {
        "title": "Ficha Bopomofo para repasar y copiar | Imprimible gratis",
        "description": (
            "Elige cualquiera de los 37 símbolos Bopomofo oficiales y crea "
            "cuadrículas A4 fijas para repasar y copiar. Sin cuenta, datos "
            "infantiles, nombre, fecha, trabajo guardado ni evaluación."
        ),
        "eyebrow": "Impresión gratis · orden oficial · sin datos infantiles",
        "heading": "Fichas Bopomofo (Zhuyin) para repasar y copiar",
        "lead": (
            "Elige los 37 símbolos, una categoría oficial o una selección "
            "exacta. Ajusta las casillas de ejemplo y copia e imprime en A4."
        ),
        "planner": "Crea las páginas de práctica exactas",
        "planner_intro": (
            "Solo se aceptan símbolos Bopomofo oficiales y ajustes de diseño. "
            "Nunca se pide nombre, edad, colegio, escritura, voz, respuesta, "
            "nota, diagnóstico ni progreso de un menor."
        ),
        "labels": {
            "presets": "Conjuntos rápidos",
            "all": "Los 37",
            "initials": "Iniciales 21",
            "medials": "Mediales 3",
            "finals": "Finales 13",
            "symbols": "Toca para incluir o quitar símbolos",
            "trace": "Casillas de ejemplo claro por símbolo",
            "blank": "Casillas en blanco por símbolo",
            "rows": "Filas por página A4",
            "category": "Categoría junto a cada símbolo",
            "show": "Mostrar",
            "hide": "Ocultar",
            "generate": "Crear fichas",
            "print": "Imprimir estas fichas",
            "result": "{count} filas · {pages} páginas A4",
            "page": "Página de práctica",
            "trace_word": "Ejemplos claros",
            "blank_word": "Casillas en blanco",
            "invalid": "Elige entre 1 y 37 símbolos y valores de diseño válidos.",
            "toggle": "Alternar",
        },
        "badges": (
            "Los 37 símbolos básicos oficiales",
            "Mismos ajustes, mismas páginas ordenadas",
            "Sin nombre, fecha, nota ni evaluación de escritura",
        ),
        "boundary": (
            "Qué hace esta ficha y qué no",
            (
                "Coloca símbolos oficiales en casillas claras y cuadrículas en "
                "blanco para practicar con lápiz y un adulto. No demuestra el "
                "orden de trazos, inspecciona la escritura, puntúa, diagnostica "
                "ni promete mejorar la escritura."
            ),
        ),
        "how": (
            "Cómo se crea la ficha fija",
            (
                "Elige un conjunto rápido o los símbolos exactos.",
                "Cada símbolo aparece una vez en el orden oficial del Ministerio "
                "de Educación de Taiwán, sin secuencia aleatoria.",
                "Elige 2, 4 o 6 casillas claras y vacías y 4–6 filas por página; "
                "las mismas opciones siempre recrean las mismas páginas.",
            ),
        ),
        "use": (
            "Uso responsable de las cuadrículas",
            (
                "Consulta el portal oficial de trazos antes de modelar un símbolo "
                "que no conozcas.",
                "Un adulto puede mostrarlo en otro papel; el alumno puede repasar, "
                "copiar, señalar o parar sin recibir una nota.",
                "Es una práctica opcional, no prueba de preparación, dominio, "
                "motricidad ni dificultad de aprendizaje.",
            ),
        ),
        "webmcp_description": (
            "Devuelve datos deterministas de páginas A4 para repasar y copiar "
            "1–37 símbolos Bopomofo oficiales. Solo lectura: sin perfil infantil, "
            "nombre, texto libre, escritura, carga, respuesta, nota, evaluación, "
            "diagnóstico ni promesa de aprendizaje."
        ),
        "faq_title": "Preguntas sobre las fichas Bopomofo",
        "faq": (
            (
                "¿La ficha enseña el orden de trazos oficial?",
                "No. El símbolo claro solo sirve de referencia visual. Consulta "
                "el portal del Ministerio de Educación de Taiwán para los trazos.",
            ),
            (
                "¿Se recopila la escritura o información de un menor?",
                "No. Solo se usan símbolos oficiales y ajustes en esta página; "
                "nada se sube ni se guarda.",
            ),
            (
                "¿Completar una página mide la escritura o el nivel de Zhuyin?",
                "No. No hay nota, nivel, clasificación, evaluación, diagnóstico "
                "ni afirmación de que terminarla pruebe dominio.",
            ),
        ),
        "index": (
            "Fichas Bopomofo para imprimir",
            (
                "Elige símbolos Zhuyin oficiales e imprime cuadrículas A4 fijas "
                "para repasar y copiar, sin nombre, nota ni trabajo guardado."
            ),
        ),
        "inline_link": "Crear una ficha Bopomofo gratis para imprimir",
        "footer": (
            "Símbolos oficiales · sin datos infantiles · sin nota · no enseña el orden de trazos"
        ),
    },
    "pt-BR": {
        "title": "Folha Bopomofo para traçar e copiar | Impressão grátis",
        "description": (
            "Escolha qualquer um dos 37 símbolos Bopomofo oficiais e crie "
            "grades A4 fixas para traçar e copiar. Sem conta, dados infantis, "
            "nome, data, trabalho salvo, pontuação ou avaliação."
        ),
        "eyebrow": "Impressão grátis · ordem oficial · sem dados infantis",
        "heading": "Folhas Bopomofo (Zhuyin) para traçar e copiar",
        "lead": (
            "Escolha todos os 37 símbolos, uma categoria oficial ou uma seleção "
            "exata. Ajuste as células de exemplo e cópia e imprima em A4."
        ),
        "planner": "Monte as páginas exatas de prática",
        "planner_intro": (
            "Somente símbolos Bopomofo oficiais e configurações de layout são "
            "aceitos. A página nunca pede nome, idade, escola, escrita, voz, "
            "resposta, nota, diagnóstico ou progresso de uma criança."
        ),
        "labels": {
            "presets": "Conjuntos rápidos",
            "all": "Todos os 37",
            "initials": "Iniciais 21",
            "medials": "Mediais 3",
            "finals": "Finais 13",
            "symbols": "Toque para incluir ou remover",
            "trace": "Células de exemplo claro por símbolo",
            "blank": "Células em branco por símbolo",
            "rows": "Linhas por página A4",
            "category": "Categoria ao lado do símbolo",
            "show": "Mostrar",
            "hide": "Ocultar",
            "generate": "Criar folhas",
            "print": "Imprimir estas folhas",
            "result": "{count} linhas · {pages} páginas A4",
            "page": "Página de prática",
            "trace_word": "Exemplos claros",
            "blank_word": "Células em branco",
            "invalid": "Escolha de 1 a 37 símbolos e valores de layout válidos.",
            "toggle": "Alternar",
        },
        "badges": (
            "Os 37 símbolos básicos oficiais",
            "Mesmos ajustes, mesmas páginas ordenadas",
            "Sem nome, data, nota ou avaliação da escrita",
        ),
        "boundary": (
            "O que esta folha faz — e não faz",
            (
                "Coloca símbolos oficiais em células claras e grades vazias "
                "para prática com lápis acompanhada por um adulto. Não demonstra "
                "ordem dos traços, analisa escrita, pontua, diagnostica ou "
                "promete melhorar a escrita."
            ),
        ),
        "how": (
            "Como a folha fixa é criada",
            (
                "Escolha um conjunto rápido ou os símbolos exatos.",
                "Cada símbolo aparece uma vez na ordem oficial do Ministério da "
                "Educação de Taiwan, sem sequência aleatória.",
                "Escolha 2, 4 ou 6 células claras e vazias e 4–6 linhas por "
                "página; os mesmos dados sempre recriam as mesmas folhas.",
            ),
        ),
        "use": (
            "Uso responsável das grades",
            (
                "Consulte o portal oficial de traços antes de demonstrar um "
                "símbolo desconhecido.",
                "Um adulto pode mostrar em outro papel; o aluno pode traçar, "
                "copiar, apontar ou parar sem receber nota.",
                "Use como prática opcional, não como prova de preparo, domínio, "
                "coordenação motora ou dificuldade de aprendizagem.",
            ),
        ),
        "webmcp_description": (
            "Retorna dados determinísticos de páginas A4 para traçar e copiar "
            "1–37 símbolos Bopomofo oficiais. Somente leitura: sem perfil "
            "infantil, nome, texto livre, escrita, upload, resposta, nota, "
            "avaliação, diagnóstico ou promessa de aprendizagem."
        ),
        "faq_title": "Dúvidas sobre folhas Bopomofo",
        "faq": (
            (
                "A folha ensina a ordem oficial dos traços?",
                "Não. O símbolo claro é apenas uma referência visual. Consulte "
                "o portal do Ministério da Educação de Taiwan para os traços.",
            ),
            (
                "A escrita ou os dados de uma criança são coletados?",
                "Não. Só símbolos oficiais e ajustes são usados nesta página; "
                "nada é enviado ou salvo.",
            ),
            (
                "Concluir uma página mede escrita ou domínio de Zhuyin?",
                "Não. Não há nota, nível, ranking, avaliação, diagnóstico ou "
                "afirmação de que concluir a folha prove domínio.",
            ),
        ),
        "index": (
            "Folhas Bopomofo para imprimir",
            (
                "Escolha símbolos Zhuyin oficiais e imprima grades A4 fixas para "
                "traçar e copiar, sem nome, nota ou trabalho salvo."
            ),
        ),
        "inline_link": "Criar uma folha Bopomofo gratuita para imprimir",
        "footer": (
            "Símbolos oficiais · sem dados infantis · sem nota · não ensina ordem dos traços"
        ),
    },
    "de-DE": {
        "title": "Bopomofo-Nachspurblatt | Zhuyin kostenlos ausdrucken",
        "description": (
            "Wähle aus allen 37 offiziellen Bopomofo-Zeichen und erstelle feste "
            "A4-Raster zum Nachspuren und Kopieren. Ohne Konto, Kinderdaten, "
            "Name, Datum, gespeicherte Arbeit, Bewertung oder Schreibanalyse."
        ),
        "eyebrow": "Kostenlos drucken · offizielle Reihenfolge · keine Kinderdaten",
        "heading": "Bopomofo-(Zhuyin-)Blätter zum Nachspuren und Kopieren",
        "lead": (
            "Wähle alle 37 Zeichen, eine offizielle Gruppe oder genau die "
            "gewünschten Zeichen. Passe Vorlagen und Leerfelder an und drucke A4."
        ),
        "planner": "Genaue Übungsseiten erstellen",
        "planner_intro": (
            "Akzeptiert werden nur offizielle Bopomofo-Zeichen und "
            "Layouteinstellungen. Die Seite fragt nie nach Name, Alter, Schule, "
            "Handschrift, Stimme, Antwort, Note, Diagnose oder Fortschritt."
        ),
        "labels": {
            "presets": "Schnellauswahl",
            "all": "Alle 37",
            "initials": "Anlaute 21",
            "medials": "Mediale 3",
            "finals": "Auslaute 13",
            "symbols": "Zeichen antippen oder entfernen",
            "trace": "Helle Vorlagen je Zeichen",
            "blank": "Leere Kopierfelder je Zeichen",
            "rows": "Zeilen je A4-Seite",
            "category": "Gruppenname neben dem Zeichen",
            "show": "Anzeigen",
            "hide": "Ausblenden",
            "generate": "Übungsblätter erstellen",
            "print": "Diese Blätter drucken",
            "result": "{count} Zeichenzeilen · {pages} A4-Seiten",
            "page": "Übungsseite",
            "trace_word": "Helle Vorlagen",
            "blank_word": "Leere Felder",
            "invalid": "Wähle 1–37 offizielle Zeichen und gültige Layoutwerte.",
            "toggle": "Umschalten",
        },
        "badges": (
            "Alle 37 offiziellen Grundzeichen",
            "Gleiche Einstellungen, gleiche Seiten",
            "Kein Name, Datum, Ergebnis oder Schreibtest",
        ),
        "boundary": (
            "Was dieses Blatt leistet — und was nicht",
            (
                "Es setzt offizielle Zeichen in helle Vorlagen und leere "
                "Fadenkreuzfelder für erwachsenengeleitete Stiftübungen. Es "
                "zeigt keine Strichfolge, prüft keine Handschrift, bewertet "
                "nicht, diagnostiziert nicht und verspricht keine Verbesserung."
            ),
        ),
        "how": (
            "So entsteht das feste Arbeitsblatt",
            (
                "Nutze die Schnellauswahl oder tippe die gewünschten Zeichen an.",
                "Jedes Zeichen erscheint einmal in der offiziellen Reihenfolge "
                "des taiwanischen Bildungsministeriums, niemals zufällig.",
                "Wähle 2, 4 oder 6 helle und leere Felder sowie 4–6 Zeilen je "
                "Seite; gleiche Eingaben erzeugen immer gleiche Seiten.",
            ),
        ),
        "use": (
            "Verantwortungsvoller Einsatz der Raster",
            (
                "Prüfe vor dem Vormachen eines unbekannten Zeichens das "
                "offizielle Strichfolge-Portal.",
                "Ein Erwachsener kann auf separatem Papier vormachen; Lernende "
                "dürfen nachspuren, kopieren, zeigen oder ohne Note aufhören.",
                "Das Blatt ist eine freiwillige Übung, kein Nachweis für "
                "Schulreife, Beherrschung, Motorik oder Lernschwierigkeiten.",
            ),
        ),
        "webmcp_description": (
            "Gibt deterministische A4-Seitendaten zum Nachspuren und Kopieren "
            "von 1–37 offiziellen Bopomofo-Zeichen zurück. Nur lesend: keine "
            "Kinderprofile, Namen, Freitexte, Handschrift, Uploads, Antworten, "
            "Noten, Tests, Diagnosen oder Lernversprechen."
        ),
        "faq_title": "Fragen zu Bopomofo-Übungsblättern",
        "faq": (
            (
                "Lehrt das Blatt die offizielle Strichfolge?",
                "Nein. Das helle Zeichen ist nur eine visuelle Kopiervorlage. "
                "Prüfe die Striche im Portal des taiwanischen Bildungsministeriums.",
            ),
            (
                "Werden Handschrift oder Kinderdaten erfasst?",
                "Nein. Nur offizielle Zeichen und Einstellungen werden auf "
                "dieser Seite verwendet; nichts wird übertragen oder gespeichert.",
            ),
            (
                "Misst eine fertige Seite Zhuyin- oder Schreibfähigkeit?",
                "Nein. Es gibt keine Note, Stufe, Rangliste, Bewertung, Diagnose "
                "oder Behauptung, die Fertigstellung beweise Beherrschung.",
            ),
        ),
        "index": (
            "Bopomofo-Übungsblätter zum Ausdrucken",
            (
                "Wähle offizielle Zhuyin-Zeichen und drucke feste A4-Raster zum "
                "Nachspuren und Kopieren, ohne Name, Note oder Speicherung."
            ),
        ),
        "inline_link": "Kostenloses Bopomofo-Übungsblatt erstellen",
        "footer": (
            "Offizielle Zeichen · keine Kinderdaten · keine Note · keine Strichfolge-Anleitung"
        ),
    },
    "fr-FR": {
        "title": "Fiche Bopomofo à tracer et copier | Impression gratuite",
        "description": (
            "Choisissez parmi les 37 symboles Bopomofo officiels et créez des "
            "grilles A4 fixes à tracer et copier. Sans compte, données d'enfant, "
            "nom, date, travail enregistré, note ni évaluation."
        ),
        "eyebrow": "Impression gratuite · ordre officiel · aucune donnée d'enfant",
        "heading": "Fiches Bopomofo (Zhuyin) à tracer et copier",
        "lead": (
            "Choisissez les 37 symboles, une catégorie officielle ou une "
            "sélection précise. Réglez les cases modèles et vierges puis imprimez."
        ),
        "planner": "Créer les pages d'exercice exactes",
        "planner_intro": (
            "Seuls les symboles Bopomofo officiels et les réglages de mise en "
            "page sont acceptés. Aucun nom, âge, école, écriture, voix, réponse, "
            "note, diagnostic ou progrès d'enfant n'est demandé."
        ),
        "labels": {
            "presets": "Sélections rapides",
            "all": "Les 37",
            "initials": "Initiales 21",
            "medials": "Médianes 3",
            "finals": "Finales 13",
            "symbols": "Touchez pour ajouter ou retirer",
            "trace": "Cases modèles claires par symbole",
            "blank": "Cases vierges par symbole",
            "rows": "Lignes par page A4",
            "category": "Catégorie à côté du symbole",
            "show": "Afficher",
            "hide": "Masquer",
            "generate": "Créer les fiches",
            "print": "Imprimer ces fiches",
            "result": "{count} lignes · {pages} pages A4",
            "page": "Page d'exercice",
            "trace_word": "Modèles clairs",
            "blank_word": "Cases vierges",
            "invalid": "Choisissez 1 à 37 symboles et des réglages valides.",
            "toggle": "Basculer",
        },
        "badges": (
            "Les 37 symboles de base officiels",
            "Mêmes réglages, mêmes pages ordonnées",
            "Sans nom, date, note ni évaluation de l'écriture",
        ),
        "boundary": (
            "Ce que fait cette fiche — et ses limites",
            (
                "Elle place des symboles officiels dans des cases claires et "
                "vierges pour une pratique au crayon guidée par un adulte. Elle "
                "ne montre pas l'ordre des traits, n'analyse pas l'écriture, ne "
                "note pas, ne diagnostique pas et ne promet aucun progrès."
            ),
        ),
        "how": (
            "Comment la fiche fixe est créée",
            (
                "Choisissez une sélection rapide ou les symboles précis.",
                "Chaque symbole apparaît une fois dans l'ordre officiel du "
                "ministère taïwanais de l'Éducation, jamais au hasard.",
                "Choisissez 2, 4 ou 6 cases claires et vierges et 4–6 lignes par "
                "page ; les mêmes données recréent toujours les mêmes pages.",
            ),
        ),
        "use": (
            "Utiliser les grilles de façon responsable",
            (
                "Consultez le portail officiel des traits avant de montrer un "
                "symbole inconnu.",
                "Un adulte peut montrer le geste sur une autre feuille ; "
                "l'apprenant peut tracer, copier, pointer ou arrêter sans note.",
                "C'est un exercice facultatif, pas une preuve de préparation, "
                "maîtrise, motricité ou difficulté d'apprentissage.",
            ),
        ),
        "webmcp_description": (
            "Renvoie des données déterministes de pages A4 pour tracer et copier "
            "1–37 symboles Bopomofo officiels. Lecture seule : aucun profil "
            "d'enfant, nom, texte libre, écriture, envoi, réponse, note, "
            "évaluation, diagnostic ou promesse d'apprentissage."
        ),
        "faq_title": "Questions sur les fiches Bopomofo",
        "faq": (
            (
                "La fiche enseigne-t-elle l'ordre officiel des traits ?",
                "Non. Le symbole clair est seulement un repère visuel. Consultez "
                "le portail du ministère taïwanais pour les traits officiels.",
            ),
            (
                "L'écriture ou les données d'un enfant sont-elles recueillies ?",
                "Non. Seuls les symboles officiels et les réglages sont utilisés "
                "sur cette page ; rien n'est envoyé ni conservé.",
            ),
            (
                "Une page terminée mesure-t-elle l'écriture ou le niveau Zhuyin ?",
                "Non. Il n'y a ni note, niveau, classement, évaluation, diagnostic "
                "ni affirmation que terminer la page prouve une maîtrise.",
            ),
        ),
        "index": (
            "Fiches Bopomofo à imprimer",
            (
                "Choisissez des symboles Zhuyin officiels et imprimez des grilles "
                "A4 fixes à tracer et copier, sans nom, note ni sauvegarde."
            ),
        ),
        "inline_link": "Créer gratuitement une fiche Bopomofo à imprimer",
        "footer": (
            "Symboles officiels · aucune donnée d'enfant · aucune note · aucun cours sur les traits"
        ),
    },
    "ja": {
        "title": "注音符号なぞり書き練習シート | 37字を無料印刷",
        "description": (
            "台湾教育部の基本37注音符号から必要な字を選び、固定A4のなぞり書き・書き写し枠を作成。"
            "アカウント、子どもの情報、氏名、日付、保存、採点、手書き評価はありません。"
        ),
        "eyebrow": "無料印刷 · 公式順 · 子どもの情報不要",
        "heading": "注音符号のなぞり書き・書き写し練習シート",
        "lead": (
            "基本37字、公式分類、または必要な字だけを選択。薄い見本枠と空欄の数を調整してA4印刷できます。"
        ),
        "planner": "必要な練習ページを作成",
        "planner_intro": (
            "入力できるのは公式注音符号とレイアウト設定だけです。子どもの氏名、年齢、学校、手書き、"
            "音声、回答、点数、診断、進度は一切求めません。"
        ),
        "labels": {
            "presets": "すぐ選べるセット",
            "all": "基本37字",
            "initials": "声母21字",
            "medials": "介音3字",
            "finals": "韻母13字",
            "symbols": "タップして追加・解除",
            "trace": "1字あたりの薄い見本枠",
            "blank": "1字あたりの空欄",
            "rows": "A4 1ページの文字行",
            "category": "文字の横に分類を表示",
            "show": "表示",
            "hide": "非表示",
            "generate": "練習シートを作成",
            "print": "このシートを印刷",
            "result": "{count}文字行 · A4 {pages}ページ",
            "page": "練習ページ",
            "trace_word": "薄い見本",
            "blank_word": "空欄",
            "invalid": "公式記号を1〜37字選び、対応するレイアウトを指定してください。",
            "toggle": "切り替え",
        },
        "badges": (
            "公式の基本37注音符号",
            "同じ設定なら同じ公式順ページ",
            "氏名・日付・採点・手書き評価なし",
        ),
        "boundary": (
            "このシートでできること・できないこと",
            (
                "選んだ公式記号を薄い見本枠と十字補助線の空欄に配置し、大人と鉛筆で練習できます。"
                "筆順は示さず、手書きを判定・採点・診断せず、上達も保証しません。"
            ),
        ),
        "how": (
            "固定シートの作り方",
            (
                "セットを選ぶか、必要な記号だけをタップします。",
                "各記号は台湾教育部の公式順で1回ずつ並び、ランダムにはなりません。",
                "薄い見本と空欄を各2・4・6枠、1ページを4〜6行から選びます。同じ設定は同じページを再現します。",
            ),
        ),
        "use": (
            "補助枠を責任をもって使う方法",
            (
                "不慣れな記号を示す前に、教育部の公式筆順サイトを確認します。",
                "大人は別の紙で手本を示せます。学習者はなぞる、写す、指す、または採点なしで中止できます。",
                "入学準備、習熟、運動能力、学習上の困難を証明するものではなく、任意の練習として使います。",
            ),
        ),
        "webmcp_description": (
            "公式注音符号1〜37字と固定設定から、なぞり書き・書き写し用A4ページデータを返す読み取り専用ツール。"
            "子どものプロフィール、氏名、自由文、手書き、アップロード、回答、点数、評価、診断、学習効果の主張は受け付けません。"
        ),
        "faq_title": "注音符号練習シートのよくある質問",
        "faq": (
            (
                "シートは公式の筆順を教えますか？",
                "いいえ。薄い文字は視覚的な写し書きの手掛かりだけです。公式筆順は台湾教育部サイトで確認してください。",
            ),
            (
                "子どもの手書きや個人情報を収集しますか？",
                "いいえ。このページ内で公式記号と設定だけを使い、送信も保存もしません。",
            ),
            (
                "完了すると注音や手書きの力を測れますか？",
                "いいえ。点数、段階、順位、評価、診断はなく、完了が習熟の証明になるとも主張しません。",
            ),
        ),
        "index": (
            "印刷用・注音符号なぞり書き練習シート",
            (
                "公式記号を選び、氏名欄・採点・保存なしで固定A4のなぞり書き・書き写し枠を作成します。"
            ),
        ),
        "inline_link": "無料の注音符号練習シートを作成",
        "footer": "公式記号 · 子どもの情報なし · 採点なし · 筆順指導ではありません",
    },
    "ko": {
        "title": "주음부호 따라 쓰기 연습지 | 37개 기호 무료 인쇄",
        "description": (
            "대만 교육부의 기본 주음부호 37개 중 필요한 기호를 골라 고정 A4 따라 쓰기·베껴 쓰기 칸을 만드세요. "
            "계정, 아동 정보, 이름, 날짜, 저장, 채점, 필기 평가가 없습니다."
        ),
        "eyebrow": "무료 인쇄 · 공식 순서 · 아동 정보 불필요",
        "heading": "주음부호 따라 쓰기·베껴 쓰기 연습지",
        "lead": (
            "37개 전체, 공식 분류 또는 필요한 기호만 선택하세요. 옅은 보기 칸과 빈칸 수를 조절해 A4로 인쇄합니다."
        ),
        "planner": "필요한 연습 페이지 만들기",
        "planner_intro": (
            "공식 주음부호와 레이아웃 설정만 입력할 수 있습니다. 아동의 이름, 나이, 학교, 필기, "
            "음성, 답변, 점수, 진단 또는 진도를 묻지 않습니다."
        ),
        "labels": {
            "presets": "빠른 기호 세트",
            "all": "기본 37개",
            "initials": "성모 21개",
            "medials": "개음 3개",
            "finals": "운모 13개",
            "symbols": "눌러서 포함 또는 제외",
            "trace": "기호당 옅은 보기 칸",
            "blank": "기호당 빈칸",
            "rows": "A4 한 쪽의 기호 줄",
            "category": "기호 옆 분류 표시",
            "show": "표시",
            "hide": "숨기기",
            "generate": "연습지 만들기",
            "print": "이 연습지 인쇄",
            "result": "기호 {count}줄 · A4 {pages}쪽",
            "page": "연습 페이지",
            "trace_word": "옅은 보기",
            "blank_word": "빈칸",
            "invalid": "공식 기호 1–37개와 지원되는 레이아웃을 선택하세요.",
            "toggle": "전환",
        },
        "badges": (
            "공식 기본 주음부호 37개",
            "같은 설정, 같은 공식 순서",
            "이름·날짜·채점·필기 평가 없음",
        ),
        "boundary": (
            "이 연습지가 하는 일과 하지 않는 일",
            (
                "선택한 공식 기호를 옅은 보기 칸과 십자 보조선 빈칸에 배치해 성인과 연필로 연습할 수 있습니다. "
                "필순을 보여 주거나 필기를 검사·채점·진단하지 않으며 향상을 보장하지 않습니다."
            ),
        ),
        "how": (
            "고정 연습지를 만드는 방법",
            (
                "빠른 세트를 고르거나 필요한 기호만 누릅니다.",
                "각 기호는 대만 교육부 공식 순서로 한 번씩 나오며 무작위로 섞이지 않습니다.",
                "옅은 보기와 빈칸을 각 2·4·6칸, 한 쪽을 4–6줄로 고릅니다. 같은 설정은 같은 페이지를 만듭니다.",
            ),
        ),
        "use": (
            "보조 칸을 책임 있게 사용하는 방법",
            (
                "익숙하지 않은 기호를 보여 주기 전에 교육부 공식 필순 사이트를 확인합니다.",
                "성인은 다른 종이에 시범을 보일 수 있고, 학습자는 따라 쓰기, 베껴 쓰기, 가리키기 또는 채점 없이 중단할 수 있습니다.",
                "입학 준비, 숙달, 운동 능력 또는 학습 어려움의 증거가 아닌 선택 활동으로 사용합니다.",
            ),
        ),
        "webmcp_description": (
            "공식 주음부호 1–37개와 고정 설정으로 따라 쓰기·베껴 쓰기 A4 페이지 데이터를 반환하는 읽기 전용 도구입니다. "
            "아동 프로필, 이름, 자유 문장, 필기, 업로드, 답변, 점수, 평가, 진단 또는 학습 효과 주장을 받지 않습니다."
        ),
        "faq_title": "주음부호 연습지 자주 묻는 질문",
        "faq": (
            (
                "연습지가 공식 필순을 가르치나요?",
                "아니요. 옅은 기호는 시각적인 베껴 쓰기 보기일 뿐입니다. 공식 필순은 대만 교육부 사이트에서 확인하세요.",
            ),
            (
                "아동의 필기나 개인정보를 수집하나요?",
                "아니요. 공식 기호와 설정만 현재 페이지에서 사용하며 전송하거나 저장하지 않습니다.",
            ),
            (
                "페이지를 마치면 주음부호나 필기 능력을 측정하나요?",
                "아니요. 점수, 단계, 순위, 평가, 진단이 없으며 완료가 숙달을 증명한다고 주장하지 않습니다.",
            ),
        ),
        "index": (
            "인쇄용 주음부호 따라 쓰기 연습지",
            (
                "공식 기호를 골라 이름 칸, 채점, 저장 없이 고정 A4 따라 쓰기·베껴 쓰기 칸을 만듭니다."
            ),
        ),
        "inline_link": "무료 주음부호 따라 쓰기 연습지 만들기",
        "footer": "공식 기호 · 아동 정보 없음 · 채점 없음 · 필순 지도 아님",
    },
    "zh-Hant": {
        "title": "注音符號描寫練習表產生器｜37 個注音免費列印",
        "description": (
            "從台灣教育部 37 個基本注音符號中選取任意符號，免費產生固定 A4 描寫與仿寫格；"
            "免登入、不收兒童資料、無姓名日期欄、不儲存、不計分、不評量書寫。"
        ),
        "eyebrow": "免費列印 · 教育部順序 · 不收兒童資料",
        "heading": "可列印注音符號描寫與仿寫練習表",
        "lead": (
            "選全部 37 個、教育部分類，或只選今天需要的符號；調整淡字格與空白格後列印固定 A4 頁面。"
        ),
        "planner": "精準建立要使用的練習頁",
        "planner_intro": (
            "本頁只接受官方注音符號與版面設定，不會要求孩子的姓名、年齡、學校、書寫、聲音、"
            "答案、分數、診斷或學習進度。"
        ),
        "labels": {
            "presets": "快速選擇",
            "all": "全部 37 個",
            "initials": "聲母 21 個",
            "medials": "介音 3 個",
            "finals": "韻母 13 個",
            "symbols": "點選要加入或移除的符號",
            "trace": "每個符號的淡字格數",
            "blank": "每個符號的空白仿寫格數",
            "rows": "每張 A4 紙的符號行數",
            "category": "符號旁是否顯示分類",
            "show": "顯示",
            "hide": "隱藏",
            "generate": "產生練習表",
            "print": "列印這些練習表",
            "result": "共 {count} 行符號 · {pages} 張 A4",
            "page": "練習頁",
            "trace_word": "淡字描寫",
            "blank_word": "空白仿寫",
            "invalid": "請選 1–37 個官方注音符號與支援的版面設定。",
            "toggle": "切換",
        },
        "badges": (
            "完整 37 個基本注音符號",
            "相同設定、相同官方順序",
            "無姓名日期、不計分、不評量書寫",
        ),
        "boundary": (
            "這份練習表會做什麼、不會做什麼",
            (
                "工具把選取的官方符號放入淡字格與十字輔助線空白格，供成人陪同的紙筆活動使用。"
                "它不示範筆順、不檢查或評分書寫、不診斷，也不承諾改善書寫。"
            ),
        ),
        "how": (
            "固定練習表如何產生",
            (
                "使用快速分類，或逐一點選真正需要的符號。",
                "每個符號只出現一次，並依台灣教育部官方順序排列，不做即時隨機排序。",
                "淡字格與空白格可選 2、4、6 格，每頁可選 4–6 行；相同設定永遠重現相同頁面。",
            ),
        ),
        "use": (
            "負責任使用輔助格的方法",
            (
                "示範不熟悉的符號前，先查閱教育部官方注音筆順入口。",
                "成人可在另一張紙上示範；學習者可以描寫、仿寫、指認，或在沒有分數的情況下停止。",
                "把它當作選用練習，不當成入學準備、熟練度、動作能力或學習困難的證據。",
            ),
        ),
        "webmcp_description": (
            "依 1–37 個官方注音符號與固定版面設定，回傳可重現的 A4 描寫與仿寫頁面資料。"
            "唯讀工具：不接收兒童檔案、姓名、自由文字、書寫、上傳、答案、分數、評量、診斷或成效宣稱。"
        ),
        "faq_title": "注音符號練習表常見問題",
        "faq": (
            (
                "練習表會教官方筆順嗎？",
                "不會。淡色符號只作為視覺仿寫提示；正式筆順請查閱台灣教育部官方入口。",
            ),
            (
                "會收集孩子的書寫或個人資料嗎？",
                "不會。固定符號與版面設定只在目前頁面使用，不會上傳或儲存。",
            ),
            (
                "完成一頁能衡量注音或書寫能力嗎？",
                "不能。它沒有分數、分級、排名、評量或診斷，也不宣稱完成就代表熟練。",
            ),
        ),
        "index": (
            "可列印注音符號描寫練習表",
            (
                "任選官方注音符號，免姓名欄、不計分、不儲存，產生固定 A4 描寫與仿寫格。"
            ),
        ),
        "inline_link": "免費產生可列印注音符號練習表",
        "footer": "官方符號 · 不收兒童資料 · 不計分 · 並非筆順教學",
    },
    "zh-Hans": {
        "title": "注音符号描写练习表生成器｜37 个符号免费打印",
        "description": (
            "从台湾教育部 37 个基本注音符号中任选符号，免费生成固定 A4 描写与临摹格；"
            "无需登录、不收集儿童数据、无姓名日期栏、不保存、不计分、不评估书写。"
        ),
        "eyebrow": "免费打印 · 教育部顺序 · 不收集儿童数据",
        "heading": "可打印注音符号描写与临摹练习表",
        "lead": (
            "选择全部 37 个、官方分类，或只选今天需要的符号；调整淡字格与空白格后打印固定 A4 页面。"
        ),
        "planner": "准确创建要使用的练习页",
        "planner_intro": (
            "本页只接受官方注音符号与版面设置，不会要求儿童的姓名、年龄、学校、书写、声音、"
            "答案、分数、诊断或学习进度。"
        ),
        "labels": {
            "presets": "快速选择",
            "all": "全部 37 个",
            "initials": "声母 21 个",
            "medials": "介音 3 个",
            "finals": "韵母 13 个",
            "symbols": "点击要加入或移除的符号",
            "trace": "每个符号的淡字格数",
            "blank": "每个符号的空白临摹格数",
            "rows": "每张 A4 纸的符号行数",
            "category": "符号旁是否显示分类",
            "show": "显示",
            "hide": "隐藏",
            "generate": "生成练习表",
            "print": "打印这些练习表",
            "result": "共 {count} 行符号 · {pages} 张 A4",
            "page": "练习页",
            "trace_word": "淡字描写",
            "blank_word": "空白临摹",
            "invalid": "请选择 1–37 个官方注音符号与支持的版面设置。",
            "toggle": "切换",
        },
        "badges": (
            "完整 37 个基本注音符号",
            "相同设置、相同官方顺序",
            "无姓名日期、不计分、不评估书写",
        ),
        "boundary": (
            "这份练习表会做什么、不会做什么",
            (
                "工具把选择的官方符号放入淡字格与十字辅助线空白格，供成人陪同的纸笔活动使用。"
                "它不示范笔顺、不检查或评判书写、不诊断，也不承诺改善书写。"
            ),
        ),
        "how": (
            "固定练习表如何生成",
            (
                "使用快速分类，或逐一点击真正需要的符号。",
                "每个符号只出现一次，并按台湾教育部官方顺序排列，不进行即时随机排序。",
                "淡字格与空白格可选 2、4、6 格，每页可选 4–6 行；相同设置始终复现相同页面。",
            ),
        ),
        "use": (
            "负责任使用辅助格的方法",
            (
                "示范不熟悉的符号前，先查阅教育部官方注音笔顺入口。",
                "成人可在另一张纸上示范；学习者可以描写、临摹、指认，或在没有分数的情况下停止。",
                "把它作为可选练习，不作为入学准备、熟练度、动作能力或学习困难的证据。",
            ),
        ),
        "webmcp_description": (
            "按 1–37 个官方注音符号与固定版面设置，返回可复现的 A4 描写与临摹页面数据。"
            "只读工具：不接收儿童档案、姓名、自由文本、书写、上传、答案、分数、评估、诊断或效果声明。"
        ),
        "faq_title": "注音符号练习表常见问题",
        "faq": (
            (
                "练习表会教官方笔顺吗？",
                "不会。淡色符号只是视觉临摹提示；正式笔顺请查阅台湾教育部官方入口。",
            ),
            (
                "会收集儿童的书写或个人数据吗？",
                "不会。固定符号与版面设置只在当前页面使用，不会上载或保存。",
            ),
            (
                "完成一页能衡量注音或书写能力吗？",
                "不能。它没有分数、分级、排名、评估或诊断，也不宣称完成就代表熟练。",
            ),
        ),
        "index": (
            "可打印注音符号描写练习表",
            (
                "任选官方注音符号，无姓名栏、不计分、不保存，生成固定 A4 描写与临摹格。"
            ),
        ),
        "inline_link": "免费生成可打印注音符号练习表",
        "footer": "官方符号 · 不收集儿童数据 · 不计分 · 并非笔顺教学",
    },
}


def build_practice_sheets(
    symbols: list[str],
    trace_cells: int,
    blank_cells: int,
    rows_per_page: int,
    show_category: bool,
) -> dict[str, object]:
    if not isinstance(symbols, list):
        raise TypeError("symbols must be an array")
    for name, value in (
        ("trace_cells", trace_cells),
        ("blank_cells", blank_cells),
        ("rows_per_page", rows_per_page),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer")
    if not isinstance(show_category, bool):
        raise TypeError("show_category must be a boolean")
    if not 1 <= len(symbols) <= len(OFFICIAL_SYMBOLS):
        raise ValueError("choose between 1 and 37 symbols")
    if trace_cells not in CELL_COUNTS or blank_cells not in CELL_COUNTS:
        raise ValueError("unsupported cell count")
    if rows_per_page not in ROWS_PER_PAGE:
        raise ValueError("unsupported rows_per_page")
    if any(not isinstance(symbol, str) for symbol in symbols):
        raise TypeError("each symbol must be a string")
    if len(symbols) != len(set(symbols)):
        raise ValueError("symbols must be unique")
    official_order = {symbol: index for index, symbol in enumerate(OFFICIAL_SYMBOLS)}
    if any(symbol not in official_order for symbol in symbols):
        raise ValueError("unsupported Bopomofo symbol")
    ordered = sorted(symbols, key=official_order.__getitem__)
    rows = [
        {
            "symbol": symbol,
            "category": CATEGORY_BY_SYMBOL[symbol],
            "trace_cells": trace_cells,
            "blank_cells": blank_cells,
        }
        for symbol in ordered
    ]
    pages = [
        rows[start : start + rows_per_page]
        for start in range(0, len(rows), rows_per_page)
    ]
    return {
        "selected_inputs": {
            "symbols": ordered,
            "trace_cells": trace_cells,
            "blank_cells": blank_cells,
            "rows_per_page": rows_per_page,
            "show_category": show_category,
        },
        "pages": [
            {"page_number": index + 1, "rows": page}
            for index, page in enumerate(pages)
        ],
    }


STYLE = r"""
:root{--ink:#20283c;--muted:#667087;--line:#dce2ef;--paper:#fff;--bg:#f4f7fc;--indigo:#3949a3;--violet:#8067d8;--trace:#bcc2d0;--soft:#eef1ff;--shadow:0 22px 60px rgba(48,57,110,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 58%,#e9eef9 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--indigo)}.wrap{width:min(1180px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--indigo);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.control-title{display:block;font-size:13px;font-weight:850;color:var(--indigo);margin:20px 0 7px;white-space:nowrap;overflow-x:auto}.presets,.picker,.actions{display:flex;gap:8px;flex-wrap:wrap}.preset,.symbol-button{border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;font:inherit}.preset{border-radius:999px;padding:9px 14px;font-weight:800;white-space:nowrap}.preset.active,.symbol-button.selected{color:#fff;border-color:transparent;background:linear-gradient(135deg,var(--indigo),var(--violet))}.picker{margin-top:9px}.symbol-button{width:48px;height:48px;border-radius:14px;font-size:25px;font-weight:900;line-height:1}.controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--indigo);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,button{font:inherit}select{width:100%;min-height:46px;border:1px solid #c9d1e3;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.actions{margin-top:18px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--indigo),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}.button.ghost{background:#fff;color:var(--indigo);border:1px solid var(--line);box-shadow:none}.note{background:#fff7dc;border:1px solid #ead7a0;border-radius:16px;padding:13px 15px;white-space:nowrap;overflow-x:auto}
.worksheet-pages{display:grid;grid-template-columns:1fr;gap:20px;margin-top:20px}.worksheet-page{background:#fff;border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 14px 34px rgba(48,57,110,.09);break-inside:avoid;page-break-inside:avoid}.page-head{display:flex;justify-content:space-between;gap:12px;border-bottom:2px solid var(--ink);padding-bottom:8px;margin-bottom:12px;font-size:13px;font-weight:850;color:var(--muted);white-space:nowrap}.practice-row{display:grid;grid-template-columns:84px minmax(0,1fr);gap:12px;align-items:center;padding:9px 0;border-bottom:1px dashed var(--line);break-inside:avoid}.practice-row:last-child{border-bottom:0}.symbol-key{text-align:center;min-width:0}.symbol-key strong{display:block;font-size:44px;line-height:1;white-space:nowrap}.category-label{display:block;color:var(--muted);font-size:12px;font-weight:800;margin-top:5px;white-space:nowrap;overflow-x:auto}.cell-strip{display:flex;gap:7px;overflow-x:auto;padding:2px}.practice-cell{position:relative;flex:0 0 52px;width:52px;height:52px;border:1.5px solid #cfd5e2;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:700;line-height:1}.practice-cell::before,.practice-cell::after{content:"";position:absolute;background:#e8ebf2;z-index:0}.practice-cell::before{top:4px;bottom:4px;left:50%;width:1px}.practice-cell::after{left:4px;right:4px;top:50%;height:1px}.practice-cell span{position:relative;z-index:1}.practice-cell.trace span{color:var(--trace)}.practice-cell.blank span{visibility:hidden}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ol,.card ul{padding-left:22px}.card li{margin:8px 0}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}.footer{background:var(--indigo);color:#f5f6ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}@media(max-width:620px){.controls{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1180px)}.practice-row{grid-template-columns:68px minmax(0,1fr)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.planner>h2,.planner form,.planner>.intro,.note,.button,.app-card,.footer,.grid,.faq{display:none!important}body{background:#fff}.wrap{width:100%}.planner{box-shadow:none;border:0;padding:0;margin:0}.worksheet-pages{display:block;margin:0}.worksheet-page{border:0;border-radius:0;box-shadow:none;padding:0;margin:0;break-after:page;page-break-after:always}.worksheet-page:last-child{break-after:auto;page-break-after:auto}.page-head{font-size:9pt;margin-bottom:3mm}.practice-row{grid-template-columns:20mm minmax(0,1fr);gap:3mm;padding:1.5mm 0}.worksheet-page.rows-4 .practice-row{height:60mm}.worksheet-page.rows-5 .practice-row{height:48mm}.worksheet-page.rows-6 .practice-row{height:40mm}.symbol-key strong{font-size:34pt}.category-label{font-size:8pt}.cell-strip{gap:1.6mm;overflow:hidden}.practice-cell{flex-basis:12.5mm;width:12.5mm;height:12.5mm;border-radius:1.5mm;font-size:23pt}.practice-cell::before{top:1mm;bottom:1mm}.practice-cell::after{left:1mm;right:1mm}@page{size:A4 portrait;margin:10mm}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("bopomofo-practice-config").textContent);
  const form = document.getElementById("bopomofo-practice-planner");
  const picker = document.getElementById("symbol-picker");
  const fields = {
    trace_cells: document.getElementById("trace-cells"),
    blank_cells: document.getElementById("blank-cells"),
    rows_per_page: document.getElementById("rows-per-page"),
    show_category: document.getElementById("show-category")
  };
  const summary = document.getElementById("result-summary");
  const pageList = document.getElementById("worksheet-pages");
  const printButton = document.getElementById("print-sheets");
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
    for (const name of ["trace_cells", "blank_cells", "rows_per_page"]) {
      const value = input[name];
      const choices = config.inputSchema.properties[name].enum;
      if (typeof value !== "number" || !Number.isInteger(value) ||
          !choices.includes(value)) {
        throw new RangeError(`${name} is not supported.`);
      }
    }
    if (typeof input.show_category !== "boolean") {
      throw new TypeError("show_category must be a boolean.");
    }
    return buildPracticeSheets(input);
  }

  function buildPracticeSheets(input) {
    const wanted = new Set(input.symbols);
    const rows = config.symbols
      .filter((item) => wanted.has(item.symbol))
      .map((item) => ({
        symbol: item.symbol,
        category: item.category,
        trace_cells: input.trace_cells,
        blank_cells: input.blank_cells
      }));
    const pages = [];
    for (let start = 0; start < rows.length; start += input.rows_per_page) {
      pages.push({
        page_number: pages.length + 1,
        rows: rows.slice(start, start + input.rows_per_page)
      });
    }
    return {
      selected_inputs: {
        symbols: rows.map((row) => row.symbol),
        trace_cells: input.trace_cells,
        blank_cells: input.blank_cells,
        rows_per_page: input.rows_per_page,
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

  function makeCell(symbol, kind) {
    const cell = document.createElement("div");
    cell.className = `practice-cell ${kind}`;
    const value = document.createElement("span");
    value.textContent = symbol;
    cell.appendChild(value);
    return cell;
  }

  function makeRow(row, showCategory) {
    const element = document.createElement("article");
    element.className = "practice-row";
    const key = document.createElement("div");
    key.className = "symbol-key";
    const symbol = document.createElement("strong");
    symbol.textContent = row.symbol;
    key.appendChild(symbol);
    if (showCategory) {
      const category = document.createElement("span");
      category.className = "category-label";
      category.textContent = config.categoryLabels[row.category];
      key.appendChild(category);
    }
    const cells = document.createElement("div");
    cells.className = "cell-strip";
    for (let index = 0; index < row.trace_cells; index += 1) {
      cells.appendChild(makeCell(row.symbol, "trace"));
    }
    for (let index = 0; index < row.blank_cells; index += 1) {
      cells.appendChild(makeCell(row.symbol, "blank"));
    }
    element.append(key, cells);
    return element;
  }

  function makePage(page, result) {
    const section = document.createElement("section");
    section.className = `worksheet-page rows-${result.selected_inputs.rows_per_page}`;
    const header = document.createElement("div");
    header.className = "page-head";
    const title = document.createElement("span");
    title.textContent = `${config.labels.page} ${page.page_number}`;
    const settings = document.createElement("span");
    settings.textContent = `${config.labels.traceWord} ${result.selected_inputs.trace_cells} · ${config.labels.blankWord} ${result.selected_inputs.blank_cells}`;
    header.append(title, settings);
    for (const row of page.rows) {
      section.appendChild(makeRow(row, result.selected_inputs.show_category));
    }
    section.prepend(header);
    return section;
  }

  function currentInput() {
    return {
      symbols: [...selected],
      trace_cells: Number(fields.trace_cells.value),
      blank_cells: Number(fields.blank_cells.value),
      rows_per_page: Number(fields.rows_per_page.value),
      show_category: fields.show_category.value === "show"
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
      name: "create_private_bopomofo_practice_sheets",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const sheets = validateInput(input);
        const result = {
          result_type: "private_bopomofo_practice_sheets",
          deterministic: true,
          official_symbol_order: true,
          is_not_stroke_order_instruction: true,
          is_not_handwriting_assessment: true,
          no_score_grade_rank_or_diagnosis: true,
          no_child_data_received: true,
          no_learning_outcome_claim: true,
          practice_sheets: sheets,
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
  for (const field of Object.values(fields)) {
    field.addEventListener("change", render);
  }
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
            "trace_cells": {
                "type": "integer",
                "enum": list(CELL_COUNTS),
                "description": labels["trace"],
            },
            "blank_cells": {
                "type": "integer",
                "enum": list(CELL_COUNTS),
                "description": labels["blank"],
            },
            "rows_per_page": {
                "type": "integer",
                "enum": list(ROWS_PER_PAGE),
                "description": labels["rows"],
            },
            "show_category": {
                "type": "boolean",
                "description": labels["category"],
            },
        },
        "required": [
            "symbols",
            "trace_cells",
            "blank_cells",
            "rows_per_page",
            "show_category",
        ],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    base = BASE_COPY[locale]
    labels = t["labels"]
    categories = FLASHCARD_COPY[locale]["categories"]
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
    source_labels = tuple(
        base["source_labels"][index] for index in SOURCE_LABEL_INDEXES
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(source_labels, sources, strict=True)
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_bopomofo_practice_sheet_{locale.lower()}")
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
            "traceWord": labels["trace_word"],
            "blankWord": labels["blank_word"],
            "invalid": labels["invalid"],
            "toggle": labels["toggle"],
        },
        "categoryLabels": categories,
        "toolDescription": t["webmcp_description"],
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(source_labels, sources, strict=True)
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

    def options(values: tuple[int, ...], selected: int) -> str:
        return "".join(
            f'<option value="{value}"'
            f'{" selected" if value == selected else ""}>{value}</option>'
            for value in values
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
<form id="bopomofo-practice-planner"><span class="control-title">{html.escape(labels["presets"])}</span><div class="presets">{preset_buttons}</div><span class="control-title">{html.escape(labels["symbols"])}</span><div class="picker" id="symbol-picker"></div>
<div class="controls"><div class="field"><label for="trace-cells">{html.escape(labels["trace"])}</label><select id="trace-cells">{options(CELL_COUNTS, DEFAULT_TRACE_CELLS)}</select></div><div class="field"><label for="blank-cells">{html.escape(labels["blank"])}</label><select id="blank-cells">{options(CELL_COUNTS, DEFAULT_BLANK_CELLS)}</select></div><div class="field"><label for="rows-per-page">{html.escape(labels["rows"])}</label><select id="rows-per-page">{options(ROWS_PER_PAGE, DEFAULT_ROWS_PER_PAGE)}</select></div><div class="field"><label for="show-category">{html.escape(labels["category"])}</label><select id="show-category"><option value="show" selected>{html.escape(labels["show"])}</option><option value="hide">{html.escape(labels["hide"])}</option></select></div></div>
<div class="actions"><button class="button" type="submit">{html.escape(labels["generate"])}</button><button class="button ghost" type="button" id="print-sheets">{html.escape(labels["print"])}</button></div></form>
<p id="result-summary" class="note" role="status" aria-live="polite"></p><div id="worksheet-pages" class="worksheet-pages"></div>
</section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["boundary"][0])}</h2><p>{html.escape(t["boundary"][1])}</p></article><article class="card"><h2>{html.escape(t["how"][0])}</h2><ol>{how_items}</ol></article><article class="card wide"><h2>{html.escape(t["use"][0])}</h2><ol>{use_items}</ol></article><article class="card wide"><h2>{html.escape(base["sources_title"])}</h2><p>{html.escape(base["sources_intro"])}</p><ul>{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(base["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="bopomofo-practice-config">{config_json}</script>
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


TARGET_ANSWER_SLUG = "bopomofo-tracing-app-for-kids.html"
INBOUND_LINK_CLASS = "bopomofo-practice-sheet-inline-link"
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
            f'data-bopomofo-practice-sheet-link="1" href="{canonical(locale)}" '
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
        print(f"bopomofo practice sheet -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
