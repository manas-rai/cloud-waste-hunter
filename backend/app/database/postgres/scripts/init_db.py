#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script

Simple script to create database tables locally.
No migrations needed for MVP - just drop and recreate.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.database.postgres.engine import async_engine
from app.schemas.base import Base
from app.schemas.detection import Detection
from app.schemas.audit import AuditLog


async def init_database(drop_existing: bool = False):
    """
    Initialize database tables
    
    Args:
        drop_existing: If True, drops existing tables before creating
    """
    print("🔧 Initializing PostgreSQL database...")
    
    async with async_engine.begin() as conn:
        if drop_existing:
            print("⚠️  Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
        
        print("📦 Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    await async_engine.dispose()
    
    print("✅ Database initialized successfully!")
    print("\nCreated tables:")
    print("  - detections")
    print("  - audit_logs")


async def drop_database():
    """Drop all tables"""
    print("⚠️  WARNING: Dropping all PostgreSQL tables...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await async_engine.dispose()
    print("✅ All tables dropped")


async def show_tables():
    """Show existing tables"""
    from sqlalchemy import text
    
    print("📊 Existing PostgreSQL tables:")
    
    async with async_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """))
        
        tables = result.fetchall()
        if tables:
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("  (no tables found)")
    
    await async_engine.dispose()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PostgreSQL database initialization script for Cloud Waste Hunter"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (WARNING: deletes all data)"
    )
    parser.add_argument(
        "--drop-only",
        action="store_true",
        help="Only drop tables, don't create (WARNING: deletes all data)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show existing tables and exit"
    )
    
    args = parser.parse_args()
    
    try:
        if args.show:
            asyncio.run(show_tables())
        elif args.drop_only:
            response = input("⚠️  This will DELETE ALL DATA. Continue? (yes/no): ")
            if response.lower() == "yes":
                asyncio.run(drop_database())
            else:
                print("Cancelled.")
        else:
            if args.drop:
                response = input("⚠️  This will DELETE ALL DATA and recreate tables. Continue? (yes/no): ")
                if response.lower() != "yes":
                    print("Cancelled.")
                    return
            
            asyncio.run(init_database(drop_existing=args.drop))
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

