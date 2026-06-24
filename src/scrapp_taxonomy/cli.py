from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict

from scrapp_taxonomy.domain.models import ScrapeAssessment
from scrapp_taxonomy.infrastructure.http import HttpPageGateway, HttpRobotsGateway, UrlLibHttpClient
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService
from scrapp_taxonomy.services.html_analyzer import StandardHtmlAnalyzer
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "assess":
        service = _build_service(args.user_agent, args.timeout)
        assessment = service.assess(args.url)
        if args.output == "json":
            print(json.dumps(asdict(assessment), ensure_ascii=False, indent=2))
        else:
            print(_format_text_report(assessment))
        return 0

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrapp-taxonomy",
        description="Assess robots.txt boundaries and discover extractable page signals.",
    )
    subparsers = parser.add_subparsers(dest="command")
    assess = subparsers.add_parser("assess", help="Assess a target URL.")
    assess.add_argument("url")
    assess.add_argument("--user-agent", default="scrapp-taxonomy/0.1")
    assess.add_argument("--timeout", type=float, default=15.0)
    assess.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def _build_service(user_agent: str, timeout: float) -> ScrapeAssessmentService:
    client = UrlLibHttpClient(user_agent=user_agent, timeout_seconds=timeout)
    return ScrapeAssessmentService(
        robots_gateway=HttpRobotsGateway(client),
        page_gateway=HttpPageGateway(client),
        robots_reader=StandardRobotsPolicyReader(),
        analyzer=StandardHtmlAnalyzer(),
        user_agent=user_agent,
    )


def _format_text_report(assessment: ScrapeAssessment) -> str:
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
        lines.extend(f"  - {recommendation}" for recommendation in assessment.recommendations)

    return "\n".join(lines)
