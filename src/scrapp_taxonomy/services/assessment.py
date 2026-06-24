"""
Orchestration service that coordinates robots evaluation and page analysis.

ScrapeAssessmentService is the primary entry point for library consumers. It
accepts any objects satisfying the gateway and analyzer protocols, making it
straightforward to substitute real HTTP calls with in-memory stubs in tests.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import logging
from dataclasses import dataclass

from scrapp_taxonomy.domain.models import FetchStatus, PageTaxonomy, RobotsPolicy, ScrapeAssessment
from scrapp_taxonomy.ports import ContentAnalyzer, PageGateway, RobotsGateway, RobotsPolicyReader

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#####################
# ---- Classes ---- #
#####################


@dataclass(frozen=True)
class ScrapeAssessmentService:
    """Coordinate a robots.txt check and page signal discovery into one assessment.

    All dependencies are injected via the constructor. Callers should prefer
    ``factory.build_service()`` for a production-wired instance rather than
    constructing this class manually.
    """

    robots_gateway: RobotsGateway
    page_gateway: PageGateway
    robots_reader: RobotsPolicyReader
    analyzer: ContentAnalyzer
    user_agent: str = "scrapp-taxonomy/0.1"

    def assess(self, target_url: str) -> ScrapeAssessment:
        """Return a ScrapeAssessment for *target_url*.

        Fetches robots.txt, resolves crawl permission, and conditionally fetches
        the page. When the user-agent is not permitted, the page is skipped and
        the taxonomy reflects that decision without making an additional request.

        Args:
            target_url: The fully-qualified URL to assess.

        Returns:
            A :class:`~scrapp_taxonomy.domain.models.ScrapeAssessment` with
            the resolved policy, taxonomy, and prioritised recommendations.
        """
        logger.info("Assessing %s", target_url)

        robots_resource = self.robots_gateway.fetch_for(target_url)
        policy = self.robots_reader.read(target_url, robots_resource, self.user_agent)

        if not policy.target_allowed:
            logger.info(
                "Skipping page fetch — %s is disallowed for %s",
                target_url,
                self.user_agent,
            )
            taxonomy = PageTaxonomy(
                url=target_url,
                status=FetchStatus.SKIPPED,
                error="robots.txt does not allow fetching this URL for the configured user agent.",
            )
            return ScrapeAssessment(
                target_url, policy, taxonomy, self._recommendations(policy, taxonomy)
            )

        logger.info("Fetching page %s", target_url)
        page = self.page_gateway.fetch(target_url)
        taxonomy = self.analyzer.analyze(page)
        logger.info("Assessment complete for %s (status=%s)", target_url, taxonomy.status.value)
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
