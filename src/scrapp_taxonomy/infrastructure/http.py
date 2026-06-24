from __future__ import annotations

from dataclasses import dataclass
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from scrapp_taxonomy.domain.models import HttpResource


@dataclass(frozen=True)
class UrlLibHttpClient:
    user_agent: str = "scrapp-taxonomy/0.1"
    timeout_seconds: float = 15.0

    def get(self, url: str) -> HttpResource:
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                headers = response.headers
                body = self._decode(response.read(), headers)
                return HttpResource(
                    url=url,
                    status_code=response.status,
                    body=body,
                    content_type=headers.get("Content-Type"),
                    final_url=response.geturl(),
                )
        except HTTPError as exc:
            body = self._decode(exc.read(), exc.headers)
            return HttpResource(
                url=url,
                status_code=exc.code,
                body=body,
                content_type=exc.headers.get("Content-Type"),
                final_url=exc.geturl(),
                error=None if exc.code == 404 else str(exc),
            )
        except URLError as exc:
            return HttpResource(url=url, status_code=None, body="", error=str(exc.reason))
        except TimeoutError as exc:
            return HttpResource(url=url, status_code=None, body="", error=str(exc))

    @staticmethod
    def _decode(raw: bytes, headers: Message) -> str:
        charset = headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


@dataclass(frozen=True)
class HttpRobotsGateway:
    client: UrlLibHttpClient

    def fetch_for(self, target_url: str) -> HttpResource:
        parsed = urlparse(target_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        return self.client.get(robots_url)


@dataclass(frozen=True)
class HttpPageGateway:
    client: UrlLibHttpClient

    def fetch(self, url: str) -> HttpResource:
        return self.client.get(url)


def absolutize_url(base_url: str, maybe_relative_url: str) -> str:
    return urljoin(base_url, maybe_relative_url)
