#!/usr/bin/env python3
"""Generate a bilingual, private document scan planning tool."""

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
            "It does not scan, enhance, OCR, inspect or store a document. It cannot certify "
            "legal sufficiency, preservation quality, accessibility, OCR accuracy or compliance. "
            "Permanent, regulated or evidentiary records require the responsible authority's "
            "current specification and quality-control process."
        ),
        "sources_title": "Official context, not endorsement",
        "sources_intro": (
            "The U.S. federal sources below explain why 300 ppi, grayscale versus colour and "
            "quality review need context. Their permanent-record rules are stricter than this "
            "personal planning tool and do not certify its output."
        ),
        "source_labels": (
            "36 CFR 1236.50: permanent paper records digitization requirements",
            "FADGI: technical digitization guidelines",
            "NARA: OCR transcription is not always accurate",
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
        "switch": "English",
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
            "它不掃描、增強、OCR、檢查或儲存文件，也無法證明法律效力、典藏品質、"
            "無障礙、OCR 準確度或法規符合性。永久、受管制或證據文件必須遵循主管機關"
            "現行規格及品質控管流程。"
        ),
        "sources_title": "官方背景資料，不代表背書",
        "sources_intro": (
            "以下美國聯邦來源說明 300 ppi、灰階或彩色及品質檢查都需要情境判斷；"
            "永久檔案規範遠比這個個人規劃工具嚴格，也不會認證本工具結果。"
        ),
        "source_labels": (
            "36 CFR 1236.50：永久紙本檔案數位化要求",
            "FADGI：數位化技術指引",
            "NARA：OCR 轉錄不一定準確",
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
                "不是。那是未壓縮像素量；壓縮、頁面結構、OCR 與 metadata 都會改變實際容量。",
            ),
            (
                "這樣就符合 NARA 或 FADGI 嗎？",
                "不符合。那些流程還包含擷取設備、測試標靶、品質管理及檔案管控等要求。",
            ),
        ),
        "footer": "只做私密規劃運算 · 不上傳 · 先核對第一頁",
        "index_title": "私密文件掃描規劃器",
        "index_description": "不讀取或上傳文件，即時計算 ppi、精確像素與未壓縮影像容量界線。",
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
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
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


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other)
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    sources = (NARA_STANDARD, FADGI_GUIDELINES, NARA_OCR)
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
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "No document or file input",
            "300, 400 and 600 ppi planning profiles",
            "Exact pixel dimensions",
            "Transparent uncompressed raster size calculation",
            "No OCR, upload, storage or analytics",
        ],
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
<link rel="alternate" hreflang="{locale}" href="{url}">
<link rel="alternate" hreflang="{other}" href="{alternate}">
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
<section class="planner wrap" id="planner"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="scan-planner"><div class="controls">
<div class="field"><label for="paper">{html.escape(t["paper_label"])}</label><select id="paper">{options(t["paper_options"])}</select></div>
<div class="field"><label for="purpose">{html.escape(t["purpose_label"])}</label><select id="purpose">{options(t["purpose_options"])}</select></div>
<div class="field"><label for="color-mode">{html.escape(t["color_label"])}</label><select id="color-mode">{options(t["color_options"])}</select></div>
<div class="field"><label for="orientation">{html.escape(t["orientation_label"])}</label><select id="orientation">{options(t["orientation_options"])}</select></div>
<div class="field"><label for="page-count">{html.escape(t["pages_label"])}</label><input id="page-count" type="number" min="1" max="100" step="1" value="1"></div>
</div><button class="button" type="submit">{html.escape(t["calculate"])}</button></form>
<div class="results" aria-live="polite">
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


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    if app_public is None:
        app_public = APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        outputs.append(canonical(locale))
    update_one_index(pages / "tools" / "index.html", "en")
    update_one_index(
        pages / "zh-Hant" / "tools" / "index.html",
        "zh-Hant",
    )
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"document scan planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
