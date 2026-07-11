#!/usr/bin/env python3
"""Build bilingual MARCXML, MODS and BIBFRAME records for the open Zhuyin EPUB."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from family_travel_dataset import render_versioned_page, write_text_if_changed
from videogen.registry import appstore_url
from zhuyin_croissant_dataset import APP_ID, APP_KEY, APP_NAME, LICENSE, SITE
from zhuyin_epub_opds import (
    COPY as EPUB_COPY,
    LANDING_URL as EPUB_LANDING_URL,
    METADATA_FILENAME as EPUB_METADATA_FILENAME,
    PACKAGE_PATH as EPUB_PACKAGE_PATH,
    is_app_public,
)


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)
VERSION = "1.0.0"
SLUG = "zhuyin-bopomofo-library-catalog-records"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-library"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}"
LANDING_PATH = Path("data") / f"{SLUG}.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
SITEMAP_PATH = Path("sitemap_library_catalog.xml")
SOURCE_METADATA_PATH = EPUB_PACKAGE_PATH / EPUB_METADATA_FILENAME
SOURCE_METADATA_URL = f"{SITE}/{SOURCE_METADATA_PATH.as_posix()}"

MARC_FILENAME = "bopomofo-37-symbol-reference.marcxml.xml"
MODS_FILENAME = "bopomofo-37-symbol-reference.mods.xml"
BIBFRAME_JSONLD_FILENAME = "bopomofo-37-symbol-reference.bibframe.jsonld"
BIBFRAME_TURTLE_FILENAME = "bopomofo-37-symbol-reference.bibframe.ttl"
BUNDLE_FILENAME = "bopomofo-37-symbol-library-catalog-bundle.zip"
METADATA_FILENAME = "metadata.jsonld"
PRIMARY_FILENAMES = (
    MARC_FILENAME,
    MODS_FILENAME,
    BIBFRAME_JSONLD_FILENAME,
    BIBFRAME_TURTLE_FILENAME,
)
DOWNLOAD_FILENAMES = (
    BUNDLE_FILENAME,
    *PRIMARY_FILENAMES,
    METADATA_FILENAME,
)

MARC_NS = "http://www.loc.gov/MARC21/slim"
MODS_NS = "http://www.loc.gov/mods/v3"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
BF = "http://id.loc.gov/ontologies/bibframe/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
MARC_SCHEMA = "https://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd"
MODS_SCHEMA = "https://www.loc.gov/standards/mods/v3/mods-3-8.xsd"
BIBFRAME_VOCABULARY = "https://id.loc.gov/ontologies/bibframe.html"
BIBFRAME_MODEL = "https://www.loc.gov/bibframe/docs/bibframe2-model.html"
CREATOR = "Lumi Apps - iOS App Guide"
CREATOR_URL = f"{SITE}/#organization"
CARD_START = "<!-- library-catalog-card:start -->"
CARD_END = "<!-- library-catalog-card:end -->"

FORMATS = {
    MARC_FILENAME: ("MARCXML", "application/marcxml+xml"),
    MODS_FILENAME: ("MODS 3.8", "application/mods+xml"),
    BIBFRAME_JSONLD_FILENAME: ("BIBFRAME 2.0 JSON-LD", "application/ld+json"),
    BIBFRAME_TURTLE_FILENAME: ("BIBFRAME 2.0 Turtle", "text/turtle"),
    BUNDLE_FILENAME: ("Complete ZIP bundle", "application/zip"),
    METADATA_FILENAME: ("Checksums and metadata", "application/ld+json"),
}

EDITIONS = {
    "en": {
        "lang": "en",
        "marc_lang": "eng",
        "title": EPUB_COPY["en"]["title"],
        "alternate": EPUB_COPY["zh-Hant"]["title"],
        "subtitle": "An EPUB 3.3 reference to all 37 Zhuyin symbols",
        "summary": EPUB_COPY["en"]["description"],
        "language_note": "Text in English with Traditional Chinese examples and Bopomofo.",
        "local_id": "LUMI-ZHUYIN-EPUB-EN-2026",
        "record_id": "lumi-zhuyin-epub-en-2026",
        "download_label": "Download the English EPUB",
        "extent": "1 online resource (1 EPUB file)",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "marc_lang": "chi",
        "title": EPUB_COPY["zh-Hant"]["title"],
        "alternate": EPUB_COPY["en"]["title"],
        "subtitle": "涵蓋全部 37 個注音符號的 EPUB 3.3 參考手冊",
        "summary": EPUB_COPY["zh-Hant"]["description"],
        "language_note": "正文為繁體中文，並附英文說明、漢語拼音與注音符號。",
        "local_id": "LUMI-ZHUYIN-EPUB-ZH-HANT-2026",
        "record_id": "lumi-zhuyin-epub-zh-hant-2026",
        "download_label": "下載繁體中文 EPUB",
        "extent": "1 個線上資源（1 個 EPUB 檔案）",
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Library catalog records for a Bopomofo EPUB",
        "description": (
            "Download bilingual MARCXML, MODS 3.8 and BIBFRAME 2.0 records "
            "for an open, 37-symbol Bopomofo EPUB."
        ),
        "eyebrow": "Library metadata · English + zh-Hant · CC BY 4.0",
        "lead": (
            "A school, public or overseas Chinese library can download one "
            "review-ready bundle, verify every byte and adapt two edition "
            "records to its local catalog."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "2 language editions",
            "MARCXML + MODS 3.8",
            "BIBFRAME 2.0",
            "SHA-256 fixity",
        ),
        "download": "Download the catalog package",
        "download_text": (
            "Start with the ZIP bundle, or download an individual syntax. "
            "Every record points to the exact EPUB edition it describes."
        ),
        "source": "Open the EPUB source page",
        "formats": "What each record contains",
        "format_items": (
            (
                "MARCXML",
                "Two MARC 21 bibliographic records with fixed fields, RDA "
                "content/media/carrier terms, summaries, language notes, "
                "access terms and direct 856 download links.",
            ),
            (
                "MODS 3.8",
                "Two MODS records with titles, corporate creator, publication, "
                "language, format, subjects, identifiers, rights and URLs.",
            ),
            (
                "BIBFRAME 2.0",
                "Two Work/Instance pairs in equivalent JSON-LD and Turtle, "
                "linked to language, carrier, creator, policy and EPUB nodes.",
            ),
        ),
        "verification": "Validation and provenance",
        "verification_text": (
            "MARCXML and MODS are checked against locally pinned official "
            "schemas on every build. JSON-LD and Turtle must parse to the same "
            "RDF graph, and every BIBFRAME term must exist in the official "
            "vocabulary snapshot. Source EPUB sizes and SHA-256 values are "
            "carried into the records."
        ),
        "limits": "Before importing into an ILS",
        "limits_text": (
            "These are candidate records, not institution-approved cataloging "
            "and not an ISBN, LCCN or OCLC assignment. Review local 040, subject, "
            "classification, access, holdings and normalization policies. If "
            "URL import rejects a static host's generic XML or JSON Content-Type, "
            "download the file first and import it locally."
        ),
        "specs": "Official specifications",
        "license": "CC BY 4.0 license",
        "app_title": "Optional companion activity",
        "app_text": (
            "The open EPUB and catalog records work without an app. If available "
            "in your region, Lumi Bopomofo adds short on-device practice."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "No account, analytics or learner profile is used. Cite the record "
            "source URL and review local cataloging policy before import."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音 EPUB 圖書館書目紀錄下載",
        "description": (
            "下載開放授權 37 符號注音 EPUB 的雙語 MARCXML、MODS 3.8 "
            "與 BIBFRAME 2.0 書目紀錄。"
        ),
        "eyebrow": "圖書館書目 · 英文＋繁體中文 · CC BY 4.0",
        "lead": (
            "學校、公共圖書館與海外華語館藏可下載一份可審核的完整資料包，"
            "逐檔驗證後，再依館內規則調整兩筆語言版本紀錄。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "2 個語言版本",
            "MARCXML + MODS 3.8",
            "BIBFRAME 2.0",
            "SHA-256 完整性",
        ),
        "download": "下載書目資料包",
        "download_text": (
            "可先下載完整 ZIP，或個別下載所需格式；每筆紀錄都會連到其描述的"
            "確切 EPUB 語言版本。"
        ),
        "source": "開啟 EPUB 來源頁",
        "formats": "每種紀錄包含的內容",
        "format_items": (
            (
                "MARCXML",
                "兩筆 MARC 21 書目紀錄，含固定欄、RDA 內容／媒體／載體詞彙、"
                "摘要、語言註、取用條件與直接下載的 856 欄位。",
            ),
            (
                "MODS 3.8",
                "兩筆 MODS 紀錄，含題名、團體創作者、出版資訊、語言、格式、"
                "主題、識別碼、權利與網址。",
            ),
            (
                "BIBFRAME 2.0",
                "JSON-LD 與 Turtle 提供語意相同的兩組 Work／Instance，並連結"
                "語言、載體、創作者、使用政策與 EPUB 節點。",
            ),
        ),
        "verification": "驗證與來源",
        "verification_text": (
            "每次建置都以本機固定版本的官方 schema 驗證 MARCXML 與 MODS；"
            "JSON-LD 與 Turtle 必須解析成相同 RDF 圖，且所有 BIBFRAME 詞彙"
            "都必須存在於官方詞彙快照。紀錄亦帶入來源 EPUB 的檔案大小與 "
            "SHA-256。"
        ),
        "limits": "匯入圖書館系統前",
        "limits_text": (
            "這些是候選紀錄，不代表任何機構已核定編目，也不是 ISBN、LCCN "
            "或 OCLC 號碼。請依館內規則審查 040、主題、分類、取用、館藏與"
            "正規化設定。若網址匯入因靜態主機的通用 XML／JSON Content-Type "
            "而失敗，請先下載檔案再從本機匯入。"
        ),
        "specs": "官方規格",
        "license": "CC BY 4.0 授權",
        "app_title": "選用的延伸活動",
        "app_text": (
            "開放 EPUB 與書目紀錄不需 App 即可使用；若所在地區可下載，"
            "Lumi 注音星球可提供裝置端短練習。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": (
            "不需帳號，不使用分析或學習者檔案。匯入前請引用紀錄來源網址，"
            "並依館內編目政策審核。"
        ),
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_bytes_if_changed(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def _parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _max_timestamp(*values: str) -> str:
    return max(values, key=_parse_timestamp)


def _next_timestamp(prior: str) -> str:
    floor = _parse_timestamp(prior) + dt.timedelta(seconds=1)
    return max(floor, _parse_timestamp(NOW)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_source(pages: Path) -> tuple[dict, dict[str, dict]]:
    metadata_path = pages / SOURCE_METADATA_PATH
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Build the Zhuyin EPUB before library records: {metadata_path}"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    editions = {}
    for item in metadata.get("encoding", []):
        if item.get("encodingFormat") != "application/epub+zip":
            continue
        locale = item.get("inLanguage")
        if locale not in EDITIONS:
            continue
        filename = Path(urlparse(item["contentUrl"]).path).name
        epub_path = pages / EPUB_PACKAGE_PATH / filename
        if not epub_path.exists():
            raise FileNotFoundError(f"Source EPUB is missing: {epub_path}")
        content = epub_path.read_bytes()
        expected_size = int(str(item["contentSize"]).split()[0])
        if len(content) != expected_size or _sha256(content) != item["sha256"]:
            raise ValueError(f"Source EPUB fixity mismatch: {epub_path}")
        editions[locale] = {
            **item,
            "filename": filename,
            "size": len(content),
            "sha256": _sha256(content),
        }
    if set(editions) != set(EDITIONS):
        raise ValueError("Source EPUB metadata must describe en and zh-Hant editions")
    modified = metadata.get("dateModified", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", modified):
        raise ValueError("Source EPUB metadata needs a full UTC dateModified")
    return metadata, editions


def _marc(name: str) -> str:
    return f"{{{MARC_NS}}}{name}"


def _marc_control(record: ET.Element, tag: str, value: str) -> None:
    ET.SubElement(record, _marc("controlfield"), {"tag": tag}).text = value


def _marc_data(
    record: ET.Element,
    tag: str,
    ind1: str,
    ind2: str,
    subfields: tuple[tuple[str, str], ...],
) -> None:
    field = ET.SubElement(
        record,
        _marc("datafield"),
        {"tag": tag, "ind1": ind1, "ind2": ind2},
    )
    for code, value in subfields:
        ET.SubElement(field, _marc("subfield"), {"code": code}).text = value


def _marc_008(date_published: str, language: str) -> str:
    value = [" "] * 40
    value[0:6] = date_published[2:].replace("-", "")
    value[6] = "s"
    value[7:11] = list(date_published[:4])
    value[15:18] = list("xx ")
    value[22] = "j"
    value[23] = "o"
    value[33] = "0"
    value[35:38] = list(language)
    value[39] = "d"
    rendered = "".join(value)
    if len(rendered) != 40:
        raise AssertionError("MARC 008 must contain exactly 40 characters")
    return rendered


def render_marcxml(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    ET.register_namespace("", MARC_NS)
    ET.register_namespace("xsi", XSI_NS)
    root = ET.Element(
        _marc("collection"),
        {
            f"{{{XSI_NS}}}schemaLocation": f"{MARC_NS} {MARC_SCHEMA}",
            "id": "bopomofo-37-symbol-reference",
        },
    )
    date_published = source["datePublished"]
    field_005 = _parse_timestamp(modified).strftime("%Y%m%d%H%M%S.0")
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        epub = editions[locale]
        record = ET.SubElement(
            root,
            _marc("record"),
            {"type": "Bibliographic", "id": copy["record_id"]},
        )
        ET.SubElement(record, _marc("leader")).text = "00000nam a2200000 i 4500"
        _marc_control(record, "001", copy["record_id"])
        _marc_control(record, "003", "LUMI")
        _marc_control(record, "005", field_005)
        _marc_control(record, "007", "cr||||||||||||")
        _marc_control(
            record,
            "008",
            _marc_008(date_published, copy["marc_lang"]),
        )
        _marc_data(
            record,
            "024",
            "7",
            " ",
            (("a", copy["local_id"]), ("2", "local")),
        )
        _marc_data(
            record,
            "040",
            " ",
            " ",
            (("a", "LUMI"), ("b", "eng"), ("e", "rda"), ("c", "LUMI")),
        )
        _marc_data(
            record,
            "041",
            "0",
            " ",
            (("a", copy["marc_lang"]),),
        )
        _marc_data(
            record,
            "245",
            "0",
            "0",
            (
                ("a", copy["title"]),
                ("b", copy["subtitle"]),
                ("c", CREATOR),
            ),
        )
        _marc_data(record, "246", "3", " ", (("a", copy["alternate"]),))
        _marc_data(record, "250", " ", " ", (("a", f"Version {VERSION}."),))
        _marc_data(
            record,
            "264",
            " ",
            "1",
            (
                ("a", "[Place of publication not identified]"),
                ("b", CREATOR),
                ("c", date_published[:4]),
            ),
        )
        _marc_data(record, "300", " ", " ", (("a", copy["extent"]),))
        _marc_data(
            record,
            "336",
            " ",
            " ",
            (("a", "text"), ("b", "txt"), ("2", "rdacontent")),
        )
        _marc_data(
            record,
            "337",
            " ",
            " ",
            (("a", "computer"), ("b", "c"), ("2", "rdamedia")),
        )
        _marc_data(
            record,
            "338",
            " ",
            " ",
            (("a", "online resource"), ("b", "cr"), ("2", "rdacarrier")),
        )
        _marc_data(
            record,
            "347",
            " ",
            " ",
            (("a", "text file"), ("b", "EPUB"), ("2", "rda")),
        )
        _marc_data(
            record,
            "500",
            " ",
            " ",
            (("a", "Text-first reference covering all 37 Bopomofo symbols."),),
        )
        _marc_data(
            record,
            "506",
            "0",
            " ",
            (("a", "Open access; no account required."),),
        )
        _marc_data(record, "520", " ", " ", (("a", copy["summary"]),))
        _marc_data(
            record,
            "538",
            " ",
            " ",
            (
                (
                    "a",
                    "EPUB 3 reading system with Unicode Bopomofo font support.",
                ),
            ),
        )
        _marc_data(
            record,
            "540",
            " ",
            " ",
            (
                ("a", "Creative Commons Attribution 4.0 International."),
                ("u", LICENSE),
            ),
        )
        _marc_data(record, "546", " ", " ", (("a", copy["language_note"]),))
        for subject in (
            "Bopomofo",
            "Chinese language--Phonetics",
            "Chinese language--Study and teaching",
        ):
            _marc_data(record, "650", " ", "4", (("a", subject),))
        _marc_data(
            record,
            "655",
            " ",
            "7",
            (("a", "Electronic books."), ("2", "lcgft")),
        )
        _marc_data(
            record,
            "710",
            "2",
            " ",
            (("a", CREATOR), ("e", "author.")),
        )
        _marc_data(
            record,
            "856",
            "4",
            "0",
            (
                ("3", copy["download_label"]),
                ("u", epub["contentUrl"]),
                ("q", "application/epub+zip"),
                ("z", f"SHA-256: {epub['sha256']}"),
            ),
        )
        _marc_data(
            record,
            "856",
            "4",
            "2",
            (
                ("3", "Description and catalog record downloads"),
                ("u", LANDING_URL),
            ),
        )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _mods(name: str) -> str:
    return f"{{{MODS_NS}}}{name}"


def _mods_text(
    parent: ET.Element,
    name: str,
    value: str,
    attributes: dict[str, str] | None = None,
) -> ET.Element:
    element = ET.SubElement(parent, _mods(name), attributes or {})
    element.text = value
    return element


def render_mods(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    ET.register_namespace("", MODS_NS)
    ET.register_namespace("xlink", XLINK_NS)
    ET.register_namespace("xsi", XSI_NS)
    root = ET.Element(
        _mods("modsCollection"),
        {f"{{{XSI_NS}}}schemaLocation": f"{MODS_NS} {MODS_SCHEMA}"},
    )
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        epub = editions[locale]
        record = ET.SubElement(
            root,
            _mods("mods"),
            {"version": "3.8", "ID": copy["record_id"]},
        )
        title_info = ET.SubElement(
            record,
            _mods("titleInfo"),
            {f"{{{XML_NS}}}lang": copy["lang"]},
        )
        _mods_text(title_info, "title", copy["title"])
        _mods_text(title_info, "subTitle", copy["subtitle"])
        alternate = ET.SubElement(
            record,
            _mods("titleInfo"),
            {"type": "alternative"},
        )
        _mods_text(alternate, "title", copy["alternate"])
        name = ET.SubElement(record, _mods("name"), {"type": "corporate"})
        _mods_text(name, "namePart", CREATOR)
        role = ET.SubElement(name, _mods("role"))
        _mods_text(
            role,
            "roleTerm",
            "aut",
            {"type": "code", "authority": "marcrelator"},
        )
        _mods_text(record, "typeOfResource", "text")
        _mods_text(record, "genre", "reference works", {"authority": "local"})
        origin = ET.SubElement(
            record,
            _mods("originInfo"),
            {"eventType": "publication"},
        )
        place = ET.SubElement(origin, _mods("place"))
        _mods_text(
            place,
            "placeTerm",
            "[Place of publication not identified]",
            {"type": "text"},
        )
        _mods_text(origin, "publisher", CREATOR)
        _mods_text(
            origin,
            "dateIssued",
            source["datePublished"][:4],
            {"encoding": "w3cdtf", "keyDate": "yes"},
        )
        _mods_text(origin, "issuance", "monographic")
        language = ET.SubElement(record, _mods("language"))
        _mods_text(
            language,
            "languageTerm",
            copy["marc_lang"],
            {"type": "code", "authority": "iso639-2b"},
        )
        _mods_text(
            language,
            "languageTerm",
            "English" if locale == "en" else "Chinese",
            {"type": "text"},
        )
        physical = ET.SubElement(record, _mods("physicalDescription"))
        _mods_text(physical, "form", "electronic", {"authority": "marcform"})
        _mods_text(physical, "internetMediaType", "application/epub+zip")
        _mods_text(physical, "extent", copy["extent"])
        _mods_text(physical, "digitalOrigin", "born digital")
        _mods_text(record, "abstract", copy["summary"])
        _mods_text(record, "note", copy["language_note"], {"type": "language"})
        for subject_text in (
            "Bopomofo",
            "Chinese language--Phonetics",
            "Chinese language--Study and teaching",
        ):
            subject = ET.SubElement(record, _mods("subject"))
            _mods_text(subject, "topic", subject_text)
        _mods_text(record, "identifier", copy["local_id"], {"type": "local"})
        _mods_text(record, "identifier", epub["sha256"], {"type": "sha256"})
        location = ET.SubElement(record, _mods("location"))
        _mods_text(
            location,
            "url",
            epub["contentUrl"],
            {"displayLabel": copy["download_label"]},
        )
        _mods_text(
            record,
            "accessCondition",
            "Creative Commons Attribution 4.0 International.",
            {
                "type": "use and reproduction",
                f"{{{XLINK_NS}}}href": LICENSE,
            },
        )
        record_info = ET.SubElement(record, _mods("recordInfo"))
        _mods_text(
            record_info,
            "recordContentSource",
            "LUMI",
            {"authority": "local"},
        )
        _mods_text(
            record_info,
            "recordCreationDate",
            source["datePublished"],
            {"encoding": "w3cdtf"},
        )
        _mods_text(
            record_info,
            "recordChangeDate",
            modified,
            {"encoding": "iso8601"},
        )
        _mods_text(
            record_info,
            "recordIdentifier",
            copy["record_id"],
            {"source": "LUMI"},
        )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _node(node_id: str, node_type: str, **properties) -> dict:
    return {"@id": node_id, "@type": node_type, **properties}


def _literal(value: str, language: str | None = None) -> dict:
    literal = {"@value": value}
    if language:
        literal["@language"] = language
    return literal


def _iri(value: str) -> dict:
    return {"@id": value}


def bibframe_graph(
    source: dict,
    editions: dict[str, dict],
) -> dict:
    genre = f"{LANDING_URL}#genre-reference"
    topics = {
        "bopomofo": f"{LANDING_URL}#topic-bopomofo",
        "phonetics": f"{LANDING_URL}#topic-chinese-phonetics",
        "teaching": f"{LANDING_URL}#topic-chinese-language-teaching",
    }
    graph = [
        _node(CREATOR_URL, "bf:Organization", **{"rdfs:label": CREATOR}),
        _node(
            genre,
            "bf:GenreForm",
            **{
                "rdfs:label": [
                    _literal("Reference works", "en"),
                    _literal("參考工具書", "zh-Hant"),
                ]
            },
        ),
        _node(
            topics["bopomofo"],
            "bf:Topic",
            **{
                "rdfs:label": [
                    _literal("Bopomofo", "en"),
                    _literal("注音符號", "zh-Hant"),
                ]
            },
        ),
        _node(
            topics["phonetics"],
            "bf:Topic",
            **{
                "rdfs:label": [
                    _literal("Chinese language--Phonetics", "en"),
                    _literal("漢語語音", "zh-Hant"),
                ]
            },
        ),
        _node(
            topics["teaching"],
            "bf:Topic",
            **{
                "rdfs:label": [
                    _literal("Chinese language--Study and teaching", "en"),
                    _literal("漢語教學", "zh-Hant"),
                ]
            },
        ),
    ]
    language_uris = {
        "en": "http://id.loc.gov/vocabulary/languages/eng",
        "zh-Hant": "http://id.loc.gov/vocabulary/languages/chi",
    }
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        epub = editions[locale]
        suffix = "en" if locale == "en" else "zh-hant"
        work = f"{LANDING_URL}#work-{suffix}"
        instance = f"{LANDING_URL}#instance-{suffix}"
        title = f"{LANDING_URL}#title-{suffix}"
        contribution = f"{LANDING_URL}#contribution-{suffix}"
        identifier = f"{LANDING_URL}#identifier-{suffix}"
        publication = f"{LANDING_URL}#publication-{suffix}"
        policy = f"{LANDING_URL}#use-policy-{suffix}"
        extent = f"{LANDING_URL}#extent-{suffix}"
        note = f"{LANDING_URL}#fixity-note-{suffix}"
        graph.extend(
            [
                _node(
                    work,
                    "bf:Work",
                    **{
                        "rdfs:label": _literal(copy["title"], copy["lang"]),
                        "bf:title": _iri(title),
                        "bf:language": _iri(language_uris[locale]),
                        "bf:content": _iri(
                            "http://id.loc.gov/vocabulary/contentTypes/txt"
                        ),
                        "bf:contribution": _iri(contribution),
                        "bf:subject": [_iri(value) for value in topics.values()],
                        "bf:genreForm": _iri(genre),
                        "bf:hasInstance": _iri(instance),
                    },
                ),
                _node(
                    instance,
                    "bf:Instance",
                    **{
                        "rdfs:label": _literal(copy["title"], copy["lang"]),
                        "bf:title": _iri(title),
                        "bf:instanceOf": _iri(work),
                        "bf:media": _iri(
                            "http://id.loc.gov/vocabulary/mediaTypes/c"
                        ),
                        "bf:carrier": _iri(
                            "http://id.loc.gov/vocabulary/carriers/cr"
                        ),
                        "bf:identifiedBy": _iri(identifier),
                        "bf:provisionActivity": _iri(publication),
                        "bf:electronicLocator": _iri(epub["contentUrl"]),
                        "bf:usageAndAccessPolicy": _iri(policy),
                        "bf:extent": _iri(extent),
                        "bf:note": _iri(note),
                    },
                ),
                _node(
                    title,
                    "bf:Title",
                    **{"bf:mainTitle": _literal(copy["title"], copy["lang"])},
                ),
                _node(
                    contribution,
                    "bf:PrimaryContribution",
                    **{
                        "bf:agent": _iri(CREATOR_URL),
                        "bf:role": _iri(
                            "http://id.loc.gov/vocabulary/relators/aut"
                        ),
                    },
                ),
                _node(
                    identifier,
                    "bf:Local",
                    **{"rdf:value": copy["local_id"]},
                ),
                _node(
                    publication,
                    "bf:Publication",
                    **{
                        "bf:agent": _iri(CREATOR_URL),
                        "bf:date": source["datePublished"][:4],
                    },
                ),
                _node(
                    policy,
                    "bf:UsePolicy",
                    **{
                        "rdfs:label": "CC BY 4.0",
                        "rdf:value": _iri(LICENSE),
                    },
                ),
                _node(
                    extent,
                    "bf:Extent",
                    **{"rdfs:label": _literal(copy["extent"], copy["lang"])},
                ),
                _node(
                    note,
                    "bf:Note",
                    **{
                        "rdfs:label": _literal(
                            f"EPUB SHA-256: {epub['sha256']}",
                            copy["lang"],
                        )
                    },
                ),
            ]
        )
    return {
        "@context": {
            "bf": BF,
            "rdf": RDF,
            "rdfs": RDFS,
        },
        "@graph": graph,
    }


def render_bibframe_jsonld(source: dict, editions: dict[str, dict]) -> bytes:
    return (
        json.dumps(
            bibframe_graph(source, editions),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _ttl_literal(value: str, language: str | None = None) -> str:
    rendered = json.dumps(value, ensure_ascii=False)
    return f"{rendered}@{language}" if language else rendered


def render_bibframe_turtle(source: dict, editions: dict[str, dict]) -> bytes:
    genre = f"{LANDING_URL}#genre-reference"
    topics = {
        "bopomofo": f"{LANDING_URL}#topic-bopomofo",
        "phonetics": f"{LANDING_URL}#topic-chinese-phonetics",
        "teaching": f"{LANDING_URL}#topic-chinese-language-teaching",
    }
    lines = [
        f"@prefix bf: <{BF}> .",
        f"@prefix rdf: <{RDF}> .",
        f"@prefix rdfs: <{RDFS}> .",
        "",
        f"<{CREATOR_URL}> a bf:Organization ;",
        f"  rdfs:label {_ttl_literal(CREATOR)} .",
        "",
        f"<{genre}> a bf:GenreForm ;",
        f"  rdfs:label {_ttl_literal('Reference works', 'en')},",
        f"    {_ttl_literal('參考工具書', 'zh-Hant')} .",
        "",
        f"<{topics['bopomofo']}> a bf:Topic ;",
        f"  rdfs:label {_ttl_literal('Bopomofo', 'en')},",
        f"    {_ttl_literal('注音符號', 'zh-Hant')} .",
        "",
        f"<{topics['phonetics']}> a bf:Topic ;",
        f"  rdfs:label {_ttl_literal('Chinese language--Phonetics', 'en')},",
        f"    {_ttl_literal('漢語語音', 'zh-Hant')} .",
        "",
        f"<{topics['teaching']}> a bf:Topic ;",
        (
            "  rdfs:label "
            f"{_ttl_literal('Chinese language--Study and teaching', 'en')},"
        ),
        f"    {_ttl_literal('漢語教學', 'zh-Hant')} .",
        "",
    ]
    language_uris = {
        "en": "http://id.loc.gov/vocabulary/languages/eng",
        "zh-Hant": "http://id.loc.gov/vocabulary/languages/chi",
    }
    subject_objects = ", ".join(f"<{value}>" for value in topics.values())
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        epub = editions[locale]
        suffix = "en" if locale == "en" else "zh-hant"
        base = f"{LANDING_URL}#"
        work = f"{base}work-{suffix}"
        instance = f"{base}instance-{suffix}"
        title = f"{base}title-{suffix}"
        contribution = f"{base}contribution-{suffix}"
        identifier = f"{base}identifier-{suffix}"
        publication = f"{base}publication-{suffix}"
        policy = f"{base}use-policy-{suffix}"
        extent = f"{base}extent-{suffix}"
        note = f"{base}fixity-note-{suffix}"
        lines.extend(
            [
                f"<{work}> a bf:Work ;",
                f"  rdfs:label {_ttl_literal(copy['title'], copy['lang'])} ;",
                f"  bf:title <{title}> ;",
                f"  bf:language <{language_uris[locale]}> ;",
                "  bf:content <http://id.loc.gov/vocabulary/contentTypes/txt> ;",
                f"  bf:contribution <{contribution}> ;",
                f"  bf:subject {subject_objects} ;",
                f"  bf:genreForm <{genre}> ;",
                f"  bf:hasInstance <{instance}> .",
                "",
                f"<{instance}> a bf:Instance ;",
                f"  rdfs:label {_ttl_literal(copy['title'], copy['lang'])} ;",
                f"  bf:title <{title}> ;",
                f"  bf:instanceOf <{work}> ;",
                "  bf:media <http://id.loc.gov/vocabulary/mediaTypes/c> ;",
                "  bf:carrier <http://id.loc.gov/vocabulary/carriers/cr> ;",
                f"  bf:identifiedBy <{identifier}> ;",
                f"  bf:provisionActivity <{publication}> ;",
                f"  bf:electronicLocator <{epub['contentUrl']}> ;",
                f"  bf:usageAndAccessPolicy <{policy}> ;",
                f"  bf:extent <{extent}> ;",
                f"  bf:note <{note}> .",
                "",
                f"<{title}> a bf:Title ;",
                (
                    "  bf:mainTitle "
                    f"{_ttl_literal(copy['title'], copy['lang'])} ."
                ),
                "",
                f"<{contribution}> a bf:PrimaryContribution ;",
                f"  bf:agent <{CREATOR_URL}> ;",
                "  bf:role <http://id.loc.gov/vocabulary/relators/aut> .",
                "",
                f"<{identifier}> a bf:Local ;",
                f"  rdf:value {_ttl_literal(copy['local_id'])} .",
                "",
                f"<{publication}> a bf:Publication ;",
                f"  bf:agent <{CREATOR_URL}> ;",
                f"  bf:date {_ttl_literal(source['datePublished'][:4])} .",
                "",
                f"<{policy}> a bf:UsePolicy ;",
                f"  rdfs:label {_ttl_literal('CC BY 4.0')} ;",
                f"  rdf:value <{LICENSE}> .",
                "",
                f"<{extent}> a bf:Extent ;",
                f"  rdfs:label {_ttl_literal(copy['extent'], copy['lang'])} .",
                "",
                f"<{note}> a bf:Note ;",
                (
                    "  rdfs:label "
                    f"{_ttl_literal(f'EPUB SHA-256: {epub['sha256']}', copy['lang'])} ."
                ),
                "",
            ]
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _artifact(
    filename: str,
    content: bytes,
    encoding_format: str | None = None,
) -> dict:
    return {
        "filename": filename,
        "url": f"{PACKAGE_URL}/{filename}",
        "encodingFormat": encoding_format or FORMATS[filename][1],
        "size": len(content),
        "sha256": _sha256(content),
    }


def render_bundle(
    primary: dict[str, bytes],
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    checksums = "".join(
        f"{_sha256(primary[name])}  {name}\n" for name in PRIMARY_FILENAMES
    )
    readme = (
        "Bopomofo 37-Symbol EPUB Library Catalog Records\n"
        "================================================\n\n"
        "This bundle contains two candidate bibliographic records, one for the "
        "English EPUB edition and one for the Traditional Chinese edition.\n\n"
        "Formats:\n"
        f"- {MARC_FILENAME}: MARC 21 XML (MARCXML)\n"
        f"- {MODS_FILENAME}: MODS 3.8 XML\n"
        f"- {BIBFRAME_JSONLD_FILENAME}: BIBFRAME 2.0 JSON-LD\n"
        f"- {BIBFRAME_TURTLE_FILENAME}: BIBFRAME 2.0 Turtle\n"
        "- checksums.sha256: SHA-256 for the four catalog files\n\n"
        f"Source EPUB page: {EPUB_LANDING_URL}\n"
        f"Source metadata: {SOURCE_METADATA_URL}\n"
        f"Source modified: {source['dateModified']}\n"
        f"Catalog modified: {modified}\n"
        f"English EPUB SHA-256: {editions['en']['sha256']}\n"
        f"Traditional Chinese EPUB SHA-256: {editions['zh-Hant']['sha256']}\n"
        f"License: {LICENSE}\n\n"
        "Review local descriptive cataloging, subjects, classification, access "
        "and holdings policies before import. These local records do not assign "
        "an ISBN, LCCN or OCLC control number.\n"
    )
    entries = {
        **primary,
        "README.txt": readme.encode("utf-8"),
        "checksums.sha256": checksums.encode("ascii"),
    }
    instant = _parse_timestamp(modified)
    zip_date = (
        max(1980, instant.year),
        instant.month,
        instant.day,
        instant.hour,
        instant.minute,
        instant.second,
    )
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for filename in sorted(entries):
            info = zipfile.ZipInfo(filename, zip_date)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[filename])
    return output.getvalue()


def render_metadata(
    source: dict,
    editions: dict[str, dict],
    artifacts: list[dict],
    modified: str,
) -> bytes:
    metadata = {
        "@context": "https://schema.org",
        "@type": ["Dataset", "CreativeWork"],
        "@id": f"{LANDING_URL}#catalog-records",
        "name": "Bopomofo EPUB library catalog records",
        "alternateName": "注音 EPUB 圖書館書目紀錄",
        "description": (
            "Two bilingual-ready bibliographic records for the open 37-symbol "
            "Bopomofo EPUB, supplied as MARCXML, MODS 3.8 and BIBFRAME 2.0."
        ),
        "url": LANDING_URL,
        "identifier": "LUMI-ZHUYIN-EPUB-CATALOG-2026",
        "version": VERSION,
        "datePublished": source["datePublished"],
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant"],
        "license": LICENSE,
        "isAccessibleForFree": True,
        "creator": {
            "@type": "Organization",
            "name": CREATOR,
            "url": SITE,
        },
        "isBasedOn": {
            "@type": "Book",
            "url": EPUB_LANDING_URL,
            "dateModified": source["dateModified"],
            "encoding": [
                {
                    "@type": "MediaObject",
                    "contentUrl": editions[locale]["contentUrl"],
                    "encodingFormat": "application/epub+zip",
                    "contentSize": f"{editions[locale]['size']} bytes",
                    "sha256": editions[locale]["sha256"],
                    "inLanguage": locale,
                }
                for locale in ("en", "zh-Hant")
            ],
        },
        "conformsTo": [
            MARC_SCHEMA,
            MODS_SCHEMA,
            BIBFRAME_VOCABULARY,
            BIBFRAME_MODEL,
        ],
        "numberOfItems": 2,
        "keywords": [
            "Bopomofo",
            "Zhuyin",
            "MARCXML",
            "MODS 3.8",
            "BIBFRAME 2.0",
            "library catalog records",
            "school library",
        ],
        "distribution": [
            {
                "@type": "DataDownload",
                "name": FORMATS[item["filename"]][0],
                "encodingFormat": item["encodingFormat"],
                "contentUrl": item["url"],
                "contentSize": f"{item['size']} bytes",
                "sha256": item["sha256"],
            }
            for item in artifacts
        ],
        "includedInDataCatalog": {
            "@type": "DataCatalog",
            "name": "Lumi Apps Open Data",
            "url": f"{SITE}/data/",
        },
    }
    return (
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def render_package(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> dict[str, bytes]:
    primary = {
        MARC_FILENAME: render_marcxml(source, editions, modified),
        MODS_FILENAME: render_mods(source, editions, modified),
        BIBFRAME_JSONLD_FILENAME: render_bibframe_jsonld(source, editions),
        BIBFRAME_TURTLE_FILENAME: render_bibframe_turtle(source, editions),
    }
    bundle = render_bundle(primary, source, editions, modified)
    artifacts = [
        _artifact(BUNDLE_FILENAME, bundle),
        *[_artifact(filename, primary[filename]) for filename in PRIMARY_FILENAMES],
    ]
    metadata = render_metadata(source, editions, artifacts, modified)
    return {
        **primary,
        BUNDLE_FILENAME: bundle,
        METADATA_FILENAME: metadata,
    }


def _prior_modified(pages: Path) -> str | None:
    path = pages / PACKAGE_PATH / METADATA_FILENAME
    if not path.exists():
        return None
    try:
        modified = json.loads(path.read_text(encoding="utf-8"))["dateModified"]
        _parse_timestamp(modified)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
    return modified


def _package_matches(pages: Path, package: dict[str, bytes]) -> bool:
    return all(
        (pages / PACKAGE_PATH / filename).exists()
        and (pages / PACKAGE_PATH / filename).read_bytes() == content
        for filename, content in package.items()
    )


def _catalog_schema(
    locale: str,
    package_info: dict[str, dict],
    catalog_modified: str,
    page_modified: str,
    app_public: bool,
) -> dict:
    copy = COPY[locale]
    canonical = LANDING_URL if locale == "en" else ZH_LANDING_URL
    graph = [
        {
            "@type": "WebPage",
            "@id": canonical,
            "name": copy["title"],
            "description": copy["description"],
            "url": canonical,
            "inLanguage": copy["lang"],
            "dateModified": page_modified,
            "mainEntity": {"@id": f"{LANDING_URL}#catalog-records"},
        },
        {
            "@type": ["Dataset", "CreativeWork"],
            "@id": f"{LANDING_URL}#catalog-records",
            "name": "Bopomofo EPUB library catalog records",
            "alternateName": "注音 EPUB 圖書館書目紀錄",
            "description": copy["description"],
            "url": LANDING_URL,
            "version": VERSION,
            "datePublished": INITIAL_DATE,
            "dateModified": catalog_modified,
            "inLanguage": ["en", "zh-Hant"],
            "license": LICENSE,
            "isAccessibleForFree": True,
            "isBasedOn": EPUB_LANDING_URL,
            "conformsTo": [
                MARC_SCHEMA,
                MODS_SCHEMA,
                BIBFRAME_VOCABULARY,
                BIBFRAME_MODEL,
            ],
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": FORMATS[filename][0],
                    "encodingFormat": FORMATS[filename][1],
                    "contentUrl": package_info[filename]["url"],
                    "contentSize": f"{package_info[filename]['size']} bytes",
                    "sha256": package_info[filename]["sha256"],
                }
                for filename in DOWNLOAD_FILENAMES
            ],
        },
    ]
    if app_public:
        graph[1]["subjectOf"] = {
            "@type": "SoftwareApplication",
            "name": APP_NAME,
            "applicationCategory": "EducationApplication",
            "operatingSystem": "iOS",
            "url": appstore_url(
                APP_KEY,
                f"iag_bopomofo_library_catalog_{locale.lower()}",
            ),
        }
    return {"@context": "https://schema.org", "@graph": graph}


def render_landing(
    locale: str,
    package_info: dict[str, dict],
    catalog_modified: str,
    page_modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = LANDING_URL if locale == "en" else ZH_LANDING_URL
    other = ZH_LANDING_URL if locale == "en" else LANDING_URL
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in copy["badges"])
    downloads = []
    for filename in DOWNLOAD_FILENAMES:
        item = package_info[filename]
        name, encoding_format = FORMATS[filename]
        primary = " primary" if filename == BUNDLE_FILENAME else ""
        downloads.append(
            f'<a class="download{primary}" href="{html.escape(item["url"], quote=True)}" '
            f'download><strong>{html.escape(name)}</strong>'
            f'<span>{html.escape(filename)}</span>'
            f'<small>{html.escape(encoding_format)} · {item["size"]:,} bytes · '
            f'SHA-256 {item["sha256"][:16]}…</small></a>'
        )
    format_cards = "".join(
        f"<article><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></article>"
        for title, text in copy["format_items"]
    )
    specs = "".join(
        f'<a href="{url}" rel="noopener">{html.escape(label)} &rarr;</a>'
        for label, url in (
            ("MARCXML", MARC_SCHEMA),
            ("MODS 3.8", MODS_SCHEMA),
            ("BIBFRAME vocabulary", BIBFRAME_VOCABULARY),
            ("BIBFRAME model", BIBFRAME_MODEL),
        )
    )
    app_block = ""
    if app_public:
        app_block = (
            '<section class="app"><p class="kicker">{title}</p><p>{text}</p>'
            '<a href="{url}" rel="nofollow noopener">{cta} &rarr;</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY,
                    f"iag_bopomofo_library_catalog_{locale.lower()}",
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _catalog_schema(
            locale,
            package_info,
            catalog_modified,
            page_modified,
            app_public,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(page_modified, quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="describedby" type="application/ld+json" href="{PACKAGE_URL}/{METADATA_FILENAME}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#142034;--sub:#5b677a;--line:#d9e2ee;--brand:#315fa8;--deep:#16345e;--bg:#f3f6fa;--paper:#fff;--soft:#eaf2fc}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.68 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}.wrap{{max-width:1040px;margin:auto;padding:24px 20px 72px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding:56px 0 30px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(33px,7vw,58px);line-height:1.07;letter-spacing:-.038em;margin:10px 0 17px;max-width:900px}}h2{{font-size:clamp(23px,4vw,32px);line-height:1.2;margin:0 0 10px}}h3{{font-size:18px;margin:0 0 7px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:820px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:730;white-space:nowrap}}section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(19px,4vw,28px);box-shadow:0 14px 35px rgba(26,49,82,.055)}}.downloads,.grid,.specs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:18px}}.download{{display:flex;min-width:0;flex-direction:column;gap:4px;border:1px solid var(--line);border-radius:15px;padding:16px;background:#fbfcfe;text-decoration:none;color:var(--ink)}}.download.primary{{grid-column:1/-1;background:var(--deep);border-color:var(--deep);color:#fff}}.download strong{{font-size:17px}}.download span,.download small{{overflow-wrap:anywhere;color:var(--sub)}}.download.primary span,.download.primary small{{color:#dbe9fb}}.grid article{{background:#fff;border:1px solid var(--line);border-radius:17px;padding:19px}}.grid p{{margin:0}}.specs a{{background:var(--soft);border-radius:13px;padding:13px 15px;text-decoration:none;font-weight:780;white-space:nowrap}}.notice{{border-left:4px solid #d79a2b}}.app a{{font-weight:820;text-decoration:none;white-space:nowrap}}footer{{margin-top:42px;padding-top:21px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}@media(max-width:520px){{.wrap{{padding-left:16px;padding-right:16px}}.panel,.app{{border-radius:18px}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{''.join(downloads)}</div><p><a href="{EPUB_LANDING_URL}">{html.escape(copy['source'])} &rarr;</a></p></section>
<section><h2>{html.escape(copy['formats'])}</h2><div class="grid">{format_cards}</div></section>
<section class="panel"><h2>{html.escape(copy['verification'])}</h2><p>{html.escape(copy['verification_text'])}</p><div class="specs">{specs}<a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])} &rarr;</a></div></section>
<section class="panel notice"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></section>
{app_block}
<footer>{html.escape(copy['footer'])}</footer>
</main>
</body>
</html>
"""


