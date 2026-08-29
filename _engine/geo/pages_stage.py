#!/usr/bin/env python3
"""Build a deterministic, semantically equivalent Pages staging tree."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import gzip
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
from typing import Any, Iterable
import urllib.parse
import xml.etree.ElementTree as ET

from official_locales import OFFICIAL_LOCALES


SITE = "https://alice51849.github.io/ios-app-guide"
SITE_PATH = "/ios-app-guide/"
MAX_UNPACKED_BYTES = 900_000_000
HTML_SUFFIXES = frozenset({".html", ".htm"})
JSON_SUFFIXES = frozenset({".json", ".jsonld", ".webmanifest"})
TEXT_HASH_SUFFIXES = frozenset(
    {
        ".atom",
        ".css",
        ".csv",
        ".htm",
        ".html",
        ".js",
        ".json",
        ".jsonl",
        ".jsonld",
        ".md",
        ".mjs",
        ".nt",
        ".rdf",
        ".rss",
        ".svg",
        ".tsv",
        ".ttl",
        ".txt",
        ".webmanifest",
        ".xhtml",
        ".xml",
        ".xsd",
    }
)
BYTE_STABLE_PREFIXES = (
    "google-images-canary/",
    "media/google-images-canary/",
)
SOURCE_INVENTORY = ".well-known/publish-inventory.json"
SOURCE_INVENTORY_GZIP = ".well-known/source-publish-inventory.json.gz"
STAGE_MANIFEST = ".well-known/pages-stage-manifest.json.gz"
CSS_PREFIX = "assets/stage-css/"
JSONLD_JS_PREFIX = "assets/stage-jsonld/"
HREFLANG_PREFIX = "sitemaps/stage-hreflang-"
HREFLANG_SHARD_LIMIT = 40_000_000
STABLE_SITEMAPS = frozenset(
    {
        "sitemap.xml",
        "sitemap_google_images_canary.xml",
        "sitemap_google_images_treatment.xml",
        "sitemap_index.xml",
    }
)
SHA_TOKEN_RE = re.compile(rb"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
WHITESPACE_RE = re.compile(r"\s+")
START_TAG_RE = re.compile(r"<\s*([A-Za-z][^\s/>]*)")
END_TAG_RE = re.compile(r"</\s*([A-Za-z][^\s/>]*)")
ATTR_RE = re.compile(
    r"""([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
    re.I,
)
SAFE_UNQUOTED_RE = re.compile(r"""[A-Za-z0-9._:/?#%+@,;~&()\-]+""")
KEEP_COMMENT_RE = re.compile(
    r"(?:^\s*\[if\b|iag-|google-images-canary)",
    re.I,
)
SCRIPT_BLOCK_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
    re.I | re.S,
)
URL_ATTRIBUTES = frozenset(
    {
        "action",
        "background",
        "cite",
        "data",
        "formaction",
        "href",
        "longdesc",
        "poster",
        "src",
        "usemap",
    }
)
URL_SHORTEN_TAGS = frozenset(
    {
        "a",
        "amp-story",
        "area",
        "audio",
        "embed",
        "form",
        "iframe",
        "img",
        "link",
        "object",
        "script",
        "source",
        "video",
    }
)
PRESERVE_TEXT_TAGS = frozenset(
    {"listing", "plaintext", "pre", "textarea", "xmp"}
)
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
URL_SCHEMA_KEYS = frozenset(
    {
        "@id",
        "contenturl",
        "downloadurl",
        "embedurl",
        "image",
        "installurl",
        "ispartof",
        "item",
        "logo",
        "mainentityofpage",
        "sameas",
        "target",
        "thumbnailurl",
        "url",
    }
)


class StageError(RuntimeError):
    """Raised when staging cannot prove publication safety."""


@dataclass(frozen=True)
class SourceFile:
    path: str
    source: Path
    size: int
    mode: int
    sha256: str


@dataclass(frozen=True)
class SemanticSnapshot:
    dom_sha256: str
    canonical: tuple[str, ...]
    hreflang: tuple[tuple[str, str], ...]
    noindex: bool
    schema_sha256: str
    styles: tuple[str, ...]
    internal_urls: tuple[str, ...]

    @property
    def semantic_sha256(self) -> str:
        return sha256_bytes(
            canonical_json(
                {
                    "canonical": self.canonical,
                    "dom": self.dom_sha256,
                    "noindex": self.noindex,
                    "schema": self.schema_sha256,
                    "styles": self.styles,
                }
            )
        )


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def digest_base64url(value: str | None) -> str | None:
    if value is None:
        return None
    return base64.urlsafe_b64encode(bytes.fromhex(value)).decode("ascii").rstrip("=")


def deterministic_gzip(content: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=output,
        compresslevel=9,
        mtime=0,
    ) as archive:
        archive.write(content)
    return output.getvalue()


