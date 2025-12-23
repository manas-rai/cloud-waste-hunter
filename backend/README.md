# Cloud Waste Hunter Backend

**Requirements**: Python 3.12+ (recommended: 3.12.12)

## Setup with uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv

# Install dependencies and create virtual environment
uv sync

# Run commands with uv
uv run uvicorn app.main:app --reload
uv run alembic upgrade head
uv run pytest
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/        # REST API endpoints
│   ├── aws/           # AWS integration
│   ├── detection/     # ML detection algorithms
│   ├── safety/        # Safety layer
│   ├── models/        # Database models
│   └── core/         # Configuration
├── alembic/          # Database migrations
├── pyproject.toml    # uv project configuration
└── requirements.txt   # pip requirements (for compatibility)
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with auto-reload
uv run uvicorn app.main:app --reload

# Run migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
- AWS credentials
- Database URL
- Detection thresholds
- Safety settings

