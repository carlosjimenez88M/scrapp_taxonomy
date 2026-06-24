.PHONY: sync fmt lint type-check test coverage check build docker-build pre-commit-install

sync:
	uv sync --dev

fmt:
	uv run ruff format
	uv run ruff check --fix

lint:
	uv run ruff format --check
	uv run ruff check

type-check:
	uv run mypy src

test:
	uv run pytest

coverage:
	uv run pytest --cov --cov-report=term-missing

check: lint type-check test

build:
	uv build --no-sources

docker-build:
	docker build -t scrapp-taxonomy:local .

pre-commit-install:
	uv run pre-commit install
