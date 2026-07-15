#!/usr/bin/env python3
"""Generate deterministic nine-locale printable Bopomofo bingo cards."""

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
    SYMBOL_VALUES,
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
SLUG = "zhuyin-bingo"
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
GRID_SIZES = (4, 5)
CARD_COUNT_MIN = 1
CARD_COUNT_MAX = 6
SET_NUMBER_MIN = 1
SET_NUMBER_MAX = 999
DEFAULT_GRID_SIZE = 5
DEFAULT_CARD_COUNT = 4
DEFAULT_SET_NUMBER = 1
LCG_MULTIPLIER = 214013
LCG_INCREMENT = 2531011
LCG_MODULUS = 2**31


COPY = {
    "en": {
        "title": "Printable Bopomofo Bingo Card Generator | Zhuyin Sets",
        "description": (
            "Create 1–6 free printable Bopomofo bingo cards in 4×4 or 5×5 "
            "format. A set number reproduces the same Zhuyin cards every "
            "time; no account, child data, scoring, or live random shuffle."
        ),
        "eyebrow": "Free printable · no account · no scoring",
        "heading": "Printable Bopomofo bingo cards",
        "lead": (
            "Choose a grid, card count, and private set number. The same "
            "inputs always rebuild the same cards, ready for an adult-led "
            "offline Zhuyin listening or symbol-finding activity."
        ),
        "planner": "Build your bingo set",
        "planner_intro": (
            "Only the three settings below are used. This page never asks "
            "for a child's name, age, school, voice, handwriting, answers, "
            "or score."
        ),
        "labels": {
            "grid": "Grid size",
            "count": "Number of different cards",
            "set": "Private set number (1–999)",
            "generate": "Generate bingo cards",
            "print": "Print these cards",
            "result": "{count} deterministic bingo cards ready",
            "deterministic": (
                "Keep the same set number to reproduce these exact cards; "
                "change it to create another fixed set."
            ),
            "free": "FREE",
            "card": "Bingo card",
            "set_word": "Set",
            "invalid": "Choose a supported grid, card count, and set number.",
        },
        "badges": (
            "Same inputs, same cards",
            "No child data or browser storage",
            "No score, grade, ranking, or diagnosis",
        ),
        "boundary": (
            "What this generator does—and does not do",
            (
                "It arranges the 37 basic Bopomofo symbols into printable "
                "bingo cards. It does not listen, assess pronunciation, "
                "track answers, score a child, diagnose a learning need, "
                "or promise any learning or memory result."
            ),
        ),
        "how": (
            "How the fixed cards are created",
            (
                "A 4×4 card contains 16 different symbols; a 5×5 card "
                "contains 24 different symbols plus one center free cell.",
                "A documented integer algorithm uses the grid, card number, "
                "and set number to arrange symbols without a live random shuffle.",
                "Every card in one batch is generated separately, while the "
                "same three inputs always reproduce the same complete batch.",
            ),
        ),
        "play": (
            "A simple adult-led way to use the cards",
            (
                "Print one different card for each player or small group.",
                "An adult chooses and says one Bopomofo symbol at a time; "
                "use an official source if pronunciation needs checking.",
                "Players cover the matching symbol with a reusable marker.",
                "Before starting, agree whether a row, column, or diagonal "
                "completes the round; do not turn the activity into a score.",
            ),
        ),
        "webmcp_description": (
            "Return deterministic printable Bopomofo bingo card contents "
            "from a grid size, card count, and set number. Read-only: never "
            "receive child data, record answers, score, assess, diagnose, "
            "or claim a learning outcome."
        ),
        "faq_title": "Printable Bopomofo bingo questions",
        "faq": (
            (
                "Will the same set number make the same cards?",
                "Yes, when the grid size and card count are also unchanged. "
                "The generator uses a fixed integer algorithm, not a live "
                "random shuffle.",
            ),
            (
                "Does this page collect or save information about a child?",
                "No. It only uses grid size, card count, and set number in "
                "the current page and does not upload or store them.",
            ),
            (
                "Does bingo measure Zhuyin ability or pronunciation?",
                "No. It is only a printable activity. It does not listen, "
                "score, grade, rank, assess, or diagnose anyone.",
            ),
        ),
        "index": (
            "Printable Bopomofo Bingo Cards",
            (
                "Build deterministic 4×4 or 5×5 Zhuyin bingo sets for "
                "printing—no account, child data, scoring, or random shuffle."
            ),
        ),
        "inline_link": "Create free printable Bopomofo bingo cards",
        "footer": (
            "Private set number only · no child data · no scoring · "
            "adult-led offline activity"
        ),
    },
    "es-ES": {
        "title": "Generador de cartones de bingo Bopomofo para imprimir",
        "description": (
            "Crea gratis de 1 a 6 cartones de bingo Bopomofo para imprimir "
            "en formato 4×4 o 5×5. El número de conjunto reproduce siempre "
            "los mismos cartones Zhuyin; sin cuenta, datos infantiles, "
            "puntuación ni mezcla aleatoria."
        ),
        "eyebrow": "Gratis para imprimir · sin cuenta · sin puntuación",
        "heading": "Cartones de bingo Bopomofo para imprimir",
        "lead": (
            "Elige cuadrícula, cantidad de cartones y número de conjunto "
            "privado. Las mismas opciones reconstruyen siempre los mismos "
            "cartones para una actividad Zhuyin offline guiada por un adulto."
        ),
        "planner": "Crea tu conjunto de bingo",
        "planner_intro": (
            "Solo se usan estos tres ajustes. La página nunca pide nombre, "
            "edad, colegio, voz, escritura, respuestas ni puntuación del menor."
        ),
        "labels": {
            "grid": "Tamaño de la cuadrícula",
            "count": "Número de cartones diferentes",
            "set": "Número de conjunto privado (1–999)",
            "generate": "Generar cartones",
            "print": "Imprimir estos cartones",
            "result": "{count} cartones deterministas listos",
            "deterministic": (
                "Conserva el número para repetir estos cartones exactos; "
                "cámbialo para crear otro conjunto fijo."
            ),
            "free": "LIBRE",
            "card": "Cartón",
            "set_word": "Conjunto",
            "invalid": "Elige una cuadrícula, cantidad y número válidos.",
        },
        "badges": (
            "Mismas opciones, mismos cartones",
            "Sin datos infantiles ni almacenamiento",
            "Sin nota, clasificación ni diagnóstico",
        ),
        "boundary": (
            "Qué hace este generador y qué no",
            (
                "Distribuye los 37 símbolos Bopomofo básicos en cartones "
                "imprimibles. No escucha, evalúa pronunciación, registra "
                "respuestas, puntúa, diagnostica ni promete resultados de "
                "aprendizaje o memoria."
            ),
        ),
        "how": (
            "Cómo se crean los cartones fijos",
            (
                "Un cartón 4×4 incluye 16 símbolos distintos; uno 5×5 "
                "incluye 24 y una casilla central libre.",
                "Un algoritmo entero documentado usa cuadrícula, número de "
                "cartón y conjunto, sin un sorteo aleatorio en vivo.",
                "Cada cartón se genera por separado y las mismas tres "
                "opciones reproducen siempre el lote completo.",
            ),
        ),
        "play": (
            "Una forma sencilla de jugar con un adulto",
            (
                "Imprime un cartón diferente para cada jugador o grupo.",
                "Un adulto elige y pronuncia un símbolo; consulta una fuente "
                "oficial si necesita comprobar la pronunciación.",
                "Cada jugador cubre el símbolo coincidente.",
                "Acordad antes si completa la ronda una fila, columna o "
                "diagonal; no conviertas la actividad en una nota.",
            ),
        ),
        "webmcp_description": (
            "Devuelve cartones deterministas de bingo Bopomofo para imprimir "
            "a partir de cuadrícula, cantidad y conjunto. Solo lectura: no "
            "recibe datos infantiles, registra respuestas, puntúa, evalúa, "
            "diagnostica ni promete resultados."
        ),
        "faq_title": "Preguntas sobre el bingo Bopomofo",
        "faq": (
            (
                "¿El mismo número de conjunto crea los mismos cartones?",
                "Sí, si tampoco cambian cuadrícula y cantidad. Se usa un "
                "algoritmo fijo, no una mezcla aleatoria en vivo.",
            ),
            (
                "¿Se recopilan o guardan datos de un menor?",
                "No. Solo se usan los tres ajustes en esta página; no se "
                "suben ni almacenan.",
            ),
            (
                "¿El bingo mide el dominio o la pronunciación Zhuyin?",
                "No. Es una actividad imprimible: no escucha, puntúa, "
                "califica, clasifica, evalúa ni diagnostica.",
            ),
        ),
        "index": (
            "Cartones de bingo Bopomofo para imprimir",
            (
                "Crea conjuntos Zhuyin 4×4 o 5×5 deterministas para imprimir, "
                "sin cuenta, datos infantiles, puntuación ni mezcla aleatoria."
            ),
        ),
        "inline_link": "Crear cartones de bingo Bopomofo gratis",
        "footer": (
            "Solo número de conjunto privado · sin datos infantiles · "
            "sin puntuación · actividad offline con un adulto"
        ),
    },
    "pt-BR": {
        "title": "Gerador de cartelas de bingo Bopomofo para imprimir",
        "description": (
            "Crie gratuitamente de 1 a 6 cartelas de bingo Bopomofo para "
            "imprimir em 4×4 ou 5×5. O número do conjunto reproduz sempre "
            "as mesmas cartelas Zhuyin, sem conta, dados infantis, "
            "pontuação ou sorteio aleatório."
        ),
        "eyebrow": "Grátis para imprimir · sem conta · sem pontuação",
        "heading": "Cartelas de bingo Bopomofo para imprimir",
        "lead": (
            "Escolha grade, quantidade e número privado do conjunto. As "
            "mesmas opções sempre recriam as mesmas cartelas para uma "
            "atividade Zhuyin offline acompanhada por um adulto."
        ),
        "planner": "Monte seu conjunto de bingo",
        "planner_intro": (
            "Somente estas três opções são usadas. A página nunca pede nome, "
            "idade, escola, voz, escrita, respostas ou pontuação da criança."
        ),
        "labels": {
            "grid": "Tamanho da grade",
            "count": "Número de cartelas diferentes",
            "set": "Número privado do conjunto (1–999)",
            "generate": "Gerar cartelas",
            "print": "Imprimir estas cartelas",
            "result": "{count} cartelas determinísticas prontas",
            "deterministic": (
                "Mantenha o número para recriar estas cartelas exatas; "
                "troque-o para gerar outro conjunto fixo."
            ),
            "free": "LIVRE",
            "card": "Cartela",
            "set_word": "Conjunto",
            "invalid": "Escolha uma grade, quantidade e número válidos.",
        },
        "badges": (
            "Mesmas opções, mesmas cartelas",
            "Sem dados infantis ou armazenamento",
            "Sem nota, ranking ou diagnóstico",
        ),
        "boundary": (
            "O que este gerador faz — e não faz",
            (
                "Ele distribui os 37 símbolos Bopomofo básicos em cartelas "
                "imprimíveis. Não escuta, avalia pronúncia, registra respostas, "
                "pontua, diagnostica nem promete resultado de aprendizagem "
                "ou memória."
            ),
        ),
        "how": (
            "Como as cartelas fixas são criadas",
            (
                "Uma cartela 4×4 tem 16 símbolos diferentes; uma 5×5 tem 24 "
                "e uma casa livre no centro.",
                "Um algoritmo inteiro documentado usa grade, cartela e "
                "conjunto, sem sorteio aleatório ao vivo.",
                "Cada cartela é gerada separadamente e as mesmas três opções "
                "sempre reproduzem o lote completo.",
            ),
        ),
        "play": (
            "Uma forma simples de usar com um adulto",
            (
                "Imprima uma cartela diferente para cada pessoa ou grupo.",
                "Um adulto escolhe e fala um símbolo; consulte uma fonte "
                "oficial se precisar conferir a pronúncia.",
                "Cada pessoa cobre o símbolo correspondente.",
                "Antes de começar, combinem se vale linha, coluna ou diagonal; "
                "não transforme a atividade em nota.",
            ),
        ),
        "webmcp_description": (
            "Retorna cartelas determinísticas de bingo Bopomofo para imprimir "
            "a partir de grade, quantidade e conjunto. Somente leitura: não "
            "recebe dados infantis, registra respostas, pontua, avalia, "
            "diagnostica ou promete resultados."
        ),
        "faq_title": "Dúvidas sobre o bingo Bopomofo",
        "faq": (
            (
                "O mesmo conjunto gera as mesmas cartelas?",
                "Sim, se grade e quantidade também forem iguais. O gerador "
                "usa um algoritmo fixo, não um sorteio ao vivo.",
            ),
            (
                "A página coleta ou salva dados de uma criança?",
                "Não. Ela usa apenas as três opções nesta página e não envia "
                "nem armazena esses dados.",
            ),
            (
                "O bingo mede domínio ou pronúncia de Zhuyin?",
                "Não. É apenas uma atividade imprimível; não escuta, pontua, "
                "classifica, avalia ou diagnostica.",
            ),
        ),
        "index": (
            "Cartelas de bingo Bopomofo para imprimir",
            (
                "Crie conjuntos Zhuyin 4×4 ou 5×5 determinísticos para "
                "imprimir, sem conta, dados infantis, pontuação ou sorteio."
            ),
        ),
        "inline_link": "Criar cartelas de bingo Bopomofo grátis",
        "footer": (
            "Somente número privado · sem dados infantis · sem pontuação · "
            "atividade offline com um adulto"
        ),
    },
    "de-DE": {
        "title": "Bopomofo-Bingokarten zum Ausdrucken | Zhuyin-Generator",
        "description": (
            "Erstelle kostenlos 1–6 Bopomofo-Bingokarten im 4×4- oder "
            "5×5-Format. Eine Setnummer erzeugt stets dieselben Zhuyin-Karten; "
            "ohne Konto, Kinderdaten, Bewertung oder Zufallsmischung."
        ),
        "eyebrow": "Kostenlos druckbar · ohne Konto · ohne Bewertung",
        "heading": "Bopomofo-Bingokarten zum Ausdrucken",
        "lead": (
            "Wähle Raster, Kartenanzahl und private Setnummer. Dieselben "
            "Eingaben erzeugen stets dieselben Karten für eine offline "
            "durch Erwachsene begleitete Zhuyin-Aktivität."
        ),
        "planner": "Bingo-Set erstellen",
        "planner_intro": (
            "Nur diese drei Einstellungen werden verwendet. Die Seite fragt "
            "nie nach Name, Alter, Schule, Stimme, Handschrift, Antworten "
            "oder Punktzahl eines Kindes."
        ),
        "labels": {
            "grid": "Rastergröße",
            "count": "Anzahl verschiedener Karten",
            "set": "Private Setnummer (1–999)",
            "generate": "Bingokarten erstellen",
            "print": "Diese Karten drucken",
            "result": "{count} feste Bingokarten sind bereit",
            "deterministic": (
                "Behalte die Setnummer für exakt diese Karten; ändere sie "
                "für ein anderes festes Set."
            ),
            "free": "FREI",
            "card": "Bingokarte",
            "set_word": "Set",
            "invalid": "Wähle gültiges Raster, Kartenanzahl und Setnummer.",
        },
        "badges": (
            "Gleiche Eingaben, gleiche Karten",
            "Keine Kinderdaten oder Browserspeicherung",
            "Keine Note, Rangliste oder Diagnose",
        ),
        "boundary": (
            "Was dieser Generator leistet — und was nicht",
            (
                "Er ordnet die 37 grundlegenden Bopomofo-Zeichen auf "
                "druckbaren Karten an. Er hört nicht zu, bewertet keine "
                "Aussprache, speichert keine Antworten, benotet und "
                "diagnostiziert nicht und verspricht keinen Lernerfolg."
            ),
        ),
        "how": (
            "So entstehen die festen Karten",
            (
                "Eine 4×4-Karte enthält 16 verschiedene Zeichen; eine "
                "5×5-Karte 24 Zeichen plus ein freies Mittelfeld.",
                "Ein dokumentierter Ganzzahl-Algorithmus verwendet Raster, "
                "Kartennummer und Setnummer ohne laufende Zufallsmischung.",
                "Jede Karte wird einzeln erzeugt; dieselben drei Eingaben "
                "stellen immer den vollständigen Satz wieder her.",
            ),
        ),
        "play": (
            "Einfache Nutzung mit Begleitung",
            (
                "Drucke für jede Person oder Kleingruppe eine andere Karte.",
                "Ein Erwachsener wählt und spricht ein Zeichen; bei Bedarf "
                "hilft eine offizielle Quelle zur Aussprache.",
                "Die Spielenden decken das passende Zeichen ab.",
                "Legt vorher Reihe, Spalte oder Diagonale als Abschluss fest; "
                "macht daraus keine Benotung.",
            ),
        ),
        "webmcp_description": (
            "Gibt feste druckbare Bopomofo-Bingokarten aus Raster, Anzahl "
            "und Setnummer zurück. Schreibgeschützt: keine Kinderdaten, "
            "Antwortaufzeichnung, Bewertung, Diagnose oder Erfolgszusage."
        ),
        "faq_title": "Fragen zu Bopomofo-Bingo",
        "faq": (
            (
                "Erzeugt dieselbe Setnummer dieselben Karten?",
                "Ja, wenn Raster und Kartenanzahl ebenfalls gleich bleiben. "
                "Es gilt ein fester Algorithmus statt einer Zufallsmischung.",
            ),
            (
                "Werden Daten über ein Kind erhoben oder gespeichert?",
                "Nein. Nur die drei Einstellungen werden auf dieser Seite "
                "verwendet; sie werden weder hochgeladen noch gespeichert.",
            ),
            (
                "Misst Bingo Zhuyin-Kenntnisse oder Aussprache?",
                "Nein. Es ist nur eine Druckaktivität und hört, bewertet, "
                "benotet, ordnet oder diagnostiziert niemanden.",
            ),
        ),
        "index": (
            "Bopomofo-Bingokarten zum Ausdrucken",
            (
                "Feste Zhuyin-Sets in 4×4 oder 5×5 erstellen—ohne Konto, "
                "Kinderdaten, Bewertung oder Zufallsmischung."
            ),
        ),
        "inline_link": "Kostenlose Bopomofo-Bingokarten erstellen",
        "footer": (
            "Nur private Setnummer · keine Kinderdaten · keine Bewertung · "
            "offline durch Erwachsene begleitet"
        ),
    },
    "fr-FR": {
        "title": "Générateur de grilles de bingo Bopomofo à imprimer",
        "description": (
            "Créez gratuitement 1 à 6 grilles de bingo Bopomofo en 4×4 ou "
            "5×5. Un numéro de série reproduit toujours les mêmes grilles "
            "Zhuyin, sans compte, données d'enfant, score ni tirage aléatoire."
        ),
        "eyebrow": "Gratuit à imprimer · sans compte · sans score",
        "heading": "Grilles de bingo Bopomofo à imprimer",
        "lead": (
            "Choisissez la grille, le nombre de cartes et un numéro de série "
            "privé. Les mêmes réglages recréent les mêmes cartes pour une "
            "activité Zhuyin hors ligne encadrée par un adulte."
        ),
        "planner": "Créer votre série de bingo",
        "planner_intro": (
            "Seuls ces trois réglages sont utilisés. La page ne demande "
            "jamais le nom, l'âge, l'école, la voix, l'écriture, les réponses "
            "ou le score d'un enfant."
        ),
        "labels": {
            "grid": "Taille de la grille",
            "count": "Nombre de cartes différentes",
            "set": "Numéro de série privé (1–999)",
            "generate": "Générer les cartes",
            "print": "Imprimer ces cartes",
            "result": "{count} cartes déterministes prêtes",
            "deterministic": (
                "Gardez le numéro pour retrouver exactement ces cartes ; "
                "changez-le pour créer une autre série fixe."
            ),
            "free": "LIBRE",
            "card": "Carte",
            "set_word": "Série",
            "invalid": "Choisissez une grille, un nombre et une série valides.",
        },
        "badges": (
            "Mêmes réglages, mêmes cartes",
            "Aucune donnée d'enfant ni stockage",
            "Aucune note, classement ou diagnostic",
        ),
        "boundary": (
            "Ce que fait ce générateur — et ce qu'il ne fait pas",
            (
                "Il répartit les 37 symboles Bopomofo de base sur des cartes "
                "imprimables. Il n'écoute pas, n'évalue pas la prononciation, "
                "n'enregistre pas les réponses, ne note pas, ne diagnostique "
                "pas et ne promet aucun résultat."
            ),
        ),
        "how": (
            "Comment les cartes fixes sont créées",
            (
                "Une carte 4×4 contient 16 symboles différents ; une 5×5 en "
                "contient 24 avec une case libre au centre.",
                "Un algorithme entier documenté utilise grille, numéro de "
                "carte et série, sans tirage aléatoire en direct.",
                "Chaque carte est générée séparément et les trois mêmes "
                "réglages reproduisent toujours le lot complet.",
            ),
        ),
        "play": (
            "Une utilisation simple encadrée par un adulte",
            (
                "Imprimez une carte différente par personne ou petit groupe.",
                "Un adulte choisit et prononce un symbole ; consultez une "
                "source officielle si la prononciation doit être vérifiée.",
                "Chaque personne couvre le symbole correspondant.",
                "Décidez avant de commencer si ligne, colonne ou diagonale "
                "termine la manche ; n'en faites pas une note.",
            ),
        ),
        "webmcp_description": (
            "Renvoie des grilles de bingo Bopomofo déterministes à partir "
            "d'une taille, d'un nombre et d'une série. Lecture seule : aucune "
            "donnée d'enfant, réponse, note, évaluation, diagnostic ou promesse."
        ),
        "faq_title": "Questions sur le bingo Bopomofo",
        "faq": (
            (
                "Le même numéro reproduit-il les mêmes cartes ?",
                "Oui, si la grille et le nombre de cartes ne changent pas. "
                "Un algorithme fixe remplace tout tirage aléatoire en direct.",
            ),
            (
                "La page collecte-t-elle des données sur un enfant ?",
                "Non. Seuls les trois réglages sont utilisés dans la page ; "
                "ils ne sont ni envoyés ni stockés.",
            ),
            (
                "Ce bingo mesure-t-il le niveau ou la prononciation Zhuyin ?",
                "Non. C'est uniquement une activité imprimable : elle "
                "n'écoute, ne note, ne classe, n'évalue et ne diagnostique pas.",
            ),
        ),
        "index": (
            "Grilles de bingo Bopomofo à imprimer",
            (
                "Créez des séries Zhuyin 4×4 ou 5×5 déterministes, sans "
                "compte, données d'enfant, score ni tirage aléatoire."
            ),
        ),
        "inline_link": "Créer gratuitement des cartes de bingo Bopomofo",
        "footer": (
            "Numéro privé uniquement · aucune donnée d'enfant · aucun score · "
            "activité hors ligne encadrée"
        ),
    },
    "ja": {
        "title": "注音符号（ボポモフォ）ビンゴカード無料作成・印刷",
        "description": (
            "4×4または5×5の注音符号（ボポモフォ）ビンゴカードを1〜6枚無料で作成。"
            "同じセット番号なら同じカードを再現できます。登録、子どもの個人情報、採点、"
            "その場限りのランダム生成はありません。"
        ),
        "eyebrow": "無料印刷 · 登録不要 · 採点なし",
        "heading": "注音符号ビンゴカード作成ツール",
        "lead": (
            "マス数、カード枚数、非公開のセット番号を選ぶだけ。同じ設定で同じカードを"
            "再作成でき、大人が進行するオフラインの注音符号探しに使えます。"
        ),
        "planner": "ビンゴセットを作る",
        "planner_intro": (
            "使うのは下の3項目だけです。子どもの氏名、年齢、学校、音声、筆跡、回答、"
            "点数を入力することはありません。"
        ),
        "labels": {
            "grid": "マス数",
            "count": "異なるカードの枚数",
            "set": "非公開セット番号（1〜999）",
            "generate": "ビンゴカードを作成",
            "print": "カードを印刷",
            "result": "再現可能なカードを{count}枚作成しました",
            "deterministic": (
                "同じカードを再作成するにはセット番号を保ち、別の固定セットには番号を変更します。"
            ),
            "free": "フリー",
            "card": "ビンゴカード",
            "set_word": "セット",
            "invalid": "対応するマス数、枚数、セット番号を選んでください。",
        },
        "badges": (
            "同じ設定なら同じカード",
            "子どもの情報・ブラウザ保存なし",
            "点数・順位・診断なし",
        ),
        "boundary": (
            "このツールがすること・しないこと",
            (
                "37個の基本注音符号を印刷用カードに配置するだけです。音声を聞く、発音を"
                "評価する、回答を記録する、採点・診断する、学習効果や記憶力向上を約束する"
                "機能はありません。"
            ),
        ),
        "how": (
            "固定カードの作り方",
            (
                "4×4は異なる16符号、5×5は異なる24符号と中央のフリーマスで構成します。",
                "マス数、カード番号、セット番号を使う整数アルゴリズムで配置し、"
                "その場限りのランダム処理は使いません。",
                "各カードは別々に生成し、同じ3設定ならセット全体をいつでも再現できます。",
            ),
        ),
        "play": (
            "大人が進行する使い方",
            (
                "参加者または小グループごとに違うカードを印刷します。",
                "大人が注音符号を1つ選んで読み上げます。発音確認には台湾教育部などの"
                "公式資料を使ってください。",
                "参加者は一致する符号に再利用できる印を置きます。",
                "始める前に縦・横・斜めのどれで終了するか決め、成績にはしません。",
            ),
        ),
        "webmcp_description": (
            "マス数、カード枚数、セット番号から再現可能な注音符号ビンゴ内容を返します。"
            "読み取り専用で、子どもの情報や回答を受け取らず、採点・評価・診断・効果保証をしません。"
        ),
        "faq_title": "注音符号ビンゴのよくある質問",
        "faq": (
            (
                "同じセット番号なら同じカードになりますか？",
                "マス数と枚数も同じなら再現できます。その場のランダム抽選ではなく固定アルゴリズムです。",
            ),
            (
                "子どもの情報を収集・保存しますか？",
                "いいえ。ページ内で3つの設定だけを使い、送信も保存もしません。",
            ),
            (
                "注音の習熟度や発音を測れますか？",
                "いいえ。印刷用の活動であり、音声認識、採点、順位付け、評価、診断は行いません。",
            ),
        ),
        "index": (
            "注音符号ビンゴカード作成・印刷",
            (
                "4×4または5×5の再現可能な注音符号カードを無料作成。登録、"
                "子どもの情報、採点、ランダム生成なし。"
            ),
        ),
        "inline_link": "無料の注音符号ビンゴカードを作成",
        "footer": "非公開セット番号のみ · 子どもの情報なし · 採点なし · 大人進行のオフライン活動",
    },
    "ko": {
        "title": "주음부호(보포모포) 빙고 카드 무료 만들기·인쇄",
        "description": (
            "4×4 또는 5×5 주음부호(보포모포) 빙고 카드를 1~6장 무료로 만드세요. "
            "같은 세트 번호는 같은 카드를 다시 만들며, 가입·아동 정보·채점·실시간 "
            "무작위 섞기가 없습니다."
        ),
        "eyebrow": "무료 인쇄 · 가입 없음 · 채점 없음",
        "heading": "인쇄용 주음부호 빙고 카드",
        "lead": (
            "격자, 카드 수, 비공개 세트 번호를 고르세요. 같은 설정은 항상 같은 카드를 "
            "재현하며, 어른이 진행하는 오프라인 주음부호 찾기 활동에 쓸 수 있습니다."
        ),
        "planner": "빙고 세트 만들기",
        "planner_intro": (
            "아래 세 가지 설정만 사용합니다. 아동의 이름, 나이, 학교, 음성, 필기, 답변, "
            "점수를 입력받지 않습니다."
        ),
        "labels": {
            "grid": "격자 크기",
            "count": "서로 다른 카드 수",
            "set": "비공개 세트 번호(1~999)",
            "generate": "빙고 카드 만들기",
            "print": "카드 인쇄",
            "result": "재현 가능한 빙고 카드 {count}장 준비 완료",
            "deterministic": (
                "같은 카드를 다시 만들려면 번호를 유지하고, 다른 고정 세트는 번호를 바꾸세요."
            ),
            "free": "자유",
            "card": "빙고 카드",
            "set_word": "세트",
            "invalid": "지원되는 격자, 카드 수, 세트 번호를 선택하세요.",
        },
        "badges": (
            "같은 설정이면 같은 카드",
            "아동 정보·브라우저 저장 없음",
            "점수·순위·진단 없음",
        ),
        "boundary": (
            "이 생성기가 하는 일과 하지 않는 일",
            (
                "37개 기본 주음부호를 인쇄용 빙고 카드에 배치합니다. 음성을 듣거나 발음을 "
                "평가하고, 답변을 기록하거나 채점·진단하지 않으며 학습·기억력 효과를 약속하지 않습니다."
            ),
        ),
        "how": (
            "고정 카드가 만들어지는 방식",
            (
                "4×4 카드는 서로 다른 16개 부호, 5×5 카드는 24개 부호와 중앙 자유 칸으로 구성됩니다.",
                "격자, 카드 번호, 세트 번호를 쓰는 정수 알고리즘으로 배치하며 실시간 무작위 섞기를 쓰지 않습니다.",
                "각 카드는 따로 생성되고 같은 세 설정은 전체 묶음을 언제나 똑같이 재현합니다.",
            ),
        ),
        "play": (
            "어른과 함께 쓰는 간단한 방법",
            (
                "참여자나 소그룹마다 다른 카드를 인쇄합니다.",
                "어른이 주음부호 하나를 골라 읽습니다. 발음 확인은 대만 교육부 등 공식 자료를 이용하세요.",
                "참여자는 일치하는 부호를 재사용 가능한 표식으로 덮습니다.",
                "시작 전 가로·세로·대각선 중 종료 기준을 정하고 성적표로 사용하지 않습니다.",
            ),
        ),
        "webmcp_description": (
            "격자 크기, 카드 수, 세트 번호로 재현 가능한 주음부호 빙고 내용을 반환합니다. "
            "읽기 전용이며 아동 정보·답변을 받거나 채점·평가·진단·효과 보장을 하지 않습니다."
        ),
        "faq_title": "주음부호 빙고 질문",
        "faq": (
            (
                "같은 세트 번호면 같은 카드가 나오나요?",
                "격자와 카드 수도 같다면 그렇습니다. 실시간 무작위가 아니라 고정 알고리즘을 사용합니다.",
            ),
            (
                "아동 정보를 수집하거나 저장하나요?",
                "아니요. 현재 페이지에서 세 설정만 사용하며 업로드하거나 저장하지 않습니다.",
            ),
            (
                "주음 실력이나 발음을 측정하나요?",
                "아니요. 인쇄 활동일 뿐이며 듣기, 채점, 등급, 순위, 평가, 진단을 하지 않습니다.",
            ),
        ),
        "index": (
            "인쇄용 주음부호 빙고 카드",
            (
                "가입, 아동 정보, 채점, 무작위 섞기 없이 재현 가능한 4×4·5×5 주음부호 세트를 만드세요."
            ),
        ),
        "inline_link": "무료 주음부호 빙고 카드 만들기",
        "footer": "비공개 세트 번호만 · 아동 정보 없음 · 채점 없음 · 어른 진행 오프라인 활동",
    },
    "zh-Hant": {
        "title": "注音賓果卡產生器｜免費列印 4×4、5×5 題卡",
        "description": (
            "免費產生 1–6 張 4×4 或 5×5 注音賓果卡；相同組別編號每次都能重現同一套題卡，"
            "免登入、不蒐集兒童資料、不計分，也不使用即時隨機洗牌。"
        ),
        "eyebrow": "免費列印 · 免登入 · 不計分",
        "heading": "可重現的注音賓果遊戲卡",
        "lead": (
            "選擇格數、卡片張數與私人組別編號；相同設定永遠產生同一套卡片，適合由大人帶領，"
            "在教室或家中進行離線聽音、找符號活動。"
        ),
        "planner": "建立你的注音賓果組",
        "planner_intro": (
            "只使用下方三項設定；不會要求孩子的姓名、年齡、學校、聲音、筆跡、作答或分數。"
        ),
        "labels": {
            "grid": "格數",
            "count": "不同卡片張數",
            "set": "私人組別編號（1–999）",
            "generate": "產生注音賓果卡",
            "print": "列印這組卡片",
            "result": "已產生 {count} 張可重現的注音賓果卡",
            "deterministic": "保留相同組別編號即可重做這套卡片；更換編號會建立另一套固定卡片。",
            "free": "自由格",
            "card": "注音賓果卡",
            "set_word": "組別",
            "invalid": "請選擇支援的格數、卡片張數與組別編號。",
        },
        "badges": (
            "設定相同，卡片完全相同",
            "不蒐集兒童資料、不寫入瀏覽器",
            "不計分、不排名、不診斷",
        ),
        "boundary": (
            "這個產生器會做什麼、不會做什麼",
            (
                "它只把 37 個基本注音符號排列成可列印賓果卡；不會收音、判斷發音、記錄作答、"
                "替孩子計分或診斷，也不宣稱可保證學習成果或提升記憶力。"
            ),
        ),
        "how": (
            "固定卡片如何產生",
            (
                "4×4 每張使用 16 個不同符號；5×5 使用 24 個不同符號與中央自由格。",
                "格數、卡片編號與組別編號會進入公開的整數演算法，不使用即時隨機洗牌。",
                "同一批每張卡片分開排列；三項設定相同時，整批卡片每次都能完整重現。",
            ),
        ),
        "play": (
            "大人帶領的簡單玩法",
            (
                "每位孩子或每個小組各印一張不同卡片。",
                "由大人每次選一個注音符號念出；需要確認讀音時請查台灣教育部官方資料。",
                "孩子用可重複使用的棋子蓋住相同符號。",
                "開始前先約定橫線、直線或斜線何者完成一局；不要把活動換算成成績。",
            ),
        ),
        "webmcp_description": (
            "依格數、卡片張數與組別編號回傳可重現的注音賓果卡內容。唯讀工具：不接收兒童資料、"
            "不記錄作答、不計分、不評量、不診斷，也不承諾學習成果。"
        ),
        "faq_title": "注音賓果卡常見問題",
        "faq": (
            (
                "相同組別編號會產生相同卡片嗎？",
                "會，只要格數與卡片張數也相同。工具使用固定整數演算法，不是每次重新亂數洗牌。",
            ),
            (
                "會蒐集或儲存孩子的資料嗎？",
                "不會。三項設定只在目前頁面中使用，不會上傳或儲存。",
            ),
            (
                "注音賓果能評量孩子的程度或發音嗎？",
                "不能。這只是可列印活動，不會收音、計分、分級、排名、評量或診斷。",
            ),
        ),
        "index": (
            "可列印注音賓果卡",
            "建立可重現的 4×4 或 5×5 注音賓果組；免登入、不蒐集兒童資料、不計分、不隨機洗牌。",
        ),
        "inline_link": "免費產生可列印注音賓果卡",
        "footer": "只使用私人組別編號 · 不蒐集兒童資料 · 不計分 · 大人帶領的離線活動",
    },
    "zh-Hans": {
        "title": "注音符号宾果卡生成器｜免费打印 4×4、5×5 卡片",
        "description": (
            "免费生成 1–6 张 4×4 或 5×5 注音符号宾果卡；相同组别编号每次都能重现同一套卡片，"
            "无需登录、不收集儿童数据、不计分，也不使用即时随机洗牌。"
        ),
        "eyebrow": "免费打印 · 无需登录 · 不计分",
        "heading": "可重现的注音符号宾果卡",
        "lead": (
            "选择格数、卡片数量和私人组别编号；相同设置始终生成同一套卡片，适合由成人带领，"
            "在家或课堂进行离线听音、找符号活动。"
        ),
        "planner": "创建注音符号宾果组",
        "planner_intro": (
            "只使用下方三项设置；不会要求儿童的姓名、年龄、学校、声音、笔迹、作答或分数。"
        ),
        "labels": {
            "grid": "格数",
            "count": "不同卡片数量",
            "set": "私人组别编号（1–999）",
            "generate": "生成宾果卡",
            "print": "打印这组卡片",
            "result": "已生成 {count} 张可重现的宾果卡",
            "deterministic": "保留组别编号可重建这套卡片；更换编号会创建另一套固定卡片。",
            "free": "自由格",
            "card": "宾果卡",
            "set_word": "组别",
            "invalid": "请选择支持的格数、卡片数量和组别编号。",
        },
        "badges": (
            "设置相同，卡片相同",
            "不收集儿童数据、不写入浏览器",
            "不计分、不排名、不诊断",
        ),
        "boundary": (
            "生成器会做什么、不会做什么",
            (
                "它只把 37 个基本注音符号排成可打印宾果卡；不会收音、判断发音、记录作答、"
                "给儿童计分或诊断，也不承诺学习成果或记忆力提升。"
            ),
        ),
        "how": (
            "固定卡片如何生成",
            (
                "4×4 每张使用 16 个不同符号；5×5 使用 24 个不同符号和中央自由格。",
                "格数、卡片编号和组别编号进入公开的整数算法，不使用即时随机洗牌。",
                "每张卡片分别排列；三项设置相同时，整批卡片每次都能完整重现。",
            ),
        ),
        "play": (
            "成人带领的简单玩法",
            (
                "每位参与者或每个小组打印一张不同卡片。",
                "由成人每次选择并读出一个注音符号；需要确认读音时请查台湾教育部官方资料。",
                "参与者用可重复使用的棋子盖住对应符号。",
                "开始前约定横线、竖线或斜线完成一局；不要把活动换算成成绩。",
            ),
        ),
        "webmcp_description": (
            "按格数、卡片数量和组别编号返回可重现的注音符号宾果卡内容。只读工具：不接收儿童数据、"
            "不记录作答、不计分、不评估、不诊断，也不承诺学习成果。"
        ),
        "faq_title": "注音符号宾果卡常见问题",
        "faq": (
            (
                "相同组别编号会生成相同卡片吗？",
                "会，只要格数和卡片数量也相同。工具使用固定整数算法，不会每次随机洗牌。",
            ),
            (
                "会收集或保存儿童数据吗？",
                "不会。三项设置只在当前页面使用，不会上载或保存。",
            ),
            (
                "宾果能评估注音程度或发音吗？",
                "不能。这只是可打印活动，不会收音、计分、分级、排名、评估或诊断。",
            ),
        ),
        "index": (
            "可打印注音符号宾果卡",
            "创建可重现的 4×4 或 5×5 注音符号宾果组；无需登录、不收集儿童数据、不计分。",
        ),
        "inline_link": "免费生成可打印注音符号宾果卡",
        "footer": "只使用私人组别编号 · 不收集儿童数据 · 不计分 · 成人带领的离线活动",
    },
}

