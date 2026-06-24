"""
HTTP infrastructure adapters built on Python's standard urllib.

These classes are the only components that perform real network I/O. They
implement the RobotsGateway and PageGateway protocols from ports.py using
nothing but the standard library, keeping the package dependency-free.
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import logging
from dataclasses import dataclass
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from scrapp_taxonomy.domain.models import HttpResource

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

############################
# ---- Infrastructure ---- #
############################


@dataclass(frozen=True)
class UrlLibHttpClient:
    """Synchronous HTTP client backed by urllib with configurable user-agent and timeout."""

    user_agent: str = "scrapp-taxonomy/0.1"
    timeout_seconds: float = 15.0

    def get(self, url: str) -> HttpResource:
        """Fetch *url* and return an HttpResource, capturing errors as structured data.

        Network and HTTP errors are caught and embedded in the returned resource
        rather than raised, so callers always receive a typed result.
        """
        logger.debug("GET %s", url)
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                headers = response.headers
                body = self._decode(response.read(), headers)
                logger.debug("HTTP %s %s", response.status, url)
                return HttpResource(
                    url=url,
                    status_code=response.status,
                    body=body,
                    content_type=headers.get("Content-Type"),
                    final_url=response.geturl(),
                )
        except HTTPError as exc:
            body = self._decode(exc.read(), exc.headers)
            logger.debug("HTTP %s %s", exc.code, url)
            return HttpResource(
                url=url,
                status_code=exc.code,
                body=body,
                content_type=exc.headers.get("Content-Type"),
                final_url=exc.geturl(),
                error=None if exc.code == 404 else str(exc),
            )
        except URLError as exc:
            logger.warning("Network error fetching %s: %s", url, exc.reason)
            return HttpResource(url=url, status_code=None, body="", error=str(exc.reason))
        except TimeoutError as exc:
            logger.warning("Timeout fetching %s", url)
            return HttpResource(url=url, status_code=None, body="", error=str(exc))

    @staticmethod
    def _decode(raw: bytes, headers: Message) -> str:
        charset = headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


@dataclass(frozen=True)
class HttpRobotsGateway:
    """Locate and fetch robots.txt for any target URL."""

    client: UrlLibHttpClient

    def fetch_for(self, target_url: str) -> HttpResource:
        """Return the robots.txt resource at the domain root of *target_url*."""
        parsed = urlparse(target_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        logger.debug("Fetching robots.txt from %s", robots_url)
        return self.client.get(robots_url)


@dataclass(frozen=True)
class HttpPageGateway:
    """Fetch arbitrary public pages via the shared HTTP client."""

    client: UrlLibHttpClient

    def fetch(self, url: str) -> HttpResource:
        """Return the HTTP resource for the given page URL."""
        return self.client.get(url)


######################
# ---- Functions ---- #
######################


def absolutize_url(base_url: str, maybe_relative_url: str) -> str:
    """Resolve *maybe_relative_url* against *base_url* and return an absolute URL."""
    return urljoin(base_url, maybe_relative_url)
