#!/usr/bin/env python3
"""Generate a nine-locale private resume evidence-coverage planner."""

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
SLUG = "ats-resume-keyword-checker"
APP_KEY = "cvdesk"
APP_ID = "6781337213"
CONTENT_DATE = "2026-07-15"

DOL_RESUME = (
    "https://www.dol.gov/agencies/vets/programs/tap/"
    "teams-workshops/resume-essentials"
)
UK_CV = "https://nationalcareers.service.gov.uk/careers-advice/cv-sections"
EUROPASS_CV = "https://europass.europa.eu/en/create-europass-cv"
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
MARKET_FORMATS = (
    "not-checked",
    "us-resume",
    "uk-cv",
    "europass",
    "other",
)
LAYOUT_STATUSES = ("not-checked", "selectable-simple", "needs-review")

COPY = {
    "en": {
        "title": "Private Resume Evidence Coverage Planner | ATS Prep, No Upload",
        "description": (
            "Count job requirements backed by truthful evidence and review resume sections "
            "without pasting a job post, resume, name, employer or contact details."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no resume text · no ATS score",
        "heading": "Private resume evidence coverage planner",
        "lead": (
            "Use counts you make outside this page to see which stated requirements still need "
            "truthful support. This is not an ATS parse, ranking or hiring prediction."
        ),
        "badges": (
            "No resume or job-post text",
            "No names, contacts or employers",
            "No files, upload or account",
            "No score, threshold or hiring prediction",
        ),
        "planner": "Record only non-sensitive self-counts",
        "planner_intro": (
            "Read the current job post outside this page. Enter counts only; never paste any "
            "document or personal detail here."
        ),
        "market_label": "Format context",
        "market_options": {
            "not-checked": "Not checked",
            "us-resume": "U.S. resume",
            "uk-cv": "UK CV",
            "europass": "Europass CV",
            "other": "Other market or employer format",
        },
        "requirements_label": "Explicit requirements counted",
        "evidence_label": "Requirements backed by truthful evidence",
        "bullets_label": "Experience bullets counted",
        "outcomes_label": "Bullets with a verified outcome",
        "experience_label": "Experience section is present",
        "skills_label": "Skills section is present",
        "education_label": "Education section is present",
        "layout_label": "Exported text and layout review",
        "layout_options": {
            "not-checked": "Not checked",
            "selectable-simple": "Text is selectable and layout is simple",
            "needs-review": "Needs review or uses complex layout",
        },
        "update": "Update private checklist",
        "invalid_input": "Enter whole-number counts from 0 to 100.",
        "relation_invalid": (
            "Supported requirements cannot exceed listed requirements, and verified-outcome "
            "bullets cannot exceed total experience bullets."
        ),
        "result_requirements": "Truthfully supported requirements",
        "result_outcomes": "Bullets with verified outcomes",
        "result_sections": "Standard sections present",
        "result_layout": "Text and layout review",
        "result_plan": "Next review sequence",
        "next_steps": (
            "Count only explicit requirements from the current posting, outside this page.",
            "Link each supported requirement to truthful evidence you can explain; never invent experience.",
            "Add an outcome to a bullet only when it is verified; do not invent numbers.",
            "Use clear section headings and inspect the exported file for selectable text and simple reading order.",
            "Follow the employer's current instructions and the official format guidance for your market.",
        ),
        "boundary_title": "What these counts do not prove",
        "boundary_text": (
            "A count or ratio cannot show whether an employer's ATS parsed, ranked or rejected a "
            "resume, whether a recruiter will agree, or whether an application will lead to an "
            "interview or offer. Employers, roles and systems differ. No target threshold is applied."
        ),
        "sources_title": "Official resume and CV guidance before any optional app",
        "sources_intro": (
            "Use the employer's current instructions first. These official public resources give "
            "market-specific structure and tailoring context; they do not reveal an employer's ATS formula."
        ),
        "source_labels": (
            "U.S. Department of Labor: Resume Essentials",
            "UK National Careers Service: How to write a CV",
            "Europass: Create your Europass CV",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Build a transparent resume evidence-coverage checklist from bounded, non-sensitive "
            "self-counted numbers and status choices. Never receive resume text, job-post text, "
            "names, contacts, employers, dates, files or accounts; never produce an ATS score, "
            "parse result, ranking, hiring likelihood or recommendation."
        ),
        "app_title": "Want an optional on-device resume workflow?",
        "app_text": (
            "CV Desk is optional. Its current App Store listing describes an on-device ATS estimate, "
            "templates, PDF and DOCX export, free building and preview, and a one-time unlock with "
            "no subscription, account, upload or watermark. ATS behavior and employer decisions "
            "vary; verify the current listing and employer instructions. This planner works without the app."
        ),
        "app_cta": "View CV Desk on the App Store",
        "faq_title": "Resume evidence coverage questions",
        "faq": (
            (
                "Does this page receive my resume or job description?",
                "No. It accepts only bounded counts, booleans and format-status choices.",
            ),
            (
                "Is the evidence ratio an ATS score?",
                "No. It is only your supported count divided by your stated total, with no target or ranking.",
            ),
            (
                "What if I cannot support a requirement?",
                "Do not invent experience or keywords. Leave it unsupported, or add evidence only if it is truthful and relevant.",
            ),
            (
                "Must every outcome be a number?",
                "No. Use a number only when it is accurate and defensible; a specific truthful qualitative outcome can also be useful.",
            ),
        ),
        "footer": "Private self-counts only · no documents · no ATS score · no hiring prediction",
        "index_title": "Private Resume Evidence Coverage Planner",
        "index_description": (
            "Count truthful evidence and review standard sections without pasting a resume, "
            "job post or personal details, and without an ATS score."
        ),
    },
    "es-ES": {
        "title": "Planificador privado de evidencias del CV | Preparación ATS sin subir archivos",
        "description": (
            "Cuenta los requisitos respaldados por pruebas reales y revisa las secciones del CV "
            "sin pegar ofertas, currículums ni datos personales."
        ),
        "tools": "Herramientas gratis",
        "switch": "English",
        "eyebrow": "Gratis · sin texto del CV · sin puntuación ATS",
        "heading": "Planificador privado de evidencias del CV",
        "lead": (
            "Usa recuentos hechos fuera de esta página para detectar qué requisitos aún necesitan "
            "pruebas reales. No analiza ATS ni predice rankings o contrataciones."
        ),
        "badges": (
            "Sin texto del CV ni de la oferta",
            "Sin nombres, contactos ni empresas",
            "Sin archivos, subida ni cuenta",
            "Sin puntuación, umbral ni predicción",
        ),
        "planner": "Anota solo recuentos no sensibles",
        "planner_intro": (
            "Lee la oferta actual fuera de esta página. Introduce solo cifras; no pegues documentos "
            "ni datos personales."
        ),
        "market_label": "Contexto de formato",
        "market_options": {
            "not-checked": "Sin revisar",
            "us-resume": "Résumé de EE. UU.",
            "uk-cv": "CV del Reino Unido",
            "europass": "CV Europass",
            "other": "Otro mercado o formato de empresa",
        },
        "requirements_label": "Requisitos explícitos contados",
        "evidence_label": "Requisitos con pruebas reales",
        "bullets_label": "Viñetas de experiencia contadas",
        "outcomes_label": "Viñetas con resultado verificado",
        "experience_label": "Incluye sección de experiencia",
        "skills_label": "Incluye sección de competencias",
        "education_label": "Incluye sección de formación",
        "layout_label": "Revisión del texto exportado y diseño",
        "layout_options": {
            "not-checked": "Sin revisar",
            "selectable-simple": "Texto seleccionable y diseño sencillo",
            "needs-review": "Necesita revisión o usa un diseño complejo",
        },
        "update": "Actualizar lista privada",
        "invalid_input": "Introduce números enteros de 0 a 100.",
        "relation_invalid": (
            "Los requisitos respaldados no pueden superar el total, y las viñetas con resultados "
            "no pueden superar el total de viñetas."
        ),
        "result_requirements": "Requisitos respaldados con veracidad",
        "result_outcomes": "Viñetas con resultados verificados",
        "result_sections": "Secciones estándar presentes",
        "result_layout": "Revisión de texto y diseño",
        "result_plan": "Siguiente secuencia de revisión",
        "next_steps": (
            "Cuenta solo los requisitos explícitos de la oferta actual, fuera de esta página.",
            "Relaciona cada requisito respaldado con pruebas reales que puedas explicar; no inventes experiencia.",
            "Añade resultados a una viñeta solo si están verificados; no inventes cifras.",
            "Usa títulos claros y comprueba que el archivo exportado tenga texto seleccionable y orden sencillo.",
            "Sigue las instrucciones actuales de la empresa y la guía oficial del formato de tu mercado.",
        ),
        "boundary_title": "Lo que estos recuentos no demuestran",
        "boundary_text": (
            "Un recuento o proporción no demuestra cómo un ATS ha leído, clasificado o rechazado un "
            "CV, ni predice la opinión de selección, una entrevista o una oferta. Cada empresa, "
            "puesto y sistema es distinto. No se aplica ningún umbral objetivo."
        ),
        "sources_title": "Guías oficiales antes de cualquier app opcional",
        "sources_intro": (
            "Prioriza las instrucciones actuales de la empresa. Estas fuentes públicas oficiales "
            "aportan contexto local, pero no revelan fórmulas ATS."
        ),
        "source_labels": (
            "Departamento de Trabajo de EE. UU.: Resume Essentials",
            "National Careers Service del Reino Unido: cómo escribir un CV",
            "Europass: crea tu CV Europass",
        ),
        "webmcp_source": "Vista previa de la API imperativa WebMCP de Chrome",
        "webmcp_description": (
            "Crea una lista transparente de evidencias del CV con cifras y estados acotados y no "
            "sensibles. No recibe textos, nombres, contactos, empresas, fechas, archivos ni cuentas, "
            "y no genera puntuaciones ATS, análisis, rankings ni predicciones de contratación."
        ),
        "app_title": "¿Quieres un flujo opcional de CV en el dispositivo?",
        "app_text": (
            "CV Desk es opcional. Su ficha actual describe una estimación ATS en el dispositivo, "
            "plantillas, exportación PDF y DOCX, creación y vista previa gratuitas, y desbloqueo único "
            "sin suscripción, cuenta, subida ni marca de agua. Los ATS y las decisiones de empresa "
            "varían; revisa la ficha y las instrucciones actuales. Este planificador funciona sin la app."
        ),
        "app_cta": "Ver CV Desk en el App Store",
        "faq_title": "Preguntas sobre evidencias del CV",
        "faq": (
            (
                "¿Esta página recibe mi CV o la oferta?",
                "No. Solo acepta recuentos acotados, opciones booleanas y estados de formato.",
            ),
            (
                "¿La proporción de evidencias es una puntuación ATS?",
                "No. Solo divide tu recuento respaldado entre el total indicado, sin objetivo ni ranking.",
            ),
            (
                "¿Qué hago si no puedo respaldar un requisito?",
                "No inventes experiencia ni palabras clave. Déjalo sin respaldo o añade pruebas solo si son reales y relevantes.",
            ),
            (
                "¿Todos los resultados deben ser números?",
                "No. Usa cifras solo si son exactas y defendibles; un resultado cualitativo específico y real también sirve.",
            ),
        ),
        "footer": "Solo recuentos privados · sin documentos · sin puntuación ATS · sin predicción",
        "index_title": "Planificador privado de evidencias del CV",
        "index_description": (
            "Cuenta pruebas reales y revisa secciones sin pegar el CV, la oferta ni datos personales, "
            "y sin generar una puntuación ATS."
        ),
    },
    "pt-BR": {
        "title": "Planejador privado de evidências do currículo | Preparação ATS sem upload",
        "description": (
            "Conte requisitos apoiados por evidências verdadeiras e revise seções do currículo "
            "sem colar vaga, currículo ou dados pessoais."
        ),
        "tools": "Ferramentas grátis",
        "switch": "English",
        "eyebrow": "Grátis · sem texto do currículo · sem nota ATS",
        "heading": "Planejador privado de evidências do currículo",
        "lead": (
            "Use contagens feitas fora desta página para ver quais requisitos ainda precisam de "
            "evidências verdadeiras. Isto não analisa ATS nem prevê ranking ou contratação."
        ),
        "badges": (
            "Sem texto do currículo ou da vaga",
            "Sem nomes, contatos ou empresas",
            "Sem arquivo, upload ou conta",
            "Sem nota, meta ou previsão",
        ),
        "planner": "Registre apenas contagens não sensíveis",
        "planner_intro": (
            "Leia a vaga atual fora desta página. Digite apenas números; nunca cole documentos ou "
            "dados pessoais aqui."
        ),
        "market_label": "Contexto de formato",
        "market_options": {
            "not-checked": "Não conferido",
            "us-resume": "Currículo dos EUA",
            "uk-cv": "CV do Reino Unido",
            "europass": "CV Europass",
            "other": "Outro mercado ou formato da empresa",
        },
        "requirements_label": "Requisitos explícitos contados",
        "evidence_label": "Requisitos com evidências verdadeiras",
        "bullets_label": "Tópicos de experiência contados",
        "outcomes_label": "Tópicos com resultado verificado",
        "experience_label": "A seção de experiência está presente",
        "skills_label": "A seção de habilidades está presente",
        "education_label": "A seção de formação está presente",
        "layout_label": "Revisão do texto exportado e do layout",
        "layout_options": {
            "not-checked": "Não conferido",
            "selectable-simple": "Texto selecionável e layout simples",
            "needs-review": "Precisa de revisão ou usa layout complexo",
        },
        "update": "Atualizar checklist privado",
        "invalid_input": "Digite números inteiros de 0 a 100.",
        "relation_invalid": (
            "Requisitos comprovados não podem superar o total, e tópicos com resultado não podem "
            "superar o total de tópicos."
        ),
        "result_requirements": "Requisitos comprovados com honestidade",
        "result_outcomes": "Tópicos com resultados verificados",
        "result_sections": "Seções padrão presentes",
        "result_layout": "Revisão de texto e layout",
        "result_plan": "Próxima sequência de revisão",
        "next_steps": (
            "Conte apenas requisitos explícitos da vaga atual, fora desta página.",
            "Ligue cada requisito comprovado a uma evidência verdadeira que você saiba explicar; não invente experiência.",
            "Inclua um resultado no tópico apenas se ele for verificado; não invente números.",
            "Use títulos claros e confira se o arquivo exportado tem texto selecionável e ordem simples.",
            "Siga as instruções atuais da empresa e a orientação oficial do formato do seu mercado.",
        ),
        "boundary_title": "O que essas contagens não comprovam",
        "boundary_text": (
            "Uma contagem ou proporção não mostra se o ATS de uma empresa leu, classificou ou "
            "rejeitou um currículo, nem prevê avaliação, entrevista ou oferta. Empresas, vagas e "
            "sistemas variam. Nenhuma meta de corte é aplicada."
        ),
        "sources_title": "Orientação oficial antes de qualquer app opcional",
        "sources_intro": (
            "Priorize as instruções atuais da empresa. Estas fontes públicas oficiais trazem "
            "contexto local, mas não revelam fórmulas de ATS."
        ),
        "source_labels": (
            "Departamento do Trabalho dos EUA: Resume Essentials",
            "National Careers Service do Reino Unido: como escrever um CV",
            "Europass: crie seu CV Europass",
        ),
        "webmcp_source": "Prévia da API imperativa WebMCP do Chrome",
        "webmcp_description": (
            "Crie um checklist transparente de evidências do currículo com números e estados "
            "limitados e não sensíveis. Não recebe textos, nomes, contatos, empresas, datas, arquivos "
            "ou contas e não gera nota ATS, análise, ranking ou previsão de contratação."
        ),
        "app_title": "Quer um fluxo opcional de currículo no dispositivo?",
        "app_text": (
            "O CV Desk é opcional. A página atual descreve estimativa ATS no dispositivo, modelos, "
            "exportação em PDF e DOCX, criação e prévia grátis e desbloqueio único sem assinatura, "
            "conta, upload ou marca-d'água. ATS e decisões das empresas variam; confira a página e "
            "as instruções atuais. Este planejador funciona sem o app."
        ),
        "app_cta": "Ver o CV Desk na App Store",
        "faq_title": "Perguntas sobre evidências do currículo",
        "faq": (
            (
                "Esta página recebe meu currículo ou a vaga?",
                "Não. Ela aceita apenas contagens limitadas, opções booleanas e estados de formato.",
            ),
            (
                "A proporção de evidências é uma nota ATS?",
                "Não. É apenas a contagem comprovada dividida pelo total informado, sem meta ou ranking.",
            ),
            (
                "E se eu não puder comprovar um requisito?",
                "Não invente experiência ou palavras-chave. Deixe sem comprovação ou adicione evidência apenas se for verdadeira e relevante.",
            ),
            (
                "Todo resultado precisa ser numérico?",
                "Não. Use números apenas quando forem corretos e defensáveis; um resultado qualitativo específico e verdadeiro também ajuda.",
            ),
        ),
        "footer": "Só contagens privadas · sem documentos · sem nota ATS · sem previsão",
        "index_title": "Planejador privado de evidências do currículo",
        "index_description": (
            "Conte evidências verdadeiras e revise seções sem colar currículo, vaga ou dados "
            "pessoais e sem gerar nota ATS."
        ),
    },
    "de-DE": {
        "title": "Privater Lebenslauf-Evidenzplaner | ATS-Vorbereitung ohne Upload",
        "description": (
            "Zähle Anforderungen mit wahrheitsgemäßen Belegen und prüfe Lebenslaufabschnitte, "
            "ohne Stellenanzeige, Lebenslauf oder persönliche Daten einzufügen."
        ),
        "tools": "Kostenlose Tools",
        "switch": "English",
        "eyebrow": "Kostenlos · kein Lebenslauftext · kein ATS-Score",
        "heading": "Privater Evidenzplaner für den Lebenslauf",
        "lead": (
            "Nutze außerhalb dieser Seite ermittelte Anzahlen, um unbelegte Anforderungen zu sehen. "
            "Dies ist weder ATS-Analyse noch Ranking- oder Einstellungsprognose."
        ),
        "badges": (
            "Kein Lebenslauf- oder Anzeigentext",
            "Keine Namen, Kontakte oder Arbeitgeber",
            "Keine Dateien, Uploads oder Konten",
            "Kein Score, Grenzwert oder Prognose",
        ),
        "planner": "Nur nicht sensible Anzahlen erfassen",
        "planner_intro": (
            "Lies die aktuelle Stellenanzeige außerhalb dieser Seite. Gib nur Anzahlen ein und "
            "füge hier niemals Dokumente oder persönliche Angaben ein."
        ),
        "market_label": "Formatkontext",
        "market_options": {
            "not-checked": "Nicht geprüft",
            "us-resume": "US-Résumé",
            "uk-cv": "Britischer CV",
            "europass": "Europass-Lebenslauf",
            "other": "Anderer Markt oder Arbeitgeberformat",
        },
        "requirements_label": "Gezählte ausdrückliche Anforderungen",
        "evidence_label": "Anforderungen mit ehrlichen Belegen",
        "bullets_label": "Gezählte Erfahrungs-Stichpunkte",
        "outcomes_label": "Stichpunkte mit geprüftem Ergebnis",
        "experience_label": "Abschnitt Berufserfahrung vorhanden",
        "skills_label": "Abschnitt Fähigkeiten vorhanden",
        "education_label": "Abschnitt Ausbildung vorhanden",
        "layout_label": "Prüfung von Exporttext und Layout",
        "layout_options": {
            "not-checked": "Nicht geprüft",
            "selectable-simple": "Text auswählbar und Layout einfach",
            "needs-review": "Prüfung nötig oder komplexes Layout",
        },
        "update": "Private Checkliste aktualisieren",
        "invalid_input": "Ganze Zahlen von 0 bis 100 eingeben.",
        "relation_invalid": (
            "Belegte Anforderungen dürfen die Gesamtzahl nicht überschreiten; Stichpunkte mit "
            "Ergebnis dürfen nicht über allen Erfahrungs-Stichpunkten liegen."
        ),
        "result_requirements": "Wahrheitsgemäß belegte Anforderungen",
        "result_outcomes": "Stichpunkte mit geprüften Ergebnissen",
        "result_sections": "Vorhandene Standardabschnitte",
        "result_layout": "Text- und Layoutprüfung",
        "result_plan": "Nächste Prüfreihenfolge",
        "next_steps": (
            "Zähle außerhalb dieser Seite nur ausdrückliche Anforderungen der aktuellen Anzeige.",
            "Verknüpfe jede belegte Anforderung mit ehrlicher, erklärbarer Evidenz; erfinde keine Erfahrung.",
            "Ergänze ein Ergebnis nur, wenn es geprüft ist; erfinde keine Zahlen.",
            "Nutze klare Überschriften und prüfe die exportierte Datei auf auswählbaren Text und einfache Lesereihenfolge.",
            "Befolge aktuelle Arbeitgebervorgaben und die offizielle Formathilfe deines Marktes.",
        ),
        "boundary_title": "Was diese Anzahlen nicht beweisen",
        "boundary_text": (
            "Anzahl oder Verhältnis zeigen nicht, ob ein Arbeitgeber-ATS den Lebenslauf gelesen, "
            "eingestuft oder abgelehnt hat, und sagen keine Bewertung, Einladung oder Zusage voraus. "
            "Arbeitgeber, Stellen und Systeme unterscheiden sich. Es gilt kein Zielgrenzwert."
        ),
        "sources_title": "Offizielle Hilfe vor jeder optionalen App",
        "sources_intro": (
            "Aktuelle Arbeitgebervorgaben haben Vorrang. Diese offiziellen öffentlichen Quellen "
            "bieten marktspezifischen Kontext, legen aber keine ATS-Formel offen."
        ),
        "source_labels": (
            "US-Arbeitsministerium: Resume Essentials",
            "UK National Careers Service: Einen CV schreiben",
            "Europass: Europass-Lebenslauf erstellen",
        ),
        "webmcp_source": "Vorschau der imperativen Chrome-WebMCP-API",
        "webmcp_description": (
            "Erstellt eine transparente Evidenz-Checkliste aus begrenzten, nicht sensiblen Anzahlen "
            "und Statusangaben. Empfängt keine Texte, Namen, Kontakte, Arbeitgeber, Daten, Dateien "
            "oder Konten und erzeugt keinen ATS-Score, Parsingbericht, Ranking oder Einstellungsprognose."
        ),
        "app_title": "Optionaler Lebenslauf-Workflow auf dem Gerät?",
        "app_text": (
            "CV Desk ist optional. Der aktuelle App-Store-Eintrag beschreibt eine ATS-Schätzung auf "
            "dem Gerät, Vorlagen, PDF-/DOCX-Export, kostenloses Erstellen und Vorschauen sowie eine "
            "einmalige Freischaltung ohne Abo, Konto, Upload oder Wasserzeichen. ATS und Entscheidungen "
            "variieren; prüfe Eintrag und Arbeitgebervorgaben. Der Planer funktioniert ohne App."
        ),
        "app_cta": "CV Desk im App Store ansehen",
        "faq_title": "Fragen zur Lebenslauf-Evidenz",
        "faq": (
            (
                "Erhält diese Seite meinen Lebenslauf oder die Anzeige?",
                "Nein. Sie akzeptiert nur begrenzte Anzahlen, Wahr/Falsch-Angaben und Formatstatus.",
            ),
            (
                "Ist das Evidenzverhältnis ein ATS-Score?",
                "Nein. Es ist nur deine belegte Anzahl geteilt durch deine Gesamtzahl, ohne Ziel oder Ranking.",
            ),
            (
                "Was, wenn ich eine Anforderung nicht belegen kann?",
                "Erfinde keine Erfahrung oder Keywords. Lass sie unbelegt oder ergänze nur wahre, relevante Evidenz.",
            ),
            (
                "Muss jedes Ergebnis eine Zahl sein?",
                "Nein. Nutze Zahlen nur korrekt und belegbar; auch ein konkretes ehrliches qualitatives Ergebnis kann nützlich sein.",
            ),
        ),
        "footer": "Nur private Anzahlen · keine Dokumente · kein ATS-Score · keine Prognose",
        "index_title": "Privater Lebenslauf-Evidenzplaner",
        "index_description": (
            "Zähle ehrliche Belege und prüfe Abschnitte, ohne Lebenslauf, Anzeige oder persönliche "
            "Daten einzufügen und ohne ATS-Score."
        ),
    },
    "fr-FR": {
        "title": "Planificateur privé de preuves pour CV | Préparation ATS sans envoi",
        "description": (
            "Comptez les exigences appuyées par des preuves véridiques et vérifiez les rubriques du "
            "CV sans coller d'offre, de CV ni de données personnelles."
        ),
        "tools": "Outils gratuits",
        "switch": "English",
        "eyebrow": "Gratuit · aucun texte de CV · aucun score ATS",
        "heading": "Planificateur privé de preuves pour CV",
        "lead": (
            "Utilisez des décomptes faits hors de cette page pour repérer les exigences sans preuve "
            "véridique. Ce n'est ni une analyse ATS ni une prédiction de classement ou d'embauche."
        ),
        "badges": (
            "Aucun texte de CV ou d'offre",
            "Aucun nom, contact ou employeur",
            "Aucun fichier, envoi ou compte",
            "Aucun score, seuil ou prédiction",
        ),
        "planner": "Saisir uniquement des décomptes non sensibles",
        "planner_intro": (
            "Lisez l'offre actuelle hors de cette page. Saisissez seulement des nombres et ne "
            "collez jamais de document ni de donnée personnelle ici."
        ),
        "market_label": "Contexte du format",
        "market_options": {
            "not-checked": "Non vérifié",
            "us-resume": "Résumé américain",
            "uk-cv": "CV britannique",
            "europass": "CV Europass",
            "other": "Autre marché ou format employeur",
        },
        "requirements_label": "Exigences explicites comptées",
        "evidence_label": "Exigences avec preuves véridiques",
        "bullets_label": "Puces d'expérience comptées",
        "outcomes_label": "Puces avec résultat vérifié",
        "experience_label": "Rubrique Expérience présente",
        "skills_label": "Rubrique Compétences présente",
        "education_label": "Rubrique Formation présente",
        "layout_label": "Vérification du texte exporté et de la mise en page",
        "layout_options": {
            "not-checked": "Non vérifié",
            "selectable-simple": "Texte sélectionnable et mise en page simple",
            "needs-review": "À vérifier ou mise en page complexe",
        },
        "update": "Mettre à jour la checklist privée",
        "invalid_input": "Saisissez des nombres entiers de 0 à 100.",
        "relation_invalid": (
            "Les exigences appuyées ne peuvent dépasser le total, et les puces avec résultat ne "
            "peuvent dépasser toutes les puces d'expérience."
        ),
        "result_requirements": "Exigences appuyées honnêtement",
        "result_outcomes": "Puces avec résultats vérifiés",
        "result_sections": "Rubriques standard présentes",
        "result_layout": "Vérification texte et mise en page",
        "result_plan": "Prochaine séquence de vérification",
        "next_steps": (
            "Comptez uniquement les exigences explicites de l'offre actuelle, hors de cette page.",
            "Reliez chaque exigence appuyée à une preuve véridique que vous pouvez expliquer; n'inventez rien.",
            "Ajoutez un résultat à une puce uniquement s'il est vérifié; n'inventez pas de chiffres.",
            "Utilisez des titres clairs et vérifiez le texte sélectionnable et l'ordre de lecture du fichier exporté.",
            "Suivez les consignes actuelles de l'employeur et le guide officiel du format de votre marché.",
        ),
        "boundary_title": "Ce que ces décomptes ne prouvent pas",
        "boundary_text": (
            "Un décompte ou ratio ne montre pas si l'ATS d'un employeur a lu, classé ou rejeté un CV "
            "et ne prédit ni l'avis du recruteur, ni entretien, ni offre. Employeurs, postes et "
            "systèmes diffèrent. Aucun seuil cible n'est appliqué."
        ),
        "sources_title": "Guides officiels avant toute app facultative",
        "sources_intro": (
            "Les consignes actuelles de l'employeur priment. Ces sources publiques officielles "
            "donnent un contexte local, mais ne révèlent aucune formule ATS."
        ),
        "source_labels": (
            "Département du Travail des États-Unis : Resume Essentials",
            "National Careers Service du Royaume-Uni : rédiger un CV",
            "Europass : créer votre CV Europass",
        ),
        "webmcp_source": "Aperçu de l'API impérative WebMCP de Chrome",
        "webmcp_description": (
            "Crée une checklist transparente à partir de nombres et d'états bornés non sensibles. "
            "Ne reçoit aucun texte, nom, contact, employeur, date, fichier ou compte et ne produit "
            "aucun score ATS, résultat d'analyse, classement ou prédiction d'embauche."
        ),
        "app_title": "Besoin d'un flux de CV facultatif sur l'appareil ?",
        "app_text": (
            "CV Desk est facultatif. Sa fiche actuelle décrit une estimation ATS sur l'appareil, "
            "des modèles, l'export PDF et DOCX, la création et l'aperçu gratuits, puis un déblocage "
            "unique sans abonnement, compte, envoi ni filigrane. ATS et décisions varient; vérifiez "
            "la fiche et les consignes actuelles. Ce planificateur fonctionne sans l'app."
        ),
        "app_cta": "Voir CV Desk sur l'App Store",
        "faq_title": "Questions sur les preuves du CV",
        "faq": (
            (
                "Cette page reçoit-elle mon CV ou l'offre ?",
                "Non. Elle accepte seulement des nombres bornés, des booléens et des états de format.",
            ),
            (
                "Le ratio de preuves est-il un score ATS ?",
                "Non. Il divise seulement votre décompte appuyé par votre total, sans cible ni classement.",
            ),
            (
                "Et si je ne peux pas appuyer une exigence ?",
                "N'inventez ni expérience ni mot-clé. Laissez-la sans preuve ou ajoutez uniquement une preuve vraie et pertinente.",
            ),
            (
                "Chaque résultat doit-il être chiffré ?",
                "Non. Utilisez un chiffre seulement s'il est exact et défendable; un résultat qualitatif précis et vrai convient aussi.",
            ),
        ),
        "footer": "Décomptes privés uniquement · aucun document · aucun score ATS · aucune prédiction",
        "index_title": "Planificateur privé de preuves pour CV",
        "index_description": (
            "Comptez les preuves véridiques et vérifiez les rubriques sans coller CV, offre ou "
            "données personnelles et sans score ATS."
        ),
    },
    "ja": {
        "title": "履歴書・職務経歴書の非公開エビデンス確認｜アップロード不要のATS準備",
        "description": "求人要件を裏づける事実の件数と書類の構成を、求人票・履歴書・個人情報を貼り付けずに確認します。",
        "tools": "無料ツール",
        "switch": "English",
        "eyebrow": "無料・書類本文不要・ATSスコアなし",
        "heading": "履歴書・職務経歴書の非公開エビデンス確認",
        "lead": "このページ外で数えた件数だけを使い、事実で裏づけていない求人要件を確認します。ATS解析、順位、採用予測ではありません。",
        "badges": (
            "求人票・応募書類の本文不要",
            "氏名・連絡先・勤務先不要",
            "ファイル・送信・アカウント不要",
            "点数・合格基準・採用予測なし",
        ),
        "planner": "機密性のない自己集計だけを入力",
        "planner_intro": "現在の求人票はこのページ外で読み、件数だけを入力してください。書類や個人情報は貼り付けないでください。",
        "market_label": "書式の前提",
        "market_options": {
            "not-checked": "未確認",
            "us-resume": "米国式レジュメ",
            "uk-cv": "英国式CV",
            "europass": "Europass CV",
            "other": "その他の市場・応募先指定書式",
        },
        "requirements_label": "数えた明示要件",
        "evidence_label": "事実で裏づけた要件",
        "bullets_label": "数えた職務経歴の箇条書き",
        "outcomes_label": "確認済み成果を含む箇条書き",
        "experience_label": "職務経歴の見出しがある",
        "skills_label": "スキルの見出しがある",
        "education_label": "学歴の見出しがある",
        "layout_label": "書き出した文字とレイアウトの確認",
        "layout_options": {
            "not-checked": "未確認",
            "selectable-simple": "文字を選択でき、構成が簡潔",
            "needs-review": "要確認、または複雑な構成",
        },
        "update": "非公開チェックリストを更新",
        "invalid_input": "0〜100の整数を入力してください。",
        "relation_invalid": "裏づけた要件は全要件以下、成果付き箇条書きは全箇条書き以下にしてください。",
        "result_requirements": "事実で裏づけた要件",
        "result_outcomes": "確認済み成果を含む箇条書き",
        "result_sections": "標準見出しの有無",
        "result_layout": "文字とレイアウトの確認",
        "result_plan": "次の確認手順",
        "next_steps": (
            "現在の求人票に明記された要件だけを、このページ外で数えます。",
            "各要件を説明できる事実に結び付け、経験を作らないでください。",
            "確認できる場合だけ成果を箇条書きに加え、数字を作らないでください。",
            "明確な見出しを使い、書き出したファイルの文字選択と読み順を確認します。",
            "応募先の最新指示と、対象市場の公式書式案内を優先します。",
        ),
        "boundary_title": "この件数で証明できないこと",
        "boundary_text": "件数や比率から、応募先ATSの読取・順位・不採用理由、採用担当者の判断、面接や内定を判断できません。応募先・職種・システムごとに異なり、目標点や合格線は設けません。",
        "sources_title": "任意のアプリより先に確認する公式案内",
        "sources_intro": "応募先の最新指示を最優先してください。以下は市場別の公式公開資料であり、応募先ATSの計算式を示すものではありません。",
        "source_labels": (
            "米国労働省：Resume Essentials",
            "英国 National Careers Service：CVの書き方",
            "Europass：Europass CVの作成",
        ),
        "webmcp_source": "Chrome WebMCP 命令型APIプレビュー",
        "webmcp_description": "機密性のない範囲限定の件数と状態だけで、透明なエビデンス確認表を作成します。文書本文、氏名、連絡先、勤務先、日付、ファイル、アカウントを受け取らず、ATSスコア、解析結果、順位、採用予測を生成しません。",
        "app_title": "端末内の応募書類作成を任意で使いますか？",
        "app_text": "CV Deskは任意です。現在のApp Store掲載内容では、端末内ATS推定、テンプレート、PDF・DOCX書き出し、無料作成・プレビュー、サブスクリプション・アカウント・アップロード・透かしなしの一度買い切り解除を案内しています。ATSと採用判断は異なるため、最新掲載内容と応募先指示を確認してください。このツールはアプリなしで使えます。",
        "app_cta": "App StoreでCV Deskを見る",
        "faq_title": "応募書類のエビデンス確認に関する質問",
        "faq": (
            ("このページに履歴書や求人票を送りますか？", "いいえ。範囲限定の件数、真偽値、書式状態だけを受け取ります。"),
            ("エビデンス比率はATSスコアですか？", "いいえ。自己申告した合計に対する裏づけ件数であり、目標点や順位はありません。"),
            ("要件を裏づけられない場合は？", "経験やキーワードを作らず、未対応のままにするか、真実で関連する事実がある場合だけ追加してください。"),
            ("成果は必ず数字で書きますか？", "いいえ。正確に説明できる場合だけ数字を使い、具体的で真実の定性的成果も利用できます。"),
        ),
        "footer": "非公開の自己集計のみ・文書不要・ATSスコアなし・採用予測なし",
        "index_title": "応募書類の非公開エビデンス確認",
        "index_description": "履歴書、求人票、個人情報を貼らずに、事実の裏づけ件数と標準見出しを確認します。ATSスコアは出しません。",
    },
    "ko": {
        "title": "비공개 이력서 근거 점검표 | 업로드 없는 ATS 준비",
        "description": "채용 공고, 이력서, 개인정보를 붙여 넣지 않고 실제 근거가 있는 요건 수와 이력서 구성을 점검합니다.",
        "tools": "무료 도구",
        "switch": "English",
        "eyebrow": "무료 · 이력서 본문 없음 · ATS 점수 없음",
        "heading": "비공개 이력서 근거 점검표",
        "lead": "이 페이지 밖에서 직접 센 수만 입력해 실제 근거가 부족한 요건을 확인하세요. ATS 분석, 순위 또는 채용 예측이 아닙니다.",
        "badges": (
            "이력서·채용 공고 본문 없음",
            "이름·연락처·회사 정보 없음",
            "파일·업로드·계정 없음",
            "점수·기준선·채용 예측 없음",
        ),
        "planner": "민감하지 않은 직접 집계만 입력",
        "planner_intro": "현재 채용 공고는 이 페이지 밖에서 읽고 숫자만 입력하세요. 문서나 개인정보를 붙여 넣지 마세요.",
        "market_label": "문서 형식 기준",
        "market_options": {
            "not-checked": "확인하지 않음",
            "us-resume": "미국식 이력서",
            "uk-cv": "영국식 CV",
            "europass": "Europass CV",
            "other": "기타 시장 또는 회사 지정 형식",
        },
        "requirements_label": "직접 센 명시 요건",
        "evidence_label": "사실로 뒷받침한 요건",
        "bullets_label": "직접 센 경력 불릿",
        "outcomes_label": "확인된 결과가 있는 불릿",
        "experience_label": "경력 섹션 있음",
        "skills_label": "기술 섹션 있음",
        "education_label": "학력 섹션 있음",
        "layout_label": "내보낸 텍스트와 레이아웃 점검",
        "layout_options": {
            "not-checked": "확인하지 않음",
            "selectable-simple": "텍스트 선택 가능, 단순한 레이아웃",
            "needs-review": "점검 필요 또는 복잡한 레이아웃",
        },
        "update": "비공개 점검표 업데이트",
        "invalid_input": "0부터 100까지의 정수를 입력하세요.",
        "relation_invalid": "근거가 있는 요건은 전체 요건 이하, 결과가 있는 불릿은 전체 경력 불릿 이하로 입력하세요.",
        "result_requirements": "사실로 뒷받침한 요건",
        "result_outcomes": "확인된 결과가 있는 불릿",
        "result_sections": "표준 섹션 보유",
        "result_layout": "텍스트와 레이아웃 점검",
        "result_plan": "다음 점검 순서",
        "next_steps": (
            "현재 공고에 명시된 요건만 이 페이지 밖에서 셉니다.",
            "각 요건을 설명할 수 있는 실제 근거와 연결하고 경험을 만들지 마세요.",
            "확인된 경우에만 불릿에 결과를 추가하고 숫자를 만들지 마세요.",
            "명확한 섹션 제목을 쓰고 내보낸 파일의 텍스트 선택과 단순한 읽기 순서를 확인하세요.",
            "회사의 최신 안내와 해당 시장의 공식 문서 형식 안내를 우선하세요.",
        ),
        "boundary_title": "이 숫자로 증명할 수 없는 것",
        "boundary_text": "숫자나 비율은 회사 ATS의 읽기·순위·탈락 여부, 채용 담당자의 판단, 면접 또는 합격을 보여 주지 않습니다. 회사, 직무, 시스템마다 다르며 목표 점수나 기준선을 적용하지 않습니다.",
        "sources_title": "선택형 앱보다 먼저 확인할 공식 안내",
        "sources_intro": "회사의 최신 지침을 가장 먼저 따르세요. 아래 공식 공개 자료는 시장별 문서 구성 참고용이며 회사 ATS 공식을 공개하지 않습니다.",
        "source_labels": (
            "미국 노동부: Resume Essentials",
            "영국 National Careers Service: CV 작성법",
            "Europass: Europass CV 만들기",
        ),
        "webmcp_source": "Chrome WebMCP 명령형 API 미리보기",
        "webmcp_description": "범위가 제한된 비민감 숫자와 상태만으로 투명한 이력서 근거 점검표를 만듭니다. 문서 본문, 이름, 연락처, 회사, 날짜, 파일, 계정을 받지 않으며 ATS 점수, 분석 결과, 순위 또는 채용 예측을 만들지 않습니다.",
        "app_title": "기기 내 이력서 작업 흐름을 선택해서 사용하시겠어요?",
        "app_text": "CV Desk는 선택 사항입니다. 현재 App Store 설명에는 기기 내 ATS 추정, 템플릿, PDF·DOCX 내보내기, 무료 작성·미리보기, 구독·계정·업로드·워터마크 없는 일회성 잠금 해제가 나옵니다. ATS와 회사 판단은 다르므로 최신 설명과 회사 지침을 확인하세요. 이 점검표는 앱 없이 작동합니다.",
        "app_cta": "App Store에서 CV Desk 보기",
        "faq_title": "이력서 근거 점검 질문",
        "faq": (
            ("이 페이지가 이력서나 채용 공고를 받나요?", "아니요. 범위가 제한된 숫자, 불리언, 형식 상태만 받습니다."),
            ("근거 비율이 ATS 점수인가요?", "아니요. 직접 입력한 전체 수 대비 근거 수일 뿐이며 목표나 순위가 없습니다."),
            ("요건을 뒷받침할 수 없다면 어떻게 하나요?", "경험이나 키워드를 만들지 마세요. 근거 없음으로 두거나 사실이고 관련된 근거가 있을 때만 추가하세요."),
            ("모든 결과가 숫자여야 하나요?", "아니요. 정확히 설명할 수 있을 때만 숫자를 쓰고, 구체적이고 사실인 정성적 결과도 사용할 수 있습니다."),
        ),
        "footer": "비공개 직접 집계만 · 문서 없음 · ATS 점수 없음 · 채용 예측 없음",
        "index_title": "비공개 이력서 근거 점검표",
        "index_description": "이력서, 공고, 개인정보를 붙이지 않고 실제 근거와 표준 섹션을 점검합니다. ATS 점수는 만들지 않습니다.",
    },
    "zh-Hant": {
        "title": "私密履歷證據覆蓋規劃器｜不上傳的 ATS 準備",
        "description": "只計算有真實證據支持的職缺要求並檢查履歷區段；不貼上職缺、履歷、姓名、公司或聯絡資料。",
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 不接收履歷文字 · 不產生 ATS 分數",
        "heading": "私密履歷證據覆蓋規劃器",
        "lead": "只輸入你在本頁之外自行清點的數量，找出仍缺真實證據的明確要求；這不是 ATS 解析、排名或錄取預測。",
        "badges": (
            "不接收履歷或職缺文字",
            "不接收姓名、聯絡資料或公司",
            "不接收檔案、不上傳、免帳號",
            "無分數、門檻或錄取預測",
        ),
        "planner": "只記錄非敏感的自行計數",
        "planner_intro": "請在本頁之外閱讀目前職缺，只輸入數量；不要在這裡貼上任何文件或個人資料。",
        "market_label": "格式情境",
        "market_options": {
            "not-checked": "尚未檢查",
            "us-resume": "美式 Resume",
            "uk-cv": "英式 CV",
            "europass": "Europass CV",
            "other": "其他市場或雇主指定格式",
        },
        "requirements_label": "已清點的明確要求",
        "evidence_label": "有真實證據支持的要求",
        "bullets_label": "已清點的經歷要點",
        "outcomes_label": "含已驗證成果的要點",
        "experience_label": "已有經歷區段",
        "skills_label": "已有技能區段",
        "education_label": "已有教育區段",
        "layout_label": "匯出文字與版面檢查",
        "layout_options": {
            "not-checked": "尚未檢查",
            "selectable-simple": "文字可選取且版面單純",
            "needs-review": "仍需檢查或版面複雜",
        },
        "update": "更新私密檢查表",
        "invalid_input": "請輸入 0 到 100 的整數。",
        "relation_invalid": "證據支持的要求不可超過全部要求；含成果的要點不可超過全部經歷要點。",
        "result_requirements": "有真實證據支持的要求",
        "result_outcomes": "含已驗證成果的要點",
        "result_sections": "已有的標準區段",
        "result_layout": "文字與版面檢查",
        "result_plan": "下一輪檢查順序",
        "next_steps": (
            "只在本頁之外清點目前職缺明確列出的要求。",
            "把每項支持要求連到你能說明的真實證據；絕不虛構經驗。",
            "只有成果已核實時才加到要點；絕不捏造數字。",
            "使用清楚區段標題，並檢查匯出檔的文字可選取性與單純閱讀順序。",
            "優先遵循雇主目前指示及目標市場的官方格式指南。",
        ),
        "boundary_title": "這些計數無法證明什麼",
        "boundary_text": "計數或比例無法顯示雇主 ATS 是否成功解析、如何排名或為何淘汰履歷，也無法預測招募人員判斷、面試或錄取。雇主、職務與系統都不同；本工具不套用任何目標門檻。",
        "sources_title": "任何選用 App 之前，先看官方履歷指南",
        "sources_intro": "請優先遵循雇主目前指示；以下官方公開資料提供各市場格式與客製方向，不會揭露雇主的 ATS 公式。",
        "source_labels": (
            "美國勞工部：Resume Essentials",
            "英國 National Careers Service：如何撰寫 CV",
            "Europass：建立 Europass CV",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": "只用有界、非敏感的自行計數與狀態建立透明履歷證據檢查表；不接收履歷、職缺、姓名、聯絡資料、公司、日期、檔案或帳號，也不產生 ATS 分數、解析結果、排名、錄取機率或建議。",
        "app_title": "需要選用的裝置端履歷工作流程？",
        "app_text": "CV Desk 是選用工具；目前 App Store 頁面說明包含裝置端 ATS 估算、範本、PDF 與 DOCX 匯出、免費建立與預覽，以及免訂閱、免帳號、不上傳、無浮水印的一次性解鎖。ATS 表現與雇主決策各異，請核對目前商店頁與雇主指示；本規劃器不需 App 也能使用。",
        "app_cta": "在 App Store 查看 CV Desk",
        "faq_title": "履歷證據覆蓋常見問題",
        "faq": (
            ("這個網頁會接收我的履歷或職缺嗎？", "不會。它只接收有界計數、布林選項與格式狀態。"),
            ("證據比例是 ATS 分數嗎？", "不是。它只把自行回報的支持數量除以總數，沒有目標或排名。"),
            ("某項要求無法提出證據怎麼辦？", "不要虛構經驗或關鍵字；維持未支持，或只在真實且相關時補上證據。"),
            ("每項成果都一定要有數字嗎？", "不用。只有數字正確且能說明時才使用；具體、真實的質性成果也可採用。"),
        ),
        "footer": "只做私密自行計數 · 不接收文件 · 無 ATS 分數 · 不預測錄取",
        "index_title": "私密履歷證據覆蓋規劃器",
        "index_description": "不貼上履歷、職缺或個人資料，清點真實證據並檢查標準區段；不產生 ATS 分數。",
    },
    "zh-Hans": {
        "title": "私密简历证据覆盖规划器｜不上传的 ATS 准备",
        "description": "只计算有真实证据支持的职位要求并检查简历区段；不粘贴职位、简历、姓名、公司或联系方式。",
        "tools": "免费工具",
        "switch": "English",
        "eyebrow": "免费 · 不接收简历文字 · 不生成 ATS 分数",
        "heading": "私密简历证据覆盖规划器",
        "lead": "只输入你在本页之外自行清点的数量，找出仍缺真实证据的明确要求；这不是 ATS 解析、排名或录用预测。",
        "badges": (
            "不接收简历或职位文字",
            "不接收姓名、联系方式或公司",
            "不接收文件、不上传、免账号",
            "无分数、门槛或录用预测",
        ),
        "planner": "只记录非敏感的自行计数",
        "planner_intro": "请在本页之外阅读当前职位，只输入数量；不要在这里粘贴任何文件或个人资料。",
        "market_label": "格式情境",
        "market_options": {
            "not-checked": "尚未检查",
            "us-resume": "美式 Resume",
            "uk-cv": "英式 CV",
            "europass": "Europass CV",
            "other": "其他市场或雇主指定格式",
        },
        "requirements_label": "已清点的明确要求",
        "evidence_label": "有真实证据支持的要求",
        "bullets_label": "已清点的经历要点",
        "outcomes_label": "含已验证成果的要点",
        "experience_label": "已有经历区段",
        "skills_label": "已有技能区段",
        "education_label": "已有教育区段",
        "layout_label": "导出文字与版面检查",
        "layout_options": {
            "not-checked": "尚未检查",
            "selectable-simple": "文字可选择且版面简单",
            "needs-review": "仍需检查或版面复杂",
        },
        "update": "更新私密检查表",
        "invalid_input": "请输入 0 到 100 的整数。",
        "relation_invalid": "证据支持的要求不可超过全部要求；含成果的要点不可超过全部经历要点。",
        "result_requirements": "有真实证据支持的要求",
        "result_outcomes": "含已验证成果的要点",
        "result_sections": "已有的标准区段",
        "result_layout": "文字与版面检查",
        "result_plan": "下一轮检查顺序",
        "next_steps": (
            "只在本页之外清点当前职位明确列出的要求。",
            "把每项支持要求连到你能说明的真实证据；绝不虚构经历。",
            "只有成果已核实时才加到要点；绝不捏造数字。",
            "使用清楚区段标题，并检查导出文件的文字可选择性与简单阅读顺序。",
            "优先遵循雇主当前指示及目标市场的官方格式指南。",
        ),
        "boundary_title": "这些计数无法证明什么",
        "boundary_text": "计数或比例无法显示雇主 ATS 是否成功解析、如何排名或为何淘汰简历，也无法预测招聘人员判断、面试或录用。雇主、职位与系统都不同；本工具不套用任何目标门槛。",
        "sources_title": "任何可选 App 之前，先看官方简历指南",
        "sources_intro": "请优先遵循雇主当前指示；以下官方公开资料提供各市场格式与定制方向，不会揭露雇主的 ATS 公式。",
        "source_labels": (
            "美国劳工部：Resume Essentials",
            "英国 National Careers Service：如何撰写 CV",
            "Europass：创建 Europass CV",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览（规范可能变化）",
        "webmcp_description": "只用有界、非敏感的自行计数与状态建立透明简历证据检查表；不接收简历、职位、姓名、联系方式、公司、日期、文件或账号，也不生成 ATS 分数、解析结果、排名、录用概率或建议。",
        "app_title": "需要可选的设备端简历工作流程？",
        "app_text": "CV Desk 是可选工具；当前 App Store 页面说明包含设备端 ATS 估算、模板、PDF 与 DOCX 导出、免费创建与预览，以及免订阅、免账号、不上传、无水印的一次性解锁。ATS 表现与雇主决策各异，请核对当前商店页与雇主指示；本规划器不需 App 也能使用。",
        "app_cta": "在 App Store 查看 CV Desk",
        "faq_title": "简历证据覆盖常见问题",
        "faq": (
            ("这个网页会接收我的简历或职位吗？", "不会。它只接收有界计数、布尔选项与格式状态。"),
            ("证据比例是 ATS 分数吗？", "不是。它只把自行报告的支持数量除以总数，没有目标或排名。"),
            ("某项要求无法提出证据怎么办？", "不要虚构经历或关键词；保持未支持，或只在真实且相关时补上证据。"),
            ("每项成果都一定要有数字吗？", "不用。只有数字正确且能说明时才使用；具体、真实的定性成果也可采用。"),
        ),
        "footer": "只做私密自行计数 · 不接收文件 · 无 ATS 分数 · 不预测录用",
        "index_title": "私密简历证据覆盖规划器",
        "index_description": "不粘贴简历、职位或个人资料，清点真实证据并检查标准区段；不生成 ATS 分数。",
    },
}

STYLE = r"""
:root{--ink:#21314a;--muted:#67738a;--line:#dfe5f0;--paper:#fff;--bg:#f3f6fb;--deep:#3949a3;--violet:#7566c8;--soft:#edf0ff;--warn:#fff6d8;--shadow:0 22px 60px rgba(47,57,108,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e9edf7 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;line-height:1.62}
a{color:var(--deep)}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cad2e4;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--violet));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(57,73,163,.2)}
.results{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #d7dcfa;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#5360a8;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#3b467a;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fff,#edf0ff)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#f4f5ff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("resume-evidence-config").textContent);
  const form = document.getElementById("resume-evidence-planner");
  const fields = {
    market_format: document.getElementById("market-format"),
    listed_requirements: document.getElementById("listed-requirements"),
    requirements_with_truthful_evidence: document.getElementById("evidence-requirements"),
    experience_bullets: document.getElementById("experience-bullets"),
    bullets_with_verified_outcomes: document.getElementById("outcome-bullets"),
    has_experience_section: document.getElementById("has-experience"),
    has_skills_section: document.getElementById("has-skills"),
    has_education_section: document.getElementById("has-education"),
    text_layout_review: document.getElementById("layout-review")
  };
  const output = {
    requirements: document.getElementById("result-requirements"),
    outcomes: document.getElementById("result-outcomes"),
    sections: document.getElementById("result-sections"),
    layout: document.getElementById("result-layout"),
    plan: document.getElementById("result-plan")
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

  function plan(input) {
    const market = enumValue(input, "market_format");
    const listed = integerValue(input, "listed_requirements");
    const evidence = integerValue(input, "requirements_with_truthful_evidence");
    const bullets = integerValue(input, "experience_bullets");
    const outcomes = integerValue(input, "bullets_with_verified_outcomes");
    const experienceSection = booleanValue(input, "has_experience_section");
    const skillsSection = booleanValue(input, "has_skills_section");
    const educationSection = booleanValue(input, "has_education_section");
    const layout = enumValue(input, "text_layout_review");
    if (evidence > listed) {
      throw new RangeError(
        "requirements_with_truthful_evidence cannot exceed listed_requirements.");
    }
    if (outcomes > bullets) {
      throw new RangeError(
        "bullets_with_verified_outcomes cannot exceed experience_bullets.");
    }
    const sections = {
      experience: experienceSection,
      skills: skillsSection,
      education: educationSection
    };
    const presentSections = Object.values(sections).filter(Boolean).length;
    return {
      selected_inputs: {
        market_format: market,
        market_format_label: config.labels.market[market],
        listed_requirements: listed,
        requirements_with_truthful_evidence: evidence,
        experience_bullets: bullets,
        bullets_with_verified_outcomes: outcomes,
        standard_sections: sections,
        text_layout_review: layout,
        text_layout_review_label: config.labels.layout[layout]
      },
      self_counted_evidence_coverage: {
        requirement_evidence: {
          supported_count: evidence,
          listed_count: listed,
          ratio: listed === 0 ? null : evidence / listed
        },
        outcome_evidence: {
          verified_outcome_bullets: outcomes,
          experience_bullets: bullets,
          ratio: bullets === 0 ? null : outcomes / bullets
        },
        standard_sections_present: presentSections,
        standard_sections_checked: 3,
        no_target_threshold_applied: true,
        is_not_ats_score: true
      },
      evidence_gaps_for_manual_review: {
        listed_requirements_without_truthful_evidence: listed - evidence,
        experience_bullets_without_verified_outcome: bullets - outcomes
      },
      next_review_steps: config.nextSteps,
      boundary: config.boundary
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
    output.requirements.textContent = "—";
    output.outcomes.textContent = "—";
    output.sections.textContent = "—";
    output.layout.textContent = "—";
    output.plan.textContent = message;
  }

  function render() {
    let result;
    try {
      result = plan({
        market_format: fields.market_format.value,
        listed_requirements: humanInteger(
          fields.listed_requirements, "listed_requirements"),
        requirements_with_truthful_evidence: humanInteger(
          fields.requirements_with_truthful_evidence,
          "requirements_with_truthful_evidence"),
        experience_bullets: humanInteger(
          fields.experience_bullets, "experience_bullets"),
        bullets_with_verified_outcomes: humanInteger(
          fields.bullets_with_verified_outcomes,
          "bullets_with_verified_outcomes"),
        has_experience_section: fields.has_experience_section.checked,
        has_skills_section: fields.has_skills_section.checked,
        has_education_section: fields.has_education_section.checked,
        text_layout_review: fields.text_layout_review.value
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        const relationError =
          fields.requirements_with_truthful_evidence.valueAsNumber >
            fields.listed_requirements.valueAsNumber ||
          fields.bullets_with_verified_outcomes.valueAsNumber >
            fields.experience_bullets.valueAsNumber;
        renderInvalid(relationError ? config.relationInvalid : config.invalidInput);
        return;
      }
      throw error;
    }
    const coverage = result.self_counted_evidence_coverage;
    output.requirements.textContent =
      `${coverage.requirement_evidence.supported_count} / ` +
      `${coverage.requirement_evidence.listed_count}`;
    output.outcomes.textContent =
      `${coverage.outcome_evidence.verified_outcome_bullets} / ` +
      `${coverage.outcome_evidence.experience_bullets}`;
    output.sections.textContent =
      `${coverage.standard_sections_present} / ` +
      `${coverage.standard_sections_checked}`;
    output.layout.textContent =
      result.selected_inputs.text_layout_review_label;
    output.plan.textContent = result.next_review_steps.join(" ");
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_resume_evidence_coverage",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_resume_evidence_coverage_plan",
          resume_job_post_personal_data_files_accounts_not_received: true,
          no_ats_parse_score_ranking_or_hiring_prediction: true,
          plan,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_cv_desk = config.optionalApp;
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
    count = {"type": "integer", "minimum": 0, "maximum": 100}
    return {
        "type": "object",
        "properties": {
            "market_format": {
                "type": "string",
                "enum": list(MARKET_FORMATS),
                "description": t["market_label"],
            },
            "listed_requirements": {
                **count,
                "description": t["requirements_label"],
            },
            "requirements_with_truthful_evidence": {
                **count,
                "description": (
                    f'{t["evidence_label"]}. {t["relation_invalid"]}'
                ),
            },
            "experience_bullets": {
                **count,
                "description": t["bullets_label"],
            },
            "bullets_with_verified_outcomes": {
                **count,
                "description": (
                    f'{t["outcomes_label"]}. {t["relation_invalid"]}'
                ),
            },
            "has_experience_section": {
                "type": "boolean",
                "description": t["experience_label"],
            },
            "has_skills_section": {
                "type": "boolean",
                "description": t["skills_label"],
            },
            "has_education_section": {
                "type": "boolean",
                "description": t["education_label"],
            },
            "text_layout_review": {
                "type": "string",
                "enum": list(LAYOUT_STATUSES),
                "description": t["layout_label"],
            },
        },
        "required": [
            "market_format",
            "listed_requirements",
            "requirements_with_truthful_evidence",
            "experience_bullets",
            "bullets_with_verified_outcomes",
            "has_experience_section",
            "has_skills_section",
            "has_education_section",
            "text_layout_review",
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
    sources = (DOL_RESUME, UK_CV, EUROPASS_CV)
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
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
        appstore_url(APP_KEY, f"iag_resume_evidence_{locale.lower()}")
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
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "labels": {
            "market": t["market_options"],
            "layout": t["layout_options"],
        },
        "nextSteps": t["next_steps"],
        "boundary": t["boundary_text"],
        "invalidInput": t["invalid_input"],
        "relationInvalid": t["relation_invalid"],
        "toolDescription": t["webmcp_description"],
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
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [*t["badges"], t["boundary_text"]],
        "citation": list(sources),
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
{json_script(faq_schema)}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="resume-evidence-planner"><div class="controls">
<div class="field"><label for="market-format">{html.escape(t["market_label"])}</label><select id="market-format">{options(t["market_options"])}</select></div>
<div class="field"><label for="listed-requirements">{html.escape(t["requirements_label"])}</label><input id="listed-requirements" type="number" min="0" max="100" step="1" value="0" required></div>
<div class="field"><label for="evidence-requirements">{html.escape(t["evidence_label"])}</label><input id="evidence-requirements" type="number" min="0" max="100" step="1" value="0" required></div>
<div class="field"><label for="experience-bullets">{html.escape(t["bullets_label"])}</label><input id="experience-bullets" type="number" min="0" max="100" step="1" value="0" required></div>
<div class="field"><label for="outcome-bullets">{html.escape(t["outcomes_label"])}</label><input id="outcome-bullets" type="number" min="0" max="100" step="1" value="0" required></div>
<div class="field"><label for="layout-review">{html.escape(t["layout_label"])}</label><select id="layout-review">{options(t["layout_options"])}</select></div>
<label class="toggle"><input id="has-experience" type="checkbox">{html.escape(t["experience_label"])}</label>
<label class="toggle"><input id="has-skills" type="checkbox">{html.escape(t["skills_label"])}</label>
<label class="toggle"><input id="has-education" type="checkbox">{html.escape(t["education_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_requirements"])}</strong><span id="result-requirements"></span></div><div class="result"><strong>{html.escape(t["result_outcomes"])}</strong><span id="result-outcomes"></span></div><div class="result"><strong>{html.escape(t["result_sections"])}</strong><span id="result-sections"></span></div><div class="result"><strong>{html.escape(t["result_layout"])}</strong><span id="result-layout"></span></div></div>
<p class="note"><strong>{html.escape(t["result_plan"])}:</strong> <span id="result-plan"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["result_plan"])}</h2><ol>{checklist_items}</ol></article><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p>{html.escape(t["boundary_text"])}</p></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="resume-evidence-config">{config_json}</script>
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


def update_inbound_answer_labels(pages: Path = PAGES) -> int:
    escaped_slug = re.escape(SLUG)
    href_target = (
        rf'(?:"(?:[^"?#]*/)?{escaped_slug}\.html(?:[?#][^"]*)?"'
        rf"|'(?:[^'?#]*/)?{escaped_slug}\.html(?:[?#][^']*)?')"
    )
    anchor = re.compile(
        rf'(?P<open><a\b(?=[^>]*\shref\s*=\s*{href_target})[^>]*>)'
        rf'.*?(?P<close></a>)',
        re.IGNORECASE | re.DOTALL,
    )
    changed = 0
    answer_dirs = [(pages / "answers", "en")]
    answer_dirs.extend(
        (path, path.parent.name)
        for path in sorted(pages.glob("*/answers"))
    )
    for answers, locale in answer_dirs:
        if not answers.is_dir():
            continue
        replacement = html.escape(
            COPY.get(locale, COPY["en"])["heading"]
        )
        for path in sorted(answers.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            updated = anchor.sub(
                lambda match: (
                    f'{match.group("open")}{replacement}{match.group("close")}'
                ),
                text,
            )
            if write_text_if_changed(path, updated):
                changed += 1
    replacement = html.escape(COPY["en"]["heading"])
    for path in sorted(pages.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        updated = anchor.sub(
            lambda match: (
                f'{match.group("open")}{replacement}{match.group("close")}'
            ),
            text,
        )
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
    update_inbound_answer_labels(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"resume evidence planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