def _update_data_index(
    pages: Path,
    package_info: dict[str, dict],
    modified: str,
) -> None:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index is missing: {index}")
    content = index.read_text(encoding="utf-8")
    block = (
        f'{CARD_START}<a class="item" href="{LANDING_URL}"><div>'
        '<span class="tag">MARCXML · MODS 3.8 · BIBFRAME 2.0</span>'
        "<h2>Bopomofo EPUB library catalog records</h2>"
        "<p>Two language-edition records with official-schema validation, "
        "linked data and SHA-256 fixity.</p></div>"
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
    match = schema_pattern.search(updated)
    if match:
        try:
            catalog = json.loads(match.group(2))
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
                    "@type": ["Dataset", "CreativeWork"],
                    "name": "Bopomofo EPUB library catalog records",
                    "description": COPY["en"]["description"],
                    "url": LANDING_URL,
                    "dateModified": modified,
                    "license": LICENSE,
                    "conformsTo": [
                        MARC_SCHEMA,
                        MODS_SCHEMA,
                        BIBFRAME_VOCABULARY,
                    ],
                    "distribution": [
                        {
                            "@type": "DataDownload",
                            "name": FORMATS[filename][0],
                            "encodingFormat": FORMATS[filename][1],
                            "contentUrl": package_info[filename]["url"],
                        }
                        for filename in (
                            BUNDLE_FILENAME,
                            *PRIMARY_FILENAMES,
                        )
                    ],
                }
            )
            catalog["dataset"] = datasets
            rendered = json.dumps(catalog, ensure_ascii=False)
            updated = (
                updated[: match.start()]
                + match.group(1)
                + rendered
                + match.group(3)
                + updated[match.end() :]
            )
    write_text_if_changed(index, updated)


