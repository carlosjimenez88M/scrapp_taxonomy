"""
Dependency-injection factory for the application's object graph.

This is the only module that imports concrete infrastructure adapters directly.
All other application code (CLI, library consumers) wires the system through
`build_service` and then works against the domain interfaces.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import logging

from scrapp_taxonomy.infrastructure.http import HttpPageGateway, HttpRobotsGateway, UrlLibHttpClient
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService
from scrapp_taxonomy.services.html_analyzer import StandardHtmlAnalyzer
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#####################
# ---- Factory ---- #
#####################

_DEFAULT_USER_AGENT = "scrapp-taxonomy/0.1"
_DEFAULT_TIMEOUT = 15.0


def build_service(
    user_agent: str = _DEFAULT_USER_AGENT,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> ScrapeAssessmentService:
    """Wire all adapters and return a ready-to-use ScrapeAssessmentService.

    Args:
        user_agent: The User-Agent string sent in every outbound HTTP request.
        timeout_seconds: Maximum seconds to wait for any single HTTP response.

    Returns:
        A fully-configured :class:`ScrapeAssessmentService`.
    """
    logger.debug(
        "Building ScrapeAssessmentService (user_agent=%r, timeout=%.1fs)",
        user_agent,
        timeout_seconds,
    )
    client = UrlLibHttpClient(user_agent=user_agent, timeout_seconds=timeout_seconds)
    return ScrapeAssessmentService(
        robots_gateway=HttpRobotsGateway(client),
        page_gateway=HttpPageGateway(client),
        robots_reader=StandardRobotsPolicyReader(),
        analyzer=StandardHtmlAnalyzer(),
        user_agent=user_agent,
    )
