#!/usr/bin/env python3
"""Build a local-only Google Education Q&A canary for Bopomofo flashcards."""

from __future__ import annotations

import hashlib
import html
import json
import re

import bopomofo_flashcards as base
from official_locales import OFFICIAL_LOCALES
from zhuyin_croissant_dataset import (
    SOURCE_DATASET,
    records,
    validate_records,
)


EXPERIMENT_SCHEMA = "education_qa_experiment/1"
EXPERIMENT_ID = "bopomofo-flashcards-20260829"
CONTROL_COMMIT = "6b4745d040e43a5bb0c5c8e4c35404f33101bddd"
CANARY_LOCALES = ("en", "pt-BR", "es-MX", "vi")
FLASHCARD_ORDERS = (
    1,
    2,
    3,
    4,
    5,
    6,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
)
HEAD_START = "<!-- education-qa-canary:head:start -->"
HEAD_END = "<!-- education-qa-canary:head:end -->"
BODY_START = "<!-- education-qa-canary:body:start -->"
BODY_END = "<!-- education-qa-canary:body:end -->"

GOOGLE_EDUCATION_QA_DOC = (
    "https://developers.google.com/search/docs/appearance/"
    "structured-data/education-qa"
)
GOOGLE_QAPAGE_DOC = (
    "https://developers.google.com/search/docs/appearance/"
    "structured-data/qapage"
)
GOOGLE_SPAM_DOC = (
    "https://developers.google.com/search/docs/essentials/spam-policies"
)
QTI_PAGE = f"{base.SITE}/data/zhuyin-bopomofo-lms-question-bank.html"
OER_PAGE = (
    f"{base.SITE}/data/zhuyin-bopomofo-oer-repository-metadata.html"
)

CANONICAL_ROWS = tuple(records())
validate_records(list(CANONICAL_ROWS))
ROWS_BY_ORDER = {row["order"]: row for row in CANONICAL_ROWS}
if set(FLASHCARD_ORDERS) - set(ROWS_BY_ORDER):
    raise RuntimeError("Education Q&A orders are outside the canonical dataset")

SOURCE_PROVENANCE = (
    {
        "url": SOURCE_DATASET,
        "role": "single canonical 37-symbol source data",
    },
    {
        "url": base.MOE_HANDBOOK,
        "role": "Taiwan Ministry of Education Bopomofo reference",
    },
    {
        "url": base.UNICODE_CHART_PDF,
        "role": "Unicode code point chart",
    },
    {
        "url": QTI_PAGE,
        "role": "existing deterministic QTI/OER interoperability surface",
    },
    {
        "url": OER_PAGE,
        "role": "existing OER provenance and fixity surface",
    },
)


