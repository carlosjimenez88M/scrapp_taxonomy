# scrapp-taxonomy

Evaluate a URL before scraping it. The package checks `robots.txt` for permission and then reports what kinds of data are likely extractable from the page — headings, links, images, feeds, article URLs, JSON-LD types, forms — all with counts and samples.

Zero external dependencies. Pure Python ≥ 3.11.

---

## Install

```bash
# uv (recommended)
uv add scrapp-taxonomy

# pip
pip install scrapp-taxonomy

# try it without installing
uvx scrapp-taxonomy assess https://cnnespanol.cnn.com/colombia
```

---

## CLI

### Basic usage

```bash
scrapp-taxonomy assess https://cnnespanol.cnn.com/colombia
```

Output:

```
Target: https://cnnespanol.cnn.com/colombia
Robots: https://cnnespanol.cnn.com/robots.txt (found)
Allowed for scrapp-taxonomy/0.1: yes
Sitemaps:
  - https://cnnespanol.cnn.com/sitemap/index.xml
  - https://cnnespanol.cnn.com/sitemap/news.xml
Page fetch: fetched
Title: Noticias de Colombia hoy: política, elecciones, economía y más | CNN
Language: es
Extractable signals:
  - Headings: 5
  - Links: 285
  - Images: 45
  - JSON-LD structured data: 1
  - Article-like links: 85
Recommendations:
  - The target URL is fetchable for the configured user agent.
  - Use sitemap URLs as the first source for crawl discovery.
  - Initial extractable signals found: Headings, Links, Images, ...
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--output` | `text` | `text` or `json` |
| `--user-agent` | `scrapp-taxonomy/0.1` | HTTP User-Agent string |
| `--timeout` | `15.0` | Request timeout in seconds |
| `--log-level` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### JSON output

```bash
scrapp-taxonomy assess https://www.bbc.com/mundo --output json
```

The JSON structure matches the `ScrapeAssessment` dataclass exactly and is pipe-friendly:

```bash
scrapp-taxonomy assess https://www.eltiempo.com --output json \
  | jq '.page_taxonomy.candidates[] | select(.kind == "article_links") | .count'
```

---

## Library

### Quick start

```python
from scrapp_taxonomy import build_service

service = build_service(user_agent="mybot/1.0", timeout_seconds=10.0)
result = service.assess("https://cnnespanol.cnn.com/colombia")

print(result.robots_policy.target_allowed)  # True
print(result.page_taxonomy.title)           # page title
print(result.page_taxonomy.candidates)      # signal categories with counts
print(result.recommendations)              # prioritised action list
```

### Formatters

Both output formats are available programmatically:

```python
from scrapp_taxonomy import build_service, TextFormatter, JsonFormatter

service = build_service()
result = service.assess("https://cnnespanol.cnn.com/colombia")

print(TextFormatter().format(result))   # same as CLI text output
print(JsonFormatter(indent=2).format(result))  # same as CLI --output json
```

### Custom signal extractors

Signal categories are injected — you can add new ones or remove defaults without touching the package source:

```python
from scrapp_taxonomy import build_service
from scrapp_taxonomy.services.html_analyzer import (
    DEFAULT_SIGNALS,
    SignalSpec,
    StandardHtmlAnalyzer,
    _ParseResult,
)
from scrapp_taxonomy.services.assessment import ScrapeAssessmentService
from scrapp_taxonomy.infrastructure.http import (
    HttpRobotsGateway, HttpPageGateway, UrlLibHttpClient,
)
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader

# Add a custom signal: detect video embed iframes
video_signal = SignalSpec(
    kind="video_embeds",
    label="Video embeds",
    extract=lambda r: [lnk for lnk in r.links if "youtube" in lnk or "vimeo" in lnk],
)

client = UrlLibHttpClient()
service = ScrapeAssessmentService(
    robots_gateway=HttpRobotsGateway(client),
    page_gateway=HttpPageGateway(client),
    robots_reader=StandardRobotsPolicyReader(),
    analyzer=StandardHtmlAnalyzer(signals=(*DEFAULT_SIGNALS, video_signal)),
)

result = service.assess("https://example.com")
```

