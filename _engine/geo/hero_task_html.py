"""Non-destructive HTML boundaries for supplemental hero-task resources."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


@dataclass(eq=False)
class Element:
    tag: str
    attrs: dict
    start: int
    open_end: int
    parent: Element | None
    end: int | None = None
    children: list[Element] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def within(self, ancestor: Element) -> bool:
        node = self
        while node:
            if node is ancestor:
                return True
            node = node.parent
        return False


class Document(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0, *(match.end() for match in re.finditer("\n", source))]
        self.root = Element("", {}, 0, 0, None, len(source))
        self.stack = [self.root]
        self.nodes: list[Element] = []
        self.text: list[tuple[Element, str]] = []
        self.feed(source)
        self.close()

    def absolute_position(self) -> int:
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.absolute_position()
        end = start + len(self.get_starttag_text())
        node = Element(tag, dict(attrs), start, end, self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag in VOID:
            node.end = end
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            node = self.stack.pop()
            node.end = node.open_end

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack[index].end = self.source.find(">", self.absolute_position()) + 1
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.text.append((self.stack[-1], data))

    def first(self, tag: str) -> Element | None:
        return next((node for node in self.nodes if node.tag == tag), None)


def without_resource(source: str, marker: str) -> str:
    return re.sub(
        rf"<!-- {re.escape(marker)}:start -->.*?<!-- {re.escape(marker)}:end -->",
        "", source, flags=re.S,
    )


def generated_index(source: str) -> bool:
    return any(
        node.tag == "meta" and node.attrs.get("name") == "hero-tools-index"
        and node.attrs.get("content") == "v1"
        for node in Document(source).nodes
    )


def require_retirable_index(source: str, marker: str, *, label: str) -> None:
    if not generated_index(source):
        raise ValueError(f"Refusing to delete an index not owned by hero tasks: {label}")
    document = Document(without_resource(source, marker))
    body = document.first("body")
    headings = [node for node in document.nodes if node.tag == "h1" and body and node.within(body)]
    if (
        not body or len(headings) != 1
        or any(node.tag not in {"body", "main", "h1"} for node in document.nodes if node.within(body))
        or any(text.strip() and node.within(body) and not node.within(headings[0])
               for node, text in document.text)
    ):
        raise ValueError(f"Generated index now contains other content; preserving it: {label}")


def useful_navigation(source: str, locale: str, url: str, marker: str, *, tools: bool) -> bool:
    document = Document(without_resource(source, marker))
    root, head = document.first("html"), document.first("head")
    accepted_languages = {locale}
    if locale not in {"zh-Hant", "zh-Hans"}:
        accepted_languages.add(locale.split("-")[0])
    if not root or root.attrs.get("lang") not in accepted_languages or not head or not document.first("h1"):
        return False
    if generated_index(source):
        return False
    metadata = [node for node in document.nodes if node.within(head)]
    if any(node.tag == "meta" and node.attrs.get("name", "").lower() == "robots"
           and "noindex" in (node.attrs.get("content") or "").lower() for node in metadata):
        return False
    if not any(node.tag == "link" and "canonical" in (node.attrs.get("rel") or "").split()
               and node.attrs.get("href") == url for node in metadata):
        return False
    if not any(node.tag == "meta" and node.attrs.get("name") == "description"
               and (node.attrs.get("content") or "").strip() for node in metadata):
        return False
    if tools and not any(node.tag == "link" and node.attrs.get("hreflang") for node in metadata):
        return False
    links = set()
    for node in document.nodes:
        href = node.attrs.get("href") or ""
        if node.tag != "a" or not href or href.startswith("#"):
            continue
        target = urlsplit(urljoin(url, href))
        stem = target.path.rsplit("/", 1)[-1]
        if (
            target.netloc == urlsplit(url).netloc and target.path.endswith(".html")
            and stem not in {"index.html", "about.html", "privacy.html", "support.html", "terms.html", "contact.html"}
            and (not tools or "/tools/" in target.path)
        ):
            links.add(target.path)
    return len(links) >= 2


def visible(node: Element) -> bool:
    while node:
        if (
            node.tag in {"template", "nav", "footer"}
            or "hidden" in node.attrs or node.attrs.get("aria-hidden") == "true"
            or "display:none" in re.sub(r"\s+", "", node.attrs.get("style") or "").lower()
        ):
            return False
        node = node.parent
    return True


def is_primary_action(node: Element) -> bool:
    return (
        node.tag in {"a", "button"} and visible(node)
        and "ghost" not in node.classes
        and (
            bool(node.classes & {"cta", "primary", "primary-cta", "button-primary", "iag-decision-card__cta"})
            or (node.attrs.get("href") or "").startswith("https://apps.apple.com/")
        )
    )


def insert_resource(source: str, block: str, marker: str, *, index: bool = False, label: str = "") -> str:
    source = without_resource(source, marker)
    document = Document(source)
    main = document.first("main") or document.first("body")
    heading = next(
        (node for node in document.nodes
         if node.tag == "h1" and main and node.within(main) and visible(node)),
        None,
    )
    if heading is None:
        body = document.first("body")
        heading = next(
            (node for node in document.nodes
             if node.tag == "h1" and body and node.within(body) and visible(node)),
            None,
        )
    if not heading or heading.end is None:
        raise ValueError(f"No complete primary h1 for supplemental resources: {label}")
    scope = heading.parent
    while scope and not (
        scope.tag in {"main", "body"} or scope.classes & {"e-content", "entry-content", "h-entry", "hentry"}
    ):
        scope = scope.parent
    if scope is None or scope.end is None:
        raise ValueError(f"No complete primary content boundary: {label}")
    intro = heading.parent
    while intro is not scope and intro is not None:
        if intro.tag == "header" or intro.classes & {"hero", "page-hero", "app-hero", "page-header"}:
            break
        intro = intro.parent
    if intro is scope:
        intro = None
    boundary = min(
        (node.start for node in document.nodes
         if node.tag in {"h2", "h3"} and node.start > heading.end
         and node.within(scope) and visible(node)),
        default=scope.end,
    )
    anchors = [heading]
    if intro:
        anchors.append(intro)
    anchors.extend(
        node for node in document.nodes
        if node.tag == "p" and heading.end <= node.start < boundary
        and node.within(scope) and visible(node)
        and (node.parent is scope or node.classes & {"lead", "p-summary", "entry-summary"})
    )
    if not index:
        action = next(
            (node for node in document.nodes
             if heading.end <= node.start < boundary and node.within(scope) and is_primary_action(node)),
            None,
        )
        if action:
            anchors.append(action)
    ends = []
    for node in anchors:
        while node.parent is not scope:
            node = node.parent
            if node is None or node is scope:
                raise ValueError(f"Unsafe supplemental content boundary: {label}")
        if node.end is None:
            raise ValueError(f"Unclosed introductory content: {label}")
        ends.append(node.end)
    position = max(ends)
    # Stay outside replaceable CTA blocks, not between their element and end marker.
    closing_marker = re.compile(r"\s*<!--\s*[\w.-]+:end\s*-->")
    while match := closing_marker.match(source, position):
        position = match.end()
    return source[:position] + block + source[position:]
