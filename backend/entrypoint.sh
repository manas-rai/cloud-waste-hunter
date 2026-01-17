#!/bin/bash
set -e

echo "🚀 Starting backend entrypoint script..."
echo "📂 Current directory: $(pwd)"
echo "👤 User: $(whoami)"
echo "📦 Python version: $(python --version)"
echo "📦 Installed packages:"
/app/.venv/bin/pip list | head -n 20

echo "🚀 Starting Uvicorn..."
exec /app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
