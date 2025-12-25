.PHONY: help lint format type-check check-all fix-all

help:
	@echo "Available commands:"
	@echo "  make lint          - Run all linters (ruff, black check)"
	@echo "  make format        - Format code with ruff and black"
	@echo "  make type-check    - Run type checking with mypy"
	@echo "  make check-all     - Run all checks (lint + type-check)"
	@echo "  make fix-all       - Auto-fix all fixable issues"
	@echo "  make pre-commit    - Run pre-commit on all files"

lint:
	@echo "Running Ruff linter..."
	cd backend && uv run ruff check .
	@echo "Checking Black formatting..."
	cd backend && uv run black --check .

format:
	@echo "Formatting with Ruff..."
	cd backend && uv run ruff format .
	@echo "Formatting with Black..."
	cd backend && uv run black .

type-check:
	@echo "Running mypy type checker..."
	cd backend && uv run mypy app

check-all: lint type-check
	@echo "All checks completed!"

fix-all:
	@echo "Auto-fixing with Ruff..."
	cd backend && uv run ruff check --fix .
	@echo "Formatting with Ruff..."
	cd backend && uv run ruff format .
	@echo "Formatting with Black..."
	cd backend && uv run black .

pre-commit:
	@echo "Running pre-commit on all files..."
	cd backend && uv run pre-commit run --all-files
