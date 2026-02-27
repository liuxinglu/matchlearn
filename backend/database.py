"""
Database configuration for MatchLearn application.

This module provides the database engine, session factory, and base class
for SQLAlchemy models using async SQLite.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Create a database URL for SQLite
DATABASE_URL = "sqlite+aiosqlite:///./matchlearn.db"

# Create the async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

# Create a configured "Session" class
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for our models
Base = declarative_base()


# Dependency to get the database session
async def get_db():
    """
    FastAPI dependency that provides a database session.

    Yields:
        AsyncSession: An async database session

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
    """
    async with AsyncSessionLocal() as session:
        yield session
