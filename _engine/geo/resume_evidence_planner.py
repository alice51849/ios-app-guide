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
    "vi",
    "th",
    "id",
    "tr",
    "hi",
    "ms",
    "ru",
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
    "vi": {
        "title": "Công cụ rà soát độ phủ bằng chứng CV riêng tư | Chuẩn bị ATS, không tải lên",
        "description": "Đếm số yêu cầu công việc có bằng chứng trung thực và rà soát các mục CV, không dán tin tuyển dụng, CV, tên, công ty hay thông tin liên lạc.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Miễn phí · không nhận nội dung CV · không chấm điểm ATS",
        "heading": "Công cụ rà soát độ phủ bằng chứng CV riêng tư",
        "lead": "Dùng các con số bạn tự đếm bên ngoài trang này để thấy yêu cầu nào còn thiếu bằng chứng trung thực. Đây không phải phân tích ATS, xếp hạng hay dự đoán tuyển dụng.",
        "badges": ("Không nhận nội dung CV hay tin tuyển dụng", "Không tên, liên lạc hay công ty", "Không tệp, tải lên hay tài khoản", "Không điểm số, ngưỡng hay dự đoán tuyển dụng"),
        "planner": "Chỉ ghi các con số tự đếm không nhạy cảm",
        "planner_intro": "Đọc tin tuyển dụng hiện tại bên ngoài trang này. Chỉ nhập số đếm; đừng bao giờ dán tài liệu hay chi tiết cá nhân vào đây.",
        "market_label": "Ngữ cảnh định dạng",
        "market_options": {"not-checked": "Chưa kiểm tra", "us-resume": "Resume kiểu Mỹ", "uk-cv": "CV kiểu Anh", "europass": "CV Europass", "other": "Thị trường hoặc định dạng khác"},
        "requirements_label": "Số yêu cầu rõ ràng đã đếm",
        "evidence_label": "Số yêu cầu có bằng chứng trung thực",
        "bullets_label": "Số gạch đầu dòng kinh nghiệm đã đếm",
        "outcomes_label": "Số gạch đầu dòng có kết quả kiểm chứng",
        "experience_label": "Có mục Kinh nghiệm",
        "skills_label": "Có mục Kỹ năng",
        "education_label": "Có mục Học vấn",
        "layout_label": "Rà soát văn bản và bố cục file xuất",
        "layout_options": {"not-checked": "Chưa kiểm tra", "selectable-simple": "Chữ chọn được và bố cục đơn giản", "needs-review": "Cần xem lại hoặc bố cục phức tạp"},
        "update": "Cập nhật danh sách riêng tư",
        "invalid_input": "Nhập số nguyên từ 0 đến 100.",
        "relation_invalid": "Số yêu cầu có bằng chứng không thể vượt tổng số yêu cầu, và số gạch đầu dòng có kết quả kiểm chứng không thể vượt tổng số gạch đầu dòng.",
        "result_requirements": "Yêu cầu được hỗ trợ trung thực",
        "result_outcomes": "Gạch đầu dòng có kết quả kiểm chứng",
        "result_sections": "Các mục chuẩn hiện có",
        "result_layout": "Rà soát văn bản và bố cục",
        "result_plan": "Trình tự rà soát tiếp theo",
        "next_steps": (
            "Chỉ đếm các yêu cầu rõ ràng trong tin tuyển dụng hiện tại, bên ngoài trang này.",
            "Gắn mỗi yêu cầu được hỗ trợ với bằng chứng trung thực bạn giải thích được; đừng bao giờ bịa kinh nghiệm.",
            "Chỉ thêm kết quả vào gạch đầu dòng khi nó đã kiểm chứng; không bịa con số.",
            "Dùng tiêu đề mục rõ ràng và kiểm tra file xuất có chữ chọn được, thứ tự đọc đơn giản.",
            "Làm theo hướng dẫn hiện tại của nhà tuyển dụng và chuẩn định dạng chính thức của thị trường bạn.",
        ),
        "boundary_title": "Những con số này không chứng minh điều gì",
        "boundary_text": "Số đếm hay tỷ lệ không cho biết ATS của nhà tuyển dụng có phân tích, xếp hạng hay loại CV không, nhà tuyển dụng có đồng ý không, hay đơn ứng tuyển có dẫn đến phỏng vấn hoặc offer không. Mỗi công ty, vị trí và hệ thống đều khác. Không áp ngưỡng mục tiêu nào.",
        "sources_title": "Hướng dẫn CV chính thức trước mọi ứng dụng tùy chọn",
        "sources_intro": "Ưu tiên hướng dẫn hiện tại của nhà tuyển dụng. Các nguồn công khai chính thức này cung cấp cấu trúc theo thị trường; chúng không tiết lộ công thức ATS của bất kỳ công ty nào.",
        "source_labels": (
            "Bộ Lao động Hoa Kỳ: Resume Essentials",
            "National Careers Service (Anh): Cách viết CV",
            "Europass: Tạo CV Europass",
        ),
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP (có thể thay đổi)",
        "webmcp_description": "Xây danh sách kiểm tra độ phủ bằng chứng CV minh bạch từ các con số tự đếm không nhạy cảm và lựa chọn trạng thái có giới hạn. Không bao giờ nhận nội dung CV, tin tuyển dụng, tên, liên lạc, công ty, ngày tháng, tệp hay tài khoản; không tạo điểm ATS, kết quả phân tích, xếp hạng, xác suất tuyển dụng hay khuyến nghị.",
        "app_title": "Muốn quy trình làm CV trên thiết bị (tùy chọn)?",
        "app_text": "CV Desk là tùy chọn. Trang App Store hiện tại mô tả ước tính ATS trên thiết bị, mẫu CV, xuất PDF và DOCX, dựng và xem trước miễn phí, mở khóa một lần không đăng ký, không tài khoản, không tải lên, không watermark. Hành vi ATS và quyết định tuyển dụng luôn khác nhau; hãy kiểm tra trang hiện tại và hướng dẫn của nhà tuyển dụng. Công cụ này hoạt động không cần ứng dụng.",
        "app_cta": "Xem CV Desk trên App Store",
        "faq_title": "Câu hỏi về độ phủ bằng chứng CV",
        "faq": (
            ("Trang này có nhận CV hay mô tả công việc của tôi không?", "Không. Nó chỉ nhận số đếm có giới hạn, giá trị đúng/sai và lựa chọn trạng thái định dạng."),
            ("Tỷ lệ bằng chứng có phải điểm ATS không?", "Không. Đó chỉ là số yêu cầu được hỗ trợ chia cho tổng số bạn đếm, không có ngưỡng hay xếp hạng."),
            ("Nếu tôi không hỗ trợ được một yêu cầu thì sao?", "Đừng bịa kinh nghiệm hay từ khóa. Cứ để trống, hoặc chỉ thêm bằng chứng khi nó trung thực và liên quan."),
            ("Mọi kết quả có bắt buộc là con số không?", "Không. Chỉ dùng số khi nó chính xác và bảo vệ được; một kết quả định tính cụ thể, trung thực cũng hữu ích."),
        ),
        "footer": "Chỉ tự đếm riêng tư · không nhận tài liệu · không điểm ATS · không dự đoán tuyển dụng",
        "index_title": "Công cụ rà soát độ phủ bằng chứng CV riêng tư",
        "index_description": "Đếm bằng chứng trung thực và rà soát các mục chuẩn, không dán CV, tin tuyển dụng hay thông tin cá nhân, không điểm ATS.",
    },
    "th": {
        "title": "เครื่องมือตรวจความครอบคลุมหลักฐานเรซูเม่แบบส่วนตัว | เตรียม ATS ไม่อัปโหลด",
        "description": "นับข้อกำหนดงานที่มีหลักฐานจริงรองรับ และตรวจส่วนต่าง ๆ ของเรซูเม่ โดยไม่วางประกาศงาน เรซูเม่ ชื่อ นายจ้าง หรือข้อมูลติดต่อ",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "ฟรี · ไม่รับข้อความเรซูเม่ · ไม่มีคะแนน ATS",
        "heading": "เครื่องมือตรวจความครอบคลุมหลักฐานเรซูเม่แบบส่วนตัว",
        "lead": "ใช้ตัวเลขที่คุณนับเองนอกหน้านี้ เพื่อดูว่าข้อกำหนดใดยังขาดหลักฐานจริงรองรับ นี่ไม่ใช่การวิเคราะห์ ATS การจัดอันดับ หรือการทำนายการจ้างงาน",
        "badges": ("ไม่รับข้อความเรซูเม่หรือประกาศงาน", "ไม่มีชื่อ ข้อมูลติดต่อ หรือนายจ้าง", "ไม่มีไฟล์ อัปโหลด หรือบัญชี", "ไม่มีคะแนน เกณฑ์ หรือการทำนายการจ้าง"),
        "planner": "บันทึกเฉพาะตัวเลขนับเองที่ไม่อ่อนไหว",
        "planner_intro": "อ่านประกาศงานปัจจุบันนอกหน้านี้ กรอกเฉพาะจำนวน อย่าวางเอกสารหรือรายละเอียดส่วนตัวที่นี่",
        "market_label": "บริบทรูปแบบ",
        "market_options": {"not-checked": "ยังไม่ตรวจ", "us-resume": "เรซูเม่แบบสหรัฐฯ", "uk-cv": "CV แบบอังกฤษ", "europass": "CV Europass", "other": "ตลาดหรือรูปแบบอื่น"},
        "requirements_label": "จำนวนข้อกำหนดชัดเจนที่นับได้",
        "evidence_label": "ข้อกำหนดที่มีหลักฐานจริงรองรับ",
        "bullets_label": "จำนวนหัวข้อย่อยประสบการณ์ที่นับได้",
        "outcomes_label": "หัวข้อย่อยที่มีผลลัพธ์ยืนยันแล้ว",
        "experience_label": "มีส่วนประสบการณ์",
        "skills_label": "มีส่วนทักษะ",
        "education_label": "มีส่วนการศึกษา",
        "layout_label": "ตรวจข้อความและเลย์เอาต์ไฟล์ส่งออก",
        "layout_options": {"not-checked": "ยังไม่ตรวจ", "selectable-simple": "ข้อความเลือกได้และเลย์เอาต์เรียบง่าย", "needs-review": "ต้องตรวจเพิ่มหรือเลย์เอาต์ซับซ้อน"},
        "update": "อัปเดตเช็กลิสต์ส่วนตัว",
        "invalid_input": "กรอกจำนวนเต็มตั้งแต่ 0 ถึง 100",
        "relation_invalid": "ข้อกำหนดที่มีหลักฐานต้องไม่เกินข้อกำหนดทั้งหมด และหัวข้อย่อยที่มีผลลัพธ์ยืนยันต้องไม่เกินหัวข้อย่อยทั้งหมด",
        "result_requirements": "ข้อกำหนดที่รองรับด้วยความจริง",
        "result_outcomes": "หัวข้อย่อยที่มีผลลัพธ์ยืนยัน",
        "result_sections": "ส่วนมาตรฐานที่มี",
        "result_layout": "การตรวจข้อความและเลย์เอาต์",
        "result_plan": "ลำดับการตรวจถัดไป",
        "next_steps": (
            "นับเฉพาะข้อกำหนดชัดเจนจากประกาศงานปัจจุบัน นอกหน้านี้",
            "เชื่อมข้อกำหนดที่รองรับกับหลักฐานจริงที่คุณอธิบายได้ อย่าแต่งประสบการณ์",
            "ใส่ผลลัพธ์ในหัวข้อย่อยเมื่อยืนยันแล้วเท่านั้น อย่าแต่งตัวเลข",
            "ใช้หัวข้อส่วนที่ชัดเจน และตรวจไฟล์ส่งออกว่าเลือกข้อความได้ ลำดับการอ่านเรียบง่าย",
            "ทำตามคำแนะนำปัจจุบันของนายจ้าง และแนวทางรูปแบบทางการของตลาดคุณ",
        ),
        "boundary_title": "ตัวเลขเหล่านี้พิสูจน์อะไรไม่ได้",
        "boundary_text": "จำนวนหรืออัตราส่วนบอกไม่ได้ว่า ATS ของนายจ้างแยกวิเคราะห์ จัดอันดับ หรือปฏิเสธเรซูเม่หรือไม่ ผู้สรรหาจะเห็นด้วยหรือไม่ หรือใบสมัครจะนำไปสู่การสัมภาษณ์หรือข้อเสนอหรือไม่ นายจ้าง ตำแหน่ง และระบบต่างกัน ไม่มีเกณฑ์เป้าหมายใด ๆ",
        "sources_title": "แนวทางเรซูเม่ทางการก่อนใช้แอปเสริมใด ๆ",
        "sources_intro": "ยึดคำแนะนำปัจจุบันของนายจ้างก่อน แหล่งข้อมูลสาธารณะทางการเหล่านี้ให้โครงสร้างตามตลาด ไม่ได้เปิดเผยสูตร ATS ของนายจ้างใด",
        "source_labels": (
            "กระทรวงแรงงานสหรัฐฯ: Resume Essentials",
            "National Careers Service (สหราชอาณาจักร): วิธีเขียน CV",
            "Europass: สร้าง CV Europass",
        ),
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP (อาจเปลี่ยนแปลง)",
        "webmcp_description": "สร้างเช็กลิสต์ความครอบคลุมหลักฐานเรซูเม่แบบโปร่งใสจากตัวเลขนับเองที่ไม่อ่อนไหวและตัวเลือกสถานะแบบมีขอบเขต ไม่รับข้อความเรซูเม่ ประกาศงาน ชื่อ ข้อมูลติดต่อ นายจ้าง วันที่ ไฟล์ หรือบัญชี ไม่สร้างคะแนน ATS ผลวิเคราะห์ อันดับ ความน่าจะเป็นการจ้าง หรือคำแนะนำ",
        "app_title": "อยากได้เวิร์กโฟลว์เรซูเม่บนอุปกรณ์ (ตัวเลือกเสริม)?",
        "app_text": "CV Desk เป็นตัวเลือกเสริม หน้า App Store ปัจจุบันอธิบายการประเมิน ATS บนอุปกรณ์ เทมเพลต ส่งออก PDF และ DOCX สร้างและพรีวิวฟรี ปลดล็อกครั้งเดียว ไม่มีสมัครสมาชิก บัญชี อัปโหลด หรือลายน้ำ พฤติกรรม ATS และการตัดสินใจของนายจ้างแตกต่างกัน โปรดตรวจหน้าปัจจุบันและคำแนะนำของนายจ้าง เครื่องมือนี้ใช้ได้โดยไม่ต้องมีแอป",
        "app_cta": "ดู CV Desk บน App Store",
        "faq_title": "คำถามเรื่องความครอบคลุมหลักฐานเรซูเม่",
        "faq": (
            ("หน้านี้รับเรซูเม่หรือรายละเอียดงานของฉันไหม?", "ไม่ มันรับเฉพาะจำนวนแบบมีขอบเขต ค่าจริง/เท็จ และตัวเลือกสถานะรูปแบบ"),
            ("อัตราส่วนหลักฐานคือคะแนน ATS ไหม?", "ไม่ มันคือจำนวนที่รองรับหารด้วยจำนวนทั้งหมดที่คุณนับ ไม่มีเป้าหมายหรืออันดับ"),
            ("ถ้ารองรับข้อกำหนดหนึ่งไม่ได้ล่ะ?", "อย่าแต่งประสบการณ์หรือคีย์เวิร์ด ปล่อยว่างไว้ หรือเพิ่มหลักฐานเมื่อจริงและเกี่ยวข้องเท่านั้น"),
            ("ผลลัพธ์ทุกข้อต้องเป็นตัวเลขไหม?", "ไม่ ใช้ตัวเลขเมื่อถูกต้องและยืนยันได้เท่านั้น ผลลัพธ์เชิงคุณภาพที่จริงและเฉพาะเจาะจงก็มีประโยชน์"),
        ),
        "footer": "นับเองแบบส่วนตัวเท่านั้น · ไม่รับเอกสาร · ไม่มีคะแนน ATS · ไม่ทำนายการจ้าง",
        "index_title": "เครื่องมือตรวจความครอบคลุมหลักฐานเรซูเม่แบบส่วนตัว",
        "index_description": "นับหลักฐานจริงและตรวจส่วนมาตรฐาน โดยไม่วางเรซูเม่ ประกาศงาน หรือข้อมูลส่วนตัว และไม่มีคะแนน ATS",
    },
    "id": {
        "title": "Perencana Cakupan Bukti Resume Privat | Persiapan ATS, Tanpa Unggah",
        "description": "Hitung persyaratan kerja yang didukung bukti jujur dan tinjau bagian resume tanpa menempel iklan lowongan, resume, nama, perusahaan, atau kontak.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Gratis · tanpa teks resume · tanpa skor ATS",
        "heading": "Perencana cakupan bukti resume privat",
        "lead": "Gunakan hitungan yang Anda buat di luar halaman ini untuk melihat persyaratan mana yang masih butuh dukungan jujur. Ini bukan analisis ATS, pemeringkatan, atau prediksi perekrutan.",
        "badges": ("Tanpa teks resume atau lowongan", "Tanpa nama, kontak, atau perusahaan", "Tanpa file, unggahan, atau akun", "Tanpa skor, ambang, atau prediksi perekrutan"),
        "planner": "Catat hanya hitungan mandiri yang tidak sensitif",
        "planner_intro": "Baca lowongan saat ini di luar halaman ini. Masukkan hanya angka; jangan pernah menempel dokumen atau detail pribadi di sini.",
        "market_label": "Konteks format",
        "market_options": {"not-checked": "Belum diperiksa", "us-resume": "Resume gaya AS", "uk-cv": "CV gaya Inggris", "europass": "CV Europass", "other": "Pasar atau format lain"},
        "requirements_label": "Persyaratan eksplisit yang dihitung",
        "evidence_label": "Persyaratan dengan bukti jujur",
        "bullets_label": "Butir pengalaman yang dihitung",
        "outcomes_label": "Butir dengan hasil terverifikasi",
        "experience_label": "Ada bagian Pengalaman",
        "skills_label": "Ada bagian Keahlian",
        "education_label": "Ada bagian Pendidikan",
        "layout_label": "Tinjauan teks dan tata letak file ekspor",
        "layout_options": {"not-checked": "Belum diperiksa", "selectable-simple": "Teks bisa dipilih dan tata letak sederhana", "needs-review": "Perlu ditinjau atau tata letak kompleks"},
        "update": "Perbarui daftar periksa privat",
        "invalid_input": "Masukkan bilangan bulat 0 sampai 100.",
        "relation_invalid": "Persyaratan yang didukung tidak boleh melebihi total persyaratan, dan butir dengan hasil terverifikasi tidak boleh melebihi total butir pengalaman.",
        "result_requirements": "Persyaratan yang didukung secara jujur",
        "result_outcomes": "Butir dengan hasil terverifikasi",
        "result_sections": "Bagian standar yang ada",
        "result_layout": "Tinjauan teks dan tata letak",
        "result_plan": "Urutan tinjauan berikutnya",
        "next_steps": (
            "Hitung hanya persyaratan eksplisit dari lowongan saat ini, di luar halaman ini.",
            "Kaitkan tiap persyaratan yang didukung dengan bukti jujur yang bisa Anda jelaskan; jangan pernah mengarang pengalaman.",
            "Tambahkan hasil pada butir hanya jika sudah terverifikasi; jangan mengarang angka.",
            "Gunakan judul bagian yang jelas dan periksa file ekspor: teks bisa dipilih, urutan baca sederhana.",
            "Ikuti instruksi terbaru pemberi kerja dan panduan format resmi pasar Anda.",
        ),
        "boundary_title": "Yang tidak dibuktikan hitungan ini",
        "boundary_text": "Hitungan atau rasio tidak menunjukkan apakah ATS pemberi kerja mengurai, memeringkat, atau menolak resume, apakah perekrut setuju, atau apakah lamaran berujung wawancara atau tawaran. Pemberi kerja, posisi, dan sistem berbeda-beda. Tidak ada ambang target yang diterapkan.",
        "sources_title": "Panduan resume resmi sebelum aplikasi opsional apa pun",
        "sources_intro": "Utamakan instruksi terbaru pemberi kerja. Sumber publik resmi ini memberi struktur per pasar; mereka tidak membuka formula ATS pemberi kerja mana pun.",
        "source_labels": (
            "Departemen Tenaga Kerja AS: Resume Essentials",
            "National Careers Service (Inggris): Cara menulis CV",
            "Europass: Buat CV Europass Anda",
        ),
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP (dapat berubah)",
        "webmcp_description": "Bangun daftar periksa cakupan bukti resume yang transparan dari hitungan mandiri tidak sensitif dan pilihan status terbatas. Tidak pernah menerima teks resume, teks lowongan, nama, kontak, perusahaan, tanggal, file, atau akun; tidak pernah menghasilkan skor ATS, hasil parsing, peringkat, kemungkinan direkrut, atau rekomendasi.",
        "app_title": "Ingin alur kerja resume di perangkat (opsional)?",
        "app_text": "CV Desk bersifat opsional. Halaman App Store terbarunya menjelaskan estimasi ATS di perangkat, templat, ekspor PDF dan DOCX, membangun dan pratinjau gratis, serta buka kunci sekali bayar tanpa langganan, akun, unggahan, atau watermark. Perilaku ATS dan keputusan pemberi kerja bervariasi; periksa halaman terbaru dan instruksi pemberi kerja. Perencana ini bekerja tanpa aplikasi tersebut.",
        "app_cta": "Lihat CV Desk di App Store",
        "faq_title": "Pertanyaan cakupan bukti resume",
        "faq": (
            ("Apakah halaman ini menerima resume atau deskripsi pekerjaan saya?", "Tidak. Ia hanya menerima hitungan terbatas, nilai benar/salah, dan pilihan status format."),
            ("Apakah rasio bukti adalah skor ATS?", "Tidak. Itu hanya jumlah yang didukung dibagi total yang Anda hitung, tanpa target atau peringkat."),
            ("Bagaimana jika saya tidak bisa mendukung satu persyaratan?", "Jangan mengarang pengalaman atau kata kunci. Biarkan tanpa dukungan, atau tambah bukti hanya jika jujur dan relevan."),
            ("Haruskah setiap hasil berupa angka?", "Tidak. Gunakan angka hanya jika akurat dan dapat dipertanggungjawabkan; hasil kualitatif yang spesifik dan jujur juga berguna."),
        ),
        "footer": "Hanya hitungan mandiri privat · tanpa dokumen · tanpa skor ATS · tanpa prediksi perekrutan",
        "index_title": "Perencana Cakupan Bukti Resume Privat",
        "index_description": "Hitung bukti jujur dan tinjau bagian standar tanpa menempel resume, lowongan, atau data pribadi, dan tanpa skor ATS.",
    },
    "tr": {
        "title": "Gizli Özgeçmiş Kanıt Kapsamı Planlayıcı | ATS Hazırlığı, Yükleme Yok",
        "description": "İlan, özgeçmiş, ad, işveren veya iletişim bilgisi yapıştırmadan; dürüst kanıtla desteklenen iş gereksinimlerini sayın ve özgeçmiş bölümlerini gözden geçirin.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Ücretsiz · özgeçmiş metni yok · ATS puanı yok",
        "heading": "Gizli özgeçmiş kanıt kapsamı planlayıcı",
        "lead": "Bu sayfanın dışında yaptığınız sayımları kullanarak hangi gereksinimlerin hâlâ dürüst destek gerektirdiğini görün. Bu bir ATS analizi, sıralama veya işe alım tahmini değildir.",
        "badges": ("Özgeçmiş veya ilan metni yok", "Ad, iletişim veya işveren yok", "Dosya, yükleme veya hesap yok", "Puan, eşik veya işe alım tahmini yok"),
        "planner": "Yalnızca hassas olmayan öz sayımları kaydedin",
        "planner_intro": "Güncel ilanı bu sayfanın dışında okuyun. Yalnızca sayıları girin; asla belge veya kişisel ayrıntı yapıştırmayın.",
        "market_label": "Biçim bağlamı",
        "market_options": {"not-checked": "Kontrol edilmedi", "us-resume": "ABD tarzı özgeçmiş", "uk-cv": "Birleşik Krallık CV", "europass": "Europass CV", "other": "Başka pazar veya biçim"},
        "requirements_label": "Sayılan açık gereksinimler",
        "evidence_label": "Dürüst kanıtla desteklenen gereksinimler",
        "bullets_label": "Sayılan deneyim maddeleri",
        "outcomes_label": "Doğrulanmış sonuçlu maddeler",
        "experience_label": "Deneyim bölümü var",
        "skills_label": "Beceriler bölümü var",
        "education_label": "Eğitim bölümü var",
        "layout_label": "Dışa aktarılan metin ve düzen incelemesi",
        "layout_options": {"not-checked": "Kontrol edilmedi", "selectable-simple": "Metin seçilebilir ve düzen sade", "needs-review": "İnceleme gerek veya düzen karmaşık"},
        "update": "Gizli kontrol listesini güncelle",
        "invalid_input": "0 ile 100 arasında tam sayılar girin.",
        "relation_invalid": "Desteklenen gereksinimler toplam gereksinimleri aşamaz; doğrulanmış sonuçlu maddeler toplam deneyim maddelerini aşamaz.",
        "result_requirements": "Dürüstçe desteklenen gereksinimler",
        "result_outcomes": "Doğrulanmış sonuçlu maddeler",
        "result_sections": "Mevcut standart bölümler",
        "result_layout": "Metin ve düzen incelemesi",
        "result_plan": "Sonraki inceleme sırası",
        "next_steps": (
            "Yalnızca güncel ilandaki açık gereksinimleri, bu sayfanın dışında sayın.",
            "Desteklenen her gereksinimi açıklayabileceğiniz dürüst kanıta bağlayın; asla deneyim uydurmayın.",
            "Bir maddeye sonucu yalnızca doğrulanmışsa ekleyin; sayı uydurmayın.",
            "Net bölüm başlıkları kullanın; dışa aktarılan dosyada metnin seçilebilir ve okuma sırasının sade olduğunu kontrol edin.",
            "İşverenin güncel talimatlarını ve pazarınızın resmî biçim rehberini izleyin.",
        ),
        "boundary_title": "Bu sayımların kanıtlamadıkları",
        "boundary_text": "Bir sayım veya oran; işverenin ATS'sinin özgeçmişi ayrıştırıp ayrıştırmadığını, sıralayıp sıralamadığını veya reddedip reddetmediğini, işe alım uzmanının aynı fikirde olup olmayacağını ya da başvurunun görüşme veya teklife dönüşüp dönüşmeyeceğini gösteremez. İşverenler, roller ve sistemler farklıdır. Hedef eşik uygulanmaz.",
        "sources_title": "İsteğe bağlı herhangi bir uygulamadan önce resmî özgeçmiş rehberliği",
        "sources_intro": "Önce işverenin güncel talimatlarını kullanın. Bu resmî kamu kaynakları pazara özgü yapı sunar; hiçbir işverenin ATS formülünü açıklamaz.",
        "source_labels": (
            "ABD Çalışma Bakanlığı: Resume Essentials",
            "National Careers Service (BK): CV nasıl yazılır",
            "Europass: Europass CV'nizi oluşturun",
        ),
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi (değişebilir)",
        "webmcp_description": "Sınırlı, hassas olmayan öz sayımlardan ve durum seçimlerinden şeffaf bir özgeçmiş kanıt-kapsamı kontrol listesi oluşturur. Özgeçmiş metni, ilan metni, ad, iletişim, işveren, tarih, dosya veya hesap asla almaz; ATS puanı, ayrıştırma sonucu, sıralama, işe alım olasılığı veya öneri üretmez.",
        "app_title": "Cihaz üzerinde bir özgeçmiş akışı ister misiniz (isteğe bağlı)?",
        "app_text": "CV Desk isteğe bağlıdır. Güncel App Store sayfası cihaz üzerinde ATS tahminini, şablonları, PDF ve DOCX dışa aktarımı, ücretsiz oluşturma ve önizlemeyi, abonelik, hesap, yükleme veya filigran olmadan tek seferlik kilit açmayı anlatır. ATS davranışı ve işveren kararları değişkendir; güncel sayfayı ve işveren talimatlarını doğrulayın. Bu planlayıcı uygulama olmadan da çalışır.",
        "app_cta": "App Store'da CV Desk'i görüntüle",
        "faq_title": "Özgeçmiş kanıt kapsamı soruları",
        "faq": (
            ("Bu sayfa özgeçmişimi veya iş tanımımı alıyor mu?", "Hayır. Yalnızca sınırlı sayımlar, doğru/yanlış değerleri ve biçim durumu seçimleri kabul eder."),
            ("Kanıt oranı bir ATS puanı mı?", "Hayır. Yalnızca desteklenen sayının saydığınız toplama bölümüdür; hedef veya sıralama yoktur."),
            ("Bir gereksinimi destekleyemezsem ne olur?", "Deneyim veya anahtar kelime uydurmayın. Onu desteksiz bırakın ya da kanıtı yalnızca dürüst ve ilgiliyse ekleyin."),
            ("Her sonuç bir sayı olmak zorunda mı?", "Hayır. Sayıyı yalnızca doğru ve savunulabilirse kullanın; belirli, dürüst nitel bir sonuç da yararlıdır."),
        ),
        "footer": "Yalnızca gizli öz sayımlar · belge yok · ATS puanı yok · işe alım tahmini yok",
        "index_title": "Gizli Özgeçmiş Kanıt Kapsamı Planlayıcı",
        "index_description": "Özgeçmiş, ilan veya kişisel bilgi yapıştırmadan ve ATS puanı olmadan dürüst kanıtı sayın, standart bölümleri gözden geçirin.",
    },
    "hi": {
        "title": "निजी रिज़्यूमे साक्ष्य-कवरेज योजनाकार | ATS तैयारी, कोई अपलोड नहीं",
        "description": "विज्ञापन, रिज़्यूमे, नाम, नियोक्ता या संपर्क जानकारी चिपकाए बिना; ईमानदार साक्ष्य-समर्थित नौकरी-आवश्यकताएँ गिनें और रिज़्यूमे अनुभाग समीक्षा करें।",
        "tools": "मुफ़्त उपकरण",
        "switch": "English",
        "eyebrow": "मुफ़्त · कोई रिज़्यूमे टेक्स्ट नहीं · कोई ATS स्कोर नहीं",
        "heading": "निजी रिज़्यूमे साक्ष्य-कवरेज योजनाकार",
        "lead": "इस पृष्ठ के बाहर की गई गिनतियों से देखें कि कौन-सी आवश्यकताएँ अब भी ईमानदार समर्थन माँगती हैं। यह ATS विश्लेषण, रैंकिंग या भर्ती-पूर्वानुमान नहीं है।",
        "badges": ("कोई रिज़्यूमे या विज्ञापन टेक्स्ट नहीं", "कोई नाम, संपर्क या नियोक्ता नहीं", "कोई फ़ाइल, अपलोड या खाता नहीं", "कोई स्कोर, सीमा या भर्ती-पूर्वानुमान नहीं"),
        "planner": "केवल असंवेदनशील स्व-गिनतियाँ दर्ज करें",
        "planner_intro": "वर्तमान विज्ञापन इस पृष्ठ के बाहर पढ़ें। केवल अंक दर्ज करें; कभी दस्तावेज़ या व्यक्तिगत विवरण न चिपकाएँ।",
        "market_label": "प्रारूप संदर्भ",
        "market_options": {"not-checked": "जाँचा नहीं", "us-resume": "अमेरिकी शैली रिज़्यूमे", "uk-cv": "यूके CV", "europass": "Europass CV", "other": "अन्य बाज़ार या प्रारूप"},
        "requirements_label": "गिनी गई स्पष्ट आवश्यकताएँ",
        "evidence_label": "ईमानदार साक्ष्य-समर्थित आवश्यकताएँ",
        "bullets_label": "गिने गए अनुभव बुलेट",
        "outcomes_label": "सत्यापित परिणाम वाले बुलेट",
        "experience_label": "अनुभव अनुभाग मौजूद",
        "skills_label": "कौशल अनुभाग मौजूद",
        "education_label": "शिक्षा अनुभाग मौजूद",
        "layout_label": "निर्यातित टेक्स्ट व लेआउट समीक्षा",
        "layout_options": {"not-checked": "जाँचा नहीं", "selectable-simple": "टेक्स्ट चयन-योग्य और लेआउट सरल", "needs-review": "समीक्षा चाहिए या लेआउट जटिल"},
        "update": "निजी जाँच-सूची अपडेट करें",
        "invalid_input": "0 से 100 के बीच पूर्णांक दर्ज करें।",
        "relation_invalid": "समर्थित आवश्यकताएँ कुल आवश्यकताओं से अधिक नहीं हो सकतीं; सत्यापित-परिणाम बुलेट कुल अनुभव बुलेटों से अधिक नहीं हो सकते।",
        "result_requirements": "ईमानदारी से समर्थित आवश्यकताएँ",
        "result_outcomes": "सत्यापित परिणाम वाले बुलेट",
        "result_sections": "मौजूद मानक अनुभाग",
        "result_layout": "टेक्स्ट व लेआउट समीक्षा",
        "result_plan": "अगला समीक्षा क्रम",
        "next_steps": (
            "केवल वर्तमान विज्ञापन की स्पष्ट आवश्यकताएँ, इस पृष्ठ के बाहर गिनें।",
            "हर समर्थित आवश्यकता को ऐसे ईमानदार साक्ष्य से जोड़ें जिसे आप समझा सकें; कभी अनुभव न गढ़ें।",
            "बुलेट में परिणाम केवल तभी जोड़ें जब सत्यापित हो; अंक न गढ़ें।",
            "स्पष्ट अनुभाग-शीर्षक उपयोग करें; निर्यातित फ़ाइल में टेक्स्ट चयन-योग्य और पठन-क्रम सरल है, जाँचें।",
            "नियोक्ता के वर्तमान निर्देश और अपने बाज़ार की आधिकारिक प्रारूप-मार्गदर्शिका का पालन करें।",
        ),
        "boundary_title": "ये गिनतियाँ क्या सिद्ध नहीं करतीं",
        "boundary_text": "कोई गिनती या अनुपात यह नहीं दिखा सकता कि नियोक्ता का ATS रिज़्यूमे पार्स, रैंक या अस्वीकार करेगा, भर्तीकर्ता सहमत होगा या आवेदन साक्षात्कार अथवा प्रस्ताव में बदलेगा। नियोक्ता, भूमिकाएँ और सिस्टम भिन्न हैं। कोई लक्ष्य-सीमा लागू नहीं होती।",
        "sources_title": "किसी वैकल्पिक ऐप से पहले आधिकारिक रिज़्यूमे मार्गदर्शन",
        "sources_intro": "पहले नियोक्ता के वर्तमान निर्देश देखें। ये आधिकारिक सार्वजनिक स्रोत बाज़ार-विशिष्ट संरचना देते हैं; कोई नियोक्ता ATS-सूत्र नहीं बताता।",
        "source_labels": (
            "अमेरिकी श्रम विभाग: Resume Essentials",
            "National Careers Service (यूके): CV कैसे लिखें",
            "Europass: अपना Europass CV बनाएँ",
        ),
        "webmcp_source": "Chrome WebMCP अनिवार्य API पूर्वावलोकन (परिवर्तनशील)",
        "webmcp_description": "सीमित, असंवेदनशील स्व-गिनतियों और स्थिति-चयनों से एक पारदर्शी रिज़्यूमे साक्ष्य-कवरेज जाँच-सूची बनाता है। रिज़्यूमे टेक्स्ट, विज्ञापन टेक्स्ट, नाम, संपर्क, नियोक्ता, तिथि, फ़ाइल या खाता कभी नहीं लेता; ATS स्कोर, पार्सिंग परिणाम, रैंकिंग, भर्ती-संभावना या सिफ़ारिश नहीं देता।",
        "app_title": "क्या ऑन-डिवाइस रिज़्यूमे फ़्लो चाहिए (वैकल्पिक)?",
        "app_text": "CV Desk वैकल्पिक है। वर्तमान App Store पृष्ठ ऑन-डिवाइस ATS अनुमान, टेम्पलेट, PDF व DOCX निर्यात, मुफ़्त निर्माण-पूर्वावलोकन और बिना सदस्यता, खाते, अपलोड या वॉटरमार्क के एक-बार अनलॉक बताता है। ATS व्यवहार और नियोक्ता निर्णय परिवर्तनशील हैं; वर्तमान पृष्ठ और नियोक्ता निर्देश सत्यापित करें। यह योजनाकार ऐप के बिना भी काम करता है।",
        "app_cta": "App Store पर CV Desk देखें",
        "faq_title": "रिज़्यूमे साक्ष्य-कवरेज प्रश्न",
        "faq": (
            ("क्या यह पृष्ठ मेरा रिज़्यूमे या जॉब विवरण लेता है?", "नहीं। यह केवल सीमित गिनतियाँ, हाँ/नहीं मान और प्रारूप-स्थिति चयन स्वीकार करता है।"),
            ("क्या साक्ष्य-अनुपात एक ATS स्कोर है?", "नहीं। यह केवल समर्थित संख्या को आपकी गिनी कुल संख्या से भाग है; कोई लक्ष्य या रैंकिंग नहीं।"),
            ("यदि मैं किसी आवश्यकता का समर्थन न कर सकूँ?", "अनुभव या कीवर्ड न गढ़ें। उसे असमर्थित छोड़ें या साक्ष्य तभी जोड़ें जब ईमानदार और प्रासंगिक हो।"),
            ("क्या हर परिणाम अंक होना चाहिए?", "नहीं। अंक तभी उपयोग करें जब सही और तर्कसंगत हो; विशिष्ट, ईमानदार गुणात्मक परिणाम भी उपयोगी है।"),
        ),
        "footer": "केवल निजी स्व-गिनतियाँ · कोई दस्तावेज़ नहीं · कोई ATS स्कोर नहीं · कोई भर्ती-पूर्वानुमान नहीं",
        "index_title": "निजी रिज़्यूमे साक्ष्य-कवरेज योजनाकार",
        "index_description": "रिज़्यूमे, विज्ञापन या व्यक्तिगत जानकारी चिपकाए बिना और बिना ATS स्कोर के ईमानदार साक्ष्य गिनें व मानक अनुभाग समीक्षा करें।",
    },
    "ms": {
        "title": "Perancang Liputan Bukti Resume Peribadi | Persediaan ATS, Tiada Muat Naik",
        "description": "Kira keperluan kerja yang disokong bukti jujur dan semak bahagian resume tanpa menampal iklan, resume, nama, majikan atau maklumat hubungan.",
        "tools": "Alat percuma",
        "switch": "English",
        "eyebrow": "Percuma · tiada teks resume · tiada skor ATS",
        "heading": "Perancang liputan bukti resume peribadi",
        "lead": "Guna kiraan yang anda buat di luar halaman ini untuk melihat keperluan mana yang masih memerlukan sokongan jujur. Ini bukan analisis ATS, penarafan atau ramalan pengambilan.",
        "badges": ("Tiada teks resume atau iklan", "Tiada nama, hubungan atau majikan", "Tiada fail, muat naik atau akaun", "Tiada skor, ambang atau ramalan pengambilan"),
        "planner": "Rekod kiraan kendiri tidak sensitif sahaja",
        "planner_intro": "Baca iklan semasa di luar halaman ini. Masukkan nombor sahaja; jangan sekali-kali menampal dokumen atau butiran peribadi.",
        "market_label": "Konteks format",
        "market_options": {"not-checked": "Belum diperiksa", "us-resume": "Resume gaya AS", "uk-cv": "CV UK", "europass": "CV Europass", "other": "Pasaran atau format lain"},
        "requirements_label": "Keperluan jelas yang dikira",
        "evidence_label": "Keperluan disokong bukti jujur",
        "bullets_label": "Bulet pengalaman yang dikira",
        "outcomes_label": "Bulet dengan hasil disahkan",
        "experience_label": "Bahagian pengalaman wujud",
        "skills_label": "Bahagian kemahiran wujud",
        "education_label": "Bahagian pendidikan wujud",
        "layout_label": "Semakan teks dan susun atur yang dieksport",
        "layout_options": {"not-checked": "Belum diperiksa", "selectable-simple": "Teks boleh dipilih dan susun atur ringkas", "needs-review": "Perlu semakan atau susun atur kompleks"},
        "update": "Kemas kini senarai semak peribadi",
        "invalid_input": "Masukkan integer antara 0 dan 100.",
        "relation_invalid": "Keperluan disokong tidak boleh melebihi jumlah keperluan; bulet hasil disahkan tidak boleh melebihi jumlah bulet pengalaman.",
        "result_requirements": "Keperluan disokong secara jujur",
        "result_outcomes": "Bulet dengan hasil disahkan",
        "result_sections": "Bahagian standard sedia ada",
        "result_layout": "Semakan teks dan susun atur",
        "result_plan": "Susunan semakan seterusnya",
        "next_steps": (
            "Kira hanya keperluan jelas dalam iklan semasa, di luar halaman ini.",
            "Kaitkan setiap keperluan disokong dengan bukti jujur yang boleh anda terangkan; jangan sekali-kali mereka pengalaman.",
            "Tambah hasil pada bulet hanya jika disahkan; jangan mereka nombor.",
            "Guna tajuk bahagian yang jelas; semak teks boleh dipilih dan urutan bacaan ringkas dalam fail yang dieksport.",
            "Ikut arahan semasa majikan dan panduan format rasmi pasaran anda.",
        ),
        "boundary_title": "Apa yang kiraan ini tidak buktikan",
        "boundary_text": "Kiraan atau nisbah tidak dapat menunjukkan sama ada ATS majikan akan menghurai, menaraf atau menolak resume, sama ada perekrut bersetuju, atau sama ada permohonan menjadi temu duga atau tawaran. Majikan, peranan dan sistem berbeza. Tiada ambang sasaran dikenakan.",
        "sources_title": "Panduan resume rasmi sebelum sebarang aplikasi pilihan",
        "sources_intro": "Guna arahan semasa majikan dahulu. Sumber awam rasmi ini memberi struktur khusus pasaran; tiada satu pun mendedahkan formula ATS mana-mana majikan.",
        "source_labels": (
            "Jabatan Buruh AS: Resume Essentials",
            "National Careers Service (UK): cara menulis CV",
            "Europass: bina CV Europass anda",
        ),
        "webmcp_source": "Pratonton API imperatif Chrome WebMCP (boleh berubah)",
        "webmcp_description": "Membina senarai semak liputan bukti resume yang telus daripada kiraan kendiri tidak sensitif dan pilihan status yang terhad. Tidak sekali-kali menerima teks resume, teks iklan, nama, hubungan, majikan, tarikh, fail atau akaun; tidak menghasilkan skor ATS, hasil penghuraian, penarafan, kebarangkalian pengambilan atau cadangan.",
        "app_title": "Mahukan aliran resume pada peranti (pilihan)?",
        "app_text": "CV Desk adalah pilihan. Halaman App Store semasa menerangkan anggaran ATS pada peranti, templat, eksport PDF dan DOCX, pembinaan dan pratonton percuma, serta buka kunci sekali tanpa langganan, akaun, muat naik atau tera air. Tingkah laku ATS dan keputusan majikan berubah-ubah; sahkan halaman semasa dan arahan majikan. Perancang ini berfungsi tanpa aplikasi.",
        "app_cta": "Lihat CV Desk di App Store",
        "faq_title": "Soalan liputan bukti resume",
        "faq": (
            ("Adakah halaman ini menerima resume atau huraian kerja saya?", "Tidak. Ia hanya menerima kiraan terhad, nilai ya/tidak dan pilihan status format."),
            ("Adakah nisbah bukti itu skor ATS?", "Tidak. Ia hanya bilangan disokong dibahagikan dengan jumlah yang anda kira; tiada sasaran atau penarafan."),
            ("Bagaimana jika saya tidak dapat menyokong satu keperluan?", "Jangan mereka pengalaman atau kata kunci. Biarkan ia tidak disokong atau tambah bukti hanya jika jujur dan relevan."),
            ("Adakah setiap hasil mesti berupa nombor?", "Tidak. Guna nombor hanya jika benar dan boleh dipertahankan; hasil kualitatif yang khusus dan jujur juga berguna."),
        ),
        "footer": "Kiraan kendiri peribadi sahaja · tiada dokumen · tiada skor ATS · tiada ramalan pengambilan",
        "index_title": "Perancang Liputan Bukti Resume Peribadi",
        "index_description": "Kira bukti jujur dan semak bahagian standard tanpa menampal resume, iklan atau maklumat peribadi dan tanpa skor ATS.",
    },
    "ru": {
        "title": "Приватный планировщик покрытия резюме доказательствами | Подготовка к ATS, без загрузок",
        "description": "Считайте требования вакансии, подкреплённые честными доказательствами, и проверяйте разделы резюме — не вставляя объявление, резюме, имя, работодателя или контакты.",
        "tools": "Бесплатные инструменты",
        "switch": "English",
        "eyebrow": "Бесплатно · без текста резюме · без ATS-балла",
        "heading": "Приватный планировщик покрытия резюме доказательствами",
        "lead": "По подсчётам, сделанным вне этой страницы, увидьте, какие требования всё ещё требуют честной поддержки. Это не анализ ATS, не рейтинг и не прогноз найма.",
        "badges": ("Без текста резюме и объявления", "Без имён, контактов и работодателей", "Без файлов, загрузок и аккаунтов", "Без баллов, порогов и прогнозов найма"),
        "planner": "Записывайте только нечувствительные самоподсчёты",
        "planner_intro": "Читайте актуальное объявление вне этой страницы. Вводите только числа; никогда не вставляйте документы или личные детали.",
        "market_label": "Контекст формата",
        "market_options": {"not-checked": "Не проверено", "us-resume": "Резюме в стиле США", "uk-cv": "CV Великобритании", "europass": "CV Europass", "other": "Другой рынок или формат"},
        "requirements_label": "Подсчитанные явные требования",
        "evidence_label": "Требования с честными доказательствами",
        "bullets_label": "Подсчитанные пункты опыта",
        "outcomes_label": "Пункты с проверенными результатами",
        "experience_label": "Раздел опыта есть",
        "skills_label": "Раздел навыков есть",
        "education_label": "Раздел образования есть",
        "layout_label": "Проверка экспортированного текста и вёрстки",
        "layout_options": {"not-checked": "Не проверено", "selectable-simple": "Текст выделяется, вёрстка простая", "needs-review": "Нужна проверка или вёрстка сложная"},
        "update": "Обновить приватный чек-лист",
        "invalid_input": "Введите целые числа от 0 до 100.",
        "relation_invalid": "Подкреплённые требования не могут превышать общее число требований; пункты с проверенными результатами — общее число пунктов опыта.",
        "result_requirements": "Честно подкреплённые требования",
        "result_outcomes": "Пункты с проверенными результатами",
        "result_sections": "Имеющиеся стандартные разделы",
        "result_layout": "Проверка текста и вёрстки",
        "result_plan": "Следующий порядок проверки",
        "next_steps": (
            "Считайте только явные требования актуального объявления — вне этой страницы.",
            "Связывайте каждое подкреплённое требование с честным доказательством, которое можете объяснить; никогда не выдумывайте опыт.",
            "Добавляйте результат в пункт только если он проверен; не выдумывайте числа.",
            "Используйте чёткие заголовки разделов; проверьте, что в экспортированном файле текст выделяется и порядок чтения прост.",
            "Следуйте актуальным инструкциям работодателя и официальному руководству по формату вашего рынка.",
        ),
        "boundary_title": "Чего эти подсчёты не доказывают",
        "boundary_text": "Подсчёт или доля не могут показать, распарсит ли, отранжирует ли или отклонит ли резюме ATS работодателя, согласится ли рекрутер и превратится ли отклик в собеседование или оффер. Работодатели, роли и системы различаются. Целевой порог не применяется.",
        "sources_title": "Официальные руководства по резюме до любого необязательного приложения",
        "sources_intro": "Сначала используйте актуальные инструкции работодателя. Эти официальные публичные источники дают структуру по рынкам; ни один не раскрывает формулу ATS какого-либо работодателя.",
        "source_labels": (
            "Министерство труда США: Resume Essentials",
            "National Careers Service (Великобритания): как написать CV",
            "Europass: создайте своё CV Europass",
        ),
        "webmcp_source": "Предварительная версия императивного API Chrome WebMCP (может меняться)",
        "webmcp_description": "Строит прозрачный чек-лист покрытия резюме доказательствами из ограниченных нечувствительных самоподсчётов и выборов статуса. Никогда не принимает текст резюме, текст объявления, имена, контакты, работодателей, даты, файлы или аккаунты; не выдаёт ATS-балл, результат парсинга, рейтинг, вероятность найма или рекомендации.",
        "app_title": "Нужен поток резюме на устройстве (по желанию)?",
        "app_text": "CV Desk — по желанию. Текущая страница App Store описывает оценку ATS на устройстве, шаблоны, экспорт PDF и DOCX, бесплатное создание и предпросмотр, разовую разблокировку без подписки, аккаунтов, загрузок и водяных знаков. Поведение ATS и решения работодателей изменчивы; проверьте актуальную страницу и инструкции работодателя. Планировщик работает и без приложения.",
        "app_cta": "Открыть CV Desk в App Store",
        "faq_title": "Вопросы о покрытии резюме доказательствами",
        "faq": (
            ("Принимает ли страница моё резюме или описание вакансии?", "Нет. Она принимает только ограниченные подсчёты, значения да/нет и выборы статуса формата."),
            ("Является ли доля доказательств ATS-баллом?", "Нет. Это лишь подкреплённое число, делённое на подсчитанный вами итог; без цели и рейтинга."),
            ("Что делать, если требование нечем подкрепить?", "Не выдумывайте опыт или ключевые слова. Оставьте его неподкреплённым или добавьте доказательство, только если оно честно и уместно."),
            ("Каждый результат должен быть числом?", "Нет. Используйте число, только если оно верно и защитимо; конкретный честный качественный результат тоже полезен."),
        ),
        "footer": "Только приватные самоподсчёты · без документов · без ATS-балла · без прогнозов найма",
        "index_title": "Приватный планировщик покрытия резюме доказательствами",
        "index_description": "Считайте честные доказательства и проверяйте стандартные разделы, не вставляя резюме, объявление или личные данные и без ATS-балла.",
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
            # Lite-generated hub (vi/th/id/tr/hi/ms/ru) uses a different
            # structure and is rebuilt by gen_tools_index_lite; skip.
            if '<div class="grid">' in text:
                return False
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