EDUCATION_COPY = {
    "en": {
        "heading": "18 fixed Bopomofo recognition flashcards",
        "intro": (
            "Every question and answer is visible immediately. The cards use "
            "fixed symbol, category, and Unicode facts from one canonical "
            "37-symbol dataset; no answer is generated from a guess."
        ),
        "question": (
            "Which Bopomofo symbol in the “{category}” group is encoded at "
            "{unicode}?"
        ),
        "categories": {
            "initial": "initial",
            "medial": "medial",
            "final": "final",
        },
        "answer": "Answer",
        "record_source": "Source row {order}",
        "boundary": (
            "The Unicode code point identifies the character. Unicode's English "
            "character name is an identifier, not a pronunciation lesson; use "
            "the linked Taiwan Ministry of Education reference for pronunciation."
        ),
        "sources_heading": "Sources and traceability",
        "sources_intro": (
            "Each answer is joined directly to its canonical source row. The "
            "QTI and OER links expose the same source lineage in reusable formats."
        ),
        "source_labels": (
            "Canonical 37-symbol dataset",
            "Taiwan Ministry of Education Bopomofo reference",
            "Unicode Bopomofo chart",
            "QTI 2.1 question-bank source",
            "OER metadata and fixity source",
        ),
        "first_party": (
            "First-party disclosure: iOS App Guide and the optional Lumi "
            "Bopomofo app are both published by Lumi Apps. These flashcards and "
            "the printable generator work without the app."
        ),
        "about": "Bopomofo symbol recognition",
    },
    "pt-BR": {
        "heading": "18 cartões fixos para reconhecer símbolos Bopomofo",
        "intro": (
            "Cada pergunta e resposta fica visível imediatamente. Os cartões "
            "usam fatos fixos de símbolo, categoria e Unicode vindos de um único "
            "conjunto canônico com 37 símbolos; nenhuma resposta é adivinhada."
        ),
        "question": (
            "Qual símbolo Bopomofo do grupo “{category}” está codificado em "
            "{unicode}?"
        ),
        "categories": {
            "initial": "inicial",
            "medial": "medial",
            "final": "final",
        },
        "answer": "Resposta",
        "record_source": "Linha da fonte {order}",
        "boundary": (
            "O ponto de código Unicode identifica o caractere. O nome do "
            "caractere em inglês no Unicode é um identificador, não uma aula de "
            "pronúncia; use a referência do Ministério da Educação de Taiwan."
        ),
        "sources_heading": "Fontes e rastreabilidade",
        "sources_intro": (
            "Cada resposta aponta diretamente para sua linha na fonte canônica. "
            "Os links QTI e OER mostram a mesma origem em formatos reutilizáveis."
        ),
        "source_labels": (
            "Conjunto canônico com 37 símbolos",
            "Referência Bopomofo do Ministério da Educação de Taiwan",
            "Tabela Bopomofo do Unicode",
            "Fonte do banco de questões QTI 2.1",
            "Fonte de metadados e fixidade OER",
        ),
        "first_party": (
            "Divulgação de primeira parte: o iOS App Guide e o app opcional "
            "Lumi Bopomofo são publicados pela Lumi Apps. Estes cartões e o "
            "gerador para impressão funcionam sem o app."
        ),
        "about": "Reconhecimento de símbolos Bopomofo",
    },
    "es-MX": {
        "heading": "18 tarjetas fijas para reconocer símbolos Bopomofo",
        "intro": (
            "Cada pregunta y respuesta se muestra de inmediato. Las tarjetas "
            "usan datos fijos de símbolo, categoría y Unicode procedentes de un "
            "solo conjunto canónico de 37 símbolos; ninguna respuesta se adivina."
        ),
        "question": (
            "¿Qué símbolo Bopomofo del grupo «{category}» está codificado en "
            "{unicode}?"
        ),
        "categories": {
            "initial": "inicial",
            "medial": "medial",
            "final": "final",
        },
        "answer": "Respuesta",
        "record_source": "Fila de origen {order}",
        "boundary": (
            "El punto de código Unicode identifica el carácter. El nombre del "
            "carácter en inglés de Unicode es un identificador, no una lección "
            "de pronunciación; usa la referencia del Ministerio de Educación "
            "de Taiwán para consultar la pronunciación."
        ),
        "sources_heading": "Fuentes y trazabilidad",
        "sources_intro": (
            "Cada respuesta se enlaza directamente con su fila de la fuente "
            "canónica. Los enlaces QTI y OER muestran el mismo origen en "
            "formatos reutilizables."
        ),
        "source_labels": (
            "Conjunto canónico de 37 símbolos",
            "Referencia Bopomofo del Ministerio de Educación de Taiwán",
            "Tabla Bopomofo de Unicode",
            "Fuente del banco de preguntas QTI 2.1",
            "Fuente de metadatos y fijación OER",
        ),
        "first_party": (
            "Divulgación de primera parte: iOS App Guide y la app opcional "
            "Lumi Bopomofo son publicados por Lumi Apps. Estas tarjetas y el "
            "generador para imprimir funcionan sin la app."
        ),
        "about": "Reconocimiento de símbolos Bopomofo",
    },
    "vi": {
        "heading": "18 thẻ cố định để nhận biết ký hiệu Bopomofo",
        "intro": (
            "Mỗi câu hỏi và câu trả lời đều hiện ngay trên trang. Các thẻ dùng "
            "dữ kiện cố định về ký hiệu, nhóm và Unicode từ một bộ dữ liệu chuẩn "
            "duy nhất gồm 37 ký hiệu; không câu trả lời nào được suy đoán."
        ),
        "question": (
            "Ký hiệu Bopomofo thuộc nhóm “{category}” được mã hóa tại "
            "{unicode} là gì?"
        ),
        "categories": {
            "initial": "phụ âm đầu",
            "medial": "âm đệm",
            "final": "vần",
        },
        "answer": "Đáp án",
        "record_source": "Dòng nguồn {order}",
        "boundary": (
            "Điểm mã Unicode xác định ký tự. Tên ký tự tiếng Anh của Unicode là "
            "một mã định danh, không phải bài hướng dẫn phát âm; hãy dùng tài "
            "liệu liên kết của Bộ Giáo dục Đài Loan để tra cách đọc."
        ),
        "sources_heading": "Nguồn và khả năng truy vết",
        "sources_intro": (
            "Mỗi đáp án liên kết trực tiếp với dòng dữ liệu chuẩn tương ứng. "
            "Các liên kết QTI và OER trình bày cùng nguồn gốc ở định dạng có thể "
            "tái sử dụng."
        ),
        "source_labels": (
            "Bộ dữ liệu chuẩn gồm 37 ký hiệu",
            "Tài liệu Bopomofo của Bộ Giáo dục Đài Loan",
            "Bảng mã Bopomofo của Unicode",
            "Nguồn ngân hàng câu hỏi QTI 2.1",
            "Nguồn siêu dữ liệu và kiểm định OER",
        ),
        "first_party": (
            "Công bố bên thứ nhất: iOS App Guide và ứng dụng Lumi Bopomofo tùy "
            "chọn đều do Lumi Apps phát hành. Các thẻ này và trình tạo bản in "
            "hoạt động mà không cần ứng dụng."
        ),
        "about": "Nhận biết ký hiệu Bopomofo",
    },
}

