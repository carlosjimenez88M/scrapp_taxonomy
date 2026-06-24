"""
Output formatters that serialise a ScrapeAssessment to a printable string.

Each formatter implements the Formatter protocol from ports.py. The CLI selects
the appropriate formatter based on the --output flag; library consumers can
instantiate any formatter directly or supply their own implementation.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import json
import logging
from dataclasses import asdict
from typing import Protocol

from scrapp_taxonomy.domain.models import ScrapeAssessment

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#######################
# ---- Protocols ---- #
#######################


class Formatter(Protocol):
    """Render a ScrapeAssessment as a printable string."""

    def format(self, assessment: ScrapeAssessment) -> str:
        """Return *assessment* serialised to a human- or machine-readable string."""
        ...


#####################
# ---- Classes ---- #
#####################


class TextFormatter:
    """Render a ScrapeAssessment as an indented, human-readable text report."""

    def format(self, assessment: ScrapeAssessment) -> str:
        """Return the assessment as a multi-line text report.

        The report includes robots availability, page fetch status, discovered
        signal counts with URL samples, and prioritised recommendations.
        """
        logger.debug("Formatting assessment for %s as text", assessment.target_url)
        policy = assessment.robots_policy
        taxonomy = assessment.page_taxonomy

        lines = [
            f"Target: {assessment.target_url}",
            f"Robots: {policy.robots_url} ({policy.availability.value})",
            f"Allowed for {policy.user_agent}: {'yes' if policy.target_allowed else 'no'}",
        ]

        if policy.crawl_delay is not None:
            lines.append(f"Crawl delay: {policy.crawl_delay:g}s")
        if policy.request_rate:
            lines.append(f"Request rate: {policy.request_rate}")
        if policy.sitemaps:
            lines.append("Sitemaps:")
            lines.extend(f"  - {url}" for url in policy.sitemaps[:10])

        if policy.matching_groups:
            lines.append("Matching robots rules:")
            for group in policy.matching_groups:
                lines.append(f"  User-agent: {', '.join(group.user_agents)}")
                if group.allow:
                    lines.append(f"    Allow sample: {', '.join(group.allow[:5])}")
                if group.disallow:
                    lines.append(f"    Disallow sample: {', '.join(group.disallow[:5])}")

        lines.append(f"Page fetch: {taxonomy.status.value}")
        if taxonomy.error:
            lines.append(f"Page note: {taxonomy.error}")
        if taxonomy.title:
            lines.append(f"Title: {taxonomy.title}")
        if taxonomy.meta_description:
            lines.append(f"Description: {taxonomy.meta_description}")
        if taxonomy.language:
            lines.append(f"Language: {taxonomy.language}")

        if taxonomy.candidates:
            lines.append("Extractable signals:")
            for candidate in taxonomy.candidates:
                lines.append(f"  - {candidate.label}: {candidate.count}")
                for value in candidate.sample[:5]:
                    lines.append(f"      {value}")

        if assessment.recommendations:
            lines.append("Recommendations:")
            lines.extend(f"  - {rec}" for rec in assessment.recommendations)

        return "\n".join(lines)


class JsonFormatter:
    """Render a ScrapeAssessment as a JSON string suitable for piping."""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False) -> None:
        """Initialise with JSON serialisation options.

        Args:
            indent: Number of spaces per indentation level.
            ensure_ascii: When True, escape all non-ASCII characters.
        """
        self._indent = indent
        self._ensure_ascii = ensure_ascii

    def format(self, assessment: ScrapeAssessment) -> str:
        """Return the assessment serialised as an indented JSON string."""
        logger.debug("Formatting assessment for %s as JSON", assessment.target_url)
        return json.dumps(
            asdict(assessment),
            indent=self._indent,
            ensure_ascii=self._ensure_ascii,
        )
