#!/usr/bin/env python3
"""Generate a nine-locale, private cycle-tracker choice checklist."""

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
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SLUG = "private-cycle-tracker-checklist"
APP_KEY = "cyca"
APP_ID = "6782251621"
CONTENT_DATE = "2026-07-16"
APPLE_CYCLE_TRACKING = "https://support.apple.com/en-us/120356"
APPLE_HEALTH_PRIVACY = "https://www.apple.com/legal/privacy/data/en/health-app/"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

STORAGE = ("device-only", "encrypted-sync", "either")
ACCOUNTS = ("no-account", "optional", "any")
USE_CASES = ("basic-log", "pattern-review", "appointment-summary")
NOTIFICATIONS = ("none", "limited", "period-estimate")
SHARING = ("none", "essential-only", "unknown")
ALT_LOCALES = ("en", "es-ES", "pt-BR", "de-DE", "fr-FR", "ja", "ko", "zh-Hant", "zh-Hans", "vi", "th", "id", "tr", "hi", "ms", "ru")


def _copy(
    *,
    title: str, description: str, tools: str, switch: str, eyebrow: str,
    heading: str, lead: str, badges: tuple[str, ...], planner: str,
    intro: str, labels: tuple[str, ...], storage: tuple[str, ...],
    accounts: tuple[str, ...], uses: tuple[str, ...], notifications: tuple[str, ...],
    sharing: tuple[str, ...], booleans: tuple[str, ...], update: str,
    results: tuple[str, ...], readiness: tuple[str, ...],
    notes: tuple[tuple[str, ...], ...], questions: tuple[str, ...],
    safety: str, medical: str, sources: tuple[str, ...], source_intro: str,
    webmcp_source: str, webmcp_description: str, app: tuple[str, ...],
    faq_title: str, faq: tuple[tuple[str, str], ...], footer: str,
    features: tuple[str, ...], inline: str, index: tuple[str, str],
) -> dict[str, object]:
    return {
        "title": title, "description": description, "tools": tools, "switch": switch,
        "eyebrow": eyebrow, "heading": heading, "lead": lead, "badges": badges,
        "planner": planner, "planner_intro": intro,
        "storage_label": labels[0], "account_label": labels[1], "use_label": labels[2],
        "notification_label": labels[3], "sharing_label": labels[4],
        "lock_label": labels[5], "export_label": labels[6],
        "storage_options": dict(zip(STORAGE, storage, strict=True)),
        "account_options": dict(zip(ACCOUNTS, accounts, strict=True)),
        "use_options": dict(zip(USE_CASES, uses, strict=True)),
        "notification_options": dict(zip(NOTIFICATIONS, notifications, strict=True)),
        "sharing_options": dict(zip(SHARING, sharing, strict=True)),
        "yes": booleans[0], "no": booleans[1], "update": update,
        "readiness_title": results[0], "setup_title": results[1],
        "questions_title": results[2], "handling_title": results[3],
        "safety_title": results[4],
        "readiness_labels": dict(zip(("strict", "minimized", "flexible", "review-first"), readiness, strict=True)),
        "storage_notes": dict(zip(STORAGE, notes[0], strict=True)),
        "account_notes": dict(zip(ACCOUNTS, notes[1], strict=True)),
        "use_notes": dict(zip(USE_CASES, notes[2], strict=True)),
        "notification_notes": dict(zip(NOTIFICATIONS, notes[3], strict=True)),
        "sharing_notes": dict(zip(SHARING, notes[4], strict=True)),
        "lock_yes": notes[5][0], "lock_no": notes[5][1],
        "export_yes": notes[6][0], "export_no": notes[6][1],
        "privacy_questions": questions, "safety_boundary": safety,
        "medical_boundary": medical, "sources_title": sources[0],
        "source_labels": sources[1:], "sources_intro": source_intro,
        "webmcp_source": webmcp_source, "webmcp_description": webmcp_description,
        "app_title": app[0], "app_text": app[1], "app_cta": app[2],
        "faq_title": faq_title, "faq": faq, "footer": footer,
        "feature_list": features, "inline_link": inline,
        "index_title": index[0], "index_description": index[1],
    }


COPY = {
    "en": _copy(
        title="Private Cycle-Tracker Choice Checklist | No Health Data",
        description="Compare bounded privacy preferences for a cycle tracker without entering dates, symptoms, cycle records, sexual activity, pregnancy intent or personal data.",
        tools="Free tools", switch="繁體中文", eyebrow="Free · local choices · no health data",
        heading="Private cycle-tracker choice checklist",
        lead="Choose privacy and handling preferences only. The page returns a transparent minimum-data checklist and never receives a cycle record.",
        badges=("No dates or cycle history", "No symptoms or intimate data", "No account, name or free text", "No upload, analytics or ads"),
        planner="Set your minimum privacy requirements",
        intro="This compares your own preferences; it does not inspect, certify or rank any app.",
        labels=("Storage preference", "Account preference", "Generic use case", "Notifications", "Third-party sharing", "Screen lock required", "Export needed"),
        storage=("Device only", "Encrypted sync", "Either"), accounts=("No account", "Account optional", "Any"),
        uses=("Basic period logging", "Pattern review", "Appointment summary"),
        notifications=("None", "Limited reminders", "Period estimate"),
        sharing=("None", "Essential only", "Unknown"),
        booleans=("Yes", "No"), update="Build privacy checklist",
        results=("Privacy-readiness profile", "Minimum-data setup", "Questions to verify", "Notification and export guidance", "Safety boundary"),
        readiness=("Strict minimization", "Data minimized", "Flexible with checks", "Review before choosing"),
        notes=(
            ("Prefer storage confined to the device and verify backup behavior.", "Verify encryption in transit and at rest, recovery access and deletion controls.", "Compare both local and sync behavior before choosing."),
            ("Exclude mandatory-account options.", "Prefer an app usable without an account and verify what an account changes.", "If an account is used, verify collection, deletion and recovery."),
            ("Keep the log to the minimum dates or status needed in the chosen app.", "Review only broad patterns; predictions remain estimates.", "Export only the minimum summary needed for the appointment."),
            ("Disable cycle notifications.", "Use only discreet reminders you intentionally enable.", "Treat every period notification as an estimate based on logged data."),
            ("Do not authorize third-party sharing.", "Limit sharing to a necessary purpose, data type and duration.", "Resolve who receives data and under which privacy policy before use."),
            ("Require device or app screen protection before recording anything.", "Reconsider lock protection because cycle data can be sensitive."),
            ("Verify format, included fields, storage destination and secure deletion.", "Leave export off until a specific need exists."),
        ),
        questions=("Where is data stored and how is it encrypted?", "Can the app work without an account and delete all data?", "Which third parties can receive data and can access be revoked?", "What appears in notifications, exports and backups?"),
        safety="No tracker can promise absolute privacy. Review the current privacy policy, permissions, backup behavior, export contents and deletion controls before entering real data.",
        medical="Cycle predictions are estimates, not birth control and not a diagnosis. Do not use predictions to prevent pregnancy. For health concerns, consult a qualified healthcare professional.",
        sources=("Apple official context, not endorsement", "Apple Support: Cycle Tracking data, estimates, notifications, export and safety limits", "Apple Health privacy: encryption, iCloud, export and third-party sharing controls"),
        source_intro="Apple documents Apple Health and Cycle Tracking only. Those features and safeguards are not claims about Cyca, and Apple does not endorse this checklist or Cyca.",
        webmcp_source="Chrome WebMCP imperative API preview (subject to change)",
        webmcp_description="Create a deterministic private cycle-tracker choice checklist from bounded, non-health preferences. Accept no dates, cycle records, symptoms, sexual activity, pregnancy intent, names, free text, files or personal data.",
        app=("Want to compare one current option?", "Cyca is optional. Its verified positioning is pay once, private and on-device. Check the current App Store listing and privacy details for exact availability and features. This checklist works without the app.", "View Cyca on the App Store"),
        faq_title="Privacy checklist questions",
        faq=(("Does this page receive cycle or health data?", "No. It accepts only bounded preferences and has no fields for dates, symptoms, intimate activity or pregnancy intent."), ("Does a strict profile certify an app?", "No. It describes your selected preferences and never audits or rates an app."), ("Are period predictions reliable for contraception?", "No. Predictions are estimates and must not be used as birth control."), ("Is privacy guaranteed?", "No. Verify current permissions, policies, encryption, backups, exports and deletion controls.")),
        footer="Private preference checklist only · no health data · verify before logging",
        features=("No health records, dates, symptoms or intimate inputs", "Bounded privacy preferences only", "Transparent deterministic readiness profile", "No upload, storage, cookies, analytics, ads or network requests", "No medical, contraception, accuracy or absolute-privacy claim"),
        inline="Compare privacy requirements before choosing a cycle tracker",
        index=("Private Cycle-Tracker Choice Checklist", "Build a minimum-data privacy checklist without entering cycle or health information."),
    ),
    "zh-Hant": _copy(
        title="私密週期追蹤選擇清單｜不輸入健康資料", description="不用輸入日期、症狀、週期紀錄、性行為、懷孕意圖或個資，即可比較週期追蹤工具的私密偏好。",
        tools="免費工具", switch="英文", eyebrow="免費 · 本機選擇 · 不輸入健康資料", heading="私密週期追蹤選擇清單",
        lead="只選擇隱私與資料處理偏好；本頁回傳透明的最少資料清單，完全不接收週期紀錄。",
        badges=("不輸入日期或週期歷史", "不輸入症狀或私密資料", "不輸入帳號、姓名或自由文字", "不上傳、不分析、無廣告"),
        planner="設定最低隱私要求", intro="本工具只比較你的偏好，不檢查、認證或評分任何 App。",
        labels=("儲存偏好", "帳號偏好", "一般用途", "通知偏好", "第三方分享容忍度", "必須有螢幕鎖定", "需要匯出"),
        storage=("僅限裝置", "加密同步", "兩者皆可"), accounts=("不需帳號", "帳號選用", "皆可"),
        uses=("基本經期記錄", "查看整體模式", "就診摘要"), notifications=("不通知", "有限提醒", "經期估計"),
        sharing=("完全不分享", "僅必要用途", "尚不清楚"), booleans=("是", "否"), update="建立隱私清單",
        results=("隱私準備程度", "最少資料設定", "必須核對的問題", "通知與匯出建議", "安全界線"),
        readiness=("嚴格最小化", "資料已最小化", "彈性但須核對", "選擇前先查清楚"),
        notes=(
            ("優先把資料限制在裝置上，並核對備份方式。", "核對傳輸與靜態加密、復原存取及刪除控制。", "選擇前比較本機與同步方式。"),
            ("排除強制建立帳號的選項。", "優先選擇免帳號可用，並核對帳號會改變什麼。", "若使用帳號，核對蒐集、刪除與復原方式。"),
            ("只在選定工具記錄用途所需的最少日期或狀態。", "只看整體模式；所有預測仍是估計。", "只匯出就診真正需要的最少摘要。"),
            ("關閉週期通知。", "只啟用自己需要且內容低調的提醒。", "把所有經期通知視為依記錄資料產生的估計。"),
            ("不要授權第三方分享。", "把分享限制在必要目的、資料類型與期間。", "使用前查清楚接收者及適用的隱私政策。"),
            ("記錄前要求裝置或 App 有螢幕保護。", "週期資料可能敏感，請重新考慮鎖定保護。"),
            ("核對格式、包含欄位、儲存位置與安全刪除。", "沒有明確需要前，維持關閉匯出。"),
        ),
        questions=("資料存在哪裡，如何加密？", "能否免帳號使用並完整刪除資料？", "哪些第三方會收到資料，能否撤銷？", "通知、匯出與備份會出現哪些內容？"),
        safety="沒有追蹤工具能保證絕對隱私。輸入真實資料前，請核對現行隱私政策、權限、備份、匯出內容及刪除控制。",
        medical="週期預測只是估計，不是避孕方式，也不能診斷健康狀況。不可用預測避免懷孕；有健康疑慮請諮詢合格醫療專業人員。",
        sources=("Apple 官方背景，不代表背書", "Apple 支援：週期追蹤資料、估計、通知、匯出與安全限制", "Apple 健康隱私：加密、iCloud、匯出與第三方分享控制"),
        source_intro="Apple 只說明 Apple 健康與「經期追蹤」。這些功能及保護不代表 Cyca 功能，Apple 也未推薦本清單或 Cyca。",
        webmcp_source="Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        webmcp_description="只用有界、非健康資料的偏好建立私密週期追蹤選擇清單；不接收日期、週期紀錄、症狀、性行為、懷孕意圖、姓名、自由文字、檔案或個資。",
        app=("想比較一個現有選項？", "Cyca 是選用工具；已驗證定位為買斷、私密及裝置端使用。供應地區與確切功能、隱私細節請以目前 App Store 頁面為準；本清單不需 App 也能使用。", "在 App Store 查看 Cyca"),
        faq_title="隱私清單常見問題",
        faq=(("本頁會接收週期或健康資料嗎？", "不會。只接受有界偏好，沒有日期、症狀、私密行為或懷孕意圖欄位。"), ("嚴格結果代表認證某款 App 嗎？", "不是。它只描述你的選擇，不稽核或評分任何 App。"), ("經期預測可用來避孕嗎？", "不可。預測只是估計，不能作為避孕方式。"), ("能保證隱私嗎？", "不能。請核對現行權限、政策、加密、備份、匯出及刪除控制。")),
        footer="只做私密偏好清單 · 不輸入健康資料 · 記錄前先核對",
        features=("不輸入健康紀錄、日期、症狀或私密資料", "只接受有界隱私偏好", "透明且固定的準備程度分類", "不上傳、不儲存，不用 cookie、分析、廣告或網路請求", "不宣稱醫療、避孕、準確或絕對隱私"),
        inline="選擇週期追蹤工具前先比較隱私要求", index=("私密週期追蹤選擇清單", "不輸入週期或健康資料，建立最少資料隱私清單。"),
    ),
}


