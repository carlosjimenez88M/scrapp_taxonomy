from __future__ import annotations

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


@dataclass(frozen=True)
class StandardRobotsPolicyReader:
    """Read robots.txt through Python's parser and expose human-facing hints."""

    def read(self, target_url: str, robots_resource: HttpResource, user_agent: str) -> RobotsPolicy:
        availability = self._availability_for(robots_resource)
        if availability is RobotsAvailability.UNAVAILABLE:
            return RobotsPolicy(
                robots_url=robots_resource.url,
                availability=availability,
                target_allowed=False,
                user_agent=user_agent,
                error=robots_resource.error or f"HTTP {robots_resource.status_code}",
            )

        if availability is RobotsAvailability.NOT_FOUND:
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
        return RobotsPolicy(
            robots_url=robots_resource.url,
            availability=availability,
            target_allowed=parser.can_fetch(user_agent, target_url),
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
    def parse(self, robots_text: str, user_agent: str) -> list[RobotsGroup]:
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
                current_agents = []
                allow = []
                disallow = []
                crawl_delay = None
                seen_rule = False
                continue

            if ":" not in line:
                continue

            field, value = [part.strip() for part in line.split(":", 1)]
            field = field.lower()

            if field == "user-agent":
                if seen_rule and current_agents:
                    self._append_group(groups, current_agents, allow, disallow, crawl_delay)
                    current_agents = []
                    allow = []
                    disallow = []
                    crawl_delay = None
                    seen_rule = False
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
