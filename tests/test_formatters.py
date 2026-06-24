from __future__ import annotations

import json

from scrapp_taxonomy.domain.models import (
    FetchStatus,
    PageTaxonomy,
    ResourceCandidate,
    RobotsAvailability,
    RobotsPolicy,
    ScrapeAssessment,
)
from scrapp_taxonomy.formatters import JsonFormatter, TextFormatter


def _make_assessment(*, allowed: bool = True, fetched: bool = True) -> ScrapeAssessment:
    policy = RobotsPolicy(
        robots_url="https://example.com/robots.txt",
        availability=RobotsAvailability.FOUND,
        target_allowed=allowed,
        user_agent="scrapp-taxonomy/0.1",
    )
    if fetched and allowed:
        taxonomy = PageTaxonomy(
            url="https://example.com/",
            status=FetchStatus.FETCHED,
            title="Example",
            candidates=(
                ResourceCandidate(
                    kind="links",
                    label="Links",
                    count=3,
                    sample=("https://example.com/a", "https://example.com/b"),
                ),
            ),
        )
    else:
        taxonomy = PageTaxonomy(
            url="https://example.com/",
            status=FetchStatus.SKIPPED,
            error="robots.txt does not allow fetching this URL for the configured user agent.",
        )
    return ScrapeAssessment(
        target_url="https://example.com/",
        robots_policy=policy,
        page_taxonomy=taxonomy,
        recommendations=("The target URL is fetchable for the configured user agent.",),
    )


def test_text_formatter_includes_target_url() -> None:
    output = TextFormatter().format(_make_assessment())
    assert "https://example.com/" in output


def test_text_formatter_shows_allowed_yes() -> None:
    output = TextFormatter().format(_make_assessment(allowed=True))
    assert "yes" in output


def test_text_formatter_shows_allowed_no() -> None:
    output = TextFormatter().format(_make_assessment(allowed=False, fetched=False))
    assert "no" in output


def test_text_formatter_shows_candidates_when_fetched() -> None:
    output = TextFormatter().format(_make_assessment(allowed=True, fetched=True))
    assert "Links" in output


def test_json_formatter_produces_valid_json() -> None:
    output = JsonFormatter().format(_make_assessment())
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


def test_json_formatter_contains_target_url() -> None:
    output = JsonFormatter().format(_make_assessment())
    parsed = json.loads(output)
    assert parsed["target_url"] == "https://example.com/"


def test_json_formatter_custom_indent() -> None:
    output = JsonFormatter(indent=4).format(_make_assessment())
    parsed = json.loads(output)
    assert "target_url" in parsed
