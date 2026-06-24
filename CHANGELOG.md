# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-23

### Added

- **robots.txt evaluation** — fetches and parses `robots.txt` for any target URL,
  determines whether the configured user-agent is permitted to fetch the page,
  and exposes crawl-delay, request-rate, sitemaps, and matching rule groups.
- **HTML signal discovery** — extracts headings, links, images, forms, RSS/Atom
  feeds, article-like links, and JSON-LD structured-data types from public pages.
- **`ScrapeAssessmentService`** — orchestrates robots evaluation and page analysis
  into a single `ScrapeAssessment` value object with actionable recommendations.
- **CLI** (`scrapp-taxonomy assess <url>`) — supports `--output text` (default)
  and `--output json`, `--user-agent`, and `--timeout` options.
- **`TextFormatter` / `JsonFormatter`** — pluggable output formatters decoupled
  from the CLI; importable for use in library contexts.
- **`build_service` factory** — one-call dependency wiring for production use.
- **`StandardHtmlAnalyzer`** with extensible `SignalSpec` / `DEFAULT_SIGNALS` —
  users can add or replace signal types without modifying the package.
- Multi-stage Docker image (builder + slim runtime, non-root user).
- Full type-checked codebase (mypy --strict) and ≥ 80 % test coverage gate.
