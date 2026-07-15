#!/usr/bin/env python3
"""Generate a nine-locale, private daily checklist planning tool."""

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
SLUG = "private-daily-checklist-planner"
APP_KEY = "mochi"
APP_ID = "6785004775"
CONTENT_DATE = "2026-07-15"
APPLE_REMINDERS = (
    "https://support.apple.com/guide/iphone/"
    "get-started-with-reminders-iphc7880ecd6/ios"
)
APPLE_CREATE_REMINDERS = (
    "https://support.apple.com/guide/iphone/"
    "create-reminders-iph88463e18/ios"
)
APPLE_WATCH_REMINDERS = (
    "https://support.apple.com/guide/watch/"
    "make-and-view-lists-apdf10efb1bf/watchos"
)
APPLE_REMINDER_DETAILS = "https://support.apple.com/en-us/102484"
APPLE_LISTS_AND_TEMPLATES = "https://support.apple.com/en-us/119953"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

CONTEXTS = ("mixed-day", "work-study", "home", "errands", "routine")
AVAILABLE_MINUTES = (15, 30, 60, 120)
STARTING_STYLES = ("priority-first", "shortest-first", "due-time-first")
REPEAT_PATTERNS = ("none", "daily", "weekdays", "weekly")
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

COPY = {
    "en": {
        "title": "Private Daily Checklist Planner | No Task Text Required",
        "description": (
            "Turn a task count and available time into transparent checklist structure "
            "without entering task text, names, dates, accounts or calendar data."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · local math · no task text",
        "heading": "Private daily checklist planner",
        "lead": (
            "Choose only counts and planning preferences. The browser divides the available "
            "window transparently and returns a blank structure you can fill elsewhere."
        ),
        "badges": (
            "No task names or notes",
            "No account or calendar access",
            "No upload or storage",
            "No productivity promise",
        ),
        "planner": "Shape today's checklist",
        "planner_intro": (
            "The equal-share calculation is planning math, not a prediction of how long "
            "any real task will take."
        ),
        "context_label": "List context",
        "context_options": {
            "mixed-day": "Mixed day",
            "work-study": "Work or study",
            "home": "Home",
            "errands": "Errands",
            "routine": "Routine",
        },
        "minutes_label": "Available window",
        "minutes_options": {
            15: "15 minutes",
            30: "30 minutes",
            60: "60 minutes",
            120: "120 minutes",
        },
        "count_label": "Number of items",
        "style_label": "Starting style",
        "style_options": {
            "priority-first": "Most important first",
            "shortest-first": "Genuinely short items first",
            "due-time-first": "Real due times first",
        },
        "repeat_label": "Repeat pattern",
        "repeat_options": {
            "none": "No repeat",
            "daily": "Daily",
            "weekdays": "Weekdays",
            "weekly": "Weekly",
        },
        "carryover_label": "One or more items are carried over",
        "update": "Build blank checklist plan",
        "context_notes": {
            "mixed-day": (
                "Add a short context label when you transfer each item, so unrelated work "
                "does not look like one continuous block."
            ),
            "work-study": (
                "Separate outcome work from messages, filing and other administration when "
                "you fill the blank slots."
            ),
            "home": (
                "Separate items that must happen today from maintenance that can move without harm."
            ),
            "errands": (
                "When you fill the plan, group real stops by location or route before choosing order."
            ),
            "routine": (
                "Keep genuinely repeating actions separate from one-off items before setting a cadence."
            ),
        },
        "style_steps": {
            "priority-first": (
                "Choose one item that matters most inside this planning window and place it in the first slot.",
                "Place up to two next items after it, then keep every remaining item visibly later.",
            ),
            "shortest-first": (
                "Identify up to two items that are genuinely short; do not guess from the title alone.",
                "Place those first, then keep one important item visible before the later group.",
            ),
            "due-time-first": (
                "Verify actual external due times and place only truly time-bound items first.",
                "If no real due time exists, choose one important item rather than inventing urgency.",
            ),
        },
        "repeat_notes": {
            "none": "Leave repeat off; review the item again only when it is genuinely needed.",
            "daily": "Use a daily repeat only for an action that truly belongs every day.",
            "weekdays": "Use a weekday repeat only when weekends are intentionally excluded.",
            "weekly": "Choose a specific weekly review point rather than silently duplicating the item.",
        },
        "carryover_yes": (
            "Review each carried item: keep it today, move it with a reason, or remove it. "
            "Do not roll everything forward automatically."
        ),
        "carryover_no": (
            "Start with today's blank structure; do not prefill old items that are no longer relevant."
        ),
        "load_notes": {
            "tight": (
                "The equal share is under 5 minutes per item. Treat this as a capture list "
                "and move unrealistic items to the later group."
            ),
            "brief": (
                "The equal share is 5–14 minutes per item. Verify each real item before "
                "assuming it fits."
            ),
            "open": (
                "The equal share is at least 15 minutes per item. Real tasks can still vary "
                "widely, so revise the count when needed."
            ),
        },
        "structure_labels": {
            "first": "Start-here slots",
            "next": "Next slots",
            "later": "Later or optional slots",
        },
        "result_per_item": "Equal-share minutes per item",
        "result_remainder": "Unallocated minutes",
        "result_structure": "Blank list structure",
        "result_setup": "Setup sequence",
        "result_repeat": "Repeat decision",
        "result_carryover": "Carryover decision",
        "result_boundary": (
            "This plan uses only integer division of the selected window. It does not know "
            "task difficulty, interruptions, deadlines, accessibility needs or actual duration. "
            "It receives no free text, task content, names, dates, accounts, personal data or "
            "uploads, and uses no storage, cookies, analytics, ads or network requests."
        ),
        "review_title": "Five checks before transferring real tasks",
        "review_checks": (
            "Keep task text in the checklist system you choose, not in this planning page.",
            "Confirm real deadlines before ordering anything as urgent.",
            "Break a large item elsewhere if it cannot fit the selected window.",
            "Use repeat only when the action truly recurs at that cadence.",
            "At the end of the window, review unfinished items instead of silently carrying all of them forward.",
        ),
        "sources_title": "Official feature context, not productivity evidence",
        "sources_intro": (
            "Apple documents reminders, lists, dates, times, repeat settings, tags, subtasks, "
            "templates and Apple Watch list actions. These are Apple Reminders features, not "
            "Mochi claims or endorsement, and they do not prove productivity or any outcome."
        ),
        "source_labels": (
            "Apple: get started with Reminders on iPhone",
            "Apple: create reminders on iPhone",
            "Apple: make and view Reminders lists on Apple Watch",
            "Apple Support: create, edit, schedule, repeat and organize reminders",
            "Apple Support: organize lists, tags, subtasks and templates",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Build a private blank daily checklist plan from bounded context, available-time, "
            "item-count, starting-style, repeat-pattern and carryover inputs. Return transparent "
            "equal-share math and structure without accepting task text, names, dates, accounts "
            "or calendar data, and without predicting duration or productivity."
        ),
        "app_title": "Want a cozy place to keep the real list?",
        "app_text": (
            "Mochi is optional. Its current App Store listing describes simple checklists, "
            "reminders, daily planning, habits, routines, notes, grocery lists, Home Screen "
            "widgets, Apple Watch access and 100 skins, and says it is free with no ads. "
            "Check the current listing for exact availability and features. This planner "
            "works without the app."
        ),
        "app_cta": "View Mochi on the App Store",
        "faq_title": "Checklist planning questions",
        "faq": (
            (
                "Does this page receive my task names?",
                "No. It accepts only bounded counts and planning choices, never task text, dates or calendar contents.",
            ),
            (
                "Are equal-share minutes a task-duration estimate?",
                "No. They are transparent division of the chosen window and item count.",
            ),
            (
                "Why separate later items?",
                "The blank groups keep every captured item visible without pretending all items fit the active window.",
            ),
            (
                "Does this guarantee I will finish the list?",
                "No. It makes no productivity, health or performance promise.",
            ),
        ),
        "footer": "Private planning math only · no task text · revise with real constraints",
        "feature_list": (
            "No task text, names, dates, accounts or personal data",
            "Bounded checklist inputs and transparent integer math",
            "Blank start, next and later slot structure",
            "No upload, storage, cookies, analytics, ads or network requests",
            "No productivity, duration, health or performance promise",
        ),
        "inline_link": "Shape a private blank daily checklist before choosing an app",
        "index_title": "Private Daily Checklist Planner",
        "index_description": (
            "Turn available minutes and an item count into a blank daily structure without "
            "entering tasks, dates or account data."
        ),
    },
    "zh-Hant": {
        "title": "私密每日清單規劃器｜不用輸入任務內容",
        "description": "只用項目數與可用時間建立透明清單結構，不輸入任務文字、姓名、日期、帳號或行事曆資料。",
        "tools": "免費工具",
        "switch": "英文",
        "eyebrow": "免費 · 本機運算 · 不輸入任務文字",
        "heading": "私密每日清單規劃器",
        "lead": "只選擇數量與規劃偏好；瀏覽器會透明分配可用時間，回傳可在其他地方填寫的空白結構。",
        "badges": (
            "不輸入任務名稱或筆記",
            "不存取帳號或行事曆",
            "不上傳或儲存",
            "不保證提升效率",
        ),
        "planner": "安排今天的清單結構",
        "planner_intro": "平均分配只是規劃算式，不是任何真實任務的時間預測。",
        "context_label": "清單情境",
        "context_options": {
            "mixed-day": "混合的一天",
            "work-study": "工作或學習",
            "home": "居家",
            "errands": "外出辦事",
            "routine": "固定流程",
        },
        "minutes_label": "可用時段",
        "minutes_options": {
            15: "15 分鐘",
            30: "30 分鐘",
            60: "60 分鐘",
            120: "120 分鐘",
        },
        "count_label": "項目數",
        "style_label": "起始方式",
        "style_options": {
            "priority-first": "最重要項目優先",
            "shortest-first": "真正較短的項目優先",
            "due-time-first": "真實到期時間優先",
        },
        "repeat_label": "重複週期",
        "repeat_options": {
            "none": "不重複",
            "daily": "每天",
            "weekdays": "平日",
            "weekly": "每週",
        },
        "carryover_label": "有一項以上從前一天延續",
        "update": "建立空白清單規劃",
        "context_notes": {
            "mixed-day": "轉移每個項目時加上簡短情境標記，避免把無關工作看成一個連續區塊。",
            "work-study": "填寫空白位置時，把成果型工作和訊息、歸檔等行政項目分開。",
            "home": "把今天必須完成的項目，和不影響結果、可以移動的維護項目分開。",
            "errands": "填入清單後，先依真實地點或路線分組，再決定順序。",
            "routine": "設定週期前，把真正會重複的行動和一次性項目分開。",
        },
        "style_steps": {
            "priority-first": (
                "選一個在這段時間內最重要的項目，放進第一個位置。",
                "後面最多放兩個下一步，其餘項目清楚保留在稍後群組。",
            ),
            "shortest-first": (
                "找出最多兩個確實較短的項目，不可只看標題猜測。",
                "先放這些短項目，再讓一個重要項目保持可見，最後才是稍後群組。",
            ),
            "due-time-first": (
                "核對真實的外部到期時間，只把確實有時限的項目排在前面。",
                "若沒有真實期限，就選一個重要項目，不要自行製造急迫感。",
            ),
        },
        "repeat_notes": {
            "none": "關閉重複；只有真的再次需要時才重新檢視。",
            "daily": "只有確實每天都要做的行動才設定每天重複。",
            "weekdays": "只有刻意排除週末時，才設定平日重複。",
            "weekly": "選一個明確的每週檢視時間，不要默默複製項目。",
        },
        "carryover_yes": "逐項檢查延續項目：今天保留、附理由改期，或直接移除；不要全部自動滾動。",
        "carryover_no": "從今天的空白結構開始，不要預先填入已經不相關的舊項目。",
        "load_notes": {
            "tight": "每項平均不到 5 分鐘；請把它視為收集清單，並把不實際的項目移到稍後群組。",
            "brief": "每項平均為 5–14 分鐘；請先核對真實項目，不要直接假設一定放得下。",
            "open": "每項平均至少 15 分鐘；真實任務仍可能差異很大，需要時就調整項目數。",
        },
        "structure_labels": {
            "first": "立即開始位置",
            "next": "下一步位置",
            "later": "稍後或選做位置",
        },
        "result_per_item": "每項平均分配分鐘",
        "result_remainder": "未分配分鐘",
        "result_structure": "空白清單結構",
        "result_setup": "設定順序",
        "result_repeat": "重複決策",
        "result_carryover": "延續項目決策",
        "result_boundary": (
            "本規劃只對選定時段做整數除法；它不知道任務難度、中斷、期限、無障礙需求或真實所需時間。"
            "本頁不接收自由文字、任務內容、姓名、日期、帳號、個資或上傳內容，也不用儲存、cookie、"
            "分析、廣告或網路請求。"
        ),
        "review_title": "轉入真實任務前先確認五件事",
        "review_checks": (
            "把任務文字留在你選擇的清單系統，不要輸入這個規劃頁。",
            "把任何項目標成急迫之前，先確認真實期限。",
            "大型項目若無法放進選定時段，請在其他地方拆分。",
            "只有行動真的依該週期重複時才設定重複。",
            "時段結束後逐項檢查未完成內容，不要全部默默延續。",
        ),
        "sources_title": "官方功能背景，不是效率證據",
        "sources_intro": (
            "Apple 說明提醒事項、清單、日期、時間、重複、標籤、子任務、範本及 Apple Watch 清單操作。"
            "這些都是 Apple 提醒事項功能，不代表 Mochi 功能或 Apple 背書，也不能證明效率或任何結果。"
        ),
        "source_labels": (
            "Apple：開始使用 iPhone 提醒事項",
            "Apple：在 iPhone 建立提醒事項",
            "Apple：在 Apple Watch 建立及查看提醒事項清單",
            "Apple 支援：建立、編輯、排程、重複及整理提醒事項",
            "Apple 支援：整理清單、標籤、子任務及範本",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只用有界的情境、可用時間、項目數、起始方式、重複週期及延續選項建立私密每日空白清單；"
            "回傳透明平均分配與結構，不接收任務文字、姓名、日期、帳號或行事曆資料，也不預測時間或效率。"
        ),
        "app_title": "想用療癒的地方保存真實清單？",
        "app_text": (
            "Mochi 是選用工具；目前 App Store 頁面說明包含簡易清單、提醒事項、每日規劃、習慣、"
            "固定流程、筆記、購物清單、主畫面小工具、Apple Watch 與 100 款外觀，並標示免費、"
            "無廣告。供應地區與確切功能請以目前商店頁為準；這個規劃器不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Mochi",
        "faq_title": "清單規劃常見問題",
        "faq": (
            (
                "這個網頁會收到我的任務名稱嗎？",
                "不會。它只接受有界的數量與規劃選項，不接收任務文字、日期或行事曆內容。",
            ),
            (
                "平均分鐘是任務時間估算嗎？",
                "不是。它只是把選定時段除以項目數的透明算式。",
            ),
            (
                "為什麼要分出稍後項目？",
                "空白分組會保留所有已收集項目，但不假裝每個項目都放得進目前時段。",
            ),
            (
                "這能保證完成清單嗎？",
                "不能。本工具不承諾效率、健康或表現結果。",
            ),
        ),
        "footer": "只做私密規劃算式 · 不輸入任務文字 · 依真實限制調整",
        "feature_list": (
            "不輸入任務文字、姓名、日期、帳號或個資",
            "有界清單輸入與透明整數算式",
            "空白的立即、下一步與稍後位置結構",
            "不上傳、不儲存，不用 cookie、分析、廣告或網路請求",
            "不承諾效率、時間、健康或表現結果",
        ),
        "inline_link": "選擇 App 前先建立私密的空白每日清單結構",
        "index_title": "私密每日清單規劃器",
        "index_description": "只用可用分鐘與項目數建立空白每日結構，不輸入任務、日期或帳號資料。",
    },
    "es-ES": {
        "title": "Planificador privado de listas diarias | Sin escribir tareas",
        "description": "Convierte un número de elementos y un tiempo disponible en una estructura diaria sin introducir tareas, nombres, fechas, cuentas ni datos personales.",
        "tools": "Herramientas gratuitas", "switch": "Inglés",
        "eyebrow": "Gratis · cálculo local · sin texto de tareas",
        "heading": "Planificador privado de listas diarias",
        "lead": "Elige solo cantidades y preferencias; el navegador reparte el tiempo de forma transparente y devuelve una estructura vacía para completar en otro lugar.",
        "badges": ("Sin nombres ni notas de tareas", "Sin acceso a cuentas ni calendarios", "Sin subidas ni almacenamiento", "Sin promesas de productividad"),
        "planner": "Da forma a la lista de hoy",
        "planner_intro": "El reparto equitativo es solo una operación de planificación, no una predicción de la duración real.",
        "context_label": "Contexto de la lista",
        "context_options": {"mixed-day": "Día variado", "work-study": "Trabajo o estudio", "home": "Casa", "errands": "Recados", "routine": "Rutina"},
        "minutes_label": "Tiempo disponible",
        "minutes_options": {15: "15 minutos", 30: "30 minutos", 60: "60 minutos", 120: "120 minutos"},
        "count_label": "Número de elementos", "style_label": "Orden inicial",
        "style_options": {"priority-first": "Lo más importante primero", "shortest-first": "Lo realmente breve primero", "due-time-first": "Los plazos reales primero"},
        "repeat_label": "Frecuencia",
        "repeat_options": {"none": "Sin repetición", "daily": "Cada día", "weekdays": "Días laborables", "weekly": "Cada semana"},
        "carryover_label": "Hay uno o más elementos pendientes de antes", "update": "Crear plan de lista vacío",
        "context_notes": {
            "mixed-day": "Añade una etiqueta breve al trasladar cada elemento para no presentar trabajos inconexos como un bloque continuo.",
            "work-study": "Separa el trabajo que produce resultados de mensajes, archivo y otras tareas administrativas.",
            "home": "Distingue lo que debe hacerse hoy del mantenimiento que puede moverse sin consecuencias.",
            "errands": "Agrupa las paradas reales por lugar o ruta antes de decidir el orden.",
            "routine": "Separa las acciones que de verdad se repiten de las tareas puntuales antes de fijar una frecuencia.",
        },
        "style_steps": {
            "priority-first": ("Elige el elemento más importante en este intervalo y colócalo en la primera posición.", "Coloca después hasta dos elementos y deja el resto claramente para más tarde."),
            "shortest-first": ("Identifica hasta dos elementos realmente breves; no lo deduzcas solo por el título.", "Ponlos primero y mantén visible un elemento importante antes del grupo posterior."),
            "due-time-first": ("Comprueba los plazos externos y adelanta solo lo que de verdad vence.", "Si no hay un plazo real, elige un elemento importante en vez de inventar urgencia."),
        },
        "repeat_notes": {
            "none": "No repitas; vuelve a revisar el elemento solo cuando haga falta.",
            "daily": "Usa la repetición diaria únicamente para una acción que corresponda cada día.",
            "weekdays": "Úsala en días laborables solo si excluyes el fin de semana de forma intencionada.",
            "weekly": "Elige un momento semanal concreto en lugar de duplicar el elemento sin revisarlo.",
        },
        "carryover_yes": "Revisa cada pendiente: mantenlo hoy, muévelo con un motivo o elimínalo; no arrastres todo automáticamente.",
        "carryover_no": "Empieza con la estructura vacía de hoy; no rellenes tareas antiguas que ya no sean pertinentes.",
        "load_notes": {
            "tight": "El reparto es inferior a 5 minutos por elemento; trátalo como captura y mueve lo irreal al grupo posterior.",
            "brief": "El reparto es de 5 a 14 minutos; comprueba cada tarea real antes de asumir que cabe.",
            "open": "El reparto es de al menos 15 minutos; las tareas reales varían mucho, así que ajusta el número si hace falta.",
        },
        "structure_labels": {"first": "Posiciones para empezar", "next": "Posiciones siguientes", "later": "Posiciones posteriores u opcionales"},
        "result_per_item": "Minutos repartidos por elemento", "result_remainder": "Minutos sin asignar", "result_structure": "Estructura vacía", "result_setup": "Secuencia inicial", "result_repeat": "Decisión de repetición", "result_carryover": "Decisión sobre pendientes",
        "result_boundary": "El plan solo aplica división entera al tiempo elegido; desconoce dificultad, interrupciones, plazos, accesibilidad y duración real. No recibe texto libre, tareas, nombres, fechas, cuentas, datos personales ni subidas, y no usa almacenamiento, cookies, analítica, anuncios ni red.",
        "review_title": "Cinco comprobaciones antes de trasladar tareas reales",
        "review_checks": ("Conserva el texto de las tareas en el sistema que elijas, no en esta página.", "Confirma los plazos reales antes de marcar algo como urgente.", "Divide fuera de esta página cualquier elemento grande que no quepa.", "Activa una repetición solo si la acción sigue esa frecuencia de verdad.", "Al terminar, revisa lo pendiente en vez de arrastrarlo todo sin pensar."),
        "sources_title": "Contexto oficial de funciones, no pruebas de productividad",
        "sources_intro": "Apple documenta recordatorios, listas, fechas, horas, repeticiones, etiquetas, subtareas, plantillas y acciones en Apple Watch. Son funciones de Recordatorios de Apple, no afirmaciones sobre Mochi ni una recomendación, y no demuestran productividad ni resultados.",
        "source_labels": ("Apple: primeros pasos con Recordatorios en iPhone", "Apple: crear recordatorios en iPhone", "Apple: crear y consultar listas en Apple Watch", "Soporte de Apple: crear, editar, programar, repetir y organizar recordatorios", "Soporte de Apple: organizar listas, etiquetas, subtareas y plantillas"),
        "webmcp_source": "Vista previa de la API imperativa WebMCP de Chrome (sujeta a cambios)",
        "webmcp_description": "Crea una lista diaria privada y vacía con entradas acotadas de contexto, tiempo, cantidad, orden, repetición y pendientes. Devuelve estructura y reparto transparente sin aceptar tareas, nombres, fechas, cuentas ni datos personales y sin predecir duración o productividad.",
        "app_title": "¿Quieres un lugar agradable para guardar la lista real?",
        "app_text": "Mochi es opcional. Su ficha actual describe listas simples, recordatorios, planificación diaria, hábitos, rutinas, notas, compras, widgets, Apple Watch y 100 estilos, y señala que es gratis y sin anuncios. Comprueba la ficha vigente para conocer disponibilidad y funciones exactas. Este planificador funciona sin la app.",
        "app_cta": "Ver Mochi en App Store", "faq_title": "Preguntas sobre la planificación",
        "faq": (("¿Esta página recibe los nombres de mis tareas?", "No. Solo admite cantidades y opciones acotadas, nunca tareas, fechas ni calendarios."), ("¿Los minutos repartidos estiman la duración?", "No. Son la división transparente del tiempo elegido entre los elementos."), ("¿Por qué separar lo posterior?", "Los grupos vacíos conservan todos los elementos sin fingir que caben en el intervalo activo."), ("¿Garantiza que terminaré la lista?", "No. No promete productividad, salud, bienestar ni rendimiento.")),
        "footer": "Solo cálculo privado · sin texto de tareas · ajusta según límites reales",
        "feature_list": ("Sin tareas, nombres, fechas, cuentas ni datos personales", "Entradas acotadas y cálculo entero transparente", "Estructura vacía de inicio, siguiente y posterior", "Sin subidas, almacenamiento, cookies, analítica, anuncios ni red", "Sin promesas de productividad, duración, salud o rendimiento"),
        "inline_link": "Da forma a una lista diaria privada y vacía antes de elegir una app",
        "index_title": "Planificador privado de listas diarias", "index_description": "Crea una estructura diaria vacía con minutos y cantidad, sin introducir tareas, fechas ni cuentas.",
    },
    "pt-BR": {
        "title": "Planejador privado de checklist diário | Sem texto de tarefas",
        "description": "Transforme quantidade de itens e tempo disponível em uma estrutura diária sem inserir tarefas, nomes, datas, contas ou dados pessoais.",
        "tools": "Ferramentas gratuitas", "switch": "Inglês",
        "eyebrow": "Grátis · cálculo local · sem texto de tarefas", "heading": "Planejador privado de checklist diário",
        "lead": "Escolha apenas quantidades e preferências; o navegador divide o tempo com transparência e devolve uma estrutura vazia para preencher em outro lugar.",
        "badges": ("Sem nomes ou notas de tarefas", "Sem acesso a conta ou calendário", "Sem envio ou armazenamento", "Sem promessa de produtividade"),
        "planner": "Estruture a lista de hoje", "planner_intro": "A divisão igual é só matemática de planejamento, não previsão da duração real.",
        "context_label": "Contexto da lista", "context_options": {"mixed-day": "Dia variado", "work-study": "Trabalho ou estudo", "home": "Casa", "errands": "Tarefas na rua", "routine": "Rotina"},
        "minutes_label": "Tempo disponível", "minutes_options": {15: "15 minutos", 30: "30 minutos", 60: "60 minutos", 120: "120 minutos"},
        "count_label": "Número de itens", "style_label": "Ordem inicial",
        "style_options": {"priority-first": "Mais importante primeiro", "shortest-first": "Itens realmente curtos primeiro", "due-time-first": "Prazos reais primeiro"},
        "repeat_label": "Frequência", "repeat_options": {"none": "Sem repetição", "daily": "Diária", "weekdays": "Dias úteis", "weekly": "Semanal"},
        "carryover_label": "Há um ou mais itens trazidos de antes", "update": "Criar checklist vazio",
        "context_notes": {
            "mixed-day": "Ao transferir cada item, acrescente um rótulo curto para não juntar trabalhos sem relação em um único bloco.",
            "work-study": "Separe trabalho de resultado de mensagens, arquivamento e outras tarefas administrativas.",
            "home": "Separe o que precisa acontecer hoje da manutenção que pode mudar sem prejuízo.",
            "errands": "Agrupe paradas reais por local ou rota antes de escolher a ordem.",
            "routine": "Separe ações realmente recorrentes de itens pontuais antes de definir frequência.",
        },
        "style_steps": {
            "priority-first": ("Escolha o item mais importante nesta janela e coloque-o na primeira posição.", "Coloque até dois itens depois e mantenha os demais claramente para mais tarde."),
            "shortest-first": ("Identifique até dois itens realmente curtos; não deduza apenas pelo título.", "Coloque-os primeiro e mantenha um item importante antes do grupo posterior."),
            "due-time-first": ("Confirme prazos externos e antecipe somente itens realmente vinculados a horário.", "Sem prazo real, escolha um item importante em vez de inventar urgência."),
        },
        "repeat_notes": {"none": "Deixe a repetição desligada; reveja só quando for necessário.", "daily": "Repita diariamente apenas uma ação que realmente cabe em todos os dias.", "weekdays": "Repita em dias úteis apenas quando o fim de semana for excluído de propósito.", "weekly": "Escolha um ponto semanal específico em vez de duplicar o item sem revisão."},
        "carryover_yes": "Revise cada item trazido: mantenha hoje, mova com um motivo ou remova; não leve tudo automaticamente.",
        "carryover_no": "Comece pela estrutura vazia de hoje; não preencha itens antigos que perderam relevância.",
        "load_notes": {"tight": "A divisão fica abaixo de 5 minutos por item; trate como captura e leve o irreal ao grupo posterior.", "brief": "A divisão fica entre 5 e 14 minutos; confira cada tarefa real antes de presumir que cabe.", "open": "A divisão é de pelo menos 15 minutos; tarefas reais variam muito, então ajuste a quantidade quando necessário."},
        "structure_labels": {"first": "Posições para começar", "next": "Próximas posições", "later": "Posições posteriores ou opcionais"},
        "result_per_item": "Minutos iguais por item", "result_remainder": "Minutos não alocados", "result_structure": "Estrutura vazia", "result_setup": "Sequência inicial", "result_repeat": "Decisão de repetição", "result_carryover": "Decisão sobre itens trazidos",
        "result_boundary": "O plano usa apenas divisão inteira da janela escolhida; não conhece dificuldade, interrupções, prazos, acessibilidade ou duração real. Não recebe texto livre, tarefas, nomes, datas, contas, dados pessoais ou envios e não usa armazenamento, cookies, análise, anúncios ou rede.",
        "review_title": "Cinco verificações antes de transferir tarefas reais",
        "review_checks": ("Mantenha o texto das tarefas no sistema escolhido, não nesta página.", "Confirme prazos reais antes de tratar algo como urgente.", "Divida em outro lugar qualquer item grande que não caiba.", "Use repetição só quando a ação realmente tiver aquela frequência.", "No fim, revise o que ficou pendente em vez de levar tudo sem pensar."),
        "sources_title": "Contexto oficial de recursos, não prova de produtividade",
        "sources_intro": "A Apple documenta lembretes, listas, datas, horários, repetição, etiquetas, subtarefas, modelos e ações no Apple Watch. São recursos do Lembretes da Apple, não afirmações sobre Mochi nem endosso, e não comprovam produtividade ou resultados.",
        "source_labels": ("Apple: primeiros passos com Lembretes no iPhone", "Apple: criar lembretes no iPhone", "Apple: criar e ver listas no Apple Watch", "Suporte da Apple: criar, editar, agendar, repetir e organizar lembretes", "Suporte da Apple: organizar listas, etiquetas, subtarefas e modelos"),
        "webmcp_source": "Prévia da API imperativa WebMCP do Chrome (sujeita a alterações)",
        "webmcp_description": "Cria um checklist diário privado e vazio com entradas limitadas de contexto, tempo, quantidade, ordem, repetição e itens trazidos. Retorna estrutura e divisão transparentes sem aceitar tarefas, nomes, datas, contas ou dados pessoais e sem prever duração ou produtividade.",
        "app_title": "Quer um lugar aconchegante para guardar a lista real?",
        "app_text": "Mochi é opcional. A página atual descreve checklists simples, lembretes, planejamento diário, hábitos, rotinas, notas, compras, widgets, Apple Watch e 100 visuais, e informa que é grátis e sem anúncios. Confira a página vigente para disponibilidade e recursos exatos. Este planejador funciona sem o app.",
        "app_cta": "Ver Mochi na App Store", "faq_title": "Dúvidas sobre planejamento",
        "faq": (("Esta página recebe os nomes das minhas tarefas?", "Não. Aceita apenas quantidades e escolhas limitadas, nunca tarefas, datas ou calendário."), ("Os minutos iguais estimam duração?", "Não. São apenas a divisão transparente do tempo escolhido pela quantidade."), ("Por que separar itens posteriores?", "Os grupos vazios mantêm todos visíveis sem fingir que cabem na janela ativa."), ("Isso garante que terminarei a lista?", "Não. Não promete produtividade, saúde, bem-estar ou desempenho.")),
        "footer": "Apenas cálculo privado · sem texto de tarefas · ajuste aos limites reais",
        "feature_list": ("Sem tarefas, nomes, datas, contas ou dados pessoais", "Entradas limitadas e cálculo inteiro transparente", "Estrutura vazia de início, próximas e posteriores", "Sem envio, armazenamento, cookies, análise, anúncios ou rede", "Sem promessa de produtividade, duração, saúde ou desempenho"),
        "inline_link": "Estruture um checklist diário privado e vazio antes de escolher um app",
        "index_title": "Planejador privado de checklist diário", "index_description": "Crie uma estrutura diária vazia com minutos e quantidade, sem inserir tarefas, datas ou contas.",
    },
    "de-DE": {
        "title": "Privater Tageschecklisten-Planer | Ohne Aufgabentext",
        "description": "Aus Anzahl und verfügbarer Zeit eine leere Tagesstruktur bilden, ohne Aufgaben, Namen, Daten, Konten oder Personendaten einzugeben.",
        "tools": "Kostenlose Werkzeuge", "switch": "Englisch", "eyebrow": "Kostenlos · lokale Berechnung · kein Aufgabentext",
        "heading": "Privater Planer für Tageschecklisten", "lead": "Nur Mengen und Vorlieben wählen; der Browser teilt die Zeit nachvollziehbar und gibt eine leere Struktur zum Ausfüllen an anderer Stelle zurück.",
        "badges": ("Keine Aufgabennamen oder Notizen", "Kein Konto- oder Kalenderzugriff", "Kein Upload oder Speichern", "Kein Produktivitätsversprechen"),
        "planner": "Heutige Liste strukturieren", "planner_intro": "Die Gleichverteilung ist Planungsrechnung, keine Vorhersage der tatsächlichen Dauer.",
        "context_label": "Listenkontext", "context_options": {"mixed-day": "Gemischter Tag", "work-study": "Arbeit oder Lernen", "home": "Zuhause", "errands": "Besorgungen", "routine": "Routine"},
        "minutes_label": "Verfügbares Zeitfenster", "minutes_options": {15: "15 Minuten", 30: "30 Minuten", 60: "60 Minuten", 120: "120 Minuten"},
        "count_label": "Anzahl der Punkte", "style_label": "Startreihenfolge",
        "style_options": {"priority-first": "Wichtigstes zuerst", "shortest-first": "Tatsächlich Kurzes zuerst", "due-time-first": "Echte Fristen zuerst"},
        "repeat_label": "Wiederholung", "repeat_options": {"none": "Keine", "daily": "Täglich", "weekdays": "Werktags", "weekly": "Wöchentlich"},
        "carryover_label": "Mindestens ein Punkt wurde übernommen", "update": "Leeren Listenplan erstellen",
        "context_notes": {"mixed-day": "Beim Übertragen jeden Punkt kurz kennzeichnen, damit Unverbundenes nicht wie ein durchgehender Block wirkt.", "work-study": "Ergebnisarbeit von Nachrichten, Ablage und anderer Verwaltung trennen.", "home": "Heute Notwendiges von Wartung trennen, die sich folgenlos verschieben lässt.", "errands": "Reale Stopps nach Ort oder Route gruppieren, bevor die Reihenfolge feststeht.", "routine": "Wirklich wiederkehrende Handlungen vor der Taktwahl von Einzelaufgaben trennen."},
        "style_steps": {
            "priority-first": ("Den wichtigsten Punkt dieses Zeitfensters an die erste Stelle setzen.", "Bis zu zwei nächste Punkte folgen lassen und alle übrigen sichtbar nach hinten stellen."),
            "shortest-first": ("Bis zu zwei wirklich kurze Punkte bestimmen, nicht allein anhand des Titels.", "Diese zuerst setzen und einen wichtigen Punkt vor der späteren Gruppe sichtbar halten."),
            "due-time-first": ("Externe Fristen prüfen und nur tatsächlich zeitgebundene Punkte vorziehen.", "Ohne echte Frist einen wichtigen Punkt wählen, statt Dringlichkeit zu erfinden."),
        },
        "repeat_notes": {"none": "Wiederholung auslassen und erst bei echtem Bedarf erneut prüfen.", "daily": "Täglich nur für Handlungen verwenden, die wirklich jeden Tag anstehen.", "weekdays": "Werktags nur wählen, wenn Wochenenden bewusst ausgeschlossen sind.", "weekly": "Einen bestimmten Wochenzeitpunkt wählen, statt den Punkt ungeprüft zu duplizieren."},
        "carryover_yes": "Jeden übernommenen Punkt prüfen: heute behalten, begründet verschieben oder entfernen; nicht alles automatisch weiterrollen.",
        "carryover_no": "Mit der leeren Struktur von heute beginnen und überholte Punkte nicht vorfüllen.",
        "load_notes": {"tight": "Unter 5 Minuten je Punkt: als Erfassungsliste behandeln und Unrealistisches nach hinten stellen.", "brief": "5–14 Minuten je Punkt: jede reale Aufgabe prüfen, bevor sie als passend gilt.", "open": "Mindestens 15 Minuten je Punkt: reale Aufgaben schwanken trotzdem stark; Anzahl bei Bedarf ändern."},
        "structure_labels": {"first": "Startplätze", "next": "Nächste Plätze", "later": "Spätere oder optionale Plätze"},
        "result_per_item": "Gleich verteilte Minuten je Punkt", "result_remainder": "Nicht zugeteilte Minuten", "result_structure": "Leere Listenstruktur", "result_setup": "Startfolge", "result_repeat": "Wiederholungsentscheidung", "result_carryover": "Übernahmeentscheidung",
        "result_boundary": "Der Plan nutzt nur ganzzahlige Teilung des gewählten Fensters; Schwierigkeit, Unterbrechungen, Fristen, Barrierefreiheit und reale Dauer sind unbekannt. Er nimmt keine Freitexte, Aufgaben, Namen, Daten, Konten, Personendaten oder Uploads an und nutzt keine Speicherung, Cookies, Analysen, Werbung oder Netzwerkanfragen.",
        "review_title": "Fünf Prüfungen vor dem Übertragen echter Aufgaben",
        "review_checks": ("Aufgabentext im gewählten Listensystem behalten, nicht auf dieser Seite.", "Echte Fristen bestätigen, bevor etwas als dringend gilt.", "Große Punkte anderswo teilen, wenn sie nicht ins Fenster passen.", "Nur wiederholen, wenn die Handlung wirklich diesem Takt folgt.", "Am Ende Unerledigtes prüfen, statt alles ungeprüft zu übernehmen."),
        "sources_title": "Amtlicher Funktionskontext, kein Produktivitätsnachweis",
        "sources_intro": "Apple dokumentiert Erinnerungen, Listen, Datum, Uhrzeit, Wiederholung, Tags, Teilaufgaben, Vorlagen und Listenaktionen auf der Apple Watch. Das sind Apple-Erinnerungen-Funktionen, keine Mochi-Aussagen oder Empfehlung und kein Nachweis für Produktivität oder Ergebnisse.",
        "source_labels": ("Apple: Einstieg in Erinnerungen auf dem iPhone", "Apple: Erinnerungen auf dem iPhone erstellen", "Apple: Listen auf der Apple Watch erstellen und ansehen", "Apple Support: Erinnerungen erstellen, bearbeiten, planen, wiederholen und ordnen", "Apple Support: Listen, Tags, Teilaufgaben und Vorlagen ordnen"),
        "webmcp_source": "Vorschau der imperativen Chrome-WebMCP-API (Änderungen vorbehalten)",
        "webmcp_description": "Erstellt aus begrenzten Kontext-, Zeit-, Anzahl-, Reihenfolge-, Wiederholungs- und Übernahmewerten eine private leere Tagesliste. Gibt Struktur und nachvollziehbare Teilung zurück, ohne Aufgaben, Namen, Daten, Konten oder Personendaten anzunehmen oder Dauer und Produktivität vorherzusagen.",
        "app_title": "Soll die echte Liste an einem gemütlichen Ort liegen?",
        "app_text": "Mochi ist optional. Der aktuelle Store-Eintrag beschreibt einfache Checklisten, Erinnerungen, Tagesplanung, Gewohnheiten, Routinen, Notizen, Einkaufslisten, Widgets, Apple Watch und 100 Designs und nennt die App kostenlos und werbefrei. Verfügbarkeit und genaue Funktionen bitte im aktuellen Eintrag prüfen. Dieser Planer funktioniert ohne App.",
        "app_cta": "Mochi im App Store ansehen", "faq_title": "Fragen zur Listenplanung",
        "faq": (("Erhält diese Seite meine Aufgabennamen?", "Nein. Sie nimmt nur begrenzte Mengen und Auswahlwerte an, niemals Aufgaben, Daten oder Kalenderinhalte."), ("Schätzen die Minuten die Dauer?", "Nein. Sie sind nur die nachvollziehbare Teilung des gewählten Fensters durch die Anzahl."), ("Warum gibt es eine spätere Gruppe?", "Die leeren Gruppen halten alles sichtbar, ohne zu behaupten, dass alles ins aktive Fenster passt."), ("Garantiert dies, dass ich fertig werde?", "Nein. Es gibt kein Versprechen zu Produktivität, Gesundheit, Wohlbefinden oder Leistung.")),
        "footer": "Nur private Planungsrechnung · kein Aufgabentext · an reale Grenzen anpassen",
        "feature_list": ("Keine Aufgaben, Namen, Daten, Konten oder Personendaten", "Begrenzte Eingaben und nachvollziehbare Ganzzahlrechnung", "Leere Start-, nächste und spätere Struktur", "Keine Uploads, Speicherung, Cookies, Analysen, Werbung oder Netzwerkanfragen", "Kein Versprechen zu Produktivität, Dauer, Gesundheit oder Leistung"),
        "inline_link": "Vor der App-Wahl eine private leere Tagesliste strukturieren",
        "index_title": "Privater Tageschecklisten-Planer", "index_description": "Mit Minuten und Anzahl eine leere Tagesstruktur erstellen, ohne Aufgaben, Daten oder Konten einzugeben.",
    },
    "fr-FR": {
        "title": "Planificateur privé de liste quotidienne | Sans saisir de tâches",
        "description": "Transformez un nombre d'éléments et un temps disponible en structure quotidienne sans saisir tâches, noms, dates, comptes ou données personnelles.",
        "tools": "Outils gratuits", "switch": "Anglais", "eyebrow": "Gratuit · calcul local · aucun texte de tâche",
        "heading": "Planificateur privé de liste quotidienne", "lead": "Choisissez seulement des quantités et préférences ; le navigateur répartit le temps de façon transparente et renvoie une structure vide à remplir ailleurs.",
        "badges": ("Aucun nom ni note de tâche", "Aucun accès au compte ou calendrier", "Aucun téléversement ni stockage", "Aucune promesse de productivité"),
        "planner": "Structurer la liste du jour", "planner_intro": "Le partage égal est un calcul de planification, pas une prévision de durée réelle.",
        "context_label": "Contexte de la liste", "context_options": {"mixed-day": "Journée variée", "work-study": "Travail ou études", "home": "Maison", "errands": "Courses", "routine": "Routine"},
        "minutes_label": "Temps disponible", "minutes_options": {15: "15 minutes", 30: "30 minutes", 60: "60 minutes", 120: "120 minutes"},
        "count_label": "Nombre d'éléments", "style_label": "Ordre de départ",
        "style_options": {"priority-first": "Le plus important d'abord", "shortest-first": "Le réellement court d'abord", "due-time-first": "Les vraies échéances d'abord"},
        "repeat_label": "Répétition", "repeat_options": {"none": "Aucune", "daily": "Chaque jour", "weekdays": "Jours ouvrés", "weekly": "Chaque semaine"},
        "carryover_label": "Un ou plusieurs éléments sont reportés", "update": "Créer le plan vide",
        "context_notes": {"mixed-day": "Ajoutez un libellé bref lors du transfert afin que des travaux sans lien ne semblent pas former un seul bloc.", "work-study": "Séparez le travail de résultat des messages, du classement et de l'administration.", "home": "Séparez ce qui doit arriver aujourd'hui de l'entretien déplaçable sans conséquence.", "errands": "Regroupez les arrêts réels par lieu ou trajet avant de fixer l'ordre.", "routine": "Séparez les actions vraiment récurrentes des éléments ponctuels avant de choisir une fréquence."},
        "style_steps": {
            "priority-first": ("Placez en premier l'élément le plus important dans ce créneau.", "Ajoutez jusqu'à deux éléments suivants et gardez clairement tous les autres pour plus tard."),
            "shortest-first": ("Repérez jusqu'à deux éléments réellement courts sans le déduire du seul titre.", "Placez-les d'abord puis gardez un élément important visible avant le groupe ultérieur."),
            "due-time-first": ("Vérifiez les échéances externes et avancez uniquement les éléments vraiment datés.", "Sans vraie échéance, choisissez un élément important au lieu d'inventer une urgence."),
        },
        "repeat_notes": {"none": "Laissez la répétition désactivée et réexaminez seulement en cas de besoin réel.", "daily": "Répétez chaque jour uniquement une action qui appartient vraiment à chaque journée.", "weekdays": "Choisissez les jours ouvrés seulement si le week-end est volontairement exclu.", "weekly": "Choisissez un moment hebdomadaire précis plutôt que de dupliquer sans révision."},
        "carryover_yes": "Examinez chaque report : garder aujourd'hui, déplacer avec une raison ou supprimer ; ne reportez pas tout automatiquement.",
        "carryover_no": "Commencez par la structure vide du jour sans préremplir d'anciens éléments devenus inutiles.",
        "load_notes": {"tight": "Moins de 5 minutes par élément : traitez la liste comme une capture et placez l'irréaliste plus tard.", "brief": "De 5 à 14 minutes par élément : vérifiez chaque tâche réelle avant de supposer qu'elle tient.", "open": "Au moins 15 minutes par élément : les tâches réelles varient beaucoup ; ajustez le nombre si nécessaire."},
        "structure_labels": {"first": "Emplacements de départ", "next": "Emplacements suivants", "later": "Emplacements ultérieurs ou facultatifs"},
        "result_per_item": "Minutes réparties par élément", "result_remainder": "Minutes non attribuées", "result_structure": "Structure de liste vide", "result_setup": "Séquence de départ", "result_repeat": "Décision de répétition", "result_carryover": "Décision de report",
        "result_boundary": "Le plan applique seulement une division entière au créneau choisi ; il ignore difficulté, interruptions, échéances, accessibilité et durée réelle. Il ne reçoit ni texte libre, tâches, noms, dates, comptes, données personnelles ou téléversements et n'utilise ni stockage, cookies, analyse, publicité ou réseau.",
        "review_title": "Cinq contrôles avant de transférer les vraies tâches",
        "review_checks": ("Gardez le texte des tâches dans le système choisi, pas sur cette page.", "Confirmez les vraies échéances avant de qualifier un élément d'urgent.", "Découpez ailleurs tout gros élément qui ne tient pas dans le créneau.", "Répétez uniquement si l'action suit réellement cette fréquence.", "À la fin, examinez l'inachevé au lieu de tout reporter sans réflexion."),
        "sources_title": "Contexte fonctionnel officiel, pas une preuve de productivité",
        "sources_intro": "Apple documente rappels, listes, dates, heures, répétitions, tags, sous-tâches, modèles et actions sur Apple Watch. Ce sont des fonctions de Rappels d'Apple, pas des affirmations sur Mochi ni une approbation, et elles ne prouvent aucune productivité ou résultat.",
        "source_labels": ("Apple : premiers pas avec Rappels sur iPhone", "Apple : créer des rappels sur iPhone", "Apple : créer et consulter des listes sur Apple Watch", "Assistance Apple : créer, modifier, programmer, répéter et organiser des rappels", "Assistance Apple : organiser listes, tags, sous-tâches et modèles"),
        "webmcp_source": "Aperçu de l'API impérative WebMCP de Chrome (susceptible d'évoluer)",
        "webmcp_description": "Crée une liste quotidienne privée et vide avec des entrées bornées de contexte, temps, nombre, ordre, répétition et report. Renvoie structure et partage transparent sans accepter tâches, noms, dates, comptes ou données personnelles ni prévoir durée ou productivité.",
        "app_title": "Envie d'un endroit chaleureux pour conserver la vraie liste ?",
        "app_text": "Mochi est facultatif. Sa fiche actuelle décrit des listes simples, rappels, planification quotidienne, habitudes, routines, notes, courses, widgets, Apple Watch et 100 apparences, et indique que l'app est gratuite et sans publicité. Consultez la fiche en vigueur pour la disponibilité et les fonctions exactes. Ce planificateur fonctionne sans l'app.",
        "app_cta": "Voir Mochi dans l'App Store", "faq_title": "Questions sur la planification",
        "faq": (("Cette page reçoit-elle le nom de mes tâches ?", "Non. Elle accepte seulement des quantités et choix bornés, jamais tâches, dates ou calendrier."), ("Les minutes partagées estiment-elles la durée ?", "Non. C'est seulement la division transparente du créneau par le nombre."), ("Pourquoi séparer les éléments ultérieurs ?", "Les groupes vides gardent tout visible sans prétendre que tout tient dans le créneau actif."), ("Cela garantit-il que je finirai la liste ?", "Non. Aucune promesse de productivité, santé, bien-être ou performance.")),
        "footer": "Calcul privé uniquement · aucun texte de tâche · ajustez aux contraintes réelles",
        "feature_list": ("Aucune tâche, nom, date, compte ou donnée personnelle", "Entrées bornées et calcul entier transparent", "Structure vide de départ, suivante et ultérieure", "Aucun téléversement, stockage, cookie, analyse, publicité ou réseau", "Aucune promesse de productivité, durée, santé ou performance"),
        "inline_link": "Structurez une liste quotidienne privée et vide avant de choisir une app",
        "index_title": "Planificateur privé de liste quotidienne", "index_description": "Créez une structure quotidienne vide avec minutes et nombre, sans saisir tâches, dates ou comptes.",
    },
    "ja": {
        "title": "非公開の毎日チェックリスト計画｜タスク入力不要",
        "description": "タスク、氏名、日付、アカウント、個人情報を入力せず、項目数と使える時間から空の一日構成を作ります。",
        "tools": "無料ツール", "switch": "英語", "eyebrow": "無料 · 端末内計算 · タスク本文不要",
        "heading": "非公開の毎日チェックリスト計画", "lead": "数と計画方針だけを選ぶと、ブラウザが時間を明確に分け、別の場所で埋められる空の構成を返します。",
        "badges": ("タスク名やメモの入力なし", "アカウントやカレンダーへのアクセスなし", "アップロードや保存なし", "生産性向上の約束なし"),
        "planner": "今日のリストを組み立てる", "planner_intro": "均等配分は計画用の計算であり、実際の所要時間の予測ではありません。",
        "context_label": "リストの場面", "context_options": {"mixed-day": "用事が混ざる日", "work-study": "仕事または学習", "home": "家", "errands": "外出用事", "routine": "日課"},
        "minutes_label": "使える時間", "minutes_options": {15: "15 分", 30: "30 分", 60: "60 分", 120: "120 分"},
        "count_label": "項目数", "style_label": "最初の並べ方",
        "style_options": {"priority-first": "最重要から", "shortest-first": "本当に短いものから", "due-time-first": "実際の期限から"},
        "repeat_label": "繰り返し", "repeat_options": {"none": "繰り返さない", "daily": "毎日", "weekdays": "平日", "weekly": "毎週"},
        "carryover_label": "前から持ち越した項目がある", "update": "空のリスト計画を作る",
        "context_notes": {"mixed-day": "転記時に短い場面ラベルを付け、無関係な作業を一続きに見せないようにします。", "work-study": "成果に直結する作業と、連絡、整理などの事務を分けます。", "home": "今日必須のものと、支障なく動かせる維持作業を分けます。", "errands": "順番を決める前に、実際の立ち寄り先を場所や経路でまとめます。", "routine": "頻度を設定する前に、本当に繰り返す行動と一度だけの項目を分けます。"},
        "style_steps": {
            "priority-first": ("この時間内で最も重要な項目を一番目に置きます。", "次に最大 2 項目を置き、残りは明確に後のグループへ置きます。"),
            "shortest-first": ("本当に短い項目を最大 2 つ選びます。題名だけで判断しません。", "それらを先に置き、後のグループより前に重要項目を 1 つ見える状態にします。"),
            "due-time-first": ("外部の実際の期限を確認し、本当に時間指定がある項目だけを先にします。", "期限がなければ、急ぎを作らず重要項目を 1 つ選びます。"),
        },
        "repeat_notes": {"none": "繰り返しを切り、本当に必要になった時だけ再検討します。", "daily": "毎日行うべき行動だけを毎日に設定します。", "weekdays": "週末を意図して除く場合だけ平日に設定します。", "weekly": "無確認で複製せず、具体的な週次確認時点を選びます。"},
        "carryover_yes": "持ち越しを一つずつ確認し、今日残す、理由を付けて移す、削除するのいずれかを選びます。自動で全部を送りません。",
        "carryover_no": "今日の空の構成から始め、不要になった古い項目を先に入れません。",
        "load_notes": {"tight": "1 項目 5 分未満です。収集用と考え、現実的でないものは後へ移します。", "brief": "1 項目 5〜14 分です。実際に収まると決めつけず、一つずつ確認します。", "open": "1 項目 15 分以上です。それでも実作業の差は大きいため、必要なら項目数を変えます。"},
        "structure_labels": {"first": "開始位置", "next": "次の位置", "later": "後または任意の位置"},
        "result_per_item": "1 項目の均等配分時間", "result_remainder": "未配分の分数", "result_structure": "空のリスト構成", "result_setup": "開始手順", "result_repeat": "繰り返しの判断", "result_carryover": "持ち越しの判断",
        "result_boundary": "選んだ時間を整数で割るだけの計画です。難しさ、中断、期限、アクセシビリティ、実際の時間は分かりません。自由記述、タスク、氏名、日付、アカウント、個人情報、アップロードを受け取らず、保存、cookie、解析、広告、通信も使いません。",
        "review_title": "実際のタスクを移す前の 5 項目",
        "review_checks": ("タスク本文は選んだリスト側に置き、このページには入力しません。", "緊急として並べる前に実際の期限を確認します。", "時間内に収まらない大項目は別の場所で分けます。", "本当にその頻度で繰り返す行動だけを設定します。", "終了時に未完了を見直し、考えずに全部を持ち越しません。"),
        "sources_title": "公式の機能背景であり、生産性の証拠ではありません",
        "sources_intro": "Apple はリマインダー、リスト、日付、時刻、繰り返し、タグ、サブタスク、テンプレート、Apple Watch での操作を説明しています。Apple のリマインダー機能であり、Mochi の機能や推奨を示さず、生産性や結果も証明しません。",
        "source_labels": ("Apple：iPhone でリマインダーを使い始める", "Apple：iPhone でリマインダーを作成する", "Apple：Apple Watch でリストを作成・表示する", "Apple サポート：リマインダーの作成、編集、日時、繰り返し、整理", "Apple サポート：リスト、タグ、サブタスク、テンプレートの整理"),
        "webmcp_source": "Chrome WebMCP 命令型 API プレビュー（変更される場合があります）",
        "webmcp_description": "範囲を限定した場面、時間、数、順序、繰り返し、持ち越しから非公開の空の毎日リストを作ります。タスク、氏名、日付、アカウント、個人情報を受け取らず、時間や生産性を予測せずに構成と明確な配分を返します。",
        "app_title": "実際のリストを心地よく保管したいですか？",
        "app_text": "Mochi は任意で使うアプリです。現在のストア掲載情報には、シンプルなチェックリスト、リマインダー、毎日の計画、習慣、日課、メモ、買い物リスト、ウィジェット、Apple Watch、100 種類の外観が記載され、無料・広告なしと説明されています。提供状況と正確な機能は現行の掲載情報を確認してください。この計画ツールはアプリなしで使えます。",
        "app_cta": "App Store で Mochi を見る", "faq_title": "リスト計画の質問",
        "faq": (("このページはタスク名を受け取りますか？", "いいえ。範囲を限定した数と選択肢だけを受け取り、タスク、日付、カレンダー内容は受け取りません。"), ("均等配分時間は所要時間の見積もりですか？", "いいえ。選んだ時間を項目数で割った明確な計算だけです。"), ("なぜ後の項目を分けますか？", "空のグループは、すべてが今の時間に入ると装わずに項目を見える状態にします。"), ("完了を保証しますか？", "いいえ。生産性、健康、心身の効果、成績を約束しません。")),
        "footer": "非公開の計画計算のみ · タスク入力なし · 実際の制約で調整",
        "feature_list": ("タスク、氏名、日付、アカウント、個人情報の入力なし", "限定入力と明確な整数計算", "空の開始・次・後の位置構成", "アップロード、保存、cookie、解析、広告、通信なし", "生産性、時間、健康、成績の約束なし"),
        "inline_link": "アプリを選ぶ前に非公開の空の毎日リストを組み立てる",
        "index_title": "非公開の毎日チェックリスト計画", "index_description": "タスク、日付、アカウントを入力せず、時間と項目数から空の一日構成を作ります。",
    },
    "ko": {
        "title": "비공개 일일 체크리스트 계획 | 할 일 내용 입력 없음",
        "description": "할 일, 이름, 날짜, 계정이나 개인정보를 입력하지 않고 항목 수와 사용 가능 시간으로 빈 하루 구조를 만드세요.",
        "tools": "무료 도구", "switch": "영어", "eyebrow": "무료 · 로컬 계산 · 할 일 내용 없음",
        "heading": "비공개 일일 체크리스트 계획 도구", "lead": "수량과 계획 방식만 고르면 브라우저가 시간을 투명하게 나누고 다른 곳에서 채울 빈 구조를 반환합니다.",
        "badges": ("할 일 이름이나 메모 입력 없음", "계정이나 캘린더 접근 없음", "업로드나 저장 없음", "생산성 향상 약속 없음"),
        "planner": "오늘의 목록 구조 만들기", "planner_intro": "균등 배분은 계획용 계산일 뿐 실제 소요 시간 예측이 아닙니다.",
        "context_label": "목록 상황", "context_options": {"mixed-day": "여러 일이 섞인 날", "work-study": "업무 또는 공부", "home": "집", "errands": "외출 용무", "routine": "일과"},
        "minutes_label": "사용 가능 시간", "minutes_options": {15: "15분", 30: "30분", 60: "60분", 120: "120분"},
        "count_label": "항목 수", "style_label": "시작 순서",
        "style_options": {"priority-first": "가장 중요한 것부터", "shortest-first": "실제로 짧은 것부터", "due-time-first": "실제 마감부터"},
        "repeat_label": "반복 주기", "repeat_options": {"none": "반복 안 함", "daily": "매일", "weekdays": "평일", "weekly": "매주"},
        "carryover_label": "이전에 미룬 항목이 하나 이상 있음", "update": "빈 체크리스트 계획 만들기",
        "context_notes": {"mixed-day": "항목을 옮길 때 짧은 상황 표시를 붙여 관련 없는 일이 하나의 연속 작업처럼 보이지 않게 하세요.", "work-study": "결과를 만드는 일과 메시지, 정리 같은 행정 업무를 나누세요.", "home": "오늘 꼭 해야 하는 일과 문제없이 옮길 수 있는 유지 관리를 나누세요.", "errands": "순서를 정하기 전에 실제 방문지를 장소나 동선별로 묶으세요.", "routine": "주기를 정하기 전에 실제 반복 행동과 일회성 항목을 나누세요."},
        "style_steps": {
            "priority-first": ("이 시간 안에서 가장 중요한 항목 하나를 첫 자리에 두세요.", "다음 항목을 최대 두 개 놓고 나머지는 분명히 이후 그룹에 두세요."),
            "shortest-first": ("제목만 보고 추측하지 말고 실제로 짧은 항목을 최대 두 개 찾으세요.", "짧은 항목을 먼저 두고 이후 그룹 앞에 중요한 항목 하나를 보이게 두세요."),
            "due-time-first": ("외부의 실제 마감을 확인하고 정말 시간 제한이 있는 항목만 앞에 두세요.", "실제 마감이 없다면 긴급함을 만들지 말고 중요한 항목 하나를 고르세요."),
        },
        "repeat_notes": {"none": "반복을 끄고 정말 다시 필요할 때만 검토하세요.", "daily": "실제로 매일 해야 하는 행동만 매일 반복으로 설정하세요.", "weekdays": "주말을 의도적으로 제외할 때만 평일 반복을 사용하세요.", "weekly": "검토 없이 복제하지 말고 구체적인 주간 검토 시점을 고르세요."},
        "carryover_yes": "미룬 항목을 하나씩 검토해 오늘 유지, 이유와 함께 이동, 삭제 중 하나를 선택하세요. 모두 자동으로 넘기지 마세요.",
        "carryover_no": "오늘의 빈 구조에서 시작하고 더 이상 관련 없는 이전 항목을 미리 채우지 마세요.",
        "load_notes": {"tight": "항목당 5분 미만입니다. 수집 목록으로 보고 비현실적인 항목은 이후 그룹으로 옮기세요.", "brief": "항목당 5~14분입니다. 실제로 들어간다고 가정하기 전에 각 항목을 확인하세요.", "open": "항목당 15분 이상입니다. 실제 작업 차이는 여전히 크므로 필요하면 항목 수를 바꾸세요."},
        "structure_labels": {"first": "시작 자리", "next": "다음 자리", "later": "이후 또는 선택 자리"},
        "result_per_item": "항목당 균등 배분 시간", "result_remainder": "배분되지 않은 분", "result_structure": "빈 목록 구조", "result_setup": "시작 순서", "result_repeat": "반복 결정", "result_carryover": "미룬 항목 결정",
        "result_boundary": "선택한 시간을 정수로 나누기만 합니다. 난이도, 방해, 마감, 접근성, 실제 시간은 알 수 없습니다. 자유 입력, 할 일, 이름, 날짜, 계정, 개인정보, 업로드를 받지 않고 저장, cookie, 분석, 광고, 네트워크 요청도 사용하지 않습니다.",
        "review_title": "실제 할 일을 옮기기 전 다섯 가지 확인",
        "review_checks": ("할 일 내용은 선택한 목록 시스템에 두고 이 페이지에는 입력하지 마세요.", "긴급하게 정렬하기 전에 실제 마감을 확인하세요.", "시간 안에 들어가지 않는 큰 항목은 다른 곳에서 나누세요.", "실제로 그 주기로 반복하는 행동만 반복 설정하세요.", "종료 시 미완료 항목을 검토하고 생각 없이 전부 넘기지 마세요."),
        "sources_title": "공식 기능 배경이며 생산성 근거가 아닙니다",
        "sources_intro": "Apple은 미리 알림, 목록, 날짜, 시간, 반복, 태그, 하위 항목, 템플릿과 Apple Watch 목록 동작을 설명합니다. 이는 Apple 미리 알림 기능이며 Mochi 기능이나 추천을 뜻하지 않고 생산성이나 결과를 입증하지도 않습니다.",
        "source_labels": ("Apple: iPhone에서 미리 알림 시작하기", "Apple: iPhone에서 미리 알림 생성하기", "Apple: Apple Watch에서 목록 만들고 보기", "Apple 지원: 미리 알림 생성, 편집, 일정, 반복, 정리", "Apple 지원: 목록, 태그, 하위 항목, 템플릿 정리"),
        "webmcp_source": "Chrome WebMCP 명령형 API 미리보기(변경될 수 있음)",
        "webmcp_description": "범위가 제한된 상황, 시간, 수량, 순서, 반복, 이월 값으로 비공개 빈 일일 목록을 만듭니다. 할 일, 이름, 날짜, 계정이나 개인정보를 받지 않고 시간이나 생산성을 예측하지 않으며 구조와 투명한 배분을 반환합니다.",
        "app_title": "실제 목록을 편안한 곳에 보관하고 싶나요?",
        "app_text": "Mochi는 선택 사항입니다. 현재 스토어 설명에는 간단한 체크리스트, 미리 알림, 일일 계획, 습관, 일과, 메모, 장보기 목록, 위젯, Apple Watch, 100가지 외관이 기재되어 있으며 무료이고 광고가 없다고 안내합니다. 제공 여부와 정확한 기능은 현재 설명을 확인하세요. 이 계획 도구는 앱 없이 작동합니다.",
        "app_cta": "App Store에서 Mochi 보기", "faq_title": "목록 계획 질문",
        "faq": (("이 페이지가 내 할 일 이름을 받나요?", "아니요. 제한된 수량과 선택만 받고 할 일, 날짜나 캘린더 내용은 받지 않습니다."), ("균등 배분 시간이 소요 시간 추정인가요?", "아니요. 선택한 시간을 항목 수로 나눈 투명한 계산일 뿐입니다."), ("왜 이후 항목을 나누나요?", "빈 그룹은 모두 현재 시간에 들어간다고 가장하지 않으면서 항목을 보이게 합니다."), ("목록 완료를 보장하나요?", "아니요. 생산성, 건강, 심리 효과나 성과를 약속하지 않습니다.")),
        "footer": "비공개 계획 계산만 수행 · 할 일 입력 없음 · 실제 제약에 맞게 조정",
        "feature_list": ("할 일, 이름, 날짜, 계정이나 개인정보 입력 없음", "제한된 입력과 투명한 정수 계산", "빈 시작·다음·이후 자리 구조", "업로드, 저장, cookie, 분석, 광고, 네트워크 요청 없음", "생산성, 시간, 건강이나 성과 약속 없음"),
        "inline_link": "앱을 고르기 전에 비공개 빈 일일 목록 구조 만들기",
        "index_title": "비공개 일일 체크리스트 계획", "index_description": "할 일, 날짜나 계정을 입력하지 않고 시간과 항목 수로 빈 하루 구조를 만드세요.",
    },
    "zh-Hans": {
        "title": "私密每日清单规划器｜无需输入任务内容",
        "description": "只用项目数与可用时间建立每日空白结构，不输入任务、姓名、日期、账号或个人信息。",
        "tools": "免费工具", "switch": "英文", "eyebrow": "免费 · 本地计算 · 不输入任务文字",
        "heading": "私密每日清单规划器", "lead": "只选择数量与规划偏好；浏览器会透明分配可用时间，返回可在其他地方填写的空白结构。",
        "badges": ("不输入任务名称或备注", "不访问账号或日历", "不上传或存储", "不保证提升效率"),
        "planner": "安排今天的清单结构", "planner_intro": "平均分配只是规划算式，不是任何真实任务的时间预测。",
        "context_label": "清单场景", "context_options": {"mixed-day": "事务混合的一天", "work-study": "工作或学习", "home": "居家", "errands": "外出办事", "routine": "固定流程"},
        "minutes_label": "可用时段", "minutes_options": {15: "15 分钟", 30: "30 分钟", 60: "60 分钟", 120: "120 分钟"},
        "count_label": "项目数", "style_label": "起始方式",
        "style_options": {"priority-first": "最重要项目优先", "shortest-first": "真正较短的项目优先", "due-time-first": "真实截止时间优先"},
        "repeat_label": "重复周期", "repeat_options": {"none": "不重复", "daily": "每天", "weekdays": "工作日", "weekly": "每周"},
        "carryover_label": "有一个以上之前延续的项目", "update": "建立空白清单规划",
        "context_notes": {"mixed-day": "转移每个项目时添加简短场景标记，避免把无关工作看成一个连续区块。", "work-study": "填写空白位置时，把成果型工作与消息、归档等行政项目分开。", "home": "把今天必须完成的项目与可以无损移动的维护项目分开。", "errands": "先按真实地点或路线分组，再决定顺序。", "routine": "设置周期前，把真正重复的行动与一次性项目分开。"},
        "style_steps": {
            "priority-first": ("选择这段时间内最重要的一个项目，放在第一个位置。", "后面最多放两个下一步，其余项目清楚保留在稍后组。"),
            "shortest-first": ("找出最多两个确实较短的项目，不可只看标题猜测。", "先放这些短项目，再让一个重要项目保持可见，最后才是稍后组。"),
            "due-time-first": ("核对真实的外部截止时间，只把确实有时限的项目排在前面。", "若没有真实期限，就选择一个重要项目，不要自行制造紧迫感。"),
        },
        "repeat_notes": {"none": "关闭重复；只有确实再次需要时才重新检查。", "daily": "只有确实每天都要做的行动才设置每天重复。", "weekdays": "只有刻意排除周末时才设置工作日重复。", "weekly": "选择一个明确的每周检查时间，不要默默复制项目。"},
        "carryover_yes": "逐项检查延续项目：今天保留、附理由改期或直接移除；不要全部自动滚动。",
        "carryover_no": "从今天的空白结构开始，不要预先填入已经不相关的旧项目。",
        "load_notes": {"tight": "每项平均不到 5 分钟；把它视为收集清单，并把不实际的项目移到稍后组。", "brief": "每项平均为 5–14 分钟；先核对真实项目，不要直接假设一定放得下。", "open": "每项平均至少 15 分钟；真实任务仍可能差异很大，需要时调整项目数。"},
        "structure_labels": {"first": "立即开始位置", "next": "下一步位置", "later": "稍后或选做位置"},
        "result_per_item": "每项平均分配分钟", "result_remainder": "未分配分钟", "result_structure": "空白清单结构", "result_setup": "设置顺序", "result_repeat": "重复决定", "result_carryover": "延续项目决定",
        "result_boundary": "本规划只对选定时段做整数除法；它不知道任务难度、中断、期限、无障碍需求或真实所需时间。本页不接收自由文本、任务内容、姓名、日期、账号、个人信息或上传内容，也不使用存储、cookie、分析、广告或网络请求。",
        "review_title": "转入真实任务前先确认五件事",
        "review_checks": ("把任务文字留在你选择的清单系统，不要输入本页。", "把任何项目标成紧急之前，先确认真实期限。", "大型项目若无法放进选定时段，请在其他地方拆分。", "只有行动确实按该周期重复时才设置重复。", "时段结束后逐项检查未完成内容，不要全部默默延续。"),
        "sources_title": "官方功能背景，不是效率证据",
        "sources_intro": "Apple 说明提醒事项、清单、日期、时间、重复、标签、子任务、模板及 Apple Watch 清单操作。这些都是 Apple 提醒事项功能，不代表 Mochi 功能或 Apple 背书，也不能证明效率或任何结果。",
        "source_labels": ("Apple：开始使用 iPhone 提醒事项", "Apple：在 iPhone 创建提醒事项", "Apple：在 Apple Watch 创建及查看提醒事项清单", "Apple 支持：创建、编辑、排期、重复及整理提醒事项", "Apple 支持：整理清单、标签、子任务及模板"),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览（规范可能变更）",
        "webmcp_description": "只用有界的场景、可用时间、项目数、起始方式、重复周期及延续选项建立私密每日空白清单；返回透明平均分配与结构，不接收任务、姓名、日期、账号或个人信息，也不预测时间或效率。",
        "app_title": "想用舒适的地方保存真实清单？",
        "app_text": "Mochi 是可选工具；当前 App Store 页面说明包含简易清单、提醒事项、每日规划、习惯、固定流程、备注、购物清单、主屏幕小组件、Apple Watch 与 100 款外观，并标示免费、无广告。供应地区与确切功能请以当前商店页面为准；这个规划器无需 App 也能使用。",
        "app_cta": "在 App Store 查看 Mochi", "faq_title": "清单规划常见问题",
        "faq": (("这个网页会收到我的任务名称吗？", "不会。它只接受有界的数量与规划选项，不接收任务、日期或日历内容。"), ("平均分钟是任务时间估算吗？", "不是。它只是把选定时段除以项目数的透明算式。"), ("为什么要分出稍后项目？", "空白分组会保留所有项目，但不假装每个项目都放得进当前时段。"), ("这能保证完成清单吗？", "不能。本工具不承诺效率、健康、心理效果或表现结果。")),
        "footer": "只做私密规划算式 · 不输入任务文字 · 按真实限制调整",
        "feature_list": ("不输入任务、姓名、日期、账号或个人信息", "有界输入与透明整数算式", "空白的立即、下一步与稍后位置结构", "不上传、不存储，不用 cookie、分析、广告或网络请求", "不承诺效率、时间、健康或表现结果"),
        "inline_link": "选择 App 前先建立私密的空白每日清单结构",
        "index_title": "私密每日清单规划器", "index_description": "只用可用分钟与项目数建立每日空白结构，不输入任务、日期或账号。",
    },
}

STYLE = r"""
:root{--ink:#263126;--muted:#667066;--line:#dfe7dc;--paper:#fff;--bg:#f4f8ef;--green:#426443;--leaf:#729d62;--peach:#f8e6d3;--soft:#ebf4e6;--warn:#fff6d9;--shadow:0 22px 60px rgba(53,78,48,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e5eedc 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#46723f}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--green);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--green);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cddac8;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--green),var(--leaf));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(66,100,67,.2)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #cfe1c8;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#4f704b;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#334732;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fffdf9,var(--peach))}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--green);color:#f2f8ef;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls,.results{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
@media(max-width:560px){.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("checklist-config").textContent);
  const form = document.getElementById("checklist-planner");
  const fields = {
    context: document.getElementById("context"),
    available_minutes: document.getElementById("available-minutes"),
    item_count: document.getElementById("item-count"),
    starting_style: document.getElementById("starting-style"),
    repeat_pattern: document.getElementById("repeat-pattern"),
    has_carryover: document.getElementById("has-carryover")
  };
  const output = {
    perItem: document.getElementById("result-per-item"),
    remainder: document.getElementById("result-remainder"),
    structure: document.getElementById("result-structure"),
    setup: document.getElementById("result-setup"),
    repeat: document.getElementById("result-repeat"),
    carryover: document.getElementById("result-carryover"),
    load: document.getElementById("result-load")
  };

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
    if (!Number.isInteger(value)) {
      throw new TypeError(`${name} must be an integer.`);
    }
    if (schema.enum && !schema.enum.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    if ((schema.minimum && value < schema.minimum) ||
        (schema.maximum && value > schema.maximum)) {
      throw new RangeError(`${name} is outside the supported range.`);
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
    const context = enumValue(input, "context");
    const availableMinutes = integerValue(input, "available_minutes");
    const itemCount = integerValue(input, "item_count");
    const startingStyle = enumValue(input, "starting_style");
    const repeatPattern = enumValue(input, "repeat_pattern");
    const hasCarryover = booleanValue(input, "has_carryover");
    const minutesPerItem = Math.floor(availableMinutes / itemCount);
    const unallocatedMinutes = availableMinutes - minutesPerItem * itemCount;
    const firstSlots = 1;
    const nextSlots = Math.min(2, Math.max(0, itemCount - firstSlots));
    const laterSlots = Math.max(0, itemCount - firstSlots - nextSlots);
    const loadKey = minutesPerItem < 5 ? "tight" :
      (minutesPerItem < 15 ? "brief" : "open");
    return {
      selected_inputs: {
        context,
        context_label: config.labels.context[context],
        available_minutes: availableMinutes,
        item_count: itemCount,
        starting_style: startingStyle,
        starting_style_label: config.labels.starting_style[startingStyle],
        repeat_pattern: repeatPattern,
        repeat_pattern_label: config.labels.repeat_pattern[repeatPattern],
        has_carryover: hasCarryover
      },
      transparent_time_math: {
        formula: "floor(available_minutes / item_count)",
        equal_share_minutes_per_item: minutesPerItem,
        unallocated_minutes: unallocatedMinutes,
        is_duration_prediction: false
      },
      blank_list_structure: {
        start_here_slots: firstSlots,
        next_slots: nextSlots,
        later_or_optional_slots: laterSlots
      },
      setup_sequence: [
        config.contextNotes[context],
        ...config.styleSteps[startingStyle]
      ],
      repeat_decision: config.repeatNotes[repeatPattern],
      carryover_decision: hasCarryover ?
        config.carryoverYes : config.carryoverNo,
      load_boundary: config.loadNotes[loadKey],
      planning_boundary: config.resultBoundary
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

  function render() {
    const result = plan({
      context: fields.context.value,
      available_minutes: Number(fields.available_minutes.value),
      item_count: Number(fields.item_count.value),
      starting_style: fields.starting_style.value,
      repeat_pattern: fields.repeat_pattern.value,
      has_carryover: fields.has_carryover.checked
    });
    output.perItem.textContent =
      String(result.transparent_time_math.equal_share_minutes_per_item);
    output.remainder.textContent =
      String(result.transparent_time_math.unallocated_minutes);
    const slots = result.blank_list_structure;
    output.structure.textContent =
      `${config.structureLabels.first}: ${slots.start_here_slots}. ` +
      `${config.structureLabels.next}: ${slots.next_slots}. ` +
      `${config.structureLabels.later}: ${slots.later_or_optional_slots}.`;
    output.setup.textContent = result.setup_sequence.join(" ");
    output.repeat.textContent = result.repeat_decision;
    output.carryover.textContent = result.carryover_decision;
    output.load.textContent = `${result.load_boundary} ${result.planning_boundary}`;
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_daily_checklist",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const checklist = validateInput(input);
        const result = {
          result_type: "private_daily_checklist_plan",
          task_text_not_received_or_processed: true,
          no_account_calendar_or_storage_access: true,
          not_a_duration_or_productivity_prediction: true,
          checklist,
          transfer_review_checklist: config.reviewChecklist,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_mochi = config.optionalApp;
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
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        '<script type="application/ld+json">'
        + payload.replace("</", "<\\/")
        + "</script>"
    )


def options(values: dict[object, str]) -> str:
    return "".join(
        f'<option value="{html.escape(str(key), quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    return {
        "type": "object",
        "properties": {
            "context": {"type": "string", "enum": list(CONTEXTS)},
            "available_minutes": {
                "type": "integer",
                "enum": list(AVAILABLE_MINUTES),
            },
            "item_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 12,
            },
            "starting_style": {
                "type": "string",
                "enum": list(STARTING_STYLES),
            },
            "repeat_pattern": {
                "type": "string",
                "enum": list(REPEAT_PATTERNS),
            },
            "has_carryover": {"type": "boolean"},
        },
        "required": [
            "context",
            "available_minutes",
            "item_count",
            "starting_style",
            "repeat_pattern",
            "has_carryover",
        ],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool = False) -> str:
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
        f'<link rel="alternate" hreflang="{item}" href="{canonical(item)}">'
        for item in ALT_LOCALES
    )
    alternate_links += (
        f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    )
    sources = (
        APPLE_REMINDERS,
        APPLE_CREATE_REMINDERS,
        APPLE_WATCH_REMINDERS,
        APPLE_REMINDER_DETAILS,
        APPLE_LISTS_AND_TEMPLATES,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    review_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["review_checks"]
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
        appstore_url(APP_KEY, f"iag_checklist_plan_{locale.lower()}")
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
            "context": t["context_options"],
            "starting_style": t["style_options"],
            "repeat_pattern": t["repeat_options"],
        },
        "contextNotes": t["context_notes"],
        "styleSteps": t["style_steps"],
        "repeatNotes": t["repeat_notes"],
        "carryoverYes": t["carryover_yes"],
        "carryoverNo": t["carryover_no"],
        "loadNotes": t["load_notes"],
        "structureLabels": t["structure_labels"],
        "resultBoundary": t["result_boundary"],
        "reviewChecklist": t["review_checks"],
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
        "applicationCategory": "ProductivityApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "featureList": list(t["feature_list"]),
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
<form id="checklist-planner"><div class="controls">
<div class="field"><label for="context">{html.escape(t["context_label"])}</label><select id="context">{options(t["context_options"])}</select></div>
<div class="field"><label for="available-minutes">{html.escape(t["minutes_label"])}</label><select id="available-minutes">{options(t["minutes_options"])}</select></div>
<div class="field"><label for="item-count">{html.escape(t["count_label"])}</label><input id="item-count" type="number" min="1" max="12" step="1" value="5"></div>
<div class="field"><label for="starting-style">{html.escape(t["style_label"])}</label><select id="starting-style">{options(t["style_options"])}</select></div>
<div class="field"><label for="repeat-pattern">{html.escape(t["repeat_label"])}</label><select id="repeat-pattern">{options(t["repeat_options"])}</select></div>
<label class="toggle"><input id="has-carryover" type="checkbox">{html.escape(t["carryover_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_per_item"])}</strong><span id="result-per-item"></span></div><div class="result"><strong>{html.escape(t["result_remainder"])}</strong><span id="result-remainder"></span></div><div class="result"><strong>{html.escape(t["result_structure"])}</strong><span id="result-structure"></span></div></div>
<p class="note"><strong>{html.escape(t["result_setup"])}:</strong> <span id="result-setup"></span></p><p class="note"><strong>{html.escape(t["result_repeat"])}:</strong> <span id="result-repeat"></span></p><p class="note"><strong>{html.escape(t["result_carryover"])}:</strong> <span id="result-carryover"></span></p><p class="note" id="result-load"></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["review_title"])}</h2><ol>{review_items}</ol></article><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="checklist-config">{config_json}</script>
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
    updated = existing.sub("", text)
    anchor = re.compile(
        r'(<article class="card third"><h2><a href="'
        r'screen-time-calculator\.html">.*?</article>)',
        re.S,
    )
    if anchor.search(updated):
        updated = anchor.sub(r"\1" + card, updated, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in updated:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = updated.replace(marker, marker + card, 1)
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


TARGET_ANSWER_SLUGS = (
    "how-to-make-a-daily-planning-routine-you-actually-enjoy-and-stick-to.html",
    "what-is-the-best-to-do-list-app-with-an-apple-watch-complication.html",
)
INBOUND_LINK_CLASS = "daily-checklist-planner-inline-link"
_MOCHI_CTA = re.compile(
    r'<a\b(?=[^>]*\shref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + re.escape(APP_ID)
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)


def insert_answer_links(pages: Path = PAGES) -> int:
    """Insert one localized planner link before each eligible Mochi CTA."""
    changed = 0
    for locale in ALT_LOCALES:
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
        link = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-daily-checklist-planner-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS:
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _MOCHI_CTA.search(text)
            if not match:
                continue
            updated = text[: match.start()] + link + text[match.start() :]
            if write_text_if_changed(path, updated):
                changed += 1
    return changed


def build(pages: Path = PAGES, app_public: bool = False) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        outputs.append(canonical(locale))
        index = pages / "tools" / "index.html"
        if locale != "en":
            index = pages / locale / "tools" / "index.html"
        update_one_index(index, locale)
    insert_answer_links(pages)
    return outputs


def main() -> None:
    app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
    outputs = build(app_public=app_public)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"daily checklist planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
