"""
Command-line interface for scrapp-taxonomy.

Exposes a single sub-command — ``assess`` — that evaluates a URL against its
robots.txt policy and reports discoverable page signals. Output can be rendered
as a plain-text report or as JSON for downstream processing.

Usage::

    scrapp-taxonomy assess <url> [--output json] [--user-agent <ua>] [--timeout <s>]
                                 [--log-level DEBUG|INFO|WARNING|ERROR]
"""

from __future__ import annotations

#######################
# ---- Libraries ---- #
#######################
import argparse
import logging
import sys
from collections.abc import Sequence

from scrapp_taxonomy.factory import build_service
from scrapp_taxonomy.formatters import JsonFormatter, TextFormatter

######################
# ---- Loggers  ---- #
######################

logger = logging.getLogger(__name__)

#######################
# ---- Functions ---- #
#######################


def main(argv: Sequence[str] | None = None) -> int:
    """Parse *argv* and execute the requested sub-command.

    Returns an exit code: 0 on success, 2 when no sub-command is given.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)
    logger.debug("CLI invoked with args: %s", vars(args))

    if args.command == "assess":
        service = build_service(user_agent=args.user_agent, timeout_seconds=args.timeout)
        assessment = service.assess(args.url)
        formatter = JsonFormatter() if args.output == "json" else TextFormatter()
        print(formatter.format(assessment))
        return 0

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrapp-taxonomy",
        description="Assess robots.txt boundaries and discover extractable page signals.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity (default: WARNING).",
    )
    subparsers = parser.add_subparsers(dest="command")
    assess = subparsers.add_parser("assess", help="Assess a target URL.")
    assess.add_argument("url", help="Fully-qualified URL to assess.")
    assess.add_argument(
        "--user-agent", default="scrapp-taxonomy/0.1", help="HTTP User-Agent string."
    )
    assess.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds.")
    assess.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level),
        format="%(levelname)-8s %(name)s %(message)s",
    )
