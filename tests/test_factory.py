from __future__ import annotations

from scrapp_taxonomy.factory import build_service
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService


def test_returns_assessment_service() -> None:
    service = build_service()
    assert isinstance(service, ScrapeAssessmentService)


def test_default_user_agent() -> None:
    service = build_service()
    assert service.user_agent == "scrapp-taxonomy/0.1"


def test_custom_user_agent_propagates() -> None:
    service = build_service(user_agent="mybot/1.0")
    assert service.user_agent == "mybot/1.0"


def test_custom_timeout_accepted() -> None:
    service = build_service(timeout_seconds=30.0)
    assert isinstance(service, ScrapeAssessmentService)