CANARY_STYLE = """
.education-qa-canary{margin:0 auto 30px;padding:clamp(20px,4vw,36px);
background:#fff;border:1px solid var(--line);border-radius:26px;
box-shadow:var(--shadow)}
.education-qa-canary h2,.education-qa-canary h3{margin:.1em 0 .35em}
.education-qa-canary-intro,.education-qa-boundary,
.education-qa-source-intro,.education-qa-first-party{color:var(--muted)}
.education-qa-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
gap:14px;margin:22px 0}
.education-qa-card{display:flex;flex-direction:column;justify-content:space-between;
min-height:178px;padding:18px;border:1px solid var(--line);border-radius:18px;
background:linear-gradient(180deg,#fff,#f7f8ff)}
.education-qa-question{font-weight:760;margin:0 0 18px}
.education-qa-answer{margin:0;padding-top:12px;border-top:1px solid var(--line)}
.education-qa-answer-text{font-size:34px;font-weight:760;margin-left:8px}
.education-qa-record-link{align-self:flex-end;margin-top:10px;font-size:12px}
.education-qa-sources{padding-left:22px}
@media(max-width:680px){.education-qa-list{grid-template-columns:1fr}}
""".strip()


def google_education_qa_supported(locale: str) -> bool:
    """Match Google's documented language and region availability exactly."""
    normalized = locale.replace("_", "-")
    language = normalized.split("-", 1)[0].lower()
    if language in {"en", "pt", "vi"}:
        return True
    return normalized.lower() == "es-mx"


