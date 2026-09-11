#!/usr/bin/env python3
"""Publish only evidenced, native-language result images; never create imagery."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

from PIL import Image, UnidentifiedImageError

import image_transport_evidence as image_transport
from crawler_policy import RobotsPolicy
from deployment_generation import GenerationError, parse_json, validate_binding, verify_output_bytes
from image_transport_evidence import (
    APPLE_COMMENT_TRANSFORM, CORRELATION, canonical_asset_bytes, decode_content,
    pixel_evidence, verify_decoded_evidence,
)
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "data/result_image_evidence_v1.json"
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITEMAP = "sitemap_result_images.xml"
COVERAGE = "data/result-image-coverage.json"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"
READY = "VERIFIED_PUBLIC_IMAGE"
BLOCKED = "BLOCKED_EVIDENCE"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_ROBOTS_BYTES = 512 * 1024
PUBLIC_ASSET_HOSTS = frozenset({"is1-ssl.mzstatic.com"})
COPY_FIELDS = ("alt", "caption", "nearby_text", "limitation")
PARAMETER_DIRECTIVES = frozenset({
    "max-snippet", "max-image-preview", "max-video-preview", "unavailable_after",
})
LABEL_FIELDS = (
    "title", "intro", "source_label", "store_label", "unavailable", "home_label"
)
FORBIDDEN_FIELDS = frozenset({
    "aggregateRating", "ratingValue", "ratingCount", "reviewCount",
    "customer_reviews", "customerReviews", "reviews",
})
SCRIPT_RANGES = {
    "ar": r"[\u0600-\u06ff]", "ur": r"[\u0600-\u06ff]",
    "he": r"[\u0590-\u05ff]", "bn": r"[\u0980-\u09ff]",
    "gu": r"[\u0a80-\u0aff]", "hi": r"[\u0900-\u097f]",
    "mr": r"[\u0900-\u097f]", "kn": r"[\u0c80-\u0cff]",
    "ml": r"[\u0d00-\u0d7f]", "or": r"[\u0b00-\u0b7f]",
    "pa": r"[\u0a00-\u0a7f]", "ta": r"[\u0b80-\u0bff]",
    "te": r"[\u0c00-\u0c7f]", "th": r"[\u0e00-\u0e7f]",
    "ja": r"[\u3040-\u30ff\u4e00-\u9fff]",
    "zh": r"[\u4e00-\u9fff]", "ko": r"[\uac00-\ud7af]",
    "ru": r"[\u0400-\u04ff]", "uk": r"[\u0400-\u04ff]",
    "el": r"[\u0370-\u03ff]",
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def copy_digest(value: dict, fields: tuple[str, ...] = COPY_FIELDS) -> str:
    return digest(canonical_json({field: value[field] for field in fields}).encode())


def gallery_path(locale: str) -> str:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Noncanonical locale: {locale}")
    return f"{locale}/results/index.html"


def gallery_url(locale: str, site: str) -> str:
    return f"{site}/{gallery_path(locale).removesuffix('index.html')}"


def _url(value: object, *, hosts: set[str] | frozenset[str] | None = None) -> str:
    if not isinstance(value, str):
        raise ValueError("A public absolute URL is required")
    parts = urlsplit(value)
    if (
        parts.scheme != "https" or not parts.hostname or parts.username
        or parts.password or parts.port not in (None, 443)
        or parts.query or parts.fragment or "\\" in value
        or any(c.isspace() for c in value)
        or "/../" in f"/{unquote(parts.path)}/"
        or (hosts is not None and parts.hostname not in hosts)
    ):
        raise ValueError(f"Not an approved canonical public URL: {value}")
    return value


def _no_ratings(value: object) -> None:
    if isinstance(value, dict):
        if FORBIDDEN_FIELDS.intersection(value):
            raise ValueError("Apple reviews and rating claims are not image evidence")
        for child in value.values():
            _no_ratings(child)
    elif isinstance(value, list):
        for child in value:
            _no_ratings(child)


def _native_copy(value: dict, locale: str, fields: tuple[str, ...]) -> None:
    for field in fields:
        text = value.get(field)
        if (
            not isinstance(text, str) or not text.strip()
            or text != text.strip() or "\n" in text
            or re.search(r"\b(lorem ipsum|placeholder|test fixture)\b", text, re.I)
        ):
            raise ValueError(f"{locale}: missing real native {field}")
        script = SCRIPT_RANGES.get(locale.split("-")[0])
        if script and not re.search(script, text):
            raise ValueError(f"{locale}: {field} lacks its native script")
    review = value.get("native_review", {})
    if (
        review.get("locale") != locale
        or review.get("copy_sha256") != copy_digest(value, fields)
        or not review.get("review_ref")
    ):
        raise ValueError(f"{locale}: native copy review is missing or stale")


def validate_manifest(manifest: dict) -> None:
    _no_ratings(manifest)
    if manifest.get("schema_version") != 2 or manifest.get("scope") != "public_result_images_only":
        raise ValueError("Unsupported result-image evidence contract")
    if manifest.get("expected_locales") != list(OFFICIAL_LOCALES):
        raise ValueError("Expected locales must be the exact official 50")
    apps = manifest.get("apps", [])
    keys = [app["key"] for app in apps]
    ids = [app["app_id"] for app in apps]
    if len(set(keys)) != len(keys) or len(set(ids)) != len(ids):
        raise ValueError("Duplicate app identity")
    families = Counter(app["family"] for app in apps)
    if families != {"photo6": 6, "kids14": 14, "scanner_pdf2": 2, "notes_onepage": 2}:
        raise ValueError("Priority inventory must cover photo6, Kids14, scanner/PDF2, Notes/OnePage")
    for app in apps:
        if not re.fullmatch(r"[a-z0-9]+", app["key"]) or not re.fullmatch(r"\d{9,12}", app["app_id"]):
            raise ValueError("Invalid app identity")
        if not app.get("missing_evidence"):
            raise ValueError("Missing evidence must have a specific reason")
    labels = manifest.get("labels", {})
    for locale, value in labels.items():
        if locale not in OFFICIAL_LOCALES:
            raise ValueError("Unexpected labels locale")
        _native_copy(value, locale, LABEL_FIELDS)
    approved = manifest.get("images", [])
    image_ids: set[str] = set()
    hashes: dict[str, str] = {}
    urls: set[str] = set()
    copies: dict[tuple[str, str], str] = {}
    for asset in approved:
        identifier = asset["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier) or identifier in image_ids:
            raise ValueError("Duplicate or invalid image identity")
        image_ids.add(identifier)
        if asset["app_key"] not in keys:
            raise ValueError("Image refers to an unlisted app")
        if asset.get("kind") != "published_app_result" or asset.get("status") != "APPROVED_PUBLIC":
            raise ValueError("Fixtures, posters and synthetic cards are not real result images")
        url = _url(asset["canonical_asset_url"], hosts=PUBLIC_ASSET_HOSTS)
        sha = asset["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("A byte-exact SHA-256 is required")
        if sha in hashes or url in urls:
            raise ValueError("Duplicate bytes or canonical URL; reuse the same image record")
        hashes[sha] = url
        urls.add(url)
        if any(type(asset.get(d)) is not int or asset[d] <= 0 for d in ("width", "height")):
            raise ValueError("Explicit positive image width and height are required")
        if asset["width"] * asset["height"] > 20_000_000:
            raise ValueError("Result image exceeds the bounded decode size")
        evidence = asset.get("evidence", {})
        app = apps[keys.index(asset["app_key"])]
        if evidence.get("app_store_url") != f"https://apps.apple.com/us/app/id{app['app_id']}":
            raise ValueError("Public approval is not bound to the exact app")
        if (
            evidence.get("source_sha256") != sha
            or evidence.get("rights_status") != "FIRST_PARTY_INTERFACE_REVIEWED"
            or evidence.get("result_status") != "VISIBLE_PUBLISHED_RESULT_ONLY"
            or not evidence.get("rights_basis")
            or not evidence.get("review_ref")
            or not evidence.get("published_version")
        ):
            raise ValueError("Publication, rights or visible-result proof is missing")
        decoded = asset.get("decoded_evidence")
        decoded_fields = {
            "format", "mode", "width", "height", "pixel_algorithm", "pixels_sha256",
            "rgb_sha256", "exif_sha256", "icc_sha256", "orientation",
        }
        if (
            not isinstance(decoded, dict) or set(decoded) != decoded_fields
            or decoded["pixel_algorithm"] != "sha256-rgba8-dimensions-v1"
            or any(type(decoded[key]) is not int or decoded[key] != asset[key]
                   for key in ("width", "height"))
            or type(decoded["orientation"]) is not int or decoded["orientation"] not in range(1, 9)
            or any(re.fullmatch(r"[0-9a-f]{64}", str(decoded[key])) is None
                   for key in ("pixels_sha256", "rgb_sha256", "exif_sha256", "icc_sha256"))
            or not isinstance(decoded["format"], str) or not isinstance(decoded["mode"], str)
        ):
            raise ValueError("Explicit source-bound decoded pixel and dimension evidence is required")
        reversal = asset.get("transport_reversal")
        if reversal is not None and (
            not isinstance(reversal, dict)
            or set(reversal) != {"algorithm", "source_correlation_key", "comment_offset", "evidence_ref"}
            or reversal["algorithm"] != APPLE_COMMENT_TRANSFORM
            or CORRELATION.fullmatch(str(reversal["source_correlation_key"])) is None
            or type(reversal["comment_offset"]) is not int or reversal["comment_offset"] < 8
            or not reversal["evidence_ref"] or decoded["format"] != "JPEG"
        ):
            raise ValueError("Invalid source-bound reversible CDN transport")
        if date.fromisoformat(evidence["reviewed_on"]) > date.today():
            raise ValueError("Future image evidence")
        if type(asset.get("contains_text")) is not bool:
            raise ValueError("Image text presence must be explicitly reviewed")
        if asset["contains_text"]:
            if asset.get("content_locale") not in OFFICIAL_LOCALES:
                raise ValueError("Text-bearing images need their actual native locale")
        elif not evidence.get("textless_review_ref"):
            raise ValueError("Cross-locale reuse needs an affirmative textless review")
        localizations = asset.get("localizations", {})
        if not localizations:
            raise ValueError("Images cannot publish without native copy")
        for locale, copy in localizations.items():
            if locale not in labels:
                raise ValueError(f"{locale}: missing reviewed native page labels")
            if asset["contains_text"] and locale != asset["content_locale"]:
                raise ValueError("Text-bearing images cannot be reused across locales")
            _native_copy(copy, locale, COPY_FIELDS)
            for field in ("alt", "caption", "nearby_text"):
                fingerprint = (field, re.sub(r"\s+", " ", copy[field]).casefold())
                other = copies.get(fingerprint)
                if other and other != locale:
                    raise ValueError("Shared cross-locale copy is not native coverage")
                copies[fingerprint] = locale
    for rejected in manifest.get("rejected_candidates", []):
        if rejected.get("status") != BLOCKED or not rejected.get("reason"):
            raise ValueError("Rejected candidates must remain explicitly BLOCKED_EVIDENCE")
        if rejected["id"] in image_ids:
            raise ValueError("A blocked image cannot also be approved")
    for claim in manifest.get("unproven_claims", []):
        if (
            claim.get("status") != BLOCKED or claim.get("app_key") not in keys
            or not isinstance(claim.get("claim"), str) or not claim["claim"].strip()
        ):
            raise ValueError("Unproven result claims must remain BLOCKED_EVIDENCE")
    label_copies: dict[tuple[str, str], str] = {}
    for locale, value in labels.items():
        for field in ("title", "intro", "unavailable", "home_label"):
            key = (field, value[field].casefold())
            other = label_copies.get(key)
            if other and other.split("-")[0] != locale.split("-")[0]:
                raise ValueError("Shared cross-locale page copy is not native coverage")
            label_copies[key] = locale


@dataclass(frozen=True)
class Response:
    status: int
    url: str
    headers: dict[str, str | tuple[str, ...]]
    body: bytes


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, limit: int) -> Response:
    request = Request(url, headers={
        "User-Agent": "Lumi-Public-Image-Check/1.0", "Accept-Encoding": "identity",
    })
    opener = build_opener(_NoRedirect())
    for attempt in range(3):
        try:
            response = opener.open(request, timeout=20)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ValueError("public GET unavailable") from None
            time.sleep(2 ** attempt)
            continue
        with response:
            body = response.read(limit + 1)
            status = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
            headers["x-robots-tag"] = tuple(response.headers.get_all("X-Robots-Tag", []))
            for name in ("content-encoding", "x-correlation-key", "x-apple-jingle-correlation-key"):
                values = response.headers.get_all(name, [])
                if values:
                    headers[name] = ", ".join(values)
            result = Response(
                status, response.geturl(), headers, body,
            )
        if len(body) > limit:
            raise ValueError("public response exceeds the bounded size limit")
        if status != 429 and status < 500:
            return result
        if attempt < 2:
            time.sleep(2 ** attempt)
    return result


def robots_allowed(body: str, url: str, agent: str) -> bool:
    """Share the canonical crawler parser, including wildcard/end-anchor priority."""
    parts = urlsplit(url)
    return RobotsPolicy(body).allowed(
        agent, url, f"{parts.scheme}://{parts.netloc}/robots.txt",
    )


def _header_blocks(value: str | tuple[str, ...], agent: str) -> bool:
    if not isinstance(value, str):
        return any(_header_blocks(field, agent) for field in value)
    # A bot-specific directive must not accidentally block unrelated crawlers.
    current_agent = "*"
    for token in value.lower().split(","):
        token = token.strip()
        if ":" in token and token.split(":", 1)[0].strip() not in PARAMETER_DIRECTIVES:
            current_agent, token = (part.strip() for part in token.split(":", 1))
        token = re.sub(
            r"\b(max-snippet|max-image-preview|max-video-preview)\s*:\s*",
            r"\1:", token,
        )
        applies = current_agent == "*" or current_agent in agent.lower()
        if applies and (
            set(token.split()).intersection({"noindex", "noimageindex", "none"})
            or token.startswith("unavailable_after:")
        ):
            return True
    return False


class PublicVerifier:
    def __init__(self, transport: Callable[[str, int], Response] = fetch):
        self.transport = transport
        self.robots: dict[str, Response] = {}

    def crawlable(self, url: str, agent: str) -> None:
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        if robots_url not in self.robots:
            self.robots[robots_url] = self.transport(robots_url, MAX_ROBOTS_BYTES)
        response = self.robots[robots_url]
        # Google treats 4xx other than 429 as an absent robots file.
        if 400 <= response.status < 500 and response.status != 429:
            return
        if response.status != 200 or response.url != robots_url:
            raise ValueError("authoritative origin robots is unavailable")
        if not robots_allowed(response.body.decode("utf-8-sig"), url, agent):
            raise ValueError(f"authoritative robots disallows {agent}")

    def image(self, asset: dict) -> dict:
        url = asset["canonical_asset_url"]
        self.crawlable(url, "Googlebot-Image")
        response = self.transport(url, MAX_IMAGE_BYTES)
        if response.status != 200 or response.url != url:
            raise ValueError("canonical image does not return a direct HTTP 200")
        if any(_header_blocks(response.headers.get("x-robots-tag", ""), agent)
               for agent in ("Googlebot", "Googlebot-Image")):
            raise ValueError("image X-Robots-Tag prevents indexing")
        entity = decode_content(response.body, response.headers.get("content-encoding", ""))
        canonical, reversal = canonical_asset_bytes(entity, asset, response.headers)
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if not media_type.startswith("image/"):
            raise ValueError("public asset is not served as an image")
        try:
            with Image.open(io.BytesIO(entity)) as image:
                image.verify()
            with Image.open(io.BytesIO(entity)) as image:
                formats = {
                    "PNG": ("image/png", {".png"}),
                    "JPEG": ("image/jpeg", {".jpg", ".jpeg"}),
                    "WEBP": ("image/webp", {".webp"}),
                    "GIF": ("image/gif", {".gif"}),
                    "BMP": ("image/bmp", {".bmp"}),
                    "AVIF": ("image/avif", {".avif"}),
                }
                if image.format not in formats:
                    raise ValueError("unsupported result-image format")
                if image.size != (asset["width"], asset["height"]):
                    raise ValueError("public image dimensions differ from the reviewed image")
                expected_type, extensions = formats[image.format]
                if media_type != expected_type or Path(urlsplit(url).path).suffix.lower() not in extensions:
                    raise ValueError("image format, MIME type and canonical extension disagree")
                image.load()
            decoded = verify_decoded_evidence(entity, canonical, asset)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ValueError("public image cannot be decoded") from error
        return {
            "http_status": 200, "sha256": asset["sha256"], "decoded": True,
            "wire_sha256": digest(response.body), "entity_sha256": digest(entity),
            "canonical_sha256": digest(canonical),
            "decoded_pixels_sha256": decoded["pixels_sha256"],
            "width": decoded["width"], "height": decoded["height"],
            "content_encoding": response.headers.get("content-encoding", "identity"),
            **reversal,
        }

    def landing(self, url: str, expected: str, *, indexable: bool = True) -> dict:
        if not url.startswith(f"{PUBLIC_SITE}/"):
            raise ValueError("Result landing URL is outside the approved public site")
        self.crawlable(url, "Googlebot")
        self.crawlable(url, "Googlebot-Image")
        response = self.transport(url, 2 * 1024 * 1024)
        if response.status != 200 or response.url != url:
            raise ValueError("published landing page does not return direct HTTP 200")
        if response.headers.get("content-type", "").split(";", 1)[0].strip().lower() not in {
            "text/html", "application/xhtml+xml",
        }:
            raise ValueError("published landing page is not served as HTML")
        if indexable and any(_header_blocks(response.headers.get("x-robots-tag", ""), agent)
                             for agent in ("Googlebot", "Googlebot-Image")):
            raise ValueError("landing X-Robots-Tag prevents image indexing")
        relative = url[len(PUBLIC_SITE) + 1:]
        if not relative or relative.endswith("/"):
            relative += "index.html"
        try:
            canonical = canonical_gallery_source(expected)
            directive = "none"
            try:
                check = verify_output_bytes(
                    response.body, site=PUBLIC_SITE, relative=relative,
                    expected_sha256=digest(expected.encode("utf-8")),
                )
            except GenerationError:
                if canonical == expected:
                    raise
                check = verify_output_bytes(
                    response.body, site=PUBLIC_SITE, relative=relative,
                    expected_sha256=digest(canonical.encode("utf-8")),
                )
                directive = "cloudflare-email-off-v1"
            return {
                **check, "source_sha256": digest(expected.encode("utf-8")),
                "canonical_sha256": digest(canonical.encode("utf-8")),
                "source_directive": directive,
            }
        except GenerationError as error:
            raise ValueError("published landing does not match the generated result page") from error


def render_gallery(locale: str, assets: list[dict], labels: dict, apps: dict, site: str) -> str:
    esc = html.escape
    cards = []
    for asset in assets:
        copy = asset["localizations"][locale]
        app = apps[asset["app_key"]]
        token = f"img_{asset['app_key']}"[:30]
        store_url = (
            f"https://apps.apple.com/us/app/id{app['app_id']}"
            f"?pt=118326163&ct={token}&mt=8"
        )
        cards.append(
            f'<article id="{esc(asset["id"])}" data-result-image="{esc(asset["id"])}">'
            f'<h2>{esc(app["name"])}</h2><p>{esc(copy["nearby_text"])}</p>'
            f'<figure><img src="{esc(asset["canonical_asset_url"], quote=True)}" '
            f'alt="{esc(copy["alt"], quote=True)}" width="{asset["width"]}" '
            f'height="{asset["height"]}" data-result-image-sha256="{asset["sha256"]}" '
            'decoding="async" loading="lazy">'
            f'<figcaption>{esc(copy["caption"])}</figcaption></figure>'
            f'<p class="limitation">{esc(copy["limitation"])}</p>'
            f'<p>{esc(labels["source_label"])} · '
            f'<a href="{esc(store_url, quote=True)}">{esc(labels["store_label"])}</a></p>'
            '</article>'
        )
    content = "\n".join(cards)
    intro = labels["intro"] if cards else labels["unavailable"]
    robots = "index,follow,max-image-preview:large" if cards else "noindex,follow"
    direction = ' dir="rtl"' if locale in {"ar-SA", "he", "ur-PK"} else ""
    return (
        '<!doctype html>\n'
        f'<html lang="{locale}"{direction}><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(labels["title"])}</title>'
        f'<meta name="description" content="{esc(intro, quote=True)}">'
        f'<meta name="robots" content="{robots}">'
        f'<link rel="canonical" href="{gallery_url(locale, site)}">'
        '<style>body{font:1.1rem/1.65 system-ui,sans-serif;margin:0;background:#fff8fd;'
        'color:#291246}main{max-width:74rem;margin:auto;padding:clamp(1rem,4vw,3rem)}'
        'article{margin:2.5rem 0;padding:clamp(1rem,3vw,2rem);background:#fff;'
        'border:1px solid #ecd9fa;border-radius:1.4rem}figure{margin:1rem 0}'
        'img{display:block;max-width:100%;height:auto;border-radius:.7rem}'
        'figcaption{margin-top:1rem}a{color:#7139a8;text-underline-offset:.2em}'
        '.limitation{border-left:3px solid #cc90dd;padding-left:1rem}'
        'a{display:inline-block;min-height:44px}p{max-width:75ch}</style></head><body>'
        f'<main><nav><a href="{site}/">{esc(labels["home_label"])}</a></nav>'
        f'<h1>{esc(labels["title"])}</h1><p>{esc(intro)}</p>{content}'
        '<footer><!--email_off--><a href="mailto:hourstag.app@gmail.com">'
        'hourstag.app@gmail.com</a><!--/email_off--></footer></main></body></html>\n'
    )


def canonical_gallery_source(source: str) -> str:
    """Derive the published SHA from a source-owned directive, not an edge wildcard."""
    if "email_off" not in source:
        return source
    contact = '<a href="mailto:hourstag.app@gmail.com">hourstag.app@gmail.com</a>'
    protected = f"<footer><!--email_off-->{contact}<!--/email_off--></footer>"
    if source.count(protected) != 1 or source.count("email_off") != 2:
        raise ValueError("Unbound or ambiguous email_off source directive")
    return source.replace(protected, f"<footer>{contact}</footer>", 1)


class GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images: list[dict] = []
        self.canonicals: list[str] = []
        self.robots: list[str] = []
        self.language = ""
        self.captions = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"img", "link", "meta", "html"} and len(values) != len(attrs):
            raise ValueError("Duplicate indexing attributes")
        if tag == "html":
            self.language = values.get("lang", "")
        if tag == "img":
            self.images.append(values)
        if tag == "link" and "canonical" in values.get("rel", "").split():
            self.canonicals.append(values.get("href"))
        if tag == "meta" and values.get("name", "").lower() in {"robots", "googlebot", "googlebot-image"}:
            self.robots.append(values.get("content", ""))
        if tag == "figcaption":
            self.captions += 1


def validate_gallery(source: str, locale: str, assets: list[dict], site: str) -> None:
    parser = GalleryParser()
    parser.feed(source)
    if parser.language != locale or parser.canonicals != [gallery_url(locale, site)]:
        raise ValueError("Gallery language or canonical is inconsistent")
    if any(_header_blocks(value, "Googlebot-Image") for value in parser.robots):
        raise ValueError("Gallery robots prevents image indexing")
    if len(parser.images) != len(assets) or parser.captions != len(assets):
        raise ValueError("Every result needs a real img src and a native figcaption")
    for image, asset in zip(parser.images, assets, strict=True):
        for key, expected in (
            ("src", asset["canonical_asset_url"]),
            ("alt", asset["localizations"][locale]["alt"]),
            ("width", str(asset["width"])), ("height", str(asset["height"])),
            ("data-result-image-sha256", asset["sha256"]),
        ):
            if image.get(key) != expected:
                raise ValueError(f"Invalid result image {key}")
    if "application/ld+json" in source or re.search(r"background-image\s*:", source, re.I):
        raise ValueError("Result proof cannot be CSS imagery or invented structured data")


def _managed(source: str, block: str, name: str, closing: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}\n?", re.S)
    replacement = f"{start}\n{block}\n{end}\n" if block else ""
    if start in source or end in source:
        if source.count(start) != 1 or source.count(end) != 1 or not pattern.search(source):
            raise ValueError(f"Corrupt managed block: {name}")
        return pattern.sub(lambda _: replacement, source)
    if closing not in source:
        raise ValueError(f"Missing managed destination: {closing}")
    return source.replace(closing, replacement + closing, 1)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def generate(
    pages: Path,
    manifest: dict,
    *,
    site: str = PUBLIC_SITE,
    verifier: PublicVerifier | None = None,
    today: str | None = None,
    check: bool = False,
    require_approved: bool = False,
) -> dict:
    validate_manifest(manifest)
    site = _url(site.rstrip("/"), hosts={urlsplit(PUBLIC_SITE).hostname})
    verifier = verifier or PublicVerifier()
    today = today or date.today().isoformat()
    if date.fromisoformat(today) > date.today():
        raise ValueError("Future lastmod")
    apps = {app["key"]: app for app in manifest["apps"]}
    previous = json.loads(_read(pages / COVERAGE) or "{}")
    previous_pages = previous.get("pages", {})
    previous_retired = previous.get("retired_pages", {})
    previous_managed = {**previous_retired, **previous_pages}
    for relative, record in previous_managed.items():
        if (
            relative != gallery_path(record["locale"])
            or record["url"] != gallery_url(record["locale"], site)
        ):
            raise ValueError("Previous image coverage contains an unmanaged page")
    ready: dict[str, list[dict]] = {}
    failed: dict[str, str] = {}
    image_readbacks = {}
    for asset in manifest["images"]:
        try:
            image_readbacks[asset["id"]] = verifier.image(asset)
            for locale in asset["localizations"]:
                url = gallery_url(locale, site)
                verifier.crawlable(url, "Googlebot")
                verifier.crawlable(url, "Googlebot-Image")
            for locale in asset["localizations"]:
                ready.setdefault(locale, []).append(asset)
        except (ValueError, UnicodeError) as error:
            failed[asset["id"]] = str(error)
    if require_approved and failed:
        raise ValueError("Approved image verification blocks publication: " + canonical_json(failed))
    outputs: dict[str, str] = {}
    page_records: dict[str, dict] = {}
    retired_records: dict[str, dict] = {}
    managed_locales = set(manifest["labels"]) | {
        record["locale"] for record in previous_managed.values()
    }
    for locale in sorted(managed_locales):
        assets = sorted(ready.get(locale, []), key=lambda item: item["id"])
        relative = gallery_path(locale)
        prior = previous_managed.get(relative, {})
        labels = manifest["labels"].get(locale) or prior.get("labels")
        if labels is None:
            raise ValueError("Retiring a gallery requires its previously reviewed native labels")
        _native_copy(labels, locale, LABEL_FIELDS)
        if not assets and not prior and not (pages / relative).is_file():
            continue
        content = render_gallery(locale, assets, labels, apps, site)
        outputs[relative] = content
        if not assets:
            retired_records[relative] = {
                "url": gallery_url(locale, site), "locale": locale, "labels": labels,
                "html_sha256": digest(content.encode()),
                "canonical_html_sha256": digest(canonical_gallery_source(content).encode()),
                "status": BLOCKED,
            }
            continue
        validate_gallery(content, locale, assets, site)
        fingerprint = digest((content + "".join(asset["sha256"] for asset in assets)).encode())
        lastmod = prior.get("lastmod") if prior.get("content_sha256") == fingerprint else today
        if not isinstance(lastmod, str) or date.fromisoformat(lastmod) > date.fromisoformat(today):
            raise ValueError("Invalid or future stored lastmod")
        page_records[relative] = {
            "url": gallery_url(locale, site), "locale": locale,
            "content_sha256": fingerprint, "lastmod": lastmod,
            "image_ids": [asset["id"] for asset in assets],
            "labels": labels,
            "html_sha256": digest(content.encode()),
            "canonical_html_sha256": digest(canonical_gallery_source(content).encode()),
        }
    entries = []
    matrix = []
    for app in manifest["apps"]:
        for locale in OFFICIAL_LOCALES:
            images = [asset for asset in ready.get(locale, []) if asset["app_key"] == app["key"]]
            row = {
                "app_key": app["key"], "locale": locale,
                "status": READY if images else BLOCKED,
                "image_ids": [asset["id"] for asset in images],
            }
            if not images:
                failures = [failed[asset["id"]] for asset in manifest["images"]
                            if asset["app_key"] == app["key"] and locale in asset["localizations"]
                            and asset["id"] in failed]
                row["reason"] = "; ".join(failures) or app["missing_evidence"]
            matrix.append(row)
    for relative, record in sorted(page_records.items()):
        entries.append((record, ready[record["locale"]]))
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for record, images in entries:
        node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = record["url"]
        ET.SubElement(node, f"{{{SITEMAP_NS}}}lastmod").text = record["lastmod"]
        for asset in sorted(images, key=lambda item: item["id"]):
            image = ET.SubElement(node, f"{{{IMAGE_NS}}}image")
            ET.SubElement(image, f"{{{IMAGE_NS}}}loc").text = asset["canonical_asset_url"]
    ET.indent(root, space="  ")
    outputs[SITEMAP] = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    index = _read(pages / "sitemap_index.xml")
    parsed_index = ET.fromstring(index)
    if parsed_index.tag != f"{{{SITEMAP_NS}}}sitemapindex":
        raise ValueError("The canonical sitemap index is missing")
    sitemap_url = f"{site}/{SITEMAP}"
    sitemap_fingerprint = digest(outputs[SITEMAP].encode())
    prior_sitemap = previous.get("sitemap", {})
    sitemap_lastmod = today
    if prior_sitemap.get("content_sha256") == sitemap_fingerprint:
        sitemap_lastmod = prior_sitemap["lastmod"]
    elif not prior_sitemap and _read(pages / SITEMAP) == outputs[SITEMAP]:
        for node in parsed_index.findall(f"{{{SITEMAP_NS}}}sitemap"):
            if node.findtext(f"{{{SITEMAP_NS}}}loc") == sitemap_url:
                sitemap_lastmod = node.findtext(f"{{{SITEMAP_NS}}}lastmod") or today
    if date.fromisoformat(sitemap_lastmod) > date.fromisoformat(today):
        raise ValueError("Future image sitemap lastmod")
    sitemap_record = {"content_sha256": sitemap_fingerprint, "lastmod": sitemap_lastmod}
    if "<!-- result-image-sitemap:start -->" not in index:
        for node in parsed_index.findall(f"{{{SITEMAP_NS}}}sitemap"):
            if node.findtext(f"{{{SITEMAP_NS}}}loc") == sitemap_url:
                index = re.sub(
                    r"<sitemap(?:\s[^>]*)?>\s*<loc>"
                    + re.escape(sitemap_url)
                    + r"</loc>.*?</sitemap>\s*", "", index, flags=re.S,
                )
    block = (f"<sitemap><loc>{sitemap_url}</loc><lastmod>{sitemap_lastmod}</lastmod>"
             "</sitemap>") if page_records else ""
    outputs["sitemap_index.xml"] = _managed(index, block, "result-image-sitemap", "</sitemapindex>")
    robots = _read(pages / "robots.txt")
    if not robots.strip():
        raise ValueError("Published robots discovery is missing")
    robots_start, robots_end = "# result-image-sitemap:start", "# result-image-sitemap:end"
    robots_block = (
        f"{robots_start}\nSitemap: {sitemap_url}\n{robots_end}\n" if page_records else ""
    )
    robots_pattern = re.compile(rf"{robots_start}.*?{robots_end}\n?", re.S)
    if robots_start in robots or robots_end in robots:
        if robots.count(robots_start) != 1 or robots.count(robots_end) != 1 or not robots_pattern.search(robots):
            raise ValueError("Corrupt result-image robots discovery block")
        robots = robots_pattern.sub(lambda _: robots_block, robots)
    elif robots_block:
        robots = robots.rstrip() + "\n\n" + robots_block
    outputs["robots.txt"] = robots
    links = "".join(
        f'<li><a href="{gallery_url(locale, site)}" lang="{locale}">'
        f'{html.escape(manifest["labels"][locale]["title"])}</a></li>'
        for locale in sorted(ready)
    )
    outputs["index.html"] = _managed(
        _read(pages / "index.html"),
        f'<nav aria-label="Published app images"><ul>{links}</ul></nav>' if links else "",
        "result-image-links", "</body>",
    )
    unique = {asset["sha256"] for assets in ready.values() for asset in assets}
    report = {
        "schema_version": 1, "scope": manifest["scope"],
        "evidence_manifest_sha256": digest(canonical_json(manifest).encode()),
        "indexing_state": "ELIGIBLE_IS_NOT_INDEXED",
        "expected_locales": list(OFFICIAL_LOCALES),
        "counts": {
            "priority_apps": len(apps), "expected_app_locales": len(matrix),
            "indexable_unique_images": len(unique), "indexable_pages": len(page_records),
            "verified_app_locales": sum(row["status"] == READY for row in matrix),
            "blocked_app_locales": sum(row["status"] == BLOCKED for row in matrix),
            "blocked_candidate_images": len(manifest["rejected_candidates"]) + len(failed),
        },
        "pages": page_records, "retired_pages": retired_records,
        "sitemap": sitemap_record, "coverage": matrix,
        "blocked_candidates": manifest["rejected_candidates"],
        "public_check_failures": failed,
        "unproven_claims": manifest["unproven_claims"],
    }
    outputs[COVERAGE] = canonical_json(report)
    changed = sorted(relative for relative, content in outputs.items() if _read(pages / relative) != content)
    if check and changed:
        raise ValueError("Stale result-image outputs: " + ", ".join(changed))
    if not check:
        for relative in changed:
            target = pages / relative
            if target.is_symlink() or not target.resolve().is_relative_to(pages.resolve()):
                raise ValueError("Result output escapes the Pages checkout")
        for relative in changed:
            target = pages / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(outputs[relative], encoding="utf-8")
    return {
        **report["counts"], "public_check_failures": failed,
        "image_readbacks": image_readbacks,
        "changed_files": changed,
        "changed_pages": [
            f"{site}/{relative.removesuffix('index.html')}" if relative.endswith("index.html")
            else f"{site}/{relative}"
            for relative in changed if relative.endswith(".html")
        ],
        "indexing_state": report["indexing_state"],
    }


def image_readback_generation(pages: Path, manifest_path: Path) -> dict:
    document = parse_json((pages / ".well-known/deployment.json").read_bytes())
    generation = validate_binding(document)
    revision = subprocess.check_output(
        ["git", "-C", str(pages), "rev-parse", "HEAD"], text=True, timeout=15,
    ).strip()
    if (
        generation["pages_source_sha"] != revision
        or document["source_commit"] != revision
        or document["engine_source_revision"] != generation["source_sha"]
    ):
        raise ValueError("Image readback cannot reuse an older deployment generation")
    for relative, actual in (
        ("result_image_index.py", Path(__file__)),
        ("image_transport_evidence.py", Path(image_transport.__file__)),
        ("data/result_image_evidence_v1.json", manifest_path),
    ):
        committed = subprocess.check_output(
            ["git", "-C", str(pages), "show", f"{revision}:_engine/geo/{relative}"],
            timeout=15,
        )
        if committed != actual.read_bytes():
            raise ValueError(f"Image readback source is not the sealed generation: {relative}")
    return generation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-live", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    verifier = PublicVerifier()
    generation = image_readback_generation(args.pages, args.manifest) if args.verify_live else None
    result = generate(
        args.pages, manifest, verifier=verifier, check=args.check, require_approved=True,
    )
    if args.verify_live:
        coverage = json.loads((args.pages / COVERAGE).read_text(encoding="utf-8"))
        readback_pages = {
            **coverage.get("retired_pages", {}), **coverage["pages"],
        }
        readbacks = {}
        for relative, record in readback_pages.items():
            content = (args.pages / relative).read_text(encoding="utf-8")
            for attempt in range(6):
                try:
                    readbacks[relative] = verifier.landing(
                        record["url"], content, indexable=relative in coverage["pages"],
                    )
                    break
                except ValueError:
                    if attempt == 5:
                        raise
                    time.sleep(5)
        result["live_landing_pages_verified"] = len(coverage["pages"])
        result["live_retired_pages_verified"] = len(coverage.get("retired_pages", {}))
        result["live_readbacks"] = readbacks
        result["deployment_generation"] = generation
        result["image_evidence_manifest_sha256"] = digest(args.manifest.read_bytes())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(canonical_json(result), encoding="utf-8")
    print(canonical_json(result), end="")


if __name__ == "__main__":
    main()
