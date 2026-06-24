"""Tools to assess respectful web scraping boundaries."""

from importlib.metadata import version

from scrapp_taxonomy.domain.models import ScrapeAssessment
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService

__version__ = version("scrapp-taxonomy")
__all__ = ["ScrapeAssessment", "ScrapeAssessmentService", "__version__"]
