FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

LABEL org.opencontainers.image.title="scrapp-taxonomy" \
      org.opencontainers.image.description="Assess robots.txt constraints and discover extractable public page signals." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/danieljimenez88m/scrapp-taxonomy"

ENV PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

ENTRYPOINT ["scrapp-taxonomy"]
CMD ["--help"]
