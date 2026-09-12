"""Lossless direction/isolation for external HTML, never locale-copy rewriting."""

from __future__ import annotations

import html
from html.parser import HTMLParser
import re
import unicodedata

RTL_LANGUAGES = frozenset({"ar", "ur", "he"})
TRANSPARENT_BDI = re.compile(r"</?bdi\b[^>]*>", re.I)
ENTITIES = re.compile(r"&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);?")
SEPARATORS = frozenset(" \t\u00a0:/+&.#'’@%=_~?()[],-–‑")
VOID_TAGS = frozenset("area base br col embed hr img input link meta param source track wbr".split())
PROTECTED = frozenset({"head", "script", "style", "title", "pre", "code", "textarea", "svg", "math", "bdi", "bdo"})


def transparent_bidi(fragment):
    return TRANSPARENT_BDI.sub("", fragment)


def _decoded_offsets(raw):
    text, spans = [], []
    index = 0
    while index < len(raw):
        entity = ENTITIES.match(raw, index)
        end = entity.end() if entity else index + 1
        decoded = html.unescape(raw[index:end]) if entity else raw[index:end]
        text.extend(decoded)
        spans.extend([(index, end)] * len(decoded))
        index = end
    return "".join(text), spans


def _ltr(character):
    return unicodedata.bidirectional(character) in {"L", "EN", "AN"}


def isolate_text(raw):
    text, offsets = _decoded_offsets(raw)
    spans = []
    index = 0
    while index < len(text):
        if not _ltr(text[index]):
            index += 1
            continue
        start = index
        index += 1
        while index < len(text):
            if _ltr(text[index]) or unicodedata.combining(text[index]):
                index += 1
                continue
            cursor = index
            while cursor < len(text) and text[cursor] in SEPARATORS:
                cursor += 1
            if cursor > index and cursor < len(text) and _ltr(text[cursor]):
                index = cursor + 1
                continue
            break
        spans.append((offsets[start][0], offsets[index - 1][1]))
    for start, end in reversed(spans):
        raw = raw[:start] + '<bdi dir="ltr">' + raw[start:end] + "</bdi>" + raw[end:]
    return raw


class _Isolation(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0, *(match.end() for match in re.finditer("\n", source))]
        self.stack = []
        self.rtl = False
        self.pending = None
        self.edits = []

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def flush(self):
        if self.pending is None:
            return
        start, end = self.pending
        self.pending = None
        if self.rtl and not any(tag in PROTECTED for tag in self.stack):
            original = self.source[start:end]
            updated = isolate_text(original)
            if original != updated:
                self.edits.append((start, end, updated))

    def handle_starttag(self, tag, attributes):
        self.flush()
        attrs = dict(attributes)
        if tag == "html":
            self.rtl = (attrs.get("lang") or "").lower().split("-")[0] in RTL_LANGUAGES
            if self.rtl and attrs.get("dir", "").lower() != "rtl":
                original = self.get_starttag_text()
                updated = re.sub(r'(?<![\w:-])dir\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', 'dir="rtl"', original, flags=re.I)
                if updated == original:
                    updated = original[:-1] + ' dir="rtl">'
                self.edits.append((self.source_offset(), self.source_offset() + len(original), updated))
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        self.flush()
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_startendtag(self, tag, attributes):
        self.flush()

    def remember(self, length):
        start = self.source_offset()
        if self.pending is None:
            self.pending = (start, start + length)
        else:
            self.pending = (self.pending[0], start + length)

    def handle_data(self, data):
        self.remember(len(data))

    def handle_entityref(self, name):
        match = ENTITIES.match(self.source, self.source_offset())
        self.remember(len(match.group()) if match else len(name) + 1)

    def handle_charref(self, name):
        match = ENTITIES.match(self.source, self.source_offset())
        self.remember(len(match.group()) if match else len(name) + 2)

    def handle_comment(self, data):
        self.flush()

    def handle_decl(self, decl):
        self.flush()

    def handle_pi(self, data):
        self.flush()


def isolate_document(source):
    parser = _Isolation(source)
    parser.feed(source)
    parser.close()
    parser.flush()
    for start, end, replacement in sorted(parser.edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source
