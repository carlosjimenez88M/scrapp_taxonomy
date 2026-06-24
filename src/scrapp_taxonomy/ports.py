"""
Protocol interfaces that decouple domain logic from infrastructure.

Every concrete adapter (HTTP clients, parsers, formatters) must satisfy one of
the protocols defined here. Application code imports only these interfaces;
infrastructure imports nothing from here.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
from typing import Protocol

from scrapp_taxonomy.domain.models import HttpResource, PageTaxonomy, RobotsPolicy, ScrapeAssessment

#######################
# ---- Protocols ---- #
#######################


class RobotsGateway(Protocol):
    """Fetch the robots.txt file for a given target URL."""

    def fetch_for(self, target_url: str) -> HttpResource:
        """Return the robots.txt resource located at the domain root of *target_url*."""
        ...


class PageGateway(Protocol):
    """Fetch an arbitrary public page."""

    def fetch(self, url: str) -> HttpResource:
        """Return the HTTP resource at *url*."""
        ...


class RobotsPolicyReader(Protocol):
    """Parse a robots.txt document and resolve crawl permissions."""

    def read(self, target_url: str, robots_resource: HttpResource, user_agent: str) -> RobotsPolicy:
        """Convert the raw robots.txt body into a policy decision for *target_url*."""
        ...


class ContentAnalyzer(Protocol):
    """Analyse an HTTP page and report extractable signals."""

    def analyze(self, page: HttpResource) -> PageTaxonomy:
        """Return a PageTaxonomy describing the discoverable data on *page*."""
        ...


class Formatter(Protocol):
    """Render a ScrapeAssessment as a printable string."""

    def format(self, assessment: ScrapeAssessment) -> str:
        """Return *assessment* serialised to a human- or machine-readable string."""
        ...
