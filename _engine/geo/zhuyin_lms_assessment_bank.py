#!/usr/bin/env python3
"""Publish a bilingual, deterministic Bopomofo LMS question bank."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import (  # noqa: E402
    render_versioned_page,
    write_text_if_changed,
)
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from zhuyin_croissant_dataset import (  # noqa: E402
    APP_ID,
    APP_KEY,
    APP_NAME,
    LICENSE,
    SITE,
    records,
    validate_records,
)


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
VERSION = "1.0.0"
SLUG = "zhuyin-bopomofo-lms-question-bank"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-lms"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
LANDING_PATH = Path("data") / f"{SLUG}.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
METADATA_FILENAME = "metadata.jsonld"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
ANSWER_KEY_FILENAME = "answer-key.csv"
ANSWER_KEY_URL = f"{PACKAGE_URL}{ANSWER_KEY_FILENAME}"
SITEMAP_PATH = Path("sitemap_lms.xml")
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"

QTI_NAMESPACE = "http://www.imsglobal.org/xsd/imsqti_v2p1"
CP_NAMESPACE = "http://www.imsglobal.org/xsd/imscp_v1p1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
QTI_PACKAGE_SCHEMA_VERSION = "1.0.0"
QTI_SCHEMA = "http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
QTI_SPEC = "https://www.imsglobal.org/question/qtiv2p1/imsqti_implv2p1.html"
CANVAS_IMPORT = (
    "https://community.instructure.com/en/kb/articles/"
    "660996-how-do-i-import-quizzes-from-qti-packages"
)
MOODLE_IMPORT = "https://docs.moodle.org/en/Import_questions"
SOURCE_DATASET = f"{SITE}/data/zhuyin-bopomofo-ml-dataset.html"
RESOURCE_SYNC = f"{SITE}/resourcesync/capabilitylist.xml"
CARD_START = "<!-- lms-question-bank-card:start -->"
CARD_END = "<!-- lms-question-bank-card:end -->"

ARTIFACT_SPECS = {
    "qti_en": {
        "filename": "bopomofo-qti-2.1-en.zip",
        "label": "QTI 2.1 - English",
        "media_type": "application/zip",
        "locale": "en",
    },
    "qti_zh": {
        "filename": "bopomofo-qti-2.1-zh-hant.zip",
        "label": "QTI 2.1 - Traditional Chinese",
        "media_type": "application/zip",
        "locale": "zh-Hant",
    },
    "moodle_en": {
        "filename": "bopomofo-moodle-en.xml",
        "label": "Moodle XML - English",
        "media_type": "application/xml",
        "locale": "en",
    },
    "moodle_zh": {
        "filename": "bopomofo-moodle-zh-hant.xml",
        "label": "Moodle XML - Traditional Chinese",
        "media_type": "application/xml",
        "locale": "zh-Hant",
    },
    "answer_key": {
        "filename": ANSWER_KEY_FILENAME,
        "label": "Answer key",
        "media_type": "text/csv",
        "locale": "en",
    },
}

CATEGORY_NAMES = {
    "en": {
        "initial": "initial",
        "medial": "medial",
        "final": "final",
    },
    "zh-Hant": {
        "initial": "聲母",
        "medial": "介音",
        "final": "韻母",
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Free Bopomofo LMS Question Bank - QTI 2.1 and Moodle XML",
        "description": (
            "Download 37 bilingual-ready Bopomofo symbol-recognition questions "
            "as QTI 2.1 packages or native Moodle XML, with a CSV answer key."
        ),
        "eyebrow": "37 editable questions · QTI 2.1 · Moodle XML · CC BY 4.0",
        "lead": (
            "A teacher-ready, account-free question bank covering every Zhuyin "
            "initial, medial and final through its Hanyu Pinyin correspondence."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": (
            "37 single-response items",
            "English + Traditional Chinese",
            "No images or external media",
            "Deterministic packages",
        ),
        "downloads": "Choose an import format",
        "download_text": (
            "Use QTI 2.1 where the LMS supports QTI import. Use the separate "
            "Moodle XML files for Moodle's native question-bank importer."
        ),
        "qti": "QTI 2.1 packages",
        "qti_text": (
            "Each ZIP contains imsmanifest.xml and 37 self-contained QTI "
            "assessmentItem files using one accessible choiceInteraction each."
        ),
        "moodle": "Moodle XML files",
        "moodle_text": (
            "Each XML file contains one category and 37 multichoice questions "
            "with stable idnumbers, one-point grades and answer feedback."
        ),
        "answer": "Answer key and metadata",
        "answer_text": (
            "The CSV maps every stable item ID to category, Pinyin, Unicode and "
            "the correct symbol. JSON-LD records byte lengths and SHA-256 hashes."
        ),
        "canvas": "Import into Canvas",
        "canvas_steps": (
            "Download one QTI 2.1 ZIP without extracting it.",
            "In Course Settings, choose Import Course Content and QTI .zip file.",
            "Import into a staging course first and review all 37 questions.",
        ),
        "moodle_steps_title": "Import into Moodle",
        "moodle_steps": (
            "Download one Moodle XML file.",
            "Open the course Question bank, choose Import, then Moodle XML format.",
            "Review the imported category before using questions with learners.",
        ),
        "compatibility": "Compatibility boundary",
        "compatibility_text": (
            "LMS import behavior varies by product and version. QTI 2.1 is "
            "provided because Canvas currently documents QTI 1.2 and 2.1 "
            "imports; QTI 3.0 is intentionally not mislabeled as compatible. "
            "Moodle receives its own native XML export."
        ),
        "scope": "What this bank measures - and what it does not",
        "scope_text": (
            "These editable practice items check symbol-to-Pinyin correspondence "
            "only. They do not assess pronunciation, tone production, reading "
            "fluency or school readiness, and include no norm, level or cut score."
        ),
        "preview": "Question design preview",
        "category": "Category",
        "prompt": "Prompt",
        "correct": "Correct",
        "sources": "Standards and source data",
        "qti_standard": "Official QTI 2.1 implementation guide",
        "canvas_docs": "Canvas QTI import documentation",
        "moodle_docs": "Moodle question-import documentation",
        "dataset": "Canonical 37-symbol dataset",
        "license": "License and independence",
        "license_text": (
            "The question files, answer key and metadata are CC BY 4.0 and contain "
            "no App Store link, app identifier, account code or tracking."
        ),
        "app_title": "Optional on-device practice layer",
        "app_text": (
            "Lumi Bopomofo adds short on-device learning activities. The LMS "
            "question bank remains free, editable and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Open assessment content for teachers, weekend schools and "
            "heritage-language programs."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "免費注音 LMS 題庫：QTI 2.1 與 Moodle XML",
        "description": (
            "免費下載 37 題完整注音符號辨識題庫，提供 QTI 2.1、Moodle XML、"
            "CSV 答案鍵與可驗證 metadata。"
        ),
        "eyebrow": "37 題可編輯題目 · QTI 2.1 · Moodle XML · CC BY 4.0",
        "lead": (
            "教師可直接匯入的免帳號題庫，以漢語拼音對照完整涵蓋所有注音聲母、"
            "介音與韻母。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": (
            "37 題單選題",
            "英文＋繁體中文",
            "無圖片與外部媒體",
            "固定可重現套件",
        ),
        "downloads": "選擇匯入格式",
        "download_text": (
            "LMS 支援 QTI 時使用 QTI 2.1；Moodle 則使用另外提供的原生 "
            "Moodle XML 檔案。"
        ),
        "qti": "QTI 2.1 套件",
        "qti_text": (
            "每個 ZIP 內含 imsmanifest.xml 與 37 個自含 QTI assessmentItem，"
            "每題只使用一個易讀的 choiceInteraction。"
        ),
        "moodle": "Moodle XML 檔案",
        "moodle_text": (
            "每個 XML 內含一個分類與 37 題單選題，具穩定 idnumber、每題一分"
            "與答案回饋。"
        ),
        "answer": "答案鍵與 metadata",
        "answer_text": (
            "CSV 將每個穩定題目 ID 對應至分類、拼音、Unicode 與正確符號；"
            "JSON-LD 記錄 byte 長度與 SHA-256。"
        ),
        "canvas": "匯入 Canvas",
        "canvas_steps": (
            "下載一個 QTI 2.1 ZIP，不要解壓縮。",
            "在 Course Settings 選擇 Import Course Content 與 QTI .zip file。",
            "先匯入測試課程，逐一確認 37 題後再使用。",
        ),
        "moodle_steps_title": "匯入 Moodle",
        "moodle_steps": (
            "下載一個 Moodle XML 檔案。",
            "進入課程 Question bank，選擇 Import，再選 Moodle XML format。",
            "先檢查匯入的題目分類，再提供給學習者使用。",
        ),
        "compatibility": "相容性界線",
        "compatibility_text": (
            "LMS 匯入行為會因產品與版本而異。Canvas 目前文件列出 QTI 1.2 "
            "與 2.1，因此提供 QTI 2.1，而不把 QTI 3.0 誤標為相容；Moodle "
            "另提供原生 XML。"
        ),
        "scope": "本題庫可觀察與不可判斷的範圍",
        "scope_text": (
            "這些可編輯練習題只檢查符號與拼音對照，不評量發音、聲調表達、"
            "閱讀流暢度或入學準備，也沒有常模、分級或門檻分數。"
        ),
        "preview": "題目設計預覽",
        "category": "分類",
        "prompt": "題目",
        "correct": "正確答案",
        "sources": "標準與來源資料",
        "qti_standard": "QTI 2.1 官方實作指南",
        "canvas_docs": "Canvas QTI 匯入文件",
        "moodle_docs": "Moodle 題目匯入文件",
        "dataset": "37 符號標準資料集",
        "license": "授權與獨立性",
        "license_text": (
            "題目檔、答案鍵與 metadata 採 CC BY 4.0，且不含 App Store 連結、"
            "App 識別碼、帳號程式碼或追蹤。"
        ),
        "app_title": "選用裝置端練習層",
        "app_text": (
            "Lumi 注音星球提供裝置端短活動；LMS 題庫仍維持免費、可編輯且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": "供教師、週末中文學校與傳承語言課程使用的開放評量內容。",
    },
}


def page_url(locale: str) -> str:
    return LANDING_URL if locale == "en" else ZH_LANDING_URL


def _prompt(row: dict, locale: str) -> str:
    category = CATEGORY_NAMES[locale][row["category"]]
    if locale == "en":
        return (
            f'Which Bopomofo {category} corresponds to Hanyu Pinyin '
            f'"{row["pinyin"]}"?'
        )
    return (
        f'哪一個注音{category}對應漢語拼音「{row["pinyin"]}」？'
    )


def _feedback(row: dict, locale: str) -> str:
    if locale == "en":
        return (
            f'Correct answer: {row["symbol"]}. Example: '
            f'{row["example_character"]} ({row["example_pinyin"]}, '
            f'{row["example_meaning_en"]}).'
        )
    return (
        f'正確答案：{row["symbol"]}。例字：'
        f'{row["example_character"]}（{row["example_pinyin"]}）。'
    )


def questions(rows: list[dict], locale: str) -> list[dict]:
    groups = {
        category: [row for row in rows if row["category"] == category]
        for category in ("initial", "medial", "final")
    }
    output = []
    for row in rows:
        group = groups[row["category"]]
        index = group.index(row)
        choice_count = min(4, len(group))
        choices = [
            group[(index + offset) % len(group)]
            for offset in range(choice_count)
        ]
        shift = (row["order"] - 1) % choice_count
        choices = choices[shift:] + choices[:shift]
        output.append(
            {
                "item_id": f"bopomofo_{row['symbol_id'].lower()}",
                "title": (
                    f"Bopomofo {CATEGORY_NAMES['en'][row['category']]} "
                    f"{row['order']:02d}"
                    if locale == "en"
                    else f"注音{CATEGORY_NAMES['zh-Hant'][row['category']]}"
                    f"第 {row['order']:02d} 題"
                ),
                "prompt": _prompt(row, locale),
                "feedback": _feedback(row, locale),
                "correct_id": f"choice_{row['symbol_id'].lower()}",
                "correct_symbol": row["symbol"],
                "choices": [
                    {
                        "id": f"choice_{choice['symbol_id'].lower()}",
                        "symbol": choice["symbol"],
                    }
                    for choice in choices
                ],
                "source": row,
            }
        )
    return output


def render_qti_item(question: dict, locale: str) -> str:
    choices = "\n".join(
        f"      <simpleChoice identifier={quoteattr(choice['id'])}>"
        f"{escape(choice['symbol'])}</simpleChoice>"
        for choice in question["choices"]
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns="{QTI_NAMESPACE}"
  xmlns:xsi="{XSI_NAMESPACE}"
  xsi:schemaLocation="{QTI_NAMESPACE} {QTI_SCHEMA}"
  identifier={quoteattr(question["item_id"])}
  title={quoteattr(question["title"])}
  adaptive="false"
  timeDependent="false"
  xml:lang={quoteattr(locale)}>
  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{escape(question["correct_id"])}</value>
    </correctResponse>
  </responseDeclaration>
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float">
    <defaultValue><value>0</value></defaultValue>
  </outcomeDeclaration>
  <itemBody>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="1">
      <prompt>{escape(question["prompt"])}</prompt>
{choices}
    </choiceInteraction>
  </itemBody>
  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>
</assessmentItem>
"""


