#!/usr/bin/env python3
"""Generate a nine-locale private TOEIC study-allocation planner (Aim990)."""

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

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "private-toeic-study-allocation-planner"
APP_KEY = "aim990"
APP_ID = "6784974530"
CONTENT_DATE = "2026-07-15"

IIBC_FORMAT = "https://www.iibc-global.org/english/toeic/test/lr/about/format.html"
ETS_SAMPLE_PDF = (
    "https://www.ets.org/pdfs/toeic/toeic-listening-reading-sample-test.pdf"
)
ETS_ABOUT = "https://www.ets.org/toeic/about/listening-reading.html"
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
    "vi",
    "th",
    "id",
    "tr",
)
EMPHASIS_CHOICES = ("balanced", "listening", "reading")

COPY = {
    "en": {
        "title": "Private TOEIC Study Allocation Planner | No Score Prediction",
        "description": (
            "Turn days available, study days per week, minutes per day and study emphasis "
            "into a transparent listening/reading/review/timed-practice minute plan — no "
            "account, no score prediction, no ETS affiliation."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no account · no score prediction",
        "heading": "Private TOEIC study allocation planner",
        "lead": (
            "Turn a few bounded numbers into a transparent split of study minutes across "
            "listening, reading, review and timed practice. This is a planning heuristic "
            "built by this site, not a score prediction, diagnosis or ETS recommendation."
        ),
        "badges": (
            "No test answers, recordings or documents",
            "No name, email, account or exact test date",
            "No score, grade or pass/fail prediction",
            "Not affiliated with or endorsed by ETS",
        ),
        "planner": "Build your private study allocation",
        "planner_intro": (
            "Enter only bounded numbers and short choices below. This page never asks "
            "for test answers, recordings, documents or personal details."
        ),
        "days_label": "Days available before your target date (1–30)",
        "days_per_week_label": "Study days you can commit per week (1–7)",
        "minutes_label": "Minutes you can study on each study day (10–120)",
        "emphasis_label": "Which balance do you want?",
        "emphasis_options": {
            "balanced": "Balanced listening & reading",
            "listening": "Emphasize listening",
            "reading": "Emphasize reading",
        },
        "timed_label": "I'm ready to include timed practice sessions",
        "update": "Update private plan",
        "invalid_input": "Enter values within the supported ranges shown above.",
        "result_sessions": "Planned study sessions",
        "result_total": "Total planned minutes",
        "result_listening": "Listening minutes",
        "result_reading": "Reading minutes",
        "result_review": "Review minutes",
        "result_timed": "Timed-practice minutes",
        "result_plan_label": "Next steps",
        "next_steps": (
            "Confirm your own days available, study days per week and minutes per day; "
            "this page never sees your exact test date.",
            "Pick a balance (balanced, listening or reading) and whether you're ready "
            "for timed practice.",
            "Use the minute split only as an editable starting point, then adjust it to "
            "match your own weak areas.",
            "Review the official IIBC format and ETS sample test before planning "
            "further, since the real test is fixed-format and English-only.",
            "Repeat and adjust the split every few days instead of following it "
            "rigidly.",
        ),
        "boundary_title": "What this planner does not do",
        "boundary_text": (
            "This planner does not predict a TOEIC score, grade your readiness, "
            "diagnose ability, guarantee improvement, or imply any ETS affiliation or "
            "endorsement. It only turns your own bounded numbers into an editable "
            "minute split using a fixed, documented heuristic."
        ),
        "sources_title": "Official TOEIC L&R format facts and sources",
        "sources_intro": (
            "These facts come from IIBC and ETS official pages, not from this site. Use "
            "them to sanity-check any study plan, including this one."
        ),
        "official_facts": (
            "The TOEIC Listening & Reading test has 200 questions completed in two "
            "hours.",
            "Listening: about 45 minutes for 100 questions.",
            "Reading: 75 minutes for 100 questions.",
            "The test itself is presented only in English, and the format is the same "
            "at every administration.",
        ),
        "source_labels": (
            "IIBC official TOEIC L&R test format",
            "ETS official TOEIC L&R sample test (PDF)",
            "ETS official TOEIC L&R program overview",
        ),
        "heuristic_title": "How this planner's allocation heuristic works",
        "heuristic_intro": (
            "This split is a simple, editable heuristic created by this site. It is not "
            "an ETS recommendation, and it does not predict a score."
        ),
        "heuristic_list": (
            "Balanced: 35% listening, 35% reading, 20% review, 10% timed practice.",
            "Listening emphasis: 50% listening, 25% reading, 15% review, 10% timed "
            "practice.",
            "Reading emphasis: 25% listening, 50% reading, 15% review, 10% timed "
            "practice.",
            "If you are not ready for timed practice, its share moves into review "
            "instead.",
            "Minutes are shared out with a largest-remainder method so the four parts "
            "always add up exactly to your total planned minutes.",
        ),
        "trademark_notice": (
            "TOEIC is a trademark of ETS. Aim990 is an independent study aid and is not "
            "affiliated with or endorsed by ETS. No app or plan can guarantee a TOEIC "
            "score."
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Build a transparent TOEIC study-minute allocation from bounded, "
            "non-sensitive counts and choices. Never receive test answers, recordings, "
            "documents, names, contacts, accounts or an exact test date; never produce "
            "a score prediction, readiness grade, pass/fail result or ETS-affiliation "
            "claim."
        ),
        "app_title": "Want an optional guided TOEIC coach?",
        "app_text": (
            "Aim990 is optional. Its current App Store listing describes a free "
            "download with in-app purchases, a 30-day TOEIC Listening & Reading coach, "
            "an 8-minute level diagnostic, daily listening/reading/grammar/vocabulary "
            "and mock-test tasks, and progress and weak-area tracking; Apple's privacy "
            "label states no data is collected. Verify the current listing before "
            "buying, since features and pricing can change. This planner works fully "
            "without the app."
        ),
        "app_cta": "View Aim990 on the App Store",
        "faq_title": "TOEIC study allocation questions",
        "faq": (
            (
                "Does this page receive my test answers, recordings or documents?",
                "No. It only accepts bounded counts, a balance choice and a readiness "
                "toggle.",
            ),
            (
                "Does this predict my TOEIC score?",
                "No. It only splits your own minutes into a plan; it never estimates, "
                "grades or predicts any score or pass/fail result.",
            ),
            (
                "Is Aim990 affiliated with ETS or the TOEIC program?",
                "No. TOEIC is a trademark of ETS. Aim990 is an independent study aid "
                "and is not affiliated with or endorsed by ETS.",
            ),
            (
                "Where does the allocation percentage come from?",
                "It is this site's own editable planning heuristic, not an official "
                "ETS or IIBC recommendation.",
            ),
            (
                "What if I'm not ready for timed practice?",
                "Turn the readiness toggle off and its planned minutes move into "
                "review instead, so your total stays the same.",
            ),
        ),
        "footer": (
            "Private bounded numbers only · no documents · no score prediction · no "
            "ETS affiliation"
        ),
        "index_title": "Private TOEIC Study Allocation Planner",
        "index_description": (
            "Turn bounded study numbers into a transparent listening/reading/review/"
            "timed-practice minute split, with no account and no score prediction."
        ),
        "inline_link_label": (
            "Free TOEIC study allocation planner (no score prediction)"
        ),
    },
    "es-ES": {
        "title": (
            "Planificador privado de reparto de estudio TOEIC | Sin predicción de "
            "puntuación"
        ),
        "description": (
            "A partir de los días disponibles, los días de estudio por semana, los "
            "minutos por día y el énfasis deseado, calcula de forma transparente un "
            "reparto del tiempo de estudio entre escucha, lectura, repaso y práctica "
            "cronometrada, sin cuenta, sin predicción de puntuación y sin relación con "
            "ETS."
        ),
        "tools": "Herramientas gratis",
        "switch": "English",
        "eyebrow": "Gratis · sin cuenta · sin predicción de puntuación",
        "heading": "Planificador privado de reparto de estudio TOEIC",
        "lead": (
            "Con solo unos pocos números acotados, obtén un reparto transparente del "
            "tiempo de estudio entre escucha, lectura, repaso y práctica cronometrada. "
            "Esto es una referencia de planificación creada por este sitio, no una "
            "predicción de puntuación, un diagnóstico ni una recomendación de ETS."
        ),
        "badges": (
            "Sin respuestas del examen, grabaciones ni documentos",
            "Sin nombre, correo, cuenta ni fecha exacta del examen",
            "Sin predicción de puntuación, nota ni aprobado/suspenso",
            "Sin afiliación ni respaldo de ETS",
        ),
        "planner": "Crea tu reparto de estudio privado",
        "planner_intro": (
            "Introduce solo números dentro de los límites y opciones breves. Esta "
            "página nunca solicita respuestas del examen, grabaciones, documentos ni "
            "datos personales."
        ),
        "days_label": "Días disponibles hasta tu fecha objetivo (1 a 30)",
        "days_per_week_label": "Días de estudio que puedes dedicar por semana (1 a 7)",
        "minutes_label": (
            "Minutos que puedes dedicar cada día de estudio (10 a 120)"
        ),
        "emphasis_label": "¿Qué equilibrio prefieres?",
        "emphasis_options": {
            "balanced": "Escucha y lectura equilibradas",
            "listening": "Énfasis en escucha",
            "reading": "Énfasis en lectura",
        },
        "timed_label": "Estoy listo/a para práctica cronometrada",
        "update": "Actualizar plan privado",
        "invalid_input": (
            "Introduce valores dentro de los rangos admitidos indicados arriba."
        ),
        "result_sessions": "Sesiones de estudio planificadas",
        "result_total": "Minutos totales planificados",
        "result_listening": "Minutos de escucha",
        "result_reading": "Minutos de lectura",
        "result_review": "Minutos de repaso",
        "result_timed": "Minutos de práctica cronometrada",
        "result_plan_label": "Próximos pasos",
        "next_steps": (
            "Confirma tus propios días disponibles, días de estudio por semana y "
            "minutos por día; esta página nunca recibe tu fecha exacta de examen.",
            "Elige un equilibrio (equilibrado, escucha o lectura) e indica si estás "
            "listo/a para práctica cronometrada.",
            "Usa este reparto solo como punto de partida editable y ajústalo según "
            "tus propios puntos débiles.",
            "El examen TOEIC real tiene un formato fijo y es solo en inglés; consulta "
            "el formato oficial de IIBC y el examen de muestra oficial de ETS antes de "
            "seguir planificando.",
            "Revisa y ajusta el reparto cada pocos días en lugar de seguirlo de forma "
            "rígida.",
        ),
        "boundary_title": "Lo que este planificador no hace",
        "boundary_text": (
            "Este planificador no predice tu puntuación TOEIC, no evalúa ni "
            "diagnostica tu nivel, no garantiza ninguna mejora y no sugiere afiliación "
            "ni respaldo de ETS. Solo convierte tus propios números acotados en un "
            "reparto editable mediante un cálculo fijo y transparente."
        ),
        "sources_title": "Datos oficiales del formato TOEIC L&R y fuentes",
        "sources_intro": (
            "Estos datos provienen de las páginas oficiales de IIBC y ETS, no de este "
            "sitio. Úsalos para comprobar cualquier plan de estudio, incluido este."
        ),
        "official_facts": (
            "El examen TOEIC Listening & Reading tiene 200 preguntas que se completan "
            "en dos horas.",
            "Escucha: unos 45 minutos para 100 preguntas.",
            "Lectura: 75 minutos para 100 preguntas.",
            "El examen en sí se presenta solo en inglés, y el formato es el mismo en "
            "cada convocatoria.",
        ),
        "source_labels": (
            "Formato oficial del examen TOEIC L&R (IIBC)",
            "Examen de muestra oficial TOEIC L&R de ETS (PDF)",
            "Resumen oficial del programa TOEIC L&R de ETS",
        ),
        "heuristic_title": "Cómo funciona la lógica de reparto de este planificador",
        "heuristic_intro": (
            "Este reparto es una referencia simple y editable creada por este sitio. "
            "No es una recomendación de ETS y no predice ninguna puntuación."
        ),
        "heuristic_list": (
            "Equilibrado: 35 % escucha, 35 % lectura, 20 % repaso, 10 % práctica "
            "cronometrada.",
            "Énfasis en escucha: 50 % escucha, 25 % lectura, 15 % repaso, 10 % "
            "práctica cronometrada.",
            "Énfasis en lectura: 25 % escucha, 50 % lectura, 15 % repaso, 10 % "
            "práctica cronometrada.",
            "Si no estás listo/a para la práctica cronometrada, su parte se traslada "
            "al repaso.",
            "Los minutos se reparten con el método del resto mayor, para que las "
            "cuatro partes sumen siempre exactamente tus minutos totales "
            "planificados.",
        ),
        "trademark_notice": (
            "TOEIC es una marca de ETS. Aim990 es una ayuda de estudio independiente y "
            "no está afiliada a ETS ni respaldada por ETS. Ninguna app ni plan puede "
            "garantizar una puntuación TOEIC."
        ),
        "webmcp_source": (
            "Vista previa de la API imperativa Chrome WebMCP (sujeta a cambios)"
        ),
        "webmcp_description": (
            "Crea un reparto transparente del tiempo de estudio TOEIC a partir de "
            "números y opciones acotados y no sensibles. Nunca recibe respuestas del "
            "examen, grabaciones, documentos, nombres, contactos, cuentas ni fecha "
            "exacta del examen; nunca genera una predicción de puntuación, una nota de "
            "nivel, un resultado de aprobado/suspenso ni una afirmación de afiliación "
            "con ETS."
        ),
        "app_title": "¿Quieres un coach TOEIC guiado opcional?",
        "app_text": (
            "Aim990 es opcional. Su ficha actual de App Store describe una descarga "
            "gratuita con compras integradas, un coach TOEIC Listening & Reading de 30 "
            "días, un diagnóstico de nivel de 8 minutos, tareas diarias de escucha/"
            "lectura/gramática/vocabulario y simulacros de examen, además de "
            "seguimiento del progreso y puntos débiles; la etiqueta de privacidad de "
            "Apple indica que no se recopilan datos. Verifica la ficha actual antes de "
            "comprar, ya que las funciones y el precio pueden cambiar. Este "
            "planificador funciona por completo sin la app."
        ),
        "app_cta": "Ver Aim990 en la App Store",
        "faq_title": "Preguntas sobre el reparto de estudio TOEIC",
        "faq": (
            (
                "¿Esta página recibe mis respuestas del examen, grabaciones o "
                "documentos?",
                "No. Solo acepta números acotados, una elección de equilibrio y un "
                "interruptor de disposición.",
            ),
            (
                "¿Esto predice mi puntuación TOEIC?",
                "No. Solo reparte tus propios minutos; nunca estima, evalúa ni "
                "predice ninguna puntuación o resultado de aprobado/suspenso.",
            ),
            (
                "¿Aim990 está afiliada a ETS o al programa TOEIC?",
                "No. TOEIC es una marca de ETS. Aim990 es una ayuda de estudio "
                "independiente y no está afiliada a ETS ni respaldada por ETS.",
            ),
            (
                "¿De dónde sale el porcentaje de reparto?",
                "Es la referencia de planificación propia y editable de este sitio, "
                "no una recomendación oficial de ETS ni de IIBC.",
            ),
            (
                "¿Qué pasa si no estoy listo/a para la práctica cronometrada?",
                "Desactiva el interruptor de disposición y esos minutos se trasladan "
                "al repaso; el total permanece igual.",
            ),
        ),
        "footer": (
            "Solo números privados acotados · sin documentos · sin predicción de "
            "puntuación · sin afiliación a ETS"
        ),
        "index_title": "Planificador privado de reparto de estudio TOEIC",
        "index_description": (
            "Convierte números de estudio acotados en un reparto transparente entre "
            "escucha, lectura, repaso y práctica cronometrada, sin cuenta y sin "
            "predicción de puntuación."
        ),
        "inline_link_label": (
            "Planificador gratis de reparto de estudio TOEIC (sin predicción de "
            "puntuación)"
        ),
    },
    "pt-BR": {
        "title": (
            "Planejador privado de distribuição de estudo TOEIC | Sem previsão de "
            "nota"
        ),
        "description": (
            "A partir dos dias disponíveis, dias de estudo por semana, minutos por "
            "dia e ênfase desejada, calcule de forma transparente uma distribuição do "
            "tempo de estudo entre listening, reading, revisão e prática cronometrada "
            "— sem conta, sem previsão de nota, sem vínculo com a ETS."
        ),
        "tools": "Ferramentas grátis",
        "switch": "English",
        "eyebrow": "Grátis · sem conta · sem previsão de nota",
        "heading": "Planejador privado de distribuição de estudo TOEIC",
        "lead": (
            "Com apenas alguns números limitados, obtenha uma distribuição "
            "transparente do tempo de estudo entre listening, reading, revisão e "
            "prática cronometrada. Isto é uma referência de planejamento criada por "
            "este site, não uma previsão de nota, um diagnóstico nem uma recomendação "
            "da ETS."
        ),
        "badges": (
            "Sem respostas de prova, gravações ou documentos",
            "Sem nome, e-mail, conta ou data exata da prova",
            "Sem previsão de nota, conceito ou aprovação/reprovação",
            "Sem vínculo ou endosso da ETS",
        ),
        "planner": "Criar sua distribuição de estudo privada",
        "planner_intro": (
            "Informe apenas números dentro dos limites e opções curtas. Esta página "
            "nunca solicita respostas da prova, gravações, documentos nem dados "
            "pessoais."
        ),
        "days_label": "Dias disponíveis até a data-alvo (1 a 30)",
        "days_per_week_label": (
            "Dias de estudo que você pode reservar por semana (1 a 7)"
        ),
        "minutes_label": (
            "Minutos que você pode dedicar em cada dia de estudo (10 a 120)"
        ),
        "emphasis_label": "Qual equilíbrio você prefere?",
        "emphasis_options": {
            "balanced": "Listening e reading equilibrados",
            "listening": "Ênfase em listening",
            "reading": "Ênfase em reading",
        },
        "timed_label": "Estou pronto(a) para incluir prática cronometrada",
        "update": "Atualizar plano privado",
        "invalid_input": (
            "Informe valores dentro dos intervalos suportados mostrados acima."
        ),
        "result_sessions": "Sessões de estudo planejadas",
        "result_total": "Total de minutos planejados",
        "result_listening": "Minutos de listening",
        "result_reading": "Minutos de reading",
        "result_review": "Minutos de revisão",
        "result_timed": "Minutos de prática cronometrada",
        "result_plan_label": "Próximos passos",
        "next_steps": (
            "Confirme seus próprios dias disponíveis, dias de estudo por semana e "
            "minutos por dia; esta página nunca recebe sua data exata de prova.",
            "Escolha um equilíbrio (equilibrado, listening ou reading) e se você está "
            "pronto(a) para prática cronometrada.",
            "Use esta distribuição apenas como ponto de partida editável e ajuste "
            "conforme seus próprios pontos fracos.",
            "A prova real do TOEIC tem formato fixo e é somente em inglês; consulte o "
            "formato oficial da IIBC e a prova de exemplo oficial da ETS antes de "
            "planejar mais.",
            "Revise e ajuste a distribuição a cada poucos dias, em vez de segui-la "
            "rigidamente.",
        ),
        "boundary_title": "O que este planejador não faz",
        "boundary_text": (
            "Este planejador não prevê sua nota do TOEIC, não avalia nem diagnostica "
            "sua habilidade, não garante nenhuma melhora e não sugere vínculo ou "
            "endosso da ETS. Ele apenas transforma seus próprios números limitados em "
            "uma distribuição editável, usando um cálculo fixo e transparente."
        ),
        "sources_title": "Fatos oficiais sobre o formato do TOEIC L&R e fontes",
        "sources_intro": (
            "Esses fatos vêm das páginas oficiais da IIBC e da ETS, não deste site. "
            "Use-os para conferir qualquer plano de estudo, incluindo este."
        ),
        "official_facts": (
            "A prova TOEIC Listening & Reading tem 200 questões, concluídas em duas "
            "horas.",
            "Listening: cerca de 45 minutos para 100 questões.",
            "Reading: 75 minutos para 100 questões.",
            "A prova em si é aplicada somente em inglês, e o formato é o mesmo em "
            "todas as aplicações.",
        ),
        "source_labels": (
            "Formato oficial da prova TOEIC L&R (IIBC)",
            "Prova de exemplo oficial do TOEIC L&R da ETS (PDF)",
            "Visão geral oficial do programa TOEIC L&R da ETS",
        ),
        "heuristic_title": (
            "Como funciona a lógica de distribuição deste planejador"
        ),
        "heuristic_intro": (
            "Esta distribuição é uma referência simples e editável criada por este "
            "site. Não é uma recomendação da ETS e não prevê nenhuma nota."
        ),
        "heuristic_list": (
            "Equilibrado: 35% listening, 35% reading, 20% revisão, 10% prática "
            "cronometrada.",
            "Ênfase em listening: 50% listening, 25% reading, 15% revisão, 10% "
            "prática cronometrada.",
            "Ênfase em reading: 25% listening, 50% reading, 15% revisão, 10% prática "
            "cronometrada.",
            "Se você não estiver pronto(a) para a prática cronometrada, essa parte é "
            "transferida para a revisão.",
            "Os minutos são distribuídos pelo método do maior resto, para que as "
            "quatro partes sempre somem exatamente o total de minutos planejados.",
        ),
        "trademark_notice": (
            "TOEIC é uma marca da ETS. O Aim990 é um auxílio de estudo independente e "
            "não é afiliado nem endossado pela ETS. Nenhum aplicativo ou plano pode "
            "garantir uma nota do TOEIC."
        ),
        "webmcp_source": (
            "Prévia da API imperativa Chrome WebMCP (sujeita a alterações)"
        ),
        "webmcp_description": (
            "Cria uma distribuição transparente do tempo de estudo do TOEIC a partir "
            "de números e opções limitados e não sensíveis. Nunca recebe respostas de "
            "prova, gravações, documentos, nomes, contatos, contas ou data exata da "
            "prova; nunca produz previsão de nota, conceito de nível, resultado de "
            "aprovação/reprovação ou alegação de vínculo com a ETS."
        ),
        "app_title": "Quer um coach de TOEIC guiado opcional?",
        "app_text": (
            "O Aim990 é opcional. Sua ficha atual na App Store descreve um download "
            "gratuito com compras no app, um coach de TOEIC Listening & Reading de 30 "
            "dias, um diagnóstico de nível de 8 minutos, tarefas diárias de listening/"
            "reading/gramática/vocabulário e simulados, além de acompanhamento de "
            "progresso e pontos fracos; o rótulo de privacidade da Apple indica que "
            "nenhum dado é coletado. Verifique a ficha atual antes de comprar, pois "
            "recursos e preços podem mudar. Este planejador funciona completamente "
            "sem o aplicativo."
        ),
        "app_cta": "Ver Aim990 na App Store",
        "faq_title": "Perguntas sobre a distribuição de estudo do TOEIC",
        "faq": (
            (
                "Esta página recebe minhas respostas de prova, gravações ou "
                "documentos?",
                "Não. Ela aceita apenas números limitados, uma escolha de equilíbrio "
                "e um alternador de prontidão.",
            ),
            (
                "Isso prevê minha nota do TOEIC?",
                "Não. Isso apenas distribui seus próprios minutos; nunca estima, "
                "avalia ou prevê nenhuma nota ou resultado de aprovação/reprovação.",
            ),
            (
                "O Aim990 é afiliado à ETS ou ao programa TOEIC?",
                "Não. TOEIC é uma marca da ETS. O Aim990 é um auxílio de estudo "
                "independente e não é afiliado nem endossado pela ETS.",
            ),
            (
                "De onde vem a porcentagem de distribuição?",
                "É a referência de planejamento própria e editável deste site, não "
                "uma recomendação oficial da ETS ou da IIBC.",
            ),
            (
                "E se eu não estiver pronto(a) para a prática cronometrada?",
                "Desative o alternador de prontidão e esses minutos são transferidos "
                "para a revisão; o total permanece o mesmo.",
            ),
        ),
        "footer": (
            "Somente números privados limitados · sem documentos · sem previsão de "
            "nota · sem vínculo com a ETS"
        ),
        "index_title": "Planejador privado de distribuição de estudo TOEIC",
        "index_description": (
            "Transforma números de estudo limitados em uma distribuição transparente "
            "entre listening, reading, revisão e prática cronometrada, sem conta e "
            "sem previsão de nota."
        ),
        "inline_link_label": (
            "Planejador grátis de distribuição de estudo TOEIC (sem previsão de "
            "nota)"
        ),
    },
    "de-DE": {
        "title": (
            "Privater TOEIC-Lernzeit-Verteilungsplaner | Keine Punktzahlprognose"
        ),
        "description": (
            "Aus verfügbaren Tagen, Lerntagen pro Woche, Minuten pro Lerntag und "
            "Schwerpunkt wird transparent eine Aufteilung der Lernzeit auf Hören, "
            "Lesen, Wiederholung und Zeitübungen berechnet — ohne Konto, ohne "
            "Punktzahlprognose, ohne ETS-Zugehörigkeit."
        ),
        "tools": "Kostenlose Tools",
        "switch": "English",
        "eyebrow": "Kostenlos · kein Konto · keine Punktzahlprognose",
        "heading": "Privater TOEIC-Lernzeit-Verteilungsplaner",
        "lead": (
            "Aus wenigen begrenzten Zahlen entsteht eine transparente Aufteilung der "
            "Lernzeit auf Hören, Lesen, Wiederholung und Zeitübungen. Dies ist eine "
            "von dieser Seite erstellte Planungshilfe, keine Punktzahlprognose, keine "
            "Diagnose und keine Empfehlung von ETS."
        ),
        "badges": (
            "Keine Testantworten, Aufnahmen oder Dokumente",
            "Kein Name, keine E-Mail, kein Konto, kein genaues Prüfungsdatum",
            "Keine Punktzahl-, Noten- oder Bestehensprognose",
            "Keine Zugehörigkeit zu oder Befürwortung durch ETS",
        ),
        "planner": "Deine private Lernzeit-Verteilung erstellen",
        "planner_intro": (
            "Gib nur begrenzte Zahlen und kurze Auswahlen ein. Diese Seite fragt nie "
            "nach Testantworten, Aufnahmen, Dokumenten oder persönlichen Angaben."
        ),
        "days_label": "Verfügbare Tage bis zum Zieldatum (1–30)",
        "days_per_week_label": (
            "Lerntage, die du pro Woche einplanen kannst (1–7)"
        ),
        "minutes_label": (
            "Minuten, die du an jedem Lerntag aufwenden kannst (10–120)"
        ),
        "emphasis_label": "Welche Gewichtung möchtest du?",
        "emphasis_options": {
            "balanced": "Hören und Lesen ausgewogen",
            "listening": "Schwerpunkt Hören",
            "reading": "Schwerpunkt Lesen",
        },
        "timed_label": "Ich bin bereit für Zeitübungen",
        "update": "Privaten Plan aktualisieren",
        "invalid_input": (
            "Gib Werte innerhalb der oben angegebenen unterstützten Bereiche ein."
        ),
        "result_sessions": "Geplante Lerneinheiten",
        "result_total": "Geplante Gesamtminuten",
        "result_listening": "Hörverstehen-Minuten",
        "result_reading": "Lesen-Minuten",
        "result_review": "Wiederholungs-Minuten",
        "result_timed": "Zeitübungs-Minuten",
        "result_plan_label": "Nächste Schritte",
        "next_steps": (
            "Bestätige deine eigenen verfügbaren Tage, Lerntage pro Woche und Minuten "
            "pro Lerntag; dein genaues Prüfungsdatum erhält diese Seite nie.",
            "Wähle eine Gewichtung (ausgewogen, Hören oder Lesen) und ob du für "
            "Zeitübungen bereit bist.",
            "Nutze die Zeitaufteilung nur als bearbeitbaren Ausgangspunkt und passe "
            "sie an deine eigenen Schwächen an.",
            "Der echte TOEIC-Test hat ein festes, nur englischsprachiges Format — "
            "prüfe vor der weiteren Planung das offizielle IIBC-Format und den "
            "offiziellen ETS-Beispieltest.",
            "Überarbeite die Aufteilung alle paar Tage, statt ihr starr zu folgen.",
        ),
        "boundary_title": "Was dieser Planer nicht tut",
        "boundary_text": (
            "Dieser Planer sagt keine TOEIC-Punktzahl voraus, bewertet oder "
            "diagnostiziert keine Fähigkeit, garantiert keine Verbesserung und "
            "suggeriert keine Zugehörigkeit zu oder Befürwortung durch ETS. Er "
            "wandelt lediglich deine eigenen begrenzten Zahlen mit einer festen, "
            "dokumentierten Heuristik in eine bearbeitbare Zeitaufteilung um."
        ),
        "sources_title": "Offizielle Fakten und Quellen zum TOEIC-L&R-Format",
        "sources_intro": (
            "Diese Fakten stammen von den offiziellen Seiten von IIBC und ETS, nicht "
            "von dieser Website. Nutze sie, um jeden Lernplan — auch diesen — zu "
            "überprüfen."
        ),
        "official_facts": (
            "Der TOEIC-Listening-&-Reading-Test umfasst 200 Fragen, die in zwei "
            "Stunden bearbeitet werden.",
            "Hören: etwa 45 Minuten für 100 Fragen.",
            "Lesen: 75 Minuten für 100 Fragen.",
            "Der Test selbst wird ausschließlich auf Englisch durchgeführt, und das "
            "Format ist bei jeder Durchführung gleich.",
        ),
        "source_labels": (
            "Offizielles TOEIC-L&R-Testformat der IIBC",
            "Offizieller TOEIC-L&R-Beispieltest der ETS (PDF)",
            "Offizieller Überblick zum TOEIC-L&R-Programm der ETS",
        ),
        "heuristic_title": (
            "So funktioniert die Verteilungslogik dieses Planers"
        ),
        "heuristic_intro": (
            "Diese Aufteilung ist eine einfache, bearbeitbare Heuristik dieser "
            "Website. Sie ist keine Empfehlung von ETS und sagt keine Punktzahl "
            "voraus."
        ),
        "heuristic_list": (
            "Ausgewogen: 35 % Hören, 35 % Lesen, 20 % Wiederholung, 10 % "
            "Zeitübungen.",
            "Schwerpunkt Hören: 50 % Hören, 25 % Lesen, 15 % Wiederholung, 10 % "
            "Zeitübungen.",
            "Schwerpunkt Lesen: 25 % Hören, 50 % Lesen, 15 % Wiederholung, 10 % "
            "Zeitübungen.",
            "Bist du nicht bereit für Zeitübungen, wandert dieser Anteil stattdessen "
            "in die Wiederholung.",
            "Die Minuten werden nach dem Verfahren des größten Rests verteilt, "
            "sodass die vier Teile immer genau der geplanten Gesamtminutenzahl "
            "entsprechen.",
        ),
        "trademark_notice": (
            "TOEIC ist eine Marke von ETS. Aim990 ist eine unabhängige Lernhilfe und "
            "steht in keiner Verbindung zu ETS und wird nicht von ETS befürwortet. "
            "Keine App und kein Plan kann eine TOEIC-Punktzahl garantieren."
        ),
        "webmcp_source": (
            "Vorschau der Chrome-WebMCP-Imperative-API (kann sich noch ändern)"
        ),
        "webmcp_description": (
            "Erstellt eine transparente TOEIC-Lernzeit-Verteilung aus begrenzten, "
            "nicht sensiblen Zahlen und Auswahlmöglichkeiten. Es werden nie "
            "Testantworten, Aufnahmen, Dokumente, Namen, Kontaktdaten, Konten oder "
            "ein genaues Prüfungsdatum entgegengenommen, und es wird nie eine "
            "Punktzahlprognose, Bewertungsnote, ein Bestehensergebnis oder eine "
            "ETS-Zugehörigkeit behauptet."
        ),
        "app_title": "Möchtest du einen optionalen geführten TOEIC-Coach?",
        "app_text": (
            "Aim990 ist optional. Der aktuelle App-Store-Eintrag beschreibt einen "
            "kostenlosen Download mit In-App-Käufen, einen 30-tägigen "
            "TOEIC-Listening-&-Reading-Coach, eine 8-minütige Niveaudiagnose, "
            "tägliche Aufgaben zu Hören/Lesen/Grammatik/Wortschatz und "
            "Testsimulationen sowie Fortschritts- und Schwachstellen-Tracking; Apples "
            "Datenschutzlabel gibt an, dass keine Daten erhoben werden. Prüfe vor dem "
            "Kauf den aktuellen Eintrag, da sich Funktionen und Preise ändern können. "
            "Dieser Planer funktioniert auch vollständig ohne die App."
        ),
        "app_cta": "Aim990 im App Store ansehen",
        "faq_title": "Fragen zur TOEIC-Lernzeit-Verteilung",
        "faq": (
            (
                "Erhält diese Seite meine Testantworten, Aufnahmen oder Dokumente?",
                "Nein. Sie akzeptiert nur begrenzte Zahlen, eine "
                "Gewichtungsauswahl und einen Bereitschafts-Schalter.",
            ),
            (
                "Sagt das meine TOEIC-Punktzahl voraus?",
                "Nein. Es teilt nur deine eigenen Minuten auf; es schätzt, bewertet "
                "oder prognostiziert nie eine Punktzahl oder ein Bestehensergebnis.",
            ),
            (
                "Ist Aim990 mit ETS oder dem TOEIC-Programm verbunden?",
                "Nein. TOEIC ist eine Marke von ETS. Aim990 ist eine unabhängige "
                "Lernhilfe und steht in keiner Verbindung zu ETS und wird nicht von "
                "ETS befürwortet.",
            ),
            (
                "Woher stammt der Verteilungsprozentsatz?",
                "Er stammt aus der eigenen, bearbeitbaren Planungsheuristik dieser "
                "Website und ist keine offizielle Empfehlung von ETS oder IIBC.",
            ),
            (
                "Was, wenn ich für Zeitübungen noch nicht bereit bin?",
                "Schalte den Bereitschafts-Schalter aus, und die dafür geplanten "
                "Minuten wandern in die Wiederholung — die Gesamtzeit bleibt gleich.",
            ),
        ),
        "footer": (
            "Nur private, begrenzte Zahlen · keine Dokumente · keine "
            "Punktzahlprognose · keine ETS-Zugehörigkeit"
        ),
        "index_title": "Privater TOEIC-Lernzeit-Verteilungsplaner",
        "index_description": (
            "Wandelt begrenzte Lernzahlen in eine transparente Aufteilung von Hören, "
            "Lesen, Wiederholung und Zeitübungen um — ohne Konto und ohne "
            "Punktzahlprognose."
        ),
        "inline_link_label": (
            "Kostenloser TOEIC-Lernzeit-Verteilungsplaner (keine Punktzahlprognose)"
        ),
    },
    "fr-FR": {
        "title": (
            "Planificateur privé de répartition d'étude TOEIC | Aucune prédiction "
            "de score"
        ),
        "description": (
            "À partir des jours disponibles, des jours d'étude par semaine, des "
            "minutes par jour et de l'accent souhaité, calculez de façon "
            "transparente une répartition du temps d'étude entre écoute, lecture, "
            "révision et entraînement chronométré — sans compte, sans prédiction de "
            "score, sans lien avec ETS."
        ),
        "tools": "Outils gratuits",
        "switch": "English",
        "eyebrow": "Gratuit · sans compte · aucune prédiction de score",
        "heading": "Planificateur privé de répartition d'étude TOEIC",
        "lead": (
            "À partir de quelques chiffres bornés, obtenez une répartition "
            "transparente du temps d'étude entre écoute, lecture, révision et "
            "entraînement chronométré. Il s'agit d'un repère de planification créé "
            "par ce site, pas d'une prédiction de score, d'un diagnostic ni d'une "
            "recommandation d'ETS."
        ),
        "badges": (
            "Aucune réponse de test, enregistrement ou document",
            "Aucun nom, e-mail, compte ni date d'examen exacte",
            "Aucune prédiction de score, de note ou de réussite",
            "Aucun lien ni approbation avec ETS",
        ),
        "planner": "Créer votre répartition d'étude privée",
        "planner_intro": (
            "Saisissez uniquement des nombres dans les limites indiquées et de courts "
            "choix. Cette page ne demande jamais de réponses au test, "
            "d'enregistrements, de documents ni de données personnelles."
        ),
        "days_label": "Jours disponibles avant votre date cible (1 à 30)",
        "days_per_week_label": (
            "Jours d'étude que vous pouvez consacrer par semaine (1 à 7)"
        ),
        "minutes_label": (
            "Minutes que vous pouvez consacrer chaque jour d'étude (10 à 120)"
        ),
        "emphasis_label": "Quel équilibre souhaitez-vous?",
        "emphasis_options": {
            "balanced": "Écoute et lecture équilibrées",
            "listening": "Accent sur l'écoute",
            "reading": "Accent sur la lecture",
        },
        "timed_label": "Je suis prêt(e) pour l'entraînement chronométré",
        "update": "Mettre à jour le plan privé",
        "invalid_input": (
            "Saisissez des valeurs dans les plages prises en charge indiquées "
            "ci-dessus."
        ),
        "result_sessions": "Séances d'étude planifiées",
        "result_total": "Minutes totales planifiées",
        "result_listening": "Minutes d'écoute",
        "result_reading": "Minutes de lecture",
        "result_review": "Minutes de révision",
        "result_timed": "Minutes d'entraînement chronométré",
        "result_plan_label": "Prochaines étapes",
        "next_steps": (
            "Confirmez vos propres jours disponibles, jours d'étude par semaine et "
            "minutes par jour; cette page ne reçoit jamais votre date d'examen "
            "exacte.",
            "Choisissez un équilibre (équilibré, écoute ou lecture) et indiquez si "
            "vous êtes prêt(e) pour l'entraînement chronométré.",
            "Utilisez cette répartition uniquement comme point de départ "
            "modifiable, puis ajustez-la selon vos propres points faibles.",
            "Le format du vrai test TOEIC est fixe et uniquement en anglais; "
            "consultez le format officiel de l'IIBC et l'exemple de test officiel "
            "d'ETS avant d'aller plus loin.",
            "Révisez et ajustez la répartition tous les quelques jours plutôt que "
            "de la suivre rigidement.",
        ),
        "boundary_title": "Ce que ce planificateur ne fait pas",
        "boundary_text": (
            "Ce planificateur ne prédit pas votre score TOEIC, ne note ni ne "
            "diagnostique votre niveau, ne garantit aucune progression et ne "
            "suggère aucun lien ni approbation avec ETS. Il transforme uniquement "
            "vos propres chiffres bornés en une répartition modifiable, selon un "
            "calcul fixe et transparent."
        ),
        "sources_title": "Faits officiels sur le format TOEIC L&R et sources",
        "sources_intro": (
            "Ces faits proviennent des pages officielles de l'IIBC et d'ETS, pas de "
            "ce site. Utilisez-les pour vérifier tout plan d'étude, y compris "
            "celui-ci."
        ),
        "official_facts": (
            "Le test TOEIC Listening & Reading comporte 200 questions à réaliser en "
            "deux heures.",
            "Écoute: environ 45 minutes pour 100 questions.",
            "Lecture: 75 minutes pour 100 questions.",
            "Le test lui-même est proposé uniquement en anglais, et le format est "
            "identique à chaque session.",
        ),
        "source_labels": (
            "Format officiel du test TOEIC L&R (IIBC)",
            "Exemple de test officiel TOEIC L&R d'ETS (PDF)",
            "Présentation officielle du programme TOEIC L&R d'ETS",
        ),
        "heuristic_title": (
            "Comment fonctionne le repère de répartition de ce planificateur"
        ),
        "heuristic_intro": (
            "Cette répartition est un repère simple et modifiable créé par ce "
            "site. Ce n'est pas une recommandation d'ETS et cela ne prédit aucun "
            "score."
        ),
        "heuristic_list": (
            "Équilibré: 35 % écoute, 35 % lecture, 20 % révision, 10 % "
            "entraînement chronométré.",
            "Accent écoute: 50 % écoute, 25 % lecture, 15 % révision, 10 % "
            "entraînement chronométré.",
            "Accent lecture: 25 % écoute, 50 % lecture, 15 % révision, 10 % "
            "entraînement chronométré.",
            "Si vous n'êtes pas prêt(e) pour l'entraînement chronométré, sa part "
            "est reportée sur la révision.",
            "Les minutes sont réparties selon la méthode du plus fort reste, afin "
            "que les quatre parts totalisent toujours exactement vos minutes "
            "totales planifiées.",
        ),
        "trademark_notice": (
            "TOEIC est une marque d'ETS. Aim990 est une aide à l'étude indépendante "
            "et n'est ni affiliée à ETS ni approuvée par ETS. Aucune application ni "
            "aucun plan ne peut garantir un score TOEIC."
        ),
        "webmcp_source": (
            "Aperçu de l'API impérative Chrome WebMCP (susceptible de changer)"
        ),
        "webmcp_description": (
            "Crée une répartition transparente du temps d'étude TOEIC à partir de "
            "chiffres et de choix bornés et non sensibles. Ne reçoit jamais de "
            "réponses de test, d'enregistrements, de documents, de noms, de "
            "coordonnées, de comptes ni de date d'examen exacte; ne produit jamais "
            "de prédiction de score, de note de niveau, de résultat de réussite ni "
            "d'affirmation de lien avec ETS."
        ),
        "app_title": "Vous voulez un coach TOEIC guidé en option?",
        "app_text": (
            "Aim990 est optionnel. Sa fiche App Store actuelle décrit un "
            "téléchargement gratuit avec achats intégrés, un coach TOEIC Listening "
            "& Reading sur 30 jours, un diagnostic de niveau en 8 minutes, des "
            "tâches quotidiennes d'écoute/lecture/grammaire/vocabulaire et des "
            "tests blancs, ainsi qu'un suivi de la progression et des points "
            "faibles; l'étiquette de confidentialité d'Apple indique qu'aucune "
            "donnée n'est collectée. Vérifiez la fiche actuelle avant tout achat, "
            "car les fonctionnalités et les prix peuvent changer. Ce planificateur "
            "fonctionne entièrement sans l'application."
        ),
        "app_cta": "Voir Aim990 sur l'App Store",
        "faq_title": "Questions sur la répartition d'étude TOEIC",
        "faq": (
            (
                "Cette page reçoit-elle mes réponses de test, enregistrements ou "
                "documents?",
                "Non. Elle n'accepte que des chiffres bornés, un choix d'équilibre "
                "et un interrupteur de disponibilité.",
            ),
            (
                "Cela prédit-il mon score TOEIC?",
                "Non. Cela répartit uniquement vos propres minutes; cela n'estime, "
                "ne note ni ne prédit jamais un score ou un résultat de réussite.",
            ),
            (
                "Aim990 est-il affilié à ETS ou au programme TOEIC?",
                "Non. TOEIC est une marque d'ETS. Aim990 est une aide à l'étude "
                "indépendante et n'est ni affiliée à ETS ni approuvée par ETS.",
            ),
            (
                "D'où vient le pourcentage de répartition?",
                "Il s'agit du repère de planification propre et modifiable de ce "
                "site, pas d'une recommandation officielle d'ETS ou de l'IIBC.",
            ),
            (
                "Que se passe-t-il si je ne suis pas prêt(e) pour l'entraînement "
                "chronométré?",
                "Désactivez l'interrupteur de disponibilité et ces minutes seront "
                "reportées sur la révision, le total restant inchangé.",
            ),
        ),
        "footer": (
            "Uniquement des chiffres privés bornés · aucun document · aucune "
            "prédiction de score · aucun lien avec ETS"
        ),
        "index_title": "Planificateur privé de répartition d'étude TOEIC",
        "index_description": (
            "Transforme des chiffres d'étude bornés en une répartition "
            "transparente entre écoute, lecture, révision et entraînement "
            "chronométré, sans compte ni prédiction de score."
        ),
        "inline_link_label": (
            "Planificateur gratuit de répartition d'étude TOEIC (sans prédiction "
            "de score)"
        ),
    },
    "ja": {
        "title": "非公開TOEIC学習配分プランナー | スコア予測なし",
        "description": (
            "学習可能日数、週の学習日数、1日の学習分数、重視バランスから、リスニング/"
            "リーディング/復習/タイム練習の学習時間配分を透明に算出。アカウント不要、"
            "スコア予測なし、ETSとの提携なし。"
        ),
        "tools": "無料ツール",
        "switch": "English",
        "eyebrow": "無料・アカウント不要・スコア予測なし",
        "heading": "非公開TOEIC学習配分プランナー",
        "lead": (
            "いくつかの範囲内の数値だけで、リスニング・リーディング・復習・タイム練習"
            "への学習時間配分を透明に算出します。これは本サイトが作成した学習用の目安"
            "であり、スコア予測・診断・ETSの推奨ではありません。"
        ),
        "badges": (
            "解答・録音・書類の送信なし",
            "氏名・メール・アカウント・正確な受験日の送信なし",
            "スコア・等級・合否の予測なし",
            "ETSとの提携・推奨関係なし",
        ),
        "planner": "非公開の学習配分を作成",
        "planner_intro": (
            "入力するのは範囲内の数値と短い選択肢だけです。テストの解答、録音、書類、"
            "個人情報を入力する必要はありません。"
        ),
        "days_label": "目標日までに使える日数(1〜30)",
        "days_per_week_label": "週に確保できる学習日数(1〜7)",
        "minutes_label": "1回の学習日に使える分数(10〜120)",
        "emphasis_label": "どのバランスを希望しますか?",
        "emphasis_options": {
            "balanced": "リスニングとリーディングを均等に",
            "listening": "リスニング重視",
            "reading": "リーディング重視",
        },
        "timed_label": "タイム練習(時間を計る練習)を含める準備がある",
        "update": "非公開プランを更新",
        "invalid_input": "上記の対応範囲内の値を入力してください。",
        "result_sessions": "計画された学習回数",
        "result_total": "計画された合計分数",
        "result_listening": "リスニングの分数",
        "result_reading": "リーディングの分数",
        "result_review": "復習の分数",
        "result_timed": "タイム練習の分数",
        "result_plan_label": "次のステップ",
        "next_steps": (
            "自分の学習可能日数・週の学習日数・1日の学習分数を確認してください。正確"
            "な受験日はこのページに送信されません。",
            "バランス(均等・リスニング重視・リーディング重視)と、タイム練習の準備"
            "状況を選んでください。",
            "この時間配分は編集可能な出発点として使い、自分の弱点に合わせて調整して"
            "ください。",
            "本番のTOEICは形式が固定で英語のみのため、計画を進める前にIIBCの公式形"
            "式とETSのサンプルテストを確認してください。",
            "配分を厳格に守るのではなく、数日ごとに見直して調整してください。",
        ),
        "boundary_title": "このプランナーが行わないこと",
        "boundary_text": (
            "このプランナーはTOEICスコアを予測したり、習熟度を採点・診断したり、ス"
            "コア向上を保証したり、ETSとの提携や推奨関係を示唆したりしません。あなた"
            "自身が入力した範囲内の数値を、決まった透明な計算式で編集可能な時間配分"
            "に変換するだけです。"
        ),
        "sources_title": "TOEIC L&Rの公式形式に関する事実と情報源",
        "sources_intro": (
            "これらの事実はIIBCおよびETSの公式ページによるもので、本サイトの見解で"
            "はありません。本プランナーを含め、どの学習計画も、この事実と照らし合わ"
            "せて確認してください。"
        ),
        "official_facts": (
            "TOEIC Listening & Readingテストは200問で、2時間で実施されます。",
            "リスニング:約45分で100問。",
            "リーディング:75分で100問。",
            "テスト自体は英語のみで実施され、形式は毎回同じです。",
        ),
        "source_labels": (
            "IIBC公式 TOEIC L&Rテスト形式",
            "ETS公式 TOEIC L&Rサンプルテスト(PDF)",
            "ETS公式 TOEIC L&Rプログラム概要",
        ),
        "heuristic_title": "このプランナーの配分ロジックの仕組み",
        "heuristic_intro": (
            "この配分は本サイトが作成した、編集可能なシンプルな目安です。ETSの推奨で"
            "はなく、スコアを予測するものでもありません。"
        ),
        "heuristic_list": (
            "均等:リスニング35%、リーディング35%、復習20%、タイム練習10%。",
            "リスニング重視:リスニング50%、リーディング25%、復習15%、タイム練習"
            "10%。",
            "リーディング重視:リスニング25%、リーディング50%、復習15%、タイム練習"
            "10%。",
            "タイム練習の準備がない場合、その分は復習に振り替えられます。",
            "分数は最大剰余法で配分されるため、4項目の合計は常に計画した合計分数と"
            "正確に一致します。",
        ),
        "trademark_notice": (
            "TOEICはETSの商標です。Aim990は独立した学習アプリであり、ETSとの提携や"
            "推奨関係はありません。どのアプリやプランもTOEICスコアを保証することは"
            "できません。"
        ),
        "webmcp_source": "Chrome WebMCP 命令型APIプレビュー(仕様変更の可能性あり)",
        "webmcp_description": (
            "範囲が決まった非機密の数値と選択肢から、透明なTOEIC学習時間配分を作成"
            "します。解答・録音・書類・氏名・連絡先・アカウント・正確な受験日は一切"
            "受け取らず、スコア予測・習熟度評価・合否判定・ETS提携の主張も一切行い"
            "ません。"
        ),
        "app_title": "ガイド付きのTOEICコーチアプリも試しますか?",
        "app_text": (
            "Aim990は任意です。現在のApp Store掲載によると、アプリ内課金付きの無料"
            "ダウンロード、30日間のTOEIC Listening & Readingコーチ、8分間のレベル診"
            "断、毎日のリスニング/リーディング/文法/語彙と模擬テストの課題、進捗と弱"
            "点の追跡機能があり、Appleのプライバシーラベルではデータは収集されない"
            "とされています。機能や価格は変更される可能性があるため、購入前に必ず現"
            "在の掲載内容を確認してください。本プランナーはアプリなしでも完全に機能"
            "します。"
        ),
        "app_cta": "App StoreでAim990を見る",
        "faq_title": "TOEIC学習配分に関するよくある質問",
        "faq": (
            (
                "このページは解答・録音・書類を受け取りますか?",
                "いいえ。範囲が決まった数値、バランスの選択、準備状況のトグルのみを"
                "受け付けます。",
            ),
            (
                "これは私のTOEICスコアを予測しますか?",
                "いいえ。あなた自身の分数を配分するだけで、スコアや合否を推定・採"
                "点・予測することはありません。",
            ),
            (
                "Aim990はETSやTOEICプログラムと提携していますか?",
                "いいえ。TOEICはETSの商標です。Aim990は独立した学習アプリであり、"
                "ETSとの提携や推奨関係はありません。",
            ),
            (
                "配分の割合はどこから来ていますか?",
                "本サイトが作成した編集可能な目安であり、ETSやIIBCの公式な推奨では"
                "ありません。",
            ),
            (
                "タイム練習の準備ができていない場合は?",
                "準備状況のトグルをオフにすると、その分の時間は復習に振り替えられ、"
                "合計時間は変わりません。",
            ),
        ),
        "footer": (
            "非公開の範囲内数値のみ・書類なし・スコア予測なし・ETS提携なし"
        ),
        "index_title": "非公開TOEIC学習配分プランナー",
        "index_description": (
            "範囲が決まった学習数値から、リスニング/リーディング/復習/タイム練習の"
            "時間配分を透明に算出。アカウント不要、スコア予測なし。"
        ),
        "inline_link_label": "無料TOEIC学習配分プランナー(スコア予測なし)",
    },
    "ko": {
        "title": "비공개 TOEIC 학습 배분 플래너 | 점수 예측 없음",
        "description": (
            "학습 가능 일수, 주당 학습일, 하루 학습 분수, 학습 비중을 바탕으로 리스"
            "닝/리딩/복습/시간제 연습 시간을 투명하게 배분합니다. 계정 불필요, 점수 "
            "예측 없음, ETS와 제휴 없음."
        ),
        "tools": "무료 도구",
        "switch": "English",
        "eyebrow": "무료 · 계정 불필요 · 점수 예측 없음",
        "heading": "비공개 TOEIC 학습 배분 플래너",
        "lead": (
            "제한된 범위의 숫자 몇 개만으로 리스닝, 리딩, 복습, 시간제 연습에 대한 "
            "학습 시간을 투명하게 배분합니다. 이는 본 사이트가 만든 학습 참고용 계"
            "산일 뿐, 점수 예측이나 진단, ETS의 권장 사항이 아닙니다."
        ),
        "badges": (
            "정답, 녹음, 서류 전송 없음",
            "이름, 이메일, 계정, 정확한 시험일 전송 없음",
            "점수, 등급, 합격/불합격 예측 없음",
            "ETS와 제휴 또는 보증 관계 없음",
        ),
        "planner": "비공개 학습 배분 만들기",
        "planner_intro": (
            "범위 안의 숫자와 짧은 선택 항목만 입력하세요. 이 페이지는 시험 답안, "
            "녹음, 문서 또는 개인정보를 요구하지 않습니다."
        ),
        "days_label": "목표일까지 남은 학습 가능 일수(1~30)",
        "days_per_week_label": "주당 확보 가능한 학습일 수(1~7)",
        "minutes_label": "학습일마다 사용할 수 있는 분수(10~120)",
        "emphasis_label": "어떤 비중을 원하시나요?",
        "emphasis_options": {
            "balanced": "리스닝과 리딩 균형",
            "listening": "리스닝 중심",
            "reading": "리딩 중심",
        },
        "timed_label": "시간제 연습을 포함할 준비가 되었습니다",
        "update": "비공개 플랜 업데이트",
        "invalid_input": "위에 표시된 지원 범위 내의 값을 입력하세요.",
        "result_sessions": "계획된 학습 횟수",
        "result_total": "계획된 총 분수",
        "result_listening": "리스닝 분수",
        "result_reading": "리딩 분수",
        "result_review": "복습 분수",
        "result_timed": "시간제 연습 분수",
        "result_plan_label": "다음 단계",
        "next_steps": (
            "본인의 학습 가능 일수, 주당 학습일, 하루 학습 분수를 확인하세요. 이 페"
            "이지는 정확한 시험일을 받지 않습니다.",
            "비중(균형, 리스닝 중심, 리딩 중심)과 시간제 연습 준비 여부를 선택하세"
            "요.",
            "이 시간 배분은 수정 가능한 출발점으로만 사용하고, 본인의 취약 영역에 "
            "맞게 조정하세요.",
            "실제 TOEIC은 형식이 고정되어 있고 영어로만 진행되므로, 계획을 세우기 "
            "전에 IIBC 공식 형식과 ETS 샘플 테스트를 확인하세요.",
            "배분을 엄격히 따르기보다 며칠마다 다시 검토하고 조정하세요.",
        ),
        "boundary_title": "이 플래너가 하지 않는 것",
        "boundary_text": (
            "이 플래너는 TOEIC 점수를 예측하거나, 실력을 채점·진단하거나, 향상을 보"
            "장하거나, ETS와의 제휴나 보증 관계를 암시하지 않습니다. 본인이 입력한 "
            "제한된 숫자를 고정되고 투명한 계산식으로 수정 가능한 시간 배분으로 변환"
            "할 뿐입니다."
        ),
        "sources_title": "TOEIC L&R 공식 형식 사실 및 출처",
        "sources_intro": (
            "이 사실들은 IIBC와 ETS의 공식 페이지에서 가져온 것이며, 본 사이트의 의"
            "견이 아닙니다. 이 플래너를 포함한 어떤 학습 계획도 이 사실과 대조하여 "
            "확인하세요."
        ),
        "official_facts": (
            "TOEIC Listening & Reading 시험은 총 200문항으로 2시간 동안 진행됩니다.",
            "리스닝: 약 45분, 100문항.",
            "리딩: 75분, 100문항.",
            "시험 자체는 영어로만 진행되며, 형식은 매회 동일합니다.",
        ),
        "source_labels": (
            "IIBC 공식 TOEIC L&R 시험 형식",
            "ETS 공식 TOEIC L&R 샘플 테스트(PDF)",
            "ETS 공식 TOEIC L&R 프로그램 개요",
        ),
        "heuristic_title": "이 플래너의 배분 계산 방식",
        "heuristic_intro": (
            "이 배분은 본 사이트가 만든 간단하고 수정 가능한 참고 계산입니다. ETS의 "
            "권장 사항이 아니며 점수를 예측하지도 않습니다."
        ),
        "heuristic_list": (
            "균형: 리스닝 35%, 리딩 35%, 복습 20%, 시간제 연습 10%.",
            "리스닝 중심: 리스닝 50%, 리딩 25%, 복습 15%, 시간제 연습 10%.",
            "리딩 중심: 리스닝 25%, 리딩 50%, 복습 15%, 시간제 연습 10%.",
            "시간제 연습 준비가 안 된 경우, 해당 비중은 복습으로 이동합니다.",
            "분수는 최대 나머지 방식으로 배분되어 네 항목의 합이 항상 계획된 총 분"
            "수와 정확히 일치합니다.",
        ),
        "trademark_notice": (
            "TOEIC은 ETS의 상표입니다. Aim990은 독립적인 학습 보조 앱이며 ETS와 제"
            "휴하거나 보증받지 않았습니다. 어떤 앱이나 계획도 TOEIC 점수를 보장할 수"
            " 없습니다."
        ),
        "webmcp_source": "Chrome WebMCP 명령형 API 프리뷰(변경될 수 있음)",
        "webmcp_description": (
            "범위가 제한된 비민감 숫자와 선택 항목으로 투명한 TOEIC 학습 시간 배분"
            "을 만듭니다. 정답, 녹음, 서류, 이름, 연락처, 계정, 정확한 시험일은 받지"
            " 않으며, 점수 예측, 실력 등급, 합격/불합격 결과, ETS 제휴 주장도 하지 "
            "않습니다."
        ),
        "app_title": "가이드가 있는 TOEIC 코치 앱도 원하시나요?",
        "app_text": (
            "Aim990은 선택 사항입니다. 현재 App Store 등록 정보에 따르면 인앱 구매"
            "가 있는 무료 다운로드, 30일 TOEIC Listening & Reading 코치, 8분 레벨 진"
            "단, 매일 리스닝/리딩/문법/어휘 및 모의고사 과제, 진행 상황 및 취약 영역"
            " 추적 기능이 있으며, Apple의 개인정보 보호 라벨에는 데이터가 수집되지 "
            "않는다고 명시되어 있습니다. 기능과 가격은 변경될 수 있으니 구매 전 현재"
            " 등록 정보를 확인하세요. 이 플래너는 앱 없이도 완전히 작동합니다."
        ),
        "app_cta": "App Store에서 Aim990 보기",
        "faq_title": "TOEIC 학습 배분 관련 질문",
        "faq": (
            (
                "이 페이지가 제 정답, 녹음, 서류를 받나요?",
                "아니요. 범위가 제한된 숫자, 비중 선택, 준비 여부 토글만 받습니다.",
            ),
            (
                "이것이 제 TOEIC 점수를 예측하나요?",
                "아니요. 본인의 시간을 배분할 뿐이며, 점수나 합격 여부를 추정·채점·"
                "예측하지 않습니다.",
            ),
            (
                "Aim990이 ETS나 TOEIC 프로그램과 제휴되어 있나요?",
                "아니요. TOEIC은 ETS의 상표입니다. Aim990은 독립적인 학습 보조 앱이"
                "며 ETS와 제휴하거나 보증받지 않았습니다.",
            ),
            (
                "배분 비율은 어디서 나온 것인가요?",
                "본 사이트가 만든 수정 가능한 참고 계산이며, ETS나 IIBC의 공식 권장"
                " 사항이 아닙니다.",
            ),
            (
                "시간제 연습 준비가 안 되어 있다면요?",
                "준비 여부 토글을 끄면 해당 시간이 복습으로 이동하며, 총 시간은 그"
                "대로 유지됩니다.",
            ),
        ),
        "footer": "비공개 제한 숫자만 · 서류 없음 · 점수 예측 없음 · ETS 제휴 없음",
        "index_title": "비공개 TOEIC 학습 배분 플래너",
        "index_description": (
            "제한된 학습 숫자를 리스닝/리딩/복습/시간제 연습 시간으로 투명하게 배분"
            "합니다. 계정 불필요, 점수 예측 없음."
        ),
        "inline_link_label": "무료 TOEIC 학습 배분 플래너(점수 예측 없음)",
    },
    "zh-Hant": {
        "title": "私人 TOEIC 讀寫學習時間分配規劃器 | 不預測分數",
        "description": (
            "只需輸入可用天數、每週學習天數、每天學習分鐘數與偏重方向,就能透明算出"
            "聽力、閱讀、複習與計時練習的學習時間分配。免帳號、不預測分數、與 ETS "
            "無關。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費・免帳號・不預測分數",
        "heading": "私人 TOEIC 讀寫學習時間分配規劃器",
        "lead": (
            "只用幾個有範圍限制的數字,就能透明算出聽力、閱讀、複習與計時練習之間的"
            "學習時間分配。這只是本站建立的規劃參考,不是分數預測、能力診斷,也不是 "
            "ETS 的建議。"
        ),
        "badges": (
            "不收集答案、錄音或文件",
            "不收集姓名、Email、帳號或確切考試日期",
            "不預測分數、等級或及格與否",
            "與 ETS 無合作或背書關係",
        ),
        "planner": "建立你的私人學習時間分配",
        "planner_intro": (
            "只需輸入範圍內的數字與簡短選項。本頁不會要求測驗答案、錄音、文件或"
            "個人資料。"
        ),
        "days_label": "距離目標日期的可用天數(1–30)",
        "days_per_week_label": "每週能安排的學習天數(1–7)",
        "minutes_label": "每個學習日能投入的分鐘數(10–120)",
        "emphasis_label": "你想要哪種分配偏重?",
        "emphasis_options": {
            "balanced": "聽力與閱讀均衡",
            "listening": "偏重聽力",
            "reading": "偏重閱讀",
        },
        "timed_label": "我已準備好加入計時練習",
        "update": "更新私人規劃",
        "invalid_input": "請輸入上方標示的支援範圍內數值。",
        "result_sessions": "規劃的學習次數",
        "result_total": "規劃的總分鐘數",
        "result_listening": "聽力分鐘數",
        "result_reading": "閱讀分鐘數",
        "result_review": "複習分鐘數",
        "result_timed": "計時練習分鐘數",
        "result_plan_label": "接下來的步驟",
        "next_steps": (
            "確認你自己的可用天數、每週學習天數與每天學習分鐘數;本頁面不會收到你"
            "確切的考試日期。",
            "選擇偏重方向(均衡、偏重聽力或偏重閱讀),以及是否已準備好計時練習。",
            "把這個時間分配當成可調整的起點,再依自己的弱點自行調整。",
            "正式 TOEIC 考試形式固定且全程英語,規劃前請先查閱 IIBC 官方形式說明與 "
            "ETS 官方範例試題。",
            "不要死板地照著分配走,每隔幾天就重新檢視並調整。",
        ),
        "boundary_title": "這個規劃器不會做的事",
        "boundary_text": (
            "這個規劃器不會預測你的 TOEIC 分數、為你的能力打分或診斷、保證分數進"
            "步,也不會暗示與 ETS 有任何合作或背書關係。它只是用你自己輸入的有範圍"
            "限制數字,依固定且透明的公式轉換成可調整的時間分配。"
        ),
        "sources_title": "TOEIC 讀寫測驗官方形式事實與資料來源",
        "sources_intro": (
            "以下事實來自 IIBC 與 ETS 的官方頁面,不是本站的說法。無論是這個規劃器"
            "或任何學習計畫,都應該對照這些事實來檢查。"
        ),
        "official_facts": (
            "TOEIC 聽力與閱讀測驗共 200 題,於兩小時內完成。",
            "聽力:約 45 分鐘,共 100 題。",
            "閱讀:75 分鐘,共 100 題。",
            "測驗本身只以英語進行,且每次考試形式相同。",
        ),
        "source_labels": (
            "IIBC 官方 TOEIC 讀寫測驗形式說明",
            "ETS 官方 TOEIC 讀寫官方範例試題(PDF)",
            "ETS 官方 TOEIC 讀寫測驗簡介",
        ),
        "heuristic_title": "這個規劃器的分配邏輯",
        "heuristic_intro": (
            "這個時間分配是本站建立的簡單、可調整參考公式,不是 ETS 的建議,也不會"
            "預測分數。"
        ),
        "heuristic_list": (
            "均衡:聽力 35%、閱讀 35%、複習 20%、計時練習 10%。",
            "偏重聽力:聽力 50%、閱讀 25%、複習 15%、計時練習 10%。",
            "偏重閱讀:聽力 25%、閱讀 50%、複習 15%、計時練習 10%。",
            "如果還沒準備好計時練習,這部分時間會改分配到複習。",
            "分鐘數採最大餘數法分配,確保四個項目加總一定會精確等於你規劃的總分鐘"
            "數。",
        ),
        "trademark_notice": (
            "TOEIC 是 ETS 的商標。Aim990 是獨立的學習輔助工具,與 ETS 沒有合作或背"
            "書關係。沒有任何 App 或計畫能保證 TOEIC 分數。"
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽(規格可能異動)",
        "webmcp_description": (
            "只用有範圍限制、非敏感的數字與選項,建立透明的 TOEIC 學習時間分配。不"
            "會接收答案、錄音、文件、姓名、聯絡方式、帳號或確切考試日期,也不會產生"
            "分數預測、能力等級、及格與否結果,或與 ETS 合作的宣稱。"
        ),
        "app_title": "想要有指引的 TOEIC 教練 App 嗎?",
        "app_text": (
            "Aim990 是選用的。依目前 App Store 頁面說明,它是可免費下載、內含應用"
            "程式內購買的 App,提供 30 天 TOEIC 讀寫教練流程、8 分鐘程度診斷、每日聽"
            "力/閱讀/文法/單字與模擬測驗任務,並提供進度與弱點追蹤;Apple 隱私標籤標"
            "示不會收集資料。功能與價格可能變動,購買前請先確認目前頁面內容。本規劃"
            "器完全不需要這個 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Aim990",
        "faq_title": "TOEIC 學習時間分配常見問題",
        "faq": (
            (
                "這個頁面會收到我的答案、錄音或文件嗎?",
                "不會。它只接受有範圍限制的數字、偏重選項與計時練習準備開關。",
            ),
            (
                "這會預測我的 TOEIC 分數嗎?",
                "不會。它只是分配你自己的時間,不會估算、評分或預測任何分數或及格"
                "結果。",
            ),
            (
                "Aim990 與 ETS 或 TOEIC 官方有合作關係嗎?",
                "沒有。TOEIC 是 ETS 的商標。Aim990 是獨立的學習輔助工具,與 ETS "
                "沒有合作或背書關係。",
            ),
            (
                "分配比例是怎麼來的?",
                "這是本站自行建立、可調整的規劃參考,不是 ETS 或 IIBC 的官方建議。",
            ),
            (
                "如果我還沒準備好計時練習呢?",
                "把準備開關關掉,原本分配給計時練習的時間就會改到複習,總時間不"
                "變。",
            ),
        ),
        "footer": "只有私人有範圍限制數字・不含文件・不預測分數・與 ETS 無關",
        "index_title": "私人 TOEIC 讀寫學習時間分配規劃器",
        "index_description": (
            "只用有範圍限制的學習數字,透明算出聽力、閱讀、複習與計時練習的時間分"
            "配,免帳號、不預測分數。"
        ),
        "inline_link_label": "免費 TOEIC 學習時間分配規劃器(不預測分數)",
    },
    "zh-Hans": {
        "title": "私人 TOEIC 听读学习时间分配规划器 | 不预测分数",
        "description": (
            "只需输入可用天数、每周学习天数、每天学习分钟数与侧重方向,就能透明算"
            "出听力、阅读、复习与计时练习的学习时间分配。免账号、不预测分数、与 "
            "ETS 无关。"
        ),
        "tools": "免费工具",
        "switch": "English",
        "eyebrow": "免费・免账号・不预测分数",
        "heading": "私人 TOEIC 听读学习时间分配规划器",
        "lead": (
            "只用几个有范围限制的数字,就能透明算出听力、阅读、复习与计时练习之间"
            "的学习时间分配。这只是本站建立的规划参考,不是分数预测、能力诊断,也不"
            "是 ETS 的建议。"
        ),
        "badges": (
            "不收集答案、录音或文件",
            "不收集姓名、邮箱、账号或确切考试日期",
            "不预测分数、等级或及格与否",
            "与 ETS 无合作或背书关系",
        ),
        "planner": "创建你的私人学习时间分配",
        "planner_intro": (
            "只需输入范围内的数字与简短选项。本页不会要求测试答案、录音、文件或"
            "个人信息。"
        ),
        "days_label": "距目标日期的可用天数(1–30)",
        "days_per_week_label": "每周能安排的学习天数(1–7)",
        "minutes_label": "每个学习日能投入的分钟数(10–120)",
        "emphasis_label": "你想要哪种分配侧重?",
        "emphasis_options": {
            "balanced": "听力与阅读均衡",
            "listening": "侧重听力",
            "reading": "侧重阅读",
        },
        "timed_label": "我已准备好加入计时练习",
        "update": "更新私人规划",
        "invalid_input": "请输入上方标示的支持范围内数值。",
        "result_sessions": "规划的学习次数",
        "result_total": "规划的总分钟数",
        "result_listening": "听力分钟数",
        "result_reading": "阅读分钟数",
        "result_review": "复习分钟数",
        "result_timed": "计时练习分钟数",
        "result_plan_label": "接下来的步骤",
        "next_steps": (
            "确认你自己的可用天数、每周学习天数与每天学习分钟数;本页面不会收到你"
            "确切的考试日期。",
            "选择侧重方向(均衡、侧重听力或侧重阅读),以及是否已准备好计时练习。",
            "把这个时间分配当作可调整的起点,再依据自己的薄弱环节自行调整。",
            "正式 TOEIC 考试形式固定且全程英语,规划前请先查阅 IIBC 官方形式说明与 "
            "ETS 官方样题。",
            "不要死板地照搬这个分配,每隔几天就重新检视并调整。",
        ),
        "boundary_title": "这个规划器不会做的事",
        "boundary_text": (
            "这个规划器不会预测你的 TOEIC 分数、为你的能力打分或诊断、保证分数提"
            "升,也不会暗示与 ETS 有任何合作或背书关系。它只是用你自己输入的有范围"
            "限制数字,按固定且透明的公式转换成可调整的时间分配。"
        ),
        "sources_title": "TOEIC 听读测验官方形式事实与资料来源",
        "sources_intro": (
            "以下事实来自 IIBC 与 ETS 的官方页面,不是本站的说法。无论是这个规划器"
            "还是任何学习计划,都应对照这些事实来核对。"
        ),
        "official_facts": (
            "TOEIC 听力与阅读测验共 200 题,在两小时内完成。",
            "听力:约 45 分钟,共 100 题。",
            "阅读:75 分钟,共 100 题。",
            "测验本身只用英语进行,且每次考试形式相同。",
        ),
        "source_labels": (
            "IIBC 官方 TOEIC 听读测验形式说明",
            "ETS 官方 TOEIC 听读官方样题(PDF)",
            "ETS 官方 TOEIC 听读测验简介",
        ),
        "heuristic_title": "这个规划器的分配逻辑",
        "heuristic_intro": (
            "这个时间分配是本站建立的简单、可调整参考公式,不是 ETS 的建议,也不会"
            "预测分数。"
        ),
        "heuristic_list": (
            "均衡:听力 35%、阅读 35%、复习 20%、计时练习 10%。",
            "侧重听力:听力 50%、阅读 25%、复习 15%、计时练习 10%。",
            "侧重阅读:听力 25%、阅读 50%、复习 15%、计时练习 10%。",
            "如果还没准备好计时练习,这部分时间会改分配到复习。",
            "分钟数采用最大余数法分配,确保四个项目加总始终精确等于你规划的总分钟"
            "数。",
        ),
        "trademark_notice": (
            "TOEIC 是 ETS 的商标。Aim990 是独立的学习辅助工具,与 ETS 没有合作或背"
            "书关系。没有任何 App 或计划能保证 TOEIC 分数。"
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览(规格可能变更)",
        "webmcp_description": (
            "只用有范围限制、非敏感的数字与选项,创建透明的 TOEIC 学习时间分配。不"
            "会接收答案、录音、文件、姓名、联系方式、账号或确切考试日期,也不会产生"
            "分数预测、能力等级、及格与否结果,或与 ETS 合作的宣称。"
        ),
        "app_title": "想要有指引的 TOEIC 教练 App 吗?",
        "app_text": (
            "Aim990 是可选的。根据目前 App Store 页面说明,它可免费下载、内含应用"
            "内购买,提供 30 天 TOEIC 听读教练流程、8 分钟水平诊断、每日听力/阅读/"
            "语法/词汇与模拟测验任务,并提供进度与薄弱环节追踪;Apple 隐私标签标示"
            "不会收集数据。功能与价格可能变动,购买前请先确认当前页面内容。本规划器"
            "完全不需要这个 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Aim990",
        "faq_title": "TOEIC 学习时间分配常见问题",
        "faq": (
            (
                "这个页面会收到我的答案、录音或文件吗?",
                "不会。它只接受有范围限制的数字、侧重选项与计时练习准备开关。",
            ),
            (
                "这会预测我的 TOEIC 分数吗?",
                "不会。它只是分配你自己的时间,不会估算、评分或预测任何分数或及格"
                "结果。",
            ),
            (
                "Aim990 与 ETS 或 TOEIC 官方有合作关系吗?",
                "没有。TOEIC 是 ETS 的商标。Aim990 是独立的学习辅助工具,与 ETS "
                "没有合作或背书关系。",
            ),
            (
                "分配比例是怎么来的?",
                "这是本站自行建立、可调整的规划参考,不是 ETS 或 IIBC 的官方建"
                "议。",
            ),
            (
                "如果我还没准备好计时练习呢?",
                "把准备开关关闭,原本分配给计时练习的时间就会改到复习,总时间不"
                "变。",
            ),
        ),
        "footer": "仅私人有范围限制数字・不含文件・不预测分数・与 ETS 无关",
        "index_title": "私人 TOEIC 听读学习时间分配规划器",
        "index_description": (
            "只用有范围限制的学习数字,透明算出听力、阅读、复习与计时练习的时间分"
            "配,免账号、不预测分数。"
        ),
        "inline_link_label": "免费 TOEIC 学习时间分配规划器(不预测分数)",
    },
    "vi": {
        "title": "Công cụ phân bổ thời gian học TOEIC riêng tư | Không dự đoán điểm",
        "description": "Biến số ngày còn lại, số ngày học mỗi tuần, số phút mỗi ngày và trọng tâm học thành kế hoạch phút nghe/đọc/ôn tập/luyện tính giờ minh bạch — không tài khoản, không dự đoán điểm, không liên kết ETS.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Miễn phí · không tài khoản · không dự đoán điểm",
        "heading": "Công cụ phân bổ thời gian học TOEIC riêng tư",
        "lead": "Biến vài con số có giới hạn thành bảng chia phút học minh bạch cho nghe, đọc, ôn tập và luyện tính giờ. Đây là công thức lập kế hoạch của trang này, không phải dự đoán điểm, chẩn đoán hay khuyến nghị của ETS.",
        "badges": ("Không nhận đáp án, ghi âm hay tài liệu", "Không tên, email, tài khoản hay ngày thi chính xác", "Không dự đoán điểm, xếp loại hay đậu/rớt", "Không liên kết với hay được ETS chứng thực"),
        "planner": "Xây bảng phân bổ học tập riêng tư của bạn",
        "planner_intro": "Chỉ nhập các con số có giới hạn và lựa chọn ngắn bên dưới. Trang này không bao giờ hỏi đáp án, ghi âm, tài liệu hay chi tiết cá nhân.",
        "days_label": "Số ngày còn lại trước ngày mục tiêu (1–30)",
        "days_per_week_label": "Số ngày học mỗi tuần bạn cam kết được (1–7)",
        "minutes_label": "Số phút học được mỗi ngày học (10–120)",
        "emphasis_label": "Bạn muốn cân bằng thế nào?",
        "emphasis_options": {"balanced": "Cân bằng nghe & đọc", "listening": "Thiên về nghe", "reading": "Thiên về đọc"},
        "timed_label": "Tôi sẵn sàng luyện đề tính giờ",
        "update": "Cập nhật kế hoạch riêng tư",
        "invalid_input": "Nhập giá trị trong phạm vi hỗ trợ ở trên.",
        "result_sessions": "Số buổi học dự kiến",
        "result_total": "Tổng số phút dự kiến",
        "result_listening": "Phút nghe",
        "result_reading": "Phút đọc",
        "result_review": "Phút ôn tập",
        "result_timed": "Phút luyện tính giờ",
        "result_plan_label": "Bước tiếp theo",
        "next_steps": (
            "Tự xác nhận số ngày còn lại, số ngày học mỗi tuần và số phút mỗi ngày; trang này không bao giờ biết ngày thi chính xác của bạn.",
            "Chọn hướng cân bằng (cân bằng, nghe hay đọc) và bạn đã sẵn sàng luyện tính giờ chưa.",
            "Chỉ dùng bảng chia phút làm điểm khởi đầu có thể chỉnh, rồi điều chỉnh theo điểm yếu của chính bạn.",
            "Xem định dạng chính thức của IIBC và đề mẫu ETS trước khi lập kế hoạch sâu hơn, vì đề thi thật có định dạng cố định và toàn tiếng Anh.",
            "Vài ngày lặp lại và điều chỉnh một lần thay vì bám cứng nhắc.",
        ),
        "boundary_title": "Điều công cụ này không làm",
        "boundary_text": "Công cụ này không dự đoán điểm TOEIC, không chấm mức sẵn sàng, không chẩn đoán năng lực, không bảo đảm tiến bộ, và không ngụ ý liên kết hay chứng thực từ ETS. Nó chỉ biến các con số có giới hạn của bạn thành bảng chia phút có thể chỉnh, theo một công thức cố định được ghi rõ.",
        "sources_title": "Thông tin định dạng TOEIC L&R chính thức",
        "sources_intro": "Các dữ kiện này lấy từ trang chính thức của IIBC và ETS, không phải từ trang này. Dùng chúng để kiểm chứng mọi kế hoạch học, kể cả kế hoạch này.",
        "official_facts": (
            "Bài thi TOEIC Listening & Reading gồm 200 câu hoàn thành trong hai giờ.",
            "Nghe: khoảng 45 phút cho 100 câu.",
            "Đọc: 75 phút cho 100 câu.",
            "Đề thi chỉ trình bày bằng tiếng Anh và định dạng giống nhau ở mọi kỳ thi.",
        ),
        "source_labels": ("Định dạng TOEIC L&R chính thức của IIBC", "Đề mẫu TOEIC L&R chính thức của ETS (PDF)", "Tổng quan chương trình TOEIC L&R chính thức của ETS"),
        "heuristic_title": "Công thức phân bổ của công cụ này hoạt động ra sao",
        "heuristic_intro": "Bảng chia này là công thức đơn giản, có thể chỉnh, do trang này tạo. Không phải khuyến nghị của ETS và không dự đoán điểm.",
        "heuristic_list": (
            "Cân bằng: 35% nghe, 35% đọc, 20% ôn tập, 10% luyện tính giờ.",
            "Thiên nghe: 50% nghe, 25% đọc, 15% ôn tập, 10% luyện tính giờ.",
            "Thiên đọc: 25% nghe, 50% đọc, 15% ôn tập, 10% luyện tính giờ.",
            "Nếu chưa sẵn sàng luyện tính giờ, phần đó chuyển sang ôn tập.",
            "Phút được chia theo phương pháp phần dư lớn nhất nên bốn phần luôn cộng đúng bằng tổng số phút.",
        ),
        "trademark_notice": "TOEIC là thương hiệu của ETS. Aim990 là công cụ hỗ trợ học độc lập, không liên kết với hay được ETS chứng thực. Không ứng dụng hay kế hoạch nào bảo đảm được điểm TOEIC.",
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP (có thể thay đổi)",
        "webmcp_description": "Xây bảng phân bổ phút học TOEIC minh bạch từ các con số và lựa chọn không nhạy cảm, có giới hạn. Không bao giờ nhận đáp án, ghi âm, tài liệu, tên, liên lạc, tài khoản hay ngày thi chính xác; không tạo dự đoán điểm, xếp loại sẵn sàng, kết quả đậu/rớt hay tuyên bố liên kết ETS.",
        "app_title": "Muốn một huấn luyện viên TOEIC có hướng dẫn (tùy chọn)?",
        "app_text": "Aim990 là tùy chọn. Trang App Store hiện tại mô tả tải miễn phí kèm mua trong ứng dụng, lộ trình TOEIC Listening & Reading 30 ngày, bài chẩn đoán trình độ 8 phút, nhiệm vụ nghe/đọc/ngữ pháp/từ vựng và thi thử hằng ngày, theo dõi tiến bộ và điểm yếu; nhãn quyền riêng tư của Apple ghi không thu thập dữ liệu. Kiểm tra trang hiện tại trước khi mua vì tính năng và giá có thể thay đổi. Công cụ này hoạt động đầy đủ không cần ứng dụng.",
        "app_cta": "Xem Aim990 trên App Store",
        "faq_title": "Câu hỏi về phân bổ thời gian học TOEIC",
        "faq": (
            ("Trang này có nhận đáp án, ghi âm hay tài liệu của tôi không?", "Không. Nó chỉ nhận các con số có giới hạn, một lựa chọn cân bằng và một nút sẵn sàng."),
            ("Cái này có dự đoán điểm TOEIC của tôi không?", "Không. Nó chỉ chia số phút của bạn thành kế hoạch; không bao giờ ước lượng, chấm hay dự đoán điểm hoặc đậu/rớt."),
            ("Aim990 có liên kết với ETS hay chương trình TOEIC không?", "Không. TOEIC là thương hiệu của ETS. Aim990 là công cụ hỗ trợ học độc lập, không liên kết với hay được ETS chứng thực."),
            ("Tỷ lệ phân bổ lấy từ đâu?", "Đó là công thức lập kế hoạch có thể chỉnh của riêng trang này, không phải khuyến nghị chính thức của ETS hay IIBC."),
            ("Nếu tôi chưa sẵn sàng luyện tính giờ thì sao?", "Tắt nút sẵn sàng và số phút đó chuyển sang ôn tập, tổng số phút không đổi."),
        ),
        "footer": "Chỉ nhận số có giới hạn riêng tư · không tài liệu · không dự đoán điểm · không liên kết ETS",
        "index_title": "Công cụ phân bổ thời gian học TOEIC riêng tư",
        "index_description": "Biến các con số học tập có giới hạn thành bảng chia phút nghe/đọc/ôn tập/luyện tính giờ minh bạch, không tài khoản, không dự đoán điểm.",
        "inline_link_label": "Công cụ phân bổ thời gian học TOEIC miễn phí (không dự đoán điểm)",
    },
    "th": {
        "title": "เครื่องมือจัดสรรเวลาอ่าน TOEIC แบบส่วนตัว | ไม่ทำนายคะแนน",
        "description": "เปลี่ยนจำนวนวันที่เหลือ วันอ่านต่อสัปดาห์ นาทีต่อวัน และจุดเน้น เป็นแผนนาทีฟัง/อ่าน/ทบทวน/ฝึกจับเวลาแบบโปร่งใส — ไม่มีบัญชี ไม่ทำนายคะแนน ไม่เกี่ยวข้องกับ ETS",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "ฟรี · ไม่มีบัญชี · ไม่ทำนายคะแนน",
        "heading": "เครื่องมือจัดสรรเวลาอ่าน TOEIC แบบส่วนตัว",
        "lead": "เปลี่ยนตัวเลขไม่กี่ตัวเป็นการแบ่งนาทีอ่านหนังสือแบบโปร่งใสสำหรับการฟัง การอ่าน การทบทวน และการฝึกจับเวลา นี่คือสูตรวางแผนของเว็บนี้ ไม่ใช่การทำนายคะแนน การวินิจฉัย หรือคำแนะนำจาก ETS",
        "badges": ("ไม่รับคำตอบข้อสอบ ไฟล์เสียง หรือเอกสาร", "ไม่มีชื่อ อีเมล บัญชี หรือวันสอบจริง", "ไม่ทำนายคะแนน เกรด หรือผ่าน/ตก", "ไม่เกี่ยวข้องหรือได้รับการรับรองจาก ETS"),
        "planner": "สร้างแผนจัดสรรเวลาอ่านส่วนตัวของคุณ",
        "planner_intro": "กรอกเฉพาะตัวเลขแบบมีขอบเขตและตัวเลือกสั้น ๆ ด้านล่าง หน้านี้ไม่ถามคำตอบข้อสอบ ไฟล์เสียง เอกสาร หรือข้อมูลส่วนตัว",
        "days_label": "จำนวนวันก่อนถึงวันเป้าหมาย (1–30)",
        "days_per_week_label": "วันที่อ่านได้ต่อสัปดาห์ (1–7)",
        "minutes_label": "นาทีที่อ่านได้ในแต่ละวันอ่าน (10–120)",
        "emphasis_label": "อยากเน้นแบบไหน?",
        "emphasis_options": {"balanced": "สมดุลฟังและอ่าน", "listening": "เน้นการฟัง", "reading": "เน้นการอ่าน"},
        "timed_label": "พร้อมฝึกทำข้อสอบจับเวลาแล้ว",
        "update": "อัปเดตแผนส่วนตัว",
        "invalid_input": "กรอกค่าภายในช่วงที่รองรับด้านบน",
        "result_sessions": "จำนวนครั้งที่วางแผนอ่าน",
        "result_total": "นาทีรวมที่วางแผน",
        "result_listening": "นาทีการฟัง",
        "result_reading": "นาทีการอ่าน",
        "result_review": "นาทีทบทวน",
        "result_timed": "นาทีฝึกจับเวลา",
        "result_plan_label": "ขั้นตอนถัดไป",
        "next_steps": (
            "ยืนยันเองว่ามีกี่วัน อ่านได้กี่วันต่อสัปดาห์ วันละกี่นาที หน้านี้ไม่เห็นวันสอบจริงของคุณ",
            "เลือกจุดเน้น (สมดุล ฟัง หรืออ่าน) และพร้อมฝึกจับเวลาหรือยัง",
            "ใช้การแบ่งนาทีเป็นจุดเริ่มต้นที่แก้ได้ แล้วปรับตามจุดอ่อนของตัวเอง",
            "ดูรูปแบบทางการของ IIBC และข้อสอบตัวอย่าง ETS ก่อนวางแผนต่อ เพราะข้อสอบจริงมีรูปแบบตายตัวและเป็นภาษาอังกฤษล้วน",
            "ทุกสองสามวันให้ทบทวนและปรับการแบ่งใหม่ แทนที่จะยึดตายตัว",
        ),
        "boundary_title": "สิ่งที่เครื่องมือนี้ไม่ทำ",
        "boundary_text": "เครื่องมือนี้ไม่ทำนายคะแนน TOEIC ไม่ให้เกรดความพร้อม ไม่วินิจฉัยความสามารถ ไม่รับประกันพัฒนาการ และไม่สื่อว่ามีความเกี่ยวข้องหรือการรับรองจาก ETS มันแค่เปลี่ยนตัวเลขของคุณเป็นการแบ่งนาทีที่แก้ไขได้ ตามสูตรคงที่ที่เขียนไว้ชัดเจน",
        "sources_title": "ข้อเท็จจริงรูปแบบ TOEIC L&R อย่างเป็นทางการ",
        "sources_intro": "ข้อมูลเหล่านี้มาจากหน้าอย่างเป็นทางการของ IIBC และ ETS ไม่ใช่จากเว็บนี้ ใช้ตรวจสอบทุกแผนการอ่าน รวมถึงแผนนี้",
        "official_facts": (
            "ข้อสอบ TOEIC Listening & Reading มี 200 ข้อ ทำในสองชั่วโมง",
            "การฟัง: ประมาณ 45 นาที 100 ข้อ",
            "การอ่าน: 75 นาที 100 ข้อ",
            "ตัวข้อสอบเป็นภาษาอังกฤษล้วน และรูปแบบเหมือนกันทุกรอบสอบ",
        ),
        "source_labels": ("รูปแบบข้อสอบ TOEIC L&R ทางการของ IIBC", "ข้อสอบตัวอย่าง TOEIC L&R ทางการของ ETS (PDF)", "ภาพรวมโปรแกรม TOEIC L&R ทางการของ ETS"),
        "heuristic_title": "สูตรจัดสรรของเครื่องมือนี้ทำงานอย่างไร",
        "heuristic_intro": "การแบ่งนี้เป็นสูตรง่าย ๆ ที่แก้ไขได้ สร้างโดยเว็บนี้ ไม่ใช่คำแนะนำของ ETS และไม่ทำนายคะแนน",
        "heuristic_list": (
            "สมดุล: ฟัง 35% อ่าน 35% ทบทวน 20% ฝึกจับเวลา 10%",
            "เน้นฟัง: ฟัง 50% อ่าน 25% ทบทวน 15% ฝึกจับเวลา 10%",
            "เน้นอ่าน: ฟัง 25% อ่าน 50% ทบทวน 15% ฝึกจับเวลา 10%",
            "ถ้ายังไม่พร้อมฝึกจับเวลา ส่วนนั้นจะย้ายไปทบทวนแทน",
            "นาทีถูกแบ่งด้วยวิธีเศษมากที่สุด สี่ส่วนจึงรวมเท่ากับนาทีทั้งหมดเสมอ",
        ),
        "trademark_notice": "TOEIC เป็นเครื่องหมายการค้าของ ETS Aim990 เป็นเครื่องมือช่วยเรียนอิสระ ไม่เกี่ยวข้องหรือได้รับการรับรองจาก ETS ไม่มีแอปหรือแผนใดรับประกันคะแนน TOEIC ได้",
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP (อาจเปลี่ยนแปลง)",
        "webmcp_description": "สร้างการจัดสรรนาทีอ่าน TOEIC แบบโปร่งใสจากตัวเลขและตัวเลือกที่ไม่อ่อนไหวแบบมีขอบเขต ไม่รับคำตอบข้อสอบ ไฟล์เสียง เอกสาร ชื่อ ข้อมูลติดต่อ บัญชี หรือวันสอบจริง ไม่สร้างการทำนายคะแนน เกรดความพร้อม ผลผ่าน/ตก หรือคำกล่าวอ้างความเกี่ยวข้องกับ ETS",
        "app_title": "อยากได้โค้ช TOEIC แบบมีไกด์ (ตัวเลือกเสริม)?",
        "app_text": "Aim990 เป็นตัวเลือกเสริม หน้า App Store ปัจจุบันอธิบายการดาวน์โหลดฟรีพร้อมซื้อในแอป โค้ช TOEIC Listening & Reading 30 วัน แบบวัดระดับ 8 นาที ภารกิจฟัง/อ่าน/ไวยากรณ์/คำศัพท์และข้อสอบจำลองรายวัน พร้อมติดตามพัฒนาการและจุดอ่อน ป้ายความเป็นส่วนตัวของ Apple ระบุว่าไม่เก็บข้อมูล โปรดตรวจหน้าปัจจุบันก่อนซื้อ เพราะฟีเจอร์และราคาเปลี่ยนได้ เครื่องมือนี้ใช้ได้เต็มที่โดยไม่ต้องมีแอป",
        "app_cta": "ดู Aim990 บน App Store",
        "faq_title": "คำถามเรื่องการจัดสรรเวลาอ่าน TOEIC",
        "faq": (
            ("หน้านี้รับคำตอบข้อสอบ ไฟล์เสียง หรือเอกสารของฉันไหม?", "ไม่ มันรับเฉพาะตัวเลขแบบมีขอบเขต ตัวเลือกจุดเน้น และปุ่มความพร้อมเท่านั้น"),
            ("ทำนายคะแนน TOEIC ของฉันไหม?", "ไม่ มันแค่แบ่งนาทีของคุณเป็นแผน ไม่ประเมิน ไม่ให้เกรด ไม่ทำนายคะแนนหรือผ่าน/ตก"),
            ("Aim990 เกี่ยวข้องกับ ETS หรือโปรแกรม TOEIC ไหม?", "ไม่ TOEIC เป็นเครื่องหมายการค้าของ ETS Aim990 เป็นเครื่องมือช่วยเรียนอิสระ ไม่เกี่ยวข้องหรือได้รับการรับรองจาก ETS"),
            ("เปอร์เซ็นต์การจัดสรรมาจากไหน?", "เป็นสูตรวางแผนที่แก้ไขได้ของเว็บนี้เอง ไม่ใช่คำแนะนำทางการของ ETS หรือ IIBC"),
            ("ถ้ายังไม่พร้อมฝึกจับเวลาล่ะ?", "ปิดปุ่มความพร้อม แล้วนาทีส่วนนั้นจะย้ายไปทบทวนแทน นาทีรวมเท่าเดิม"),
        ),
        "footer": "เฉพาะตัวเลขส่วนตัวแบบมีขอบเขต · ไม่มีเอกสาร · ไม่ทำนายคะแนน · ไม่เกี่ยวข้องกับ ETS",
        "index_title": "เครื่องมือจัดสรรเวลาอ่าน TOEIC แบบส่วนตัว",
        "index_description": "เปลี่ยนตัวเลขการอ่านแบบมีขอบเขตเป็นการแบ่งนาทีฟัง/อ่าน/ทบทวน/ฝึกจับเวลาแบบโปร่งใส ไม่มีบัญชี ไม่ทำนายคะแนน",
        "inline_link_label": "เครื่องมือจัดสรรเวลาอ่าน TOEIC ฟรี (ไม่ทำนายคะแนน)",
    },
    "id": {
        "title": "Perencana Alokasi Belajar TOEIC Privat | Tanpa Prediksi Skor",
        "description": "Ubah hari tersisa, hari belajar per minggu, menit per hari, dan fokus belajar menjadi rencana menit mendengarkan/membaca/ulasan/latihan berwaktu yang transparan — tanpa akun, tanpa prediksi skor, tanpa afiliasi ETS.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Gratis · tanpa akun · tanpa prediksi skor",
        "heading": "Perencana alokasi belajar TOEIC privat",
        "lead": "Ubah beberapa angka terbatas menjadi pembagian menit belajar yang transparan untuk mendengarkan, membaca, ulasan, dan latihan berwaktu. Ini heuristik perencanaan buatan situs ini, bukan prediksi skor, diagnosis, atau rekomendasi ETS.",
        "badges": ("Tanpa jawaban tes, rekaman, atau dokumen", "Tanpa nama, email, akun, atau tanggal tes pasti", "Tanpa prediksi skor, nilai, atau lulus/gagal", "Tidak berafiliasi dengan atau didukung ETS"),
        "planner": "Bangun alokasi belajar privat Anda",
        "planner_intro": "Masukkan hanya angka terbatas dan pilihan singkat di bawah. Halaman ini tidak pernah meminta jawaban tes, rekaman, dokumen, atau detail pribadi.",
        "days_label": "Hari tersedia sebelum tanggal target (1–30)",
        "days_per_week_label": "Hari belajar yang bisa Anda komitmenkan per minggu (1–7)",
        "minutes_label": "Menit belajar tiap hari belajar (10–120)",
        "emphasis_label": "Keseimbangan mana yang Anda mau?",
        "emphasis_options": {"balanced": "Seimbang mendengarkan & membaca", "listening": "Tekankan mendengarkan", "reading": "Tekankan membaca"},
        "timed_label": "Saya siap memasukkan sesi latihan berwaktu",
        "update": "Perbarui rencana privat",
        "invalid_input": "Masukkan nilai dalam rentang yang didukung di atas.",
        "result_sessions": "Sesi belajar terencana",
        "result_total": "Total menit terencana",
        "result_listening": "Menit mendengarkan",
        "result_reading": "Menit membaca",
        "result_review": "Menit ulasan",
        "result_timed": "Menit latihan berwaktu",
        "result_plan_label": "Langkah berikutnya",
        "next_steps": (
            "Konfirmasi sendiri hari tersedia, hari belajar per minggu, dan menit per hari; halaman ini tidak pernah melihat tanggal tes pasti Anda.",
            "Pilih keseimbangan (seimbang, mendengarkan, atau membaca) dan apakah Anda siap latihan berwaktu.",
            "Gunakan pembagian menit hanya sebagai titik awal yang bisa diedit, lalu sesuaikan dengan titik lemah Anda.",
            "Tinjau format resmi IIBC dan tes contoh ETS sebelum merencanakan lebih jauh, karena tes asli berformat tetap dan sepenuhnya bahasa Inggris.",
            "Ulangi dan sesuaikan pembagian tiap beberapa hari alih-alih mengikutinya secara kaku.",
        ),
        "boundary_title": "Yang tidak dilakukan perencana ini",
        "boundary_text": "Perencana ini tidak memprediksi skor TOEIC, tidak menilai kesiapan, tidak mendiagnosis kemampuan, tidak menjamin peningkatan, dan tidak menyiratkan afiliasi atau dukungan ETS. Ia hanya mengubah angka terbatas Anda menjadi pembagian menit yang bisa diedit memakai heuristik tetap yang terdokumentasi.",
        "sources_title": "Fakta format TOEIC L&R resmi dan sumbernya",
        "sources_intro": "Fakta ini berasal dari halaman resmi IIBC dan ETS, bukan dari situs ini. Gunakan untuk memeriksa kewajaran rencana belajar mana pun, termasuk yang ini.",
        "official_facts": (
            "Tes TOEIC Listening & Reading berisi 200 soal yang diselesaikan dalam dua jam.",
            "Mendengarkan: sekitar 45 menit untuk 100 soal.",
            "Membaca: 75 menit untuk 100 soal.",
            "Tes disajikan hanya dalam bahasa Inggris, dan formatnya sama di setiap penyelenggaraan.",
        ),
        "source_labels": ("Format tes TOEIC L&R resmi IIBC", "Tes contoh TOEIC L&R resmi ETS (PDF)", "Ikhtisar program TOEIC L&R resmi ETS"),
        "heuristic_title": "Cara kerja heuristik alokasi perencana ini",
        "heuristic_intro": "Pembagian ini heuristik sederhana yang bisa diedit, dibuat situs ini. Bukan rekomendasi ETS dan tidak memprediksi skor.",
        "heuristic_list": (
            "Seimbang: 35% mendengarkan, 35% membaca, 20% ulasan, 10% latihan berwaktu.",
            "Tekanan mendengarkan: 50% mendengarkan, 25% membaca, 15% ulasan, 10% latihan berwaktu.",
            "Tekanan membaca: 25% mendengarkan, 50% membaca, 15% ulasan, 10% latihan berwaktu.",
            "Jika belum siap latihan berwaktu, porsinya berpindah ke ulasan.",
            "Menit dibagi dengan metode sisa-terbesar sehingga keempat bagian selalu berjumlah persis total menit Anda.",
        ),
        "trademark_notice": "TOEIC adalah merek dagang ETS. Aim990 adalah alat bantu belajar independen dan tidak berafiliasi dengan atau didukung ETS. Tidak ada aplikasi atau rencana yang dapat menjamin skor TOEIC.",
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP (dapat berubah)",
        "webmcp_description": "Bangun alokasi menit belajar TOEIC yang transparan dari hitungan dan pilihan terbatas yang tidak sensitif. Tidak pernah menerima jawaban tes, rekaman, dokumen, nama, kontak, akun, atau tanggal tes pasti; tidak pernah menghasilkan prediksi skor, nilai kesiapan, hasil lulus/gagal, atau klaim afiliasi ETS.",
        "app_title": "Ingin pelatih TOEIC terpandu (opsional)?",
        "app_text": "Aim990 bersifat opsional. Halaman App Store terbarunya menjelaskan unduhan gratis dengan pembelian dalam aplikasi, pelatih TOEIC Listening & Reading 30 hari, diagnostik level 8 menit, tugas harian mendengarkan/membaca/tata bahasa/kosakata dan tes simulasi, serta pelacakan kemajuan dan titik lemah; label privasi Apple menyatakan tidak ada data yang dikumpulkan. Periksa halaman terbaru sebelum membeli karena fitur dan harga bisa berubah. Perencana ini bekerja penuh tanpa aplikasi tersebut.",
        "app_cta": "Lihat Aim990 di App Store",
        "faq_title": "Pertanyaan alokasi belajar TOEIC",
        "faq": (
            ("Apakah halaman ini menerima jawaban tes, rekaman, atau dokumen saya?", "Tidak. Ia hanya menerima hitungan terbatas, pilihan keseimbangan, dan sakelar kesiapan."),
            ("Apakah ini memprediksi skor TOEIC saya?", "Tidak. Ia hanya membagi menit Anda menjadi rencana; tidak pernah memperkirakan, menilai, atau memprediksi skor atau lulus/gagal."),
            ("Apakah Aim990 berafiliasi dengan ETS atau program TOEIC?", "Tidak. TOEIC adalah merek dagang ETS. Aim990 adalah alat bantu belajar independen dan tidak berafiliasi dengan atau didukung ETS."),
            ("Dari mana persentase alokasi berasal?", "Itu heuristik perencanaan situs ini yang bisa diedit, bukan rekomendasi resmi ETS atau IIBC."),
            ("Bagaimana jika saya belum siap latihan berwaktu?", "Matikan sakelar kesiapan dan menitnya berpindah ke ulasan, sehingga total tetap sama."),
        ),
        "footer": "Hanya angka terbatas privat · tanpa dokumen · tanpa prediksi skor · tanpa afiliasi ETS",
        "index_title": "Perencana Alokasi Belajar TOEIC Privat",
        "index_description": "Ubah angka belajar terbatas menjadi pembagian menit mendengarkan/membaca/ulasan/latihan berwaktu yang transparan, tanpa akun dan tanpa prediksi skor.",
        "inline_link_label": "Perencana alokasi belajar TOEIC gratis (tanpa prediksi skor)",
    },
    "tr": {
        "title": "Gizli TOEIC Çalışma Dağılımı Planlayıcı | Puan Tahmini Yok",
        "description": "Kalan günleri, haftalık çalışma günlerini, günlük dakikaları ve çalışma vurgusunu şeffaf bir dinleme/okuma/tekrar/süreli-alıştırma dakika planına çevirin — hesap yok, puan tahmini yok, ETS bağlantısı yok.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Ücretsiz · hesap yok · puan tahmini yok",
        "heading": "Gizli TOEIC çalışma dağılımı planlayıcı",
        "lead": "Birkaç sınırlı sayıyı dinleme, okuma, tekrar ve süreli alıştırma için şeffaf bir dakika dağılımına çevirin. Bu, bu sitenin kurduğu bir planlama sezgiselidir; puan tahmini, teşhis veya ETS önerisi değildir.",
        "badges": ("Sınav yanıtı, kayıt veya belge yok", "Ad, e-posta, hesap veya kesin sınav tarihi yok", "Puan, not veya geçti/kaldı tahmini yok", "ETS ile bağlantılı veya onaylı değil"),
        "planner": "Gizli çalışma dağılımınızı kurun",
        "planner_intro": "Aşağıya yalnızca sınırlı sayılar ve kısa seçimler girin. Bu sayfa asla sınav yanıtı, kayıt, belge veya kişisel ayrıntı istemez.",
        "days_label": "Hedef tarihinize kadar kalan gün (1–30)",
        "days_per_week_label": "Haftada ayırabileceğiniz çalışma günü (1–7)",
        "minutes_label": "Her çalışma gününde çalışabileceğiniz dakika (10–120)",
        "emphasis_label": "Hangi dengeyi istiyorsunuz?",
        "emphasis_options": {"balanced": "Dengeli dinleme ve okuma", "listening": "Dinlemeye ağırlık ver", "reading": "Okumaya ağırlık ver"},
        "timed_label": "Süreli alıştırma oturumlarına hazırım",
        "update": "Gizli planı güncelle",
        "invalid_input": "Yukarıda gösterilen desteklenen aralıklarda değer girin.",
        "result_sessions": "Planlanan çalışma oturumları",
        "result_total": "Toplam planlanan dakika",
        "result_listening": "Dinleme dakikaları",
        "result_reading": "Okuma dakikaları",
        "result_review": "Tekrar dakikaları",
        "result_timed": "Süreli alıştırma dakikaları",
        "result_plan_label": "Sonraki adımlar",
        "next_steps": (
            "Kalan günleri, haftalık çalışma günlerini ve günlük dakikaları kendiniz doğrulayın; bu sayfa kesin sınav tarihinizi asla görmez.",
            "Bir denge (dengeli, dinleme veya okuma) ve süreli alıştırmaya hazır olup olmadığınızı seçin.",
            "Dakika dağılımını yalnızca düzenlenebilir bir başlangıç olarak kullanın, sonra kendi zayıf alanlarınıza göre ayarlayın.",
            "Daha fazla plan yapmadan önce resmî IIBC formatını ve ETS örnek testini inceleyin; gerçek sınav sabit formatlı ve yalnızca İngilizcedir.",
            "Dağılımı katı biçimde izlemek yerine birkaç günde bir tekrarlayıp ayarlayın.",
        ),
        "boundary_title": "Bu planlayıcının yapmadıkları",
        "boundary_text": "Bu planlayıcı TOEIC puanı tahmin etmez, hazırlığınızı notlamaz, yetenek teşhisi koymaz, gelişme garantisi vermez ve herhangi bir ETS bağlantısı veya onayı ima etmez. Yalnızca kendi sınırlı sayılarınızı, sabit ve belgelenmiş bir sezgiselle düzenlenebilir bir dakika dağılımına çevirir.",
        "sources_title": "Resmî TOEIC L&R format bilgileri ve kaynaklar",
        "sources_intro": "Bu bilgiler bu siteden değil, IIBC ve ETS resmî sayfalarından gelir. Bu plan dahil her çalışma planını doğrulamak için kullanın.",
        "official_facts": (
            "TOEIC Listening & Reading testi iki saatte tamamlanan 200 sorudan oluşur.",
            "Dinleme: 100 soru için yaklaşık 45 dakika.",
            "Okuma: 100 soru için 75 dakika.",
            "Test yalnızca İngilizce sunulur ve format her oturumda aynıdır.",
        ),
        "source_labels": ("IIBC resmî TOEIC L&R test formatı", "ETS resmî TOEIC L&R örnek testi (PDF)", "ETS resmî TOEIC L&R program özeti"),
        "heuristic_title": "Bu planlayıcının dağılım sezgiseli nasıl çalışır",
        "heuristic_intro": "Bu dağılım, bu sitenin oluşturduğu basit ve düzenlenebilir bir sezgiseldir. ETS önerisi değildir ve puan tahmin etmez.",
        "heuristic_list": (
            "Dengeli: %35 dinleme, %35 okuma, %20 tekrar, %10 süreli alıştırma.",
            "Dinleme ağırlıklı: %50 dinleme, %25 okuma, %15 tekrar, %10 süreli alıştırma.",
            "Okuma ağırlıklı: %25 dinleme, %50 okuma, %15 tekrar, %10 süreli alıştırma.",
            "Süreli alıştırmaya hazır değilseniz payı tekrara aktarılır.",
            "Dakikalar en-büyük-kalan yöntemiyle paylaştırılır; dört bölüm her zaman toplam dakikanıza tam eşittir.",
        ),
        "trademark_notice": "TOEIC, ETS'nin ticari markasıdır. Aim990 bağımsız bir çalışma yardımcısıdır; ETS ile bağlantılı veya onaylı değildir. Hiçbir uygulama veya plan TOEIC puanı garanti edemez.",
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi (değişebilir)",
        "webmcp_description": "Sınırlı, hassas olmayan sayı ve seçimlerden şeffaf bir TOEIC çalışma-dakikası dağılımı kurar. Sınav yanıtı, kayıt, belge, ad, iletişim, hesap veya kesin sınav tarihi asla almaz; puan tahmini, hazırlık notu, geçti/kaldı sonucu veya ETS bağlantısı iddiası üretmez.",
        "app_title": "İsteğe bağlı rehberli bir TOEIC koçu ister misiniz?",
        "app_text": "Aim990 isteğe bağlıdır. Güncel App Store sayfası; uygulama içi satın almalı ücretsiz indirmeyi, 30 günlük TOEIC Listening & Reading koçunu, 8 dakikalık seviye tanılamayı, günlük dinleme/okuma/dil bilgisi/kelime ve deneme sınavı görevlerini, ilerleme ve zayıf alan takibini anlatır; Apple gizlilik etiketi veri toplanmadığını belirtir. Özellikler ve fiyat değişebileceği için satın almadan önce güncel sayfayı doğrulayın. Bu planlayıcı uygulama olmadan da tam çalışır.",
        "app_cta": "App Store'da Aim990'ı görüntüle",
        "faq_title": "TOEIC çalışma dağılımı soruları",
        "faq": (
            ("Bu sayfa sınav yanıtlarımı, kayıtlarımı veya belgelerimi alıyor mu?", "Hayır. Yalnızca sınırlı sayıları, bir denge seçimini ve bir hazırlık anahtarını kabul eder."),
            ("Bu, TOEIC puanımı tahmin eder mi?", "Hayır. Yalnızca kendi dakikalarınızı bir plana böler; asla puan veya geçti/kaldı sonucu kestirmez, notlamaz, tahmin etmez."),
            ("Aim990, ETS veya TOEIC programıyla bağlantılı mı?", "Hayır. TOEIC, ETS'nin ticari markasıdır. Aim990 bağımsız bir çalışma yardımcısıdır; ETS ile bağlantılı veya onaylı değildir."),
            ("Dağılım yüzdeleri nereden geliyor?", "Bu sitenin kendi düzenlenebilir planlama sezgiselidir; resmî bir ETS veya IIBC önerisi değildir."),
            ("Süreli alıştırmaya hazır değilsem ne olur?", "Hazırlık anahtarını kapatın; planlanan dakikaları tekrara geçer, böylece toplamınız aynı kalır."),
        ),
        "footer": "Yalnızca gizli sınırlı sayılar · belge yok · puan tahmini yok · ETS bağlantısı yok",
        "index_title": "Gizli TOEIC Çalışma Dağılımı Planlayıcı",
        "index_description": "Sınırlı çalışma sayılarını hesapsız ve puan tahmini olmadan şeffaf bir dinleme/okuma/tekrar/süreli-alıştırma dakika dağılımına çevirin.",
        "inline_link_label": "Ücretsiz TOEIC çalışma dağılımı planlayıcı (puan tahmini yok)",
    },
}


STYLE = r"""
:root{--ink:#21314a;--muted:#67738a;--line:#dfe5f0;--paper:#fff;--bg:#f3f6fb;--deep:#3949a3;--violet:#7566c8;--soft:#edf0ff;--warn:#fff6d8;--shadow:0 22px 60px rgba(47,57,108,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e9edf7 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--deep)}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cad2e4;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #d7dcfa;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#5360a8;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#3b467a;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#f4f5ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("toeic-study-config").textContent);
  const form = document.getElementById("toeic-study-planner");
  const fields = {
    days_available: document.getElementById("days-available"),
    study_days_per_week: document.getElementById("study-days-per-week"),
    minutes_per_study_day: document.getElementById("minutes-per-study-day"),
    emphasis: document.getElementById("emphasis"),
    timed_practice_ready: document.getElementById("timed-ready")
  };
  const output = {
    sessions: document.getElementById("result-sessions"),
    total: document.getElementById("result-total"),
    listening: document.getElementById("result-listening"),
    reading: document.getElementById("result-reading"),
    review: document.getElementById("result-review"),
    timed: document.getElementById("result-timed"),
    plan: document.getElementById("result-plan")
  };

  const WEIGHTS = {
    balanced: {listening: 35, reading: 35, review: 20, timed: 10},
    listening: {listening: 50, reading: 25, review: 15, timed: 10},
    reading: {listening: 25, reading: 50, review: 15, timed: 10}
  };

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

  function booleanValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    if (typeof input[name] !== "boolean") {
      throw new TypeError(`${name} must be a boolean.`);
    }
    return input[name];
  }

  function largestRemainderAllocate(total, weights) {
    const keys = Object.keys(weights);
    const weightSum = keys.reduce((sum, key) => sum + weights[key], 0);
    const raw = keys.map((key) => (total * weights[key]) / weightSum);
    const floors = raw.map(Math.floor);
    let allocated = floors.reduce((sum, value) => sum + value, 0);
    let remaining = total - allocated;
    const remainders = keys
      .map((key, index) => ({key, index, remainder: raw[index] - floors[index]}))
      .sort((a, b) => (b.remainder - a.remainder) || (a.index - b.index));
    const result = {};
    keys.forEach((key, index) => { result[key] = floors[index]; });
    for (let i = 0; i < remainders.length && remaining > 0; i += 1) {
      result[remainders[i].key] += 1;
      remaining -= 1;
    }
    return result;
  }

  function plan(input) {
    const daysAvailable = integerValue(input, "days_available");
    const studyDaysPerWeek = integerValue(input, "study_days_per_week");
    const minutesPerStudyDay = integerValue(input, "minutes_per_study_day");
    const emphasis = enumValue(input, "emphasis");
    const timedPracticeReady = booleanValue(input, "timed_practice_ready");

    const rawSessions = Math.round(
      (daysAvailable * studyDaysPerWeek) / 7);
    const plannedSessions = Math.min(
      daysAvailable, Math.max(1, rawSessions));
    const totalPlannedMinutes = plannedSessions * minutesPerStudyDay;

    const baseWeights = WEIGHTS[emphasis];
    const weights = timedPracticeReady ?
      {...baseWeights} :
      {
        listening: baseWeights.listening,
        reading: baseWeights.reading,
        review: baseWeights.review + baseWeights.timed,
        timed: 0
      };
    const minutes = weights.timed === 0 ?
      {...largestRemainderAllocate(totalPlannedMinutes, {
        listening: weights.listening,
        reading: weights.reading,
        review: weights.review
      }), timed: 0} :
      largestRemainderAllocate(totalPlannedMinutes, weights);

    return {
      selected_inputs: {
        days_available: daysAvailable,
        study_days_per_week: studyDaysPerWeek,
        minutes_per_study_day: minutesPerStudyDay,
        emphasis,
        emphasis_label: config.labels.emphasis[emphasis],
        timed_practice_ready: timedPracticeReady
      },
      session_math: {
        formula:
          "planned_sessions = clamp(round(days_available * " +
          "study_days_per_week / 7), 1, days_available)",
        planned_sessions: plannedSessions,
        total_planned_minutes: totalPlannedMinutes,
        is_duration_prediction: false
      },
      study_allocation_heuristic: {
        listening_minutes: minutes.listening,
        reading_minutes: minutes.reading,
        review_minutes: minutes.review,
        timed_practice_minutes: minutes.timed,
        minutes_sum_matches_total:
          minutes.listening + minutes.reading + minutes.review +
            minutes.timed === totalPlannedMinutes,
        heuristic_is_editable_and_created_by_this_site: true,
        is_not_an_ets_recommendation: true,
        no_score_grade_or_pass_fail_prediction: true
      },
      next_steps: config.nextSteps,
      boundary: config.boundary,
      official_format_facts: config.officialFormatFacts
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
    return plan(input);
  }

  function humanInteger(field, name) {
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
    output.sessions.textContent = "—";
    output.total.textContent = "—";
    output.listening.textContent = "—";
    output.reading.textContent = "—";
    output.review.textContent = "—";
    output.timed.textContent = "—";
    output.plan.textContent = message;
  }

  function render() {
    let result;
    try {
      result = plan({
        days_available: humanInteger(
          fields.days_available, "days_available"),
        study_days_per_week: humanInteger(
          fields.study_days_per_week, "study_days_per_week"),
        minutes_per_study_day: humanInteger(
          fields.minutes_per_study_day, "minutes_per_study_day"),
        emphasis: fields.emphasis.value,
        timed_practice_ready: fields.timed_practice_ready.checked
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        renderInvalid(config.invalidInput);
        return;
      }
      throw error;
    }
    const heuristic = result.study_allocation_heuristic;
    output.sessions.textContent =
      String(result.session_math.planned_sessions);
    output.total.textContent =
      String(result.session_math.total_planned_minutes);
    output.listening.textContent = String(heuristic.listening_minutes);
    output.reading.textContent = String(heuristic.reading_minutes);
    output.review.textContent = String(heuristic.review_minutes);
    output.timed.textContent = String(heuristic.timed_practice_minutes);
    output.plan.textContent = result.next_steps.join(" ");
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_toeic_study_allocation",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_toeic_study_allocation_plan",
          test_answers_recordings_documents_or_accounts_not_received: true,
          no_score_prediction_readiness_grade_or_ets_affiliation_claim: true,
          plan,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_aim990 = config.optionalApp;
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
            "days_available": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
                "description": t["days_label"],
            },
            "study_days_per_week": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": t["days_per_week_label"],
            },
            "minutes_per_study_day": {
                "type": "integer",
                "minimum": 10,
                "maximum": 120,
                "description": t["minutes_label"],
            },
            "emphasis": {
                "type": "string",
                "enum": list(EMPHASIS_CHOICES),
                "description": t["emphasis_label"],
            },
            "timed_practice_ready": {
                "type": "boolean",
                "description": t["timed_label"],
            },
        },
        "required": [
            "days_available",
            "study_days_per_week",
            "minutes_per_study_day",
            "emphasis",
            "timed_practice_ready",
        ],
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
    sources = (IIBC_FORMAT, ETS_SAMPLE_PDF, ETS_ABOUT)
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    facts_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["official_facts"]
    )
    heuristic_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["heuristic_list"]
    )
    checklist_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["next_steps"]
    )
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_toeic_allocation_{locale.lower()}")
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
    official_format_facts = {
        "total_questions": 200,
        "total_test_minutes": 120,
        "listening_minutes": 45,
        "listening_questions": 100,
        "reading_minutes": 75,
        "reading_questions": 100,
        "test_language": "English only",
        "format_is_the_same_each_administration": True,
        "source": IIBC_FORMAT,
    }
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "labels": {
            "emphasis": t["emphasis_options"],
        },
        "nextSteps": t["next_steps"],
        "boundary": t["boundary_text"],
        "invalidInput": t["invalid_input"],
        "toolDescription": t["webmcp_description"],
        "officialFormatFacts": official_format_facts,
        "freePlanner": {
            "label": t["heading"],
            "url": url,
            "boundary": t["planner_intro"],
        },
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(t["source_labels"], sources, strict=True)
        ],
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
        "description": t["lead"],
        "step": [
            {
                "@type": "HowToStep",
                "position": index + 1,
                "text": step,
            }
            for index, step in enumerate(t["next_steps"])
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
<form id="toeic-study-planner"><div class="controls">
<div class="field"><label for="days-available">{html.escape(t["days_label"])}</label><input id="days-available" type="number" min="1" max="30" step="1" value="14" required></div>
<div class="field"><label for="study-days-per-week">{html.escape(t["days_per_week_label"])}</label><input id="study-days-per-week" type="number" min="1" max="7" step="1" value="5" required></div>
<div class="field"><label for="minutes-per-study-day">{html.escape(t["minutes_label"])}</label><input id="minutes-per-study-day" type="number" min="10" max="120" step="1" value="30" required></div>
<div class="field"><label for="emphasis">{html.escape(t["emphasis_label"])}</label><select id="emphasis">{options(t["emphasis_options"])}</select></div>
<label class="toggle"><input id="timed-ready" type="checkbox">{html.escape(t["timed_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_sessions"])}</strong><span id="result-sessions"></span></div><div class="result"><strong>{html.escape(t["result_total"])}</strong><span id="result-total"></span></div><div class="result"><strong>{html.escape(t["result_listening"])}</strong><span id="result-listening"></span></div><div class="result"><strong>{html.escape(t["result_reading"])}</strong><span id="result-reading"></span></div><div class="result"><strong>{html.escape(t["result_review"])}</strong><span id="result-review"></span></div><div class="result"><strong>{html.escape(t["result_timed"])}</strong><span id="result-timed"></span></div></div>
<p class="note"><strong>{html.escape(t["result_plan_label"])}:</strong> <span id="result-plan"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["result_plan_label"])}</h2><ol>{checklist_items}</ol></article><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p>{html.escape(t["boundary_text"])}</p></article><article class="card wide"><h2>{html.escape(t["heuristic_title"])}</h2><p>{html.escape(t["heuristic_intro"])}</p><ul>{heuristic_items}</ul></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul>{facts_items}</ul><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
<p class="wrap">{html.escape(t["trademark_notice"])}</p>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="toeic-study-config">{config_json}</script>
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


INBOUND_LINK_CLASS = "toeic-planner-inline-link"
_CTA_ANCHOR_PATTERN = re.compile(
    r'<a\b[^>]*\bclass\s*=\s*(?P<q1>["\'])[^"\']*\bcta\b[^"\']*(?P=q1)[^>]*'
    r'\bhref\s*=\s*(?P<q2>["\'])[^"\']*apps\.apple\.com/app/id'
    + re.escape(APP_ID) +
    r'[^"\']*(?P=q2)[^>]*>',
    re.IGNORECASE,
)
_QR_CTA_ANCHOR_PATTERN = re.compile(
    r'<a\b[^>]*\bclass\s*=\s*(?P<q1>["\'])[^"\']*'
    r'\bapp-store-qr-card__link\b[^"\']*(?P=q1)[^>]*'
    r'\bhref\s*=\s*(?P<q2>["\'])[^"\']*apps\.apple\.com/app/id'
    + re.escape(APP_ID) +
    r'[^"\']*(?P=q2)[^>]*>',
    re.IGNORECASE,
)


def _answer_directories(pages: Path):
    for locale in ALT_LOCALES:
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
        yield locale, directory


def insert_answer_links(pages: Path = PAGES) -> int:
    """Insert one localized planner link before the first Aim990 App Store CTA.

    Narrowly scoped: only files in the 9 supported locale answer directories
    that literally contain the Aim990 App ID are candidates. Insertion is
    idempotent (skips files that already carry the marker class) and safe
    (skips files where no recognizable pre-CTA anchor can be found, rather
    than risking corrupt HTML).
    """
    changed = 0
    for locale, directory in _answer_directories(pages):
        if not directory.is_dir():
            continue
        t = COPY[locale]
        link_html = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-toeic-planner-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(t["inline_link_label"])}</a> '
        )
        for path in sorted(directory.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            if APP_ID not in text:
                continue
            if INBOUND_LINK_CLASS in text:
                continue
            match = _CTA_ANCHOR_PATTERN.search(text)
            if not match:
                match = _QR_CTA_ANCHOR_PATTERN.search(text)
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
        print(f"toeic study allocation planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