def render_sitemap(
    package_info: dict[str, dict],
    catalog_modified: str,
    page_modified: dict[str, str],
) -> str:
    entries = [
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        *[
            (package_info[filename]["url"], catalog_modified[:10])
            for filename in DOWNLOAD_FILENAMES
        ],
    ]
    rows = "\n".join(
        f"  <url><loc>{xml_escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n"
    )


def validate_raw_package(package: dict[str, bytes], editions: dict[str, dict]) -> None:
    combined = b"\n".join(package.values())
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
        b"analytics",
        b"tracking",
        b"learner profile",
    ):
        if forbidden in combined:
            raise ValueError(
                "Library catalog package must remain app-independent: "
                + forbidden.decode("utf-8")
            )
    marc = ET.fromstring(package[MARC_FILENAME])
    mods = ET.fromstring(package[MODS_FILENAME])
    if len(marc.findall(_marc("record"))) != 2:
        raise ValueError("MARCXML must contain two bibliographic records")
    if len(mods.findall(_mods("mods"))) != 2:
        raise ValueError("MODS must contain two records")
    for record in marc.findall(_marc("record")):
        leader = record.findtext(_marc("leader"), "")
        fixed = next(
            (
                item.text or ""
                for item in record.findall(_marc("controlfield"))
                if item.get("tag") == "008"
            ),
            "",
        )
        if len(leader) != 24 or len(fixed) != 40:
            raise ValueError("MARC fixed fields have invalid lengths")
    json.loads(package[BIBFRAME_JSONLD_FILENAME])
    turtle = package[BIBFRAME_TURTLE_FILENAME].decode("utf-8")
    for term in ("bf:Work", "bf:Instance", "bf:instanceOf", "bf:hasInstance"):
        if term not in turtle:
            raise ValueError(f"BIBFRAME Turtle is missing {term}")
    for edition in editions.values():
        if edition["sha256"].encode("ascii") not in combined:
            raise ValueError("Source EPUB SHA-256 is missing from catalog records")
    with zipfile.ZipFile(io.BytesIO(package[BUNDLE_FILENAME])) as archive:
        expected = {*PRIMARY_FILENAMES, "README.txt", "checksums.sha256"}
        if set(archive.namelist()) != expected:
            raise ValueError("Catalog ZIP does not contain the expected files")
        for filename in PRIMARY_FILENAMES:
            if archive.read(filename) != package[filename]:
                raise ValueError(f"Catalog ZIP content mismatch: {filename}")


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    source, editions = _load_source(pages)
    source_modified = source["dateModified"]
    prior = _prior_modified(pages)
    base_modified = (
        _max_timestamp(prior, source_modified) if prior else source_modified
    )
    package = render_package(source, editions, base_modified)
    if prior and not _package_matches(pages, package):
        target_modified = (
            source_modified
            if _parse_timestamp(source_modified) > _parse_timestamp(prior)
            else _next_timestamp(prior)
        )
        package = render_package(source, editions, target_modified)
    else:
        target_modified = base_modified
    validate_raw_package(package, editions)

    package_dir = pages / PACKAGE_PATH
    for filename, content in package.items():
        _write_bytes_if_changed(package_dir / filename, content)
    package_info = {
        filename: _artifact(filename, content)
        for filename, content in package.items()
    }

    live = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / LANDING_PATH),
        ("zh-Hant", pages / ZH_LANDING_PATH),
    ):
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_landing(
                locale,
                package_info,
                target_modified,
                modified,
                live,
            ),
            INITIAL_DATE,
            TODAY,
        )
    _update_data_index(pages, package_info, target_modified)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(package_info, target_modified, page_modified),
    )
    return [
        *(str(PACKAGE_PATH / filename) for filename in DOWNLOAD_FILENAMES),
        str(LANDING_PATH),
        str(ZH_LANDING_PATH),
        str(SITEMAP_PATH),
    ]


if __name__ == "__main__":
    built = build()
    print(f"Built {len(built)} library catalog resources")