def _localized(
    locale: str, *, title: str, tools: str, switch: str, heading: str, lead: str,
    planner: str, labels: tuple[str, ...], options: tuple[tuple[str, ...], ...],
    yes_no: tuple[str, str], update: str, results: tuple[str, ...],
    readiness: tuple[str, ...], notes: tuple[tuple[str, ...], ...],
    questions: tuple[str, ...], safety: str, medical: str,
    source_text: tuple[str, ...], webmcp: tuple[str, str],
    app: tuple[str, ...], faq_title: str, faq: tuple[tuple[str, str], ...],
    footer: str, features: tuple[str, ...], inline: str, index: tuple[str, str],
) -> None:
    COPY[locale] = _copy(
        title=title,
        description=lead,
        tools=tools, switch=switch,
        eyebrow=features[0], heading=heading, lead=lead,
        badges=features[:4], planner=planner,
        intro=features[4], labels=labels,
        storage=options[0], accounts=options[1], uses=options[2],
        notifications=options[3], sharing=options[4], booleans=yes_no,
        update=update, results=results, readiness=readiness, notes=notes,
        questions=questions, safety=safety, medical=medical,
        sources=source_text[:3], source_intro=source_text[3],
        webmcp_source=webmcp[0], webmcp_description=webmcp[1],
        app=app, faq_title=faq_title, faq=faq, footer=footer,
        features=features, inline=inline, index=index,
    )


_localized(
    "es-ES", title="Lista privada para elegir un registro del ciclo | Sin datos de salud",
    tools="Herramientas gratuitas", switch="Inglés",
    heading="Lista privada para elegir un registro del ciclo",
    lead="Compara preferencias de privacidad sin introducir fechas, síntomas, historial del ciclo, actividad íntima, intención de embarazo ni datos personales.",
    planner="Define tus requisitos mínimos de privacidad",
    labels=("Almacenamiento", "Cuenta", "Uso general", "Notificaciones", "Compartir con terceros", "Bloqueo de pantalla obligatorio", "Necesitas exportar"),
    options=(("Solo en el dispositivo", "Sincronización cifrada", "Cualquiera"), ("Sin cuenta", "Cuenta opcional", "Cualquiera"), ("Registro menstrual básico", "Revisión de patrones", "Resumen para una consulta"), ("Ninguna", "Avisos limitados", "Estimación del periodo"), ("Nada", "Solo lo imprescindible", "No se sabe")),
    yes_no=("Sí", "No"), update="Crear lista de privacidad",
    results=("Perfil de preparación", "Configuración con datos mínimos", "Preguntas que comprobar", "Consejo sobre avisos y exportación", "Límite de seguridad"),
    readiness=("Minimización estricta", "Datos minimizados", "Flexible con comprobaciones", "Revisar antes de elegir"),
    notes=(("Prioriza guardar solo en el dispositivo y revisa las copias.", "Comprueba cifrado, recuperación y borrado.", "Compara el funcionamiento local y sincronizado."), ("Descarta cuentas obligatorias.", "Prefiere uso sin cuenta y comprueba qué cambia al crearla.", "Si hay cuenta, revisa recogida, borrado y recuperación."), ("Registra solo el mínimo necesario.", "Revisa patrones generales; toda predicción es una estimación.", "Exporta únicamente el resumen necesario para la consulta."), ("Desactiva avisos del ciclo.", "Usa solo avisos discretos elegidos por ti.", "Trata cada aviso del periodo como una estimación."), ("No autorices compartir con terceros.", "Limita finalidad, datos y duración.", "Aclara quién recibe los datos y bajo qué política."), ("Exige protección del dispositivo o la app.", "Reconsidera el bloqueo: estos datos son sensibles."), ("Comprueba formato, campos, destino y borrado seguro.", "No exportes hasta tener una necesidad concreta.")),
    questions=("¿Dónde se guardan y cómo se cifran los datos?", "¿Funciona sin cuenta y permite borrarlo todo?", "¿Qué terceros reciben datos y puede revocarse el acceso?", "¿Qué aparece en avisos, exportaciones y copias?"),
    safety="Ningún registro garantiza privacidad absoluta. Revisa política, permisos, copias, exportación y borrado antes de añadir datos reales.",
    medical="Las predicciones son estimaciones, no anticoncepción ni diagnóstico. No las uses para evitar un embarazo; ante dudas de salud consulta a un profesional sanitario cualificado.",
    source_text=("Contexto oficial de Apple, no respaldo", "Apple: datos, estimaciones, avisos, exportación y límites de Cycle Tracking", "Privacidad de Salud de Apple: cifrado, iCloud, exportación y terceros", "Apple solo documenta Salud y Cycle Tracking de Apple; no describe Cyca ni recomienda esta lista o Cyca."),
    webmcp=("Vista previa de la API imperativa WebMCP de Chrome", "Crea una lista determinista con preferencias acotadas y sin datos de salud; no admite fechas, historial, síntomas, actividad íntima, embarazo, nombres, texto libre, archivos ni datos personales."),
    app=("¿Quieres comparar una opción actual?", "Cyca es opcional. Su posicionamiento verificado es privado, en el dispositivo y con pago único. Consulta la ficha vigente para disponibilidad, funciones y privacidad exactas.", "Ver Cyca en App Store"),
    faq_title="Preguntas de privacidad", faq=(("¿Recibe datos del ciclo?", "No; solo preferencias acotadas."), ("¿Certifica una app?", "No; no audita ni puntúa apps."), ("¿Sirve la predicción como anticonceptivo?", "No; es una estimación."), ("¿Garantiza privacidad?", "No; comprueba políticas y controles actuales.")),
    footer="Solo preferencias privadas · sin datos de salud · comprueba antes de registrar",
    features=("Gratis · cálculo local · sin datos de salud", "Sin fechas, síntomas ni historial", "Sin nombres, cuentas ni texto libre", "Sin subidas, analítica ni anuncios", "Compara preferencias; no certifica ninguna app"),
    inline="Compara requisitos de privacidad antes de elegir un registro del ciclo",
    index=("Lista privada para elegir un registro del ciclo", "Crea una lista de datos mínimos sin introducir información del ciclo o de salud."),
)

_localized(
    "pt-BR", title="Checklist privado para escolher um rastreador de ciclo | Sem dados de saúde",
    tools="Ferramentas gratuitas", switch="Inglês", heading="Checklist privado para escolher um rastreador de ciclo",
    lead="Compare preferências de privacidade sem inserir datas, sintomas, histórico do ciclo, atividade íntima, intenção de gravidez ou dados pessoais.",
    planner="Defina seus requisitos mínimos de privacidade",
    labels=("Armazenamento", "Conta", "Uso geral", "Notificações", "Compartilhamento com terceiros", "Bloqueio de tela obrigatório", "Precisa exportar"),
    options=(("Somente no aparelho", "Sincronização criptografada", "Qualquer um"), ("Sem conta", "Conta opcional", "Qualquer um"), ("Registro menstrual básico", "Revisão de padrões", "Resumo para consulta"), ("Nenhuma", "Lembretes limitados", "Estimativa da menstruação"), ("Nenhum", "Somente essencial", "Desconhecido")),
    yes_no=("Sim", "Não"), update="Criar checklist de privacidade",
    results=("Perfil de preparo", "Configuração com dados mínimos", "Perguntas para conferir", "Orientação de notificações e exportação", "Limite de segurança"),
    readiness=("Minimização rigorosa", "Dados minimizados", "Flexível com verificações", "Revisar antes de escolher"),
    notes=(("Prefira dados apenas no aparelho e confira backups.", "Confira criptografia, recuperação e exclusão.", "Compare uso local e sincronizado."), ("Exclua conta obrigatória.", "Prefira uso sem conta e confira o que muda ao criar uma.", "Se usar conta, revise coleta, exclusão e recuperação."), ("Registre apenas o mínimo necessário.", "Veja padrões gerais; toda previsão é estimativa.", "Exporte só o resumo necessário à consulta."), ("Desative notificações do ciclo.", "Use apenas lembretes discretos escolhidos por você.", "Trate toda notificação como estimativa."), ("Não autorize terceiros.", "Limite finalidade, dados e duração.", "Descubra quem recebe e qual política se aplica."), ("Exija proteção do aparelho ou app.", "Reconsidere o bloqueio: os dados são sensíveis."), ("Confira formato, campos, destino e exclusão segura.", "Não exporte sem uma necessidade específica.")),
    questions=("Onde os dados ficam e como são criptografados?", "Funciona sem conta e apaga tudo?", "Quais terceiros recebem dados e o acesso pode ser revogado?", "O que aparece em notificações, exportações e backups?"),
    safety="Nenhum rastreador garante privacidade absoluta. Revise política, permissões, backups, exportação e exclusão antes de inserir dados reais.",
    medical="Previsões são estimativas, não contracepção nem diagnóstico. Não use para evitar gravidez; em caso de preocupação, consulte profissional de saúde qualificado.",
    source_text=("Contexto oficial da Apple, não endosso", "Apple: dados, estimativas, notificações, exportação e limites do Cycle Tracking", "Privacidade do app Saúde: criptografia, iCloud, exportação e terceiros", "A Apple documenta apenas Saúde e Cycle Tracking da Apple; não descreve Cyca nem recomenda esta lista ou Cyca."),
    webmcp=("Prévia da API imperativa WebMCP do Chrome", "Cria checklist determinista com preferências limitadas e sem dados de saúde; não aceita datas, histórico, sintomas, atividade íntima, gravidez, nomes, texto livre, arquivos ou dados pessoais."),
    app=("Quer comparar uma opção atual?", "Cyca é opcional. O posicionamento verificado é privado, no aparelho e com pagamento único. Confira a página vigente para disponibilidade, recursos e privacidade exatos.", "Ver Cyca na App Store"),
    faq_title="Perguntas de privacidade", faq=(("Recebe dados do ciclo?", "Não; somente preferências limitadas."), ("Certifica um app?", "Não; não audita nem avalia apps."), ("Previsão serve como contraceptivo?", "Não; é apenas estimativa."), ("Garante privacidade?", "Não; confira políticas e controles atuais.")),
    footer="Somente preferências privadas · sem dados de saúde · confira antes de registrar",
    features=("Grátis · cálculo local · sem dados de saúde", "Sem datas, sintomas ou histórico", "Sem nomes, contas ou texto livre", "Sem envio, análise ou anúncios", "Compara preferências; não certifica apps"),
    inline="Compare requisitos de privacidade antes de escolher um rastreador",
    index=("Checklist privado para escolher rastreador", "Crie requisitos mínimos sem inserir dados do ciclo ou de saúde."),
)

