"""
Immutable data models for the scrapp-taxonomy domain.

All types are frozen dataclasses or StrEnums — nothing in this module performs
I/O or carries mutable state. Every layer above (services, infrastructure, CLI)
may import from here; this module imports from nothing else in the package.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
from dataclasses import dataclass, field
from enum import StrEnum

##########################
# ---- Enumerations ---- #
##########################


class RobotsAvailability(StrEnum):
    """Whether robots.txt was found, absent, or unreachable."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


class FetchStatus(StrEnum):
    """Outcome of attempting to retrieve a target page."""

    FETCHED = "fetched"
    SKIPPED = "skipped"
    FAILED = "failed"


##########################
# ---- Domain Models ---- #
##########################


@dataclass(frozen=True)
class HttpResource:
    """Raw HTTP response for a single URL, including structured error details."""

    url: str
    status_code: int | None
    body: str
    content_type: str | None = None
    final_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Return True when the response carries no error and status is 2xx/3xx."""
        return self.error is None and self.status_code is not None and 200 <= self.status_code < 400


@dataclass(frozen=True)
class RobotsGroup:
    """A single user-agent group extracted from a robots.txt file."""

    user_agents: tuple[str, ...]
    allow: tuple[str, ...] = ()
    disallow: tuple[str, ...] = ()
    crawl_delay: float | None = None


@dataclass(frozen=True)
class RobotsPolicy:
    """Resolved crawl policy for a specific target URL and user-agent combination."""

    robots_url: str
    availability: RobotsAvailability
    target_allowed: bool
    user_agent: str
    crawl_delay: float | None = None
    request_rate: str | None = None
    sitemaps: tuple[str, ...] = ()
    matching_groups: tuple[RobotsGroup, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ResourceCandidate:
    """A discovered extractable signal category found on a page."""

    kind: str
    label: str
    url: str | None = None
    count: int | None = None
    sample: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageTaxonomy:
    """All signals and metadata collected from a single page fetch."""

    url: str
    status: FetchStatus
    title: str | None = None
    meta_description: str | None = None
    language: str | None = None
    candidates: tuple[ResourceCandidate, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ScrapeAssessment:
    """Combined result of a robots.txt evaluation and page signal discovery."""

    target_url: str
    robots_policy: RobotsPolicy
    page_taxonomy: PageTaxonomy
    recommendations: tuple[str, ...] = field(default_factory=tuple)
