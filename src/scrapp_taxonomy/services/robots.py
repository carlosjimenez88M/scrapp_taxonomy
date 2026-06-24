"""
robots.txt parsing and crawl policy resolution.

StandardRobotsPolicyReader delegates permission resolution to Python's built-in
robotparser and augments the result with structured group data (allow/disallow
rules, crawl-delay) extracted by a hand-rolled line parser.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import logging
from dataclasses import dataclass
from io import StringIO
from urllib import robotparser
from urllib.parse import urlparse

from scrapp_taxonomy.domain.models import (
    HttpResource,
    RobotsAvailability,
    RobotsGroup,
    RobotsPolicy,
)

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#####################
# ---- Classes ---- #
#####################


@dataclass(frozen=True)
class StandardRobotsPolicyReader:
    """Parse robots.txt and resolve crawl permissions for a target URL and user-agent."""

    def read(self, target_url: str, robots_resource: HttpResource, user_agent: str) -> RobotsPolicy:
        """Return a RobotsPolicy for the given target URL.

        Delegates permission resolution to Python's robotparser and enriches the
        result with crawl-delay, request-rate, sitemaps, and matching rule groups.

        Args:
            target_url: The page URL being assessed.
            robots_resource: The raw robots.txt HTTP resource.
            user_agent: The user-agent string to evaluate permissions for.

        Returns:
            A :class:`~scrapp_taxonomy.domain.models.RobotsPolicy` with the
            resolved permission and all relevant metadata.
        """
        availability = self._availability_for(robots_resource)
        logger.debug("robots.txt for %s: availability=%s", target_url, availability.value)

        if availability is RobotsAvailability.UNAVAILABLE:
            return RobotsPolicy(
                robots_url=robots_resource.url,
                availability=availability,
                target_allowed=False,
                user_agent=user_agent,
                error=robots_resource.error or f"HTTP {robots_resource.status_code}",
            )

        if availability is RobotsAvailability.NOT_FOUND:
            logger.debug("No robots.txt found — allowing by convention")
            return RobotsPolicy(
                robots_url=robots_resource.url,
                availability=availability,
                target_allowed=True,
                user_agent=user_agent,
            )

        parser = robotparser.RobotFileParser()
        parser.set_url(robots_resource.url)
        parser.parse(robots_resource.body.splitlines())

        groups = tuple(_RobotsTxtGroupParser().parse(robots_resource.body, user_agent))
        raw_crawl_delay = parser.crawl_delay(user_agent)
        crawl_delay = float(raw_crawl_delay) if raw_crawl_delay is not None else None
        request_rate = parser.request_rate(user_agent)
        allowed = parser.can_fetch(user_agent, target_url)

        logger.debug(
            "Policy for %s: allowed=%s crawl_delay=%s",
            target_url,
            allowed,
            crawl_delay,
        )
        return RobotsPolicy(
            robots_url=robots_resource.url,
            availability=availability,
            target_allowed=allowed,
            user_agent=user_agent,
            crawl_delay=crawl_delay,
            request_rate=str(request_rate) if request_rate else None,
            sitemaps=tuple(parser.site_maps() or ()),
            matching_groups=groups,
        )

    @staticmethod
    def _availability_for(resource: HttpResource) -> RobotsAvailability:
        if resource.status_code == 404:
            return RobotsAvailability.NOT_FOUND
        if resource.ok:
            return RobotsAvailability.FOUND
        return RobotsAvailability.UNAVAILABLE


class _RobotsTxtGroupParser:
    """Extract user-agent groups from a robots.txt body for structured reporting."""

    def parse(self, robots_text: str, user_agent: str) -> list[RobotsGroup]:
        """Return the groups from *robots_text* that apply to *user_agent*.

        Prefers exact or partial matches over the wildcard (*) group.
        """
        groups = self._parse_groups(robots_text)
        matches = [group for group in groups if self._matches(group.user_agents, user_agent)]
        wildcard = [group for group in groups if "*" in group.user_agents]
        return matches or wildcard

    def _parse_groups(self, robots_text: str) -> list[RobotsGroup]:
        groups: list[RobotsGroup] = []
        current_agents: list[str] = []
        allow: list[str] = []
        disallow: list[str] = []
        crawl_delay: float | None = None
        seen_rule = False

        for raw_line in StringIO(robots_text):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                self._append_group(groups, current_agents, allow, disallow, crawl_delay)
                current_agents, allow, disallow, crawl_delay, seen_rule = [], [], [], None, False
                continue

            if ":" not in line:
                continue

            field, value = [part.strip() for part in line.split(":", 1)]
            field = field.lower()

            if field == "user-agent":
                if seen_rule and current_agents:
                    self._append_group(groups, current_agents, allow, disallow, crawl_delay)
                    current_agents, allow, disallow = [], [], []
                    crawl_delay, seen_rule = None, False
                current_agents.append(value.lower())
                continue

            if not current_agents:
                continue

            if field == "allow":
                allow.append(value)
                seen_rule = True
            elif field == "disallow":
                if value:
                    disallow.append(value)
                seen_rule = True
            elif field == "crawl-delay":
                crawl_delay = self._as_float(value)
                seen_rule = True

        self._append_group(groups, current_agents, allow, disallow, crawl_delay)
        return groups

    @staticmethod
    def _append_group(
        groups: list[RobotsGroup],
        agents: list[str],
        allow: list[str],
        disallow: list[str],
        crawl_delay: float | None,
    ) -> None:
        if agents and (allow or disallow or crawl_delay is not None):
            groups.append(RobotsGroup(tuple(agents), tuple(allow), tuple(disallow), crawl_delay))

    @staticmethod
    def _matches(agents: tuple[str, ...], user_agent: str) -> bool:
        normalized = user_agent.lower()
        parsed_name = urlparse(user_agent).netloc.lower()
        return any(agent == "*" or agent in normalized or agent in parsed_name for agent in agents)

    @staticmethod
    def _as_float(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None
