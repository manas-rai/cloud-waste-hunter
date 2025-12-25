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
│   │   ├── api/         # REST API endpoints (Presentation Layer)
│   │   ├── models/      # Pydantic models (API request/response)
│   │   ├── schemas/     # SQLAlchemy models (Database tables)
│   │   ├── database/    # Database connection management
│   │   │   └── postgres/
│   │   │       ├── engine.py   # Connection pool, sessions
│   │   │       └── scripts/    # Setup scripts (init_db.py)
│   │   ├── services/    # Business logic layer
│   │   ├── repositories/# Data access layer
│   │   ├── detection/   # ML detection algorithms
│   │   ├── aws/         # AWS integration
│   │   ├── safety/      # Safety mechanisms (dry-run, rollback)
│   │   └── core/        # Configuration
│   └── pyproject.toml   # Dependencies (managed by uv)
├── frontend/            # Next.js/React/TypeScript dashboard
│   ├── app/            # Next.js app directory
│   └── package.json
└── README.md           # This file
```

## Tech Stack

- **Backend**: Python 3.12+, FastAPI 0.126+, SQLAlchemy, boto3
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (fast Python package installer)
- **ML**: scikit-learn (Isolation Forest), pandas, numpy
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL
- **Infrastructure**: Docker, AWS SDK

## Getting Started

## 🚀 Quick Start (First-Time Setup)

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+** (recommended: 3.12.12)
  ```bash
  python --version  # Should be 3.12.x
  ```

- **uv** - Fast Python package installer
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Verify: uv --version
  ```

- **Node.js 18+** with npm
  ```bash
  node --version  # Should be 18.x or higher
  ```

- **PostgreSQL 18**
  ```bash
  # macOS (Homebrew)
  brew install postgresql@18
  brew services start postgresql@18

  # Verify
  psql --version
  ```

- **AWS Account** with IAM credentials (for scanning AWS resources)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd cloud-waste-hunter
```

### Step 2: Backend Setup

```bash
cd backend

# 1. Install dependencies (creates .venv automatically)
uv sync

# 2. Create .env file
cp .env.example .env
# Edit .env with your configuration (see Configuration section below)

# 3. Create PostgreSQL database
createdb cloud_waste_hunter

# 4. Initialize database tables (ONE-TIME SETUP)
uv run python -m app.database.postgres.scripts.init_db

# Verify tables were created
uv run python -m app.database.postgres.scripts.init_db --show
```

### Step 3: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

### Configuration

Edit `backend/.env` with your settings:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cloud_waste_hunter

# AWS Credentials (from AWS IAM)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Application
DEBUG=true
CORS_ORIGINS=http://localhost:3000

# Detection Thresholds (optional - defaults provided)
EC2_IDLE_CPU_THRESHOLD=5.0
EC2_IDLE_DAYS=7
EBS_UNATTACHED_DAYS=30
SNAPSHOT_AGE_DAYS=90
```

**Getting AWS Credentials:**
1. Go to AWS Console → IAM → Users
2. Create user or select existing user
3. Create Access Key → "Command Line Interface (CLI)"
4. Copy Access Key ID and Secret Access Key

### Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload
# Server runs on http://localhost:8000
# API docs at http://localhost:8000/api/docs
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Dashboard runs on http://localhost:3000
```

### Verify Setup

1. **Backend Health Check:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

2. **Frontend:**
   Open browser to `http://localhost:3000`

3. **Database:**
   ```bash
   cd backend
   uv run python -m app.database.postgres.scripts.init_db --show
   # Should show: detections, audit_logs tables
   ```

## 🔧 Troubleshooting

### Database Connection Issues

**Error: "could not connect to server"**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL (macOS)
brew services start postgresql@18
```

**Error: "database does not exist"**
```bash
# Create the database
createdb cloud_waste_hunter
```

### Import Errors

**Error: "ModuleNotFoundError"**
```bash
# Reinstall dependencies
cd backend
uv sync --reinstall
```

### Port Already in Use

**Error: "Address already in use"**
```bash
# Kill process on port 8000
lsof -ti :8000 | xargs kill -9

# Or use a different port
uv run uvicorn app.main:app --reload --port 8001
```

## 📖 Usage

### Running a Scan

1. **Via Dashboard:**
   - Go to http://localhost:3000
   - Click "Run Scan"
   - Select resource types (EC2, EBS, Snapshots)
   - View results in Detections page

2. **Via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/detections/scan \
     -H "Content-Type: application/json" \
     -d '{"resource_types": ["ec2_instance", "ebs_volume", "ebs_snapshot"]}'
   ```

### Approving Actions

1. Navigate to Actions page
2. Review detection details
3. Click "Preview" to see impact
4. Click "Approve" to execute (or "Dry Run" to test)

### Viewing Audit Logs

1. Go to Audit page
2. Filter by action type, status, or resource
3. Review execution history
4. Rollback actions if needed (within 7 days)

## 🏗️ Architecture Overview

### Backend Layers

1. **API Layer** (`api/`) - HTTP endpoints, request validation
2. **Service Layer** (`services/`) - Business logic orchestration
3. **Repository Layer** (`repositories/`) - Data access
4. **Detection Layer** (`detection/`) - ML algorithms
5. **Database Layer** (`database/`) - Connection management
6. **Schemas** (`schemas/`) - Database tables (SQLAlchemy)
7. **Models** (`models/`) - API models (Pydantic)

### Key Design Decisions

- ✅ **Separation of Concerns**: Each layer has single responsibility
- ✅ **No Session Leaks**: Centralized session management via `get_db()`
- ✅ **Setup vs Runtime**: Database setup is one-time, separate from app lifecycle
- ✅ **Clean Architecture**: Easy to test, maintain, and extend

## 📚 Additional Documentation

- **Database Setup**: `backend/app/database/postgres/scripts/README.md`
- **API Documentation**: http://localhost:8000/api/docs (when running)
- **Architecture Details**: See `backend/` folder structure

## 🤝 Contributing

For development:

1. Follow the setup steps above
2. Make changes in a feature branch
3. Test locally before committing
4. Use descriptive commit messages

## License

Proprietary
