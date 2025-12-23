"""
Repository Layer - Data Access Layer

This layer encapsulates all database operations and provides a clean interface
for the service layer to interact with data.

Responsibilities:
- Execute database queries
- Handle ORM operations
- Provide data access abstractions
- Single source of truth for queries

Benefits:
- Service layer focuses on business logic
- Easier to test (mock repositories)
- Query optimization in one place
- Can add caching, query logging, etc.
"""

