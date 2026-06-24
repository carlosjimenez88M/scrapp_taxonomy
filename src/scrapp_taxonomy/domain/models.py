from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RobotsAvailability(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


class FetchStatus(StrEnum):
    FETCHED = "fetched"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class HttpResource:
    url: str
    status_code: int | None
    body: str
    content_type: str | None = None
    final_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code is not None and 200 <= self.status_code < 400


@dataclass(frozen=True)
class RobotsGroup:
    user_agents: tuple[str, ...]
    allow: tuple[str, ...] = ()
    disallow: tuple[str, ...] = ()
    crawl_delay: float | None = None


@dataclass(frozen=True)
class RobotsPolicy:
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
    kind: str
    label: str
    url: str | None = None
    count: int | None = None
    sample: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageTaxonomy:
    url: str
    status: FetchStatus
    title: str | None = None
    meta_description: str | None = None
    language: str | None = None
    candidates: tuple[ResourceCandidate, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ScrapeAssessment:
    target_url: str
    robots_policy: RobotsPolicy
    page_taxonomy: PageTaxonomy
    recommendations: tuple[str, ...] = field(default_factory=tuple)
