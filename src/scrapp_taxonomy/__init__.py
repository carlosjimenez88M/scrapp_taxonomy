"""
scrapp-taxonomy — assess robots.txt constraints and discover page signals.

Public API surface for library consumers. Import from here rather than from
internal sub-modules; only the names listed in ``__all__`` are considered stable.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import logging
from importlib.metadata import version

from scrapp_taxonomy.domain.models import ScrapeAssessment
from scrapp_taxonomy.factory import build_service
from scrapp_taxonomy.formatters import JsonFormatter, TextFormatter
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService

######################
# ---- Loggers  ---- #
######################

logging.getLogger(__name__).addHandler(logging.NullHandler())

############################
# ---- Package Metadata ---- #
############################

__version__ = version("scrapp-taxonomy")
__all__ = [
    "ScrapeAssessment",
    "ScrapeAssessmentService",
    "build_service",
    "TextFormatter",
    "JsonFormatter",
    "__version__",
]
