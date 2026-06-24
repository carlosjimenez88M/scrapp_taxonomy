from __future__ import annotations

from typing import Protocol

from scrapp_taxonomy.domain.models import HttpResource, PageTaxonomy, RobotsPolicy


class RobotsGateway(Protocol):
    def fetch_for(self, target_url: str) -> HttpResource:
        """Return the robots.txt resource for a target URL."""


class PageGateway(Protocol):
    def fetch(self, url: str) -> HttpResource:
        """Return a public page resource."""


class RobotsPolicyReader(Protocol):
    def read(self, target_url: str, robots_resource: HttpResource, user_agent: str) -> RobotsPolicy:
        """Convert robots.txt text into a policy decision."""


class ContentAnalyzer(Protocol):
    def analyze(self, page: HttpResource) -> PageTaxonomy:
        """Discover high-level extractable public page signals."""