def render_qti_manifest(bank: list[dict], locale: str) -> str:
    resources = "\n".join(
        "    <resource identifier={identifier} type=\"imsqti_item_xmlv2p1\" "
        "href={href}>\n"
        "      <file href={href}/>\n"
        "    </resource>".format(
            identifier=quoteattr(f"resource_{question['item_id']}"),
            href=quoteattr(f"items/{question['item_id']}.xml"),
        )
        for question in bank
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="{CP_NAMESPACE}"
  xmlns:xsi="{XSI_NAMESPACE}"
  xsi:schemaLocation="{CP_NAMESPACE} http://www.imsglobal.org/xsd/qti/qtiv2p1/qtiv2p1_imscpv1p2_v1p0.xsd"
  identifier="bopomofo_question_bank_{locale.lower().replace('-', '_')}">
  <metadata>
    <schema>QTIv2.1 Package</schema>
    <schemaversion>{QTI_PACKAGE_SCHEMA_VERSION}</schemaversion>
  </metadata>
  <organizations/>
  <resources>
{resources}
  </resources>
</manifest>
"""


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for filename, payload in files.items():
            info = zipfile.ZipInfo(filename, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return buffer.getvalue()


def render_qti_package(rows: list[dict], locale: str) -> bytes:
    bank = questions(rows, locale)
    files = {
        "imsmanifest.xml": render_qti_manifest(bank, locale).encode("utf-8")
    }
    files.update(
        {
            f"items/{question['item_id']}.xml": render_qti_item(
                question, locale
            ).encode("utf-8")
            for question in bank
        }
    )
    return _zip_bytes(files)


def render_moodle_xml(rows: list[dict], locale: str) -> str:
    bank = questions(rows, locale)
    category = (
        "Bopomofo 37 Symbols - English"
        if locale == "en"
        else "注音符號 37 題 - 繁體中文"
    )
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<quiz>",
        '  <question type="category">',
        "    <category><text>"
        + escape(f"$course$/top/{category}")
        + "</text></category>",
        "  </question>",
    ]
    for question in bank:
        answers = []
        for choice in question["choices"]:
            fraction = "100" if choice["id"] == question["correct_id"] else "0"
            answers.append(
                f'    <answer fraction="{fraction}" format="html">'
                f"<text>{escape(choice['symbol'])}</text>"
                '<feedback format="html"><text></text></feedback></answer>'
            )
        parts.extend(
            [
                '  <question type="multichoice">',
                f"    <name><text>{escape(question['title'])}</text></name>",
                '    <questiontext format="html"><text>'
                + escape(f"<p>{question['prompt']}</p>")
                + "</text></questiontext>",
                '    <generalfeedback format="html"><text>'
                + escape(f"<p>{question['feedback']}</p>")
                + "</text></generalfeedback>",
                "    <defaultgrade>1.0000000</defaultgrade>",
                "    <penalty>0.3333333</penalty>",
                "    <hidden>0</hidden>",
                f"    <idnumber>{escape(question['item_id'])}</idnumber>",
                "    <single>true</single>",
                "    <shuffleanswers>false</shuffleanswers>",
                "    <answernumbering>abc</answernumbering>",
                *answers,
                "  </question>",
            ]
        )
    parts.append("</quiz>")
    return "\n".join(parts) + "\n"


def render_answer_key(rows: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    fieldnames = (
        "order",
        "item_id",
        "category",
        "pinyin",
        "correct_symbol",
        "unicode",
        "example_character",
        "example_pinyin",
    )
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "order": row["order"],
                "item_id": f"bopomofo_{row['symbol_id'].lower()}",
                "category": row["category"],
                "pinyin": row["pinyin"],
                "correct_symbol": row["symbol"],
                "unicode": row["unicode"],
                "example_character": row["example_character"],
                "example_pinyin": row["example_pinyin"],
            }
        )
    return buffer.getvalue()


def _artifact(key: str, payload: bytes) -> dict:
    spec = ARTIFACT_SPECS[key]
    return {
        **spec,
        "url": f"{PACKAGE_URL}{spec['filename']}",
        "bytes": payload,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def make_core_artifacts(rows: list[dict]) -> dict[str, dict]:
    return {
        "qti_en": _artifact("qti_en", render_qti_package(rows, "en")),
        "qti_zh": _artifact(
            "qti_zh", render_qti_package(rows, "zh-Hant")
        ),
        "moodle_en": _artifact(
            "moodle_en", render_moodle_xml(rows, "en").encode("utf-8")
        ),
        "moodle_zh": _artifact(
            "moodle_zh",
            render_moodle_xml(rows, "zh-Hant").encode("utf-8"),
        ),
        "answer_key": _artifact(
            "answer_key", render_answer_key(rows).encode("utf-8")
        ),
    }


def metadata_document(core: dict[str, dict], modified: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": ["Dataset", "LearningResource"],
        "@id": f"{LANDING_URL}#question-bank",
        "name": "Bopomofo 37-symbol LMS question bank",
        "alternateName": "注音符號 LMS 37 題題庫",
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "license": LICENSE,
        "isAccessibleForFree": True,
        "learningResourceType": "Assessment",
        "educationalUse": ["practice", "assessment"],
        "assesses": "Bopomofo symbol-to-Hanyu-Pinyin correspondence",
        "keywords": [
            "Bopomofo",
            "Zhuyin",
            "QTI 2.1",
            "Moodle XML",
            "LMS question bank",
            "Traditional Chinese",
            "heritage language",
        ],
        "conformsTo": [QTI_SPEC, MOODLE_IMPORT],
        "isBasedOn": SOURCE_DATASET,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps",
            "url": SITE,
        },
        "includedInDataCatalog": {
            "@type": "DataCatalog",
            "name": "Lumi Apps Open Data",
            "url": f"{SITE}/data/",
        },
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifact["label"],
                "encodingFormat": artifact["media_type"],
                "contentUrl": artifact["url"],
                "contentSize": f"{len(artifact['bytes'])} bytes",
                "sha256": artifact["sha256"],
                "inLanguage": artifact["locale"],
            }
            for artifact in core.values()
        ],
    }


def _metadata_artifact(core: dict[str, dict], modified: str) -> dict:
    payload = (
        json.dumps(
            metadata_document(core, modified),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    return {
        "filename": METADATA_FILENAME,
        "label": "Schema.org JSON-LD metadata",
        "media_type": "application/ld+json",
        "locale": "en",
        "url": METADATA_URL,
        "bytes": payload,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _prior_modified(output: Path) -> str:
    path = output / METADATA_FILENAME
    if not path.exists():
        return INITIAL_DATE
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get(
            "dateModified"
        )
    except (OSError, json.JSONDecodeError):
        return INITIAL_DATE
    return value if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or "") else INITIAL_DATE


def _write_bytes_if_changed(path: Path, payload: bytes) -> bool:
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


def _differs(path: Path, payload: bytes) -> bool:
    return not path.exists() or path.read_bytes() != payload


def write_artifacts(
    output: Path, rows: list[dict]
) -> tuple[dict[str, dict], str]:
    output.mkdir(parents=True, exist_ok=True)
    core = make_core_artifacts(rows)
    prior = _prior_modified(output)
    provisional_metadata = _metadata_artifact(core, prior)
    changed = any(
        _differs(output / artifact["filename"], artifact["bytes"])
        for artifact in core.values()
    ) or _differs(
        output / provisional_metadata["filename"],
        provisional_metadata["bytes"],
    )
    modified = TODAY if changed else prior
    artifacts = {**core, "metadata": _metadata_artifact(core, modified)}
    validate_artifacts(rows, artifacts)
    for artifact in artifacts.values():
        _write_bytes_if_changed(
            output / artifact["filename"], artifact["bytes"]
        )
    return artifacts, modified


def validate_artifacts(
    rows: list[dict], artifacts: dict[str, dict]
) -> None:
    validate_records(rows)
    expected = {
        f"bopomofo_{row['symbol_id'].lower()}": row for row in rows
    }
    text_payloads = []
    for key in ("qti_en", "qti_zh"):
        with zipfile.ZipFile(io.BytesIO(artifacts[key]["bytes"])) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"{key} contains a corrupt ZIP member")
            names = archive.namelist()
            if len(names) != len(set(names)) or names[0] != "imsmanifest.xml":
                raise ValueError(f"{key} has an invalid member inventory")
            expected_names = {
                "imsmanifest.xml",
                *[f"items/{item_id}.xml" for item_id in expected],
            }
            if set(names) != expected_names:
                raise ValueError(f"{key} does not contain all 37 QTI items")
            manifest = ET.fromstring(archive.read("imsmanifest.xml"))
            resources = manifest.findall(
                f".//{{{CP_NAMESPACE}}}resource"
            )
            if (
                len(resources) != 37
                or any(
                    resource.attrib.get("type") != "imsqti_item_xmlv2p1"
                    for resource in resources
                )
            ):
                raise ValueError(f"{key} has an invalid QTI manifest")
            for item_id, row in expected.items():
                payload = archive.read(f"items/{item_id}.xml")
                text_payloads.append(payload.decode("utf-8"))
                root = ET.fromstring(payload)
                if root.tag != f"{{{QTI_NAMESPACE}}}assessmentItem":
                    raise ValueError(f"{item_id} is not a QTI 2.1 item")
                values = root.findall(
                    f".//{{{QTI_NAMESPACE}}}correctResponse/"
                    f"{{{QTI_NAMESPACE}}}value"
                )
                choices = {
                    choice.attrib["identifier"]: choice.text
                    for choice in root.findall(
                        f".//{{{QTI_NAMESPACE}}}simpleChoice"
                    )
                }
                if (
                    len(values) != 1
                    or values[0].text not in choices
                    or choices[values[0].text] != row["symbol"]
                    or not 3 <= len(choices) <= 4
                ):
                    raise ValueError(f"{item_id} has an invalid answer")
            text_payloads.append(
                archive.read("imsmanifest.xml").decode("utf-8")
            )

    for key in ("moodle_en", "moodle_zh"):
        payload = artifacts[key]["bytes"]
        text_payloads.append(payload.decode("utf-8"))
        root = ET.fromstring(payload)
        questions_xml = root.findall("question")
        items = [
            question
            for question in questions_xml
            if question.attrib.get("type") == "multichoice"
        ]
        if len(items) != 37:
            raise ValueError(f"{key} must contain exactly 37 questions")
        seen = set()
        for item in items:
            item_id = item.findtext("idnumber")
            answers = item.findall("answer")
            correct = [
                answer
                for answer in answers
                if answer.attrib.get("fraction") == "100"
            ]
            if (
                item_id not in expected
                or item_id in seen
                or len(correct) != 1
                or correct[0].findtext("text")
                != expected[item_id]["symbol"]
            ):
                raise ValueError(f"{key} has an invalid Moodle question")
            seen.add(item_id)

    answer_rows = list(
        csv.DictReader(
            io.StringIO(
                artifacts["answer_key"]["bytes"].decode("utf-8")
            )
        )
    )
    if len(answer_rows) != 37 or {
        row["item_id"] for row in answer_rows
    } != set(expected):
        raise ValueError("Answer key must contain all 37 stable item IDs")
    for row in answer_rows:
        if row["correct_symbol"] != expected[row["item_id"]]["symbol"]:
            raise ValueError("Answer key drifted from the source table")

    metadata = json.loads(artifacts["metadata"]["bytes"])
    if len(metadata.get("distribution", [])) != 5:
        raise ValueError("Question-bank metadata must list five downloads")
    text_payloads.extend(
        artifact["bytes"].decode("utf-8")
        for key, artifact in artifacts.items()
        if key not in {"qti_en", "qti_zh"}
    )
    combined = "\n".join(text_payloads)
    for forbidden in (
        "apps.apple.com",
        APP_ID,
        APP_NAME,
        "SoftwareApplication",
    ):
        if forbidden in combined:
            raise ValueError(
                f"App promotion leaked into LMS artifacts: {forbidden}"
            )


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _schema_graph(
    locale: str,
    artifacts: dict[str, dict],
    artifact_modified: str,
    page_modified: str,
    app_public: bool,
) -> dict:
    learning_resource = metadata_document(
        {
            key: value
            for key, value in artifacts.items()
            if key != "metadata"
        },
        artifact_modified,
    )
    learning_resource.pop("@context")
    learning_resource.update(
        {
            "name": COPY[locale]["title"],
            "description": COPY[locale]["description"],
            "url": page_url(locale),
            "inLanguage": locale,
        }
    )
    graph = [
        {
            "@type": "WebPage",
            "@id": page_url(locale),
            "name": COPY[locale]["title"],
            "description": COPY[locale]["description"],
            "url": page_url(locale),
            "inLanguage": locale,
            "dateModified": page_modified,
            "mainEntity": {"@id": f"{LANDING_URL}#question-bank"},
        },
        learning_resource,
    ]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "EducationApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(
                    APP_KEY, f"iag_bopomofo_lms_{locale.lower()}"
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, artifacts: dict[str, dict]) -> str:
    return "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>{filename}</span><small>{size}</small></a>".format(
            url=html.escape(artifact["url"], quote=True),
            label=html.escape(artifact["label"]),
            filename=html.escape(artifact["filename"]),
            size=f"{len(artifact['bytes']):,} bytes",
        )
        for artifact in artifacts.values()
    )


def _preview_rows(rows: list[dict], locale: str) -> str:
    selected = [rows[0], rows[11], rows[21], rows[23], rows[24], rows[36]]
    return "".join(
        "<tr><td>{category}</td><td>{prompt}</td>"
        '<td class="symbol">{symbol}</td></tr>'.format(
            category=html.escape(CATEGORY_NAMES[locale][row["category"]]),
            prompt=html.escape(_prompt(row, locale)),
            symbol=html.escape(row["symbol"]),
        )
        for row in selected
    )


def render_page(
    locale: str,
    rows: list[dict],
    artifacts: dict[str, dict],
    artifact_modified: str,
    app_public: bool,
    page_modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    canvas_steps = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["canvas_steps"]
    )
    moodle_steps = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["moodle_steps"]
    )
    schema = json.dumps(
        _schema_graph(
            locale,
            artifacts,
            artifact_modified,
            page_modified,
            app_public,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel app"><p class="kicker">{title}</p>'
            "<p>{text}</p><a class=\"button\" href=\"{url}\" "
            'rel="nofollow noopener">{cta} &rarr;</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY, f"iag_bopomofo_lms_{locale.lower()}"
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(page_modified, quote=True)}">
<link rel="canonical" href="{html.escape(page_url(locale), quote=True)}">
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<link rel="resourcesync" href="{RESOURCE_SYNC}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#15213a;--sub:#5d687c;--line:#dce3ed;--brand:#315fc4;--bg:#f4f7fb;--paper:#fff;--soft:#edf3ff;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.67 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1080px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.94);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding:62px 20px 34px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.07em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:980px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}h3{{margin:0 0 6px}}p{{color:var(--sub);margin:8px 0}}.lead{{font-size:clamp(17px,3vw,21px);max-width:850px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:23px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}main>.wrap{{margin-bottom:24px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 34px rgba(34,53,91,.05)}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:17px;background:var(--soft);text-decoration:none;min-width:0}}.download strong{{font-size:16px}}.download span,.download small{{color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.download span{{font-size:13px}}.two,.three{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.three{{grid-template-columns:repeat(3,minmax(0,1fr))}}ol{{padding-left:23px}}li{{margin:8px 0;color:var(--sub)}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:17px;margin-top:17px}}table{{border-collapse:collapse;width:100%;background:#fff}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line)}}th{{background:var(--soft);font-size:13px;white-space:nowrap}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:27px;font-weight:850;text-align:center;white-space:nowrap}}.links{{display:flex;flex-wrap:wrap;gap:10px;margin-top:17px}}.links a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:720;background:#fff}}.button{{display:inline-flex;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:820;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}footer{{padding:18px 20px 44px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:780px){{.downloads,.two,.three{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.links{{display:grid}}.links a{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(page_url(other), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="wrap hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap three"><article class="panel"><h2>{html.escape(copy['qti'])}</h2><p>{html.escape(copy['qti_text'])}</p></article><article class="panel"><h2>{html.escape(copy['moodle'])}</h2><p>{html.escape(copy['moodle_text'])}</p></article><article class="panel"><h2>{html.escape(copy['answer'])}</h2><p>{html.escape(copy['answer_text'])}</p></article></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['canvas'])}</h2><ol>{canvas_steps}</ol></article><article class="panel"><h2>{html.escape(copy['moodle_steps_title'])}</h2><ol>{moodle_steps}</ol></article></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['compatibility'])}</h2><p>{html.escape(copy['compatibility_text'])}</p></article><article class="panel"><h2>{html.escape(copy['scope'])}</h2><p>{html.escape(copy['scope_text'])}</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['category'])}</th><th>{html.escape(copy['prompt'])}</th><th>{html.escape(copy['correct'])}</th></tr></thead><tbody>{_preview_rows(rows, locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['sources'])}</h2><div class="links"><a href="{QTI_SPEC}" rel="noopener">{html.escape(copy['qti_standard'])}</a><a href="{CANVAS_IMPORT}" rel="noopener">{html.escape(copy['canvas_docs'])}</a><a href="{MOODLE_IMPORT}" rel="noopener">{html.escape(copy['moodle_docs'])}</a><a href="{SOURCE_DATASET}">{html.escape(copy['dataset'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a></article></section>
<div class="wrap">{app_section}</div>
</main>
<footer>{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def _update_data_index(
    pages: Path, artifacts: dict[str, dict], modified: str
) -> None:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index is missing: {index}")
    content = index.read_text(encoding="utf-8")
    block = (
        f'{CARD_START}<a class="item" href="{LANDING_URL}"><div>'
        '<span class="tag">QTI 2.1 · Moodle XML</span>'
        "<h2>Bopomofo LMS question bank</h2>"
        "<p>Thirty-seven editable symbol-recognition questions in English and "
        "Traditional Chinese with verifiable import files.</p></div>"
        f'<span class="arrow">&rarr;</span></a>{CARD_END}'
    )
    if CARD_START in content and CARD_END in content:
        updated = re.sub(
            re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        marker = '<p class="foot">'
        if marker not in content:
            raise RuntimeError("data/index.html is missing its footer marker")
        updated = content.replace(marker, block + marker, 1)

    schema_pattern = re.compile(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        re.DOTALL,
    )
    schema_match = schema_pattern.search(updated)
    if schema_match:
        try:
            catalog = json.loads(schema_match.group(2))
        except json.JSONDecodeError:
            catalog = None
        if isinstance(catalog, dict) and catalog.get("@type") == "DataCatalog":
            datasets = [
                dataset
                for dataset in catalog.get("dataset", [])
                if dataset.get("url") != LANDING_URL
            ]
            datasets.append(
                {
                    "@type": ["Dataset", "LearningResource"],
                    "name": COPY["en"]["title"],
                    "description": COPY["en"]["description"],
                    "url": LANDING_URL,
                    "dateModified": modified,
                    "license": LICENSE,
                    "learningResourceType": "Assessment",
                    "distribution": [
                        {
                            "@type": "DataDownload",
                            "name": artifact["label"],
                            "encodingFormat": artifact["media_type"],
                            "contentUrl": artifact["url"],
                        }
                        for artifact in artifacts.values()
                    ],
                }
            )
            catalog["dataset"] = datasets
            updated = (
                updated[: schema_match.start()]
                + schema_match.group(1)
                + json.dumps(catalog, ensure_ascii=False)
                + schema_match.group(3)
                + updated[schema_match.end() :]
            )
    write_text_if_changed(index, updated)


def render_sitemap(
    page_modified: dict[str, str],
    artifact_modified: str,
    artifacts: dict[str, dict],
) -> str:
    entries = [
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        *[
            (artifact["url"], artifact_modified)
            for artifact in artifacts.values()
        ],
    ]
    rows = "\n".join(
        f"  <url><loc>{escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n"
    )


def build(
    pages: Path = PAGES, app_public: bool | None = None
) -> list[str]:
    rows = records()
    validate_records(rows)
    artifacts, artifact_modified = write_artifacts(
        pages / PACKAGE_PATH, rows
    )
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / LANDING_PATH),
        ("zh-Hant", pages / ZH_LANDING_PATH),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_page(
                locale,
                rows,
                artifacts,
                artifact_modified,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    _update_data_index(pages, artifacts, artifact_modified)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(page_modified, artifact_modified, artifacts),
    )
    return [
        LANDING_URL,
        ZH_LANDING_URL,
        *[artifact["url"] for artifact in artifacts.values()],
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin LMS assessment resource -> {output}")


if __name__ == "__main__":
    main()
