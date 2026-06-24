from __future__ import annotations

from scrapp_taxonomy.domain.models import FetchStatus, HttpResource
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService
from scrapp_taxonomy.services.html_analyzer import StandardHtmlAnalyzer
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _RobotsStub:
    def __init__(self, resource: HttpResource) -> None:
        self._r = resource

    def fetch_for(self, url: str) -> HttpResource:
        return self._r


class _PageStub:
    def __init__(self, resource: HttpResource) -> None:
        self._r = resource

    def fetch(self, url: str) -> HttpResource:
        return self._r


def _make_robots_resource(body: str, status_code: int = 200) -> HttpResource:
    return HttpResource(
        url="https://example.com/robots.txt",
        status_code=status_code,
        body=body,
    )


def _make_page_resource(body: str) -> HttpResource:
    return HttpResource(
        url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/html",
        body=body,
    )


def _make_service(
    robots_body: str,
    page_body: str = "<html><body></body></html>",
    robots_status: int = 200,
) -> ScrapeAssessmentService:
    robots_resource = _make_robots_resource(robots_body, robots_status)
    page_resource = _make_page_resource(page_body)
    return ScrapeAssessmentService(
        robots_gateway=_RobotsStub(robots_resource),
        page_gateway=_PageStub(page_resource),
        robots_reader=StandardRobotsPolicyReader(),
        analyzer=StandardHtmlAnalyzer(),
        user_agent="scrapp-taxonomy/0.1",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_skips_page_when_robots_disallows() -> None:
    service = _make_service("User-agent: *\nDisallow: /")
    assessment = service.assess("https://example.com/")
    assert assessment.page_taxonomy.status is FetchStatus.SKIPPED


def test_fetches_page_when_allowed() -> None:
    service = _make_service("User-agent: *\nDisallow:\n")
    assessment = service.assess("https://example.com/")
    assert assessment.page_taxonomy.status is FetchStatus.FETCHED


def test_recommendations_include_crawl_delay() -> None:
    service = _make_service("User-agent: *\nAllow: /\nCrawl-delay: 5\n")
    assessment = service.assess("https://example.com/")
    assert any("crawl delay" in rec.lower() for rec in assessment.recommendations)


def test_assessment_target_url_matches_input() -> None:
    service = _make_service("User-agent: *\nDisallow:\n")
    assessment = service.assess("https://example.com/")
    assert assessment.target_url == "https://example.com/"


def test_skipped_assessment_has_no_candidates() -> None:
    service = _make_service("User-agent: *\nDisallow: /")
    assessment = service.assess("https://example.com/")
    assert assessment.page_taxonomy.candidates == ()
