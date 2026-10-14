.PHONY: setup test lint format format-check check

setup:
	uv sync --group dev

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check . --fix

format-check:
	uv run ruff format --check .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest
