# Database Scripts

Simple utility scripts for database management.

## Database Initialization

### `init_db.py`

Creates database tables locally without migrations. Perfect for MVP development.

### Usage

#### First Time Setup
```bash
# Initialize database tables
uv run python scripts/init_db.py
```

#### Drop and Recreate (WARNING: Deletes all data)
```bash
# This will prompt for confirmation
uv run python scripts/init_db.py --drop
```

#### Show Existing Tables
```bash
uv run python scripts/init_db.py --show
```

#### Drop Tables Only
```bash
# This will prompt for confirmation
uv run python scripts/init_db.py --drop-only
```

### What It Creates

The script creates two tables:

1. **`detections`**
   - Stores waste detection results
   - Fields: resource_type, resource_id, confidence_score, status, etc.

2. **`audit_logs`**
   - Tracks all actions taken
   - Fields: action_type, resource_id, status, executed_by, etc.

### Prerequisites

- PostgreSQL running locally
- `.env` file configured with `DATABASE_URL`
- Example: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cloud_waste_hunter`

### Troubleshooting

#### Connection Error
```
ERROR: could not connect to server
```
**Solution**: Make sure PostgreSQL is running:
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql@18
```

#### Database Does Not Exist
```
ERROR: database "cloud_waste_hunter" does not exist
```
**Solution**: Create the database:
```bash
createdb cloud_waste_hunter
# or
psql -U postgres -c "CREATE DATABASE cloud_waste_hunter;"
```

#### Permission Denied
```
ERROR: permission denied for schema public
```
**Solution**: Grant permissions:
```bash
psql -U postgres -d cloud_waste_hunter -c "GRANT ALL ON SCHEMA public TO postgres;"
```

### Why No Migrations?

For MVP simplicity:
- ✅ **Faster**: No migration files to manage
- ✅ **Simpler**: Just drop and recreate when schema changes
- ✅ **Local-first**: Perfect for development
- ⚠️ **Not for production**: Use proper migrations (Alembic) before production

### When to Add Migrations

Add proper migration tooling (Alembic) when:
- Moving to production
- Multiple developers need schema versioning
- Need to preserve existing data during schema changes
- Deploying to staging/production environments

For now, this simple script is perfect for MVP development! 🚀

