# ── Stage 1: builder ────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /build

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ── Stage 2: runtime ────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="scrapp-taxonomy" \
      org.opencontainers.image.description="Assess robots.txt constraints and discover extractable public page signals." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/carlosjimenez88M/scrapp_taxonomy"

RUN groupadd --system --gid 1001 scrapp \
 && useradd --system --uid 1001 --gid scrapp --no-create-home --shell /sbin/nologin scrapp

COPY --from=builder --chown=scrapp:scrapp /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

USER scrapp
WORKDIR /app

ENTRYPOINT ["scrapp-taxonomy"]
CMD ["--help"]