for _locale, _data in {
    "de-DE": dict(
        title="Private Checkliste zur Wahl eines Zyklus-Trackers | Keine Gesundheitsdaten", tools="Kostenlose Werkzeuge", switch="Englisch",
        heading="Private Checkliste zur Wahl eines Zyklus-Trackers", lead="Datenschutzwünsche vergleichen, ohne Daten, Symptome, Zyklusverlauf, intime Aktivitäten, Kinderwunsch oder Personendaten einzugeben.",
        planner="Mindestanforderungen an den Datenschutz festlegen",
        labels=("Speicherung", "Konto", "Allgemeiner Zweck", "Mitteilungen", "Weitergabe an Dritte", "Bildschirmsperre erforderlich", "Export erforderlich"),
        options=(("Nur auf dem Gerät", "Verschlüsselte Synchronisierung", "Beides"), ("Kein Konto", "Konto optional", "Beliebig"), ("Einfache Periodenerfassung", "Muster prüfen", "Zusammenfassung für einen Termin"), ("Keine", "Begrenzte Erinnerungen", "Periodenschätzung"), ("Keine", "Nur zwingend nötig", "Unbekannt")),
        yes_no=("Ja", "Nein"), update="Datenschutzcheckliste erstellen",
        results=("Datenschutzprofil", "Datensparsame Einrichtung", "Zu prüfende Fragen", "Hinweise zu Mitteilungen und Export", "Sicherheitsgrenze"),
        readiness=("Strikte Minimierung", "Daten minimiert", "Flexibel mit Prüfungen", "Vor der Wahl prüfen"),
        words=("Daten auf dem Gerät bevorzugen und Backups prüfen.", "Verschlüsselung, Wiederherstellung und Löschung prüfen.", "Lokale und synchronisierte Nutzung vergleichen.", "Pflichtkonten ausschließen.", "Nutzung ohne Konto bevorzugen.", "Bei Konto Erhebung und Löschung prüfen.", "Nur das Nötigste erfassen.", "Muster allgemein betrachten; Vorhersagen bleiben Schätzungen.", "Nur nötige Terminzusammenfassung exportieren.", "Zyklusmitteilungen ausschalten.", "Nur bewusst gewählte diskrete Erinnerungen nutzen.", "Periodenhinweise als Schätzung behandeln.", "Keine Weitergabe erlauben.", "Zweck, Daten und Dauer begrenzen.", "Empfänger und Datenschutzregeln klären.", "Geräte- oder App-Schutz verlangen.", "Sperrschutz wegen sensibler Daten neu erwägen.", "Format, Felder, Ziel und sichere Löschung prüfen.", "Export bis zu einem konkreten Bedarf ausschalten."),
        questions=("Wo liegen die Daten und wie sind sie verschlüsselt?", "Funktioniert es ohne Konto und lassen sich alle Daten löschen?", "Welche Dritten erhalten Daten und ist der Zugriff widerrufbar?", "Was erscheint in Mitteilungen, Exporten und Backups?"),
        safety="Kein Tracker garantiert absoluten Datenschutz. Vor echten Einträgen Richtlinie, Rechte, Backups, Exporte und Löschung prüfen.",
        medical="Vorhersagen sind Schätzungen, keine Verhütung und keine Diagnose. Nicht zur Schwangerschaftsvermeidung nutzen; bei Beschwerden medizinisches Fachpersonal fragen.",
        source=("Offizieller Apple-Kontext, keine Empfehlung", "Apple: Daten, Schätzungen, Mitteilungen, Export und Grenzen von Cycle Tracking", "Apple-Datenschutz für Health: Verschlüsselung, iCloud, Export und Dritte", "Apple beschreibt nur Apple Health und Cycle Tracking, nicht Cyca, und empfiehlt weder diese Checkliste noch Cyca."),
        web=("Vorschau der imperativen Chrome-WebMCP-API", "Erstellt aus begrenzten, nicht medizinischen Wünschen eine feste Checkliste; keine Daten, Verläufe, Symptome, intime Aktivitäten, Schwangerschaftsabsicht, Namen, Freitexte, Dateien oder Personendaten."),
        app=("Eine aktuelle Option vergleichen?", "Cycas bestätigte Positionierung ist einmal bezahlen, privat und auf dem Gerät. Aktuellen Store-Eintrag für genaue Verfügbarkeit, Funktionen und Datenschutz prüfen.", "Cyca im App Store ansehen"),
        faq=("Datenschutzfragen", (("Erhält die Seite Zyklusdaten?", "Nein, nur begrenzte Wünsche."), ("Zertifiziert sie Apps?", "Nein, sie prüft oder bewertet keine App."), ("Ist die Schätzung Verhütung?", "Nein, sie ist nur eine Schätzung."), ("Ist Datenschutz garantiert?", "Nein, aktuelle Regeln und Kontrollen prüfen."))),
        footer="Nur private Präferenzen · keine Gesundheitsdaten · vor dem Erfassen prüfen",
        features=("Kostenlos · lokale Berechnung · keine Gesundheitsdaten", "Keine Daten, Symptome oder Verläufe", "Keine Namen, Konten oder Freitexte", "Keine Uploads, Analysen oder Werbung", "Vergleicht Wünsche; zertifiziert keine App"),
        inline="Datenschutzanforderungen vor der Tracker-Wahl vergleichen", index=("Private Zyklus-Tracker-Checkliste", "Datensparsame Anforderungen ohne Zyklus- oder Gesundheitsdaten erstellen."),
    ),
    "fr-FR": dict(
        title="Liste privée pour choisir un suivi de cycle | Aucune donnée de santé", tools="Outils gratuits", switch="Anglais",
        heading="Liste privée pour choisir un suivi de cycle", lead="Comparez vos exigences de confidentialité sans saisir dates, symptômes, historique, activité intime, projet de grossesse ou données personnelles.",
        planner="Définir vos exigences minimales de confidentialité",
        labels=("Stockage", "Compte", "Usage général", "Notifications", "Partage avec des tiers", "Verrouillage requis", "Export nécessaire"),
        options=(("Sur l'appareil uniquement", "Synchronisation chiffrée", "Les deux"), ("Sans compte", "Compte facultatif", "Indifférent"), ("Suivi menstruel simple", "Examen des tendances", "Résumé pour un rendez-vous"), ("Aucune", "Rappels limités", "Estimation des règles"), ("Aucun", "Strict nécessaire", "Inconnu")),
        yes_no=("Oui", "Non"), update="Créer la liste de confidentialité",
        results=("Profil de préparation", "Réglage minimal", "Questions à vérifier", "Conseil notifications et export", "Limite de sécurité"),
        readiness=("Minimisation stricte", "Données minimisées", "Souple avec contrôles", "Vérifier avant de choisir"),
        words=("Privilégiez l'appareil et contrôlez les sauvegardes.", "Vérifiez chiffrement, récupération et suppression.", "Comparez local et synchronisé.", "Écartez les comptes obligatoires.", "Privilégiez l'usage sans compte.", "Avec compte, vérifiez collecte et suppression.", "Ne consignez que le minimum.", "Examinez les tendances; toute prévision reste estimative.", "Exportez seulement le résumé nécessaire.", "Désactivez les notifications.", "Gardez uniquement des rappels discrets choisis.", "Traitez toute notification comme une estimation.", "N'autorisez aucun tiers.", "Limitez finalité, données et durée.", "Identifiez destinataire et politique.", "Exigez une protection de l'appareil ou de l'app.", "Réexaminez le verrouillage pour ces données sensibles.", "Vérifiez format, champs, destination et suppression.", "N'exportez pas sans besoin précis."),
        questions=("Où sont stockées et chiffrées les données ?", "L'outil fonctionne-t-il sans compte et efface-t-il tout ?", "Quels tiers reçoivent les données et l'accès est-il révocable ?", "Que montrent notifications, exports et sauvegardes ?"),
        safety="Aucun suivi ne garantit une confidentialité absolue. Vérifiez politique, autorisations, sauvegardes, exports et suppression avant toute vraie saisie.",
        medical="Les prévisions sont des estimations, ni contraception ni diagnostic. Ne les utilisez pas pour éviter une grossesse; consultez un professionnel de santé qualifié en cas d'inquiétude.",
        source=("Contexte officiel Apple, pas une approbation", "Apple : données, estimations, notifications, export et limites de Cycle Tracking", "Confidentialité Santé Apple : chiffrement, iCloud, export et tiers", "Apple décrit uniquement Santé et Cycle Tracking d'Apple, pas Cyca, et ne recommande ni cette liste ni Cyca."),
        web=("Aperçu de l'API impérative WebMCP de Chrome", "Crée une liste déterministe avec préférences bornées et non médicales; aucune date, historique, symptôme, activité intime, grossesse, nom, texte libre, fichier ou donnée personnelle."),
        app=("Comparer une option actuelle ?", "Le positionnement vérifié de Cyca est privé, sur l'appareil et en achat unique. Consultez la fiche en vigueur pour disponibilité, fonctions et confidentialité exactes.", "Voir Cyca dans l'App Store"),
        faq=("Questions de confidentialité", (("La page reçoit-elle des données de cycle ?", "Non, seulement des préférences bornées."), ("Certifie-t-elle une app ?", "Non, elle n'audite ni ne note aucune app."), ("La prévision est-elle contraceptive ?", "Non, ce n'est qu'une estimation."), ("La confidentialité est-elle garantie ?", "Non, contrôlez les règles et réglages actuels."))),
        footer="Préférences privées uniquement · aucune donnée de santé · vérifier avant saisie",
        features=("Gratuit · calcul local · aucune donnée de santé", "Aucune date, symptôme ou historique", "Aucun nom, compte ou texte libre", "Aucun téléversement, analyse ou publicité", "Compare les exigences; ne certifie aucune app"),
        inline="Comparer la confidentialité avant de choisir un suivi", index=("Liste privée de choix d'un suivi de cycle", "Définissez un minimum de données sans saisir d'informations de cycle ou de santé."),
    ),
    "vi": dict(
        title="Danh sách riêng tư để chọn ứng dụng theo dõi chu kỳ | Không dữ liệu sức khỏe", tools="Công cụ miễn phí", switch="English",
        heading="Danh sách riêng tư để chọn ứng dụng theo dõi chu kỳ", lead="So sánh các yêu cầu quyền riêng tư mà không nhập ngày, triệu chứng, tiền sử chu kỳ, hoạt động thân mật, ý định mang thai hay dữ liệu cá nhân.",
        planner="Xác định yêu cầu quyền riêng tư tối thiểu của bạn",
        labels=("Lưu trữ", "Tài khoản", "Mục đích chung", "Thông báo", "Chia sẻ với bên thứ ba", "Bắt buộc khóa màn hình", "Cần xuất dữ liệu"),
        options=(("Chỉ trên thiết bị", "Đồng bộ mã hóa", "Cả hai"), ("Không tài khoản", "Tài khoản tùy chọn", "Bất kỳ"), ("Ghi kinh nguyệt cơ bản", "Xem xu hướng", "Tóm tắt cho buổi khám"), ("Không có", "Nhắc hạn chế", "Ước tính kỳ kinh"), ("Không", "Chỉ thiết yếu", "Không rõ")),
        yes_no=("Có", "Không"), update="Tạo danh sách quyền riêng tư",
        results=("Hồ sơ mức độ sẵn sàng", "Thiết lập dữ liệu tối thiểu", "Câu hỏi cần kiểm", "Lời khuyên về thông báo và xuất", "Giới hạn an toàn"),
        readiness=("Tối giản nghiêm ngặt", "Dữ liệu tối giản", "Linh hoạt kèm kiểm tra", "Xem lại trước khi chọn"),
        words=("Ưu tiên chỉ lưu trên thiết bị và kiểm tra bản sao lưu.", "Kiểm tra mã hóa, khôi phục và xóa.", "So sánh dùng cục bộ và đồng bộ.", "Loại bỏ ứng dụng bắt buộc tài khoản.", "Ưu tiên dùng không cần tài khoản.", "Nếu có tài khoản, xem thu thập và xóa.", "Chỉ ghi mức tối thiểu cần thiết.", "Xem xu hướng chung; mọi dự đoán chỉ là ước tính.", "Chỉ xuất bản tóm tắt cần cho buổi khám.", "Tắt thông báo chu kỳ.", "Chỉ dùng nhắc kín đáo do bạn chọn.", "Coi mọi thông báo kỳ kinh là ước tính.", "Không cho phép bên thứ ba.", "Giới hạn mục đích, dữ liệu và thời hạn.", "Làm rõ ai nhận dữ liệu và theo chính sách nào.", "Yêu cầu bảo vệ thiết bị hoặc ứng dụng.", "Cân nhắc lại khóa màn hình vì dữ liệu nhạy cảm.", "Kiểm tra định dạng, trường, đích đến và xóa an toàn.", "Không xuất cho đến khi có nhu cầu cụ thể."),
        questions=("Dữ liệu lưu ở đâu và được mã hóa thế nào?", "Có hoạt động không cần tài khoản và xóa được hết không?", "Bên thứ ba nào nhận dữ liệu và có thu hồi được quyền không?", "Thông báo, bản xuất và sao lưu hiển thị gì?"),
        safety="Không ứng dụng nào bảo đảm quyền riêng tư tuyệt đối. Hãy xem chính sách, quyền, sao lưu, xuất và xóa trước khi thêm dữ liệu thật.",
        medical="Dự đoán là ước tính, không phải biện pháp tránh thai hay chẩn đoán. Đừng dùng để tránh thai; nếu lo ngại về sức khỏe hãy hỏi chuyên gia y tế có chuyên môn.",
        source=("Bối cảnh chính thức của Apple, không phải sự chứng thực", "Apple: dữ liệu, ước tính, thông báo, xuất và giới hạn của Cycle Tracking", "Quyền riêng tư của Apple Health: mã hóa, iCloud, xuất và bên thứ ba", "Apple chỉ mô tả Health và Cycle Tracking của Apple, không mô tả Cyca và không khuyến nghị danh sách này hay Cyca."),
        web=("Bản xem trước API mệnh lệnh WebMCP của Chrome", "Tạo danh sách xác định từ các tùy chọn có giới hạn, phi y tế; không nhận ngày, tiền sử, triệu chứng, hoạt động thân mật, ý định mang thai, tên, văn bản tự do, tệp hay dữ liệu cá nhân."),
        app=("Muốn so sánh một lựa chọn hiện có?", "Cyca là tùy chọn. Định vị đã xác minh của nó là riêng tư, trên thiết bị và trả một lần. Hãy xem trang hiện tại để biết tình trạng, tính năng và quyền riêng tư chính xác.", "Xem Cyca trên App Store"),
        faq=("Câu hỏi về quyền riêng tư", (("Trang này có nhận dữ liệu chu kỳ không?", "Không; chỉ nhận các tùy chọn có giới hạn."), ("Nó có chứng nhận một ứng dụng không?", "Không; nó không kiểm định hay chấm điểm ứng dụng."), ("Dự đoán có dùng làm biện pháp tránh thai không?", "Không; đó chỉ là ước tính."), ("Có bảo đảm quyền riêng tư không?", "Không; hãy kiểm tra chính sách và kiểm soát hiện tại."))),
        footer="Chỉ tùy chọn riêng tư · không dữ liệu sức khỏe · kiểm tra trước khi ghi",
        features=("Miễn phí · tính tại chỗ · không dữ liệu sức khỏe", "Không ngày, triệu chứng hay tiền sử", "Không tên, tài khoản hay văn bản tự do", "Không tải lên, phân tích hay quảng cáo", "So sánh tùy chọn; không chứng nhận ứng dụng nào"),
        inline="So sánh yêu cầu quyền riêng tư trước khi chọn ứng dụng theo dõi chu kỳ", index=("Danh sách riêng tư chọn ứng dụng theo dõi chu kỳ", "Tạo yêu cầu dữ liệu tối thiểu mà không nhập thông tin chu kỳ hay sức khỏe."),
    ),
    "th": dict(
        title="เช็กลิสต์ส่วนตัวสำหรับเลือกแอปติดตามรอบเดือน | ไม่มีข้อมูลสุขภาพ", tools="เครื่องมือฟรี", switch="English",
        heading="เช็กลิสต์ส่วนตัวสำหรับเลือกแอปติดตามรอบเดือน", lead="เปรียบเทียบความต้องการด้านความเป็นส่วนตัวโดยไม่กรอกวันที่ อาการ ประวัติรอบเดือน กิจกรรมใกล้ชิด ความตั้งใจตั้งครรภ์ หรือข้อมูลส่วนบุคคล",
        planner="กำหนดข้อกำหนดความเป็นส่วนตัวขั้นต่ำของคุณ",
        labels=("การจัดเก็บ", "บัญชี", "การใช้งานทั่วไป", "การแจ้งเตือน", "การแบ่งปันกับบุคคลที่สาม", "ต้องล็อกหน้าจอ", "ต้องส่งออกข้อมูล"),
        options=(("เฉพาะบนเครื่อง", "ซิงก์แบบเข้ารหัส", "อย่างใดก็ได้"), ("ไม่มีบัญชี", "บัญชีเป็นทางเลือก", "แบบใดก็ได้"), ("บันทึกประจำเดือนพื้นฐาน", "ทบทวนรูปแบบ", "สรุปสำหรับการนัดพบแพทย์"), ("ไม่มี", "เตือนแบบจำกัด", "ประมาณการรอบเดือน"), ("ไม่มี", "เฉพาะที่จำเป็น", "ไม่ทราบ")),
        yes_no=("ใช่", "ไม่"), update="สร้างเช็กลิสต์ความเป็นส่วนตัว",
        results=("โปรไฟล์ความพร้อม", "การตั้งค่าข้อมูลน้อยที่สุด", "คำถามที่ต้องตรวจ", "คำแนะนำเรื่องการแจ้งเตือนและการส่งออก", "ขอบเขตความปลอดภัย"),
        readiness=("ลดข้อมูลอย่างเข้มงวด", "ลดข้อมูลแล้ว", "ยืดหยุ่นพร้อมการตรวจสอบ", "ทบทวนก่อนเลือก"),
        words=("เลือกเก็บเฉพาะบนเครื่องและตรวจการสำรองข้อมูล", "ตรวจการเข้ารหัส การกู้คืน และการลบ", "เปรียบเทียบการใช้แบบเฉพาะเครื่องและแบบซิงก์", "ตัดแอปที่บังคับมีบัญชีออก", "เลือกใช้แบบไม่ต้องมีบัญชี", "ถ้ามีบัญชี ให้ตรวจการเก็บและการลบ", "บันทึกเฉพาะเท่าที่จำเป็นน้อยที่สุด", "ดูรูปแบบโดยรวม ทุกการทำนายเป็นเพียงประมาณการ", "ส่งออกเฉพาะสรุปที่จำเป็นสำหรับการนัด", "ปิดการแจ้งเตือนรอบเดือน", "ใช้เฉพาะการเตือนที่ไม่เปิดเผยซึ่งคุณเลือกเอง", "ถือว่าการแจ้งเตือนรอบเดือนทุกครั้งเป็นประมาณการ", "อย่าอนุญาตบุคคลที่สาม", "จำกัดวัตถุประสงค์ ข้อมูล และระยะเวลา", "ทำให้ชัดเจนว่าใครรับข้อมูลและตามนโยบายใด", "กำหนดให้มีการป้องกันเครื่องหรือแอป", "พิจารณาการล็อกใหม่เพราะข้อมูลอ่อนไหว", "ตรวจรูปแบบ ฟิลด์ ปลายทาง และการลบอย่างปลอดภัย", "อย่าส่งออกจนกว่าจะมีความจำเป็นเฉพาะเจาะจง"),
        questions=("ข้อมูลเก็บที่ไหนและเข้ารหัสอย่างไร?", "ใช้งานได้โดยไม่มีบัญชีและลบได้ทั้งหมดไหม?", "บุคคลที่สามรายใดได้รับข้อมูลและเพิกถอนสิทธิ์ได้ไหม?", "การแจ้งเตือน การส่งออก และการสำรองแสดงอะไร?"),
        safety="ไม่มีแอปใดรับประกันความเป็นส่วนตัวสัมบูรณ์ โปรดตรวจนโยบาย สิทธิ์ การสำรอง การส่งออก และการลบก่อนเพิ่มข้อมูลจริง",
        medical="การทำนายเป็นประมาณการ ไม่ใช่การคุมกำเนิดหรือการวินิจฉัย อย่าใช้เพื่อหลีกเลี่ยงการตั้งครรภ์ หากกังวลเรื่องสุขภาพให้ปรึกษาผู้เชี่ยวชาญทางการแพทย์ที่มีคุณสมบัติ",
        source=("บริบททางการของ Apple ไม่ใช่การรับรอง", "Apple: ข้อมูล ประมาณการ การแจ้งเตือน การส่งออก และขอบเขตของ Cycle Tracking", "ความเป็นส่วนตัวของ Apple Health: การเข้ารหัส iCloud การส่งออก และบุคคลที่สาม", "Apple อธิบายเฉพาะ Health และ Cycle Tracking ของ Apple ไม่ได้อธิบาย Cyca และไม่แนะนำเช็กลิสต์นี้หรือ Cyca"),
        web=("ตัวอย่าง API เชิงคำสั่ง WebMCP ของ Chrome", "สร้างเช็กลิสต์แบบกำหนดแน่นอนจากตัวเลือกที่มีขอบเขตและไม่ใช่ทางการแพทย์ ไม่รับวันที่ ประวัติ อาการ กิจกรรมใกล้ชิด ความตั้งใจตั้งครรภ์ ชื่อ ข้อความอิสระ ไฟล์ หรือข้อมูลส่วนบุคคล"),
        app=("อยากเปรียบเทียบตัวเลือกที่มีอยู่ไหม?", "Cyca เป็นทางเลือก การวางตำแหน่งที่ยืนยันแล้วคือส่วนตัว อยู่บนเครื่อง และจ่ายครั้งเดียว โปรดดูหน้าปัจจุบันเพื่อความพร้อม ฟีเจอร์ และความเป็นส่วนตัวที่แน่นอน", "ดู Cyca บน App Store"),
        faq=("คำถามเรื่องความเป็นส่วนตัว", (("หน้านี้รับข้อมูลรอบเดือนไหม?", "ไม่ รับเพียงตัวเลือกที่มีขอบเขต"), ("รับรองแอปไหม?", "ไม่ ไม่ตรวจสอบหรือให้คะแนนแอป"), ("การทำนายใช้คุมกำเนิดได้ไหม?", "ไม่ เป็นเพียงประมาณการ"), ("รับประกันความเป็นส่วนตัวไหม?", "ไม่ ตรวจนโยบายและการควบคุมปัจจุบัน"))),
        footer="เฉพาะความชอบส่วนตัว · ไม่มีข้อมูลสุขภาพ · ตรวจก่อนบันทึก",
        features=("ฟรี · คำนวณในเครื่อง · ไม่มีข้อมูลสุขภาพ", "ไม่มีวันที่ อาการ หรือประวัติ", "ไม่มีชื่อ บัญชี หรือข้อความอิสระ", "ไม่อัปโหลด วิเคราะห์ หรือโฆษณา", "เปรียบเทียบความต้องการ ไม่รับรองแอปใด"),
        inline="เปรียบเทียบข้อกำหนดความเป็นส่วนตัวก่อนเลือกแอปติดตามรอบเดือน", index=("เช็กลิสต์ส่วนตัวเลือกแอปติดตามรอบเดือน", "สร้างข้อกำหนดข้อมูลน้อยที่สุดโดยไม่กรอกข้อมูลรอบเดือนหรือสุขภาพ"),
    ),
    "id": dict(
        title="Daftar Periksa Privasi untuk Memilih Pelacak Siklus | Tanpa Data Kesehatan", tools="Alat gratis", switch="English",
        heading="Daftar periksa privasi untuk memilih pelacak siklus", lead="Bandingkan preferensi privasi tanpa memasukkan tanggal, gejala, riwayat siklus, aktivitas intim, niat kehamilan, atau data pribadi.",
        planner="Tetapkan persyaratan privasi minimum Anda",
        labels=("Penyimpanan", "Akun", "Tujuan umum", "Notifikasi", "Berbagi dengan pihak ketiga", "Kunci layar wajib", "Perlu ekspor"),
        options=(("Hanya di perangkat", "Sinkronisasi terenkripsi", "Keduanya"), ("Tanpa akun", "Akun opsional", "Apa pun"), ("Catatan menstruasi dasar", "Tinjauan pola", "Ringkasan untuk janji temu"), ("Tidak ada", "Pengingat terbatas", "Perkiraan menstruasi"), ("Tidak ada", "Hanya yang penting", "Tidak diketahui")),
        yes_no=("Ya", "Tidak"), update="Buat daftar periksa privasi",
        results=("Profil kesiapan", "Pengaturan data minimum", "Pertanyaan untuk diperiksa", "Saran notifikasi dan ekspor", "Batas keamanan"),
        readiness=("Minimalisasi ketat", "Data diminimalkan", "Fleksibel dengan pemeriksaan", "Tinjau sebelum memilih"),
        words=("Utamakan penyimpanan hanya di perangkat dan periksa cadangan.", "Periksa enkripsi, pemulihan, dan penghapusan.", "Bandingkan penggunaan lokal dan tersinkron.", "Singkirkan aplikasi yang mewajibkan akun.", "Utamakan penggunaan tanpa akun.", "Jika ada akun, periksa pengumpulan dan penghapusan.", "Catat hanya yang minimum diperlukan.", "Lihat pola umum; setiap prediksi hanyalah perkiraan.", "Ekspor hanya ringkasan yang diperlukan untuk janji temu.", "Matikan notifikasi siklus.", "Gunakan hanya pengingat diskret pilihan Anda.", "Perlakukan setiap notifikasi menstruasi sebagai perkiraan.", "Jangan izinkan pihak ketiga.", "Batasi tujuan, data, dan durasi.", "Perjelas siapa penerima data dan menurut kebijakan mana.", "Wajibkan perlindungan perangkat atau aplikasi.", "Pertimbangkan ulang kunci layar karena data sensitif.", "Periksa format, bidang, tujuan, dan penghapusan aman.", "Jangan ekspor sampai ada kebutuhan spesifik."),
        questions=("Di mana data disimpan dan bagaimana dienkripsi?", "Apakah berfungsi tanpa akun dan bisa hapus semua?", "Pihak ketiga mana yang menerima data dan bisakah akses dicabut?", "Apa yang tampil di notifikasi, ekspor, dan cadangan?"),
        safety="Tidak ada pelacak yang menjamin privasi mutlak. Tinjau kebijakan, izin, cadangan, ekspor, dan penghapusan sebelum menambahkan data nyata.",
        medical="Prediksi adalah perkiraan, bukan kontrasepsi atau diagnosis. Jangan gunakan untuk mencegah kehamilan; jika khawatir soal kesehatan, konsultasikan tenaga kesehatan berkualifikasi.",
        source=("Konteks resmi Apple, bukan dukungan", "Apple: data, perkiraan, notifikasi, ekspor, dan batas Cycle Tracking", "Privasi Apple Health: enkripsi, iCloud, ekspor, dan pihak ketiga", "Apple hanya mendokumentasikan Health dan Cycle Tracking Apple, bukan Cyca, dan tidak merekomendasikan daftar ini atau Cyca."),
        web=("Pratinjau API imperatif WebMCP Chrome", "Membuat daftar periksa deterministik dari preferensi terbatas dan non-medis; tidak menerima tanggal, riwayat, gejala, aktivitas intim, niat kehamilan, nama, teks bebas, berkas, atau data pribadi."),
        app=("Ingin membandingkan satu opsi yang ada?", "Cyca bersifat opsional. Posisi terverifikasinya adalah privat, di perangkat, dan sekali bayar. Periksa halaman terkini untuk ketersediaan, fitur, dan privasi pastinya.", "Lihat Cyca di App Store"),
        faq=("Pertanyaan privasi", (("Apakah halaman ini menerima data siklus?", "Tidak; hanya preferensi terbatas."), ("Apakah ini menyertifikasi aplikasi?", "Tidak; ia tidak mengaudit atau menilai aplikasi."), ("Apakah prediksi berfungsi sebagai kontrasepsi?", "Tidak; itu hanya perkiraan."), ("Apakah privasi dijamin?", "Tidak; periksa kebijakan dan kontrol terkini."))),
        footer="Hanya preferensi privat · tanpa data kesehatan · periksa sebelum mencatat",
        features=("Gratis · hitung lokal · tanpa data kesehatan", "Tanpa tanggal, gejala, atau riwayat", "Tanpa nama, akun, atau teks bebas", "Tanpa unggahan, analitik, atau iklan", "Membandingkan preferensi; tidak menyertifikasi aplikasi mana pun"),
        inline="Bandingkan persyaratan privasi sebelum memilih pelacak siklus", index=("Daftar periksa privasi pemilihan pelacak siklus", "Buat persyaratan data minimum tanpa memasukkan info siklus atau kesehatan."),
    ),
    "tr": dict(
        title="Döngü Takipçisi Seçmek İçin Özel Kontrol Listesi | Sağlık Verisi Yok", tools="Ücretsiz araçlar", switch="English",
        heading="Döngü takipçisi seçmek için özel kontrol listesi", lead="Tarih, belirti, döngü geçmişi, mahrem etkinlik, gebelik niyeti veya kişisel veri girmeden gizlilik tercihlerini karşılaştırın.",
        planner="Asgari gizlilik gereksinimlerinizi belirleyin",
        labels=("Depolama", "Hesap", "Genel amaç", "Bildirimler", "Üçüncü taraflarla paylaşım", "Ekran kilidi zorunlu", "Dışa aktarma gerekli"),
        options=(("Yalnızca cihazda", "Şifreli eşitleme", "Herhangi biri"), ("Hesap yok", "Hesap isteğe bağlı", "Herhangi biri"), ("Temel regl kaydı", "Örüntü incelemesi", "Randevu için özet"), ("Yok", "Sınırlı hatırlatma", "Regl tahmini"), ("Yok", "Yalnızca zorunlu", "Bilinmiyor")),
        yes_no=("Evet", "Hayır"), update="Gizlilik kontrol listesi oluştur",
        results=("Hazırlık profili", "Asgari veri kurulumu", "Kontrol edilecek sorular", "Bildirim ve dışa aktarma önerisi", "Güvenlik sınırı"),
        readiness=("Sıkı en aza indirme", "Veri en aza indirildi", "Kontrollerle esnek", "Seçmeden önce gözden geçir"),
        words=("Yalnızca cihazda saklamayı tercih edin ve yedekleri kontrol edin.", "Şifreleme, kurtarma ve silmeyi kontrol edin.", "Yerel ve eşitlenmiş kullanımı karşılaştırın.", "Hesap zorunlu uygulamaları eleyin.", "Hesapsız kullanımı tercih edin.", "Hesap varsa toplamayı ve silmeyi inceleyin.", "Yalnızca gereken asgari kaydı tutun.", "Örüntülere genel bakın; her tahmin bir tahmindir.", "Yalnızca randevu için gereken özeti dışa aktarın.", "Döngü bildirimlerini kapatın.", "Yalnızca kendi seçtiğiniz gizli hatırlatmaları kullanın.", "Her regl bildirimini bir tahmin olarak görün.", "Üçüncü taraflara izin vermeyin.", "Amacı, veriyi ve süreyi sınırlayın.", "Veriyi kimin, hangi politikayla aldığını netleştirin.", "Cihaz veya uygulama koruması isteyin.", "Hassas veri nedeniyle kilidi yeniden değerlendirin.", "Biçimi, alanları, hedefi ve güvenli silmeyi kontrol edin.", "Belirli bir gereksinim olmadan dışa aktarmayın."),
        questions=("Veriler nerede saklanır ve nasıl şifrelenir?", "Hesapsız çalışır mı ve her şey silinebilir mi?", "Hangi üçüncü taraflar veri alır ve erişim geri alınabilir mi?", "Bildirimlerde, dışa aktarmalarda ve yedeklerde ne görünür?"),
        safety="Hiçbir takipçi mutlak gizlilik garanti etmez. Gerçek veri eklemeden önce politikayı, izinleri, yedekleri, dışa aktarmayı ve silmeyi inceleyin.",
        medical="Tahminler birer tahmindir, doğum kontrolü veya teşhis değildir. Gebeliği önlemek için kullanmayın; bir sağlık endişeniz varsa nitelikli bir sağlık uzmanına danışın.",
        source=("Resmi Apple bağlamı, bir onay değil", "Apple: Cycle Tracking verileri, tahminleri, bildirimleri, dışa aktarımı ve sınırları", "Apple Health gizliliği: şifreleme, iCloud, dışa aktarma ve üçüncü taraflar", "Apple yalnızca Apple Health ve Cycle Tracking'i belgeler, Cyca'yı değil ve ne bu listeyi ne de Cyca'yı önerir."),
        web=("Chrome zorunlu WebMCP API önizlemesi", "Sınırlı ve tıbbi olmayan tercihlerden belirlenimci bir kontrol listesi oluşturur; tarih, geçmiş, belirti, mahrem etkinlik, gebelik niyeti, ad, serbest metin, dosya veya kişisel veri kabul etmez."),
        app=("Mevcut bir seçeneği karşılaştırmak ister misiniz?", "Cyca isteğe bağlıdır. Doğrulanmış konumu özel, cihazda ve tek seferlik ödemedir. Kesin kullanılabilirlik, özellikler ve gizlilik için güncel sayfaya bakın.", "Cyca'yı App Store'da görüntüleyin"),
        faq=("Gizlilik soruları", (("Bu sayfa döngü verisi alıyor mu?", "Hayır; yalnızca sınırlı tercihler."), ("Bir uygulamayı sertifikalıyor mu?", "Hayır; hiçbir uygulamayı denetlemez veya puanlamaz."), ("Tahmin bir doğum kontrolü mü?", "Hayır; yalnızca bir tahmindir."), ("Gizlilik garanti mi?", "Hayır; güncel politikaları ve denetimleri kontrol edin."))),
        footer="Yalnızca özel tercihler · sağlık verisi yok · kaydetmeden önce kontrol edin",
        features=("Ücretsiz · yerel hesap · sağlık verisi yok", "Tarih, belirti veya geçmiş yok", "Ad, hesap veya serbest metin yok", "Yükleme, analitik veya reklam yok", "Tercihleri karşılaştırır; hiçbir uygulamayı sertifikalamaz"),
        inline="Bir döngü takipçisi seçmeden önce gizlilik gereksinimlerini karşılaştırın", index=("Döngü takipçisi seçimi için özel kontrol listesi", "Döngü veya sağlık bilgisi girmeden asgari veri gereksinimleri oluşturun."),
    ),
    "hi": dict(
        title="साइकल ट्रैकर चुनने की निजी जाँच-सूची | कोई स्वास्थ्य डेटा नहीं", tools="मुफ़्त उपकरण", switch="English",
        heading="साइकल ट्रैकर चुनने की निजी जाँच-सूची", lead="तारीख़, लक्षण, चक्र इतिहास, अंतरंग गतिविधि, गर्भावस्था की मंशा या व्यक्तिगत डेटा दर्ज किए बिना गोपनीयता प्राथमिकताएँ तुलना करें।",
        planner="अपनी न्यूनतम गोपनीयता आवश्यकताएँ तय करें",
        labels=("संग्रहण", "खाता", "सामान्य उद्देश्य", "सूचनाएँ", "तृतीय-पक्ष साझाकरण", "स्क्रीन लॉक अनिवार्य", "निर्यात आवश्यक"),
        options=(("केवल डिवाइस पर", "एन्क्रिप्टेड सिंक", "कोई भी"), ("कोई खाता नहीं", "खाता वैकल्पिक", "कोई भी"), ("मूल मासिक-धर्म रिकॉर्ड", "पैटर्न समीक्षा", "अपॉइंटमेंट हेतु सारांश"), ("कोई नहीं", "सीमित अनुस्मारक", "पीरियड अनुमान"), ("कुछ नहीं", "केवल अनिवार्य", "अज्ञात")),
        yes_no=("हाँ", "नहीं"), update="गोपनीयता जाँच-सूची बनाएँ",
        results=("तैयारी प्रोफ़ाइल", "न्यूनतम-डेटा सेटअप", "जाँचने योग्य प्रश्न", "सूचना और निर्यात सलाह", "सुरक्षा सीमा"),
        readiness=("कठोर न्यूनतमकरण", "डेटा न्यूनतम", "जाँच सहित लचीला", "चुनने से पहले समीक्षा करें"),
        words=("केवल डिवाइस पर रखने को प्राथमिकता दें और बैकअप जाँचें।", "एन्क्रिप्शन, पुनर्प्राप्ति और मिटाना जाँचें।", "स्थानीय और सिंक उपयोग की तुलना करें।", "अनिवार्य-खाता ऐप हटाएँ।", "बिना खाते के उपयोग को प्राथमिकता दें।", "खाता हो तो संग्रह और मिटाना जाँचें।", "केवल आवश्यक न्यूनतम दर्ज करें।", "पैटर्न सामान्य रूप से देखें; हर पूर्वानुमान अनुमान है।", "केवल अपॉइंटमेंट के लिए ज़रूरी सारांश निर्यात करें।", "चक्र-सूचनाएँ बंद करें।", "केवल स्वयं चुने विवेकी अनुस्मारक रखें।", "हर पीरियड-सूचना को अनुमान मानें।", "तृतीय-पक्षों को अनुमति न दें।", "उद्देश्य, डेटा और अवधि सीमित करें।", "प्राप्तकर्ता और नीति स्पष्ट करें।", "डिवाइस या ऐप सुरक्षा माँगें।", "संवेदनशील डेटा के कारण लॉक पर पुनर्विचार करें।", "प्रारूप, फ़ील्ड, गंतव्य और सुरक्षित मिटाना जाँचें।", "स्पष्ट आवश्यकता के बिना निर्यात न करें।"),
        questions=("डेटा कहाँ रहता है और कैसे एन्क्रिप्ट होता है?", "क्या यह बिना खाते के चलता है और सब कुछ मिटा सकता है?", "कौन-से तृतीय-पक्ष डेटा पाते हैं और क्या पहुँच वापस ली जा सकती है?", "सूचनाओं, निर्यातों और बैकअप में क्या दिखता है?"),
        safety="कोई ट्रैकर पूर्ण गोपनीयता की गारंटी नहीं देता। वास्तविक डेटा जोड़ने से पहले नीति, अनुमतियाँ, बैकअप, निर्यात और मिटाना जाँचें।",
        medical="पूर्वानुमान केवल अनुमान हैं, गर्भनिरोधक या निदान नहीं। गर्भावस्था टालने के लिए इनका उपयोग न करें; स्वास्थ्य चिंता होने पर योग्य चिकित्सा पेशेवर से परामर्श करें।",
        source=("आधिकारिक Apple संदर्भ, कोई समर्थन नहीं", "Apple: Cycle Tracking का डेटा, अनुमान, सूचनाएँ, निर्यात और सीमाएँ", "Apple Health गोपनीयता: एन्क्रिप्शन, iCloud, निर्यात और तृतीय-पक्ष", "Apple केवल Apple Health और Cycle Tracking का दस्तावेज़ देता है, Cyca का नहीं, और न यह सूची न Cyca की सिफ़ारिश करता है।"),
        web=("Chrome अनिवार्य WebMCP API पूर्वावलोकन", "सीमित, ग़ैर-चिकित्सीय प्राथमिकताओं से एक निर्धारित जाँच-सूची बनाता है; तारीख़, इतिहास, लक्षण, अंतरंग गतिविधि, गर्भावस्था मंशा, नाम, मुक्त टेक्स्ट, फ़ाइल या व्यक्तिगत डेटा स्वीकार नहीं करता।"),
        app=("क्या किसी मौजूदा विकल्प से तुलना करना चाहते हैं?", "Cyca वैकल्पिक है। इसकी सत्यापित स्थिति निजी, ऑन-डिवाइस और एक-बार भुगतान है। सटीक उपलब्धता, विशेषताओं और गोपनीयता के लिए वर्तमान पृष्ठ देखें।", "App Store पर Cyca देखें"),
        faq=("गोपनीयता प्रश्न", (("क्या यह पृष्ठ चक्र डेटा लेता है?", "नहीं; केवल सीमित प्राथमिकताएँ।"), ("क्या यह किसी ऐप को प्रमाणित करता है?", "नहीं; यह किसी ऐप का ऑडिट या स्कोर नहीं करता।"), ("क्या अनुमान गर्भनिरोधक है?", "नहीं; यह केवल अनुमान है।"), ("क्या गोपनीयता की गारंटी है?", "नहीं; वर्तमान नीतियाँ और नियंत्रण जाँचें।"))),
        footer="केवल निजी प्राथमिकताएँ · कोई स्वास्थ्य डेटा नहीं · दर्ज करने से पहले जाँचें",
        features=("मुफ़्त · स्थानीय गणना · कोई स्वास्थ्य डेटा नहीं", "कोई तारीख़, लक्षण या इतिहास नहीं", "कोई नाम, खाता या मुक्त टेक्स्ट नहीं", "कोई अपलोड, विश्लेषण या विज्ञापन नहीं", "प्राथमिकताएँ तुलना करता है; किसी ऐप को प्रमाणित नहीं करता"),
        inline="साइकल ट्रैकर चुनने से पहले गोपनीयता आवश्यकताएँ तुलना करें", index=("साइकल ट्रैकर चयन की निजी जाँच-सूची", "चक्र या स्वास्थ्य जानकारी दर्ज किए बिना न्यूनतम-डेटा आवश्यकताएँ बनाएँ।"),
    ),
    "ms": dict(
        title="Senarai Semak Peribadi untuk Memilih Penjejak Kitaran | Tiada Data Kesihatan", tools="Alat percuma", switch="English",
        heading="Senarai semak peribadi untuk memilih penjejak kitaran", lead="Bandingkan keutamaan privasi tanpa memasukkan tarikh, simptom, sejarah kitaran, aktiviti intim, niat kehamilan atau data peribadi.",
        planner="Tetapkan keperluan privasi minimum anda",
        labels=("Storan", "Akaun", "Tujuan umum", "Pemberitahuan", "Perkongsian pihak ketiga", "Kunci skrin diwajibkan", "Eksport diperlukan"),
        options=(("Pada peranti sahaja", "Segerak tersulit", "Mana-mana"), ("Tiada akaun", "Akaun pilihan", "Mana-mana"), ("Rekod haid asas", "Semakan corak", "Ringkasan untuk temu janji"), ("Tiada", "Peringatan terhad", "Anggaran haid"), ("Tiada", "Hanya yang wajib", "Tidak diketahui")),
        yes_no=("Ya", "Tidak"), update="Bina senarai semak privasi",
        results=("Profil kesediaan", "Persediaan data minimum", "Soalan untuk disemak", "Nasihat pemberitahuan dan eksport", "Sempadan keselamatan"),
        readiness=("Peminimuman ketat", "Data diminimumkan", "Fleksibel dengan semakan", "Semak sebelum memilih"),
        words=("Utamakan simpanan pada peranti sahaja dan semak sandaran.", "Semak penyulitan, pemulihan dan pemadaman.", "Bandingkan penggunaan setempat dan disegerak.", "Ketepikan aplikasi yang mewajibkan akaun.", "Utamakan penggunaan tanpa akaun.", "Jika ada akaun, semak pengumpulan dan pemadaman.", "Rekod hanya minimum yang diperlukan.", "Lihat corak secara umum; setiap ramalan hanyalah anggaran.", "Eksport hanya ringkasan yang diperlukan untuk temu janji.", "Matikan pemberitahuan kitaran.", "Guna hanya peringatan bijaksana yang anda pilih sendiri.", "Anggap setiap pemberitahuan haid sebagai anggaran.", "Jangan benarkan pihak ketiga.", "Hadkan tujuan, data dan tempoh.", "Jelaskan siapa penerima dan polisi yang terpakai.", "Wajibkan perlindungan peranti atau aplikasi.", "Pertimbang semula kunci kerana data sensitif.", "Semak format, medan, destinasi dan pemadaman selamat.", "Jangan eksport tanpa keperluan khusus."),
        questions=("Di mana data disimpan dan bagaimana ia disulitkan?", "Adakah ia berfungsi tanpa akaun dan boleh memadam semuanya?", "Pihak ketiga mana menerima data dan bolehkah akses ditarik balik?", "Apa yang muncul dalam pemberitahuan, eksport dan sandaran?"),
        safety="Tiada penjejak menjamin privasi mutlak. Semak polisi, kebenaran, sandaran, eksport dan pemadaman sebelum menambah data sebenar.",
        medical="Ramalan hanyalah anggaran, bukan kontraseptif atau diagnosis. Jangan guna untuk mengelak kehamilan; jika ada kebimbangan kesihatan, rujuk profesional kesihatan bertauliah.",
        source=("Konteks rasmi Apple, bukan sokongan", "Apple: data, anggaran, pemberitahuan, eksport dan had Cycle Tracking", "Privasi Apple Health: penyulitan, iCloud, eksport dan pihak ketiga", "Apple hanya mendokumenkan Apple Health dan Cycle Tracking, bukan Cyca, dan tidak mengesyorkan senarai ini mahupun Cyca."),
        web=("Pratonton API imperatif WebMCP Chrome", "Membina senarai semak berketentuan daripada keutamaan terhad bukan perubatan; tidak menerima tarikh, sejarah, simptom, aktiviti intim, niat kehamilan, nama, teks bebas, fail atau data peribadi."),
        app=("Mahu membandingkan satu pilihan semasa?", "Cyca adalah pilihan. Kedudukan yang disahkan ialah peribadi, pada peranti dan bayaran sekali. Rujuk halaman semasa untuk ketersediaan, ciri dan privasi yang tepat.", "Lihat Cyca di App Store"),
        faq=("Soalan privasi", (("Adakah halaman ini menerima data kitaran?", "Tidak; hanya keutamaan terhad."), ("Adakah ia memperakui sesuatu aplikasi?", "Tidak; ia tidak mengaudit atau menskor aplikasi."), ("Bolehkah ramalan dijadikan kontraseptif?", "Tidak; ia hanya anggaran."), ("Adakah privasi dijamin?", "Tidak; semak polisi dan kawalan semasa."))),
        footer="Keutamaan peribadi sahaja · tiada data kesihatan · semak sebelum merekod",
        features=("Percuma · kiraan setempat · tiada data kesihatan", "Tiada tarikh, simptom atau sejarah", "Tiada nama, akaun atau teks bebas", "Tiada muat naik, analitik atau iklan", "Membandingkan keutamaan; tidak memperakui aplikasi"),
        inline="Bandingkan keperluan privasi sebelum memilih penjejak kitaran", index=("Senarai semak peribadi pemilihan penjejak kitaran", "Bina keperluan data minimum tanpa memasukkan maklumat kitaran atau kesihatan."),
    ),
    "ru": dict(
        title="Приватный чек-лист выбора трекера цикла | Без данных о здоровье", tools="Бесплатные инструменты", switch="English",
        heading="Приватный чек-лист выбора трекера цикла", lead="Сравнивайте требования к приватности, не вводя даты, симптомы, историю цикла, интимную активность, планы беременности или личные данные.",
        planner="Определите минимальные требования к приватности",
        labels=("Хранение", "Аккаунт", "Общая цель", "Уведомления", "Передача третьим лицам", "Обязательная блокировка экрана", "Нужен экспорт"),
        options=(("Только на устройстве", "Шифрованная синхронизация", "Любое"), ("Без аккаунта", "Аккаунт по желанию", "Любой"), ("Базовые записи менструации", "Просмотр закономерностей", "Сводка для приёма"), ("Нет", "Ограниченные напоминания", "Прогноз месячных"), ("Ничего", "Только необходимое", "Неизвестно")),
        yes_no=("Да", "Нет"), update="Создать чек-лист приватности",
        results=("Профиль готовности", "Настройка с минимумом данных", "Вопросы для проверки", "Совет по уведомлениям и экспорту", "Граница безопасности"),
        readiness=("Строгая минимизация", "Данные минимизированы", "Гибко с проверками", "Проверить перед выбором"),
        words=("Предпочитайте хранение только на устройстве и проверяйте резервные копии.", "Проверьте шифрование, восстановление и удаление.", "Сравните локальное и синхронизированное использование.", "Исключите приложения с обязательным аккаунтом.", "Предпочитайте работу без аккаунта.", "Если аккаунт есть, проверьте сбор и удаление данных.", "Записывайте только необходимый минимум.", "Смотрите на закономерности в целом; любой прогноз — оценка.", "Экспортируйте только сводку, нужную для приёма.", "Отключите уведомления о цикле.", "Оставьте только выбранные вами неброские напоминания.", "Считайте каждое уведомление о месячных оценкой.", "Не разрешайте передачу третьим лицам.", "Ограничьте цель, данные и срок.", "Уточните получателя и применимую политику.", "Требуйте защиту устройства или приложения.", "Пересмотрите блокировку: данные чувствительные.", "Проверьте формат, поля, назначение и безопасное удаление.", "Не экспортируйте без конкретной необходимости."),
        questions=("Где хранятся данные и как они шифруются?", "Работает ли без аккаунта и можно ли удалить всё?", "Какие третьи лица получают данные и отзывается ли доступ?", "Что видно в уведомлениях, экспортах и резервных копиях?"),
        safety="Ни один трекер не гарантирует абсолютную приватность. Перед вводом реальных данных проверьте политику, разрешения, резервные копии, экспорт и удаление.",
        medical="Прогнозы — это оценки, а не контрацепция и не диагноз. Не используйте их для предотвращения беременности; при проблемах со здоровьем обратитесь к квалифицированному врачу.",
        source=("Официальный контекст Apple, а не одобрение", "Apple: данные, оценки, уведомления, экспорт и ограничения Cycle Tracking", "Приватность Apple Health: шифрование, iCloud, экспорт и третьи лица", "Apple документирует только Apple Health и Cycle Tracking, а не Cyca, и не рекомендует ни этот чек-лист, ни Cyca."),
        web=("Предварительная версия императивного API WebMCP в Chrome", "Строит детерминированный чек-лист из ограниченных немедицинских предпочтений; не принимает даты, историю, симптомы, интимную активность, планы беременности, имена, свободный текст, файлы или личные данные."),
        app=("Хотите сравнить один из текущих вариантов?", "Cyca — по желанию. Подтверждённое позиционирование: приватно, на устройстве, разовая оплата. Точную доступность, функции и приватность смотрите на актуальной странице.", "Открыть Cyca в App Store"),
        faq=("Вопросы о приватности", (("Получает ли страница данные цикла?", "Нет; только ограниченные предпочтения."), ("Сертифицирует ли она приложения?", "Нет; она не проверяет и не оценивает приложения."), ("Можно ли использовать прогноз как контрацепцию?", "Нет; это лишь оценка."), ("Гарантируется ли приватность?", "Нет; проверяйте актуальные политики и настройки."))),
        footer="Только приватные предпочтения · без данных о здоровье · проверяйте перед записью",
        features=("Бесплатно · локальный расчёт · без данных о здоровье", "Без дат, симптомов и истории", "Без имён, аккаунтов и свободного текста", "Без загрузок, аналитики и рекламы", "Сравнивает предпочтения; не сертифицирует приложения"),
        inline="Сравните требования к приватности перед выбором трекера цикла", index=("Приватный чек-лист выбора трекера цикла", "Составьте требования с минимумом данных, не вводя сведения о цикле или здоровье."),
    ),
}.items():
    _w = _data.pop("words")
    _notes = tuple(tuple(_w[i:i + 3]) for i in range(0, 15, 3)) + (tuple(_w[15:17]), tuple(_w[17:19]))
    _faq_title, _faq_values = _data.pop("faq")
    _localized(_locale, notes=_notes, source_text=_data.pop("source"), webmcp=_data.pop("web"),
               faq_title=_faq_title, faq=_faq_values, **_data)

STYLE = """
:root{color-scheme:light;--ink:#18221f;--muted:#586660;--paper:#fbfcf9;--card:#fff;--line:#dce5df;--accent:#356c5a;--soft:#edf5f0}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.wrap{width:min(1120px,96%);margin:auto}.top{border-bottom:1px solid var(--line);background:#ffffffdd}.nav{display:flex;justify-content:space-between;align-items:center;padding:14px 0}.nav a{color:var(--ink);font-weight:700;text-decoration:none;white-space:nowrap}.links{display:flex;gap:18px}.hero{padding:66px 0 30px}.eyebrow{color:var(--accent);font-weight:800;white-space:nowrap}h1{font-size:clamp(2rem,5vw,4rem);line-height:1.08;max-width:900px}.lead{font-size:1.16rem;color:var(--muted);max-width:850px}.badges{display:flex;flex-wrap:wrap;gap:8px}.badge{padding:7px 11px;border:1px solid var(--line);border-radius:99px;background:var(--card);white-space:nowrap}.planner,.card,.app-card{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:clamp(20px,4vw,38px);box-shadow:0 16px 45px #203b2d0b}.controls,.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.field{display:grid;gap:6px}.field label,.toggle{font-weight:750;white-space:nowrap}select{width:100%;padding:12px;border:1px solid var(--line);border-radius:12px;background:#fff;font:inherit}.toggle{display:flex;align-items:center;gap:9px}.button{display:inline-block;border:0;border-radius:99px;padding:12px 18px;background:var(--accent);color:#fff;text-decoration:none;font-weight:800;white-space:nowrap}.results{margin-top:22px}.result,.note{padding:14px;border-radius:14px;background:var(--soft)}.result{display:flex;justify-content:space-between;gap:15px}.note strong,.result strong{white-space:nowrap}.grid{margin-top:24px}.faq,.app-card{margin-top:24px}details{border-top:1px solid var(--line);padding:12px 0}summary{font-weight:750;cursor:pointer}.source-list a{overflow-wrap:anywhere}.footer{margin-top:42px;padding:25px 0;border-top:1px solid var(--line);color:var(--muted);text-align:center}.footer div{white-space:nowrap}
@media(max-width:520px){.links{gap:10px}.hero{padding-top:42px}.result{display:grid}.footer div{font-size:.78rem}}
"""

SCRIPT = r"""
(() => {
  "use strict";
  const config = JSON.parse(document.getElementById("cycle-config").textContent);
  const form = document.getElementById("cycle-planner");
  const fields = {
    storage_preference: document.getElementById("storage-preference"),
    account_preference: document.getElementById("account-preference"),
    use_case: document.getElementById("use-case"),
    notification_preference: document.getElementById("notification-preference"),
    third_party_sharing_tolerance: document.getElementById("sharing-tolerance"),
    screen_lock_required: document.getElementById("screen-lock"),
    export_needed: document.getElementById("export-needed")
  };
  const output = {
    readiness: document.getElementById("result-readiness"),
    setup: document.getElementById("result-setup"),
    questions: document.getElementById("result-questions"),
    advice: document.getElementById("result-advice"),
    safety: document.getElementById("result-safety")
  };

  function requireEnum(name, value) {
    const allowed = config.inputSchema.properties[name].enum;
    if (typeof value !== "string" || !allowed.includes(value)) {
      throw new RangeError(`${name} is outside its allowed choices.`);
    }
    return value;
  }
  function requireBoolean(name, value) {
    if (typeof value !== "boolean") throw new TypeError(`${name} must be boolean.`);
    return value;
  }
  function calculateCyclePrivacyPlan(input) {
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
    const storage = requireEnum("storage_preference", input.storage_preference);
    const account = requireEnum("account_preference", input.account_preference);
    const useCase = requireEnum("use_case", input.use_case);
    const notification = requireEnum("notification_preference", input.notification_preference);
    const sharing = requireEnum("third_party_sharing_tolerance", input.third_party_sharing_tolerance);
    const lock = requireBoolean("screen_lock_required", input.screen_lock_required);
    const exportNeeded = requireBoolean("export_needed", input.export_needed);
    let readiness = "flexible";
    if (sharing === "unknown") readiness = "review-first";
    else if (storage === "device-only" && account === "no-account" && sharing === "none" && lock) readiness = "strict";
    else if (sharing === "none" && account !== "any") readiness = "minimized";
    return {
      readiness: config.readiness[readiness],
      readiness_code: readiness,
      minimal_setup: [
        config.notes.storage[storage],
        config.notes.account[account],
        config.notes.use_case[useCase],
        lock ? config.notes.lock.yes : config.notes.lock.no
      ],
      privacy_questions: config.questions,
      notification_export_advice: [
        config.notes.notification[notification],
        config.notes.sharing[sharing],
        exportNeeded ? config.notes.export.yes : config.notes.export.no
      ],
      safety_boundary: `${config.safety} ${config.medical}`
    };
  }
  function visibleInput() {
    return {
      storage_preference: fields.storage_preference.value,
      account_preference: fields.account_preference.value,
      use_case: fields.use_case.value,
      notification_preference: fields.notification_preference.value,
      third_party_sharing_tolerance: fields.third_party_sharing_tolerance.value,
      screen_lock_required: fields.screen_lock_required.checked,
      export_needed: fields.export_needed.checked
    };
  }
  function render() {
    const result = calculateCyclePrivacyPlan(visibleInput());
    output.readiness.textContent = result.readiness;
    output.setup.textContent = result.minimal_setup.join(" ");
    output.questions.textContent = result.privacy_questions.join(" ");
    output.advice.textContent = result.notification_export_advice.join(" ");
    output.safety.textContent = result.safety_boundary;
  }
  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_cycle_tracker_choice",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const checklist = calculateCyclePrivacyPlan(input);
        const result = {
          result_type: "private_cycle_tracker_choice_checklist",
          health_or_personal_data_not_received_or_processed: true,
          not_an_app_rating_or_privacy_guarantee: true,
          not_for_birth_control_or_diagnosis: true,
          checklist,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) result.optional_cyca = config.optionalApp;
        return JSON.stringify(result);
      }
    });
  }
  form.addEventListener("submit", (event) => { event.preventDefault(); render(); });
  for (const field of Object.values(fields)) field.addEventListener("change", render);
  render();
  registerWebMcp().catch((error) => console.error("WebMCP tool registration failed.", error));
})();
"""


def canonical(locale: str) -> str:
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + payload.replace("</", "<\\/") + "</script>"


def select_options(values: tuple[str, ...], labels: tuple[str, ...]) -> str:
    return "".join(
        f'<option value="{html.escape(value, quote=True)}">{html.escape(label)}</option>'
        for value, label in zip(values, labels, strict=True)
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    properties = {
        "storage_preference": {"type": "string", "enum": list(STORAGE)},
        "account_preference": {"type": "string", "enum": list(ACCOUNTS)},
        "use_case": {"type": "string", "enum": list(USE_CASES)},
        "notification_preference": {"type": "string", "enum": list(NOTIFICATIONS)},
        "third_party_sharing_tolerance": {"type": "string", "enum": list(SHARING)},
        "screen_lock_required": {"type": "boolean"},
        "export_needed": {"type": "boolean"},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool = False) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    url = canonical(locale)
    prefix = "" if locale == "en" else f"{locale}/"
    home, tools = f"{SITE}/{prefix}index.html", f"{SITE}/{prefix}tools/index.html"
    alternate = canonical("zh-Hant" if locale == "en" else "en")
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{item}" href="{canonical(item)}">'
        for item in ALT_LOCALES
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    sources = (APPLE_CYCLE_TRACKING, APPLE_HEALTH_PRIVACY)
    source_items = "".join(
        f'<li><a href="{source}" rel="noopener">{html.escape(label)}</a></li>'
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_cycle_privacy_{locale.lower()}") if app_public else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            f'<section class="app-card wrap"><h2>{html.escape(t["app_title"])}</h2>'
            f'<p>{html.escape(t["app_text"])}</p><a class="button" href="'
            f'{html.escape(tracked_app_url, quote=True)}" rel="nofollow noopener">'
            f'{html.escape(t["app_cta"])}</a></section>'
        )
    notes = {
        "storage": t["storage_notes"],
        "account": t["account_notes"],
        "use_case": t["use_notes"],
        "notification": t["notification_notes"],
        "sharing": t["sharing_notes"],
        "lock": {"yes": t["lock_yes"], "no": t["lock_no"]},
        "export": {"yes": t["export_yes"], "no": t["export_no"]},
    }
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "readiness": t["readiness_labels"],
        "notes": notes,
        "questions": t["privacy_questions"],
        "safety": t["safety_boundary"],
        "medical": t["medical_boundary"],
        "toolDescription": t["webmcp_description"],
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(t["source_labels"], sources, strict=True)
        ],
        "webmcpSource": WEBMCP_SOURCE,
        "optionalApp": (
            {"label": t["app_cta"], "boundary": t["app_text"], "app_store_url": tracked_app_url}
            if tracked_app_url else None
        ),
    }
    config_json = json.dumps(config, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    schema = {
        "@context": "https://schema.org", "@type": "WebApplication",
        "name": t["heading"], "description": t["description"], "url": url,
        "inLanguage": locale, "datePublished": CONTENT_DATE, "dateModified": CONTENT_DATE,
        "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
        "isAccessibleForFree": True, "featureList": list(t["feature_list"]),
        "citation": list(sources),
    }
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage", "inLanguage": locale,
        "mainEntity": [
            {"@type": "Question", "name": question,
             "acceptedAnswer": {"@type": "Answer", "text": answer}}
            for question, answer in t["faq"]
        ],
    }
    return f"""<!DOCTYPE html>
<html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title><meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">{alternates}
<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(t["heading"])}"><meta property="og:description" content="{html.escape(t["description"])}"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary"><style>{STYLE}</style>{json_script(schema)}{json_script(faq_schema)}{feed_discovery_links()}</head>
<body><header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main><section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{''.join(f'<span class="badge">{html.escape(x)}</span>' for x in t["badges"])}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="cycle-planner"><div class="controls">
<div class="field"><label for="storage-preference">{html.escape(t["storage_label"])}</label><select id="storage-preference">{select_options(STORAGE, tuple(t["storage_options"].values()))}</select></div>
<div class="field"><label for="account-preference">{html.escape(t["account_label"])}</label><select id="account-preference">{select_options(ACCOUNTS, tuple(t["account_options"].values()))}</select></div>
<div class="field"><label for="use-case">{html.escape(t["use_label"])}</label><select id="use-case">{select_options(USE_CASES, tuple(t["use_options"].values()))}</select></div>
<div class="field"><label for="notification-preference">{html.escape(t["notification_label"])}</label><select id="notification-preference">{select_options(NOTIFICATIONS, tuple(t["notification_options"].values()))}</select></div>
<div class="field"><label for="sharing-tolerance">{html.escape(t["sharing_label"])}</label><select id="sharing-tolerance">{select_options(SHARING, tuple(t["sharing_options"].values()))}</select></div>
<label class="toggle"><input id="screen-lock" type="checkbox" checked>{html.escape(t["lock_label"])}</label>
<label class="toggle"><input id="export-needed" type="checkbox">{html.escape(t["export_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["readiness_title"])}</strong><span id="result-readiness"></span></div></div>
<p class="note"><strong>{html.escape(t["setup_title"])}:</strong> <span id="result-setup"></span></p>
<p class="note"><strong>{html.escape(t["questions_title"])}:</strong> <span id="result-questions"></span></p>
<p class="note"><strong>{html.escape(t["handling_title"])}:</strong> <span id="result-advice"></span></p>
<p class="note"><strong>{html.escape(t["safety_title"])}:</strong> <span id="result-safety"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article>
<article class="card"><h2>{html.escape(t["safety_title"])}</h2><p>{html.escape(t["safety_boundary"])}</p><p>{html.escape(t["medical_boundary"])}</p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>{app_card}</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="cycle-config">{config_json}</script><script>{SCRIPT}</script></body></html>
"""


def index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="{SLUG}.html">'
        f'{html.escape(t["index_title"])}</a></h2><p>{html.escape(t["index_description"])}</p></article>'
    )


def update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>', re.S,
    )
    updated = existing.sub("", text)
    marker = '<section class="wrap grid">'
    if marker not in updated:
        # Lite-generated hub (vi/th/id/tr) uses a different structure and is
        # rebuilt by gen_tools_index_lite; skip rather than fail.
        if '<div class="grid">' in updated:
            return False
        raise RuntimeError(f"{path} is missing its tools grid")
    updated = updated.replace(marker, marker + index_card(locale), 1)
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
    "offline-period-tracker-no-account.html",
    "simple-cycle-tracking-app-no-account.html",
)
INBOUND_LINK_CLASS = "cycle-privacy-planner-inline-link"
_CYCA_CTA = re.compile(
    r'<a\b(?=[^>]*\shref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id' + re.escape(APP_ID) + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)


def insert_answer_links(pages: Path = PAGES) -> int:
    changed = 0
    for locale in ALT_LOCALES:
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
        link = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" data-cycle-privacy-planner-link="1" '
            f'href="{canonical(locale)}" rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS:
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _CYCA_CTA.search(text)
            if match and write_text_if_changed(path, text[:match.start()] + link + text[match.start():]):
                changed += 1
    return changed


def build(pages: Path = PAGES, app_public: bool = False) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        root = pages if locale == "en" else pages / locale
        write_text_if_changed(root / "tools" / f"{SLUG}.html", render_page(locale, app_public))
        update_one_index(root / "tools" / "index.html", locale)
        outputs.append(canonical(locale))
    insert_answer_links(pages)
    return outputs


def main() -> None:
    app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
    outputs = build(app_public=app_public)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"cycle privacy planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


_localized(
    "zh-Hans",
    title="私密周期记录工具选择清单｜不输入健康数据", tools="免费工具", switch="English",
    heading="私密周期记录工具选择清单", lead="不输入日期、症状、周期记录、性行为、怀孕意向或个人信息，只比较隐私偏好。",
    planner="设定最低隐私要求",
    labels=("存储偏好", "账号偏好", "一般用途", "通知偏好", "第三方共享容忍度", "必须锁定屏幕", "需要导出"),
    options=(("仅限设备", "加密同步", "均可"), ("不需要账号", "账号可选", "不限"), ("基本经期记录", "查看规律", "就诊摘要"), ("关闭", "少量提醒", "经期估算"), ("不允许", "仅必要项目", "不确定")),
    yes_no=("是", "否"), update="生成隐私核对清单",
    results=("隐私准备类型", "数据最小化设置", "选择前核对问题", "通知与导出建议", "安全界线"),
    readiness=("严格最小化", "数据最小化", "弹性但需核对", "选择前先查清楚"),
    notes=(
        ("优先仅存设备，并核对备份。", "核对同步加密、恢复与删除方式。", "比较本机与同步存储的差异。"),
        ("排除强制注册的选择。", "优先选择不登录也能使用。", "如使用账号，核对资料收集与删除。"),
        ("只记录真正需要的最少项目。", "仅观察一般规律；所有预测仍是估算。", "只导出就诊真正需要的摘要。"),
        ("关闭所有周期通知。", "只保留你主动选择且内容低调的提醒。", "把经期通知视为估算，不是确定日期。"),
        ("不允许第三方共享。", "把用途、项目与保存期限降至最低。", "先确认接收方、用途与隐私政策。"),
        ("要求设备锁定或 App 内保护。", "周期记录较敏感，建议重新考虑开启锁定。"),
        ("核对格式、字段、目的地与安全删除方法。", "没有明确需要时关闭导出。"),
    ),
    questions=("数据存在哪里，如何加密？", "不注册能否使用，能否完整删除数据？", "哪些第三方会收到数据，授权能否撤回？", "通知、导出与备份会显示哪些内容？"),
    safety="任何周期记录工具都无法保证绝对隐私。输入真实记录前，请检查最新隐私政策、权限、备份、导出与删除控制。",
    medical="周期预测只是估算，不能用于避孕，也不能诊断健康状况。请勿用于避免怀孕；如有健康疑虑，请咨询合格医疗专业人员。",
    source_text=("Apple 官方背景资料，不代表推荐", "Apple：Cycle Tracking 的输入资料、估算、通知、导出与限制", "Apple 健康 App 隐私：加密、iCloud、导出与第三方", "Apple 资料只说明 Apple 健康 App 与 Cycle Tracking，不代表 Cyca 的功能，也不代表 Apple 推荐本清单或 Cyca。"),
    webmcp=("Chrome imperative WebMCP API 预览", "只根据有范围、非医疗的偏好生成固定清单；不接收日期、周期记录、症状、性行为、怀孕意向、姓名、自由文字、文件或个人信息。"),
    app=("要比较一个现有选择吗？", "Cyca 已验证的定位为一次付费、重视隐私、资料保留在设备上。实际供应地区、功能与隐私细节，请查看目前商店页面。", "在 App Store 查看 Cyca"),
    faq_title="隐私核对问题",
    faq=(("这个页面会接收周期数据吗？", "不会，只接收有范围的偏好。"), ("它会认证或评分 App 吗？", "不会，不审计、不评分任何 App。"), ("周期估算可以用于避孕吗？", "不可以，它只是估算。"), ("它能保证隐私吗？", "不能，请核对各服务目前的政策与设置。")),
    footer="只用偏好 · 不含健康数据 · 输入记录前先核对",
    features=("免费 · 本机计算 · 不输入健康数据", "不输入日期、症状或周期记录", "不输入姓名、账号或自由文字", "不上传、不分析、不投放广告", "比较需求，不认证任何 App"),
    inline="选择周期记录工具前先比较隐私要求",
    index=("私密周期记录工具选择清单", "不输入周期或健康数据，整理数据最小化需求。"),
)

for _locale, _data in {
    "ja": dict(
        title="プライベートな周期記録アプリ選びチェックリスト｜健康データ入力なし", tools="無料ツール", switch="English",
        heading="プライベートな周期記録アプリ選びチェックリスト", lead="日付、症状、周期履歴、性行為、妊娠希望、個人情報を入力せず、プライバシー要件を整理します。",
        planner="最低限のプライバシー要件を決める",
        labels=("保存方法", "アカウント", "一般的な用途", "通知", "第三者共有", "画面ロック必須", "書き出し必須"),
        options=(("端末内のみ", "暗号化同期", "どちらでも"), ("アカウント不要", "任意", "問わない"), ("月経の基本記録", "傾向の確認", "受診用の要約"), ("なし", "限定したリマインダー", "月経予測"), ("なし", "必要最小限", "不明")),
        yes_no=("はい", "いいえ"), update="プライバシーチェックリストを作成",
        results=("準備プロファイル", "データ最小化設定", "確認する質問", "通知と書き出しの助言", "安全上の境界"),
        readiness=("厳格な最小化", "データを最小化", "確認を伴う柔軟設定", "選択前に要確認"),
        words=("端末内保存を優先しバックアップも確認。", "暗号化、復旧、削除を確認。", "端末内と同期の違いを比較。", "必須アカウントを除外。", "アカウントなしで使えるものを優先。", "使う場合は収集と削除を確認。", "必要最小限だけ記録。", "傾向は一般的に確認し予測は推定として扱う。", "必要項目だけ受診用に書き出す。", "周期通知を無効化。", "選んだ控えめな通知だけ使う。", "月経通知は推定として扱う。", "第三者共有を許可しない。", "目的、項目、期間を最小限に。", "受領者とポリシーを確認。", "端末またはアプリの保護を必須に。", "機微な記録のためロックを再検討。", "形式、項目、送信先、安全な削除を確認。", "明確な必要がなければ書き出さない。"),
        questions=("データはどこに保存され、どう暗号化されますか？", "アカウントなしで使え、全データを削除できますか？", "どの第三者が受け取り、許可を取り消せますか？", "通知、書き出し、バックアップに何が表示されますか？"),
        safety="どの記録アプリも絶対的なプライバシーを保証できません。実際の記録前に最新の方針、権限、バックアップ、書き出し、削除方法を確認してください。",
        medical="周期予測は推定であり、避妊や診断には使えません。妊娠回避に使用せず、健康上の心配は資格を持つ医療専門家へ相談してください。",
        source=("Apple公式情報による背景説明（推奨ではありません）", "Apple：Cycle Trackingの入力データ、推定、通知、書き出し、限界", "Appleヘルスケアのプライバシー：暗号化、iCloud、書き出し、第三者", "Appleの記述はAppleヘルスケアとCycle Trackingについてのみで、Cycaの機能説明や、このツール／Cycaの推奨ではありません。"),
        web=("Chrome の imperative WebMCP API プレビュー", "医療情報ではない選択式の希望だけから固定チェックリストを作成。日付、履歴、症状、性行為、妊娠希望、氏名、自由記述、ファイル、個人情報は受け取りません。"),
        app=("現在の候補と比較しますか？", "確認済みのCycaの位置付けは、買い切り、プライベート、端末内です。正確な提供状況、機能、プライバシーは現在の掲載情報をご確認ください。", "App StoreでCycaを見る"),
        faq=("プライバシーに関する質問", (("周期データを受け取りますか？", "いいえ。選択式の希望だけです。"), ("アプリを認証しますか？", "いいえ。監査も採点もしません。"), ("予測は避妊に使えますか？", "いいえ。推定にすぎません。"), ("プライバシーは保証されますか？", "いいえ。最新の方針と設定を確認してください。"))),
        footer="選択式の希望のみ・健康データなし・記録前に確認",
        features=("無料・端末内計算・健康データ不要", "日付、症状、履歴を入力しない", "氏名、アカウント、自由記述なし", "アップロード、解析、広告なし", "要件を比較し、アプリを認証しない"),
        inline="周期記録アプリを選ぶ前にプライバシー要件を比較", index=("プライベートな周期記録アプリ選び", "周期・健康データを入力せず、データ最小化要件を整理します。"),
    ),
    "ko": dict(
        title="비공개 주기 기록 앱 선택 체크리스트 | 건강 데이터 입력 없음", tools="무료 도구", switch="English",
        heading="비공개 주기 기록 앱 선택 체크리스트", lead="날짜, 증상, 주기 기록, 성생활, 임신 의도, 개인정보를 입력하지 않고 개인정보 보호 요구사항을 정리하세요.",
        planner="최소 개인정보 보호 요구사항 정하기",
        labels=("저장 방식", "계정", "일반 용도", "알림", "제3자 공유", "화면 잠금 필수", "내보내기 필요"),
        options=(("기기에만 저장", "암호화 동기화", "무관"), ("계정 없음", "선택 사항", "무관"), ("기본 생리 기록", "패턴 검토", "진료용 요약"), ("없음", "제한된 알림", "생리 예상"), ("없음", "필수 항목만", "알 수 없음")),
        yes_no=("예", "아니요"), update="개인정보 체크리스트 만들기",
        results=("준비 상태", "데이터 최소화 설정", "확인할 질문", "알림 및 내보내기 조언", "안전 경계"),
        readiness=("엄격한 최소화", "데이터 최소화", "검토를 거친 유연한 설정", "선택 전 검토"),
        words=("기기 저장을 우선하고 백업을 확인하세요.", "암호화, 복구, 삭제 방식을 확인하세요.", "로컬과 동기화 사용을 비교하세요.", "필수 계정을 제외하세요.", "계정 없이 쓰는 방식을 우선하세요.", "계정 사용 시 수집과 삭제를 확인하세요.", "필요한 최소 정보만 기록하세요.", "패턴은 일반적으로 검토하고 예측은 추정치로 보세요.", "진료에 필요한 항목만 내보내세요.", "주기 알림을 끄세요.", "직접 고른 조용한 알림만 사용하세요.", "생리 알림은 추정치로 보세요.", "제3자 공유를 허용하지 마세요.", "목적, 항목, 기간을 최소화하세요.", "수신자와 정책을 확인하세요.", "기기 또는 앱 잠금을 요구하세요.", "민감한 기록이므로 잠금을 다시 검토하세요.", "형식, 항목, 대상, 안전한 삭제를 확인하세요.", "명확한 필요가 없다면 내보내지 마세요."),
        questions=("데이터는 어디에 저장되고 어떻게 암호화되나요?", "계정 없이 작동하며 모든 데이터를 삭제할 수 있나요?", "어떤 제3자가 받고 권한을 철회할 수 있나요?", "알림, 내보내기, 백업에는 무엇이 표시되나요?"),
        safety="어떤 기록 앱도 절대적인 개인정보 보호를 보장하지 않습니다. 실제 기록 전에 최신 정책, 권한, 백업, 내보내기, 삭제 방식을 확인하세요.",
        medical="주기 예측은 추정치이며 피임이나 진단 수단이 아닙니다. 임신 방지에 사용하지 말고 건강 우려는 자격을 갖춘 의료 전문가와 상담하세요.",
        source=("Apple 공식 배경 정보이며 추천이 아님", "Apple: Cycle Tracking 입력 데이터, 추정, 알림, 내보내기와 한계", "Apple 건강 앱 개인정보 보호: 암호화, iCloud, 내보내기와 제3자", "Apple 설명은 Apple 건강 앱과 Cycle Tracking에만 해당하며 Cyca의 기능 설명이나 이 도구 또는 Cyca의 추천이 아닙니다."),
        web=("Chrome imperative WebMCP API 미리보기", "의료 정보가 아닌 제한된 선택만으로 고정 체크리스트를 만듭니다. 날짜, 기록, 증상, 성생활, 임신 의도, 이름, 자유 입력, 파일, 개인정보를 받지 않습니다."),
        app=("현재 선택지와 비교할까요?", "확인된 Cyca의 포지셔닝은 일회성 구매, 비공개, 기기 내 처리입니다. 정확한 제공 여부, 기능, 개인정보 보호는 현재 스토어 정보를 확인하세요.", "App Store에서 Cyca 보기"),
        faq=("개인정보 보호 질문", (("주기 데이터를 받나요?", "아니요. 제한된 선택만 받습니다."), ("앱을 인증하나요?", "아니요. 감사하거나 점수를 매기지 않습니다."), ("예측을 피임에 쓸 수 있나요?", "아니요. 추정치일 뿐입니다."), ("개인정보 보호를 보장하나요?", "아니요. 최신 정책과 설정을 확인하세요."))),
        footer="제한된 선택만 · 건강 데이터 없음 · 기록 전 확인",
        features=("무료 · 로컬 계산 · 건강 데이터 없음", "날짜, 증상, 기록 입력 없음", "이름, 계정, 자유 입력 없음", "업로드, 분석, 광고 없음", "요구사항 비교용이며 앱을 인증하지 않음"),
        inline="주기 기록 앱 선택 전 개인정보 요구사항 비교", index=("비공개 주기 기록 앱 선택 체크리스트", "주기나 건강 데이터 없이 데이터 최소화 요구사항을 정리하세요."),
    ),
}.items():
    _w = _data.pop("words")
    _notes = tuple(tuple(_w[i:i + 3]) for i in range(0, 15, 3)) + (tuple(_w[15:17]), tuple(_w[17:19]))
    _faq_title, _faq_values = _data.pop("faq")
    _localized(_locale, notes=_notes, source_text=_data.pop("source"), webmcp=_data.pop("web"),
               faq_title=_faq_title, faq=_faq_values, **_data)

COPY["zh-Hans"]["switch"] = "英文"
COPY["ja"]["switch"] = "英語"
COPY["ko"]["switch"] = "영어"

if __name__ == "__main__":
    main()
