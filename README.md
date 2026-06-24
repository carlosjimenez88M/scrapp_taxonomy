# scrapp-taxonomy

Assess `robots.txt` constraints and discover extractable public page signals — before you scrape.

The package answers two practical questions:

1. Can this URL be fetched according to `robots.txt` for a given user agent?
2. If it can be fetched, what public page signals look extractable?

Zero external dependencies. Pure Python ≥ 3.11.

---

## Install

```bash
# pip
pip install scrapp-taxonomy

# uv (recommended)
uv add scrapp-taxonomy

# run without installing
uvx scrapp-taxonomy assess https://cnnespanol.cnn.com/colombia
```

## CLI usage

```bash
# text report (default)
scrapp-taxonomy assess https://cnnespanol.cnn.com/colombia

# JSON output — pipe-friendly
scrapp-taxonomy assess https://www.bbc.com/mundo --output json

# custom user agent and timeout
scrapp-taxonomy assess https://www.eltiempo.com \
  --user-agent "mybot/1.0" \
  --timeout 10
```

## Library usage

```python
from scrapp_taxonomy import ScrapeAssessment, ScrapeAssessmentService
from scrapp_taxonomy.infrastructure.http import (
    HttpPageGateway,
    HttpRobotsGateway,
    UrlLibHttpClient,
)
from scrapp_taxonomy.services.html_analyzer import StandardHtmlAnalyzer
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader

client = UrlLibHttpClient(user_agent="mybot/1.0", timeout_seconds=10.0)
service = ScrapeAssessmentService(
    robots_gateway=HttpRobotsGateway(client),
    page_gateway=HttpPageGateway(client),
    robots_reader=StandardRobotsPolicyReader(),
    analyzer=StandardHtmlAnalyzer(),
)

result: ScrapeAssessment = service.assess("https://cnnespanol.cnn.com/colombia")
print(result.robots_policy.target_allowed)   # True / False
print(result.page_taxonomy.title)            # page title
print(result.recommendations)                # actionable strings
```

The package is fully typed (PEP 561 `py.typed` marker included).

## Architecture

```
src/scrapp_taxonomy/
├── domain/        # immutable data models
├── ports.py       # Protocol interfaces (RobotsGateway, PageGateway, …)
├── infrastructure/# HTTP adapters (stdlib urllib only)
├── services/      # robots policy reader, HTML analyzer, orchestration
└── cli.py         # argparse entry point
```

Custom HTTP backends (httpx, requests, async) can be plugged in by implementing the `ports.py` protocols.

## Docker

```bash
docker build -t scrapp-taxonomy:local .
docker run --rm scrapp-taxonomy:local assess https://cnnespanol.cnn.com/colombia
docker run --rm scrapp-taxonomy:local assess https://www.bbc.com/mundo --output json
```

## Development

```bash
uv sync --dev          # install all dev dependencies
make check             # lint + type-check + tests
make coverage          # tests with coverage report
make fmt               # auto-format
make build             # build wheel + sdist
make docker-build      # build Docker image locally
```

Install pre-commit hooks:

```bash
make pre-commit-install
```

## Publishing

Releases are triggered by pushing a version tag:

```bash
git tag -a v0.1.0 -m v0.1.0
git push origin v0.1.0
```

The GitHub Actions workflow publishes to PyPI using Trusted Publishing (no token stored in secrets). Configure a PyPI environment named `pypi` in your repository settings before the first release.

## Scope

This package is a technical assistant, not legal advice. `robots.txt` is treated as the first boundary for respectful crawling. You should also respect website terms, copyright, rate limits, authentication walls, and personal-data rules.
