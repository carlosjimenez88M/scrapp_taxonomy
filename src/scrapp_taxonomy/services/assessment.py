from __future__ import annotations

from dataclasses import dataclass

from scrapp_taxonomy.domain.models import FetchStatus, PageTaxonomy, RobotsPolicy, ScrapeAssessment
from scrapp_taxonomy.ports import ContentAnalyzer, PageGateway, RobotsGateway, RobotsPolicyReader


@dataclass(frozen=True)
class ScrapeAssessmentService:
    robots_gateway: RobotsGateway
    page_gateway: PageGateway
    robots_reader: RobotsPolicyReader
    analyzer: ContentAnalyzer
    user_agent: str = "scrapp-taxonomy/0.1"

    def assess(self, target_url: str) -> ScrapeAssessment:
        robots_resource = self.robots_gateway.fetch_for(target_url)
        policy = self.robots_reader.read(target_url, robots_resource, self.user_agent)

        if not policy.target_allowed:
            taxonomy = PageTaxonomy(
                url=target_url,
                status=FetchStatus.SKIPPED,
                error="robots.txt does not allow fetching this URL for the configured user agent.",
            )
            return ScrapeAssessment(
                target_url, policy, taxonomy, self._recommendations(policy, taxonomy)
            )

        page = self.page_gateway.fetch(target_url)
        taxonomy = self.analyzer.analyze(page)
        return ScrapeAssessment(
            target_url, policy, taxonomy, self._recommendations(policy, taxonomy)
        )

    @staticmethod
    def _recommendations(policy: RobotsPolicy, taxonomy: PageTaxonomy) -> tuple[str, ...]:
        recommendations: list[str] = []

        if policy.target_allowed:
            recommendations.append("The target URL is fetchable for the configured user agent.")
        else:
            recommendations.append("Do not fetch this target URL with the configured user agent.")

        if policy.crawl_delay is not None:
            recommendations.append(f"Respect a crawl delay of {policy.crawl_delay:g} seconds.")

        if policy.sitemaps:
            recommendations.append("Use sitemap URLs as the first source for crawl discovery.")

        if taxonomy.status is FetchStatus.FETCHED:
            kinds = ", ".join(candidate.label for candidate in taxonomy.candidates[:5])
            if kinds:
                recommendations.append(f"Initial extractable signals found: {kinds}.")

        return tuple(recommendations)
