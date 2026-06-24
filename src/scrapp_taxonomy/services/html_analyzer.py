from __future__ import annotations

import json as _json
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from scrapp_taxonomy.domain.models import FetchStatus, HttpResource, PageTaxonomy, ResourceCandidate


@dataclass(frozen=True)
class StandardHtmlAnalyzer:
    sample_size: int = 8

    def analyze(self, page: HttpResource) -> PageTaxonomy:
        if not page.ok:
            return PageTaxonomy(
                url=page.url,
                status=FetchStatus.FAILED,
                error=page.error or f"HTTP {page.status_code}",
            )

        parser = _TaxonomyHtmlParser(page.final_url or page.url)
        parser.feed(page.body)

        candidates = (
            self._candidate("headings", "Headings", parser.headings),
            self._candidate("links", "Links", parser.links),
            self._candidate("images", "Images", parser.images),
            self._candidate(
                "structured_data", "JSON-LD structured data", parser.structured_data_types
            ),
            self._candidate("forms", "Forms", parser.forms),
            self._candidate("feeds", "Feeds", parser.feeds),
            self._candidate("article_links", "Article-like links", parser.article_links),
        )

        return PageTaxonomy(
            url=page.final_url or page.url,
            status=FetchStatus.FETCHED,
            title=parser.title,
            meta_description=parser.meta_description,
            language=parser.language,
            candidates=tuple(candidate for candidate in candidates if candidate.count),
        )

    def _candidate(self, kind: str, label: str, values: list[str]) -> ResourceCandidate:
        sample = tuple(_unique(values)[: self.sample_size])
        return ResourceCandidate(kind=kind, label=label, count=len(values), sample=sample)


class _TaxonomyHtmlParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.base_netloc = urlparse(base_url).netloc
        self.title: str | None = None
        self.meta_description: str | None = None
        self.language: str | None = None
        self.headings: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self.forms: list[str] = []
        self.feeds: list[str] = []
        self.article_links: list[str] = []
        self.structured_data_types: list[str] = []
        self._current_tag: str | None = None
        self._current_script_type: str | None = None
        self._text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        self._current_tag = tag
        if tag in {"title", "h1", "h2", "h3"}:
            self._text_buffer = []

        if tag == "html":
            self.language = attrs_dict.get("lang") or None
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.meta_description = attrs_dict.get("content") or self.meta_description
        elif tag == "a" and attrs_dict.get("href"):
            url = urljoin(self.base_url, attrs_dict["href"])
            self.links.append(url)
            if self._looks_like_article_url(url):
                self.article_links.append(url)
        elif tag == "img" and attrs_dict.get("src"):
            self.images.append(urljoin(self.base_url, attrs_dict["src"]))
        elif tag == "form":
            action = attrs_dict.get("action") or self.base_url
            method = attrs_dict.get("method", "get").upper()
            self.forms.append(f"{method} {urljoin(self.base_url, action)}")
        elif tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            link_type = attrs_dict.get("type", "").lower()
            if "alternate" in rel and ("rss" in link_type or "atom" in link_type):
                href = attrs_dict.get("href")
                if href:
                    self.feeds.append(urljoin(self.base_url, href))
        elif tag == "script":
            self._current_script_type = attrs_dict.get("type", "").lower()
            if self._current_script_type == "application/ld+json":
                self._text_buffer = []

    def handle_data(self, data: str) -> None:
        if self._current_tag in {"title", "h1", "h2", "h3", "script"}:
            self._text_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        text = " ".join(" ".join(self._text_buffer).split())
        if tag == "title" and text and self.title is None:
            self.title = text
        elif tag in {"h1", "h2", "h3"} and text:
            self.headings.append(text)
        elif tag == "script" and self._current_script_type == "application/ld+json":
            if text:
                self.structured_data_types.extend(_guess_json_ld_types(text))
            self._current_script_type = None

        if tag == self._current_tag:
            self._current_tag = None
        self._text_buffer = []

    def _looks_like_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self.base_netloc:
            return False
        path = parsed.path.rstrip("/")
        parts = [part for part in path.split("/") if part]
        return len(parts) >= 3 and not path.lower().endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp")
        )


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _guess_json_ld_types(json_text: str) -> list[str]:
    try:
        data = _json.loads(json_text)
    except (ValueError, _json.JSONDecodeError):
        return ["JSON-LD block"]
    items = data if isinstance(data, list) else [data]
    types: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = item.get("@type")
        if isinstance(raw, str) and raw:
            types.append(raw)
        elif isinstance(raw, list):
            types.extend(t for t in raw if isinstance(t, str) and t)
    return types or ["JSON-LD block"]
