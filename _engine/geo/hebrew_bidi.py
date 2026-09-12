"""Hebrew text isolation, with no changes to shared styles or other locales."""

from __future__ import annotations

import html
import re

LTR_RUN = re.compile(
    r"[A-Za-z0-9]+(?:[ \t:/+&.#'’@%=_~?()\-–‑]+[A-Za-z0-9]+)*"
)
LRI = "\u2066"
PDI = "\u2069"


def html_text(value: str, locale: str) -> str:
    if locale != "he":
        return html.escape(value)
    parts = []
    end = 0
    for match in LTR_RUN.finditer(value):
        parts.append(html.escape(value[end:match.start()]))
        parts.append(f'<bdi dir="ltr">{html.escape(match.group())}</bdi>')
        end = match.end()
    parts.append(html.escape(value[end:]))
    return "".join(parts)


def plain_text(value: str, locale: str) -> str:
    if locale != "he":
        return value
    return LTR_RUN.sub(lambda match: LRI + match.group() + PDI, value)


def social_preview(name: str, headline: str, copy: str, locale: str) -> str:
    """An unpublished preview, not a queue entry or delivery receipt."""
    body = f"{headline}\n\n{name}\n\n{copy}"
    if locale == "he":
        # A real Hebrew first strong character also works in dir=auto clients.
        body = "להכיר את האפליקציה:\n\n" + body
    return plain_text(body, locale)
