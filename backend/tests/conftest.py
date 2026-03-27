"""
Test configuration: set dummy AWS env vars so Settings() can be instantiated
without real credentials.
"""

import os

# Set dummy values before any app modules are imported (which may load settings)
os.environ["AWS_REGION"] = "ap-south-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost/test",
)