def _root(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise StageError(f"{label} is unavailable: {path}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise StageError(f"{label} is a symlink: {path}")
    resolved = path.resolve()
    if not resolved.is_dir():
        raise StageError(f"{label} is not a directory: {resolved}")
    return resolved


def _output_root(source: Path, output: Path) -> Path:
    if output.is_symlink():
        raise StageError(f"Pages staging output is a symlink: {output}")
    resolved = output.parent.resolve() / output.name
    try:
        resolved.relative_to(source)
    except ValueError:
        pass
    else:
        raise StageError("Pages staging output must be outside the source tree")
    if resolved.exists() and any(resolved.iterdir()):
        raise StageError(f"Pages staging output must be empty: {resolved}")
    return resolved


def _relative(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    candidate = PurePosixPath(relative)
    if (
        not relative
        or relative.startswith("/")
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or "\\" in relative
    ):
        raise StageError(f"Unsafe Pages staging path: {relative!r}")
    return relative


def scan_source(
    source_root: Path,
) -> tuple[Path, list[SourceFile], set[bytes], set[str]]:
    root = _root(source_root, "Pages staging source")
    files: list[SourceFile] = []
    inodes: dict[tuple[int, int], str] = {}
    hash_tokens: set[bytes] = set()
    noindex_paths: set[str] = set()
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(dirnames)
        base = Path(directory)
        for name in sorted(filenames):
            path = base / name
            relative = _relative(root, path)
            try:
                metadata = path.lstat()
            except OSError as error:
                raise StageError(
                    f"Cannot stat Pages staging source: {relative}"
                ) from error
            if stat.S_ISLNK(metadata.st_mode):
                raise StageError(
                    f"Pages staging source contains symlink: {relative}"
                )
            if not stat.S_ISREG(metadata.st_mode):
                raise StageError(
                    f"Pages staging source contains special file: {relative}"
                )
            if metadata.st_nlink != 1:
                raise StageError(
                    f"Pages staging source contains hard-linked file: {relative}"
                )
            inode = (metadata.st_dev, metadata.st_ino)
            if inode in inodes:
                raise StageError(
                    "Pages staging source aliases one inode: "
                    f"{inodes[inode]}, {relative}"
                )
            inodes[inode] = relative
            digest = hashlib.sha256()
            token_scan = (
                path.suffix.lower() in TEXT_HASH_SUFFIXES
                and metadata.st_size <= 25_000_000
            )
            token_bytes = bytearray() if token_scan else None
            try:
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        digest.update(chunk)
                        if token_bytes is not None:
                            token_bytes.extend(chunk)
            except OSError as error:
                raise StageError(
                    f"Cannot read Pages staging source: {relative}"
                ) from error
            if token_bytes is not None:
                hash_tokens.update(SHA_TOKEN_RE.findall(token_bytes))
                if (
                    path.suffix.lower() in HTML_SUFFIXES
                    and html_is_noindex(bytes(token_bytes))
                ):
                    noindex_paths.add(relative)
            files.append(
                SourceFile(
                    path=relative,
                    source=path,
                    size=metadata.st_size,
                    mode=stat.S_IMODE(metadata.st_mode),
                    sha256=digest.hexdigest(),
                )
            )
    return root, files, hash_tokens, noindex_paths


def document_url(relative: str) -> str:
    return f"{SITE}/{urllib.parse.quote(relative, safe='/')}"


def _resolved_url(value: str, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(value.strip()))


def internal_path(value: str, base_url: str) -> str | None:
    resolved = urllib.parse.urlsplit(_resolved_url(value, base_url))
    site = urllib.parse.urlsplit(SITE)
    if resolved.scheme not in {"http", "https"} or resolved.netloc != site.netloc:
        return None
    base_path = site.path.rstrip("/")
    path = urllib.parse.unquote(resolved.path)
    if path == base_path or path == f"{base_path}/":
        return "index.html"
    prefix = f"{base_path}/"
    if not path.startswith(prefix):
        return None
    relative = path[len(prefix) :].lstrip("/")
    if not relative:
        return "index.html"
    if relative.endswith("/"):
        relative += "index.html"
    candidate = PurePosixPath(relative)
    if ".." in candidate.parts:
        raise StageError(f"Unsafe internal URL path: {value!r}")
    return candidate.as_posix()


def _attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, value in attrs:
        lowered = name.lower()
        if lowered in result:
            raise StageError(f"Duplicate HTML attribute: {name}")
        result[lowered] = "" if value is None else value
    return result


def html_is_noindex(content: bytes) -> bool:
    head_end = content.lower().find(b"</head")
    head = content if head_end < 0 else content[:head_end]
    for match in re.finditer(rb"<meta\b[^>]*>", head, re.I):
        try:
            attrs = _raw_attributes(match.group(0).decode("utf-8"))
        except (UnicodeDecodeError, StageError):
            continue
        if attrs.get("name", "").strip().lower() != "robots":
            continue
        directives = {
            token
            for token in re.split(
                r"[\s,]+",
                attrs.get("content", "").strip().lower(),
            )
            if token
        }
        if directives & {"noindex", "none"}:
            return True
    return False


def _normalized_attr(
    name: str,
    value: str | None,
    *,
    base_url: str,
) -> tuple[str, str | None]:
    lowered = name.lower()
    if value is None:
        return lowered, None
    if is_url_attribute(lowered):
        return lowered, _resolved_url(value, base_url)
    if lowered == "srcset":
        candidates = []
        for item in value.split(","):
            parts = item.strip().split()
            if not parts:
                continue
            parts[0] = _resolved_url(parts[0], base_url)
            candidates.append(" ".join(parts))
        return lowered, ", ".join(candidates)
    return lowered, value


def is_url_attribute(name: str) -> bool:
    lowered = name.lower()
    return lowered in URL_ATTRIBUTES or lowered.endswith(
        ("-href", "-src", "-url")
    )


def is_html_hreflang(values: dict[str, str]) -> bool:
    relations = {
        item.lower() for item in values.get("rel", "").split()
    }
    if (
        "alternate" not in relations
        or not values.get("hreflang")
        or not values.get("href")
    ):
        return False
    media_type = values.get("type", "").split(";", 1)[0].strip().lower()
    if media_type:
        return media_type in {"application/xhtml+xml", "text/html"}
    path = urllib.parse.urlsplit(html.unescape(values["href"])).path
    suffix = PurePosixPath(path).suffix.lower()
    return not suffix or suffix in HTML_SUFFIXES


def _schema_records(value: object) -> list[bytes]:
    if isinstance(value, dict):
        context = value.get("@context")
        material = {
            key: item for key, item in value.items() if key != "@context"
        }
        if set(material) == {"@graph"} and isinstance(
            material["@graph"], list
        ):
            values = material["@graph"]
        else:
            values = [material]
    elif isinstance(value, list):
        context = None
        values = value
    else:
        context = None
        values = [value]
    return [
        canonical_json({"@context": context, "value": item})
        for item in values
    ]


def _schema_internal_urls(
    value: object,
    *,
    base_url: str,
    key: str = "",
) -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _schema_internal_urls(
                child,
                base_url=base_url,
                key=str(child_key).lower(),
            )
    elif isinstance(value, list):
        for child in value:
            yield from _schema_internal_urls(
                child,
                base_url=base_url,
                key=key,
            )
    elif isinstance(value, str) and key in URL_SCHEMA_KEYS:
        if internal_path(value, base_url) is not None:
            yield _resolved_url(value, base_url)


class SemanticParser(HTMLParser):
    def __init__(
        self,
        *,
        base_url: str,
        css_assets: dict[str, bytes],
        json_ld_assets: dict[str, bytes] | None = None,
        neutralized_paths: set[str] | None = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.css_assets = css_assets
        self.json_ld_assets = json_ld_assets or {}
        self.neutralized_paths = neutralized_paths
        self.dom = hashlib.sha256()
        self.canonical: list[str] = []
        self.hreflang: list[tuple[str, str]] = []
        self.noindex = False
        self.schema: list[bytes] = []
        self.styles: list[str] = []
        self.internal_urls: set[str] = set()
        self.preserve_depth = 0
        self.style_attrs: tuple[tuple[str, str | None], ...] | None = None
        self.style_parts: list[str] = []
        self.script_attrs: tuple[tuple[str, str | None], ...] | None = None
        self.script_parts: list[str] = []
        self.anchor_rewrites: list[bool] = []
        self.external_json_ld = 0

    def _event(self, event: object) -> None:
        self.dom.update(canonical_json(event))

    def _reference(self, value: str) -> None:
        if internal_path(value, self.base_url) is not None:
            self.internal_urls.add(_resolved_url(value, self.base_url))

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lowered = tag.lower()
        values = _attrs_dict(attrs)
        if lowered == "a":
            href = values.get("href", "")
            target = internal_path(href, self.base_url) if href else None
            rewrite = (
                self.neutralized_paths is not None
                and target is not None
                and target in self.neutralized_paths
            )
            self.anchor_rewrites.append(rewrite)
            if rewrite:
                lowered = "span"
                attrs = []
                values = {}
        relations = {
            item.lower() for item in values.get("rel", "").split()
        }
        if (
            lowered == "meta"
            and values.get("name", "").strip().lower() == "robots"
        ):
            directives = {
                token
                for token in re.split(
                    r"[\s,]+",
                    values.get("content", "").strip().lower(),
                )
                if token
            }
            self.noindex = self.noindex or bool(
                directives & {"noindex", "none"}
            )
        if lowered == "base" and values.get("href"):
            self.base_url = _resolved_url(values["href"], self.base_url)
        if lowered == "script" and values.get("src"):
            relative = internal_path(values["src"], self.base_url)
            if relative and relative.startswith(JSONLD_JS_PREFIX):
                try:
                    content = self.json_ld_assets[relative]
                except KeyError as error:
                    raise StageError(
                        f"Missing staged JSON-LD loader asset: {relative}"
                    ) from error
                try:
                    value = json.loads(
                        content,
                        object_pairs_hook=_object_without_duplicate_keys,
                    )
                except (TypeError, ValueError, json.JSONDecodeError) as error:
                    raise StageError(
                        f"Invalid staged JSON-LD loader asset: {relative}"
                    ) from error
                self.schema.extend(_schema_records(value))
                self.internal_urls.add(
                    _resolved_url(values["src"], self.base_url)
                )
                self.external_json_ld += 1
                return
        if lowered == "link" and is_html_hreflang(values):
            self.hreflang.append(
                (
                    values["hreflang"],
                    _resolved_url(values["href"], self.base_url),
                )
            )
            return
        if lowered == "style":
            self.style_attrs = tuple(attrs)
            self.style_parts = []
            return
        if lowered == "script" and (
            values.get("type", "").lower() == "application/ld+json"
        ):
            self.script_attrs = tuple(attrs)
            self.script_parts = []
            return
        if lowered == "link" and "stylesheet" in relations:
            href = values.get("href", "")
            relative = internal_path(href, self.base_url) if href else None
            if relative and relative.startswith(CSS_PREFIX):
                try:
                    content = self.css_assets[relative]
                except KeyError as error:
                    raise StageError(
                        f"Missing staged stylesheet asset: {relative}"
                    ) from error
                self.styles.append(sha256_bytes(content))
                return
        normalized = tuple(
            _normalized_attr(name, value, base_url=self.base_url)
            for name, value in attrs
        )
        self._event(("start", lowered, normalized))
        if lowered in PRESERVE_TEXT_TAGS:
            self.preserve_depth += 1
        for name, value in attrs:
            if value is None:
                continue
            attr = name.lower()
            if is_url_attribute(attr):
                self._reference(value)
            elif attr == "srcset":
                for candidate in value.split(","):
                    url = candidate.strip().split()
                    if url:
                        self._reference(url[0])
        if lowered == "link" and "canonical" in relations and values.get("href"):
            self.canonical.append(
                _resolved_url(values["href"], self.base_url)
            )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        lowered = tag.lower()
        if lowered == "script" and self.external_json_ld:
            self.external_json_ld -= 1
            return
        if lowered not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "script" and self.external_json_ld:
            self.external_json_ld -= 1
            return
        if lowered == "a" and self.anchor_rewrites:
            if self.anchor_rewrites.pop():
                lowered = "span"
        if lowered == "style" and self.style_attrs is not None:
            body = "".join(self.style_parts).encode("utf-8")
            self.styles.append(sha256_bytes(body))
            self.style_attrs = None
            self.style_parts = []
            return
        if lowered == "script" and self.script_attrs is not None:
            source = "".join(self.script_parts)
            try:
                value = json.loads(
                    source,
                    object_pairs_hook=_object_without_duplicate_keys,
                )
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise StageError("Invalid JSON-LD in published HTML") from error
            self.schema.extend(_schema_records(value))
            self.script_attrs = None
            self.script_parts = []
            return
        if lowered in PRESERVE_TEXT_TAGS and self.preserve_depth:
            self.preserve_depth -= 1
        self._event(("end", lowered))

    def handle_data(self, data: str) -> None:
        if self.style_attrs is not None:
            self.style_parts.append(data)
            return
        if self.script_attrs is not None:
            self.script_parts.append(data)
            return
        normalized = (
            data
            if self.preserve_depth
            else WHITESPACE_RE.sub(" ", data).strip()
        )
        if normalized:
            self._event(("data", normalized))

    def handle_decl(self, decl: str) -> None:
        self._event(("decl", WHITESPACE_RE.sub(" ", decl.strip()).lower()))

    def handle_pi(self, data: str) -> None:
        self._event(("pi", data))

    def unknown_decl(self, data: str) -> None:
        self._event(("unknown_decl", data))

    def snapshot(self) -> SemanticSnapshot:
        if self.style_attrs is not None or self.script_attrs is not None:
            raise StageError("Unclosed style or JSON-LD element")
        if self.external_json_ld:
            raise StageError("Unclosed external JSON-LD loader")
        if self.anchor_rewrites:
            raise StageError("Unclosed anchor element")
        schema = hashlib.sha256()
        for record in sorted(self.schema):
            schema.update(record)
        return SemanticSnapshot(
            dom_sha256=self.dom.hexdigest(),
            canonical=tuple(sorted(self.canonical)),
            hreflang=tuple(sorted(set(self.hreflang))),
            noindex=self.noindex,
            schema_sha256=schema.hexdigest(),
            styles=tuple(self.styles),
            internal_urls=tuple(sorted(self.internal_urls)),
        )


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StageError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_semantics(
    content: bytes,
    *,
    relative: str,
    css_assets: dict[str, bytes],
    json_ld_assets: dict[str, bytes] | None = None,
    neutralized_paths: set[str] | None = None,
) -> SemanticSnapshot:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise StageError(f"HTML is not UTF-8: {relative}") from error
    parser = SemanticParser(
        base_url=document_url(relative),
        css_assets=css_assets,
        json_ld_assets=json_ld_assets,
        neutralized_paths=neutralized_paths,
    )
    try:
        parser.feed(text)
        parser.close()
    except StageError:
        raise
    except Exception as error:
        raise StageError(f"Cannot parse HTML semantics: {relative}") from error
    return parser.snapshot()


def _raw_attributes(tag: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        name = match.group(1).lower()
        if name in result:
            raise StageError(f"Duplicate HTML attribute: {name}")
        result[name] = html.unescape(
            next(
                value
                for value in match.groups()[1:]
                if value is not None
            )
        )
    return result


def _find_tag_end(source: str, start: int) -> int:
    quote = ""
    index = start + 1
    while index < len(source):
        character = source[index]
        if quote:
            if character == quote:
                quote = ""
        elif character in {'"', "'"}:
            quote = character
        elif character == ">":
            return index + 1
        index += 1
    raise StageError("Unterminated HTML tag")


def _minify_tag(raw: str) -> str:
    if raw.startswith("<!") or raw.startswith("<?"):
        return raw
    compact: list[str] = []
    quote = ""
    pending_space = False
    for character in raw:
        if quote:
            compact.append(character)
            if character == quote:
                quote = ""
            continue
        if character in {'"', "'"}:
            if pending_space and compact and compact[-1] not in "<=/":
                compact.append(" ")
            pending_space = False
            quote = character
            compact.append(character)
        elif character.isspace():
            pending_space = True
        else:
            if character == "=":
                while compact and compact[-1] == " ":
                    compact.pop()
            elif (
                pending_space
                and compact
                and compact[-1] not in "<=/"
                and character not in ">/"
            ):
                compact.append(" ")
            pending_space = False
            compact.append(character)
    value = "".join(compact)
    if not value.endswith("/>"):
        value = re.sub(
            r"""=(["'])([A-Za-z0-9._:/?#%+@,;~&()\-]+)\1""",
            lambda match: (
                f"={match.group(2)}"
                if SAFE_UNQUOTED_RE.fullmatch(match.group(2))
                else match.group(0)
            ),
            value,
        )
    return value


def _shorten_internal_urls(raw: str, tag_name: str) -> str:
    if SITE + "/" not in raw or tag_name not in URL_SHORTEN_TAGS:
        return raw
    attrs = _raw_attributes(raw)
    relations = {
        value.lower() for value in attrs.get("rel", "").split()
    }
    if tag_name == "link" and "canonical" in relations:
        return raw
    if tag_name == "meta":
        return raw
    return raw.replace(SITE + "/", SITE_PATH)


def _replace_attribute_value(
    raw: str,
    attribute: str,
    value: str,
) -> str:
    for match in ATTR_RE.finditer(raw):
        if match.group(1).lower() != attribute.lower():
            continue
        for group in (2, 3, 4):
            if match.group(group) is None:
                continue
            escaped = html.escape(
                value,
                quote=group in {2, 3},
            )
            return raw[: match.start(group)] + escaped + raw[match.end(group) :]
    return raw


def rewrite_missing_markdown_links(
    source: str,
    *,
    relative: str,
    published_paths: set[str],
    authorized_missing_paths: set[str],
) -> tuple[str, int]:
    output: list[str] = []
    position = 0
    rewrites = 0
    while True:
        match = re.search(r"<a(?=[\s/>])", source[position:], re.I)
        if match is None:
            output.append(source[position:])
            break
        start = position + match.start()
        end = _find_tag_end(source, start)
        raw = source[start:end]
        attrs = _raw_attributes(raw)
        href = attrs.get("href", "")
        target = internal_path(href, document_url(relative)) if href else None
        replacement = None
        if (
            target is not None
            and target not in published_paths
            and target in authorized_missing_paths
            and target.lower().endswith(".md")
        ):
            html_target = f"{target[:-3]}.html"
            if html_target in published_paths:
                resolved = urllib.parse.urlsplit(
                    _resolved_url(href, document_url(relative))
                )
                replacement = (
                    f"{SITE_PATH}{urllib.parse.quote(html_target, safe='/')}"
                )
                if resolved.query:
                    replacement += f"?{resolved.query}"
                if resolved.fragment:
                    replacement += f"#{resolved.fragment}"
        output.append(source[position:start])
        if replacement is None:
            output.append(raw)
        else:
            output.append(_replace_attribute_value(raw, "href", replacement))
            rewrites += 1
        position = end
    return "".join(output), rewrites


def remove_missing_markdown_alternates(
    source: str,
    *,
    relative: str,
    published_paths: set[str],
    authorized_missing_paths: set[str],
) -> tuple[str, int]:
    output: list[str] = []
    position = 0
    removed = 0
    while True:
        match = re.search(r"<link(?=[\s/>])", source[position:], re.I)
        if match is None:
            output.append(source[position:])
            break
        start = position + match.start()
        end = _find_tag_end(source, start)
        raw = source[start:end]
        attrs = _raw_attributes(raw)
        relations = {
            item.lower() for item in attrs.get("rel", "").split()
        }
        media_type = attrs.get("type", "").split(";", 1)[0].strip().lower()
        href = attrs.get("href", "")
        target = internal_path(href, document_url(relative)) if href else None
        prune = (
            "alternate" in relations
            and media_type in {"text/markdown", "text/x-markdown"}
            and target is not None
            and target not in published_paths
            and target in authorized_missing_paths
        )
        output.append(source[position:start])
        if prune:
            removed += 1
        else:
            output.append(raw)
        position = end
    return "".join(output), removed


def _json_script(body: str) -> str:
    try:
        value = json.loads(
            body,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise StageError("Invalid JSON-LD in published HTML") from error
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    rendered = (
        rendered.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return rendered


def _json_ld_loader(content: bytes) -> bytes:
    literal = json.dumps(content.decode("utf-8"), ensure_ascii=False)
    return (
        "(()=>{const n=document.createElement(\"script\");"
        'n.type="application/ld+json";'
        f"n.textContent={literal};"
        "document.currentScript.before(n)})();\n"
    ).encode("utf-8")


def collect_json_ld_assets(
    files: list[SourceFile],
) -> tuple[dict[str, str], dict[str, bytes], dict[str, bytes]]:
    records: dict[str, dict[str, object]] = {}
    for item in files:
        if (
            PurePosixPath(item.path).suffix.lower() not in HTML_SUFFIXES
            or item.path.startswith(BYTE_STABLE_PREFIXES)
        ):
            continue
        try:
            source = item.source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise StageError(f"Cannot read HTML JSON-LD: {item.path}") from error
        for match in SCRIPT_BLOCK_RE.finditer(source):
            attrs_text = match.group("attrs")
            attrs = _raw_attributes(f"<script{attrs_text}>")
            if attrs != {"type": "application/ld+json"}:
                continue
            if re.fullmatch(
                r"""\s+type\s*=\s*(?:"application/ld\+json"|'application/ld\+json'|application/ld\+json)\s*""",
                attrs_text,
                re.I,
            ) is None:
                continue
            canonical = _json_script(match.group("body")).encode("utf-8")
            digest = sha256_bytes(canonical)
            record = records.setdefault(
                digest,
                {
                    "content": canonical,
                    "count": 0,
                    "source_bytes": 0,
                },
            )
            if record["content"] != canonical:
                raise StageError("JSON-LD content-address collision")
            record["count"] = int(record["count"]) + 1
            record["source_bytes"] = int(record["source_bytes"]) + len(
                match.group(0).encode("utf-8")
            )
    links: dict[str, str] = {}
    loader_assets: dict[str, bytes] = {}
    json_assets: dict[str, bytes] = {}
    for digest, record in sorted(records.items()):
        content = record["content"]
        assert isinstance(content, bytes)
        relative = f"{JSONLD_JS_PREFIX}{digest}.js"
        link = f"<script src={SITE_PATH}{relative}></script>"
        loader = _json_ld_loader(content)
        if int(record["source_bytes"]) <= (
            int(record["count"]) * len(link.encode("utf-8"))
            + len(loader)
        ):
            continue
        links[digest] = link
        loader_assets[relative] = loader
        json_assets[relative] = content
    return links, loader_assets, json_assets


def _merge_json_ld_scripts(source: str) -> str:
    matches = list(SCRIPT_BLOCK_RE.finditer(source))
    groups: dict[bytes, list[tuple[int, object]]] = {}
    for index, match in enumerate(matches):
        attrs = _raw_attributes(f"<script{match.group('attrs')}>")
        if attrs != {"type": "application/ld+json"}:
            continue
        try:
            value = json.loads(
                match.group("body"),
                object_pairs_hook=_object_without_duplicate_keys,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise StageError("Invalid JSON-LD after HTML minification") from error
        context = value.get("@context") if isinstance(value, dict) else None
        key = canonical_json(context)
        groups.setdefault(key, []).append((index, value))
    replacements: dict[int, str] = {}
    for items in groups.values():
        if len(items) < 2:
            continue
        context = (
            items[0][1].get("@context")
            if isinstance(items[0][1], dict)
            else None
        )
        graph: list[object] = []
        for _index, value in items:
            if isinstance(value, dict):
                material = {
                    key: item
                    for key, item in value.items()
                    if key != "@context"
                }
                if set(material) == {"@graph"} and isinstance(
                    material["@graph"], list
                ):
                    graph.extend(material["@graph"])
                else:
                    graph.append(material)
            elif isinstance(value, list):
                graph.extend(value)
            else:
                graph.append(value)
        merged: dict[str, object] = {"@graph": graph}
        if context is not None:
            merged = {"@context": context, **merged}
        first = items[0][0]
        replacements[first] = (
            "<script type=application/ld+json>"
            + _json_script(json.dumps(merged, ensure_ascii=False))
            + "</script>"
        )
        for index, _value in items[1:]:
            replacements[index] = ""
    if not replacements:
        return source
    output: list[str] = []
    position = 0
    for index, match in enumerate(matches):
        output.append(source[position : match.start()])
        output.append(replacements.get(index, match.group(0)))
        position = match.end()
    output.append(source[position:])
    return "".join(output)


def minify_html(
    content: bytes,
    *,
    relative: str,
    css_assets: dict[str, bytes],
    json_ld_links: dict[str, str] | None = None,
    neutralized_paths: set[str] | None = None,
) -> bytes:
    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise StageError(f"HTML is not UTF-8: {relative}") from error
    output: list[str] = []
    position = 0
    preserve_depth = 0
    anchor_rewrites: list[bool] = []
    while position < len(source):
        start = source.find("<", position)
        if start < 0:
            text = source[position:]
            output.append(
                text if preserve_depth else WHITESPACE_RE.sub(" ", text)
            )
            break
        text = source[position:start]
        output.append(
            text if preserve_depth else WHITESPACE_RE.sub(" ", text)
        )
        if source.startswith("<!--", start):
            end = source.find("-->", start + 4)
            if end < 0:
                raise StageError(f"Unterminated HTML comment: {relative}")
            comment = source[start + 4 : end]
            if KEEP_COMMENT_RE.search(comment):
                output.append(source[start : end + 3])
            position = end + 3
            continue
        if start + 1 >= len(source) or source[start + 1] not in (
            "!/?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        ):
            output.append("<")
            position = start + 1
            continue
        end = _find_tag_end(source, start)
        raw = source[start:end]
        end_match = END_TAG_RE.match(raw)
        if end_match:
            tag_name = end_match.group(1).lower()
            if tag_name == "a" and anchor_rewrites:
                output.append(
                    "</span>" if anchor_rewrites.pop() else _minify_tag(raw)
                )
                position = end
                continue
            if tag_name in PRESERVE_TEXT_TAGS and preserve_depth:
                preserve_depth -= 1
            output.append(_minify_tag(raw))
            position = end
            continue
        start_match = START_TAG_RE.match(raw)
        if start_match is None:
            output.append(raw)
            position = end
            continue
        tag_name = start_match.group(1).lower()
        attrs = _raw_attributes(raw)
        self_closing = raw.rstrip().endswith("/>")
        if tag_name == "a":
            href = attrs.get("href", "")
            target = internal_path(href, document_url(relative)) if href else None
            rewrite = (
                neutralized_paths is not None
                and target is not None
                and target in neutralized_paths
            )
            anchor_rewrites.append(rewrite)
            if rewrite:
                output.append("<span>")
                position = end
                continue
        if tag_name in {"style", "script"} and not self_closing:
            close_match = re.search(
                rf"</\s*{re.escape(tag_name)}\s*>",
                source[end:],
                re.I,
            )
            if close_match is None:
                raise StageError(f"Unclosed {tag_name} element: {relative}")
            close_start = end + close_match.start()
            close_end = end + close_match.end()
            body = source[end:close_start]
            if tag_name == "style":
                movable = (
                    not attrs
                    and re.search(r"(?:url\s*\(|@import\b)", body, re.I)
                    is None
                )
                if movable:
                    css = body.encode("utf-8")
                    digest = sha256_bytes(css)
                    asset = f"{CSS_PREFIX}{digest}.css"
                    previous = css_assets.setdefault(asset, css)
                    if previous != css:
                        raise StageError("Stylesheet content-address collision")
                    output.append(
                        "<link rel=stylesheet "
                        f"href={SITE_PATH}{asset}>"
                    )
                else:
                    output.append(_minify_tag(raw))
                    output.append(body)
                    output.append(_minify_tag(source[close_start:close_end]))
            elif attrs.get("type", "").lower() == "application/ld+json":
                canonical = _json_script(body)
                replacement = (json_ld_links or {}).get(
                    sha256_bytes(canonical.encode("utf-8"))
                )
                if replacement is not None:
                    output.append(replacement)
                else:
                    output.append(_minify_tag(raw))
                    output.append(canonical)
                    output.append(_minify_tag(source[close_start:close_end]))
            else:
                output.append(
                    _minify_tag(_shorten_internal_urls(raw, tag_name))
                )
                output.append(body)
                output.append(_minify_tag(source[close_start:close_end]))
            position = close_end
            continue
        if tag_name == "link" and is_html_hreflang(attrs):
            position = end
            continue
        shortened = _shorten_internal_urls(raw, tag_name)
        output.append(_minify_tag(shortened))
        if (
            tag_name in PRESERVE_TEXT_TAGS
            and not self_closing
            and tag_name not in VOID_TAGS
        ):
            preserve_depth += 1
        position = end
    return _merge_json_ld_scripts("".join(output)).strip().encode("utf-8") + b"\n"


def minify_json(content: bytes, *, relative: str) -> bytes:
    try:
        value = json.loads(
            content,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise StageError(f"Invalid published JSON: {relative}") from error
    return canonical_json(value)


class HreflangWriter:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.body = bytearray()
        self.entry_count = 0
        self.relation_count = 0
        self.shards: list[dict[str, object]] = []
        self.expected: dict[str, tuple[tuple[str, str], ...]] = {}

    def add(
        self,
        *,
        page_url: str,
        values: tuple[tuple[str, str], ...],
    ) -> None:
        if not values:
            return
        if page_url in self.expected:
            raise StageError(f"Duplicate hreflang sitemap URL: {page_url}")
        languages: dict[str, str] = {}
        for language, target in values:
            previous = languages.setdefault(language, target)
            if previous != target:
                raise StageError(
                    f"Conflicting hreflang targets for {page_url}: {language}"
                )
        normalized = tuple(sorted(languages.items()))
        self.expected[page_url] = normalized
        parts = [
            "<url><loc>",
            html.escape(page_url, quote=False),
            "</loc>",
        ]
        for language, target in normalized:
            parts.extend(
                (
                    '<xhtml:link rel="alternate" hreflang="',
                    html.escape(language, quote=True),
                    '" href="',
                    html.escape(target, quote=True),
                    '"/>',
                )
            )
        parts.append("</url>")
        entry = "".join(parts).encode("utf-8")
        if self.body and len(self.body) + len(entry) > HREFLANG_SHARD_LIMIT:
            self.flush()
        self.body.extend(entry)
        self.entry_count += 1
        self.relation_count += len(normalized)

    def flush(self) -> None:
        if not self.body:
            return
        payload = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            b'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            + bytes(self.body)
            + b"</urlset>\n"
        )
        digest = sha256_bytes(payload)
        relative = (
            f"{HREFLANG_PREFIX}{len(self.shards):03d}-{digest[:20]}.xml.gz"
        )
        compressed = deterministic_gzip(payload)
        target = self.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(compressed)
        self.shards.append(
            {
                "bytes": len(compressed),
                "path": relative,
                "sha256": sha256_bytes(compressed),
                "uncompressed_bytes": len(payload),
            }
        )
        self.body.clear()

    def finish(self) -> list[dict[str, object]]:
        self.flush()
        return self.shards


def _inject_sitemap_index(
    path: Path,
    shard_paths: Iterable[str],
) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise StageError(f"Cannot read sitemap index: {path}") from error
    if HREFLANG_PREFIX in source:
        raise StageError("Sitemap index already contains staging hreflang shards")
    marker = "</sitemapindex>"
    index = source.lower().rfind(marker)
    if index < 0:
        raise StageError("Published sitemap_index.xml is not a sitemap index")
    entries = "".join(
        "<sitemap><loc>"
        f"{SITE}/{html.escape(relative, quote=False)}"
        "</loc></sitemap>"
        for relative in shard_paths
    )
    rendered = source[:index] + entries + source[index:]
    try:
        ET.fromstring(rendered)
    except ET.ParseError as error:
        raise StageError("Staged sitemap index is invalid XML") from error
    path.write_text(rendered, encoding="utf-8")


def _read_sitemap(path: Path) -> bytes:
    content = path.read_bytes()
    if path.name.endswith(".gz"):
        try:
            return gzip.decompress(content)
        except gzip.BadGzipFile as error:
            raise StageError(f"Invalid gzip sitemap: {path}") from error
    return content


def _collect_sitemap_graph(
    output: Path,
) -> tuple[set[str], set[str]]:
    pending = ["sitemap_index.xml"]
    seen: set[str] = set()
    public_urls: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in seen:
            continue
        seen.add(relative)
        path = output / relative
        if not path.is_file():
            raise StageError(f"Sitemap graph is missing: {relative}")
        try:
            root = ET.fromstring(_read_sitemap(path))
        except ET.ParseError as error:
            raise StageError(f"Invalid sitemap XML: {relative}") from error
        kind = root.tag.rsplit("}", 1)[-1]
        if kind == "sitemapindex":
            for sitemap in root:
                if sitemap.tag.rsplit("}", 1)[-1] != "sitemap":
                    continue
                location = next(
                    (
                        child
                        for child in sitemap
                        if child.tag.rsplit("}", 1)[-1] == "loc"
                    ),
                    None,
                )
                if location is None or not location.text:
                    raise StageError(f"Sitemap index entry lacks loc: {relative}")
                target = internal_path(
                    location.text.strip(),
                    document_url(relative),
                )
                if target is None:
                    raise StageError(
                        f"Sitemap index leaves the site: {relative}"
                    )
                pending.append(target)
        elif kind == "urlset":
            for url in root:
                if url.tag.rsplit("}", 1)[-1] != "url":
                    continue
                location = next(
                    (
                        child
                        for child in url
                        if child.tag.rsplit("}", 1)[-1] == "loc"
                    ),
                    None,
                )
                if location is None or not location.text:
                    raise StageError(f"Sitemap URL lacks loc: {relative}")
                public_urls.add(location.text.strip())
        else:
            raise StageError(f"Unsupported sitemap root in {relative}: {kind}")
    return seen, public_urls


def compress_child_sitemaps(
    output: Path,
    *,
    referenced_paths: set[str],
) -> tuple[dict[str, str], set[str], dict[str, int]]:
    before_paths, before_urls = _collect_sitemap_graph(output)
    before_bytes = sum((output / relative).stat().st_size for relative in before_paths)
    mapping: dict[str, str] = {}
    for relative in sorted(before_paths):
        if (
            relative in STABLE_SITEMAPS
            or relative in referenced_paths
            or not relative.endswith(".xml")
        ):
            continue
        content = (output / relative).read_bytes()
        compressed = deterministic_gzip(content)
        if len(compressed) + 32 < len(content):
            mapping[relative] = f"{relative}.gz"
    replacements = {
        f"{SITE}/{old}": f"{SITE}/{new}"
        for old, new in mapping.items()
    }
    rewritten: set[str] = set()
    row_mapping: dict[str, str] = {}
    for relative in sorted(before_paths):
        old_path = output / relative
        content = old_path.read_bytes()
        rendered = content
        if b"sitemapindex" in content.lower():
            for old_url, new_url in replacements.items():
                rendered = rendered.replace(
                    old_url.encode("utf-8"),
                    new_url.encode("utf-8"),
                )
        target_relative = mapping.get(relative, relative)
        target_path = output / target_relative
        if target_relative != relative:
            if target_path.exists():
                raise StageError(
                    f"Compressed sitemap path collision: {target_relative}"
                )
            rendered = deterministic_gzip(rendered)
            target_path.write_bytes(rendered)
            old_path.unlink()
            row_mapping[relative] = target_relative
        elif rendered != content:
            old_path.write_bytes(rendered)
            rewritten.add(relative)
    after_paths, after_urls = _collect_sitemap_graph(output)
    expected_paths = {
        mapping.get(relative, relative) for relative in before_paths
    }
    if after_paths != expected_paths or after_urls != before_urls:
        raise StageError("Sitemap gzip compaction changed the public URL graph")
    after_bytes = sum((output / relative).stat().st_size for relative in after_paths)
    return row_mapping, rewritten, {
        "compressed_files": len(mapping),
        "public_urls": len(after_urls),
        "referenced_files_retained": len(before_paths & referenced_paths),
        "saved_bytes": before_bytes - after_bytes,
    }


def _target_exists(relative: str, paths: set[str]) -> bool:
    if relative in paths:
        return True
    pure = PurePosixPath(relative)
    if pure.suffix:
        return False
    return (
        f"{relative}.html" in paths
        or f"{relative.rstrip('/')}/index.html" in paths
    )


def _validate_url(
    value: str,
    *,
    base_url: str,
    paths: set[str],
    context: str,
) -> None:
    relative = internal_path(value, base_url)
    if relative is not None and not _target_exists(relative, paths):
        raise StageError(
            f"Staged URL closure failed ({context}): {relative}"
        )


def _parse_hreflang_shards(
    output: Path,
    shards: list[dict[str, object]],
) -> dict[str, tuple[tuple[str, str], ...]]:
    result: dict[str, tuple[tuple[str, str], ...]] = {}
    for shard in shards:
        path = output / str(shard["path"])
        try:
            content = gzip.decompress(path.read_bytes())
            root = ET.fromstring(content)
        except (OSError, gzip.BadGzipFile, ET.ParseError) as error:
            raise StageError(f"Cannot parse hreflang shard: {path}") from error
        for item in root:
            loc = ""
            values: list[tuple[str, str]] = []
            for child in item:
                local = child.tag.rsplit("}", 1)[-1]
                if local == "loc":
                    loc = (child.text or "").strip()
                elif local == "link":
                    values.append(
                        (
                            child.attrib.get("hreflang", ""),
                            child.attrib.get("href", ""),
                        )
                    )
            if not loc or loc in result:
                raise StageError("Invalid or duplicate hreflang sitemap loc")
            result[loc] = tuple(sorted(values))
    return result


def validate_stage(
    output: Path,
    *,
    css_assets: dict[str, bytes],
    json_ld_assets: dict[str, bytes],
    expected_hreflang: dict[str, tuple[tuple[str, str], ...]],
    shards: list[dict[str, object]],
) -> dict[str, object]:
    paths: set[str] = set()
    inodes: dict[tuple[int, int], str] = {}
    files = 0
    unpacked_bytes = 0
    file_inventory = hashlib.sha256()
    for path in sorted(output.rglob("*")):
        relative = _relative(output, path)
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise StageError(f"Staged Pages tree contains symlink: {relative}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise StageError(
                f"Staged Pages tree contains special file: {relative}"
            )
        if metadata.st_nlink != 1:
            raise StageError(
                f"Staged Pages tree contains hard-linked file: {relative}"
            )
        inode = (metadata.st_dev, metadata.st_ino)
        if inode in inodes:
            raise StageError(
                f"Staged Pages tree aliases one inode: "
                f"{inodes[inode]}, {relative}"
            )
        inodes[inode] = relative
        paths.add(relative)
        files += 1
        unpacked_bytes += metadata.st_size
        digest = sha256_bytes(path.read_bytes())
        file_inventory.update(
            f"{relative}\0{metadata.st_size}\0{digest}\n".encode("utf-8")
        )
    parsed_hreflang = _parse_hreflang_shards(output, shards)
    if parsed_hreflang != expected_hreflang:
        raise StageError("Generated hreflang sitemap graph drift")
    html_files = 0
    inline_hreflang = 0
    semantic_root = hashlib.sha256()
    for relative in sorted(paths):
        if PurePosixPath(relative).suffix.lower() not in HTML_SUFFIXES:
            continue
        html_files += 1
        content = (output / relative).read_bytes()
        snapshot = parse_semantics(
            content,
            relative=relative,
            css_assets=css_assets,
            json_ld_assets=json_ld_assets,
        )
        if snapshot.hreflang:
            inline_hreflang += len(snapshot.hreflang)
        semantic_root.update(
            f"{relative}\0{snapshot.semantic_sha256}\n".encode("utf-8")
        )
        for value in snapshot.canonical:
            _validate_url(
                value,
                base_url=document_url(relative),
                paths=paths,
                context=f"{relative} canonical",
            )
        for _language, value in snapshot.hreflang:
            _validate_url(
                value,
                base_url=document_url(relative),
                paths=paths,
                context=f"{relative} hreflang",
            )
        for value in snapshot.internal_urls:
            _validate_url(
                value,
                base_url=document_url(relative),
                paths=paths,
                context=relative,
            )
    for page_url, values in expected_hreflang.items():
        for _language, target in values:
            _validate_url(
                target,
                base_url=page_url,
                paths=paths,
                context=f"{page_url} sitemap hreflang",
            )
    public_urls = set(expected_hreflang)
    feed_urls = 0
    for relative in sorted(paths):
        name = PurePosixPath(relative).name
        if (
            name in {"feed.json", "feed.xml", "rss.xml"}
            or name.endswith(".atom.xml")
        ):
            text = (output / relative).read_text(
                encoding="utf-8",
                errors="replace",
            )
            for value in re.findall(r"https?://[^\s<>'\"\\]+", text):
                value = value.rstrip(".,);]")
                _validate_url(
                    value,
                    base_url=document_url(relative),
                    paths=paths,
                    context=f"{relative} feed",
                )
                if internal_path(value, document_url(relative)) is not None:
                    feed_urls += 1
        if not name.startswith("sitemap") or not name.endswith(
            (".xml", ".xml.gz")
        ):
            continue
        try:
            root = ET.fromstring(_read_sitemap(output / relative))
        except ET.ParseError as error:
            raise StageError(f"Invalid staged sitemap XML: {relative}") from error
        for element in root.iter():
            local = element.tag.rsplit("}", 1)[-1]
            if local == "loc" and element.text:
                value = element.text.strip()
                _validate_url(
                    value,
                    base_url=document_url(relative),
                    paths=paths,
                    context=relative,
                )
                parsed = urllib.parse.urlsplit(value)
                if not parsed.path.endswith((".xml", ".xml.gz")):
                    public_urls.add(value)
            if local == "link" and element.attrib.get("href"):
                _validate_url(
                    element.attrib["href"],
                    base_url=document_url(relative),
                    paths=paths,
                    context=relative,
                )
    for locale in OFFICIAL_LOCALES:
        if not any(path.startswith(f"{locale}/") for path in paths):
            raise StageError(f"Staged Pages tree lost official locale: {locale}")
    return {
        "files": files,
        "feed_internal_urls": feed_urls,
        "file_inventory_sha256": file_inventory.hexdigest(),
        "html_files": html_files,
        "inline_hreflang_relations": inline_hreflang,
        "semantic_root_sha256": semantic_root.hexdigest(),
        "public_url_count": len(public_urls),
        "public_url_sha256": sha256_bytes(
            ("\n".join(sorted(public_urls)) + "\n").encode("utf-8")
        ),
        "unpacked_bytes": unpacked_bytes,
        "url_closure": "complete",
    }


def _write_file(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(mode)


def build_stage(
    source_root: Path,
    output_root: Path,
    *,
    max_unpacked_bytes: int = MAX_UNPACKED_BYTES,
) -> dict[str, object]:
    if max_unpacked_bytes <= 0:
        raise StageError("Pages unpacked byte limit must be positive")
    source, files, hash_tokens, noindex_paths = scan_source(source_root)
    published_paths = {
        item.path for item in files if item.path != SOURCE_INVENTORY
    }
    inventory_source = next(
        (item.source for item in files if item.path == SOURCE_INVENTORY),
        None,
    )
    if inventory_source is None:
        raise StageError("Pages staging source lacks publish inventory")
    try:
        source_inventory = json.loads(inventory_source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StageError("Pages source publish inventory is invalid") from error
    excluded = source_inventory.get("excluded")
    if not isinstance(excluded, list):
        raise StageError("Pages source publish inventory lacks exclusions")
    authorized_missing_paths = {
        str(item.get("path"))
        for item in excluded
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    output = _output_root(source, output_root)
    output.mkdir(parents=True, exist_ok=True)
    css_assets: dict[str, bytes] = {}
    json_ld_links, json_ld_loaders, json_ld_assets = collect_json_ld_assets(
        files
    )
    hreflang = HreflangWriter(output)
    rows: list[list[object]] = []
    semantic_before = hashlib.sha256()
    semantic_after = hashlib.sha256()
    source_bytes = sum(item.size for item in files)
    transformed_html = 0
    minified_json = 0
    removed_noindex_hreflang = 0
    removed_unpublished_hreflang = 0
    removed_markdown_alternates = 0
    rewritten_markdown_links = 0
    referenced_paths: set[str] = set()
    try:
        for item in files:
            target_relative = item.path
            transform = "copy"
            if item.path == SOURCE_INVENTORY:
                target_relative = SOURCE_INVENTORY_GZIP
                content = deterministic_gzip(item.source.read_bytes())
                transform = "gzip-source-inventory"
            elif (
                PurePosixPath(item.path).suffix.lower() in HTML_SUFFIXES
                and not item.path.startswith(BYTE_STABLE_PREFIXES)
            ):
                original = item.source.read_bytes()
                try:
                    original_text = original.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise StageError(
                        f"HTML is not UTF-8: {item.path}"
                    ) from error
                normalized_text, removed = remove_missing_markdown_alternates(
                    original_text,
                    relative=item.path,
                    published_paths=published_paths,
                    authorized_missing_paths=authorized_missing_paths,
                )
                normalized_text, rewrites = rewrite_missing_markdown_links(
                    normalized_text,
                    relative=item.path,
                    published_paths=published_paths,
                    authorized_missing_paths=authorized_missing_paths,
                )
                normalized = normalized_text.encode("utf-8")
                removed_markdown_alternates += removed
                rewritten_markdown_links += rewrites
                before = parse_semantics(
                    normalized,
                    relative=item.path,
                    css_assets={},
                    neutralized_paths=authorized_missing_paths,
                )
                content = minify_html(
                    normalized,
                    relative=item.path,
                    css_assets=css_assets,
                    json_ld_links=json_ld_links,
                    neutralized_paths=authorized_missing_paths,
                )
                after = parse_semantics(
                    content,
                    relative=item.path,
                    css_assets=css_assets,
                    json_ld_assets=json_ld_assets,
                )
                if (
                    before.dom_sha256 != after.dom_sha256
                    or before.canonical != after.canonical
                    or before.schema_sha256 != after.schema_sha256
                    or before.styles != after.styles
                ):
                    raise StageError(
                        f"HTML minification semantic drift: {item.path}"
                    )
                for value in after.internal_urls:
                    target_path = internal_path(
                        value,
                        document_url(item.path),
                    )
                    if target_path is not None:
                        referenced_paths.add(target_path)
                if after.hreflang:
                    raise StageError(
                        f"HTML hreflang migration incomplete: {item.path}"
                    )
                valid_hreflang_list: list[tuple[str, str]] = []
                for language, target in before.hreflang:
                    target_path = internal_path(
                        target,
                        document_url(item.path),
                    )
                    if (
                        item.path in noindex_paths
                        or target_path in noindex_paths
                    ):
                        removed_noindex_hreflang += 1
                        continue
                    if target_path in authorized_missing_paths:
                        removed_unpublished_hreflang += 1
                        continue
                    valid_hreflang_list.append((language, target))
                valid_hreflang = tuple(valid_hreflang_list)
                hreflang.add(
                    page_url=document_url(item.path),
                    values=valid_hreflang,
                )
                semantic_before.update(
                    f"{item.path}\0{before.semantic_sha256}\n".encode()
                )
                semantic_after.update(
                    f"{item.path}\0{after.semantic_sha256}\n".encode()
                )
                transformed_html += 1
                transform = "semantic-html-minify"
            elif (
                PurePosixPath(item.path).suffix.lower() in JSON_SUFFIXES
                and item.sha256.encode("ascii") not in hash_tokens
                and not item.path.startswith(BYTE_STABLE_PREFIXES)
            ):
                original = item.source.read_bytes()
                content = minify_json(original, relative=item.path)
                if json.loads(original) != json.loads(content):
                    raise StageError(
                        f"JSON minification semantic drift: {item.path}"
                    )
                minified_json += 1
                transform = "canonical-json"
            else:
                content = item.source.read_bytes()
            target = output / target_relative
            _write_file(target, content, item.mode)
            rows.append(
                [
                    target_relative,
                    item.sha256,
                    sha256_bytes(content),
                    len(content),
                    transform,
                ]
            )
        shards = hreflang.finish()
        for relative, content in sorted(css_assets.items()):
            target = output / relative
            if target.exists():
                raise StageError(f"Staged stylesheet path collision: {relative}")
            _write_file(target, content, 0o644)
            rows.append(
                [
                    relative,
                    None,
                    sha256_bytes(content),
                    len(content),
                    "content-addressed-css",
                ]
            )
        for relative, content in sorted(json_ld_loaders.items()):
            target = output / relative
            if target.exists():
                raise StageError(f"Staged JSON-LD path collision: {relative}")
            _write_file(target, content, 0o644)
            rows.append(
                [
                    relative,
                    None,
                    sha256_bytes(content),
                    len(content),
                    "content-addressed-jsonld-loader",
                ]
            )
        for shard in shards:
            relative = str(shard["path"])
            content = (output / relative).read_bytes()
            rows.append(
                [
                    relative,
                    None,
                    sha256_bytes(content),
                    len(content),
                    "gzip-hreflang-sitemap",
                ]
            )
        sitemap_mapping, rewritten_sitemaps, sitemap_stats = (
            compress_child_sitemaps(
                output,
                referenced_paths=referenced_paths,
            )
        )
        row_by_path = {str(row[0]): row for row in rows}
        for old, new in sitemap_mapping.items():
            row = row_by_path.pop(old)
            content = (output / new).read_bytes()
            row[0] = new
            row[2] = sha256_bytes(content)
            row[3] = len(content)
            row[4] = f"gzip-sitemap:{old}"
            row_by_path[new] = row
        for relative in rewritten_sitemaps:
            row = row_by_path[relative]
            content = (output / relative).read_bytes()
            row[2] = sha256_bytes(content)
            row[3] = len(content)
            row[4] = "rewrite-sitemap-children"
        rows = list(row_by_path.values())
        sitemap_index = output / "sitemap_index.xml"
        if not sitemap_index.is_file():
            raise StageError("Staged Pages tree lacks sitemap_index.xml")
        _inject_sitemap_index(
            sitemap_index,
            (str(shard["path"]) for shard in shards),
        )
        for row in rows:
            if row[0] == "sitemap_index.xml":
                content = sitemap_index.read_bytes()
                row[2] = sha256_bytes(content)
                row[3] = len(content)
                row[4] = "append-hreflang-sitemaps"
                break
        validation = validate_stage(
            output,
            css_assets=css_assets,
            json_ld_assets=json_ld_assets,
            expected_hreflang=hreflang.expected,
            shards=shards,
        )
        source_inventory_row = next(
            row for row in rows if row[0] == SOURCE_INVENTORY_GZIP
        )
        manifest = {
            "digest_encoding": "sha256-base64url-no-padding",
            "equivalence": {
                "after_sha256": semantic_after.hexdigest(),
                "before_sha256": semantic_before.hexdigest(),
                "canonical": "equivalent",
                "dom_key_content": "equivalent",
                "hreflang": "migrated_to_gzip_sitemaps",
                "json_ld": "equivalent",
                "styles": "content_addressed_equivalent",
                "url_closure": validation["url_closure"],
            },
            "files": [
                [
                    row[0],
                    digest_base64url(row[1]),
                    digest_base64url(row[2]),
                    row[3],
                    row[4],
                ]
                for row in sorted(rows, key=lambda row: str(row[0]))
            ],
            "hreflang": {
                "pages": len(hreflang.expected),
                "relations": hreflang.relation_count,
                "removed_noindex_relations": removed_noindex_hreflang,
                "removed_unpublished_relations": (
                    removed_unpublished_hreflang
                ),
                "shards": shards,
            },
            "limits": {
                "max_unpacked_bytes": max_unpacked_bytes,
            },
            "minification": {
                "content_addressed_css_assets": len(css_assets),
                "content_addressed_jsonld_assets": len(json_ld_loaders),
                "json_files": minified_json,
                "missing_markdown_alternates_removed": (
                    removed_markdown_alternates
                ),
                "markdown_links_rewritten_to_html": rewritten_markdown_links,
                "transformed_html_files": transformed_html,
            },
            "sitemaps": sitemap_stats,
            "schema": "lumi.pages-stage/v1",
            "source": {
                "files": len(files),
                "unpacked_bytes": source_bytes,
            },
            "source_inventory": {
                "source_path": SOURCE_INVENTORY,
                "source_sha256": source_inventory_row[1],
                "staged_path": SOURCE_INVENTORY_GZIP,
                "staged_sha256": source_inventory_row[2],
            },
            "staged_content": validation,
        }
        if semantic_before.digest() != semantic_after.digest():
            raise StageError("HTML semantic root drift")
        manifest_bytes = deterministic_gzip(canonical_json(manifest))
        manifest_path = output / STAGE_MANIFEST
        _write_file(manifest_path, manifest_bytes, 0o644)
        final = validate_stage(
            output,
            css_assets=css_assets,
            json_ld_assets=json_ld_assets,
            expected_hreflang=hreflang.expected,
            shards=shards,
        )
        final_bytes = int(final["unpacked_bytes"])
        if final_bytes > max_unpacked_bytes:
            raise StageError(
                "Final Pages staging unpacked regular-file bytes exceed "
                f"{max_unpacked_bytes}: {final_bytes}"
            )
        result = {
            **final,
            "max_unpacked_bytes": max_unpacked_bytes,
            "source_unpacked_bytes": source_bytes,
            "stage_manifest_bytes": len(manifest_bytes),
            "stage_manifest_sha256": sha256_bytes(manifest_bytes),
        }
        return result
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--max-unpacked-bytes",
        type=int,
        default=MAX_UNPACKED_BYTES,
    )
    args = parser.parse_args()
    try:
        result = build_stage(
            args.source,
            args.output,
            max_unpacked_bytes=args.max_unpacked_bytes,
        )
    except StageError as error:
        print(str(error), file=sys.stderr)
        return 1
    print("PAGES_STAGE " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