GOOGLE_ELIGIBLE_OFFICIAL_LOCALES = tuple(
    locale for locale in OFFICIAL_LOCALES if google_education_qa_supported(locale)
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


SOURCE_DIGEST = hashlib.sha256(
    _canonical_json(CANONICAL_ROWS).encode("utf-8")
).hexdigest()


def flashcards(locale: str) -> list[dict[str, object]]:
    try:
        copy = EDUCATION_COPY[locale]
    except KeyError as error:
        raise ValueError(f"unsupported Education Q&A locale: {locale}") from error
    cards = []
    for order in FLASHCARD_ORDERS:
        row = ROWS_BY_ORDER[order]
        question = copy["question"].format(
            category=copy["categories"][row["category"]],
            unicode=row["unicode"],
        )
        cards.append(
            {
                "id": row["symbol_id"].lower(),
                "order": row["order"],
                "question": question,
                "answer": row["symbol"],
                "unicode": row["unicode"],
                "category": row["category"],
                "concept_uri": row["concept_uri"],
            }
        )
    return cards


def quiz_schema(locale: str) -> dict[str, object] | None:
    if not google_education_qa_supported(locale):
        return None
    copy = EDUCATION_COPY[locale]
    return {
        "@context": "https://schema.org",
        "@type": "Quiz",
        "@id": f"{base.canonical(locale)}#fixed-study-flashcards",
        "inLanguage": locale,
        "about": {
            "@type": "Thing",
            "name": copy["about"],
        },
        "hasPart": [
            {
                "@type": "Question",
                "eduQuestionType": "Flashcard",
                "text": card["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": card["answer"],
                },
            }
            for card in flashcards(locale)
        ],
    }


def content_digest(locale: str) -> str:
    return hashlib.sha256(
        _canonical_json(flashcards(locale)).encode("utf-8")
    ).hexdigest()


def schema_digest(locale: str) -> str:
    schema = quiz_schema(locale)
    if schema is None:
        return ""
    return hashlib.sha256(_canonical_json(schema).encode("utf-8")).hexdigest()


def _json_script(value: dict[str, object]) -> str:
    payload = _canonical_json(value).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def render_visible_section(locale: str) -> str:
    copy = EDUCATION_COPY[locale]
    cards = "".join(
        (
            '<article class="education-qa-card" role="listitem" '
            f'data-flashcard-id="{html.escape(card["id"], quote=True)}" '
            f'data-source-order="{card["order"]}" '
            f'data-source-unicode="{html.escape(card["unicode"], quote=True)}">'
            '<p class="education-qa-question">'
            f'{html.escape(card["question"])}</p>'
            '<p class="education-qa-answer">'
            f'<span class="education-qa-answer-label">{html.escape(copy["answer"])}'
            ':</span><span class="education-qa-answer-text">'
            f'{html.escape(card["answer"])}</span></p>'
            '<a class="education-qa-record-link" '
            f'href="{html.escape(card["concept_uri"], quote=True)}" '
            'rel="noopener">'
            f'{html.escape(copy["record_source"].format(order=card["order"]))}'
            "</a></article>"
        )
        for card in flashcards(locale)
    )
    source_items = "".join(
        (
            f'<li><a href="{html.escape(source["url"], quote=True)}" '
            'rel="noopener">'
            f'{html.escape(label)}</a></li>'
        )
        for label, source in zip(
            copy["source_labels"],
            SOURCE_PROVENANCE,
            strict=True,
        )
    )
    return (
        f"{BODY_START}\n"
        '<section class="education-qa-canary wrap" '
        'id="fixed-study-flashcards" data-static-visible-qa="true">\n'
        f'<h2>{html.escape(copy["heading"])}</h2>\n'
        f'<p class="education-qa-canary-intro">{html.escape(copy["intro"])}</p>\n'
        f'<div class="education-qa-list" role="list">{cards}</div>\n'
        f'<p class="education-qa-boundary">{html.escape(copy["boundary"])}</p>\n'
        f'<h3>{html.escape(copy["sources_heading"])}</h3>\n'
        f'<p class="education-qa-source-intro">'
        f'{html.escape(copy["sources_intro"])}</p>\n'
        f'<ul class="education-qa-sources">{source_items}</ul>\n'
        '<p class="education-qa-first-party" '
        'data-first-party-disclosure="true">'
        f'{html.escape(copy["first_party"])}</p>\n'
        "</section>\n"
        f"{BODY_END}"
    )


def render_candidate_page(locale: str, app_public: bool = True) -> str:
    if locale not in CANARY_LOCALES:
        raise ValueError(f"locale is not in the canary roster: {locale}")
    if not google_education_qa_supported(locale):
        raise ValueError(f"locale is not eligible for Education Q&A: {locale}")
    control = base.render_page(
        locale,
        app_public=app_public,
        alternate_locales=CANARY_LOCALES,
    )
    schema = quiz_schema(locale)
    if schema is None:
        raise RuntimeError("canary locale unexpectedly lacks Quiz schema")
    head_block = (
        f"{HEAD_START}\n"
        f"<style>{CANARY_STYLE}</style>\n"
        f"{_json_script(schema)}\n"
        f"{HEAD_END}\n"
    )
    body_block = render_visible_section(locale) + "\n"
    if "</head>" not in control:
        raise RuntimeError("control page is missing </head>")
    body_marker = '<section class="wrap grid">'
    if body_marker not in control:
        raise RuntimeError("control page is missing the educational content grid")
    candidate = control.replace("</head>", head_block + "</head>", 1)
    candidate = candidate.replace(body_marker, body_block + body_marker, 1)
    errors = validate_candidate_page(locale, candidate, control)
    if errors:
        raise RuntimeError("; ".join(errors))
    return candidate


_MANAGED_BLOCK = re.compile(
    rf"(?:{re.escape(HEAD_START)}.*?{re.escape(HEAD_END)}\n?|"
    rf"{re.escape(BODY_START)}.*?{re.escape(BODY_END)}\n?)",
    re.DOTALL,
)


def strip_managed_blocks(page: str) -> str:
    return _MANAGED_BLOCK.sub("", page)


def validate_candidate_page(
    locale: str,
    page: str,
    control: str | None = None,
) -> list[str]:
    errors = []
    cards = flashcards(locale)
    schema = quiz_schema(locale)
    body_match = re.search(
        rf"{re.escape(BODY_START)}(.*?){re.escape(BODY_END)}",
        page,
        re.DOTALL,
    )
    body = body_match.group(1) if body_match else ""
    if not body:
        errors.append("missing visible Education Q&A block")
    for card in cards:
        question = f'<p class="education-qa-question">{html.escape(card["question"])}</p>'
        answer = (
            '<span class="education-qa-answer-text">'
            f'{html.escape(card["answer"])}</span>'
        )
        if question not in body:
            errors.append(f"missing visible question {card['id']}")
        if answer not in body:
            errors.append(f"missing visible answer {card['id']}")
    if body.count('class="education-qa-card"') != len(cards):
        errors.append("visible flashcard count differs from source")
    lowered_body = body.lower()
    for forbidden in (
        "<script",
        " hidden",
        "aria-hidden",
        "display:none",
        "visibility:hidden",
        "opacity:0",
        "paywall",
    ):
        if forbidden in lowered_body:
            errors.append(f"visible block contains forbidden token: {forbidden}")
    scripts = [
        json.loads(payload)
        for payload in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            page,
            re.DOTALL,
        )
    ]
    quizzes = [item for item in scripts if item.get("@type") == "Quiz"]
    if len(quizzes) != 1:
        errors.append("candidate must contain exactly one Quiz object")
    elif quizzes[0] != schema:
        errors.append("Quiz object differs from the canonical schema")
    if '"@type":"QAPage"' in page:
        errors.append("flashcard leaf page must not use QAPage")
    if '"educationalAlignment"' in page:
        errors.append("unverified curriculum alignment is forbidden")
    if not google_education_qa_supported(locale):
        errors.append("Quiz emitted for unsupported locale")
    canonical = base.canonical(locale)
    if f'<link rel="canonical" href="{canonical}">' not in page:
        errors.append("canonical URL is missing or incorrect")
    for alternate in CANARY_LOCALES:
        expected = (
            f'<link rel="alternate" hreflang="{alternate}" '
            f'href="{base.canonical(alternate)}">'
        )
        if expected not in page:
            errors.append(f"missing hreflang {alternate}")
    if 'data-first-party-disclosure="true"' not in body:
        errors.append("first-party disclosure is missing")
    app_links = re.findall(
        r'https://apps\.apple\.com/[^"\s<]+',
        page,
        re.IGNORECASE,
    )
    if any(f"id{base.APP_ID}" not in link for link in app_links):
        errors.append("unrelated App Store promotion found")
    if app_links and page.index(app_links[0]) < page.index(BODY_END):
        errors.append("App CTA appears before the complete educational content")
    if control is not None and strip_managed_blocks(page) != control:
        errors.append("non-managed control content changed")
    if any(token in body for token in ("{category}", "{unicode}", "education_qa.")):
        errors.append("raw localization key or placeholder is visible")
    if locale != "en":
        english = EDUCATION_COPY["en"]
        if english["heading"] in body or english["intro"] in body:
            errors.append("English fallback found in localized Education Q&A")
    return errors