# Japanese, Korean, and Chinese speakers have established localized terms;
# the remaining heritage-learning markets usually search with both labels.
for _locale in ("es-ES", "pt-BR", "de-DE", "fr-FR"):
    COPY[_locale]["heading"] = COPY[_locale]["heading"].replace(
        "Bopomofo", "Bopomofo (Zhuyin)"
    )


def _lcg_next(state: int) -> int:
    return (state * LCG_MULTIPLIER + LCG_INCREMENT) % LCG_MODULUS


def _lcg_draw(state: int) -> int:
    return (state // 65536) % 32768


def _card_symbols(grid_size: int, set_number: int, card_number: int) -> list[str]:
    values = list(SYMBOL_VALUES)
    state = grid_size * 1_000_000 + set_number * 100 + card_number
    for index in range(len(values) - 1, 0, -1):
        state = _lcg_next(state)
        selected = _lcg_draw(state) % (index + 1)
        values[index], values[selected] = values[selected], values[index]
    needed = grid_size * grid_size - (1 if grid_size == 5 else 0)
    return values[:needed]


def build_bingo(
    grid_size: int, card_count: int, set_number: int
) -> dict[str, object]:
    for name, value in (
        ("grid_size", grid_size),
        ("card_count", card_count),
        ("set_number", set_number),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer")
    if grid_size not in GRID_SIZES:
        raise ValueError("unsupported grid size")
    if not CARD_COUNT_MIN <= card_count <= CARD_COUNT_MAX:
        raise ValueError("unsupported card count")
    if not SET_NUMBER_MIN <= set_number <= SET_NUMBER_MAX:
        raise ValueError("unsupported set number")
    cards = []
    for card_number in range(1, card_count + 1):
        symbols = _card_symbols(grid_size, set_number, card_number)
        cells: list[dict[str, object]] = [
            {"kind": "symbol", "symbol": symbol} for symbol in symbols
        ]
        if grid_size == 5:
            cells.insert(12, {"kind": "free"})
        cards.append({"card_number": card_number, "cells": cells})
    return {
        "selected_inputs": {
            "grid_size": grid_size,
            "card_count": card_count,
            "set_number": set_number,
        },
        "cards": cards,
    }


STYLE = r"""
:root{--ink:#1f2840;--muted:#667087;--line:#dce2ef;--paper:#fff;--bg:#f3f6fc;--indigo:#3949a3;--violet:#7865d5;--gold:#f3b23f;--soft:#edf0ff;--shadow:0 22px 60px rgba(48,57,110,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 58%,#e8edf8 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--indigo)}.wrap{width:min(1140px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--indigo);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--indigo);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #c9d1e3;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--indigo),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}.button.ghost{background:#fff;color:var(--indigo);border:1px solid var(--line);box-shadow:none}.note{background:#fff7dc;border:1px solid #ead7a0;border-radius:16px;padding:13px 15px;white-space:nowrap;overflow-x:auto}
.bingo-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:20px}.bingo-card{background:#fff;border:1px solid var(--line);border-radius:22px;padding:17px;box-shadow:0 14px 34px rgba(48,57,110,.09);break-inside:avoid;page-break-inside:avoid}.bingo-head{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:2px solid var(--ink);padding-bottom:9px;margin-bottom:11px}.bingo-head h3{margin:0;font-size:19px;white-space:nowrap}.bingo-meta{font-size:12px;color:var(--muted);font-weight:800;white-space:nowrap}.board{display:grid;gap:6px}.board.size-4{grid-template-columns:repeat(4,minmax(0,1fr))}.board.size-5{grid-template-columns:repeat(5,minmax(0,1fr))}.cell{aspect-ratio:1;display:flex;align-items:center;justify-content:center;border:2px solid #d8deec;border-radius:14px;background:linear-gradient(180deg,#fff,#f9faff);font-size:clamp(28px,5vw,48px);font-weight:900;line-height:1}.cell.free{background:linear-gradient(135deg,var(--gold),#ef7c5a);color:#fff;font-size:clamp(12px,2vw,18px);white-space:nowrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ol,.card ul{padding-left:22px}.card li{margin:8px 0}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}.footer{background:var(--indigo);color:#f5f6ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:850px){.bingo-list,.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}@media(max-width:680px){.controls{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1140px)}.cell{border-radius:10px}.bingo-head{display:block}.bingo-meta{margin-top:3px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.planner form,.planner>.intro,.note,.button,.app-card,.footer,.grid,.faq{display:none!important}body{background:#fff}.wrap{width:100%}.planner{box-shadow:none;border:0;padding:0;margin:0}.bingo-list{display:block}.bingo-card{border:0;border-radius:0;box-shadow:none;padding:0;margin:0;page-break-after:always}.bingo-card:last-child{page-break-after:auto}.cell{border-color:#111;border-radius:2mm;background:#fff!important;color:#000!important}.cell.free{background:#eee!important}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("bopomofo-bingo-config").textContent);
  const form = document.getElementById("bopomofo-bingo-planner");
  const fields = {
    grid_size: document.getElementById("grid-size"),
    card_count: document.getElementById("card-count"),
    set_number: document.getElementById("set-number")
  };
  const summary = document.getElementById("result-summary");
  const list = document.getElementById("bingo-list");
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

  function integerValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const schema = config.inputSchema.properties[name];
    if (typeof value !== "number" || !Number.isInteger(value)) {
      throw new TypeError(`${name} must be an integer.`);
    }
    if (schema.enum && !schema.enum.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    if (schema.minimum !== undefined &&
        (value < schema.minimum || value > schema.maximum)) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function cardSymbols(gridSize, setNumber, cardNumber) {
    const values = [...config.symbols];
    let state = gridSize * 1000000 + setNumber * 100 + cardNumber;
    for (let index = values.length - 1; index > 0; index -= 1) {
      state = nextState(state);
      const selected = drawValue(state) % (index + 1);
      const temporary = values[index];
      values[index] = values[selected];
      values[selected] = temporary;
    }
    const needed = gridSize * gridSize - (gridSize === 5 ? 1 : 0);
    return values.slice(0, needed);
  }

  function buildBingo(input) {
    const gridSize = integerValue(input, "grid_size");
    const cardCount = integerValue(input, "card_count");
    const setNumber = integerValue(input, "set_number");
    const cards = [];
    for (let cardNumber = 1; cardNumber <= cardCount; cardNumber += 1) {
      const cells = cardSymbols(gridSize, setNumber, cardNumber).map(
        (symbol) => ({kind: "symbol", symbol}));
      if (gridSize === 5) cells.splice(12, 0, {kind: "free"});
      cards.push({card_number: cardNumber, cells});
    }
    return {
      selected_inputs: {
        grid_size: gridSize,
        card_count: cardCount,
        set_number: setNumber
      },
      cards
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
    return buildBingo(input);
  }

  function humanIntegerValue(field, name) {
    const raw = String(field.value).trim();
    const value = raw === "" ? Number.NaN : Number(raw);
    return integerValue({[name]: value}, name);
  }

  function makeCard(card, selectedInputs) {
    const article = document.createElement("article");
    article.className = "bingo-card";
    const header = document.createElement("div");
    header.className = "bingo-head";
    const title = document.createElement("h3");
    title.textContent = `${config.labels.card} ${card.card_number}`;
    const meta = document.createElement("div");
    meta.className = "bingo-meta";
    meta.textContent = `${config.labels.setWord} ${selectedInputs.set_number} · ${selectedInputs.grid_size}×${selectedInputs.grid_size}`;
    header.append(title, meta);
    const board = document.createElement("div");
    board.className = `board size-${selectedInputs.grid_size}`;
    for (const cell of card.cells) {
      const element = document.createElement("div");
      element.className = cell.kind === "free" ? "cell free" : "cell";
      element.textContent = cell.kind === "free" ? config.labels.free : cell.symbol;
      board.appendChild(element);
    }
    article.append(header, board);
    return article;
  }

  function render() {
    let result;
    try {
      result = buildBingo({
        grid_size: humanIntegerValue(fields.grid_size, "grid_size"),
        card_count: humanIntegerValue(fields.card_count, "card_count"),
        set_number: humanIntegerValue(fields.set_number, "set_number")
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        summary.textContent = config.labels.invalid;
        list.replaceChildren();
        return;
      }
      throw error;
    }
    summary.textContent = config.labels.result.replace(
      "{count}", String(result.cards.length));
    const fragment = document.createDocumentFragment();
    for (const card of result.cards) {
      fragment.appendChild(makeCard(card, result.selected_inputs));
    }
    list.replaceChildren(fragment);
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "create_private_bopomofo_bingo_cards",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const cards = validateInput(input);
        const result = {
          result_type: "private_bopomofo_bingo_cards",
          deterministic: true,
          is_not_assessment: true,
          no_score_grade_rank_or_diagnosis: true,
          no_child_data_received: true,
          cards,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) result.optional_lumibopomofo = config.optionalApp;
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
  printButton.addEventListener("click", () => window.print());
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
            "grid_size": {
                "type": "integer",
                "enum": list(GRID_SIZES),
                "description": labels["grid"],
            },
            "card_count": {
                "type": "integer",
                "minimum": CARD_COUNT_MIN,
                "maximum": CARD_COUNT_MAX,
                "description": labels["count"],
            },
            "set_number": {
                "type": "integer",
                "minimum": SET_NUMBER_MIN,
                "maximum": SET_NUMBER_MAX,
                "description": labels["set"],
            },
        },
        "required": ["grid_size", "card_count", "set_number"],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    base = BASE_COPY[locale]
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
        f'<span class="badge">{html.escape(item)}</span>'
        for item in t["badges"]
    )
    how_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["how"][1]
    )
    play_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["play"][1]
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
        for label, source in zip(base["source_labels"][:3], sources, strict=True)
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_bopomofo_bingo_{locale.lower()}")
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
    labels = t["labels"]
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "symbols": list(SYMBOL_VALUES),
        "labels": {
            "result": labels["result"],
            "free": labels["free"],
            "card": labels["card"],
            "setWord": labels["set_word"],
            "invalid": labels["invalid"],
        },
        "toolDescription": t["webmcp_description"],
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(
                base["source_labels"][:3], sources, strict=True
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
        "name": t["play"][0],
        "step": [
            {"@type": "HowToStep", "position": index + 1, "text": step}
            for index, step in enumerate(t["play"][1])
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
<form id="bopomofo-bingo-planner"><div class="controls">
<div class="field"><label for="grid-size">{html.escape(labels["grid"])}</label><select id="grid-size"><option value="4">4×4</option><option value="5" selected>5×5</option></select></div>
<div class="field"><label for="card-count">{html.escape(labels["count"])}</label><select id="card-count">{"".join(f'<option value="{count}"{" selected" if count == DEFAULT_CARD_COUNT else ""}>{count}</option>' for count in range(CARD_COUNT_MIN, CARD_COUNT_MAX + 1))}</select></div>
<div class="field"><label for="set-number">{html.escape(labels["set"])}</label><input id="set-number" type="number" min="{SET_NUMBER_MIN}" max="{SET_NUMBER_MAX}" step="1" value="{DEFAULT_SET_NUMBER}" required></div>
</div><p><button class="button" type="submit">{html.escape(labels["generate"])}</button> <button class="button ghost" type="button" id="print-cards">{html.escape(labels["print"])}</button></p>
<p class="intro">{html.escape(labels["deterministic"])}</p></form>
<p id="result-summary" class="note" role="status" aria-live="polite"></p>
<div id="bingo-list" class="bingo-list"></div>
</section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["boundary"][0])}</h2><p>{html.escape(t["boundary"][1])}</p></article><article class="card"><h2>{html.escape(t["how"][0])}</h2><ol>{how_items}</ol></article><article class="card wide"><h2>{html.escape(t["play"][0])}</h2><ol>{play_items}</ol></article><article class="card wide"><h2>{html.escape(base["sources_title"])}</h2><p>{html.escape(base["sources_intro"])}</p><ul>{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(base["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="bopomofo-bingo-config">{config_json}</script>
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


TARGET_ANSWER_SLUG = "bopomofo-tracing-app-for-kids.html"
INBOUND_LINK_CLASS = "bopomofo-bingo-inline-link"
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
            f'data-bopomofo-bingo-link="1" href="{canonical(locale)}" '
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
        print(f"bopomofo bingo cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
