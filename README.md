# Cloud Waste Hunter 🎯

**Automated AWS Cost Optimization with ML-Powered Waste Detection**

## Overview

Cloud Waste Hunter identifies and safely eliminates wasteful AWS resources, saving customers ₹2-8L/month through intelligent automation.

### MVP Features

- **Idle EC2 Instances**: ML-powered detection (Isolation Forest) for instances with <5% CPU for 7+ days
- **Unattached EBS Volumes**: Detection of volumes available for 30+ days
- **Old Snapshots**: Identification of snapshots >90 days old without associated AMIs
- **Safety-First Execution**: Dry-run preview, manual approval, audit logging, 7-day rollback

## Architecture

```
cloud-waste-hunter/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/         # REST API endpoints
│   │   ├── core/        # Core business logic
│   │   ├── detection/   # ML detection algorithms
│   │   ├── aws/         # AWS integration layer
│   │   ├── safety/      # Safety layer (dry-run, approval, audit)
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic services
│   │   └── repositories/# Data access layer
│   ├── scripts/         # Utility scripts (DB init, etc.)
│   └── pyproject.toml
├── frontend/            # React/Next.js dashboard
│   ├── app/            # Next.js app directory
│   └── package.json
└── docs/               # Documentation
```

## Tech Stack

- **Backend**: Python 3.12+, FastAPI 0.126+, SQLAlchemy, boto3
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (fast Python package installer)
- **ML**: scikit-learn (Isolation Forest), pandas, numpy
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL
- **Infrastructure**: Docker, AWS SDK

## Getting Started

### Prerequisites

- Python 3.12+ (recommended: 3.12.12)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 18+
- PostgreSQL 18
- AWS Account with appropriate IAM permissions

### Installation

```bash
# Backend (using uv)
cd backend
uv sync  # Creates virtual environment and installs dependencies

# Frontend
cd frontend
npm install
```

### Configuration

1. Copy `.env.example` to `.env` and configure:
   - AWS credentials
   - Database connection
   - API keys

2. Initialize database:
```bash
cd backend
uv run python scripts/init_db.py
```

### Running

```bash
# Backend (port 8000)
cd backend
uv run uvicorn app.main:app --reload

# Frontend (port 3000)
cd frontend
npm run dev
```

## License

Proprietary
