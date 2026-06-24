from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from scrapp_taxonomy.cli import main
from scrapp_taxonomy.domain.models import (
    FetchStatus,
    PageTaxonomy,
    RobotsAvailability,
    RobotsPolicy,
    ScrapeAssessment,
)


def _fake_assessment() -> ScrapeAssessment:
    policy = RobotsPolicy(
        robots_url="https://example.com/robots.txt",
        availability=RobotsAvailability.FOUND,
        target_allowed=True,
        user_agent="scrapp-taxonomy/0.1",
    )
    taxonomy = PageTaxonomy(
        url="https://example.com/",
        status=FetchStatus.FETCHED,
    )
    return ScrapeAssessment(
        target_url="https://example.com/",
        robots_policy=policy,
        page_taxonomy=taxonomy,
        recommendations=("The target URL is fetchable for the configured user agent.",),
    )


def _make_fake_service() -> MagicMock:
    service = MagicMock()
    service.assess.return_value = _fake_assessment()
    return service


def test_assess_command_text_output(capsys: object) -> None:
    fake_service = _make_fake_service()
    with patch("scrapp_taxonomy.cli.build_service", return_value=fake_service):
        code = main(["assess", "https://example.com/"])
    assert code == 0


def test_assess_command_json_output(capsys: object) -> None:
    from io import StringIO

    fake_service = _make_fake_service()
    captured = StringIO()
    with (
        patch("scrapp_taxonomy.cli.build_service", return_value=fake_service),
        patch("sys.stdout", captured),
    ):
        code = main(["assess", "--output", "json", "https://example.com/"])
    assert code == 0
    output = captured.getvalue()
    parsed = json.loads(output)
    assert "target_url" in parsed


def test_no_command_returns_2() -> None:
    code = main([])
    assert code == 2