### Logging

The package uses `logging.getLogger(__name__)` throughout. To see internal activity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from scrapp_taxonomy import build_service
service = build_service()
result = service.assess("https://cnnespanol.cnn.com/colombia")
```

---

## Docker

### Development

```bash
docker build -t scrapp-taxonomy:local .
docker run --rm scrapp-taxonomy:local assess https://cnnespanol.cnn.com/colombia
docker run --rm scrapp-taxonomy:local assess https://www.bbc.com/mundo --output json
```

### Production

The image runs as a non-root user (`scrapp`, uid 1001). For production workloads, add read-only filesystem and privilege restrictions:

```bash
docker run --rm \
  --read-only \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  ghcr.io/carlosjimenez88m/scrapp_taxonomy:latest \
  assess https://cnnespanol.cnn.com/colombia --output json
```

Images are published to GHCR automatically by CI on every push to `master` and on version tags. Available tags:

| Tag | When |
|---|---|
| `latest` | Every push to `master` |
| `1.2.3` | When tag `v1.2.3` is pushed |
| `1.2` | Same |
| `sha-abc1234` | Every commit |

---

## Architecture

```
src/scrapp_taxonomy/
├── domain/
│   └── models.py      # Immutable dataclasses and enums — no I/O, no imports
├── ports.py           # Protocol interfaces (RobotsGateway, PageGateway, Formatter…)
├── factory.py         # Single wiring point for the object graph (DI entry)
├── formatters.py      # TextFormatter and JsonFormatter implementations
├── infrastructure/
│   └── http.py        # urllib-based HTTP client and gateway adapters
├── services/
│   ├── assessment.py  # Orchestration: robots check → page fetch → recommendations
│   ├── html_analyzer.py # HTML parsing with injectable SignalSpec list
│   └── robots.py      # robots.txt parsing and policy resolution
└── cli.py             # argparse entry point with --log-level support
```

Each layer only imports from layers below it. `factory.py` is the one place that wires everything together; nothing else instantiates concrete classes directly.

To plug in a custom HTTP backend (httpx, requests, async), implement `RobotsGateway` and `PageGateway` from `ports.py` and pass them to `ScrapeAssessmentService` directly.

---

## Development

```bash
uv sync --dev              # install dev dependencies
make check                 # lint + type check + tests
make coverage              # tests with HTML coverage report (opens htmlcov/)
make fmt                   # auto-format with ruff
make build                 # build wheel and sdist in dist/
make docker-build          # build Docker image locally
make docker-run URL=https://cnnespanol.cnn.com/colombia  # run against a URL
make pre-commit-install    # install git hooks
```

Coverage is measured on every CI run and must stay above 80%.

---

## CI/CD pipeline

All delivery steps run in a single workflow (`.github/workflows/pipeline.yml`):

```
quality (Python 3.11, 3.12, 3.13)
    lint → type check → test + coverage gate (≥ 80%)
         ↓
    build-dist            docker
    wheel + sdist         multi-arch image (amd64 + arm64)
    smoke tests           push to GHCR on non-PR
         ↓
    publish (v* tags only)
    PyPI via Trusted Publishing
```

---

## Releasing

Releases are triggered by a version tag:

```bash
git tag -a v0.1.1 -m "v0.1.1"
git push origin v0.1.1
```

The pipeline builds the distributions, smoke-tests them in an isolated environment, and publishes to PyPI using [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no API token stored in GitHub secrets.

**One-time setup before the first release:**

1. GitHub → repo Settings → Environments → New environment → name: `pypi`
2. PyPI → your project → Settings → Trusted Publishers → add this repo and workflow

---

## Scope

This tool checks technical signals — it does not substitute for reading a website's terms of service, understanding copyright restrictions, or complying with applicable data-protection regulations. `robots.txt` is treated as the first boundary for respectful crawling, not the only one.
