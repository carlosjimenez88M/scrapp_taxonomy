"""
HTML signal extraction service.

Parses an HTML document using the standard library HTMLParser and reports
counts and URL samples for each configured signal category (headings, links,
images, feeds, forms, article-like links, JSON-LD structured data).

Signal categories are defined as SignalSpec instances and can be extended or
replaced without modifying this module — pass a custom ``signals`` tuple to
StandardHtmlAnalyzer to override the defaults.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import json as _json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from scrapp_taxonomy.domain.models import FetchStatus, HttpResource, PageTaxonomy, ResourceCandidate

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#####################
# ---- Classes ---- #
#####################


@dataclass
class _ParseResult:
    """Accumulates raw signals while the HTML parser processes the document."""

    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    article_links: list[str] = field(default_factory=list)
    structured_data_types: list[str] = field(default_factory=list)
    title: str | None = None
    meta_description: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class SignalSpec:
    """Declarative extraction rule for one signal category.

    ``kind`` is used as the machine-readable identifier in ResourceCandidate.
    ``label`` is the human-readable name shown in reports.
    ``extract`` receives the fully-populated _ParseResult and returns the raw
    list of collected values for this category.
    """

    kind: str
    label: str
    extract: Callable[[_ParseResult], list[str]]


DEFAULT_SIGNALS: tuple[SignalSpec, ...] = (
    SignalSpec("headings", "Headings", lambda r: r.headings),
    SignalSpec("links", "Links", lambda r: r.links),
    SignalSpec("images", "Images", lambda r: r.images),
    SignalSpec("structured_data", "JSON-LD structured data", lambda r: r.structured_data_types),
    SignalSpec("forms", "Forms", lambda r: r.forms),
    SignalSpec("feeds", "Feeds", lambda r: r.feeds),
    SignalSpec("article_links", "Article-like links", lambda r: r.article_links),
)


@dataclass(frozen=True)
class StandardHtmlAnalyzer:
    """Parse an HTML page and report counts and samples for each configured signal.

    Accepts a custom ``signals`` tuple to add, remove, or reorder signal
    categories without subclassing or modifying this module (Open/Closed).
    """

    sample_size: int = 8
    signals: tuple[SignalSpec, ...] = DEFAULT_SIGNALS

    def analyze(self, page: HttpResource) -> PageTaxonomy:
        """Return a PageTaxonomy for the given HTTP resource.

        Fails immediately and returns a FAILED taxonomy if the resource is not
        OK. Otherwise feeds the HTML body through the parser and maps each
        SignalSpec to a ResourceCandidate, omitting candidates with zero count.

        Args:
            page: The fetched HTTP resource to analyse.

        Returns:
            A :class:`~scrapp_taxonomy.domain.models.PageTaxonomy` with all
            discovered candidates and page metadata.
        """
        if not page.ok:
            logger.debug("Page is not OK (%s) — returning FAILED taxonomy", page.status_code)
            return PageTaxonomy(
                url=page.url,
                status=FetchStatus.FAILED,
                error=page.error or f"HTTP {page.status_code}",
            )

        parser = _TaxonomyHtmlParser(page.final_url or page.url)
        parser.feed(page.body)
        result = parser.result

        candidates = tuple(
            candidate
            for spec in self.signals
            for candidate in (self._candidate(spec.kind, spec.label, spec.extract(result)),)
            if candidate.count
        )

        logger.debug("Analyzed %s — %d signal categories found", page.url, len(candidates))
        return PageTaxonomy(
            url=page.final_url or page.url,
            status=FetchStatus.FETCHED,
            title=result.title,
            meta_description=result.meta_description,
            language=result.language,
            candidates=candidates,
        )

    def _candidate(self, kind: str, label: str, values: list[str]) -> ResourceCandidate:
        sample = tuple(_unique(values)[: self.sample_size])
        return ResourceCandidate(kind=kind, label=label, count=len(values), sample=sample)


class _TaxonomyHtmlParser(HTMLParser):
    """SAX-style HTML parser that populates a _ParseResult incrementally."""

    _base_url: str
    _base_netloc: str
    result: _ParseResult
    _current_tag: str | None
    _current_script_type: str | None
    _text_buffer: list[str]

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._base_netloc = urlparse(base_url).netloc
        self.result = _ParseResult()
        self._current_tag = None
        self._current_script_type = None
        self._text_buffer = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        self._current_tag = tag
        if tag in {"title", "h1", "h2", "h3"}:
            self._text_buffer = []

        if tag == "html":
            self.result.language = attrs_dict.get("lang") or None
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.result.meta_description = (
                    attrs_dict.get("content") or self.result.meta_description
                )
        elif tag == "a" and attrs_dict.get("href"):
            url = urljoin(self._base_url, attrs_dict["href"])
            self.result.links.append(url)
            if self._looks_like_article_url(url):
                self.result.article_links.append(url)
        elif tag == "img" and attrs_dict.get("src"):
            self.result.images.append(urljoin(self._base_url, attrs_dict["src"]))
        elif tag == "form":
            action = attrs_dict.get("action") or self._base_url
            method = attrs_dict.get("method", "get").upper()
            self.result.forms.append(f"{method} {urljoin(self._base_url, action)}")
        elif tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            link_type = attrs_dict.get("type", "").lower()
            if "alternate" in rel and ("rss" in link_type or "atom" in link_type):
                href = attrs_dict.get("href")
                if href:
                    self.result.feeds.append(urljoin(self._base_url, href))
        elif tag == "script":
            self._current_script_type = attrs_dict.get("type", "").lower()
            if self._current_script_type == "application/ld+json":
                self._text_buffer = []

    def handle_data(self, data: str) -> None:
        if self._current_tag in {"title", "h1", "h2", "h3", "script"}:
            self._text_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        text = " ".join(" ".join(self._text_buffer).split())
        if tag == "title" and text and self.result.title is None:
            self.result.title = text
        elif tag in {"h1", "h2", "h3"} and text:
            self.result.headings.append(text)
        elif tag == "script" and self._current_script_type == "application/ld+json":
            if text:
                self.result.structured_data_types.extend(_guess_json_ld_types(text))
            self._current_script_type = None

        if tag == self._current_tag:
            self._current_tag = None
        self._text_buffer = []

    def _looks_like_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self._base_netloc:
            return False
        path = parsed.path.rstrip("/")
        parts = [part for part in path.split("/") if part]
        return len(parts) >= 3 and not path.lower().endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp")
        )


######################
# ---- Functions ---- #
######################


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _guess_json_ld_types(json_text: str) -> list[str]:
    """Extract @type values from a JSON-LD script block.

    Falls back to a generic label when the block is not valid JSON or carries
    no recognisable @type field.
    """
    try:
        data = _json.loads(json_text)
    except (ValueError, _json.JSONDecodeError):
        logger.debug("Unparseable JSON-LD block (%.60s…)", json_text)
        return ["JSON-LD block"]
    items: list[object] = data if isinstance(data, list) else [data]
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
