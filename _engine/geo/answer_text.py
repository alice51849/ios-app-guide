#!/usr/bin/env python3
"""Text integrity helpers shared by Answer generators and repair gates."""

from __future__ import annotations

import re


_DANGLING_END_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "because",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "its",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "with",
    "your",
}
_BAD_TERMINAL_PUNCTUATION_RE = re.compile(
    r"[,;:\u060c\u061b\uff0c\uff1b\uff1a]\s*"
    r"[.!?\u3002\uff01\uff1f]$"
)
_DANGLING_ENGLISH_END_RE = re.compile(
    r"\b(?:" + "|".join(sorted(_DANGLING_END_WORDS)) + r")\.$",
    flags=re.IGNORECASE,
)
_DANGLING_DASH_SUBORDINATE_RE = re.compile(
    r"\s[\u2013\u2014]\s+and\s+"
    r"(?:as|because|if|when|while|although|unless|until)\b"
    r"[^.!?;:,\u060c\uff0c\u2013\u2014]*\.$",
    flags=re.IGNORECASE,
)
_LOCALIZED_DANGLING_END_WORDS = {
    "de-DE": {
        "das",
        "der",
        "die",
        "für",
        "im",
        "in",
        "mit",
        "oder",
        "und",
        "von",
        "zu",
    },
    "es-ES": {
        "con",
        "de",
        "del",
        "el",
        "la",
        "las",
        "los",
        "o",
        "para",
        "que",
        "y",
    },
    "fr-FR": {
        "avec",
        "de",
        "des",
        "du",
        "et",
        "la",
        "le",
        "les",
        "ou",
        "pour",
        "que",
        "un",
        "une",
    },
    "pt-BR": {
        "a",
        "as",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "o",
        "os",
        "ou",
        "para",
        "que",
    },
}
_STRICT_SENTENCE_LOCALES = frozenset(_LOCALIZED_DANGLING_END_WORDS)
_TERMINAL_END_RE = re.compile(
    r"[.!?\u061f\u06d4\u0964\u0965\u3002\uff01\uff1f]"
    r"[\"')\]\u2019\u201d]*$"
)
_SENTENCE_END_RE = re.compile(
    r"[.!?\u061f\u06d4\u0964\u0965\u3002\uff01\uff1f]"
    r"[\"')\]\u2019\u201d]*"
)
_CLAUSE_BOUNDARY_RE = re.compile(
    r"\s[\u2013\u2014]\s|"
    r"[;:\u060c\u061b\uff0c\uff1b\uff1a]\s*"
)
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def has_bad_terminal_punctuation(text: str) -> bool:
    """Return whether punctuation proves the description was mechanically cut."""
    return bool(_BAD_TERMINAL_PUNCTUATION_RE.search(" ".join(text.split())))


def is_malformed_meta(text: str) -> bool:
    """Detect high-confidence English metadata fragments and punctuation damage."""
    compact = " ".join(text.split())
    return (
        not compact
        or has_bad_terminal_punctuation(compact)
        or bool(_DANGLING_ENGLISH_END_RE.search(compact))
        or bool(_DANGLING_DASH_SUBORDINATE_RE.search(compact))
    )


def is_malformed_localized_meta(
    text: str,
    locale: str,
    lead: str | None = None,
) -> bool:
    """Detect localized metadata that is demonstrably cut or malformed."""
    compact = " ".join(text.split())
    if not compact or has_bad_terminal_punctuation(compact):
        return True
    dangling = _LOCALIZED_DANGLING_END_WORDS.get(locale)
    if dangling and re.search(
        r"\b(?:" + "|".join(sorted(dangling)) + r")\.$",
        compact,
        flags=re.IGNORECASE,
    ):
        return True
    if locale in _STRICT_SENTENCE_LOCALES and not _TERMINAL_END_RE.search(compact):
        return True
    if lead:
        compact_lead = " ".join(lead.split())
        if (
            compact != compact_lead
            and compact_lead.startswith(compact)
            and not _TERMINAL_END_RE.search(compact)
        ):
            return True
    return False


def _balanced_brackets(text: str) -> bool:
    stack: list[str] = []
    closing = {")": "(", "]": "[", "}": "{"}
    for char in text:
        if char in "([{":
            stack.append(char)
        elif char in closing:
            if not stack or stack.pop() != closing[char]:
                return False
    return not stack


def _finish_sentence(text: str) -> str:
    cleaned = text.rstrip(
        " \t\r\n,;:-"
        "\u060c\u061b\u2013\u2014\uff0c\uff1b\uff1a"
    )
    if not cleaned:
        return ""
    if cleaned[-1] in ".!?\u061f\u06d4\u0964\u0965\u3002\uff01\uff1f":
        return cleaned
    return cleaned + ("\u3002" if _CJK_RE.search(cleaned) else ".")


def concise_meta(
    text: str,
    limit: int = 150,
    hard_limit: int = 220,
) -> str:
    """Return a complete extractive description without ellipsis or word damage."""
    if limit < 1 or hard_limit < limit:
        raise ValueError("Meta limits must satisfy 1 <= limit <= hard_limit")
    compact = " ".join(text.split())
    if not compact:
        raise ValueError("Meta description cannot be empty")
    if len(compact) <= limit and not is_malformed_meta(compact):
        return compact

    complete_sentences: list[str] = []
    for match in _SENTENCE_END_RE.finditer(compact):
        end = match.end()
        if end > hard_limit:
            break
        if end == len(compact) or compact[end].isspace():
            candidate = compact[:end]
            if not is_malformed_meta(candidate):
                complete_sentences.append(candidate)
    if complete_sentences:
        return complete_sentences[-1]

    clauses: list[str] = []
    for match in _CLAUSE_BOUNDARY_RE.finditer(compact):
        candidate = compact[: match.start()].rstrip()
        if (
            60 <= len(candidate) <= hard_limit
            and _balanced_brackets(candidate)
        ):
            finished = _finish_sentence(candidate)
            if finished and not is_malformed_meta(finished):
                clauses.append(finished)
    if clauses:
        return clauses[-1]

    prefix = compact[: limit + 1]
    if len(compact) > limit and " " in prefix:
        prefix = prefix.rsplit(" ", 1)[0]
    words = prefix.rstrip(" ,;:-").split()
    while words and words[-1].casefold().rstrip(".") in _DANGLING_END_WORDS:
        words.pop()
    shortened = _finish_sentence(" ".join(words))
    if not shortened or is_malformed_meta(shortened):
        raise ValueError("Unable to produce a complete meta description")
    return shortened
