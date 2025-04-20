import os
import logging
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine # For sync engine if needed for migrations later

# -- DEFINE BASE HERE --
Base = declarative_base()

# Ensure models are imported somewhere before init_db is called so Base is populated.
# Remove Base import from models.py and billing_models.py
# Imports below are for database.py functionality, not Base registration
# from .models import Base # REMOVED
# from . import billing_models # Can keep this import if needed elsewhere, or remove
from . import models # Import models to ensure they register with Base here
from . import billing_models # Import billing_models to ensure they register with Base here

logger = logging.getLogger("shared_models.database")

# --- Database Configuration --- 
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "vexa")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL_SYNC = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SQLAlchemy Async Engine & Session --- 
# Use pool settings appropriate for async connections
engine = create_async_engine(
    DATABASE_URL, 
    echo=os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG",
    pool_size=10, # Example pool size
    max_overflow=20 # Example overflow
)
async_session_local = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- Sync Engine (Optional, for Alembic) ---
# sync_engine = create_engine(DATABASE_URL_SYNC)

# --- FastAPI Dependency --- 
async def get_db() -> AsyncSession:
    """FastAPI dependency to get an async database session."""
    async with async_session_local() as session:
        try:
            yield session
        finally:
            # Ensure session is closed, though context manager should handle it
            await session.close()

# --- Initialization Function (MODIFIED TO DROP/CREATE) --- 
async def init_db(drop_tables: bool = False):
    """
    Initializes database tables based on shared models' metadata.
    If drop_tables is True, ALL existing tables defined in Base.metadata
    will be dropped first. USE WITH CAUTION IN PRODUCTION.
    """
    # Ensures that models in billing_models are loaded and registered with Base.metadata
    # This is implicitly handled by the import: from . import billing_models
    
    logger.info(f"Initializing database tables at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    if drop_tables:
        logger.warning("!!! DROPPING ALL TABLES DEFINED IN Base METADATA !!!")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Existing tables dropped successfully.")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}", exc_info=True)
            raise
            
    logger.info("Creating database tables...")
    try:
        async with engine.begin() as conn:
            # This relies on all SQLAlchemy models being imported 
            # somewhere before this runs, so Base.metadata is populated
            # (models.py and billing_models.py).
            # Create all tables (no checkfirst needed after potential drop)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise 