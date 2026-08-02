#!/usr/bin/env python3
"""Generate a nine-locale, private document scan planning tool."""

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
SLUG = "private-document-scan-planner"
APP_KEY = "scanto"
APP_ID = "6779977651"
CONTENT_DATE = "2026-07-15"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"
NARA_STANDARD = (
    "https://www.ecfr.gov/current/title-36/chapter-XII/subchapter-B/"
    "part-1236/subpart-E/section-1236.50"
)
FADGI_GUIDELINES = "https://www.digitizationguidelines.gov/guidelines/"
NARA_OCR = (
    "https://www.archives.gov/research/catalog/lcdrg/contribution/"
    "ocr-transcription"
)
APPLE_SCAN_DOCUMENTS = "https://support.apple.com/en-us/108963"

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

PAPERS = {
    "a4": {"width_mm": 210.0, "height_mm": 297.0},
    "a5": {"width_mm": 148.0, "height_mm": 210.0},
    "us-letter": {"width_mm": 215.9, "height_mm": 279.4},
    "us-legal": {"width_mm": 215.9, "height_mm": 355.6},
}
PURPOSES = {
    "everyday-text": {"dpi": 300},
    "small-print": {"dpi": 400},
    "fine-detail": {"dpi": 600},
}
COLOR_MODES = {
    "grayscale": {"bits_per_pixel": 8},
    "rgb": {"bits_per_pixel": 24},
}

COPY = {
    "en": {
        "title": "Private Document Scan Planner | DPI, Pixels & Size Bounds",
        "description": (
            "Plan document scan resolution, exact pixel dimensions and transparent "
            "uncompressed raster size bounds without uploading or reading a document."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · local math · no document upload",
        "heading": "Private document scan planner",
        "lead": (
            "Choose a paper size, detail profile and colour mode. The browser calculates "
            "pixels and theoretical uncompressed raster size; it never receives a document."
        ),
        "badges": (
            "No file or document input",
            "No OCR or cloud request",
            "No compressed-size guess",
            "No archival compliance claim",
        ),
        "planner": "Plan the capture",
        "planner_intro": (
            "The three detail profiles are planning starting points, not quality guarantees "
            "or official certification."
        ),
        "paper_label": "Paper size",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "US Letter · 8.5×11 in",
            "us-legal": "US Legal · 8.5×14 in",
        },
        "purpose_label": "Detail profile",
        "purpose_options": {
            "everyday-text": "Everyday text · 300 ppi",
            "small-print": "Small print or mixed marks · 400 ppi",
            "fine-detail": "Fine lines or stamps · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": (
                "A 300 ppi planning baseline for clear modern text. This does not certify "
                "OCR accuracy or records compliance."
            ),
            "small-print": (
                "A higher-detail 400 ppi option for small text or mixed marks. Inspect the "
                "first page before scanning a batch."
            ),
            "fine-detail": (
                "A 600 ppi option when fine lines or tiny marks matter. It increases memory "
                "substantially and still does not guarantee recognition."
            ),
        },
        "color_label": "Colour mode",
        "color_options": {
            "grayscale": "8-bit grayscale",
            "rgb": "24-bit RGB colour",
        },
        "color_notes": {
            "grayscale": (
                "Use only when colour does not carry meaning. Check stamps, highlights, "
                "handwriting and annotations first."
            ),
            "rgb": (
                "Use RGB when colour helps interpret stamps, highlights, handwriting, "
                "annotations or the original appearance."
            ),
        },
        "orientation_label": "Orientation",
        "orientation_options": {
            "portrait": "Portrait",
            "landscape": "Landscape",
        },
        "pages_label": "Page count",
        "calculate": "Update plan",
        "result_title": "Calculated scan plan",
        "dpi": "Selected ppi",
        "pixels": "Pixels per page",
        "megapixels": "Megapixels per page",
        "per_page": "Uncompressed MiB per page",
        "total": "Uncompressed MiB for all pages",
        "result_boundary": (
            "These MiB values are the mathematical pixel payload before file headers, "
            "compression, OCR text or PDF structure. Real PDF, JPEG and TIFF sizes vary, "
            "so this tool does not estimate a compressed file size."
        ),
        "capture_title": "Five checks before a batch",
        "capture_checks": (
            "Keep the full page and every edge visible; flatten folds without damaging the original.",
            "Use even light and check for glare, shadows, fingers, blur and clipped corners.",
            "Choose RGB whenever colour carries information; otherwise grayscale may be appropriate.",
            "Zoom into the first page and inspect the smallest important text or mark.",
            "Compare any OCR output with the image; OCR is not always accurate.",
        ),
        "scope_title": "What this planner cannot certify",
        "scope_text": (
            "It accepts no document, image, file, camera input, OCR text, free text, name or "
            "personal data. It does not scan, enhance, OCR, inspect, upload or store anything, "
            "and uses no cookies, analytics, ads or network requests. It cannot guarantee OCR, "
            "readability, quality, legal effect, accessibility, archival, government, tax, "
            "medical or education compliance. A chosen ppi may not be precisely controllable "
            "in every phone scanning app. Permanent, regulated or evidentiary records require "
            "the responsible authority's current specification and quality-control process."
        ),
        "sources_title": "Official context, not endorsement",
        "sources_intro": (
            "NARA and FADGI describe U.S. permanent-record and digitization contexts, not local "
            "law or certification of this tool. Apple Support only documents scanning in Notes "
            "and Files, adjusting corners, multiple pages, save locations and Markup signatures; "
            "it does not support claims about OCR, ppi, file size, ScanTo or endorsement."
        ),
        "source_labels": (
            "36 CFR 1236.50: permanent paper records digitization requirements",
            "FADGI: technical digitization guidelines",
            "NARA: OCR transcription is not always accurate",
            "Apple Support: scan documents in Notes or Files and use documented editing and saving steps",
        ),
        "webmcp_source": (
            "Chrome WebMCP imperative API preview (subject to change)"
        ),
        "webmcp_description": (
            "Calculate a private document scan plan from bounded paper, detail, colour, "
            "orientation and page-count inputs. Return exact pixel dimensions and transparent "
            "uncompressed raster bounds without receiving, reading, uploading, storing or "
            "OCR-processing a document, and without claiming accuracy or compliance."
        ),
        "app_title": "Need an iPhone paper-to-PDF workflow?",
        "app_text": (
            "ScanTo Pro is an optional iPhone tool whose current listing describes document "
            "scanning, PDF creation, OCR search and Face ID document protection with a one-time "
            "lifetime unlock. Check the current listing for exact availability and features. "
            "This free planner works without the app."
        ),
        "app_cta": "View ScanTo Pro on the App Store",
        "faq_title": "Questions before scanning",
        "faq": (
            (
                "Does this page upload my document?",
                "No. It has no file picker and accepts no document text or image. It only calculates from bounded settings.",
            ),
            (
                "Does 300 ppi guarantee accurate OCR?",
                "No. OCR depends on the source, typography, language, layout, focus, lighting and processing, and must be checked.",
            ),
            (
                "Is the MiB value my final PDF size?",
                "No. It is the uncompressed pixel payload. Compression, page structure, OCR and metadata change final file size.",
            ),
            (
                "Does this meet NARA or FADGI requirements?",
                "No. Those workflows require broader capture, equipment, targets, quality management and records controls.",
            ),
        ),
        "footer": "Private planning math only · no upload · verify the first page",
        "feature_list": (
            "No document, file, camera, OCR text or personal-data input",
            "Bounded 300, 400 and 600 ppi planning profiles",
            "Exact pixel dimensions and theoretical uncompressed MiB",
            "No upload, storage, cookies, analytics, ads or network requests",
            "No accuracy, legal, accessibility or compliance guarantee",
        ),
        "inline_link": "Plan pixels and uncompressed size first with the free private tool",
        "index_title": "Private Document Scan Planner",
        "index_description": (
            "Calculate ppi, exact pixels and uncompressed raster bounds without uploading "
            "or reading a document."
        ),
    },
    "zh-Hant": {
        "title": "私密文件掃描規劃器｜解析度、像素與容量界線",
        "description": (
            "不用上傳或讀取文件，即時計算掃描解析度、精確像素與透明標示的未壓縮影像容量界線。"
        ),
        "tools": "免費工具",
        "switch": "英文",
        "eyebrow": "免費 · 本機運算 · 不上傳文件",
        "heading": "私密文件掃描規劃器",
        "lead": (
            "選擇紙張、細節需求與色彩模式；瀏覽器只計算像素及理論未壓縮容量，完全不接收文件。"
        ),
        "badges": (
            "不輸入檔案或文件",
            "不執行 OCR 或雲端請求",
            "不猜測壓縮後容量",
            "不宣稱符合典藏規範",
        ),
        "planner": "規劃掃描",
        "planner_intro": "三種細節選項只是規劃起點，不保證品質，也不是官方認證。",
        "paper_label": "紙張尺寸",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "美規 Letter · 8.5×11 吋",
            "us-legal": "美規 Legal · 8.5×14 吋",
        },
        "purpose_label": "細節需求",
        "purpose_options": {
            "everyday-text": "一般文字 · 300 ppi",
            "small-print": "小字或混合標記 · 400 ppi",
            "fine-detail": "細線或印章 · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": (
                "清楚現代文字可先用 300 ppi 規劃；這不代表 OCR 準確，也不證明符合檔案規範。"
            ),
            "small-print": "小字或混合標記可選 400 ppi；大量掃描前先放大檢查第一頁。",
            "fine-detail": (
                "細線或極小標記可選 600 ppi；記憶體用量會大幅增加，仍不保證辨識結果。"
            ),
        },
        "color_label": "色彩模式",
        "color_options": {
            "grayscale": "8-bit 灰階",
            "rgb": "24-bit RGB 彩色",
        },
        "color_notes": {
            "grayscale": "只有色彩不影響內容時才用灰階；先確認印章、螢光標記、手寫字與註記。",
            "rgb": "印章、螢光標記、手寫字、註記或原貌的色彩有意義時，使用 RGB 彩色。",
        },
        "orientation_label": "方向",
        "orientation_options": {
            "portrait": "直向",
            "landscape": "橫向",
        },
        "pages_label": "頁數",
        "calculate": "更新規劃",
        "result_title": "掃描規劃結果",
        "dpi": "選定 ppi",
        "pixels": "每頁像素",
        "megapixels": "每頁百萬像素",
        "per_page": "每頁未壓縮 MiB",
        "total": "全部頁面未壓縮 MiB",
        "result_boundary": (
            "這些 MiB 是檔頭、壓縮、OCR 文字或 PDF 結構之前的數學像素量。"
            "實際 PDF、JPEG 與 TIFF 容量都會不同，因此本工具不估算壓縮後檔案大小。"
        ),
        "capture_title": "大量掃描前先確認五件事",
        "capture_checks": (
            "保留整張紙與全部邊緣；在不傷害原件的前提下整平摺痕。",
            "使用均勻光線，檢查反光、陰影、手指、模糊及被切掉的角落。",
            "色彩會影響資訊時使用 RGB；否則才考慮灰階。",
            "放大第一頁，檢查最小但重要的文字或標記。",
            "把 OCR 結果和原始影像逐項核對；OCR 不一定準確。",
        ),
        "scope_title": "這個規劃器不能證明什麼",
        "scope_text": (
            "本頁不接收文件、影像、檔案、相機內容、OCR 文字、自由文字、姓名或任何個資，"
            "也不掃描、增強、OCR、檢查、上傳或儲存內容，且不用 cookie、分析、廣告或網路請求。"
            "它不保證 OCR、可讀性、品質、法律效力、無障礙、典藏、政府、稅務、醫療或教育合規；"
            "任意手機掃描 App 也未必能精準控制指定 ppi。永久、受管制或證據文件仍須遵循主管機關"
            "現行規格及品質控管流程。"
        ),
        "sources_title": "官方背景資料，不代表背書",
        "sources_intro": (
            "NARA 與 FADGI 是美國永久檔案及數位化脈絡，不是各地法律，也不認證本工具。"
            "Apple 支援頁只說明在備忘錄或「檔案」掃描、調整邊角、多頁、儲存位置及以「標示」"
            "加入簽名等流程；不能據此推論 OCR、ppi、檔案大小、ScanTo 功能或 Apple 背書。"
        ),
        "source_labels": (
            "36 CFR 1236.50：永久紙本檔案數位化要求",
            "FADGI：數位化技術指引",
            "NARA：OCR 轉錄不一定準確",
            "Apple 支援：在備忘錄或「檔案」掃描文件，以及明載的編輯與儲存步驟",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只用有界的紙張、細節、色彩、方向與頁數輸入計算私密文件掃描規劃，"
            "回傳精確像素與透明未壓縮容量界線；不接收、讀取、上傳、儲存或 OCR 文件，"
            "也不宣稱準確度或規範符合性。"
        ),
        "app_title": "需要 iPhone 紙本轉 PDF 工作流程？",
        "app_text": (
            "ScanTo Pro 是選用 iPhone 工具；目前商店頁說明包含文件掃描、PDF 建立、"
            "OCR 搜尋及 Face ID 文件保護，並提供一次性終身解鎖。供應地區與確切功能"
            "請以目前商店頁為準；這個免費規劃器不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 ScanTo Pro",
        "faq_title": "掃描前常見問題",
        "faq": (
            (
                "這個網頁會上傳我的文件嗎？",
                "不會。它沒有檔案選擇器，也不接收文件文字或影像，只用有界設定計算。",
            ),
            (
                "300 ppi 能保證 OCR 準確嗎？",
                "不能。OCR 受原件、字型、語言、版面、對焦、光線與處理方式影響，結果必須核對。",
            ),
            (
                "MiB 數值就是最後 PDF 大小嗎？",
                "不是。那是未壓縮像素量；壓縮、頁面結構、OCR 與中繼資料都會改變實際容量。",
            ),
            (
                "這樣就符合 NARA 或 FADGI 嗎？",
                "不符合。那些流程還包含擷取設備、測試標靶、品質管理及檔案管控等要求。",
            ),
        ),
        "footer": "只做私密規劃運算 · 不上傳 · 先核對第一頁",
        "feature_list": (
            "不輸入文件、檔案、相機內容、OCR 文字或個資",
            "有界的 300、400 與 600 ppi 規劃選項",
            "精確像素尺寸與理論未壓縮 MiB",
            "不上傳、不儲存，不用 cookie、分析、廣告或網路請求",
            "不保證準確度、法律效力、無障礙或法規符合性",
        ),
        "inline_link": "先用免費私密工具規劃像素與未壓縮容量",
        "index_title": "私密文件掃描規劃器",
        "index_description": "不讀取或上傳文件，即時計算 ppi、精確像素與未壓縮影像容量界線。",
    },
    "es-ES": {
        "title": "Planificador privado de escaneo | ppi, píxeles y límites",
        "description": "Planifica la resolución, las dimensiones exactas en píxeles y el tamaño raster sin comprimir sin subir ni leer documentos.",
        "tools": "Herramientas gratuitas",
        "switch": "Inglés",
        "eyebrow": "Gratis · cálculo local · sin subir documentos",
        "heading": "Planificador privado de escaneo de documentos",
        "lead": "Elige papel, nivel de detalle y color; el navegador solo calcula píxeles y MiB teóricos sin recibir ningún documento.",
        "badges": (
            "Sin entrada de archivos ni documentos",
            "Sin OCR ni solicitudes a la nube",
            "Sin estimar tamaños comprimidos",
            "Sin afirmar cumplimiento archivístico",
        ),
        "planner": "Planifica la captura",
        "planner_intro": "Los tres perfiles de detalle son puntos de partida, no garantías de calidad ni certificaciones oficiales.",
        "paper_label": "Tamaño del papel",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "Carta EE. UU. · 8,5×11 in",
            "us-legal": "Legal EE. UU. · 8,5×14 in",
        },
        "purpose_label": "Perfil de detalle",
        "purpose_options": {
            "everyday-text": "Texto habitual · 300 ppi",
            "small-print": "Letra pequeña o marcas mixtas · 400 ppi",
            "fine-detail": "Líneas finas o sellos · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "Una base de 300 ppi para texto moderno claro; no certifica la precisión del OCR ni el cumplimiento documental.",
            "small-print": "Una opción de 400 ppi para texto pequeño o marcas mixtas; revisa la primera página antes de procesar un lote.",
            "fine-detail": "Una opción de 600 ppi cuando importan líneas o marcas diminutas; aumenta mucho la memoria y no garantiza el reconocimiento.",
        },
        "color_label": "Modo de color",
        "color_options": {"grayscale": "Escala de grises de 8 bits", "rgb": "Color RGB de 24 bits"},
        "color_notes": {
            "grayscale": "Úsala solo si el color no aporta significado; comprueba antes sellos, resaltados, escritura y anotaciones.",
            "rgb": "Usa RGB cuando el color ayude a interpretar sellos, resaltados, escritura, anotaciones o el aspecto original.",
        },
        "orientation_label": "Orientación",
        "orientation_options": {"portrait": "Vertical", "landscape": "Horizontal"},
        "pages_label": "Número de páginas",
        "calculate": "Actualizar plan",
        "result_title": "Plan de escaneo calculado",
        "dpi": "ppi seleccionados",
        "pixels": "Píxeles por página",
        "megapixels": "Megapíxeles por página",
        "per_page": "MiB sin comprimir por página",
        "total": "MiB sin comprimir totales",
        "result_boundary": "Estos MiB son la carga matemática de píxeles antes de cabeceras, compresión, texto OCR o estructura PDF. Los tamaños reales de PDF, JPEG y TIFF varían; no se estima el tamaño comprimido.",
        "capture_title": "Cinco comprobaciones antes de un lote",
        "capture_checks": (
            "Mantén visibles la página completa y todos sus bordes; alisa los pliegues sin dañar el original.",
            "Usa luz uniforme y busca reflejos, sombras, dedos, desenfoque y esquinas recortadas.",
            "Elige RGB si el color contiene información; si no, puede servir la escala de grises.",
            "Amplía la primera página y revisa el texto o la marca importante de menor tamaño.",
            "Compara cualquier resultado OCR con la imagen; el OCR no siempre es exacto.",
        ),
        "scope_title": "Lo que este planificador no puede certificar",
        "scope_text": "No recibe documentos, imágenes, archivos, cámara, texto OCR, texto libre, nombres ni datos personales; no escanea, mejora, inspecciona, sube ni almacena, y no usa cookies, analítica, anuncios ni red. No garantiza OCR, legibilidad, calidad, validez legal, accesibilidad ni cumplimiento archivístico, público, fiscal, médico o educativo. Cualquier app móvil puede no controlar con precisión los ppi elegidos. Para documentos permanentes, regulados o probatorios rigen las especificaciones y controles vigentes de la autoridad responsable.",
        "sources_title": "Contexto oficial, no respaldo",
        "sources_intro": "NARA y FADGI tratan registros permanentes y digitalización de EE. UU.; no son ley local ni certifican esta herramienta. Apple solo documenta escanear en Notas y Archivos, ajustar esquinas, varias páginas, ubicaciones de guardado y firmas con Marcación; no acredita afirmaciones sobre OCR, ppi, tamaño, ScanTo ni respaldo.",
        "source_labels": (
            "36 CFR 1236.50: requisitos de digitalización de registros permanentes en papel",
            "FADGI: directrices técnicas de digitalización",
            "NARA: la transcripción OCR no siempre es exacta",
            "Soporte de Apple: escanear en Notas o Archivos y usar los pasos documentados de edición y guardado",
        ),
        "webmcp_source": "Vista previa de la API imperativa WebMCP de Chrome (sujeta a cambios)",
        "webmcp_description": "Calcula un plan privado con valores acotados de papel, detalle, color, orientación y páginas. Devuelve píxeles exactos y límites raster sin comprimir sin recibir, leer, subir, guardar ni procesar por OCR documentos, y sin prometer precisión ni cumplimiento.",
        "app_title": "¿Necesitas un flujo de papel a PDF en iPhone?",
        "app_text": "ScanTo Pro es una herramienta opcional para iPhone cuya ficha actual describe escaneo de documentos, creación de PDF, búsqueda OCR y protección con Face ID mediante un desbloqueo vitalicio de pago único. Consulta la ficha vigente para conocer disponibilidad y funciones exactas. Este planificador funciona sin la app.",
        "app_cta": "Ver ScanTo Pro en App Store",
        "faq_title": "Preguntas antes de escanear",
        "faq": (
            ("¿Esta página sube mi documento?", "No. No tiene selector de archivos y no acepta texto ni imágenes de documentos; solo calcula ajustes acotados."),
            ("¿300 ppi garantizan un OCR exacto?", "No. El OCR depende del original, tipografía, idioma, diseño, enfoque, luz y procesamiento, y debe comprobarse."),
            ("¿Los MiB son el tamaño final del PDF?", "No. Son la carga de píxeles sin comprimir; la compresión, estructura, OCR y metadatos cambian el tamaño final."),
            ("¿Cumple esto NARA o FADGI?", "No. Esos flujos incluyen captura, equipos, patrones, gestión de calidad y controles documentales más amplios."),
        ),
        "footer": "Solo cálculo privado · sin subidas · comprueba la primera página",
        "feature_list": (
            "Sin documentos, archivos, cámara, texto OCR ni datos personales",
            "Perfiles acotados de 300, 400 y 600 ppi",
            "Píxeles exactos y MiB teóricos sin comprimir",
            "Sin subidas, almacenamiento, cookies, analítica, anuncios ni red",
            "Sin garantía de precisión, validez, accesibilidad ni cumplimiento",
        ),
        "inline_link": "Planifica antes los píxeles y el tamaño sin comprimir con la herramienta privada gratuita",
        "index_title": "Planificador privado de escaneo",
        "index_description": "Calcula ppi, píxeles exactos y límites raster sin comprimir sin leer ni subir documentos.",
    },
    "pt-BR": {
        "title": "Planejador privado de digitalização | ppi, pixels e limites",
        "description": "Planeje resolução, dimensões exatas em pixels e tamanho raster não comprimido sem enviar nem ler documentos.",
        "tools": "Ferramentas gratuitas",
        "switch": "Inglês",
        "eyebrow": "Grátis · cálculo local · sem envio de documentos",
        "heading": "Planejador privado de digitalização de documentos",
        "lead": "Escolha papel, nível de detalhe e cor; o navegador só calcula pixels e MiB teóricos, sem receber documento algum.",
        "badges": (
            "Sem entrada de arquivo ou documento",
            "Sem OCR ou solicitação à nuvem",
            "Sem estimativa de tamanho comprimido",
            "Sem alegação de conformidade arquivística",
        ),
        "planner": "Planeje a captura",
        "planner_intro": "Os três perfis de detalhe são pontos de partida, não garantias de qualidade nem certificações oficiais.",
        "paper_label": "Tamanho do papel",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "Carta EUA · 8,5×11 in",
            "us-legal": "Ofício EUA · 8,5×14 in",
        },
        "purpose_label": "Perfil de detalhe",
        "purpose_options": {
            "everyday-text": "Texto comum · 300 ppi",
            "small-print": "Letras pequenas ou marcas variadas · 400 ppi",
            "fine-detail": "Linhas finas ou carimbos · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "Base de 300 ppi para texto moderno nítido; não certifica precisão de OCR nem conformidade documental.",
            "small-print": "Opção de 400 ppi para texto pequeno ou marcas variadas; confira a primeira página antes de um lote.",
            "fine-detail": "Opção de 600 ppi para linhas ou marcas minúsculas; aumenta muito a memória e ainda não garante reconhecimento.",
        },
        "color_label": "Modo de cor",
        "color_options": {"grayscale": "Tons de cinza de 8 bits", "rgb": "Cor RGB de 24 bits"},
        "color_notes": {
            "grayscale": "Use só quando a cor não tiver significado; confira antes carimbos, destaques, escrita e anotações.",
            "rgb": "Use RGB quando a cor ajudar a interpretar carimbos, destaques, escrita, anotações ou a aparência original.",
        },
        "orientation_label": "Orientação",
        "orientation_options": {"portrait": "Retrato", "landscape": "Paisagem"},
        "pages_label": "Número de páginas",
        "calculate": "Atualizar plano",
        "result_title": "Plano de digitalização calculado",
        "dpi": "ppi selecionados",
        "pixels": "Pixels por página",
        "megapixels": "Megapixels por página",
        "per_page": "MiB não comprimidos por página",
        "total": "MiB não comprimidos no total",
        "result_boundary": "Esses MiB são a carga matemática de pixels antes de cabeçalhos, compressão, texto OCR ou estrutura PDF. Tamanhos reais de PDF, JPEG e TIFF variam; a ferramenta não estima tamanho comprimido.",
        "capture_title": "Cinco verificações antes de um lote",
        "capture_checks": (
            "Mantenha a página inteira e todas as bordas visíveis; alise dobras sem danificar o original.",
            "Use luz uniforme e verifique reflexos, sombras, dedos, desfoque e cantos cortados.",
            "Escolha RGB quando a cor carregar informação; caso contrário, tons de cinza podem servir.",
            "Amplie a primeira página e confira o menor texto ou marca importante.",
            "Compare todo resultado de OCR com a imagem; OCR nem sempre é preciso.",
        ),
        "scope_title": "O que este planejador não pode certificar",
        "scope_text": "Não recebe documento, imagem, arquivo, câmera, texto OCR, texto livre, nome nem dado pessoal; não digitaliza, melhora, inspeciona, envia ou armazena, e não usa cookies, análise, anúncios nem rede. Não garante OCR, legibilidade, qualidade, validade jurídica, acessibilidade ou conformidade arquivística, governamental, fiscal, médica ou educacional. Um app móvel pode não controlar exatamente os ppi escolhidos. Registros permanentes, regulados ou probatórios exigem a especificação e o controle de qualidade atuais da autoridade responsável.",
        "sources_title": "Contexto oficial, não endosso",
        "sources_intro": "NARA e FADGI tratam de registros permanentes e digitalização nos EUA; não são lei local nem certificam esta ferramenta. A Apple só documenta digitalização em Notas e Arquivos, ajuste de cantos, várias páginas, locais de salvamento e assinaturas com Marcação; isso não sustenta alegações sobre OCR, ppi, tamanho, ScanTo ou endosso.",
        "source_labels": (
            "36 CFR 1236.50: requisitos de digitalização de registros permanentes em papel",
            "FADGI: diretrizes técnicas de digitalização",
            "NARA: a transcrição por OCR nem sempre é precisa",
            "Suporte da Apple: digitalizar em Notas ou Arquivos e usar as etapas documentadas de edição e salvamento",
        ),
        "webmcp_source": "Prévia da API imperativa WebMCP do Chrome (sujeita a alterações)",
        "webmcp_description": "Calcula um plano privado com entradas limitadas de papel, detalhe, cor, orientação e páginas. Retorna pixels exatos e limites raster não comprimidos sem receber, ler, enviar, armazenar ou processar documentos por OCR, e sem prometer precisão ou conformidade.",
        "app_title": "Precisa de um fluxo de papel para PDF no iPhone?",
        "app_text": "ScanTo Pro é uma ferramenta opcional para iPhone cuja página atual descreve digitalização de documentos, criação de PDF, busca por OCR e proteção com Face ID, com desbloqueio vitalício em pagamento único. Consulte a página vigente para disponibilidade e recursos exatos. Este planejador funciona sem o app.",
        "app_cta": "Ver ScanTo Pro na App Store",
        "faq_title": "Perguntas antes de digitalizar",
        "faq": (
            ("Esta página envia meu documento?", "Não. Não há seletor de arquivo e ela não aceita texto nem imagem de documento; só calcula configurações limitadas."),
            ("300 ppi garantem OCR preciso?", "Não. OCR depende do original, fonte, idioma, layout, foco, luz e processamento, e precisa ser conferido."),
            ("Os MiB são o tamanho final do PDF?", "Não. São a carga de pixels não comprimida; compressão, estrutura, OCR e metadados mudam o tamanho final."),
            ("Isso atende à NARA ou à FADGI?", "Não. Esses fluxos incluem captura, equipamentos, alvos, gestão de qualidade e controles documentais mais amplos."),
        ),
        "footer": "Apenas cálculo privado · sem envio · confira a primeira página",
        "feature_list": (
            "Sem documento, arquivo, câmera, texto OCR ou dado pessoal",
            "Perfis limitados de 300, 400 e 600 ppi",
            "Pixels exatos e MiB teóricos não comprimidos",
            "Sem envio, armazenamento, cookies, análise, anúncios ou rede",
            "Sem garantia de precisão, validade, acessibilidade ou conformidade",
        ),
        "inline_link": "Planeje primeiro os pixels e o tamanho não comprimido com a ferramenta privada grátis",
        "index_title": "Planejador privado de digitalização",
        "index_description": "Calcule ppi, pixels exatos e limites raster não comprimidos sem ler nem enviar documentos.",
    },
    "de-DE": {
        "title": "Privater Dokumentenscan-Planer | ppi, Pixel und Grenzen",
        "description": "Scanauflösung, exakte Pixelmaße und unkomprimierte Rastergröße planen, ohne ein Dokument hochzuladen oder auszulesen.",
        "tools": "Kostenlose Werkzeuge",
        "switch": "Englisch",
        "eyebrow": "Kostenlos · lokale Berechnung · kein Dokument-Upload",
        "heading": "Privater Planer für Dokumentenscans",
        "lead": "Papier, Detailstufe und Farbmodus wählen; der Browser berechnet nur Pixel und theoretische MiB und erhält kein Dokument.",
        "badges": (
            "Keine Datei- oder Dokumenteingabe",
            "Keine OCR- oder Cloud-Anfrage",
            "Keine Schätzung komprimierter Größen",
            "Keine Zusage zur Archivkonformität",
        ),
        "planner": "Aufnahme planen",
        "planner_intro": "Die drei Detailprofile sind Planungsausgangspunkte, keine Qualitätsgarantien oder amtlichen Zertifizierungen.",
        "paper_label": "Papierformat",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "US Letter · 8,5×11 in",
            "us-legal": "US Legal · 8,5×14 in",
        },
        "purpose_label": "Detailprofil",
        "purpose_options": {
            "everyday-text": "Alltagstext · 300 ppi",
            "small-print": "Kleingedrucktes oder gemischte Zeichen · 400 ppi",
            "fine-detail": "Feine Linien oder Stempel · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "Ein 300-ppi-Ausgangswert für klaren modernen Text; er bescheinigt weder OCR-Genauigkeit noch Aktenkonformität.",
            "small-print": "Eine 400-ppi-Option für kleine Schrift oder gemischte Zeichen; vor einem Stapel die erste Seite prüfen.",
            "fine-detail": "Eine 600-ppi-Option für feine Linien oder winzige Zeichen; sie benötigt deutlich mehr Speicher und garantiert keine Erkennung.",
        },
        "color_label": "Farbmodus",
        "color_options": {"grayscale": "8-Bit-Graustufen", "rgb": "24-Bit-RGB-Farbe"},
        "color_notes": {
            "grayscale": "Nur verwenden, wenn Farbe keine Bedeutung trägt; Stempel, Markierungen, Handschrift und Anmerkungen vorher prüfen.",
            "rgb": "RGB verwenden, wenn Farbe bei Stempeln, Markierungen, Handschrift, Anmerkungen oder Originalansicht hilft.",
        },
        "orientation_label": "Ausrichtung",
        "orientation_options": {"portrait": "Hochformat", "landscape": "Querformat"},
        "pages_label": "Seitenzahl",
        "calculate": "Plan aktualisieren",
        "result_title": "Berechneter Scanplan",
        "dpi": "Gewählte ppi",
        "pixels": "Pixel je Seite",
        "megapixels": "Megapixel je Seite",
        "per_page": "Unkomprimierte MiB je Seite",
        "total": "Unkomprimierte MiB insgesamt",
        "result_boundary": "Diese MiB sind die mathematische Pixellast vor Dateiköpfen, Komprimierung, OCR-Text oder PDF-Struktur. Tatsächliche PDF-, JPEG- und TIFF-Größen variieren; eine komprimierte Dateigröße wird nicht geschätzt.",
        "capture_title": "Fünf Prüfungen vor einem Stapel",
        "capture_checks": (
            "Die ganze Seite und alle Kanten sichtbar halten; Falten ohne Schaden am Original glätten.",
            "Gleichmäßiges Licht nutzen und auf Glanz, Schatten, Finger, Unschärfe und abgeschnittene Ecken prüfen.",
            "RGB wählen, wenn Farbe Information trägt; sonst können Graustufen geeignet sein.",
            "Die erste Seite vergrößern und den kleinsten wichtigen Text oder das kleinste Zeichen prüfen.",
            "Jedes OCR-Ergebnis mit dem Bild vergleichen; OCR ist nicht immer genau.",
        ),
        "scope_title": "Was dieser Planer nicht bescheinigen kann",
        "scope_text": "Er nimmt keine Dokumente, Bilder, Dateien, Kameraaufnahmen, OCR- oder Freitexte, Namen oder personenbezogenen Daten an; er scannt, verbessert, prüft, lädt und speichert nichts und nutzt keine Cookies, Analysen, Werbung oder Netzwerkanfragen. Er garantiert weder OCR, Lesbarkeit, Qualität, Rechtswirkung und Barrierefreiheit noch Archiv-, Behörden-, Steuer-, Medizin- oder Bildungskonformität. Eine beliebige Scan-App kann gewählte ppi möglicherweise nicht exakt steuern. Für dauerhafte, regulierte oder beweiserhebliche Akten gelten aktuelle Vorgaben und Qualitätskontrollen der zuständigen Stelle.",
        "sources_title": "Amtlicher Kontext, keine Empfehlung",
        "sources_intro": "NARA und FADGI behandeln dauerhafte US-Akten und Digitalisierung; sie sind kein örtliches Recht und zertifizieren dieses Werkzeug nicht. Apple dokumentiert nur Scans in Notizen und Dateien, Eckenanpassung, mehrere Seiten, Speicherorte und Markieren-Unterschriften; daraus folgen keine Aussagen zu OCR, ppi, Dateigröße, ScanTo oder Empfehlung.",
        "source_labels": (
            "36 CFR 1236.50: Anforderungen zur Digitalisierung dauerhafter Papierakten",
            "FADGI: technische Digitalisierungsrichtlinien",
            "NARA: OCR-Transkription ist nicht immer genau",
            "Apple Support: Dokumente in Notizen oder Dateien scannen und dokumentierte Bearbeitungs- und Speicherschritte nutzen",
        ),
        "webmcp_source": "Vorschau der imperativen Chrome-WebMCP-API (Änderungen vorbehalten)",
        "webmcp_description": "Berechnet aus begrenzten Papier-, Detail-, Farb-, Ausrichtungs- und Seitenangaben einen privaten Scanplan. Gibt exakte Pixel und transparente unkomprimierte Rastergrenzen zurück, ohne Dokumente anzunehmen, zu lesen, hochzuladen, zu speichern oder per OCR zu verarbeiten und ohne Genauigkeit oder Konformität zu versprechen.",
        "app_title": "Wird ein Papier-zu-PDF-Ablauf auf dem iPhone benötigt?",
        "app_text": "ScanTo Pro ist ein optionales iPhone-Werkzeug. Laut aktuellem Store-Eintrag bietet es Dokumentenscans, PDF-Erstellung, OCR-Suche und Dokumentenschutz per Face ID mit einmaliger lebenslanger Freischaltung. Verfügbarkeit und genaue Funktionen bitte im aktuellen Eintrag prüfen. Dieser Planer funktioniert ohne App.",
        "app_cta": "ScanTo Pro im App Store ansehen",
        "faq_title": "Fragen vor dem Scannen",
        "faq": (
            ("Lädt diese Seite mein Dokument hoch?", "Nein. Sie hat keine Dateiauswahl und nimmt weder Dokumenttext noch Bilder an; sie berechnet nur begrenzte Einstellungen."),
            ("Garantieren 300 ppi genaue OCR?", "Nein. OCR hängt von Vorlage, Schrift, Sprache, Layout, Fokus, Licht und Verarbeitung ab und muss geprüft werden."),
            ("Sind die MiB meine endgültige PDF-Größe?", "Nein. Sie sind die unkomprimierte Pixellast; Komprimierung, Seitenstruktur, OCR und Metadaten ändern die Endgröße."),
            ("Erfüllt dies NARA oder FADGI?", "Nein. Diese Abläufe umfassen weitergehende Aufnahme-, Geräte-, Testtafel-, Qualitäts- und Aktenkontrollen."),
        ),
        "footer": "Nur private Planungsrechnung · kein Upload · erste Seite prüfen",
        "feature_list": (
            "Keine Dokument-, Datei-, Kamera-, OCR-Text- oder Personendateneingabe",
            "Begrenzte Planungsprofile mit 300, 400 und 600 ppi",
            "Exakte Pixel und theoretische unkomprimierte MiB",
            "Keine Uploads, Speicherung, Cookies, Analysen, Werbung oder Netzwerkanfragen",
            "Keine Garantie für Genauigkeit, Rechtswirkung, Barrierefreiheit oder Konformität",
        ),
        "inline_link": "Pixel und unkomprimierte Größe zuerst mit dem kostenlosen privaten Werkzeug planen",
        "index_title": "Privater Dokumentenscan-Planer",
        "index_description": "ppi, exakte Pixel und unkomprimierte Rastergrenzen berechnen, ohne Dokumente zu lesen oder hochzuladen.",
    },
    "fr-FR": {
        "title": "Planificateur privé de numérisation | ppi, pixels et limites",
        "description": "Planifiez la résolution, les dimensions exactes en pixels et la taille raster non compressée sans téléverser ni lire de document.",
        "tools": "Outils gratuits",
        "switch": "Anglais",
        "eyebrow": "Gratuit · calcul local · aucun document téléversé",
        "heading": "Planificateur privé de numérisation de documents",
        "lead": "Choisissez le papier, le niveau de détail et la couleur ; le navigateur calcule seulement les pixels et les MiB théoriques sans recevoir de document.",
        "badges": (
            "Aucune saisie de fichier ou document",
            "Aucun OCR ni appel au cloud",
            "Aucune estimation de taille compressée",
            "Aucune affirmation de conformité archivistique",
        ),
        "planner": "Planifier la capture",
        "planner_intro": "Les trois profils de détail sont des points de départ, pas des garanties de qualité ni des certifications officielles.",
        "paper_label": "Format du papier",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "US Letter · 8,5×11 in",
            "us-legal": "US Legal · 8,5×14 in",
        },
        "purpose_label": "Profil de détail",
        "purpose_options": {
            "everyday-text": "Texte courant · 300 ppi",
            "small-print": "Petits caractères ou marques variées · 400 ppi",
            "fine-detail": "Traits fins ou tampons · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "Une base de 300 ppi pour un texte moderne net ; elle ne certifie ni la précision OCR ni la conformité documentaire.",
            "small-print": "Une option de 400 ppi pour les petits caractères ou marques variées ; contrôlez la première page avant un lot.",
            "fine-detail": "Une option de 600 ppi si les traits ou marques minuscules comptent ; elle augmente fortement la mémoire sans garantir la reconnaissance.",
        },
        "color_label": "Mode couleur",
        "color_options": {"grayscale": "Niveaux de gris 8 bits", "rgb": "Couleur RGB 24 bits"},
        "color_notes": {
            "grayscale": "À utiliser seulement si la couleur n'a pas de sens ; contrôlez d'abord tampons, surlignages, écriture et annotations.",
            "rgb": "Utilisez RGB si la couleur aide à interpréter tampons, surlignages, écriture, annotations ou aspect d'origine.",
        },
        "orientation_label": "Orientation",
        "orientation_options": {"portrait": "Portrait", "landscape": "Paysage"},
        "pages_label": "Nombre de pages",
        "calculate": "Actualiser le plan",
        "result_title": "Plan de numérisation calculé",
        "dpi": "ppi sélectionnés",
        "pixels": "Pixels par page",
        "megapixels": "Mégapixels par page",
        "per_page": "MiB non compressés par page",
        "total": "MiB non compressés au total",
        "result_boundary": "Ces MiB représentent la charge mathématique des pixels avant en-têtes, compression, texte OCR ou structure PDF. Les tailles réelles des PDF, JPEG et TIFF varient ; l'outil n'estime pas la taille compressée.",
        "capture_title": "Cinq contrôles avant un lot",
        "capture_checks": (
            "Gardez la page entière et tous ses bords visibles ; aplatissez les plis sans endommager l'original.",
            "Utilisez une lumière uniforme et vérifiez reflets, ombres, doigts, flou et coins coupés.",
            "Choisissez RGB lorsque la couleur porte une information ; sinon les niveaux de gris peuvent convenir.",
            "Agrandissez la première page et contrôlez le plus petit texte ou signe important.",
            "Comparez tout résultat OCR à l'image ; l'OCR n'est pas toujours exact.",
        ),
        "scope_title": "Ce que ce planificateur ne peut pas certifier",
        "scope_text": "Il ne reçoit ni document, image, fichier, caméra, texte OCR ou libre, nom ou donnée personnelle ; il ne numérise, améliore, inspecte, téléverse ou stocke rien et n'utilise ni cookies, analyse, publicité ou réseau. Il ne garantit ni OCR, lisibilité, qualité, valeur juridique, accessibilité, ni conformité archivistique, administrative, fiscale, médicale ou éducative. Une app mobile peut ne pas maîtriser exactement les ppi choisis. Les documents permanents, réglementés ou probatoires exigent les prescriptions et contrôles qualité actuels de l'autorité responsable.",
        "sources_title": "Contexte officiel, pas une approbation",
        "sources_intro": "NARA et FADGI concernent les archives permanentes et la numérisation aux États-Unis ; ce ne sont ni des lois locales ni une certification de cet outil. Apple décrit seulement la numérisation dans Notes et Fichiers, le réglage des coins, plusieurs pages, les emplacements d'enregistrement et les signatures avec Annoter ; aucune conclusion n'en découle sur OCR, ppi, taille, ScanTo ou approbation.",
        "source_labels": (
            "36 CFR 1236.50 : exigences de numérisation des archives papier permanentes",
            "FADGI : recommandations techniques de numérisation",
            "NARA : la transcription OCR n'est pas toujours exacte",
            "Assistance Apple : numériser dans Notes ou Fichiers et suivre les étapes documentées de modification et d'enregistrement",
        ),
        "webmcp_source": "Aperçu de l'API impérative WebMCP de Chrome (susceptible d'évoluer)",
        "webmcp_description": "Calcule un plan privé à partir d'entrées bornées de papier, détail, couleur, orientation et pages. Renvoie des pixels exacts et des limites raster non compressées sans recevoir, lire, téléverser, stocker ni traiter un document par OCR, et sans promettre précision ou conformité.",
        "app_title": "Besoin d'un flux papier vers PDF sur iPhone ?",
        "app_text": "ScanTo Pro est un outil iPhone facultatif dont la fiche actuelle décrit la numérisation de documents, la création de PDF, la recherche OCR et la protection des documents par Face ID avec déverrouillage à vie en achat unique. Consultez la fiche en vigueur pour la disponibilité et les fonctions exactes. Ce planificateur fonctionne sans l'app.",
        "app_cta": "Voir ScanTo Pro dans l'App Store",
        "faq_title": "Questions avant de numériser",
        "faq": (
            ("Cette page téléverse-t-elle mon document ?", "Non. Elle ne comporte aucun sélecteur de fichier et n'accepte ni texte ni image de document ; elle calcule seulement des réglages bornés."),
            ("300 ppi garantissent-ils un OCR exact ?", "Non. L'OCR dépend de la source, police, langue, mise en page, mise au point, lumière et traitement, et doit être contrôlé."),
            ("Les MiB correspondent-ils à la taille finale du PDF ?", "Non. C'est la charge de pixels non compressée ; compression, structure, OCR et métadonnées changent la taille finale."),
            ("Cela satisfait-il NARA ou FADGI ?", "Non. Leurs processus comportent des contrôles plus larges de capture, matériel, mires, qualité et archives."),
        ),
        "footer": "Calcul privé uniquement · aucun téléversement · contrôlez la première page",
        "feature_list": (
            "Aucun document, fichier, caméra, texte OCR ou donnée personnelle",
            "Profils bornés à 300, 400 et 600 ppi",
            "Pixels exacts et MiB théoriques non compressés",
            "Aucun téléversement, stockage, cookie, analyse, publicité ou réseau",
            "Aucune garantie de précision, valeur juridique, accessibilité ou conformité",
        ),
        "inline_link": "Planifiez d'abord les pixels et la taille non compressée avec l'outil privé gratuit",
        "index_title": "Planificateur privé de numérisation",
        "index_description": "Calculez ppi, pixels exacts et limites raster non compressées sans lire ni téléverser de document.",
    },
    "ja": {
        "title": "非公開文書スキャンプランナー｜ppi・画素数・容量の境界",
        "description": "文書をアップロードも読み取りもせず、スキャン解像度、正確な画素寸法、非圧縮ラスター容量を計画できます。",
        "tools": "無料ツール",
        "switch": "英語",
        "eyebrow": "無料 · 端末内計算 · 文書のアップロードなし",
        "heading": "非公開文書スキャンプランナー",
        "lead": "用紙、細かさ、カラーモードを選ぶと、ブラウザが画素数と理論上の非圧縮 MiB だけを計算し、文書は受け取りません。",
        "badges": (
            "ファイルや文書の入力なし",
            "OCR やクラウド通信なし",
            "圧縮後サイズの推測なし",
            "公文書保存基準への適合表明なし",
        ),
        "planner": "取り込みを計画",
        "planner_intro": "3 つの細かさは計画の出発点であり、品質保証や公的認証ではありません。",
        "paper_label": "用紙サイズ",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "米国レター · 8.5×11 in",
            "us-legal": "米国リーガル · 8.5×14 in",
        },
        "purpose_label": "細かさ",
        "purpose_options": {
            "everyday-text": "一般的な文書 · 300 ppi",
            "small-print": "小さい文字や複合した印 · 400 ppi",
            "fine-detail": "細線や印章 · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "鮮明な現代文書を想定した 300 ppi の基準です。OCR 精度や記録管理基準への適合を証明しません。",
            "small-print": "小さい文字や複合した印向けの 400 ppi です。まとめて処理する前に最初の 1 ページを確認してください。",
            "fine-detail": "細線や極小の印を重視する場合の 600 ppi です。メモリ量が大幅に増え、認識結果も保証しません。",
        },
        "color_label": "カラーモード",
        "color_options": {"grayscale": "8-bit グレースケール", "rgb": "24-bit RGB カラー"},
        "color_notes": {
            "grayscale": "色に意味がない場合だけ使用し、印章、蛍光マーカー、手書き、注記を先に確認してください。",
            "rgb": "印章、蛍光マーカー、手書き、注記、原本の外観を読み取るうえで色が重要なら RGB を使います。",
        },
        "orientation_label": "向き",
        "orientation_options": {"portrait": "縦", "landscape": "横"},
        "pages_label": "ページ数",
        "calculate": "計画を更新",
        "result_title": "計算したスキャン計画",
        "dpi": "選択した ppi",
        "pixels": "1 ページの画素数",
        "megapixels": "1 ページのメガピクセル",
        "per_page": "1 ページの非圧縮 MiB",
        "total": "全ページの非圧縮 MiB",
        "result_boundary": "この MiB は、ファイルヘッダー、圧縮、OCR テキスト、PDF 構造を含む前の数学的な画素データ量です。実際の PDF、JPEG、TIFF の容量は異なるため、圧縮後のファイルサイズは推定しません。",
        "capture_title": "まとめて取り込む前の 5 項目",
        "capture_checks": (
            "ページ全体とすべての端を画面内に収め、原本を傷めない範囲で折れを伸ばします。",
            "均一な照明を使い、反射、影、指、ぼけ、切れた角がないか確認します。",
            "色が情報を持つ場合は RGB を選び、それ以外はグレースケールを検討します。",
            "最初のページを拡大し、重要な文字や印のうち最小のものを確認します。",
            "OCR 結果は画像と照合してください。OCR は常に正確とは限りません。",
        ),
        "scope_title": "このプランナーが証明できないこと",
        "scope_text": "文書、画像、ファイル、カメラ、OCR テキスト、自由記述、氏名、個人情報を受け取らず、スキャン、補正、OCR、検査、アップロード、保存を行いません。cookie、解析、広告、ネットワーク通信も使いません。OCR、可読性、品質、法的効力、アクセシビリティ、保存、公的手続、税務、医療、教育上の適合を保証せず、任意のスマートフォン用スキャン App が指定 ppi を正確に制御できるとも限りません。永久保存、規制対象、証拠用の記録には、所管機関の現行仕様と品質管理が必要です。",
        "sources_title": "公的資料による背景説明であり、推奨ではありません",
        "sources_intro": "NARA と FADGI は米国の永久記録とデジタル化の文脈であり、各地の法律でも本ツールの認証でもありません。Apple の資料が示すのは、メモまたはファイルでの文書スキャン、四隅の調整、複数ページ、保存先、マークアップ署名だけです。OCR、ppi、容量、ScanTo の機能、Apple の推奨は導けません。",
        "source_labels": (
            "36 CFR 1236.50：永久保存紙記録のデジタル化要件",
            "FADGI：デジタル化の技術指針",
            "NARA：OCR 文字起こしは常に正確とは限らない",
            "Apple サポート：メモまたはファイルで文書をスキャンし、明記された編集・保存手順を使う方法",
        ),
        "webmcp_source": "Chrome WebMCP 命令型 API プレビュー（変更される場合があります）",
        "webmcp_description": "範囲を限定した用紙、細かさ、色、向き、ページ数から非公開のスキャン計画を計算します。文書を受領、読取、アップロード、保存、OCR 処理せず、正確性や適合性を表明せずに、正確な画素寸法と非圧縮ラスター容量の境界を返します。",
        "app_title": "iPhone で紙を PDF にする手順が必要ですか？",
        "app_text": "ScanTo Pro は任意で使える iPhone ツールです。現在のストア掲載情報には、文書スキャン、PDF 作成、OCR 検索、Face ID による文書保護、買い切りの生涯ロック解除が記載されています。提供状況と正確な機能は現行の掲載情報を確認してください。この無料プランナーは App なしで使えます。",
        "app_cta": "App Store で ScanTo Pro を見る",
        "faq_title": "スキャン前の質問",
        "faq": (
            ("このページは文書をアップロードしますか？", "いいえ。ファイル選択欄はなく、文書の文字や画像を受け取りません。限定された設定だけを計算します。"),
            ("300 ppi なら OCR は正確ですか？", "いいえ。OCR は原本、書体、言語、配置、ピント、照明、処理に左右され、確認が必要です。"),
            ("MiB は最終 PDF のサイズですか？", "いいえ。非圧縮の画素データ量です。圧縮、ページ構造、OCR、メタデータによって最終容量は変わります。"),
            ("NARA や FADGI の要件を満たしますか？", "いいえ。これらの工程には、取り込み、機器、テストターゲット、品質管理、記録管理が含まれます。"),
        ),
        "footer": "非公開の計画計算のみ · アップロードなし · 最初のページを確認",
        "feature_list": (
            "文書、ファイル、カメラ、OCR テキスト、個人情報の入力なし",
            "300、400、600 ppi の限定された計画プロファイル",
            "正確な画素寸法と理論上の非圧縮 MiB",
            "アップロード、保存、cookie、解析、広告、ネットワーク通信なし",
            "正確性、法的効力、アクセシビリティ、適合性の保証なし",
        ),
        "inline_link": "無料の非公開ツールで画素数と非圧縮容量を先に計画",
        "index_title": "非公開文書スキャンプランナー",
        "index_description": "文書を読み取りもアップロードもせず、ppi、正確な画素数、非圧縮ラスター容量を計算します。",
    },
    "ko": {
        "title": "비공개 문서 스캔 계획 도구 | ppi, 픽셀, 용량 범위",
        "description": "문서를 업로드하거나 읽지 않고 스캔 해상도, 정확한 픽셀 크기와 비압축 래스터 용량을 계획하세요.",
        "tools": "무료 도구",
        "switch": "영어",
        "eyebrow": "무료 · 로컬 계산 · 문서 업로드 없음",
        "heading": "비공개 문서 스캔 계획 도구",
        "lead": "용지, 세부 수준과 색상 모드를 선택하면 브라우저가 픽셀과 이론적 비압축 MiB만 계산하며 문서를 받지 않습니다.",
        "badges": (
            "파일이나 문서 입력 없음",
            "OCR 또는 클라우드 요청 없음",
            "압축 파일 크기 추정 없음",
            "기록 보존 규정 준수 주장 없음",
        ),
        "planner": "캡처 계획하기",
        "planner_intro": "세 가지 세부 프로필은 계획의 출발점일 뿐 품질 보장이나 공식 인증이 아닙니다.",
        "paper_label": "용지 크기",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "미국 레터 · 8.5×11 in",
            "us-legal": "미국 리걸 · 8.5×14 in",
        },
        "purpose_label": "세부 프로필",
        "purpose_options": {
            "everyday-text": "일반 텍스트 · 300 ppi",
            "small-print": "작은 글자나 혼합 표시 · 400 ppi",
            "fine-detail": "가는 선이나 도장 · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "선명한 현대 문서용 300 ppi 계획 기준이며 OCR 정확도나 기록 규정 준수를 인증하지 않습니다.",
            "small-print": "작은 글자나 혼합 표시용 400 ppi 옵션입니다. 여러 장을 처리하기 전에 첫 페이지를 확인하세요.",
            "fine-detail": "가는 선이나 아주 작은 표시가 중요한 경우의 600 ppi 옵션입니다. 메모리 사용량이 크게 늘며 인식 결과를 보장하지 않습니다.",
        },
        "color_label": "색상 모드",
        "color_options": {"grayscale": "8-bit 그레이스케일", "rgb": "24-bit RGB 컬러"},
        "color_notes": {
            "grayscale": "색상이 의미를 담지 않을 때만 사용하고 도장, 형광 표시, 손글씨와 주석을 먼저 확인하세요.",
            "rgb": "도장, 형광 표시, 손글씨, 주석 또는 원본 외관을 해석하는 데 색상이 중요하면 RGB를 사용하세요.",
        },
        "orientation_label": "방향",
        "orientation_options": {"portrait": "세로", "landscape": "가로"},
        "pages_label": "페이지 수",
        "calculate": "계획 업데이트",
        "result_title": "계산된 스캔 계획",
        "dpi": "선택한 ppi",
        "pixels": "페이지당 픽셀",
        "megapixels": "페이지당 메가픽셀",
        "per_page": "페이지당 비압축 MiB",
        "total": "전체 페이지 비압축 MiB",
        "result_boundary": "이 MiB는 파일 헤더, 압축, OCR 텍스트 또는 PDF 구조가 추가되기 전의 수학적 픽셀 데이터량입니다. 실제 PDF, JPEG, TIFF 크기는 달라지므로 압축 후 파일 크기를 추정하지 않습니다.",
        "capture_title": "여러 장을 처리하기 전 확인할 다섯 가지",
        "capture_checks": (
            "페이지 전체와 모든 가장자리가 보이게 하고 원본을 손상하지 않는 범위에서 접힌 부분을 펴세요.",
            "고른 조명을 사용하고 반사, 그림자, 손가락, 흐림과 잘린 모서리를 확인하세요.",
            "색상이 정보를 담으면 RGB를 선택하고 그렇지 않을 때만 그레이스케일을 고려하세요.",
            "첫 페이지를 확대해 가장 작은 중요 글자나 표시를 확인하세요.",
            "모든 OCR 결과를 이미지와 대조하세요. OCR은 항상 정확하지 않습니다.",
        ),
        "scope_title": "이 도구가 인증할 수 없는 사항",
        "scope_text": "문서, 이미지, 파일, 카메라 입력, OCR 텍스트, 자유 입력, 이름이나 개인정보를 받지 않으며 스캔, 보정, OCR, 검사, 업로드 또는 저장을 하지 않습니다. cookie, 분석, 광고나 네트워크 요청도 사용하지 않습니다. OCR, 가독성, 품질, 법적 효력, 접근성, 기록 보존, 정부, 세무, 의료 또는 교육 규정 준수를 보장하지 않으며 임의의 휴대폰 스캔 App에서 지정 ppi를 정밀하게 제어할 수 있다고 주장하지 않습니다. 영구, 규제 또는 증거 기록에는 담당 기관의 현행 사양과 품질 관리가 필요합니다.",
        "sources_title": "공식 배경 자료이며 보증이 아닙니다",
        "sources_intro": "NARA와 FADGI는 미국 영구 기록과 디지털화 맥락이며 지역 법률이나 이 도구의 인증이 아닙니다. Apple 자료는 메모 또는 파일에서 스캔, 모서리 조정, 여러 페이지, 저장 위치와 마크업 서명 절차만 설명합니다. OCR, ppi, 파일 크기, ScanTo 기능이나 Apple 보증을 뜻하지 않습니다.",
        "source_labels": (
            "36 CFR 1236.50: 영구 종이 기록 디지털화 요건",
            "FADGI: 기술 디지털화 지침",
            "NARA: OCR 전사는 항상 정확하지 않음",
            "Apple 지원: 메모 또는 파일에서 문서를 스캔하고 명시된 편집 및 저장 절차 사용",
        ),
        "webmcp_source": "Chrome WebMCP 명령형 API 미리보기(변경될 수 있음)",
        "webmcp_description": "범위가 제한된 용지, 세부 수준, 색상, 방향과 페이지 수로 비공개 스캔 계획을 계산합니다. 문서를 수신, 읽기, 업로드, 저장 또는 OCR 처리하지 않고 정확도나 규정 준수를 주장하지 않으며 정확한 픽셀 크기와 비압축 래스터 범위를 반환합니다.",
        "app_title": "iPhone에서 종이를 PDF로 만드는 과정이 필요한가요?",
        "app_text": "ScanTo Pro는 선택적으로 사용할 수 있는 iPhone 도구입니다. 현재 스토어 설명에는 문서 스캔, PDF 생성, OCR 검색, Face ID 문서 보호와 일회성 평생 잠금 해제가 기재되어 있습니다. 제공 여부와 정확한 기능은 현재 스토어 설명을 확인하세요. 이 무료 계획 도구는 App 없이도 작동합니다.",
        "app_cta": "App Store에서 ScanTo Pro 보기",
        "faq_title": "스캔 전 질문",
        "faq": (
            ("이 페이지가 내 문서를 업로드하나요?", "아니요. 파일 선택기가 없고 문서 텍스트나 이미지를 받지 않으며 제한된 설정만 계산합니다."),
            ("300 ppi면 OCR이 정확한가요?", "아니요. OCR은 원본, 글꼴, 언어, 배치, 초점, 조명과 처리 방식에 따라 달라지며 확인이 필요합니다."),
            ("MiB가 최종 PDF 크기인가요?", "아니요. 비압축 픽셀 데이터량이며 압축, 페이지 구조, OCR과 메타데이터가 최종 크기를 바꿉니다."),
            ("NARA 또는 FADGI 요건을 충족하나요?", "아니요. 해당 절차에는 캡처, 장비, 테스트 타깃, 품질 관리와 기록 통제가 더 폭넓게 포함됩니다."),
        ),
        "footer": "비공개 계획 계산만 수행 · 업로드 없음 · 첫 페이지 확인",
        "feature_list": (
            "문서, 파일, 카메라, OCR 텍스트 또는 개인정보 입력 없음",
            "300, 400, 600 ppi로 제한된 계획 프로필",
            "정확한 픽셀 크기와 이론적 비압축 MiB",
            "업로드, 저장, cookie, 분석, 광고 또는 네트워크 요청 없음",
            "정확도, 법적 효력, 접근성 또는 규정 준수 보장 없음",
        ),
        "inline_link": "무료 비공개 도구로 픽셀과 비압축 용량을 먼저 계획하기",
        "index_title": "비공개 문서 스캔 계획 도구",
        "index_description": "문서를 읽거나 업로드하지 않고 ppi, 정확한 픽셀과 비압축 래스터 용량을 계산합니다.",
    },
    "zh-Hans": {
        "title": "私密文档扫描规划器｜ppi、像素与容量边界",
        "description": "无需上传或读取文档，即可规划扫描分辨率、精确像素尺寸与未压缩栅格容量边界。",
        "tools": "免费工具",
        "switch": "英文",
        "eyebrow": "免费 · 本地计算 · 不上传文档",
        "heading": "私密文档扫描规划器",
        "lead": "选择纸张、细节需求与色彩模式；浏览器只计算像素及理论未压缩 MiB，完全不接收文档。",
        "badges": (
            "不输入文件或文档",
            "不执行 OCR 或云端请求",
            "不猜测压缩后大小",
            "不宣称符合档案规范",
        ),
        "planner": "规划扫描",
        "planner_intro": "三种细节选项只是规划起点，不保证质量，也不是官方认证。",
        "paper_label": "纸张尺寸",
        "paper_options": {
            "a4": "A4 · 210×297 mm",
            "a5": "A5 · 148×210 mm",
            "us-letter": "美规 Letter · 8.5×11 in",
            "us-legal": "美规 Legal · 8.5×14 in",
        },
        "purpose_label": "细节需求",
        "purpose_options": {
            "everyday-text": "一般文字 · 300 ppi",
            "small-print": "小字或混合标记 · 400 ppi",
            "fine-detail": "细线或印章 · 600 ppi",
        },
        "purpose_notes": {
            "everyday-text": "清晰现代文字可先按 300 ppi 规划；这不代表 OCR 准确，也不证明符合档案规范。",
            "small-print": "小字或混合标记可选 400 ppi；批量扫描前先放大检查第一页。",
            "fine-detail": "细线或极小标记可选 600 ppi；内存用量会大幅增加，仍不保证识别结果。",
        },
        "color_label": "色彩模式",
        "color_options": {"grayscale": "8-bit 灰度", "rgb": "24-bit RGB 彩色"},
        "color_notes": {
            "grayscale": "只有色彩不影响内容时才用灰度；先确认印章、荧光标记、手写字与批注。",
            "rgb": "印章、荧光标记、手写字、批注或原貌的色彩有意义时，使用 RGB 彩色。",
        },
        "orientation_label": "方向",
        "orientation_options": {"portrait": "纵向", "landscape": "横向"},
        "pages_label": "页数",
        "calculate": "更新规划",
        "result_title": "扫描规划结果",
        "dpi": "选定 ppi",
        "pixels": "每页像素",
        "megapixels": "每页百万像素",
        "per_page": "每页未压缩 MiB",
        "total": "全部页面未压缩 MiB",
        "result_boundary": "这些 MiB 是文件头、压缩、OCR 文字或 PDF 结构之前的数学像素量。实际 PDF、JPEG 与 TIFF 大小均会不同，因此本工具不估算压缩后文件大小。",
        "capture_title": "批量扫描前先确认五件事",
        "capture_checks": (
            "保留整张纸和全部边缘；在不损坏原件的前提下压平折痕。",
            "使用均匀光线，检查反光、阴影、手指、模糊及被裁掉的角落。",
            "色彩会影响信息时使用 RGB；否则才考虑灰度。",
            "放大第一页，检查最小但重要的文字或标记。",
            "把 OCR 结果和原始图像逐项核对；OCR 不一定准确。",
        ),
        "scope_title": "这个规划器不能证明什么",
        "scope_text": "本页不接收文档、图像、文件、相机内容、OCR 文字、自由文本、姓名或任何个人信息，也不扫描、增强、OCR、检查、上传或存储内容，且不使用 cookie、分析、广告或网络请求。它不保证 OCR、可读性、质量、法律效力、无障碍、档案、政府、税务、医疗或教育合规；任意手机扫描 App 也未必能精确控制指定 ppi。永久、受监管或证据文档仍须遵循主管机构的现行规范与质量控制流程。",
        "sources_title": "官方背景资料，不代表背书",
        "sources_intro": "NARA 与 FADGI 是美国永久档案及数字化语境，不是各地法律，也不认证本工具。Apple 支持页只说明在备忘录或“文件”中扫描、调整边角、多页、存储位置及用“标记”添加签名等流程；不能据此推断 OCR、ppi、文件大小、ScanTo 功能或 Apple 背书。",
        "source_labels": (
            "36 CFR 1236.50：永久纸质档案数字化要求",
            "FADGI：数字化技术指南",
            "NARA：OCR 转录不一定准确",
            "Apple 支持：在备忘录或“文件”中扫描文档，以及明载的编辑与存储步骤",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览（规范可能变更）",
        "webmcp_description": "仅用有界的纸张、细节、色彩、方向与页数输入计算私密文档扫描规划，返回精确像素与透明的未压缩容量边界；不接收、读取、上传、存储或 OCR 处理文档，也不宣称准确度或规范符合性。",
        "app_title": "需要 iPhone 纸质文档转 PDF 流程？",
        "app_text": "ScanTo Pro 是可选的 iPhone 工具；当前商店页面说明包含文档扫描、PDF 创建、OCR 搜索及 Face ID 文档保护，并提供一次性终身解锁。供应地区与确切功能请以当前商店页面为准；这个免费规划器无需 App 也能使用。",
        "app_cta": "在 App Store 查看 ScanTo Pro",
        "faq_title": "扫描前常见问题",
        "faq": (
            ("这个网页会上传我的文档吗？", "不会。它没有文件选择器，也不接收文档文字或图像，只用有界设置计算。"),
            ("300 ppi 能保证 OCR 准确吗？", "不能。OCR 受原件、字体、语言、版面、对焦、光线与处理方式影响，结果必须核对。"),
            ("MiB 数值就是最终 PDF 大小吗？", "不是。那是未压缩像素量；压缩、页面结构、OCR 与元数据都会改变实际大小。"),
            ("这样就符合 NARA 或 FADGI 吗？", "不符合。那些流程还包含采集设备、测试标靶、质量管理及档案控制等要求。"),
        ),
        "footer": "只做私密规划计算 · 不上传 · 先核对第一页",
        "feature_list": (
            "不输入文档、文件、相机内容、OCR 文字或个人信息",
            "有界的 300、400 与 600 ppi 规划选项",
            "精确像素尺寸与理论未压缩 MiB",
            "不上传、不存储，不用 cookie、分析、广告或网络请求",
            "不保证准确度、法律效力、无障碍或规范符合性",
        ),
        "inline_link": "先用免费私密工具规划像素与未压缩容量",
        "index_title": "私密文档扫描规划器",
        "index_description": "不读取或上传文档，即时计算 ppi、精确像素与未压缩栅格容量边界。",
    },
    "vi": {
        "title": "Công cụ lập kế hoạch quét tài liệu riêng tư | DPI, pixel & giới hạn dung lượng",
        "description": "Lập kế hoạch độ phân giải quét, kích thước pixel chính xác và giới hạn dung lượng raster chưa nén minh bạch, không tải lên hay đọc tài liệu.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Miễn phí · tính cục bộ · không tải tài liệu lên",
        "heading": "Công cụ lập kế hoạch quét tài liệu riêng tư",
        "lead": "Chọn khổ giấy, hồ sơ chi tiết và chế độ màu. Trình duyệt tính pixel và dung lượng raster chưa nén lý thuyết; nó không bao giờ nhận tài liệu.",
        "badges": ("Không nhận tệp hay tài liệu", "Không OCR hay yêu cầu đám mây", "Không đoán dung lượng sau nén", "Không tuyên bố đạt chuẩn lưu trữ"),
        "planner": "Lập kế hoạch chụp quét",
        "planner_intro": "Ba hồ sơ chi tiết là điểm khởi đầu để lập kế hoạch, không phải bảo đảm chất lượng hay chứng nhận chính thức.",
        "paper_label": "Khổ giấy",
        "paper_options": {"a4": "A4 · 210×297 mm", "a5": "A5 · 148×210 mm", "us-letter": "US Letter · 8.5×11 in", "us-legal": "US Legal · 8.5×14 in"},
        "purpose_label": "Hồ sơ chi tiết",
        "purpose_options": {"everyday-text": "Chữ thông thường · 300 ppi", "small-print": "Chữ nhỏ hoặc ký hiệu lẫn · 400 ppi", "fine-detail": "Nét mảnh hoặc con dấu · 600 ppi"},
        "purpose_notes": {
            "everyday-text": "Mốc lập kế hoạch 300 ppi cho chữ hiện đại rõ ràng. Không chứng nhận độ chính xác OCR hay tuân thủ hồ sơ.",
            "small-print": "Tùy chọn 400 ppi chi tiết hơn cho chữ nhỏ hoặc ký hiệu lẫn. Kiểm tra trang đầu trước khi quét cả lô.",
            "fine-detail": "Tùy chọn 600 ppi khi nét mảnh hay dấu nhỏ quan trọng. Nó tăng bộ nhớ đáng kể và vẫn không bảo đảm nhận dạng.",
        },
        "color_label": "Chế độ màu",
        "color_options": {"grayscale": "Thang xám 8-bit", "rgb": "Màu RGB 24-bit"},
        "color_notes": {
            "grayscale": "Chỉ dùng khi màu không mang ý nghĩa. Kiểm tra con dấu, phần tô sáng, chữ viết tay và ghi chú trước.",
            "rgb": "Dùng RGB khi màu giúp hiểu con dấu, phần tô sáng, chữ viết tay, ghi chú hoặc diện mạo gốc.",
        },
        "orientation_label": "Hướng giấy",
        "orientation_options": {"portrait": "Dọc", "landscape": "Ngang"},
        "pages_label": "Số trang",
        "calculate": "Cập nhật kế hoạch",
        "result_title": "Kế hoạch quét đã tính",
        "dpi": "ppi đã chọn",
        "pixels": "Pixel mỗi trang",
        "megapixels": "Megapixel mỗi trang",
        "per_page": "MiB chưa nén mỗi trang",
        "total": "MiB chưa nén cho toàn bộ trang",
        "result_boundary": "Các giá trị MiB này là khối pixel toán học trước header tệp, nén, chữ OCR hay cấu trúc PDF. Dung lượng PDF, JPEG, TIFF thực tế thay đổi, nên công cụ không ước tính dung lượng sau nén.",
        "capture_title": "Năm kiểm tra trước khi quét cả lô",
        "capture_checks": (
            "Giữ trọn trang và mọi mép trong khung; vuốt phẳng nếp gấp mà không làm hỏng bản gốc.",
            "Dùng ánh sáng đều và kiểm tra lóa, bóng, ngón tay, nhòe và góc bị cắt.",
            "Chọn RGB khi màu mang thông tin; nếu không, thang xám có thể phù hợp.",
            "Phóng to trang đầu và soi chữ hoặc ký hiệu quan trọng nhỏ nhất.",
            "Đối chiếu mọi kết quả OCR với hình ảnh; OCR không phải lúc nào cũng chính xác.",
        ),
        "scope_title": "Điều công cụ này không thể chứng nhận",
        "scope_text": "Nó không nhận tài liệu, hình ảnh, tệp, đầu vào camera, chữ OCR, văn bản tự do, tên hay dữ liệu cá nhân. Nó không quét, tăng cường, OCR, kiểm tra, tải lên hay lưu trữ gì, và không dùng cookie, phân tích, quảng cáo hay yêu cầu mạng. Nó không thể bảo đảm OCR, độ dễ đọc, chất lượng, hiệu lực pháp lý, trợ năng, hay tuân thủ lưu trữ, chính phủ, thuế, y tế, giáo dục. Một mức ppi đã chọn có thể không điều khiển chính xác trong mọi ứng dụng quét trên điện thoại. Hồ sơ vĩnh viễn, có quy định hay mang tính chứng cứ cần đặc tả hiện hành và quy trình kiểm soát chất lượng của cơ quan chịu trách nhiệm.",
        "sources_title": "Ngữ cảnh chính thức, không phải chứng thực",
        "sources_intro": "NARA và FADGI mô tả bối cảnh số hóa và hồ sơ vĩnh viễn của Hoa Kỳ, không phải luật địa phương hay chứng nhận cho công cụ này. Apple Support chỉ mô tả quét trong Ghi chú và Tệp, chỉnh góc, nhiều trang, nơi lưu và chữ ký Markup; không hỗ trợ tuyên bố về OCR, ppi, dung lượng tệp, ScanTo hay chứng thực.",
        "source_labels": (
            "36 CFR 1236.50: yêu cầu số hóa hồ sơ giấy vĩnh viễn",
            "FADGI: hướng dẫn kỹ thuật số hóa",
            "NARA: bản chép OCR không phải lúc nào cũng chính xác",
            "Apple Support: quét tài liệu trong Ghi chú hoặc Tệp theo các bước chỉnh sửa và lưu chính thức",
        ),
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP (có thể thay đổi)",
        "webmcp_description": "Tính kế hoạch quét tài liệu riêng tư từ các lựa chọn giấy, chi tiết, màu, hướng và số trang có giới hạn. Trả về kích thước pixel chính xác và giới hạn raster chưa nén minh bạch, không nhận, đọc, tải lên, lưu hay OCR tài liệu, và không tuyên bố độ chính xác hay tuân thủ.",
        "app_title": "Cần quy trình giấy-sang-PDF trên iPhone?",
        "app_text": "ScanTo Pro là công cụ iPhone tùy chọn; trang hiện tại mô tả quét tài liệu, tạo PDF, tìm kiếm OCR và bảo vệ tài liệu bằng Face ID với mở khóa trọn đời một lần. Kiểm tra trang hiện tại để biết tính năng chính xác. Công cụ miễn phí này hoạt động không cần ứng dụng.",
        "app_cta": "Xem ScanTo Pro trên App Store",
        "faq_title": "Câu hỏi trước khi quét",
        "faq": (
            ("Trang này có tải tài liệu của tôi lên không?", "Không. Nó không có bộ chọn tệp và không nhận chữ hay ảnh tài liệu. Nó chỉ tính từ các thiết lập có giới hạn."),
            ("300 ppi có bảo đảm OCR chính xác không?", "Không. OCR phụ thuộc nguồn, kiểu chữ, ngôn ngữ, bố cục, tiêu điểm, ánh sáng và xử lý, và phải được kiểm tra."),
            ("Giá trị MiB có phải dung lượng PDF cuối không?", "Không. Đó là khối pixel chưa nén. Nén, cấu trúc trang, OCR và metadata thay đổi dung lượng cuối."),
            ("Cái này có đạt yêu cầu NARA hay FADGI không?", "Không. Các quy trình đó cần thiết bị, mục tiêu, quản lý chất lượng và kiểm soát hồ sơ rộng hơn."),
        ),
        "footer": "Chỉ là phép tính lập kế hoạch riêng tư · không tải lên · kiểm tra trang đầu",
        "feature_list": (
            "Không nhận tài liệu, tệp, camera, chữ OCR hay dữ liệu cá nhân",
            "Ba hồ sơ lập kế hoạch 300, 400, 600 ppi có giới hạn",
            "Kích thước pixel chính xác và MiB chưa nén lý thuyết",
            "Không tải lên, lưu trữ, cookie, phân tích, quảng cáo hay yêu cầu mạng",
            "Không bảo đảm độ chính xác, pháp lý, trợ năng hay tuân thủ",
        ),
        "inline_link": "Lập kế hoạch pixel và dung lượng chưa nén trước với công cụ riêng tư miễn phí",
        "index_title": "Công cụ lập kế hoạch quét tài liệu riêng tư",
        "index_description": "Tính ppi, pixel chính xác và giới hạn raster chưa nén, không tải lên hay đọc tài liệu.",
    },
    "th": {
        "title": "เครื่องมือวางแผนสแกนเอกสารแบบส่วนตัว | DPI พิกเซล และขอบเขตขนาด",
        "description": "วางแผนความละเอียดสแกน ขนาดพิกเซลที่แน่นอน และขอบเขตขนาดราสเตอร์ไม่บีบอัดแบบโปร่งใส โดยไม่อัปโหลดหรืออ่านเอกสาร",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "ฟรี · คณิตในเครื่อง · ไม่อัปโหลดเอกสาร",
        "heading": "เครื่องมือวางแผนสแกนเอกสารแบบส่วนตัว",
        "lead": "เลือกขนาดกระดาษ โปรไฟล์รายละเอียด และโหมดสี เบราว์เซอร์คำนวณพิกเซลและขนาดราสเตอร์ไม่บีบอัดทางทฤษฎี โดยไม่เคยรับเอกสาร",
        "badges": ("ไม่รับไฟล์หรือเอกสาร", "ไม่มี OCR หรือคำขอคลาวด์", "ไม่เดาขนาดหลังบีบอัด", "ไม่อ้างมาตรฐานจดหมายเหตุ"),
        "planner": "วางแผนการถ่ายสแกน",
        "planner_intro": "โปรไฟล์รายละเอียดทั้งสามเป็นจุดเริ่มต้นสำหรับวางแผน ไม่ใช่การรับประกันคุณภาพหรือการรับรองอย่างเป็นทางการ",
        "paper_label": "ขนาดกระดาษ",
        "paper_options": {"a4": "A4 · 210×297 มม.", "a5": "A5 · 148×210 มม.", "us-letter": "US Letter · 8.5×11 นิ้ว", "us-legal": "US Legal · 8.5×14 นิ้ว"},
        "purpose_label": "โปรไฟล์รายละเอียด",
        "purpose_options": {"everyday-text": "ข้อความทั่วไป · 300 ppi", "small-print": "ตัวพิมพ์เล็กหรือเครื่องหมายผสม · 400 ppi", "fine-detail": "เส้นละเอียดหรือตราประทับ · 600 ppi"},
        "purpose_notes": {
            "everyday-text": "ฐานวางแผน 300 ppi สำหรับข้อความสมัยใหม่ที่ชัดเจน ไม่รับรองความแม่นยำ OCR หรือการปฏิบัติตามกฎเอกสาร",
            "small-print": "ตัวเลือก 400 ppi สำหรับตัวพิมพ์เล็กหรือเครื่องหมายผสม ตรวจหน้าแรกก่อนสแกนทั้งชุด",
            "fine-detail": "ตัวเลือก 600 ppi เมื่อเส้นละเอียดหรือเครื่องหมายเล็กสำคัญ ใช้หน่วยความจำเพิ่มมากและยังไม่รับประกันการรู้จำ",
        },
        "color_label": "โหมดสี",
        "color_options": {"grayscale": "เฉดเทา 8 บิต", "rgb": "สี RGB 24 บิต"},
        "color_notes": {
            "grayscale": "ใช้เมื่อสีไม่มีความหมายเท่านั้น ตรวจตราประทับ ไฮไลต์ ลายมือ และหมายเหตุก่อน",
            "rgb": "ใช้ RGB เมื่อสีช่วยตีความตราประทับ ไฮไลต์ ลายมือ หมายเหตุ หรือรูปลักษณ์ต้นฉบับ",
        },
        "orientation_label": "แนวกระดาษ",
        "orientation_options": {"portrait": "แนวตั้ง", "landscape": "แนวนอน"},
        "pages_label": "จำนวนหน้า",
        "calculate": "อัปเดตแผน",
        "result_title": "แผนสแกนที่คำนวณแล้ว",
        "dpi": "ppi ที่เลือก",
        "pixels": "พิกเซลต่อหน้า",
        "megapixels": "เมกะพิกเซลต่อหน้า",
        "per_page": "MiB ไม่บีบอัดต่อหน้า",
        "total": "MiB ไม่บีบอัดทุกหน้า",
        "result_boundary": "ค่า MiB เหล่านี้คือปริมาณพิกเซลทางคณิตก่อนเฮดเดอร์ไฟล์ การบีบอัด ข้อความ OCR หรือโครงสร้าง PDF ขนาด PDF JPEG TIFF จริงต่างกันไป เครื่องมือนี้จึงไม่ประมาณขนาดไฟล์หลังบีบอัด",
        "capture_title": "ห้าข้อตรวจก่อนสแกนทั้งชุด",
        "capture_checks": (
            "ให้เห็นทั้งหน้าและทุกขอบ กดรอยพับให้เรียบโดยไม่ทำลายต้นฉบับ",
            "ใช้แสงสม่ำเสมอ ตรวจแสงสะท้อน เงา นิ้ว ภาพเบลอ และมุมที่ถูกตัด",
            "เลือก RGB เมื่อสีมีข้อมูล มิฉะนั้นเฉดเทาอาจเหมาะสม",
            "ซูมหน้าแรกและตรวจตัวอักษรหรือเครื่องหมายสำคัญที่เล็กที่สุด",
            "เทียบผล OCR กับภาพเสมอ OCR ไม่แม่นยำเสมอไป",
        ),
        "scope_title": "สิ่งที่เครื่องมือนี้รับรองไม่ได้",
        "scope_text": "มันไม่รับเอกสาร ภาพ ไฟล์ กล้อง ข้อความ OCR ข้อความอิสระ ชื่อ หรือข้อมูลส่วนตัว ไม่สแกน ปรับแต่ง OCR ตรวจสอบ อัปโหลด หรือเก็บสิ่งใด และไม่ใช้คุกกี้ การวิเคราะห์ โฆษณา หรือคำขอเครือข่าย มันรับประกัน OCR ความอ่านง่าย คุณภาพ ผลทางกฎหมาย การช่วยการเข้าถึง หรือการปฏิบัติตามกฎจดหมายเหตุ รัฐบาล ภาษี การแพทย์ การศึกษาไม่ได้ ppi ที่เลือกอาจควบคุมแม่นยำไม่ได้ในทุกแอปสแกน เอกสารถาวร มีกฎเกณฑ์ หรือเป็นหลักฐานต้องใช้สเปกปัจจุบันและกระบวนการควบคุมคุณภาพของหน่วยงานรับผิดชอบ",
        "sources_title": "บริบททางการ ไม่ใช่การรับรอง",
        "sources_intro": "NARA และ FADGI อธิบายบริบทเอกสารถาวรและการแปลงดิจิทัลของสหรัฐฯ ไม่ใช่กฎหมายท้องถิ่นหรือการรับรองเครื่องมือนี้ Apple Support อธิบายเพียงการสแกนในโน้ตและไฟล์ การปรับมุม หลายหน้า ที่บันทึก และลายเซ็น Markup ไม่รองรับคำกล่าวอ้างเรื่อง OCR ppi ขนาดไฟล์ ScanTo หรือการรับรอง",
        "source_labels": (
            "36 CFR 1236.50: ข้อกำหนดแปลงดิจิทัลเอกสารกระดาษถาวร",
            "FADGI: แนวทางเทคนิคการแปลงดิจิทัล",
            "NARA: การถอดความ OCR ไม่แม่นยำเสมอไป",
            "Apple Support: สแกนเอกสารในโน้ตหรือไฟล์ตามขั้นตอนแก้ไขและบันทึกที่เป็นทางการ",
        ),
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP (อาจเปลี่ยนแปลง)",
        "webmcp_description": "คำนวณแผนสแกนเอกสารส่วนตัวจากตัวเลือกกระดาษ รายละเอียด สี แนว และจำนวนหน้าแบบมีขอบเขต คืนขนาดพิกเซลแน่นอนและขอบเขตราสเตอร์ไม่บีบอัดโปร่งใส โดยไม่รับ อ่าน อัปโหลด เก็บ หรือ OCR เอกสาร และไม่อ้างความแม่นยำหรือการปฏิบัติตามกฎ",
        "app_title": "ต้องการเวิร์กโฟลว์กระดาษเป็น PDF บน iPhone ไหม?",
        "app_text": "ScanTo Pro เป็นเครื่องมือ iPhone แบบเลือกได้ หน้าปัจจุบันอธิบายการสแกนเอกสาร สร้าง PDF ค้นหา OCR และปกป้องเอกสารด้วย Face ID พร้อมปลดล็อกตลอดชีพครั้งเดียว ตรวจหน้าปัจจุบันสำหรับฟีเจอร์ที่แน่นอน เครื่องมือฟรีนี้ใช้ได้โดยไม่ต้องมีแอป",
        "app_cta": "ดู ScanTo Pro บน App Store",
        "faq_title": "คำถามก่อนสแกน",
        "faq": (
            ("หน้านี้อัปโหลดเอกสารของฉันไหม?", "ไม่ มันไม่มีตัวเลือกไฟล์และไม่รับข้อความหรือภาพเอกสาร คำนวณจากการตั้งค่าแบบมีขอบเขตเท่านั้น"),
            ("300 ppi รับประกัน OCR แม่นยำไหม?", "ไม่ OCR ขึ้นกับต้นฉบับ แบบอักษร ภาษา เลย์เอาต์ โฟกัส แสง และการประมวลผล ต้องตรวจสอบเสมอ"),
            ("ค่า MiB คือขนาด PDF สุดท้ายไหม?", "ไม่ มันคือปริมาณพิกเซลไม่บีบอัด การบีบอัด โครงสร้างหน้า OCR และเมทาดาทาเปลี่ยนขนาดไฟล์สุดท้าย"),
            ("ผ่านข้อกำหนด NARA หรือ FADGI ไหม?", "ไม่ เวิร์กโฟลว์เหล่านั้นต้องการอุปกรณ์ เป้าหมาย การจัดการคุณภาพ และการควบคุมเอกสารที่กว้างกว่า"),
        ),
        "footer": "คณิตวางแผนส่วนตัวเท่านั้น · ไม่อัปโหลด · ตรวจหน้าแรก",
        "feature_list": (
            "ไม่รับเอกสาร ไฟล์ กล้อง ข้อความ OCR หรือข้อมูลส่วนตัว",
            "โปรไฟล์วางแผน 300 400 600 ppi แบบมีขอบเขต",
            "ขนาดพิกเซลแน่นอนและ MiB ไม่บีบอัดทางทฤษฎี",
            "ไม่อัปโหลด เก็บ คุกกี้ วิเคราะห์ โฆษณา หรือคำขอเครือข่าย",
            "ไม่รับประกันความแม่นยำ กฎหมาย การช่วยการเข้าถึง หรือการปฏิบัติตามกฎ",
        ),
        "inline_link": "วางแผนพิกเซลและขนาดไม่บีบอัดก่อนด้วยเครื่องมือส่วนตัวฟรี",
        "index_title": "เครื่องมือวางแผนสแกนเอกสารแบบส่วนตัว",
        "index_description": "คำนวณ ppi พิกเซลแน่นอน และขอบเขตราสเตอร์ไม่บีบอัด โดยไม่อัปโหลดหรืออ่านเอกสาร",
    },
    "id": {
        "title": "Perencana Pindai Dokumen Privat | DPI, Piksel & Batas Ukuran",
        "description": "Rencanakan resolusi pindaian, dimensi piksel persis, dan batas ukuran raster tak terkompresi yang transparan tanpa mengunggah atau membaca dokumen.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Gratis · hitung lokal · tanpa unggah dokumen",
        "heading": "Perencana pindai dokumen privat",
        "lead": "Pilih ukuran kertas, profil detail, dan mode warna. Peramban menghitung piksel dan ukuran raster tak terkompresi teoretis; ia tidak pernah menerima dokumen.",
        "badges": ("Tanpa input file atau dokumen", "Tanpa OCR atau permintaan cloud", "Tanpa tebakan ukuran terkompresi", "Tanpa klaim kepatuhan arsip"),
        "planner": "Rencanakan pengambilan",
        "planner_intro": "Ketiga profil detail adalah titik awal perencanaan, bukan jaminan kualitas atau sertifikasi resmi.",
        "paper_label": "Ukuran kertas",
        "paper_options": {"a4": "A4 · 210×297 mm", "a5": "A5 · 148×210 mm", "us-letter": "US Letter · 8.5×11 in", "us-legal": "US Legal · 8.5×14 in"},
        "purpose_label": "Profil detail",
        "purpose_options": {"everyday-text": "Teks sehari-hari · 300 ppi", "small-print": "Cetakan kecil atau tanda campuran · 400 ppi", "fine-detail": "Garis halus atau stempel · 600 ppi"},
        "purpose_notes": {
            "everyday-text": "Basis perencanaan 300 ppi untuk teks modern yang jelas. Ini tidak menyertifikasi akurasi OCR atau kepatuhan arsip.",
            "small-print": "Opsi 400 ppi berdetail lebih tinggi untuk teks kecil atau tanda campuran. Periksa halaman pertama sebelum memindai satu batch.",
            "fine-detail": "Opsi 600 ppi saat garis halus atau tanda kecil penting. Ini menambah memori secara berarti dan tetap tidak menjamin pengenalan.",
        },
        "color_label": "Mode warna",
        "color_options": {"grayscale": "Skala abu 8-bit", "rgb": "Warna RGB 24-bit"},
        "color_notes": {
            "grayscale": "Gunakan hanya bila warna tidak membawa makna. Periksa dulu stempel, sorotan, tulisan tangan, dan anotasi.",
            "rgb": "Gunakan RGB bila warna membantu menafsirkan stempel, sorotan, tulisan tangan, anotasi, atau tampilan asli.",
        },
        "orientation_label": "Orientasi",
        "orientation_options": {"portrait": "Potret", "landscape": "Lanskap"},
        "pages_label": "Jumlah halaman",
        "calculate": "Perbarui rencana",
        "result_title": "Rencana pindai terhitung",
        "dpi": "ppi terpilih",
        "pixels": "Piksel per halaman",
        "megapixels": "Megapiksel per halaman",
        "per_page": "MiB tak terkompresi per halaman",
        "total": "MiB tak terkompresi semua halaman",
        "result_boundary": "Nilai MiB ini adalah muatan piksel matematis sebelum header file, kompresi, teks OCR, atau struktur PDF. Ukuran PDF, JPEG, dan TIFF nyata bervariasi, jadi alat ini tidak menaksir ukuran file terkompresi.",
        "capture_title": "Lima pemeriksaan sebelum satu batch",
        "capture_checks": (
            "Pastikan seluruh halaman dan semua tepinya terlihat; ratakan lipatan tanpa merusak aslinya.",
            "Gunakan cahaya merata dan periksa silau, bayangan, jari, buram, dan sudut terpotong.",
            "Pilih RGB bila warna membawa informasi; jika tidak, skala abu mungkin memadai.",
            "Perbesar halaman pertama dan periksa teks atau tanda penting terkecil.",
            "Bandingkan keluaran OCR dengan gambar; OCR tidak selalu akurat.",
        ),
        "scope_title": "Yang tidak dapat disertifikasi perencana ini",
        "scope_text": "Ia tidak menerima dokumen, gambar, file, input kamera, teks OCR, teks bebas, nama, atau data pribadi. Ia tidak memindai, mempertajam, meng-OCR, memeriksa, mengunggah, atau menyimpan apa pun, dan tidak memakai cookie, analitik, iklan, atau permintaan jaringan. Ia tidak dapat menjamin OCR, keterbacaan, kualitas, efek hukum, aksesibilitas, atau kepatuhan arsip, pemerintah, pajak, medis, maupun pendidikan. Ppi terpilih mungkin tidak dapat dikontrol persis di semua aplikasi pemindai. Arsip permanen, teregulasi, atau bersifat bukti memerlukan spesifikasi terkini dan proses kendali mutu otoritas yang bertanggung jawab.",
        "sources_title": "Konteks resmi, bukan endorsemen",
        "sources_intro": "NARA dan FADGI menggambarkan konteks arsip permanen dan digitalisasi AS, bukan hukum lokal atau sertifikasi alat ini. Apple Support hanya mendokumentasikan pemindaian di Catatan dan File, penyesuaian sudut, banyak halaman, lokasi penyimpanan, dan tanda tangan Markup; tidak mendukung klaim tentang OCR, ppi, ukuran file, ScanTo, atau endorsemen.",
        "source_labels": (
            "36 CFR 1236.50: persyaratan digitalisasi arsip kertas permanen",
            "FADGI: pedoman teknis digitalisasi",
            "NARA: transkripsi OCR tidak selalu akurat",
            "Apple Support: pindai dokumen di Catatan atau File dengan langkah edit dan simpan resmi",
        ),
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP (dapat berubah)",
        "webmcp_description": "Hitung rencana pindai dokumen privat dari input kertas, detail, warna, orientasi, dan jumlah halaman yang terbatas. Kembalikan dimensi piksel persis dan batas raster tak terkompresi yang transparan tanpa menerima, membaca, mengunggah, menyimpan, atau meng-OCR dokumen, dan tanpa mengklaim akurasi atau kepatuhan.",
        "app_title": "Perlu alur kertas-ke-PDF di iPhone?",
        "app_text": "ScanTo Pro adalah alat iPhone opsional; halaman terbarunya menjelaskan pemindaian dokumen, pembuatan PDF, pencarian OCR, dan perlindungan dokumen Face ID dengan buka kunci seumur hidup sekali bayar. Periksa halaman terbaru untuk fitur pastinya. Perencana gratis ini bekerja tanpa aplikasi tersebut.",
        "app_cta": "Lihat ScanTo Pro di App Store",
        "faq_title": "Pertanyaan sebelum memindai",
        "faq": (
            ("Apakah halaman ini mengunggah dokumen saya?", "Tidak. Ia tidak punya pemilih file dan tidak menerima teks atau gambar dokumen. Ia hanya menghitung dari pengaturan terbatas."),
            ("Apakah 300 ppi menjamin OCR akurat?", "Tidak. OCR bergantung pada sumber, tipografi, bahasa, tata letak, fokus, pencahayaan, dan pemrosesan, dan harus diperiksa."),
            ("Apakah nilai MiB adalah ukuran PDF akhir saya?", "Tidak. Itu muatan piksel tak terkompresi. Kompresi, struktur halaman, OCR, dan metadata mengubah ukuran akhir."),
            ("Apakah ini memenuhi persyaratan NARA atau FADGI?", "Tidak. Alur kerja itu memerlukan peralatan, target, manajemen mutu, dan kendali arsip yang lebih luas."),
        ),
        "footer": "Hanya matematika perencanaan privat · tanpa unggahan · periksa halaman pertama",
        "feature_list": (
            "Tanpa input dokumen, file, kamera, teks OCR, atau data pribadi",
            "Profil perencanaan terbatas 300, 400, dan 600 ppi",
            "Dimensi piksel persis dan MiB tak terkompresi teoretis",
            "Tanpa unggahan, penyimpanan, cookie, analitik, iklan, atau permintaan jaringan",
            "Tanpa jaminan akurasi, hukum, aksesibilitas, atau kepatuhan",
        ),
        "inline_link": "Rencanakan piksel dan ukuran tak terkompresi lebih dulu dengan alat privat gratis",
        "index_title": "Perencana Pindai Dokumen Privat",
        "index_description": "Hitung ppi, piksel persis, dan batas raster tak terkompresi tanpa mengunggah atau membaca dokumen.",
    },
    "tr": {
        "title": "Gizli Belge Tarama Planlayıcı | DPI, Piksel ve Boyut Sınırları",
        "description": "Belge yüklemeden veya okumadan tarama çözünürlüğünü, tam piksel boyutlarını ve şeffaf sıkıştırılmamış raster boyut sınırlarını planlayın.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Ücretsiz · yerel hesap · belge yükleme yok",
        "heading": "Gizli belge tarama planlayıcı",
        "lead": "Kâğıt boyutu, ayrıntı profili ve renk modu seçin. Tarayıcı pikselleri ve kuramsal sıkıştırılmamış raster boyutunu hesaplar; asla belge almaz.",
        "badges": ("Dosya veya belge girişi yok", "OCR veya bulut isteği yok", "Sıkıştırılmış boyut tahmini yok", "Arşiv uygunluğu iddiası yok"),
        "planner": "Çekimi planlayın",
        "planner_intro": "Üç ayrıntı profili planlama başlangıç noktalarıdır; kalite garantisi veya resmî sertifika değildir.",
        "paper_label": "Kâğıt boyutu",
        "paper_options": {"a4": "A4 · 210×297 mm", "a5": "A5 · 148×210 mm", "us-letter": "US Letter · 8,5×11 inç", "us-legal": "US Legal · 8,5×14 inç"},
        "purpose_label": "Ayrıntı profili",
        "purpose_options": {"everyday-text": "Günlük metin · 300 ppi", "small-print": "Küçük baskı veya karışık işaretler · 400 ppi", "fine-detail": "İnce çizgiler veya damgalar · 600 ppi"},
        "purpose_notes": {
            "everyday-text": "Net modern metin için 300 ppi planlama tabanı. OCR doğruluğunu veya kayıt uygunluğunu belgelemez.",
            "small-print": "Küçük metin veya karışık işaretler için daha ayrıntılı 400 ppi seçeneği. Bir partiyi taramadan önce ilk sayfayı inceleyin.",
            "fine-detail": "İnce çizgiler veya küçük işaretler önemliyse 600 ppi seçeneği. Belleği ciddi artırır ve yine de tanımayı garanti etmez.",
        },
        "color_label": "Renk modu",
        "color_options": {"grayscale": "8 bit gri ton", "rgb": "24 bit RGB renk"},
        "color_notes": {
            "grayscale": "Yalnızca renk anlam taşımadığında kullanın. Önce damgaları, vurguları, el yazısını ve notları kontrol edin.",
            "rgb": "Renk; damgaları, vurguları, el yazısını, notları veya özgün görünümü yorumlamaya yardım ediyorsa RGB kullanın.",
        },
        "orientation_label": "Yön",
        "orientation_options": {"portrait": "Dikey", "landscape": "Yatay"},
        "pages_label": "Sayfa sayısı",
        "calculate": "Planı güncelle",
        "result_title": "Hesaplanan tarama planı",
        "dpi": "Seçilen ppi",
        "pixels": "Sayfa başına piksel",
        "megapixels": "Sayfa başına megapiksel",
        "per_page": "Sayfa başına sıkıştırılmamış MiB",
        "total": "Tüm sayfalar için sıkıştırılmamış MiB",
        "result_boundary": "Bu MiB değerleri; dosya başlıkları, sıkıştırma, OCR metni veya PDF yapısından önceki matematiksel piksel yüküdür. Gerçek PDF, JPEG ve TIFF boyutları değişir; bu yüzden araç sıkıştırılmış dosya boyutu tahmini yapmaz.",
        "capture_title": "Bir partiden önce beş kontrol",
        "capture_checks": (
            "Tam sayfayı ve her kenarı görünür tutun; aslına zarar vermeden katları düzleştirin.",
            "Eşit ışık kullanın; parlama, gölge, parmak, bulanıklık ve kesik köşeleri kontrol edin.",
            "Renk bilgi taşıyorsa RGB seçin; aksi halde gri ton uygun olabilir.",
            "İlk sayfaya yakınlaşın ve en küçük önemli metni veya işareti inceleyin.",
            "Her OCR çıktısını görüntüyle karşılaştırın; OCR her zaman doğru değildir.",
        ),
        "scope_title": "Bu planlayıcının belgeleyemeyecekleri",
        "scope_text": "Belge, görüntü, dosya, kamera girişi, OCR metni, serbest metin, ad veya kişisel veri kabul etmez. Hiçbir şeyi taramaz, iyileştirmez, OCR yapmaz, incelemez, yüklemez veya saklamaz; çerez, analitik, reklam veya ağ isteği kullanmaz. OCR'yi, okunabilirliği, kaliteyi, hukuki etkiyi, erişilebilirliği veya arşiv, devlet, vergi, tıp, eğitim uygunluğunu garanti edemez. Seçilen ppi her telefon tarama uygulamasında tam kontrol edilemeyebilir. Kalıcı, düzenlemeye tabi veya delil niteliğindeki kayıtlar, sorumlu kurumun güncel şartnamesini ve kalite kontrol sürecini gerektirir.",
        "sources_title": "Resmî bağlam, onay değil",
        "sources_intro": "NARA ve FADGI, ABD kalıcı kayıt ve sayısallaştırma bağlamlarını anlatır; yerel hukuku veya bu aracın sertifikasyonunu değil. Apple Support yalnızca Notlar ve Dosyalar'da taramayı, köşe ayarlamayı, çoklu sayfayı, kayıt konumlarını ve Markup imzalarını belgeler; OCR, ppi, dosya boyutu, ScanTo veya onay iddialarını desteklemez.",
        "source_labels": (
            "36 CFR 1236.50: kalıcı kâğıt kayıtların sayısallaştırma gereksinimleri",
            "FADGI: teknik sayısallaştırma yönergeleri",
            "NARA: OCR transkripsiyonu her zaman doğru değildir",
            "Apple Support: Notlar veya Dosyalar'da belge tarama ve belgelenen düzenleme-kaydetme adımları",
        ),
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi (değişebilir)",
        "webmcp_description": "Sınırlı kâğıt, ayrıntı, renk, yön ve sayfa sayısı girdilerinden gizli bir belge tarama planı hesaplar. Belge almadan, okumadan, yüklemeden, saklamadan veya OCR işlemeden; doğruluk ya da uygunluk iddia etmeden tam piksel boyutları ve şeffaf sıkıştırılmamış raster sınırları döndürür.",
        "app_title": "iPhone'da kâğıttan PDF'e bir akış mı gerekiyor?",
        "app_text": "ScanTo Pro isteğe bağlı bir iPhone aracıdır; güncel sayfası belge taramayı, PDF oluşturmayı, OCR aramayı ve tek seferlik ömür boyu kilit açmayla Face ID belge korumasını anlatır. Kesin özellikler için güncel sayfayı kontrol edin. Bu ücretsiz planlayıcı uygulama olmadan da çalışır.",
        "app_cta": "App Store'da ScanTo Pro'yu görüntüle",
        "faq_title": "Taramadan önce sorular",
        "faq": (
            ("Bu sayfa belgemi yüklüyor mu?", "Hayır. Dosya seçici yoktur; belge metni veya görüntüsü kabul etmez. Yalnızca sınırlı ayarlardan hesaplar."),
            ("300 ppi doğru OCR'yi garanti eder mi?", "Hayır. OCR; kaynağa, tipografiye, dile, düzene, odağa, ışığa ve işlemeye bağlıdır ve kontrol edilmelidir."),
            ("MiB değeri nihai PDF boyutum mu?", "Hayır. Sıkıştırılmamış piksel yüküdür. Sıkıştırma, sayfa yapısı, OCR ve meta veriler nihai boyutu değiştirir."),
            ("Bu, NARA veya FADGI gereksinimlerini karşılar mı?", "Hayır. O iş akışları daha geniş ekipman, hedefler, kalite yönetimi ve kayıt kontrolleri gerektirir."),
        ),
        "footer": "Yalnızca gizli planlama matematiği · yükleme yok · ilk sayfayı doğrulayın",
        "feature_list": (
            "Belge, dosya, kamera, OCR metni veya kişisel veri girişi yok",
            "Sınırlı 300, 400 ve 600 ppi planlama profilleri",
            "Tam piksel boyutları ve kuramsal sıkıştırılmamış MiB",
            "Yükleme, depolama, çerez, analitik, reklam veya ağ isteği yok",
            "Doğruluk, hukuk, erişilebilirlik veya uygunluk garantisi yok",
        ),
        "inline_link": "Önce ücretsiz gizli araçla pikselleri ve sıkıştırılmamış boyutu planlayın",
        "index_title": "Gizli Belge Tarama Planlayıcı",
        "index_description": "Belge yüklemeden veya okumadan ppi, tam piksel ve sıkıştırılmamış raster sınırlarını hesaplayın.",
    },
}

STYLE = r"""
:root{--ink:#172033;--muted:#5c6679;--line:#dce3ec;--paper:#fff;--bg:#edf3f7;--navy:#19344d;--blue:#347aa1;--mint:#e4f5ee;--warn:#fff6da;--shadow:0 22px 60px rgba(28,49,70,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#dfe9ef 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#1d638c}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--navy);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--navy);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input{width:100%;min-height:46px;border:1px solid #cbd6e1;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--navy),var(--blue));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(25,52,77,.2)}
.results{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:11px;margin-top:22px}.metric{background:var(--mint);border:1px solid #c4e4d7;border-radius:17px;padding:14px;min-width:0}.metric strong,.metric span{display:block;white-space:nowrap;overflow-x:auto}.metric strong{font-size:clamp(20px,3vw,29px);color:#195946}.metric span{font-size:12px;color:#3d665b;font-weight:760;margin-top:3px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:16px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 30px;background:linear-gradient(135deg,#f8fbff,#e8f1f6)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:44px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--navy);color:#eaf1f6;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.app-card,.faq,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("scan-config").textContent);
  const form = document.getElementById("scan-planner");
  const fields = {
    paper: document.getElementById("paper"),
    purpose: document.getElementById("purpose"),
    color_mode: document.getElementById("color-mode"),
    orientation: document.getElementById("orientation"),
    page_count: document.getElementById("page-count")
  };
  const output = {
    dpi: document.getElementById("result-dpi"),
    pixels: document.getElementById("result-pixels"),
    megapixels: document.getElementById("result-megapixels"),
    perPage: document.getElementById("result-per-page"),
    total: document.getElementById("result-total"),
    note: document.getElementById("profile-note")
  };
  const MM_PER_INCH = 25.4;
  const MIB = 1024 * 1024;

  function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
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

  function pageCount(input) {
    if (!Object.prototype.hasOwnProperty.call(input, "page_count")) {
      throw new TypeError("page_count is required.");
    }
    const value = input.page_count;
    if (!Number.isInteger(value)) {
      throw new TypeError("page_count must be an integer.");
    }
    const schema = config.inputSchema.properties.page_count;
    if (value < schema.minimum || value > schema.maximum) {
      throw new RangeError("page_count is outside the supported range.");
    }
    return value;
  }

  function calculate(input) {
    const paperId = enumValue(input, "paper");
    const purposeId = enumValue(input, "purpose");
    const colorId = enumValue(input, "color_mode");
    const orientation = enumValue(input, "orientation");
    const pages = pageCount(input);
    const paper = config.papers[paperId];
    const purpose = config.purposes[purposeId];
    const color = config.colorModes[colorId];
    const widthMm = orientation === "portrait" ? paper.width_mm : paper.height_mm;
    const heightMm = orientation === "portrait" ? paper.height_mm : paper.width_mm;
    const widthPx = Math.round(widthMm / MM_PER_INCH * purpose.dpi);
    const heightPx = Math.round(heightMm / MM_PER_INCH * purpose.dpi);
    const pixels = widthPx * heightPx;
    const bytesPerPage = pixels * color.bits_per_pixel / 8;
    return {
      paper_id: paperId,
      paper_label: config.labels.paper[paperId],
      purpose_id: purposeId,
      purpose_label: config.labels.purpose[purposeId],
      purpose_note: config.purposeNotes[purposeId],
      color_mode: colorId,
      color_label: config.labels.color[colorId],
      color_note: config.colorNotes[colorId],
      orientation,
      orientation_label: config.labels.orientation[orientation],
      page_count: pages,
      dpi: purpose.dpi,
      width_mm: widthMm,
      height_mm: heightMm,
      width_px: widthPx,
      height_px: heightPx,
      megapixels_per_page: round(pixels / 1000000),
      uncompressed_bytes_per_page: bytesPerPage,
      uncompressed_mib_per_page: round(bytesPerPage / MIB),
      uncompressed_bytes_total: bytesPerPage * pages,
      uncompressed_mib_total: round(bytesPerPage * pages / MIB)
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
    return calculate(input);
  }

  function render() {
    const plan = calculate({
      paper: fields.paper.value,
      purpose: fields.purpose.value,
      color_mode: fields.color_mode.value,
      orientation: fields.orientation.value,
      page_count: Number(fields.page_count.value)
    });
    output.dpi.textContent = String(plan.dpi);
    output.pixels.textContent = `${plan.width_px}×${plan.height_px}`;
    output.megapixels.textContent = String(plan.megapixels_per_page);
    output.perPage.textContent = String(plan.uncompressed_mib_per_page);
    output.total.textContent = String(plan.uncompressed_mib_total);
    output.note.textContent = `${plan.purpose_note} ${plan.color_note}`;
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_document_scan",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_document_scan_plan",
          document_not_received_or_processed: true,
          not_ocr_or_compliance_certification: true,
          selected_plan: plan,
          capture_checklist: config.captureChecklist,
          compressed_output_boundary: config.compressedBoundary,
          compliance_boundary: config.complianceBoundary,
          ocr_boundary: config.ocrBoundary,
          optional_free_planner: config.freeTool,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_scanto_pro = config.optionalApp;
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


def options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    return {
        "type": "object",
        "properties": {
            "paper": {"type": "string", "enum": list(PAPERS)},
            "purpose": {"type": "string", "enum": list(PURPOSES)},
            "color_mode": {"type": "string", "enum": list(COLOR_MODES)},
            "orientation": {
                "type": "string",
                "enum": list(COPY[locale]["orientation_options"]),
            },
            "page_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": [
            "paper",
            "purpose",
            "color_mode",
            "orientation",
            "page_count",
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
        NARA_STANDARD,
        FADGI_GUIDELINES,
        NARA_OCR,
        APPLE_SCAN_DOCUMENTS,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    capture_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["capture_checks"]
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
        appstore_url(APP_KEY, f"iag_scan_plan_{locale.lower()}")
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
        "papers": PAPERS,
        "purposes": PURPOSES,
        "colorModes": COLOR_MODES,
        "inputSchema": webmcp_input_schema(locale),
        "labels": {
            "paper": t["paper_options"],
            "purpose": t["purpose_options"],
            "color": t["color_options"],
            "orientation": t["orientation_options"],
        },
        "purposeNotes": t["purpose_notes"],
        "colorNotes": t["color_notes"],
        "toolDescription": t["webmcp_description"],
        "captureChecklist": t["capture_checks"],
        "compressedBoundary": t["result_boundary"],
        "complianceBoundary": t["scope_text"],
        "ocrBoundary": t["faq"][1][1],
        "freeTool": {
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
        "applicationCategory": "UtilitiesApplication",
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
<section class="planner wrap" id="planner"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="scan-planner"><div class="controls">
<div class="field"><label for="paper">{html.escape(t["paper_label"])}</label><select id="paper">{options(t["paper_options"])}</select></div>
<div class="field"><label for="purpose">{html.escape(t["purpose_label"])}</label><select id="purpose">{options(t["purpose_options"])}</select></div>
<div class="field"><label for="color-mode">{html.escape(t["color_label"])}</label><select id="color-mode">{options(t["color_options"])}</select></div>
<div class="field"><label for="orientation">{html.escape(t["orientation_label"])}</label><select id="orientation">{options(t["orientation_options"])}</select></div>
<div class="field"><label for="page-count">{html.escape(t["pages_label"])}</label><input id="page-count" type="number" min="1" max="100" step="1" value="1"></div>
</div><button class="button" type="submit">{html.escape(t["calculate"])}</button></form>
<h2>{html.escape(t["result_title"])}</h2><div class="results" aria-live="polite">
<div class="metric"><strong id="result-dpi"></strong><span>{html.escape(t["dpi"])}</span></div>
<div class="metric"><strong id="result-pixels"></strong><span>{html.escape(t["pixels"])}</span></div>
<div class="metric"><strong id="result-megapixels"></strong><span>{html.escape(t["megapixels"])}</span></div>
<div class="metric"><strong id="result-per-page"></strong><span>{html.escape(t["per_page"])}</span></div>
<div class="metric"><strong id="result-total"></strong><span>{html.escape(t["total"])}</span></div>
</div><p class="note" id="profile-note"></p><p class="note">{html.escape(t["result_boundary"])}</p></section>
<section class="wrap grid">
<article class="card"><h2>{html.escape(t["capture_title"])}</h2><ol>{capture_items}</ol></article>
<article class="card"><h2>{html.escape(t["scope_title"])}</h2><p>{html.escape(t["scope_text"])}</p></article>
<article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article>
</section>
{app_card}
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="scan-config">{config_json}</script>
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
        r'image-to-pdf-iphone\.html">.*?</article>)',
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
    "best-document-scanner-app.html",
    "best-offline-document-scanner-app-for-iphone.html",
)
INBOUND_LINK_CLASS = "document-scan-planner-inline-link"
_SCANTO_CTA = re.compile(
    r'<a\b(?=[^>]*\shref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + re.escape(APP_ID)
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)


def insert_answer_links(pages: Path = PAGES) -> int:
    """Insert one localized resource link before each eligible ScanTo CTA."""
    changed = 0
    for locale in ALT_LOCALES:
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
        link = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-document-scan-planner-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS:
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _SCANTO_CTA.search(text)
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
        print(f"document scan planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
